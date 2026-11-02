from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from uuid import uuid4

import typer
from rich.console import Console
from rich.table import Table

from .logging_config import configure_logging
from .manifest import Manifest, ManifestFilters, load_manifest
from .orchestrator import GitOperation, orchestrate_repositories
from .reporting import print_summary, write_json_report

app = typer.Typer(help="High-throughput git operations across VDS projects.")


def _get_real_cpu_count() -> int:
    """Get real CPU count based on system specs.

    On macOS, prefers physical CPU count over logical cores.
    Falls back to os.cpu_count() on other systems or if detection fails.
    """
    try:
        import platform

        if platform.system() == "Darwin":  # macOS
            import subprocess

            # Timeout for sysctl command (configurable via VDS_GIT_SYSCTL_TIMEOUT, default: 1 second)
            sysctl_timeout = int(os.environ.get("VDS_GIT_SYSCTL_TIMEOUT", "1"))
            result = subprocess.run(
                ["sysctl", "-n", "hw.physicalcpu"],
                capture_output=True,
                text=True,
                timeout=sysctl_timeout,
            )
            if result.returncode == 0:
                physical = int(result.stdout.strip())
                if physical > 0:
                    return physical
        # Fallback to logical CPU count
        logical = os.cpu_count() or 4
        return logical
    except Exception:
        # Fallback to os.cpu_count() on any error
        return os.cpu_count() or 4


