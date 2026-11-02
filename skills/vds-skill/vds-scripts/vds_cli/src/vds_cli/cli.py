"""Main CLI application using Typer.

Based on Typer v0.20.0+ API
Context7: /websites/typer_tiangolo
Key Features: typer.Typer(), @app.command(), Annotated options
"""

import importlib
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from vds_cli_common.env import DEFAULT_ENV_PATHS
from vds_cli_common.paths import get_shared_env_path

from . import env_git_helper as _env_git_helper
from .commands.lint_cli import lint_app
from .confluence_sync import run_confluence_sync
from .docs_cmd import check_freshness, discover_repo_roots, validate_docs
from .docs_metrics import generate_freshness_heatmap, generate_monthly_consumption_report
from .docs_sync import SyncError, run_watch_agents
from .ecosystem import ecosystem_app
from .ecosystem_docs import generate_ecosystem_index
from .env import load_environment
from .router import ORCHESTRATORS, run_orchestrator, validate_orchestrator
from .skills_cmd import skills_app
from .sync_service import ServiceError

app = typer.Typer(help="VDS Platform CLI - Unified Interface for AI Agents")
docs_app = typer.Typer(help="Instruction document synchronization operations.")
env_app = typer.Typer(help="Environment management (load, status, git credential helper lifecycle).")
console = Console()

PASS_THRU_CONTEXT = {"allow_extra_args": True, "ignore_unknown_options": True, "help_option_names": []}

# Get scripts directory (parent of vds_cli package)
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent

app.add_typer(docs_app, name="docs")
app.add_typer(skills_app, name="skills")
app.add_typer(env_app, name="env")
app.add_typer(lint_app, name="lint")
app.add_typer(ecosystem_app, name="ecosystem")


def _env_check_rows(settings) -> list[tuple[str, bool]]:
    has_user_pass = bool(settings.vds_username and settings.vds_password)
    has_bitbucket_token = bool(settings.bitbucket_access_token or os.getenv("BITBUCKET_TOKEN"))
    has_confluence_token = bool(settings.internal_confluence_token or settings.external_confluence_token)

    return [
        ("Shared env file present", get_shared_env_path().exists()),
        ("VDS credentials", has_user_pass),
        ("Bitbucket auth", has_bitbucket_token or has_user_pass),
        ("Confluence auth", has_confluence_token or has_user_pass),
    ]


def _load_manifest_module():
    """Dynamically load the shared manifest builder module.

    This avoids adding hard packaging dependencies between vds_cli and the
    root vds-scripts package while still allowing CLI commands to reuse the
    shared generator logic.
    """
    root = SCRIPT_DIR
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    try:
        return importlib.import_module("vds_scripts.manifest_builder")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Legacy manifest builder module is no longer available. "
            "Use `vds-audit export-git-manifest --output <path> --state-dsn <dsn>`."
        ) from exc


@env_app.command("load")
def env_load() -> None:
    """Load shared VDS environment from ~/.vds/.env."""
    settings = load_environment()
    console.print("[blue]🔄 Loading VDS environment...[/blue]")
    if settings.vds_username:
        console.print("[green]✅ VDS environment loaded successfully.[/green]")
    else:
        env_path = get_shared_env_path()
        console.print(f"[yellow]⚠️  VDS environment file not found at {env_path}[/yellow]")
        console.print(f"[yellow]💡 Create {env_path} with your credentials[/yellow]")


@env_app.command("status")
def env_status() -> None:
    """Show shared environment status."""
    settings = load_environment()
    table = Table(title="Environment Status")
    table.add_column("Variable", style="cyan")
    table.add_column("Status", style="magenta")
    for label, ok in _env_check_rows(settings):
        table.add_row(label, "✅ Set" if ok else "❌ Missing")
    console.print(table)

    missing = [label for label, ok in _env_check_rows(settings) if not ok]
    if missing:
        console.print("\n[yellow]Recommended actions:[/yellow]")
        if "Shared env file present" in missing:
            console.print(f"  1. Create the shared VDS env file at {get_shared_env_path()}.")
        if "VDS credentials" in missing:
            console.print("  2. Set VDS_USERNAME and VDS_PASSWORD in the shared VDS env file.")
        if "Bitbucket auth" in missing:
            console.print("  3. Set BITBUCKET_ACCESS_TOKEN or BITBUCKET_TOKEN (or VDS credentials).")
        if "Confluence auth" in missing:
            console.print("  4. Set INTERNAL_CONFLUENCE_TOKEN/EXTERNAL_CONFLUENCE_TOKEN (or VDS credentials).")


@env_app.command("install-git-helper")
def env_install_git_helper(
    force: bool = typer.Option(
        False,
        "--force",
        help="Override AC-24.6 signature check; remove pre-FR-24 artifacts unconditionally.",
    ),
) -> None:
    """Install canonical git credential helper (FR-23 AC-23.2)."""
    result = _env_git_helper.install(force=force)
    console.print(f"[green]✅ Installed[/green] git-credential-vds at {result.target}")
    console.print(f"[green]✅ Configured[/green] git: credential.helper = {result.target}")
    if result.probe_ok:
        console.print("[green]✅ Self-probe[/green] (allowlist-miss): exit 0, no output (correct)")
    else:
        console.print("[yellow]⚠️  Self-probe failed[/yellow] — investigate")
    for path in result.removed:
        console.print(f"[green]✅ Removed legacy artifact:[/green] {path}")
    for path in result.preserved:
        console.print(f"[yellow]⚠️  Preserved (signature mismatch, AC-24.6):[/yellow] {path}")
    if result.migrated_state:
        console.print(f"[green]✅ Migrated[/green] legacy state file → {result.migrated_state}")


@env_app.command("verify-git-helper")
def env_verify_git_helper(
    reset_cooldown: bool = typer.Option(
        False,
        "--reset-cooldown",
        help="Truncate the cooldown state file to clear active cooldowns.",
    ),
) -> None:
    """Verify git credential helper install state (FR-23 AC-23.3)."""
    exit_code, checks = _env_git_helper.verify(reset_cooldown=reset_cooldown)
    table = Table(title="Git Credential Helper — Verify")
    table.add_column("Check", style="cyan")
    table.add_column("Detail", style="white")
    table.add_column("Status", style="magenta")
    for check in checks:
        table.add_row(check.name, check.detail, "✅ OK" if check.ok else "❌ FAIL")
    console.print(table)
    if exit_code != 0:
        raise typer.Exit(exit_code) from None


@env_app.command("remove-git-helper")
def env_remove_git_helper(
    purge: bool = typer.Option(
        False,
        "--purge",
        help="Also delete the cooldown state file at ~/.vds/.git-credential-helper-cooldown.json.",
    ),
) -> None:
    """Uninstall git credential helper (FR-23 AC-23.4 — idempotent)."""
    result = _env_git_helper.remove(purge=purge)
    if result["deleted_binary"]:
        console.print("[green]✅ Removed[/green] git-credential-vds binary")
    else:
        console.print("[blue]ℹ️  No binary to remove[/blue] (already absent)")
    console.print("[green]✅ Unset[/green] git config credential.helper (idempotent)")
    if purge and result["deleted_state"]:
        console.print("[green]✅ Purged[/green] cooldown state file")


def _run_service(service: str, args: list[str]) -> None:
    if not args:
        typer.echo(
            f"Error: No arguments passed to '{service}'. Append the underlying CLI command and flags.",
            err=True,
        )
        raise typer.Exit(1) from None

    # Always load the shared environment before any orchestrator call
    load_environment()

    if service == "git":
        settings = load_environment()
        env_path = get_shared_env_path()

        if not settings.vds_git_projects:
            console.print(f"[red]❌ Error: VDS_GIT_PROJECTS must be set in {env_path}[/red]")
            console.print("[yellow]💡 Format: VDS_GIT_PROJECTS=lep,insurance,saving,ekyc[/yellow]")
            console.print("[yellow]💡 Example: VDS_GIT_PROJECTS=lep,insurance[/yellow]")
            raise typer.Exit(1) from None

        if settings.vds_bitbucket_http_base and "VDS_BITBUCKET_HTTP_BASE" not in os.environ:
            os.environ["VDS_BITBUCKET_HTTP_BASE"] = settings.vds_bitbucket_http_base

    try:
        exit_code = run_orchestrator(service, args, SCRIPT_DIR)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(2) from None
    if exit_code != 0:
        raise typer.Exit(exit_code) from None