def _default_concurrency() -> int:
    """Get default concurrency from the effective shared env/config layer.

    The shared VDS env loader populates values into os.environ, so this helper
    checks os.environ after the configured env-file/default path resolution.
    """
    # Check environment variable after shared env loading/bootstrap
    env_value = os.environ.get("VDS_GIT_CONCURRENCY_DEFAULT")
    if env_value:
        try:
            parsed = int(env_value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass

    # Use real CPU count based on system specs
    cpu_count = _get_real_cpu_count()
    # Reduced default concurrency to avoid overwhelming git/network resources
    # Lower concurrency reduces contention on git operations and network connections
    baseline = max(2, cpu_count // 3)  # Changed from // 2 to // 3 for more conservative default
    return min(6, baseline)  # Reduced max from 8 to 6 to prevent resource exhaustion


def _load_manifest(path: Path) -> Manifest:
    if not path.exists():
        raise typer.BadParameter(f"Manifest not found: {path}")
    try:
        return load_manifest(path)
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        raise typer.BadParameter(f"Failed to load manifest: {exc}") from exc


def _build_filters(
    project: str | None,
    match: str | None,
    tags: list[str],
    skip_tags: list[str],
) -> ManifestFilters:
    return ManifestFilters(
        project=project,
        name_match=match,
        include_tags=set(tags or []),
        exclude_tags=set(skip_tags or []),
    )


@app.callback()
def callback(
    ctx: typer.Context,
    manifest_paths: list[Path] = typer.Option(
        [Path("repo-manifest.yaml")],
        "--manifest",
        "-m",
        help="Path(s) to repository manifest(s) (YAML).",
    ),
    concurrency: int | None = typer.Option(
        None,
        "--concurrency",
        "-c",
        help="Maximum concurrent git operations.",
    ),
    report_dir: Path = typer.Option(
        Path("reports/git_runs"),
        "--report-dir",
        help="Directory for JSON run reports.",
    ),
    json_log: bool = typer.Option(
        False,
        "--json-log",
        help="Emit structured JSON logs in addition to console output.",
    ),
) -> None:
    """
    Configure logging and attach manifest to the context for subcommands.
    """

    configure_logging(json_log=json_log)
    report_dir.mkdir(parents=True, exist_ok=True)

    manifests = [_load_manifest(path) for path in manifest_paths]

    combined_manifest = Manifest.merge(manifests)

    ctx.obj = {
        "manifest": combined_manifest,
        "concurrency": concurrency if concurrency is not None else _default_concurrency(),
        "report_dir": report_dir,
        "run_id": uuid4().hex,
    }


@app.command()
def pull(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project id."),
    match: str | None = typer.Option(None, "--match", help="Wildcard match against repo name."),
    tags: list[str] = typer.Option([], "--tag", help="Only include repos with tag."),
    skip_tags: list[str] = typer.Option([], "--skip-tag", help="Exclude repos with tag."),
    dry_run: bool = typer.Option(False, "--dry-run", help="List repositories without executing git."),
    overwrite_local_with_remote: bool = typer.Option(
        False,
        "--overwrite-local/--no-overwrite-local",
        help="Force local branch to match origin/<branch> (discards local divergence on pull).",
    ),
) -> None:
    """
    Fetch and fast-forward repositories.
    """

    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.PULL,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            overwrite_local_with_remote=overwrite_local_with_remote,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Serial retries: {summary.serial_retries}")
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": GitOperation.PULL.value,
            "dry_run": dry_run,
            "overwrite_local_with_remote": overwrite_local_with_remote,
            "run_id": run_id,
            "filters": {
                "project": filters.project,
                "match": filters.name_match,
                "include_tags": sorted(filters.include_tags),
                "exclude_tags": sorted(filters.exclude_tags),
            },
            "serial_retries": summary.serial_retries,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def fetch(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """
    Fetch latest refs for repositories without fast-forward.
    """

    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.FETCH,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Serial retries: {summary.serial_retries}")
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": GitOperation.FETCH.value,
            "dry_run": dry_run,
            "run_id": run_id,
            "filters": {
                "project": filters.project,
                "match": filters.name_match,
                "include_tags": sorted(filters.include_tags),
                "exclude_tags": sorted(filters.exclude_tags),
            },
            "serial_retries": summary.serial_retries,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def status(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
) -> None:
    """
    Show git status for repositories.
    """

    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.STATUS,
            filters=filters,
            concurrency=concurrency,
            dry_run=False,
            run_id=run_id,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Serial retries: {summary.serial_retries}")
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": GitOperation.STATUS.value,
            "dry_run": False,
            "run_id": run_id,
            "filters": {
                "project": filters.project,
                "match": filters.name_match,
                "include_tags": sorted(filters.include_tags),
                "exclude_tags": sorted(filters.exclude_tags),
            },
            "serial_retries": summary.serial_retries,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def clone(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """
    Clone repositories that are missing locally.
    """

    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.CLONE,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Serial retries: {summary.serial_retries}")
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": GitOperation.CLONE.value,
            "dry_run": dry_run,
            "run_id": run_id,
            "filters": {
                "project": filters.project,
                "match": filters.name_match,
                "include_tags": sorted(filters.include_tags),
                "exclude_tags": sorted(filters.exclude_tags),
            },
            "serial_retries": summary.serial_retries,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command(name="list")
def list_repositories(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
) -> None:
    """
    List repositories from the manifest after applying filters.
    """

    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    repos = manifest.filter(filters)

    console = Console()
    if not repos:
        console.print("[yellow]No repositories matched the provided filters.[/yellow]")
        return

    table = Table("Name", "Project", "Branch", "Path", "Tags")
    for repo in repos:
        table.add_row(
            repo.name,
            repo.project,
            repo.branch,
            str(repo.absolute_path),
            ", ".join(sorted(repo.tags)) or "-",
        )

    console.print(table)


@app.command()
def branch(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, create, delete"),
    branch_name: str | None = typer.Option(None, "--name", help="Branch name (for create/delete)"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """List, create, or delete branches."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.BRANCH,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            action=action,
            branch_name=branch_name,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": f"branch-{action}",
            "dry_run": dry_run,
            "run_id": run_id,
            "branch_name": branch_name,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def checkout(
    ctx: typer.Context,
    branch_or_path: str = typer.Argument(..., help="Branch name or path to checkout"),
    create: bool = typer.Option(False, "--create", "-b", help="Create new branch"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Checkout a branch or path."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.CHECKOUT,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            branch_or_path=branch_or_path,
            create=create,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": "checkout",
            "branch_or_path": branch_or_path,
            "create": create,
            "dry_run": dry_run,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def add(
    ctx: typer.Context,
    paths: list[str] = typer.Argument(default=[], help="File paths to stage"),
    all_files: bool = typer.Option(False, "--all", "-A", help="Stage all files"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Stage files for commit."""
    if not all_files and not paths:
        typer.echo("Error: Either specify paths or use --all flag", err=True)
        raise typer.Exit(1) from None
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.ADD,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            paths=paths,
            all_files=all_files,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": "add",
            "paths": paths,
            "all_files": all_files,
            "dry_run": dry_run,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def commit(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="Commit message"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Commit staged changes."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.COMMIT,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            message=message,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": "commit",
            "message": message,
            "dry_run": dry_run,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def push(
    ctx: typer.Context,
    branch: str | None = typer.Option(None, "--branch", help="Branch to push"),
    remote: str | None = typer.Option(None, "--remote", help="Remote name (default: origin)"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Push commits to remote."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.PUSH,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            branch=branch,
            remote=remote,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": "push",
            "branch": branch,
            "remote": remote,
            "dry_run": dry_run,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def log(
    ctx: typer.Context,
    limit: int | None = typer.Option(None, "--limit", "-n", help="Number of commits to show"),
    oneline: bool = typer.Option(False, "--oneline", help="Show one line per commit"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
) -> None:
    """Show commit history."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.LOG,
            filters=filters,
            concurrency=concurrency,
            dry_run=False,
            run_id=run_id,
            limit=limit,
            oneline=oneline,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": "log",
            "limit": limit,
            "oneline": oneline,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def diff(
    ctx: typer.Context,
    paths: list[str] = typer.Argument(default=[], help="File paths to diff"),
    staged: bool = typer.Option(False, "--staged", help="Show staged changes"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
) -> None:
    """Show changes between commits, commit and working tree, etc."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.DIFF,
            filters=filters,
            concurrency=concurrency,
            dry_run=False,
            run_id=run_id,
            paths=paths,
            staged=staged,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": "diff",
            "paths": paths,
            "staged": staged,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def stash(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, save, pop, apply, drop"),
    message: str | None = typer.Option(None, "--message", "-m", help="Stash message (for save)"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Stash or restore working directory changes."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.STASH,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            action=action,
            message=message,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": f"stash-{action}",
            "message": message,
            "dry_run": dry_run,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def tag(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, create, delete"),
    tag_name: str | None = typer.Option(None, "--name", help="Tag name (for create/delete)"),
    message: str | None = typer.Option(None, "--message", "-m", help="Tag message (for create)"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """List, create, or delete tags."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.TAG,
            filters=filters,
            concurrency=concurrency,
            dry_run=dry_run,
            run_id=run_id,
            action=action,
            tag_name=tag_name,
            message=message,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": f"tag-{action}",
            "tag_name": tag_name,
            "message": message,
            "dry_run": dry_run,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


@app.command()
def remote(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, add, remove"),
    name: str | None = typer.Option(None, "--name", help="Remote name (for add/remove)"),
    url: str | None = typer.Option(None, "--url", help="Remote URL (for add)"),
    project: str | None = typer.Option(None, "--project", "-p"),
    match: str | None = typer.Option(None, "--match"),
    tags: list[str] = typer.Option([], "--tag"),
    skip_tags: list[str] = typer.Option([], "--skip-tag"),
) -> None:
    """List, add, or remove remotes."""
    manifest: Manifest = ctx.obj["manifest"]
    filters = _build_filters(project, match, tags, skip_tags)
    concurrency: int = ctx.obj["concurrency"]
    report_dir: Path = ctx.obj["report_dir"]
    run_id: str = ctx.obj["run_id"]

    start_time = time.perf_counter()
    summary = asyncio.run(
        orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.REMOTE,
            filters=filters,
            concurrency=concurrency,
            dry_run=False,
            run_id=run_id,
            action=action,
            name=name,
            url=url,
        )
    )
    duration = time.perf_counter() - start_time
    print_summary(summary)
    typer.echo(f"Duration: {duration:.2f}s")
    report_path = write_json_report(
        summary,
        report_dir,
        metadata={
            "operation": f"remote-{action}",
            "name": name,
            "url": url,
            "run_id": run_id,
            "duration_seconds": round(duration, 3),
        },
    )
    typer.echo(f"Report written to {report_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