@app.command(context_settings=PASS_THRU_CONTEXT)
def google_sheets(ctx: typer.Context) -> None:
    """Google Sheets orchestrator operations (read, write, sheet management)."""
    _run_service("google_sheets", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def elastic(ctx: typer.Context) -> None:
    """Elasticsearch operations via Kibana proxy."""
    _run_service("elastic", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def grafana(ctx: typer.Context) -> None:
    """Grafana logs operations."""
    _run_service("grafana", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def git(ctx: typer.Context) -> None:
    """Git repository operations."""
    _run_service("git", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def jira(ctx: typer.Context) -> None:
    """JIRA operations."""
    _run_service("jira", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def confluence(ctx: typer.Context) -> None:
    """Confluence operations."""
    _run_service("confluence", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def bitbucket(ctx: typer.Context) -> None:
    """Bitbucket operations."""
    _run_service("bitbucket", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def pdf(ctx: typer.Context) -> None:
    """PDF orchestrator operations."""
    _run_service("pdf", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def excel(ctx: typer.Context) -> None:
    """Excel orchestrator operations (read, write, sheet management, formatting)."""
    _run_service("excel", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def brd(ctx: typer.Context) -> None:
    """BRD coverage validation operations."""
    _run_service("brd", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def sonarqube(ctx: typer.Context) -> None:
    """SonarQube operations (quality gates, issues, scans)."""
    _run_service("sonarqube", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def markdown(ctx: typer.Context) -> None:
    """Markdown orchestrator operations."""
    _run_service("markdown", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def mcp(ctx: typer.Context) -> None:
    """MCP server operations."""
    _run_service("mcp", list(ctx.args))


@app.command(context_settings=PASS_THRU_CONTEXT)
def vidp(ctx: typer.Context) -> None:
    """VIDP third-party gateway operations (trigger workflows, poll job status)."""
    _run_service("vidp", list(ctx.args))


@docs_app.command("validate")
def docs_validate(
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        help="Repository root or umbrella directory containing VDS repos.",
    ),
    repo: str | None = typer.Option(
        None,
        "--repo",
        help="Optional specific repo name (e.g., vds-scripts, vds-skills).",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Apply safe auto-fixes for symlinks, missing llms.txt, and docs index links.",
    ),
    check_vi: bool = typer.Option(
        False,
        "--check-vi",
        help="Validate Vietnamese translations exist and are not stale.",
    ),
    check_diataxis: bool = typer.Option(
        False,
        "--check-diataxis",
        help="Validate all docs have valid diátaxis quadrant headers.",
    ),
    cross_repo: bool = typer.Option(
        False,
        "--cross-repo",
        help="Validate cross-repo links resolve to existing files.",
    ),
    check_orchestrators: bool = typer.Option(
        False,
        "--check-orchestrators",
        help="Warn if orchestrators lack corresponding documentation.",
    ),
    check_skills: bool = typer.Option(
        False,
        "--check-skills",
        help="Warn if skills lack QUALITY.md or references/.",
    ),
    check_ecosystem: bool = typer.Option(
        False,
        "--check-ecosystem",
        help="Warn if ECOSYSTEM-DOCS.md or ECOSYSTEM-CHANGELOG.md are missing or empty.",
    ),
) -> None:
    """Validate AGENTS/CLAUDE/llms/docs contracts across one or more repositories."""
    try:
        issues = validate_docs(
            repo_root,
            repo=repo,
            fix=fix,
            check_vi=check_vi,
            check_diataxis=check_diataxis,
            cross_repo=cross_repo,
            check_orchestrators=check_orchestrators,
            check_skills=check_skills,
            check_ecosystem=check_ecosystem,
        )
    except ValueError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from None

    if not issues:
        console.print("[green]✅ docs validate passed[/green]")
        return

    table = Table(title="Docs Validation Findings")
    table.add_column("Repo", style="cyan")
    table.add_column("Check", style="magenta")
    table.add_column("Status")
    table.add_column("Message")
    for issue in issues:
        status = "fixed" if issue.fixed else "error"
        table.add_row(issue.repo, issue.check, status, issue.message)
    console.print(table)

    unresolved = [issue for issue in issues if not issue.fixed]
    if unresolved:
        raise typer.Exit(1) from None

    console.print("[green]✅ docs validate completed with auto-fixes[/green]")


@docs_app.command("quality-score")
def docs_quality_score(
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root"),
    format: str = typer.Option("table", "--format"),
) -> None:
    """Score documentation quality across all docs."""
    from .docs_cmd import score_all_docs

    result = score_all_docs(repo_root)

    if format == "json":
        import json

        console.print(json.dumps(result, indent=2))
        return

    table = Table(title=f"Doc Quality Scores — {repo_root.name} ({result['count']} docs)")
    table.add_column("Doc", style="cyan")
    table.add_column("Length", style="magenta")
    table.add_column("Commands", style="green")
    table.add_column("Workflows", style="yellow")
    table.add_column("Links", style="blue")
    table.add_column("Total", style="bold")

    low_score_docs = []
    for doc, scores in sorted(result["docs"].items()):
        total = scores["total"]
        style = "red" if total < 0.5 else "green" if total >= 0.8 else "yellow"
        table.add_row(
            doc,
            str(scores["length"]),
            str(scores["commands"]),
            str(scores["workflows"]),
            str(scores["cross_links"]),
            f"[{style}]{total}[/{style}]",
        )
        if total < 0.5:
            low_score_docs.append(doc)

    console.print(table)
    console.print(f"\nAverage score: {result['average']}")

    if low_score_docs:
        console.print(f"\n[red]Warning: {len(low_score_docs)} docs score below 0.5[/red]")
        for doc in low_score_docs:
            console.print(f"  - {doc}")


@docs_app.command("freshness")
def docs_freshness(
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        help="Repository root or umbrella directory containing VDS repos.",
    ),
    repo: str = typer.Option(
        "vds-scripts",
        "--repo",
        help="Target repository for freshness checks (default: vds-scripts).",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Optional path to docs freshness config file.",
    ),
) -> None:
    """Check documentation freshness lag using git history."""
    try:
        repo_roots = discover_repo_roots(repo_root, repo)
    except ValueError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from None
    if len(repo_roots) != 1:
        console.print("[red]❌ docs freshness requires a single target repo[/red]")
        raise typer.Exit(1) from None

    target_repo = repo_roots[0]
    config_path = config if config is not None else target_repo / "docs" / ".freshness.yaml"
    try:
        issues = check_freshness(target_repo, config_path)
    except ValueError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from None

    if not issues:
        console.print("[green]✅ docs freshness passed[/green]")
        return

    table = Table(title="Docs Freshness Findings")
    table.add_column("Doc", style="cyan")
    table.add_column("Source", style="magenta")
    table.add_column("Lag (days)")
    table.add_column("Max (days)")
    table.add_column("Message")
    for issue in issues:
        table.add_row(
            issue.doc,
            issue.source,
            f"{issue.lag_days:.1f}",
            str(issue.max_lag_days),
            issue.message,
        )
    console.print(table)
    raise typer.Exit(1) from None


@docs_app.command("init-repo")
def docs_init_repo(
    repo_name: str = typer.Argument(..., help="Name for the new repo."),
    output_dir: Path = typer.Option(Path.cwd(), "--output-dir", help="Parent directory for the new repo."),
) -> None:
    """Scaffold doc surface for a new repo."""
    repo_path = output_dir / repo_name
    repo_path.mkdir(parents=True, exist_ok=False)

    # Create files
    (repo_path / "AGENTS.md").write_text(f"# {repo_name}", encoding="utf-8")
    (repo_path / "CLAUDE.md").symlink_to("AGENTS.md")

    for sub in [f"docs/agents/{q}" for q in ("how-to", "reference", "tutorials", "explanation")]:
        (repo_path / sub).mkdir(parents=True)

    (repo_path / "docs/agents/README.md").write_text("# Docs\n\nDocumentation directory.\n", encoding="utf-8")
    (repo_path / "llms.txt").write_text(f"# {repo_name}\n\n> Repository index.\n", encoding="utf-8")
    console.print(f"[green]✅[/green] Scaffolded repo: {repo_path}")


@docs_app.command("ecosystem-index")
def docs_ecosystem_index(
    output: Path = typer.Option(Path("ECOSYSTEM-DOCS.md"), "--output"),
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root"),
) -> None:
    """Generate ecosystem-wide doc index from all repos."""
    result = generate_ecosystem_index(repo_root, output)
    console.print(f"[green]OK[/green] Ecosystem index generated: {result['output']}")
    console.print(f"   Repos: {result['repos']} | Docs: {result['docs']}")


@docs_app.command("onboarding-funnel")
def docs_onboarding_funnel(
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", help="Repository root"),
    sessions_dir: Path = typer.Option(
        Path.home() / ".claude" / "projects",
        "--sessions-dir",
        help="Directory containing Claude session JSONL files",
    ),
    format: str = typer.Option("table", "--format", help="Output: table | json"),
    window_days: int = typer.Option(60, "--window-days", help="Look-back window in days"),
) -> None:
    """Show real consumption funnel from session scans (Diátaxis + dead-weight)."""
    from vds_cli.docs.consumption.funnel import aggregate_reads, dead_weight, funnel_summary
    from vds_cli.docs.consumption.scanner import scan_consumption

    reads = scan_consumption(repo_root, session_dir=sessions_dir)
    rows = aggregate_reads(reads)
    dead = dead_weight(reads, window_days)
    summary = funnel_summary(rows)

    if format == "json":
        import json

        out = {
            "repo": str(repo_root),
            "window_days": window_days,
            "total_docs": len(rows) + len(dead),
            "active_docs": len(rows),
            "dead_weight": len(dead),
            "stages": [{"stage": s.stage, "read_count": s.read_count, "unique_docs": s.unique_docs} for s in summary],
        }
        console.print(json.dumps(out, indent=2))
        return

    table = Table(title=f"Doc Funnel — {repo_root.name}")
    table.add_column("Stage", style="cyan")
    table.add_column("Reads", justify="right")
    table.add_column("Docs", justify="right")
    for s in summary:
        table.add_row(s.stage, str(s.read_count), str(s.unique_docs))
    console.print(table)
    if dead:
        console.print(f"[yellow]⚠️  {len(dead)} docs with zero reads in {window_days}d window[/yellow]")


@docs_app.command("freshness-heatmap")
def docs_freshness_heatmap(
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root"),
) -> None:
    """Generate doc freshness heatmap across repos."""
    repos = discover_repo_roots(repo_root, None)
    result = generate_freshness_heatmap(repos)
    table = Table(title="Docs Freshness Heatmap")
    table.add_column("Repo", style="cyan")
    table.add_column("Docs", justify="right")
    table.add_column("Avg Age (days)", justify="right")
    table.add_column("Oldest Doc", style="yellow")
    for repo_name, data in result["repos"].items():
        docs = data["docs"]
        avg_age = round(sum(d["age_days"] for d in docs) / len(docs), 1) if docs else 0.0
        oldest = max(docs, key=lambda d: d["age_days"], default={"path": "N/A", "age_days": 0})
        table.add_row(repo_name, str(len(docs)), str(avg_age), oldest["path"])
    console.print(table)


@docs_app.command("monthly-consumption")
def docs_monthly_consumption(
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root"),
    format: str = typer.Option("table", "--format"),
) -> None:
    """Show monthly doc consumption metrics."""
    result = generate_monthly_consumption_report(repo_root)
    if format == "json":
        import json

        console.print(json.dumps(result, indent=2))
        return
    table = Table(title=f"Monthly Consumption — {result['repo']}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Month", result["month"])
    table.add_row("Total Reads", str(result.get("total_reads", 0)))
    table.add_row("Unique Docs", str(result.get("unique_docs", 0)))
    table.add_row("Sessions", str(result.get("sessions", 0)))
    console.print(table)


@docs_app.command("confluence-sync")
def docs_confluence_sync(
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        help="Repository root containing docs/.confluence.yaml.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned changes without applying.",
    ),
    page: str | None = typer.Option(
        None,
        "--page",
        help="Sync only the page with this title.",
    ),
    create_missing: bool = typer.Option(
        False,
        "--create-missing",
        help="Create Confluence pages that don't exist yet.",
    ),
    validate_links: bool = typer.Option(
        False,
        "--validate-links",
        help="Validate Bitbucket link health before syncing.",
    ),
) -> None:
    """Sync documentation hub to Confluence pages."""
    try:
        results = run_confluence_sync(
            repo_root,
            dry_run=dry_run,
            page_title=page,
            create_missing=create_missing,
            validate_links=validate_links,
        )
    except ValueError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]❌ Confluence sync failed: {exc}[/red]")
        raise typer.Exit(1) from exc

    if dry_run:
        console.print("[cyan]Dry run complete — no changes made.[/cyan]")
    else:
        synced = [r for r in results if r.get("created") or not r.get("dry_run")]
        console.print(f"[green]✅ Synced {len(synced)} page(s)[/green]")


@docs_app.command("watch-agents")
def docs_watch_agents(
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        help="Repository root (or any child directory within the repository).",
    ),
    reconcile_interval_seconds: int = typer.Option(
        300,
        "--reconcile-interval-seconds",
        min=30,
        help="Periodic full reconciliation interval in seconds.",
    ),
    debounce_ms: int = typer.Option(
        500,
        "--debounce-ms",
        min=100,
        help="Polling debounce interval in milliseconds.",
    ),
    watch_backend: str = typer.Option(
        "auto",
        "--watch-backend",
        help="Change detection backend: auto, watchfiles, polling.",
    ),
    central_backend: str = typer.Option(
        "local",
        "--central-backend",
        help="Central state backend: local, http.",
    ),
    central_contract: str = typer.Option(
        "generic",
        "--central-contract",
        help="HTTP contract profile when --central-backend=http: generic, vds-ai-memory, confluence-property.",
    ),
    central_state_url: str | None = typer.Option(
        None,
        "--central-state-url",
        help=(
            "Central state URL. Required for --central-contract=generic. "
            "For vds-ai-memory this can be the API base URL; for confluence-property this can be Confluence base URL."
        ),
    ),
    central_timeout_seconds: int = typer.Option(
        10,
        "--central-timeout-seconds",
        min=1,
        help="Central state HTTP timeout in seconds.",
    ),
    central_auth_token: str | None = typer.Option(
        None,
        "--central-auth-token",
        envvar="VDS_SYNC_AUTH_TOKEN",
        help="Auth token override for HTTP backends (or use VDS_SYNC_AUTH_TOKEN).",
    ),
    central_memory_id: str | None = typer.Option(
        None,
        "--central-memory-id",
        envvar="VDS_SYNC_MEMORY_ID",
        help="VDS AI Memory record ID when --central-contract=vds-ai-memory.",
    ),
    central_user_id: str = typer.Option(
        "vds-sync-agent",
        "--central-user-id",
        envvar="VDS_SYNC_USER_ID",
        help="User ID for vds-ai-memory create/update payloads.",
    ),
    central_session_id: str = typer.Option(
        "vds-sync-session",
        "--central-session-id",
        envvar="VDS_SYNC_SESSION_ID",
        help="Session ID for vds-ai-memory create/update payloads.",
    ),
    central_confluence_server: str = typer.Option(
        "internal",
        "--central-confluence-server",
        envvar="CONFLUENCE_DEFAULT_SERVER",
        help="Confluence server selector for confluence-property contract: internal or external.",
    ),
    central_confluence_page_id: str | None = typer.Option(
        None,
        "--central-confluence-page-id",
        envvar="VDS_SYNC_CONFLUENCE_PAGE_ID",
        help="Confluence page ID for confluence-property contract.",
    ),
    central_confluence_property_key: str = typer.Option(
        "vds_sync_instructions",
        "--central-confluence-property-key",
        envvar="VDS_SYNC_CONFLUENCE_PROPERTY_KEY",
        help="Confluence content-property key for confluence-property contract.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run reconciliation without writing target files or ledger.",
    ),
    conflict_dir: Path | None = typer.Option(
        None,
        "--conflict-dir",
        help="Directory where unresolved conflict artifacts are written.",
    ),
    log_json: bool = typer.Option(
        True,
        "--log-json/--no-log-json",
        help="Emit JSON log events to stdout.",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="Run startup reconciliation once and exit.",
    ),
) -> None:
    """Watch and reconcile AGENTS.md plus legacy mirrored instruction files."""
    try:
        run_watch_agents(
            repo_root=repo_root,
            reconcile_interval_seconds=reconcile_interval_seconds,
            debounce_ms=debounce_ms,
            watch_backend=watch_backend,
            central_backend=central_backend,
            central_contract=central_contract,
            central_state_url=central_state_url,
            central_timeout_seconds=central_timeout_seconds,
            central_auth_token=central_auth_token,
            central_memory_id=central_memory_id,
            central_user_id=central_user_id,
            central_session_id=central_session_id,
            central_confluence_server=central_confluence_server,
            central_confluence_page_id=central_confluence_page_id,
            central_confluence_property_key=central_confluence_property_key,
            dry_run=dry_run,
            conflict_dir=conflict_dir,
            log_json=log_json,
            once=once,
        )
    except SyncError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from None
    except KeyboardInterrupt:
        console.print("[yellow]watch-agents interrupted[/yellow]")
        raise typer.Exit(130) from None


@docs_app.command("watch-agents-install")
def docs_watch_agents_install(
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        help="Repository root to watch.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing LaunchAgent plist.",
    ),
) -> None:
    """Install macOS LaunchAgent for automatic watch-agents on login."""
    try:
        from .sync_service import install as svc_install

        paths = svc_install(repo_root=repo_root, force=force)
        console.print(f"[green]✅ LaunchAgent installed:[/green] {paths.plist}")
        console.print(f"   stdout log: {paths.stdout_log}")
        console.print(f"   stderr log: {paths.stderr_log}")
        console.print(f"   repo root:  {paths.repo_root}")
        console.print("")
        console.print("Service will start automatically on login and restart on failure.")
    except ServiceError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from None


@docs_app.command("watch-agents-uninstall")
def docs_watch_agents_uninstall() -> None:
    """Uninstall the macOS LaunchAgent for watch-agents."""
    try:
        from .sync_service import uninstall as svc_uninstall

        plist_path = svc_uninstall()
        console.print(f"[green]✅ LaunchAgent removed:[/green] {plist_path}")
    except ServiceError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from None


@docs_app.command("watch-agents-status")
def docs_watch_agents_status() -> None:
    """Show macOS LaunchAgent status for watch-agents."""
    try:
        from .sync_service import status as svc_status

        st = svc_status()
        if not st.installed:
            console.print(f"[yellow]⚠ Not installed[/yellow] (expected at {st.plist_path})")
            console.print("Run: vds-cli docs watch-agents-install")
            return
        if st.running:
            console.print(f"[green]● Running[/green]  pid={st.pid}")
        else:
            msg = "[red]○ Stopped[/red]"
            if st.exit_code is not None:
                msg += f"  last exit code={st.exit_code}"
            console.print(msg)
        console.print(f"  plist: {st.plist_path}")
    except ServiceError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from None


@app.command()
def status() -> None:
    """System status and health checks."""
    settings = load_environment()
    console.print("[cyan]📊 VDS Platform Status[/cyan]\n")

    # Check orchestrators
    table = Table(title="Orchestrator Status")
    table.add_column("Orchestrator", style="cyan")
    table.add_column("Status", style="magenta")

    for service in sorted(ORCHESTRATORS):
        _, status = validate_orchestrator(service, SCRIPT_DIR)
        table.add_row(service, status)

    console.print(table)

    # Check environment
    env_table = Table(title="Environment Status")
    env_table.add_column("Variable", style="cyan")
    env_table.add_column("Status", style="magenta")

    for label, ok in _env_check_rows(settings):
        env_table.add_row(label, "✅ Set" if ok else "❌ Missing")

    console.print("\n")
    console.print(env_table)


def _doctor_check_env_files(
    checks: Table, primary_env: Path
) -> tuple[list[str], list[str]]:
    """Check shared env file presence and add rows to the checks table.

    Returns (issues, recommended) accumulators for missing primary env file.
    """
    issues: list[str] = []
    recommended: list[str] = []
    for env_path in DEFAULT_ENV_PATHS:
        exists = env_path.exists()
        if exists:
            checks.add_row(f"Env file: {env_path}", "✅ Found")
        elif env_path == primary_env:
            checks.add_row(f"Env file: {env_path}", "❌ Missing")
        else:
            checks.add_row(f"Env file: {env_path}", "ℹ️ Optional fallback missing")
    if not primary_env.exists():
        issues.append(f"Primary env file is missing: {primary_env}")
        recommended.append(f"Create {primary_env} and add required credentials.")
    return issues, recommended


def _doctor_check_auth(checks: Table, settings) -> list[str]:
    """Check VDS/Bitbucket/Confluence auth rows; return collected issues."""
    issues: list[str] = []
    for label, ok in _env_check_rows(settings):
        checks.add_row(f"Auth: {label}", "✅ OK" if ok else "❌ Missing")
        if not ok:
            issues.append(f"Missing auth requirement: {label}")
    return issues


def _doctor_check_git_helper(checks: Table) -> tuple[list[str], list[str]]:
    """Check git credential helper status; return (issues, recommended)."""
    issues: list[str] = []
    recommended: list[str] = []
    helper_status, helper_hint = _env_git_helper.status()
    checks.add_row(
        "Git credential helper",
        "✅ Installed" if helper_status == "installed" else f"❌ {helper_status.capitalize()}",
    )
    if helper_status != "installed":
        issues.append(f"Git credential helper: {helper_status}")
        if helper_hint:
            recommended.append(helper_hint)
    return issues, recommended


def _doctor_check_routing(checks: Table) -> tuple[list[str], list[str]]:
    """Check each orchestrator/router service; return (issues, recommended)."""
    issues: list[str] = []
    recommended: list[str] = []
    for service in sorted(ORCHESTRATORS):
        ok, status_msg = validate_orchestrator(service, SCRIPT_DIR)
        checks.add_row(f"Router: {service}", status_msg)
        if not ok:
            issues.append(f"{service}: {status_msg}")
            if "Broken target module" in status_msg:
                recommended.append(
                    f"Repair source module for '{service}' or align pyproject script target, then run `uv sync --project {ORCHESTRATORS[service]['path']} --reinstall`."
                )
    return issues, recommended


def _doctor_check_embedding(checks: Table) -> tuple[list[str], list[str]]:
    """Check embedding provider readiness; return (issues, recommended)."""
    import os

    issues: list[str] = []
    recommended: list[str] = []
    verify_dim = os.environ.get("VDS_AGENT_CORE_EMBED__VERIFY_DIM_AGAINST_QDRANT", "true")
    provider = os.environ.get("VDS_AGENT_CORE_EMBED__PROVIDER", "ollama")

    # FR-228.1: WARN when dimension verification is disabled
    if verify_dim.lower() in ("false", "0", "no", "off"):
        status = "WARN — embedding dimension verification disabled"
        issues.append("embedding dim verification disabled (NFR-225.11)")
        recommended.append(
            "Set VDS_AGENT_CORE_EMBED__VERIFY_DIM_AGAINST_QDRANT=true in ~/.vds/.env "
            "for production safety."
        )
    else:
        status = "OK (dimension verification enabled)"

    checks.add_row("Embedding: dimension verification", status)

    # FR-228.3: Ollama reachability probe (2s timeout)
    if provider == "ollama":
        import httpx

        base_url = os.environ.get(
            "VDS_AGENT_CORE_EMBED__OLLAMA_BASE_URL",
            os.environ.get("VDS_AGENT_CORE_EMBED__BASE_URL", "http://localhost:11434"),
        )
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{base_url}/api/tags")
                if resp.is_success:
                    checks.add_row("Embedding: Ollama reachability", "OK (reachable)")
                else:
                    checks.add_row(
                        "Embedding: Ollama reachability",
                        f"WARN — HTTP {resp.status_code}",
                    )
                    issues.append(f"Ollama returned HTTP {resp.status_code}")
        except Exception:
            checks.add_row("Embedding: Ollama reachability", "WARN — unreachable")
            issues.append(f"Ollama unreachable at {base_url}")
            recommended.append(
                "Start Ollama or set VDS_AGENT_CORE_EMBED__PROVIDER=openai "
                "for cloud failover."
            )
    else:
        checks.add_row("Embedding: provider", f"OK ({provider} — cloud, no local probe)")

    return issues, recommended


def _doctor_summarize(issues: list[str], recommended: list[str], primary_env: Path) -> None:
    """Render issues + deduplicated recommended actions and exit non-zero."""
    console.print("\n[red]Doctor detected issues:[/red]")
    for issue in issues:
        console.print(f"  - {issue}")

    if any("VDS credentials" in issue for issue in issues):
        recommended.append(f"Set VDS_USERNAME and VDS_PASSWORD in {primary_env}.")
    if any("Bitbucket auth" in issue for issue in issues):
        recommended.append(f"Set BITBUCKET_ACCESS_TOKEN or BITBUCKET_TOKEN in {primary_env}.")
    if any("Confluence auth" in issue for issue in issues):
        recommended.append(f"Set INTERNAL_CONFLUENCE_TOKEN or EXTERNAL_CONFLUENCE_TOKEN in {primary_env}.")

    if recommended:
        deduped: list[str] = []
        for item in recommended:
            if item not in deduped:
                deduped.append(item)
        console.print("\n[yellow]Recommended actions:[/yellow]")
        for idx, item in enumerate(deduped, start=1):
            console.print(f"  {idx}. {item}")
    raise typer.Exit(1) from None


@app.command()
def doctor() -> None:
    """Diagnose routing and environment readiness with recommended actions."""
    settings = load_environment()

    checks = Table(title="Doctor Checks")
    checks.add_column("Check", style="cyan")
    checks.add_column("Result", style="magenta")

    primary_env = get_shared_env_path()
    issues: list[str] = []
    recommended: list[str] = []

    env_issues, env_recommended = _doctor_check_env_files(checks, primary_env)
    issues.extend(env_issues)
    recommended.extend(env_recommended)

    issues.extend(_doctor_check_auth(checks, settings))

    helper_issues, helper_recommended = _doctor_check_git_helper(checks)
    issues.extend(helper_issues)
    recommended.extend(helper_recommended)

    routing_issues, routing_recommended = _doctor_check_routing(checks)
    issues.extend(routing_issues)
    recommended.extend(routing_recommended)

    embedding_issues, embedding_recommended = _doctor_check_embedding(checks)
    issues.extend(embedding_issues)
    recommended.extend(embedding_recommended)

    console.print(checks)

    if issues:
        _doctor_summarize(issues, recommended, primary_env)

    console.print("\n[green]Doctor checks passed.[/green]")


@app.command()
def regenerate_manifest(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the generated repo-manifest.yaml to stdout instead of writing files.",
    ),
) -> None:
    """Regenerate vds-scripts/repo-manifest.yaml from Bitbucket projects.

    Uses the existing Bitbucket settings and client to discover repositories
    for core projects (LEP, INSURANCE, SAVING, EKYC) and overwrites the
    manifest file in vds-scripts/. A backup copy is written under
    vds-scripts/reports/git_runs/repo-manifest.generated.yaml.
    """
    load_environment()
    try:
        manifest_mod = _load_manifest_module()
    except RuntimeError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        console.print(
            "[yellow]Migration path:[/yellow] "
            "`./scripts/worktree_uv.sh run --project audit_orchestrator "
            "vds-audit export-git-manifest --output <path> --state-dsn <dsn>`"
        )
        raise typer.Exit(2) from None
    exit_code = manifest_mod.generate_manifest(scripts_root=SCRIPT_DIR, dry_run=dry_run)
    if exit_code != 0:
        raise typer.Exit(exit_code) from None


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__

    console.print(f"[cyan]VDS Platform CLI v{__version__}[/cyan]")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
