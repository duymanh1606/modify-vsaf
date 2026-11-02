"""Bitbucket CLI using atlassian-python-api (consistent with VDS orchestrators)."""

from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

import structlog
import typer
from vds_cli_common.context import CLIContext
from vds_cli_common.output import OutputManager
from vds_cli_common.paths import get_vds_cache_root
from vds_platform_core.logging import configure_structlog

from .client import BitbucketClient
from .config import BitbucketSettings, SettingsError, load_settings
from .errors import (
    NotFoundError,
    VDSClientError,
)
from .repo_ops import archive_repo, build_clone_url, clone_repo, parse_repo_identifier

_REPORT_DIR = get_vds_cache_root() / "vds-bitbucket-reports"

app = typer.Typer(
    name="vds-bitbucket-cli",
    help="Bitbucket operations orchestrator (atlassian-python-api)",
    no_args_is_help=True,
)


def _version_callback(value: bool | None) -> bool | None:
    """Print CLI version when --version is provided."""
    if value:
        try:
            ver = metadata.version("vds-bitbucket-orchestrator")
        except metadata.PackageNotFoundError:
            ver = "unknown"
        typer.echo(f"vds-bitbucket-orchestrator {ver}")
        raise typer.Exit() from None
    return value


@app.callback()
def main(
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show CLI version and exit",
    ),
    _report_dir: Path | None = typer.Option(
        None, "--report-dir", help="Directory for run reports (default: <vds-scripts>/reports/bitbucket_runs)"
    ),
    _markdown: bool = typer.Option(
        True, "--markdown/--no-markdown", help="Emit Markdown summaries alongside JSON reports"
    ),
    _reports: bool = typer.Option(True, "--_reports/--no-reports", help="Write report files to report-dir"),
    json_only: bool = typer.Option(False, "--json-only", "--json", help="Emit JSON to stdout only"),
    structured_logs: bool = typer.Option(
        False, "--structured-logs/--no-structured-logs", help="Emit structured JSON logs to stderr"
    ),
    _quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
    _verbose: bool = typer.Option(False, "--verbose", "-v", help="Structured logs"),
    _no_color: bool = typer.Option(False, "--no-color", help="Disable colour"),
) -> None:
    """Global options for Bitbucket CLI."""
    # Configure structlog based on options
    if structured_logs or json_only:
        configure_structlog(
            json_logs=structured_logs, quiet=json_only and not structured_logs, cache_logger=structured_logs
        )


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def _build_client(settings: BitbucketSettings) -> BitbucketClient:
    """Build and return a configured BitbucketClient."""
    return BitbucketClient(settings)


def _get_client() -> BitbucketClient:
    """Load settings and create client."""
    settings = load_settings(strict=True)
    return _build_client(settings)


def _handle_error(exc: VDSClientError, out: OutputManager, log: structlog.BoundLogger) -> None:
    """Handle Bitbucket client errors with appropriate output."""
    context = getattr(exc, "context", {})
    log.error("bitbucket_error", message=str(exc), context=context)
    out.output_error(str(exc))


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------


@app.command("fork")
def fork(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: create, list"),
    project_key: str = typer.Argument(..., help="Source project key"),
    repository_slug: str = typer.Argument(..., help="Source repository slug"),
    new_project_key: str | None = typer.Option(
        None, "--new-project", help="Target project key (for create, if forking to new project)"
    ),
    new_repository_slug: str | None = typer.Option(None, "--new-repo", help="Target repository slug (for create)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation (for create)"),
) -> None:
    """Fork repository operations."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            if action == "create":
                if not yes:
                    raise typer.BadParameter("Refusing to fork repository without --yes")
                result = client.fork_repository(project_key, repository_slug, new_project_key, new_repository_slug)

                output_path = report_dir / f"{project_key}_{repository_slug}_forked.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with output_path.open("w") as f:
                    f.write("# Repository Forked\n\n")
                    f.write(f"- **Source**: {project_key}/{repository_slug}\n")
                    if new_project_key:
                        f.write(f"- **Target Project**: {new_project_key}\n")
                    if new_repository_slug:
                        f.write(f"- **Target Repository**: {new_repository_slug}\n")
                    f.write(f"- **Forked Repository**: {result.get('slug', 'N/A')}\n")

                log.info(
                    "fork_reported",
                    path=str(output_path),
                    project_key=project_key,
                    repository=repository_slug,
                )

                payload = {
                    "status": "success",
                    "source_project": project_key,
                    "source_repository": repository_slug,
                    "forked_repository": result,
                }
                out.output_json(payload)

            elif action == "list":
                result = client.get_forked_repositories(project_key, repository_slug)

                output_path = report_dir / f"{project_key}_{repository_slug}_forks.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with output_path.open("w") as f:
                    f.write(f"# Forks of {project_key}/{repository_slug}\n\n")
                    f.write(f"Found {len(result)} forks:\n\n")
                    for fork in result:
                        name = fork.get("name", "N/A")
                        slug = fork.get("slug", "N/A")
                        f.write(f"- **{slug}**: {name}\n")

                log.info(
                    "forks_reported",
                    path=str(output_path),
                    project_key=project_key,
                    repository=repository_slug,
                    count=len(result),
                )

                payload = {
                    "source_project": project_key,
                    "source_repository": repository_slug,
                    "forks": result,
                    "count": len(result),
                }
                out.output_json(payload)
            else:
                raise typer.BadParameter(f"Unknown action: {action}")

    except (VDSClientError, typer.BadParameter) as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def projects(
    ctx: typer.Context,
    limit: int = typer.Option(25, "--limit", help="Maximum number of projects to list"),
) -> None:
    """List all Bitbucket projects."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            projects = client.list_projects(limit=limit)

            output_path = report_dir / "projects.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write("# Bitbucket Projects\n\n")
                f.write(f"Found {len(projects)} projects:\n\n")
                for project in projects:
                    key = project.get("key", "N/A")
                    name = project.get("name", "N/A")
                    f.write(f"- **{key}**: {name}\n")

            log.info("projects_reported", path=str(output_path), count=len(projects))

            out.output_json({"projects": projects})

    except (VDSClientError, SettingsError, ValueError) as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def create_project(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Project key"),
    name: str = typer.Argument(..., help="Project name"),
    description: str = typer.Option(
        "Project created via VDS orchestrator", "--description", help="Project description"
    ),
) -> None:
    """Create a new Bitbucket project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            result = client.create_project(key, name, description)

            output_path = report_dir / "project_created.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write("# Project Created\n\n")
                f.write(f"- **Key**: {result.get('key', key)}\n")
                f.write(f"- **Name**: {result.get('name', name)}\n")
                f.write(f"- **Description**: {result.get('description', description)}\n")

            log.info("project_created_reported", path=str(output_path), key=key)

            out.output_json(result)

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def repositories(
    ctx: typer.Context,
    project_key: str = typer.Argument(..., help="Project key"),
    limit: int = typer.Option(25, "--limit", help="Maximum number of repositories to list"),
) -> None:
    """List repositories in a project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            repos = client.list_repositories(project_key, limit=limit)

            output_path = report_dir / f"{project_key}_repositories.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write(f"# {project_key} Repositories\n\n")
                f.write(f"Found {len(repos)} repositories:\n\n")
                for repo in repos:
                    name = repo.get("name", "N/A")
                    slug = repo.get("slug", "N/A")
                    f.write(f"- **{slug}**: {name}\n")

            log.info("repositories_reported", path=str(output_path), project_key=project_key, count=len(repos))

            out.output_json({"repositories": repos})

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def pull_requests(
    ctx: typer.Context,
    project_key: str = typer.Argument(..., help="Project key"),
    repository_slug: str = typer.Argument(..., help="Repository slug"),
    state: str = typer.Option("OPEN", "--state", help="PR state (OPEN, MERGED, DECLINED)"),
    order: str = typer.Option("newest", "--order", help="Sort order (newest, oldest)"),
    limit: int = typer.Option(100, "--limit", help="Maximum number of PRs to list"),
    start: int = typer.Option(0, "--start", help="Start index for pagination"),
) -> None:
    """List pull requests for a repository."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            prs = client.list_pull_requests(
                project_key, repository_slug, state=state, order=order, limit=limit, start=start
            )

            output_path = report_dir / f"{project_key}_{repository_slug}_pull_requests.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write(f"# Pull Requests - {project_key}/{repository_slug}\n\n")
                f.write(f"Found {len(prs)} {state.lower()} pull requests:\n\n")
                for pr in prs:
                    title = pr.get("title", "N/A")
                    pr_id = pr.get("id", "N/A")
                    author = pr.get("author", {}).get("displayName", "N/A")
                    f.write(f"- **#{pr_id}**: {title} (by {author})\n")

            log.info(
                "pull_requests_reported",
                path=str(output_path),
                project_key=project_key,
                repository=repository_slug,
                count=len(prs),
            )

            out.output_json({"pull_requests": prs})

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def pipelines(
    ctx: typer.Context,
    workspace: str = typer.Argument(..., help="Workspace (Bitbucket Cloud only)"),
    repository: str = typer.Argument(..., help="Repository name"),
    limit: int = typer.Option(10, "--limit", help="Maximum number of pipelines to list"),
) -> None:
    """List pipelines (Bitbucket Cloud only)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error("cloud_mode_required", message="Pipelines are only available in Bitbucket Cloud mode")
            out.output_error("Pipelines are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:
            pipelines = client.list_pipelines(workspace, repository, limit=limit)

            output_path = report_dir / f"{workspace}_{repository}_pipelines.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write(f"# Pipelines - {workspace}/{repository}\n\n")
                f.write(f"Found {len(pipelines)} pipelines:\n\n")
                for pipeline in pipelines:
                    pipeline_uuid = pipeline.get("uuid", "N/A")
                    pipeline_state = pipeline.get("state", {}).get("name", "N/A")
                    f.write(f"- **{pipeline_uuid}**: {pipeline_state}\n")

            log.info(
                "pipelines_reported",
                path=str(output_path),
                workspace=workspace,
                repository=repository,
                count=len(pipelines),
            )

            out.output_json({"pipelines": pipelines})

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def groups(
    ctx: typer.Context,
    filter: str | None = typer.Option(None, "--filter", help="Filter string to search for specific groups"),
    limit: int = typer.Option(50, "--limit", help="Maximum number of groups to list"),
) -> None:
    """List all available Bitbucket groups."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            groups = client.list_groups(group_filter=filter, limit=limit)

            output_path = report_dir / "groups.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write("# Bitbucket Groups\n\n")
                f.write(f"Found {len(groups)} groups:\n\n")
                for group in groups:
                    f.write(f"- **{group}**\n")

            log.info("groups_reported", path=str(output_path), count=len(groups))

            out.output_json({"groups": groups})

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def project_users(
    ctx: typer.Context,
    project_key: str = typer.Argument(..., help="Project key"),
    filter: str | None = typer.Option(None, "--filter", help="Filter string to search for specific users"),
    limit: int = typer.Option(25, "--limit", help="Maximum number of users to list"),
) -> None:
    """List users with permissions for a project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            users = client.list_project_users(project_key, filter_str=filter, limit=limit)

            output_path = report_dir / f"{project_key}_users.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write(f"# {project_key} Project Users\n\n")
                f.write(f"Found {len(users)} users:\n\n")
                for user in users:
                    name = user.get("name", "N/A")
                    email = user.get("emailAddress", "N/A")
                    permission = user.get("permission", "N/A")
                    f.write(f"- **{name}** ({email}) - {permission}\n")

            log.info("project_users_reported", path=str(output_path), project_key=project_key, count=len(users))

            out.output_json({"users": users})

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def project_groups(
    ctx: typer.Context,
    project_key: str = typer.Argument(..., help="Project key"),
    filter: str | None = typer.Option(None, "--filter", help="Filter string to search for specific groups"),
    limit: int = typer.Option(25, "--limit", help="Maximum number of groups to list"),
) -> None:
    """List groups with permissions for a project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            groups = client.list_project_groups(project_key, filter_str=filter, limit=limit)

            output_path = report_dir / f"{project_key}_groups.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write(f"# {project_key} Project Groups\n\n")
                f.write(f"Found {len(groups)} groups:\n\n")
                for group in groups:
                    f.write(f"- **{group}**\n")

            log.info("project_groups_reported", path=str(output_path), project_key=project_key, count=len(groups))

            out.output_json({"groups": groups})

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def grant_group_repo(
    ctx: typer.Context,
    project_key: str = typer.Argument(..., help="Project key"),
    repository_slug: str = typer.Argument(..., help="Repository slug"),
    group_name: str = typer.Argument(..., help="Group name"),
    permission: str = typer.Argument(..., help="Permission level (read, write, admin)"),
) -> None:
    """Grant group permissions to a repository."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            result = client.grant_group_repository_permissions(project_key, repository_slug, group_name, permission)

            output_path = report_dir / f"{project_key}_{repository_slug}_group_granted.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w") as f:
                f.write("# Group Permission Granted\n\n")
                f.write(f"- **Project**: {project_key}\n")
                f.write(f"- **Repository**: {repository_slug}\n")
                f.write(f"- **Group**: {group_name}\n")
                f.write(f"- **Permission**: {permission}\n")
                f.write("- **Result**: Success\n")

            log.info(
                "group_permission_granted",
                path=str(output_path),
                project_key=project_key,
                repository=repository_slug,
                group=group_name,
                permission=permission,
            )

            out.output_json(result)

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def branch_permissions(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, get, set, delete"),
    project_key: str = typer.Argument(..., help="Project key"),
    permission_id: int | None = typer.Option(None, "--permission-id", help="Permission ID (for get/delete)"),
    repository_slug: str | None = typer.Option(None, "--repo", help="Repository slug"),
    matcher_type: str | None = typer.Option(None, "--matcher-type", help="Matcher type (for set)"),
    matcher_value: str | None = typer.Option(None, "--matcher-value", help="Matcher value (for set)"),
    permission_type: str | None = typer.Option(None, "--permission-type", help="Permission type (for set)"),
    start: int = typer.Option(0, "--start", help="Start index for list pagination"),
    limit: int = typer.Option(25, "--limit", help="Max items for list pagination"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Branch permissions management."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            if action == "list":
                if not repository_slug:
                    raise typer.BadParameter("--repo required for list")
                result = client.list_branch_permissions(
                    project_key,
                    repository_slug=repository_slug,
                    start=start,
                    limit=limit,
                )
            elif action == "get":
                if not permission_id:
                    raise typer.BadParameter("--permission-id required for get")
                result = client.get_branch_permission(project_key, permission_id, repository_slug=repository_slug)
            elif action == "set":
                if not yes:
                    raise typer.BadParameter("Refusing to set permissions without --yes")
                if not matcher_type or not matcher_value or not permission_type:
                    raise typer.BadParameter("--matcher-type, --matcher-value, and --permission-type required for set")
                result = client.set_branches_permissions(
                    project_key,
                    matcher_type=matcher_type,
                    matcher_value=matcher_value,
                    permission_type=permission_type,
                    repository_slug=repository_slug,
                )
            elif action == "delete":
                if not yes:
                    raise typer.BadParameter("Refusing to delete without --yes")
                if not permission_id:
                    raise typer.BadParameter("--permission-id required for delete")
                client.delete_branch_permission(project_key, permission_id, repository_slug=repository_slug)
                result = {"deleted": permission_id}
            else:
                raise typer.BadParameter(f"Unknown action: {action}")

            output_path = report_dir / f"{project_key}_branch_permissions_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Branch Permissions - {action}\n\n")
                f.write(f"- **Project**: {project_key}\n")
                if repository_slug:
                    f.write(f"- **Repository**: {repository_slug}\n")
                f.write(f"- **Action**: {action}\n")
            log.info("branch_permissions_reported", path=str(output_path), action=action)

            if action == "list":
                out.output_json({"branch_permissions": result})
            else:
                out.output_json(result)

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def conditions(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    project_key: str = typer.Argument(..., help="Project key"),
    repository_slug: str | None = typer.Option(None, "--repo", help="Repository slug (for repo conditions)"),
    condition_id: int | None = typer.Option(None, "--condition-id", help="Condition ID (for get/update/delete)"),
    condition_file: Path | None = typer.Option(
        None, "--condition-file", help="JSON file with condition data (for create/update)"
    ),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Conditions-Reviewers management."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        import json

        load_settings(strict=True)
        with _get_client() as client:
            if action == "list":
                if repository_slug:
                    result = client.get_repo_conditions(project_key, repository_slug)
                else:
                    result = client.get_project_conditions(project_key)
            elif action == "get":
                if not condition_id:
                    raise typer.BadParameter("--condition-id required for get")
                if repository_slug:
                    result = client.get_repo_condition(project_key, repository_slug, condition_id)
                else:
                    result = client.get_project_condition(project_key, condition_id)
            elif action == "create":
                if not yes:
                    raise typer.BadParameter("Refusing to create without --yes")
                if not condition_file:
                    raise typer.BadParameter("--condition-file required for create")
                with condition_file.open() as f:
                    condition_data = json.load(f)
                if repository_slug:
                    result = client.create_repo_condition(project_key, repository_slug, condition_data)
                else:
                    result = client.create_project_condition(project_key, condition_data)
            elif action == "update":
                if not yes:
                    raise typer.BadParameter("Refusing to update without --yes")
                if not condition_id or not condition_file:
                    raise typer.BadParameter("--condition-id and --condition-file required for update")
                with condition_file.open() as f:
                    condition_data = json.load(f)
                if repository_slug:
                    result = client.update_repo_condition(project_key, repository_slug, condition_data, condition_id)
                else:
                    result = client.update_project_condition(project_key, condition_data, condition_id)
            elif action == "delete":
                if not yes:
                    raise typer.BadParameter("Refusing to delete without --yes")
                if not condition_id:
                    raise typer.BadParameter("--condition-id required for delete")
                if repository_slug:
                    client.delete_repo_condition(project_key, repository_slug, condition_id)
                else:
                    client.delete_project_condition(project_key, condition_id)
                result = {"deleted": condition_id}
            else:
                raise typer.BadParameter(f"Unknown action: {action}")

            output_path = report_dir / f"{project_key}_conditions_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Conditions - {action}\n\n")
                f.write(f"- **Project**: {project_key}\n")
                if repository_slug:
                    f.write(f"- **Repository**: {repository_slug}\n")
                f.write(f"- **Action**: {action}\n")
            log.info("conditions_reported", path=str(output_path), action=action)

            out.output_json(result)

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def code(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: file, commits, diff, changelog"),
    project_key: str = typer.Argument(..., help="Project key"),
    repository_slug: str = typer.Argument(..., help="Repository slug"),
    filename: str | None = typer.Option(None, "--file", help="File path (for file/diff)"),
    at: str | None = typer.Option(None, "--at", help="Revision/ref (for file)"),
    hash_oldest: str | None = typer.Option(
        None, "--hash-oldest", help="Oldest commit hash (for commits/diff/changelog)"
    ),
    hash_newest: str | None = typer.Option(
        None, "--hash-newest", help="Newest commit hash (for commits/diff/changelog)"
    ),
    ref_from: str | None = typer.Option(None, "--ref-from", help="From ref (for changelog)"),
    ref_to: str | None = typer.Option(None, "--ref-to", help="To ref (for changelog)"),
    limit: int = typer.Option(100, "--limit", help="Maximum number of results"),
) -> None:
    """Code/file content operations."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            if action == "file":
                if not filename:
                    raise typer.BadParameter("--file required for file action")
                result = client.get_content_of_file(project_key, repository_slug, filename, at=at)
                output_path = report_dir / f"{project_key}_{repository_slug}_{filename.replace('/', '_')}.txt"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    f.write(result)
                log.info("file_content_reported", path=str(output_path))
                out.output_json({"content": result, "path": str(output_path)})
                return
            elif action == "commits":
                result = client.get_commits(project_key, repository_slug, hash_oldest, hash_newest, limit=limit)
            elif action == "diff":
                if not filename or not hash_oldest or not hash_newest:
                    raise typer.BadParameter("--file, --hash-oldest, and --hash-newest required for diff")
                result = client.get_diff(project_key, repository_slug, filename, hash_oldest, hash_newest)
            elif action == "changelog":
                if not ref_from or not ref_to:
                    raise typer.BadParameter("--ref-from and --ref-to required for changelog")
                result = client.get_changelog(project_key, repository_slug, ref_from, ref_to, limit=limit)
            else:
                raise typer.BadParameter(f"Unknown action: {action}")

            output_path = report_dir / f"{project_key}_{repository_slug}_code_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Code Operations - {action}\n\n")
                f.write(f"- **Project**: {project_key}\n")
                f.write(f"- **Repository**: {repository_slug}\n")
                f.write(f"- **Action**: {action}\n")
            log.info("code_operation_reported", path=str(output_path), action=action)
            out.output_json(result)

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def webhooks(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    project_key: str = typer.Argument(..., help="Project key"),
    repository_slug: str = typer.Argument(..., help="Repository slug"),
    webhook_id: int | None = typer.Option(None, "--webhook-id", help="Webhook ID (get/update/delete)"),
    name: str | None = typer.Option(None, "--name", help="Webhook name (create/update)"),
    url: str | None = typer.Option(None, "--url", help="Webhook URL (create/update)"),
    events: list[str] = typer.Option(
        [],
        "--event",
        help="Webhook event key (repeatable). Required for create; optional for update.",
    ),
    filter_event: str | None = typer.Option(
        None, "--filter-event", help="Filter by event when listing repository webhooks"
    ),
    statistics: bool = typer.Option(
        False, "--statistics/--no-statistics", help="Include webhook statistics when listing"
    ),
    active_flag: bool = typer.Option(True, "--active/--inactive", help="Set active flag when creating a webhook"),
    set_active: bool | None = typer.Option(
        None, "--set-active/--set-inactive", help="Set active flag when updating a webhook"
    ),
    secret: str | None = typer.Option(None, "--secret", help="Webhook secret (create/update)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Manage Bitbucket Cloud repository webhooks."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error("cloud_mode_required", message="Webhooks are only available in Bitbucket Cloud mode")
            out.output_error("Webhooks are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:
            result: dict | None = None
            if action == "list":
                if events:
                    raise typer.BadParameter("--event is not applicable for list; use --filter-event")
                payload = client.list_webhooks(
                    project_key,
                    repository_slug,
                    event=filter_event,
                    statistics=statistics,
                )
                result = {"webhooks": payload}
            elif action == "get":
                if webhook_id is None:
                    raise typer.BadParameter("--webhook-id required for get")
                payload = client.get_webhook(project_key, repository_slug, webhook_id)
                result = {"webhook": payload}
            elif action == "create":
                if not yes:
                    raise typer.BadParameter("Refusing to create webhook without --yes")
                if not name:
                    raise typer.BadParameter("--name required for create")
                if not url:
                    raise typer.BadParameter("--url required for create")
                if not events:
                    raise typer.BadParameter("--event required at least once for create")
                payload = client.create_webhook(
                    project_key,
                    repository_slug,
                    name,
                    events,
                    url,
                    active=active_flag,
                    secret=secret,
                )
                result = {"webhook": payload}
            elif action == "update":
                if not yes:
                    raise typer.BadParameter("Refusing to update webhook without --yes")
                if webhook_id is None:
                    raise typer.BadParameter("--webhook-id required for update")
                has_changes = any(
                    [
                        name is not None,
                        url is not None,
                        bool(events),
                        set_active is not None,
                        secret is not None,
                    ]
                )
                if not has_changes:
                    raise typer.BadParameter("Must provide at least one field to update (name/url/event/secret/active)")
                payload = client.update_webhook(
                    project_key,
                    repository_slug,
                    webhook_id,
                    name=name,
                    webhook_url=url,
                    events=events or None,
                    active=set_active,
                    secret=secret,
                )
                result = {"webhook": payload}
            elif action == "delete":
                if not yes:
                    raise typer.BadParameter("Refusing to delete webhook without --yes")
                if webhook_id is None:
                    raise typer.BadParameter("--webhook-id required for delete")
                client.delete_webhook(project_key, repository_slug, webhook_id)
                result = {"deleted": webhook_id}
            else:
                raise typer.BadParameter(f"Unknown action: {action}")

            output_path = report_dir / f"{project_key}_{repository_slug}_webhooks_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Webhooks - {action}\n\n")
                f.write(f"- **Project**: {project_key}\n")
                f.write(f"- **Repository**: {repository_slug}\n")
                f.write(f"- **Action**: {action}\n")
                if action == "list":
                    hooks = result.get("webhooks", []) if result else []
                    f.write(f"- **Count**: {len(hooks)}\n")
                elif action in {"get", "create", "update"}:
                    hook = result.get("webhook", {}) if result else {}
                    f.write(f"- **Webhook ID**: {hook.get('id', 'N/A')}\n")
                    f.write(f"- **Name**: {hook.get('name', name)}\n")
                    f.write(f"- **URL**: {hook.get('url', url)}\n")
                elif action == "delete":
                    f.write(f"- **Deleted ID**: {webhook_id}\n")
            log.info("webhooks_reported", path=str(output_path), action=action)
            out.output_json(result or {})

    except VDSClientError as exc:
        log.exception("bitbucket_error", message=str(exc), context=getattr(exc, "context", {}))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def code_insights(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: create, get, annotate, delete"),
    project_key: str = typer.Argument(..., help="Project key"),
    repository_slug: str = typer.Argument(..., help="Repository slug"),
    commit_id: str = typer.Argument(..., help="Commit hash"),
    report_key: str | None = typer.Option(None, "--report-key", help="Report key (required for all actions)"),
    report_title: str | None = typer.Option(None, "--title", help="Report title (for create)"),
    reporter: str | None = typer.Option(None, "--reporter", help="Reporter name (for create)"),
    result: str | None = typer.Option(None, "--result", help="Report result: PASSED, FAILED, PENDING (for create)"),
    data_file: Path | None = typer.Option(None, "--data-file", help="Path to JSON file with report data (for create)"),
    annotations_file: Path | None = typer.Option(
        None, "--annotations-file", help="Path to JSON file with annotations (for annotate)"
    ),
    report_type: str | None = typer.Option(None, "--report-type", help="Report type (e.g., SECURITY, COVERAGE, TEST)"),
    details: str | None = typer.Option(None, "--details", help="Report details text"),
    link_text: str | None = typer.Option(None, "--link-text", help="External link text"),
    link_url: str | None = typer.Option(None, "--link-url", help="External link URL"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Manage Bitbucket Cloud Code Insights reports."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error("cloud_mode_required", message="Code Insights are only available in Bitbucket Cloud mode")
            out.output_error("Code Insights are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:
            result_obj: dict | None = None

            if not report_key:
                raise typer.BadParameter("--report-key required for all actions")

            if action == "create":
                if not yes:
                    raise typer.BadParameter("Refusing to create report without --yes")
                if not report_title:
                    raise typer.BadParameter("--title required for create")
                if not reporter:
                    raise typer.BadParameter("--reporter required for create")
                if not result:
                    raise typer.BadParameter("--result required for create")

                data = None
                if data_file:
                    if not data_file.exists():
                        raise typer.BadParameter(f"Data file not found: {data_file}")
                    with data_file.open() as f:
                        data = json.load(f)
                        if not isinstance(data, list):
                            raise typer.BadParameter("Data file must contain a JSON array")

                report_params: dict = {}
                if report_type:
                    report_params["report_type"] = report_type
                if details:
                    report_params["details"] = details
                if link_text and link_url:
                    report_params["link"] = {"text": link_text, "href": link_url}

                payload = client.create_code_insights_report(
                    project_key=project_key,
                    repository_slug=repository_slug,
                    commit_id=commit_id,
                    report_key=report_key,
                    report_title=report_title,
                    reporter=reporter,
                    result=result,
                    data=data,
                    **report_params,
                )
                result_obj = {"report": payload}

            elif action == "get":
                payload = client.get_code_insights_report(project_key, repository_slug, commit_id, report_key)
                result_obj = {"report": payload}

            elif action == "annotate":
                if not yes:
                    raise typer.BadParameter("Refusing to add annotations without --yes")
                if not annotations_file:
                    raise typer.BadParameter("--annotations-file required for annotate")
                if not annotations_file.exists():
                    raise typer.BadParameter(f"Annotations file not found: {annotations_file}")

                with annotations_file.open() as f:
                    annotations = json.load(f)
                    if not isinstance(annotations, list):
                        raise typer.BadParameter("Annotations file must contain a JSON array")

                payload = client.add_code_insights_annotations_to_report(
                    project_key, repository_slug, commit_id, report_key, annotations
                )
                result_obj = {"annotations": payload}

            elif action == "delete":
                if not yes:
                    raise typer.BadParameter("Refusing to delete report without --yes")
                client.delete_code_insights_report(project_key, repository_slug, commit_id, report_key)
                result_obj = {"deleted": report_key}

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

            output_path = report_dir / f"{project_key}_{repository_slug}_code_insights_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Code Insights - {action}\n\n")
                f.write(f"- **Project**: {project_key}\n")
                f.write(f"- **Repository**: {repository_slug}\n")
                f.write(f"- **Commit**: {commit_id}\n")
                f.write(f"- **Report Key**: {report_key}\n")
                f.write(f"- **Action**: {action}\n")
                if action == "create" and result_obj:
                    report = result_obj.get("report", {})
                    f.write(f"- **Title**: {report.get('title', report_title)}\n")
                    f.write(f"- **Result**: {report.get('result', result)}\n")
            log.info("code_insights_reported", path=str(output_path), action=action)
            out.output_json(result_obj or {})

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command("repo-variables")
def repo_variables(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace slug (Cloud only)"),
    repo_slug: str = typer.Option(..., "--repo-slug", "-r", help="Repository slug"),
    variable_uuid: str | None = typer.Option(None, "--uuid", help="Variable UUID (for get/update/delete)"),
    key: str | None = typer.Option(None, "--key", help="Variable key (for create/update)"),
    value: str | None = typer.Option(None, "--value", help="Variable value (for create/update)"),
    secured: str | None = typer.Option(None, "--secured", help="Set secured flag (true/false)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (create/update/delete)"),
) -> None:
    """Manage repository variables (Bitbucket Cloud only)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error(
                "cloud_mode_required",
                message="Repository variable operations are only available in Bitbucket Cloud mode",
            )
            out.output_error("Repository variable operations are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:

            def _coerce_secured(raw_value: str | None) -> bool | None:
                if raw_value is None:
                    return None
                normalized = raw_value.strip().lower()
                if normalized in {"true", "1", "yes"}:
                    return True
                if normalized in {"false", "0", "no"}:
                    return False
                raise typer.BadParameter("--secured must be true/false")

            if action == "list":
                variables = client.list_repository_variables(workspace, repo_slug)
                output_path = report_dir / f"{workspace}_{repo_slug}_repository_variables.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    f.write(f"# Repository Variables - {workspace}/{repo_slug}\n\n")
                    f.write(f"- **Count**: {len(variables)}\n\n")
                    for variable in variables:
                        key_value = variable.get("key", "unknown")
                        uuid_value = variable.get("uuid", "unknown")
                        secured_value = variable.get("secured", False)
                        f.write(f"- `{key_value}` (uuid={uuid_value}, secured={secured_value})\n")
                log.info(
                    "repo_variables_reported",
                    workspace=workspace,
                    repository_slug=repo_slug,
                    count=len(variables),
                    path=str(output_path),
                )
                out.output_json(
                    {"workspace": workspace, "repository": repo_slug, "count": len(variables), "variables": variables}
                )

            elif action == "get":
                if not variable_uuid:
                    raise typer.BadParameter("--uuid required for get")
                variable = client.get_repository_variable(workspace, repo_slug, variable_uuid)
                out.output_json(variable)

            elif action == "create":
                if not yes:
                    raise typer.BadParameter("Refusing to create variable without --yes")
                if not key:
                    raise typer.BadParameter("--key required for create")
                if value is None:
                    raise typer.BadParameter("--value required for create")
                secured_value = _coerce_secured(secured)
                secured_flag = secured_value if secured_value is not None else False
                variable = client.create_repository_variable(workspace, repo_slug, key, value, secured=secured_flag)
                out.output_json(variable)

            elif action == "update":
                if not yes:
                    raise typer.BadParameter("Refusing to update variable without --yes")
                if not variable_uuid:
                    raise typer.BadParameter("--uuid required for update")
                secured_value = _coerce_secured(secured)
                if key is None and value is None and secured_value is None:
                    raise typer.BadParameter("Provide at least one of --key/--value/--secured to update")
                variable = client.update_repository_variable(
                    workspace,
                    repo_slug,
                    variable_uuid,
                    key=key,
                    value=value,
                    secured=secured_value,
                )
                out.output_json(variable)

            elif action == "delete":
                if not yes:
                    raise typer.BadParameter("Refusing to delete variable without --yes")
                if not variable_uuid:
                    raise typer.BadParameter("--uuid required for delete")
                client.delete_repository_variable(workspace, repo_slug, variable_uuid)
                out.output_json({"status": "deleted", "uuid": variable_uuid})

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command("deployment-env")
def deployment_env(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, get, vars"),
    sub_action: str | None = typer.Argument(None, help="Sub-action for vars: list, create, update, delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace slug (Cloud only)"),
    repo_slug: str = typer.Option(..., "--repo-slug", "-r", help="Repository slug"),
    env_uuid: str | None = typer.Option(None, "--env-uuid", help="Deployment environment UUID"),
    variable_uuid: str | None = typer.Option(None, "--var-uuid", help="Deployment environment variable UUID"),
    key: str | None = typer.Option(None, "--key", help="Variable key (for create/update)"),
    value: str | None = typer.Option(None, "--value", help="Variable value (for create/update)"),
    secured: str | None = typer.Option(None, "--secured", help="Set secured flag (true/false)"),
    pagelen: int = typer.Option(10, "--pagelen", help="Pagelen for variable listing"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (vars create/update/delete)"),
) -> None:
    """Manage deployment environments and their variables (Bitbucket Cloud only)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error(
                "cloud_mode_required",
                message="Deployment environment operations are only available in Bitbucket Cloud mode",
            )
            out.output_error("Deployment environment operations are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:

            def _coerce_secured(raw_value: str | None) -> bool | None:
                if raw_value is None:
                    return None
                normalized = raw_value.strip().lower()
                if normalized in {"true", "1", "yes"}:
                    return True
                if normalized in {"false", "0", "no"}:
                    return False
                raise typer.BadParameter("--secured must be true/false")

            if action == "list":
                environments = client.list_deployment_environments(workspace, repo_slug)
                output_path = report_dir / f"{workspace}_{repo_slug}_deployment_environments.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    f.write(f"# Deployment Environments - {workspace}/{repo_slug}\n\n")
                    f.write(f"- **Count**: {len(environments)}\n\n")
                    for env in environments:
                        f.write(
                            f"- `{env.get('uuid', 'unknown')}` "
                            f"(name={env.get('name', 'unknown')}, category={env.get('category', 'unknown')})\n"
                        )
                log.info(
                    "deployment_env_reported",
                    workspace=workspace,
                    repository_slug=repo_slug,
                    count=len(environments),
                    path=str(output_path),
                )
                out.output_json({"workspace": workspace, "repository": repo_slug, "environments": environments})

            elif action == "get":
                if not env_uuid:
                    raise typer.BadParameter("--env-uuid required for get")
                environment = client.get_deployment_environment(workspace, repo_slug, env_uuid)
                out.output_json(environment)

            elif action == "vars":
                if sub_action is None:
                    raise typer.BadParameter("Sub-action required for vars (list, create, update, delete)")
                if sub_action not in {"list", "create", "update", "delete"}:
                    raise typer.BadParameter(f"Unknown vars sub-action: {sub_action}")
                if not env_uuid:
                    raise typer.BadParameter("--env-uuid required for vars actions")

                if sub_action == "list":
                    variables = client.list_deployment_environment_variables(
                        workspace, repo_slug, env_uuid, pagelen=pagelen
                    )
                    output_path = report_dir / f"{workspace}_{repo_slug}_{env_uuid}_deployment_env_variables.md"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with output_path.open("w") as f:
                        f.write(f"# Deployment Environment Variables - {env_uuid}\n\n")
                        f.write(f"- **Count**: {len(variables)}\n\n")
                        for variable in variables:
                            f.write(
                                f"- `{variable.get('key', 'unknown')}` "
                                f"(uuid={variable.get('uuid', 'unknown')}, secured={variable.get('secured', False)})\n"
                            )
                    log.info(
                        "deployment_env_vars_reported",
                        workspace=workspace,
                        repository_slug=repo_slug,
                        environment_uuid=env_uuid,
                        count=len(variables),
                        path=str(output_path),
                    )
                    out.output_json(
                        {
                            "workspace": workspace,
                            "repository": repo_slug,
                            "environment_uuid": env_uuid,
                            "count": len(variables),
                            "variables": variables,
                        }
                    )

                elif sub_action == "create":
                    if not yes:
                        raise typer.BadParameter("Refusing to create variable without --yes")
                    if not key:
                        raise typer.BadParameter("--key required for vars create")
                    if value is None:
                        raise typer.BadParameter("--value required for vars create")
                    secured_value = _coerce_secured(secured)
                    secured_flag = secured_value if secured_value is not None else False
                    variable = client.create_deployment_environment_variable(
                        workspace, repo_slug, env_uuid, key, value, secured=secured_flag
                    )
                    out.output_json(variable)

                elif sub_action == "update":
                    if not yes:
                        raise typer.BadParameter("Refusing to update variable without --yes")
                    if not variable_uuid:
                        raise typer.BadParameter("--var-uuid required for vars update")
                    secured_value = _coerce_secured(secured)
                    if key is None and value is None and secured_value is None:
                        raise typer.BadParameter("Provide at least one of --key/--value/--secured to update")
                    variable = client.update_deployment_environment_variable(
                        workspace,
                        repo_slug,
                        env_uuid,
                        variable_uuid,
                        key=key,
                        value=value,
                        secured=secured_value,
                    )
                    out.output_json(variable)

                elif sub_action == "delete":
                    if not yes:
                        raise typer.BadParameter("Refusing to delete variable without --yes")
                    if not variable_uuid:
                        raise typer.BadParameter("--var-uuid required for vars delete")
                    client.delete_deployment_environment_variable(workspace, repo_slug, env_uuid, variable_uuid)
                    out.output_json({"status": "deleted", "uuid": variable_uuid})

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command("pr-blocker")
def pr_blocker(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, add, delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace slug (Cloud only)"),
    repo_slug: str = typer.Option(..., "--repo-slug", "-r", help="Repository slug"),
    pull_request_id: str = typer.Option(..., "--pull-request-id", "-p", help="Pull request ID"),
    blocker_uuid: str | None = typer.Option(None, "--blocker-uuid", help="Blocker UUID (for delete)"),
    message: str | None = typer.Option(None, "--message", help="Blocker message (for add)"),
    reason: str | None = typer.Option(None, "--reason", help="Blocker reason (for add)"),
    severity: str | None = typer.Option(None, "--severity", help="Blocker severity (for add)"),
    search: str | None = typer.Option(None, "--search", help="Filter expression (for list)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm delete operation"),
) -> None:
    """Manage pull request blockers (Bitbucket Cloud only)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error(
                "cloud_mode_required",
                message="Pull request blocker operations are only available in Bitbucket Cloud mode",
            )
            out.output_error("Pull request blocker operations are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:
            if action == "list":
                blockers = client.list_pull_request_blockers(
                    workspace,
                    repo_slug,
                    pull_request_id,
                    query=search,
                )
                output_path = report_dir / f"{workspace}_{repo_slug}_{pull_request_id}_pr_blockers.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    f.write(f"# Pull Request Blockers - {pull_request_id}\n\n")
                    f.write(f"- **Count**: {len(blockers)}\n\n")
                    for blocker in blockers:
                        f.write(
                            f"- `{blocker.get('uuid', 'unknown')}` "
                            f"(message={blocker.get('message', '')}, reason={blocker.get('reason')})\n"
                        )
                log.info(
                    "pull_request_blockers_reported",
                    workspace=workspace,
                    repository_slug=repo_slug,
                    pull_request_id=pull_request_id,
                    count=len(blockers),
                    path=str(output_path),
                )
                out.output_json({"blockers": blockers})

            elif action == "add":
                if not message:
                    raise typer.BadParameter("--message required for add")
                blocker = client.add_pull_request_blocker(
                    workspace,
                    repo_slug,
                    pull_request_id,
                    message,
                    reason=reason,
                    severity=severity,
                )
                out.output_json(blocker)

            elif action == "delete":
                if not yes:
                    raise typer.BadParameter("Refusing to delete blocker without --yes")
                if not blocker_uuid:
                    raise typer.BadParameter("--blocker-uuid required for delete")
                client.delete_pull_request_blocker(
                    workspace,
                    repo_slug,
                    pull_request_id,
                    blocker_uuid,
                )
                out.output_json({"status": "deleted", "uuid": blocker_uuid})

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command("issue")
def issue(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace slug (Cloud only)"),
    repo_slug: str = typer.Option(..., "--repo-slug", "-r", help="Repository slug"),
    issue_id: str | None = typer.Option(None, "--issue-id", "-i", help="Issue ID (for get/update/delete)"),
    title: str | None = typer.Option(None, "--title", help="Issue title (for create/update)"),
    description: str | None = typer.Option(None, "--description", help="Issue description (for create/update)"),
    kind: str | None = typer.Option(None, "--kind", help="Issue kind (bug, enhancement, proposal, task)"),
    priority: str | None = typer.Option(
        None, "--priority", help="Issue priority (trivial, minor, major, critical, blocker)"
    ),
    state: str | None = typer.Option(None, "--state", help="Issue state (for update)"),
    query: str | None = typer.Option(None, "--query", help="Filtering query (for list)"),
    sort: str | None = typer.Option(None, "--sort", help="Sort clause (for list)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm delete operation"),
) -> None:
    """Manage Bitbucket Cloud issues for repositories."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error(
                "cloud_mode_required",
                message="Repository issue operations are only available in Bitbucket Cloud mode",
            )
            out.output_error("Repository issue operations are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:
            if action == "list":
                issues = client.list_repository_issues(workspace, repo_slug, query=query, sort=sort)
                output_path = report_dir / f"{workspace}_{repo_slug}_issues.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    f.write(f"# Repository Issues - {workspace}/{repo_slug}\n\n")
                    f.write(f"- **Count**: {len(issues)}\n\n")
                    for issue_obj in issues:
                        f.write(
                            f"- `{issue_obj.get('id', 'unknown')}` "
                            f"(title={issue_obj.get('title', '')}, state={issue_obj.get('state', '')})\n"
                        )
                log.info(
                    "repository_issues_reported",
                    workspace=workspace,
                    repository_slug=repo_slug,
                    count=len(issues),
                    query=query,
                    sort=sort,
                    path=str(output_path),
                )
                out.output_json({"issues": issues})

            elif action == "get":
                if not issue_id:
                    raise typer.BadParameter("--issue-id required for get")
                issue_obj = client.get_repository_issue(workspace, repo_slug, issue_id)
                out.output_json(issue_obj)

            elif action == "create":
                if not title:
                    raise typer.BadParameter("--title required for create")
                create_kind = kind or "task"
                create_priority = priority or "major"
                issue_obj = client.create_repository_issue(
                    workspace,
                    repo_slug,
                    title,
                    description or "",
                    kind=create_kind,
                    priority=create_priority,
                )
                out.output_json(issue_obj)

            elif action == "update":
                if not issue_id:
                    raise typer.BadParameter("--issue-id required for update")
                if title is None and description is None and kind is None and priority is None and state is None:
                    raise typer.BadParameter(
                        "Provide at least one field to update (--title/--description/--kind/--priority/--state)"
                    )
                issue_obj = client.update_repository_issue(
                    workspace,
                    repo_slug,
                    issue_id,
                    title=title,
                    description=description,
                    kind=kind,
                    priority=priority,
                    state=state,
                )
                out.output_json(issue_obj)

            elif action == "delete":
                if not issue_id:
                    raise typer.BadParameter("--issue-id required for delete")
                if not yes:
                    raise typer.BadParameter("Refusing to delete issue without --yes")
                client.delete_repository_issue(workspace, repo_slug, issue_id)
                out.output_json({"status": "deleted", "issue_id": issue_id})

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command("pipeline-advanced")
def pipeline_advanced(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: get, steps, step, log, stop"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace slug (Cloud only)"),
    repo_slug: str = typer.Option(..., "--repo-slug", "-r", help="Repository slug"),
    pipeline_uuid: str | None = typer.Option(None, "--pipeline-uuid", help="Pipeline UUID"),
    step_uuid: str | None = typer.Option(None, "--step-uuid", help="Step UUID (for step/log)"),
    start: int | None = typer.Option(None, "--start", help="Start byte for log range"),
    end: int | None = typer.Option(None, "--end", help="End byte for log range"),
    output: Path | None = typer.Option(None, "--output", help="Optional file path to write log output"),
    yes: bool = typer.Option(False, "--yes", help="Confirm stop operation"),
) -> None:
    """Advanced pipeline operations (Bitbucket Cloud only)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        if not settings.is_cloud_mode:
            log.error(
                "cloud_mode_required",
                message="Advanced pipeline operations are only available in Bitbucket Cloud mode",
            )
            out.output_error("Advanced pipeline operations are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:
            if action == "get":
                if not pipeline_uuid:
                    raise typer.BadParameter("--pipeline-uuid required for get")
                pipeline = client.get_pipeline(workspace, repo_slug, pipeline_uuid)
                out.output_json(pipeline)

            elif action == "steps":
                if not pipeline_uuid:
                    raise typer.BadParameter("--pipeline-uuid required for steps")
                steps = client.list_pipeline_steps(workspace, repo_slug, pipeline_uuid)
                output_path = report_dir / f"{workspace}_{repo_slug}_{pipeline_uuid}_pipeline_steps.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    f.write(f"# Pipeline Steps - {pipeline_uuid}\n\n")
                    f.write(f"- **Count**: {len(steps)}\n\n")
                    for step in steps:
                        f.write(
                            f"- `{step.get('uuid', 'unknown')}` "
                            f"(state={step.get('state', 'unknown')}, duration={step.get('duration_in_seconds')})\n"
                        )
                log.info(
                    "pipeline_steps_reported",
                    workspace=workspace,
                    repository_slug=repo_slug,
                    pipeline_uuid=pipeline_uuid,
                    count=len(steps),
                    path=str(output_path),
                )
                out.output_json({"pipeline_uuid": pipeline_uuid, "steps": steps})

            elif action == "step":
                if not pipeline_uuid:
                    raise typer.BadParameter("--pipeline-uuid required for step")
                if not step_uuid:
                    raise typer.BadParameter("--step-uuid required for step")
                step = client.get_pipeline_step(workspace, repo_slug, pipeline_uuid, step_uuid)
                out.output_json(step)

            elif action == "log":
                if not pipeline_uuid:
                    raise typer.BadParameter("--pipeline-uuid required for log")
                if not step_uuid:
                    raise typer.BadParameter("--step-uuid required for log")
                payload = client.get_pipeline_step_log(
                    workspace,
                    repo_slug,
                    pipeline_uuid,
                    step_uuid,
                    start=start,
                    end=end,
                )
                content = payload.get("content", "")
                if output:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(content)
                    log.info(
                        "pipeline_step_log_written",
                        workspace=workspace,
                        repository_slug=repo_slug,
                        pipeline_uuid=pipeline_uuid,
                        step_uuid=step_uuid,
                        path=str(output),
                    )
                    out.output_json({"status": "written", "path": str(output), **payload})
                else:
                    output_path = report_dir / f"{workspace}_{repo_slug}_{pipeline_uuid}_{step_uuid}_pipeline_log.txt"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(content)
                    log.info(
                        "pipeline_step_log_reported",
                        workspace=workspace,
                        repository_slug=repo_slug,
                        pipeline_uuid=pipeline_uuid,
                        step_uuid=step_uuid,
                        path=str(output_path),
                    )
                    out.output_json({"status": "written", "path": str(output_path), **payload})

            elif action == "stop":
                if not pipeline_uuid:
                    raise typer.BadParameter("--pipeline-uuid required for stop")
                if not yes:
                    raise typer.BadParameter("Refusing to stop pipeline without --yes")
                payload = client.stop_pipeline(workspace, repo_slug, pipeline_uuid)
                output_path = report_dir / f"{workspace}_{repo_slug}_{pipeline_uuid}_pipeline_stop.md"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    f.write(f"# Pipeline Stop - {pipeline_uuid}\n\n")
                    f.write(f"- **Status**: {payload.get('status', 'stopped')}\n")
                log.info(
                    "pipeline_stop_reported",
                    workspace=workspace,
                    repository_slug=repo_slug,
                    pipeline_uuid=pipeline_uuid,
                    path=str(output_path),
                )
                out.output_json(payload)

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def repo_settings(
    ctx: typer.Context,
    category: str = typer.Argument(..., help="Category: branching-model, default-branch, hooks, lfs"),
    action: str = typer.Argument(..., help="Action: get, set, enable, disable (varies by category)"),
    project_key: str = typer.Argument(..., help="Project key"),
    repository_slug: str = typer.Argument(..., help="Repository slug"),
    model_file: Path | None = typer.Option(
        None, "--model-file", help="Path to JSON file with branching model (for set)"
    ),
    branch: str | None = typer.Option(None, "--branch", help="Branch name (for default-branch set)"),
    hook_key: str | None = typer.Option(None, "--hook-key", help="Hook key (for hooks enable/disable)"),
    enabled: bool | None = typer.Option(None, "--enabled/--disabled", help="Enable/disable LFS (for lfs set)"),
    start: int = typer.Option(0, "--start", help="Start index for pagination (for hooks get)"),
    limit: int | None = typer.Option(None, "--limit", help="Limit for pagination (for hooks get)"),
    filter_type: str | None = typer.Option(None, "--filter-type", help="Filter type (for hooks get)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Manage Bitbucket repository settings."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        load_settings(strict=True)
        with _get_client() as client:
            result_obj: dict | None = None

            if category == "branching-model":
                if action == "get":
                    payload = client.get_branching_model(project_key, repository_slug)
                    result_obj = {"branching_model": payload}
                elif action == "set":
                    if not yes:
                        raise typer.BadParameter("Refusing to set branching model without --yes")
                    if not model_file:
                        raise typer.BadParameter("--model-file required for set")
                    if not model_file.exists():
                        raise typer.BadParameter(f"Model file not found: {model_file}")
                    with model_file.open() as f:
                        model = json.load(f)
                    payload = client.set_branching_model(project_key, repository_slug, model)
                    result_obj = {"branching_model": payload}
                elif action == "enable":
                    if not yes:
                        raise typer.BadParameter("Refusing to enable branching model without --yes")
                    payload = client.enable_branching_model(project_key, repository_slug)
                    result_obj = {"branching_model": payload}
                elif action == "disable":
                    if not yes:
                        raise typer.BadParameter("Refusing to disable branching model without --yes")
                    payload = client.disable_branching_model(project_key, repository_slug)
                    result_obj = {"branching_model": payload}
                else:
                    raise typer.BadParameter(f"Unknown action for branching-model: {action}")

            elif category == "default-branch":
                if action == "get":
                    payload = client.get_default_branch(project_key, repository_slug)
                    result_obj = {"default_branch": payload}
                elif action == "set":
                    if not yes:
                        raise typer.BadParameter("Refusing to set default branch without --yes")
                    if not branch:
                        raise typer.BadParameter("--branch required for set")
                    payload = client.set_default_branch(project_key, repository_slug, branch)
                    result_obj = {"default_branch": payload}
                else:
                    raise typer.BadParameter(f"Unknown action for default-branch: {action}")

            elif category == "hooks":
                if action == "get":
                    payload = client.get_repo_hook_settings(
                        project_key, repository_slug, start=start, limit=limit, filter_type=filter_type
                    )
                    result_obj = {"hooks": payload}
                elif action == "enable":
                    if not yes:
                        raise typer.BadParameter("Refusing to enable hook without --yes")
                    if not hook_key:
                        raise typer.BadParameter("--hook-key required for enable")
                    payload = client.enable_repo_hook_settings(project_key, repository_slug, hook_key)
                    result_obj = {"hook": payload}
                elif action == "disable":
                    if not yes:
                        raise typer.BadParameter("Refusing to disable hook without --yes")
                    if not hook_key:
                        raise typer.BadParameter("--hook-key required for disable")
                    payload = client.disable_repo_hook_settings(project_key, repository_slug, hook_key)
                    result_obj = {"hook": payload}
                else:
                    raise typer.BadParameter(f"Unknown action for hooks: {action}")

            elif category == "lfs":
                if action == "get":
                    payload = client.get_lfs_repo_status(project_key, repository_slug)
                    result_obj = {"lfs": payload}
                elif action == "set":
                    if not yes:
                        raise typer.BadParameter("Refusing to set LFS status without --yes")
                    if enabled is None:
                        raise typer.BadParameter("--enabled or --disabled required for set")
                    payload = client.set_lfs_repo_status(project_key, repository_slug, enabled)
                    result_obj = {"lfs": payload}
                else:
                    raise typer.BadParameter(f"Unknown action for lfs: {action}")

            else:
                raise typer.BadParameter(f"Unknown category: {category}")

            output_path = report_dir / f"{project_key}_{repository_slug}_repo_settings_{category}_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Repository Settings - {category} - {action}\n\n")
                f.write(f"- **Project**: {project_key}\n")
                f.write(f"- **Repository**: {repository_slug}\n")
                f.write(f"- **Category**: {category}\n")
                f.write(f"- **Action**: {action}\n")
            log.info("repo_settings_reported", path=str(output_path), category=category, action=action)
            out.output_json(result_obj or {})

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def code_advanced(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: file-list, commit-info, commit-changes, search, search-advanced"),
    project_key: str | None = typer.Option(
        None, "--project-key", help="Project key (for file-list, commit-info, commit-changes)"
    ),
    repository_slug: str | None = typer.Option(
        None, "--repository-slug", help="Repository slug (for file-list, commit-info, commit-changes)"
    ),
    sub_folder: str | None = typer.Option(None, "--sub-folder", help="Subfolder path (for file-list)"),
    query: str | None = typer.Option(None, "--query", help="Query string for filtering (for file-list)"),
    commit: str | None = typer.Option(None, "--commit", help="Commit hash (for commit-info)"),
    commit_id: str | None = typer.Option(None, "--commit-id", help="Commit ID (for commit-changes)"),
    hash_newest: str | None = typer.Option(None, "--hash-newest", help="Newest commit hash (for commit-changes)"),
    path: str | None = typer.Option(None, "--path", help="File path (for commit-info)"),
    merges: str = typer.Option(
        "include", "--merges", help="How to handle merges: include, exclude, only (for commit-changes)"
    ),
    team: str | None = typer.Option(None, "--team", help="Team/workspace name (for search, Cloud-only)"),
    search_query: str | None = typer.Option(None, "--search-query", help="Search query string (for search)"),
    repository: str | None = typer.Option(None, "--repository", help="Repository slug filter (for search-advanced)"),
    start: int = typer.Option(0, "--start", help="Start index for pagination"),
    limit: int | None = typer.Option(None, "--limit", help="Limit for pagination"),
    page: int = typer.Option(1, "--page", help="Page number (for search)"),
) -> None:
    """Advanced code operations."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)
        with _get_client() as client:
            result_obj: dict | None = None

            if action == "file-list":
                if not project_key:
                    raise typer.BadParameter("--project-key required for file-list")
                if not repository_slug:
                    raise typer.BadParameter("--repository-slug required for file-list")
                payload = client.get_file_list(
                    project_key, repository_slug, sub_folder=sub_folder, query=query, start=start, limit=limit
                )
                result_obj = {"files": payload}

            elif action == "commit-info":
                if not project_key:
                    raise typer.BadParameter("--project-key required for commit-info")
                if not repository_slug:
                    raise typer.BadParameter("--repository-slug required for commit-info")
                if not commit:
                    raise typer.BadParameter("--commit required for commit-info")
                payload = client.get_commit_info(project_key, repository_slug, commit, path=path)
                result_obj = {"commit": payload}

            elif action == "commit-changes":
                if not project_key:
                    raise typer.BadParameter("--project-key required for commit-changes")
                if not repository_slug:
                    raise typer.BadParameter("--repository-slug required for commit-changes")
                if not commit_id and not hash_newest:
                    raise typer.BadParameter("--commit-id or --hash-newest required for commit-changes")
                payload = client.get_commit_changes(
                    project_key, repository_slug, commit_id=commit_id, hash_newest=hash_newest, merges=merges
                )
                result_obj = {"changes": payload}

            elif action == "search":
                if not settings.is_cloud_mode:
                    log.error("cloud_mode_required", message="Code search is only available in Bitbucket Cloud mode")
                    out.output_error("Code search is only available in Bitbucket Cloud mode")
                    raise typer.Exit(1) from None
                if not team:
                    raise typer.BadParameter("--team required for search")
                if not search_query:
                    raise typer.BadParameter("--search-query required for search")
                payload = client.search_code(team, search_query, page=page, limit=limit or 10)
                result_obj = {"results": payload}
            elif action == "search-advanced":
                if not settings.is_cloud_mode:
                    log.error("cloud_mode_required", message="Code search is only available in Bitbucket Cloud mode")
                    out.output_error("Code search is only available in Bitbucket Cloud mode")
                    raise typer.Exit(1) from None
                if not team:
                    raise typer.BadParameter("--team required for search-advanced")
                if not search_query:
                    raise typer.BadParameter("--search-query required for search-advanced")
                payload = client.search_code_advanced(
                    team, search_query, page=page, limit=limit or 10, repository=repository
                )
                result_obj = {"results": payload, "repository_filter": repository}

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

            output_path = report_dir / f"{project_key or team}_code_advanced_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Advanced Code Operations - {action}\n\n")
                if project_key:
                    f.write(f"- **Project**: {project_key}\n")
                if repository_slug:
                    f.write(f"- **Repository**: {repository_slug}\n")
                if team:
                    f.write(f"- **Team**: {team}\n")
                f.write(f"- **Action**: {action}\n")
            log.info("code_advanced_reported", path=str(output_path), action=action)
            out.output_json(result_obj or {})

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def workspace(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, get, permissions, projects, project"),
    workspace_slug: str | None = typer.Option(
        None, "--workspace-slug", help="Workspace slug (required for all actions except list)"
    ),
    repo_slug: str | None = typer.Option(None, "--repo-slug", help="Repository slug (for permissions action)"),
    project_key: str | None = typer.Option(None, "--project-key", help="Project key (for project action)"),
) -> None:
    """Cloud workspace operations (Cloud-only)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)
    report_dir = _REPORT_DIR

    try:
        settings = load_settings(strict=True)

        if not settings.is_cloud_mode:
            log.error("cloud_mode_required", message="Workspace operations are only available in Bitbucket Cloud mode")
            out.output_error("Workspace operations are only available in Bitbucket Cloud mode")
            raise typer.Exit(1) from None

        with _get_client() as client:
            result_obj: dict | None = None

            if action == "list":
                payload = client.list_workspaces()
                result_obj = {"workspaces": payload, "count": len(payload)}

            elif action == "get":
                if not workspace_slug:
                    raise typer.BadParameter("--workspace-slug required for get")
                payload = client.get_workspace(workspace_slug)
                result_obj = {"workspace": payload}

            elif action == "permissions":
                if not workspace_slug:
                    raise typer.BadParameter("--workspace-slug required for permissions")
                if repo_slug:
                    payload = client.get_workspace_repository_permissions(workspace_slug, repo_slug=repo_slug)
                    result_obj = {"repository_permissions": payload}
                else:
                    payload = client.get_workspace_permissions(workspace_slug)
                    result_obj = {"workspace_permissions": payload, "count": len(payload)}

            elif action == "projects":
                if not workspace_slug:
                    raise typer.BadParameter("--workspace-slug required for projects")
                payload = client.list_workspace_projects(workspace_slug)
                result_obj = {"projects": payload, "count": len(payload)}

            elif action == "project":
                if not workspace_slug:
                    raise typer.BadParameter("--workspace-slug required for project")
                if not project_key:
                    raise typer.BadParameter("--project-key required for project")
                payload = client.get_workspace_project(workspace_slug, project_key)
                result_obj = {"project": payload}

            else:
                raise typer.BadParameter(f"Unknown action: {action}")

            output_path = report_dir / f"{workspace_slug or 'all'}_workspace_{action}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                f.write(f"# Workspace Operations - {action}\n\n")
                if workspace_slug:
                    f.write(f"- **Workspace**: {workspace_slug}\n")
                if repo_slug:
                    f.write(f"- **Repository**: {repo_slug}\n")
                if project_key:
                    f.write(f"- **Project**: {project_key}\n")
                f.write(f"- **Action**: {action}\n")
            log.info("workspace_reported", path=str(output_path), action=action, workspace_slug=workspace_slug)
            out.output_json(result_obj or {})

    except VDSClientError as exc:
        _handle_error(exc, out, log)
        raise typer.Exit(1) from None
    except typer.BadParameter as exc:
        log.exception("parameter_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def clone(
    ctx: typer.Context,
    identifier: str = typer.Argument(
        ..., help="Repository identifier: PROJECT/repo, browse URL, clone URL, or SSH URL"
    ),
    target: Path | None = typer.Option(None, "--target", "-t", help="Target directory (default: VDS cache root)"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch to clone"),
    shallow: bool = typer.Option(False, "--shallow", help="Shallow clone (depth 1)"),
    force: bool = typer.Option(False, "--force", help="Force reclone if directory exists"),
) -> None:
    """Clone a Bitbucket repository to the local VDS cache."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)

    try:
        ref = parse_repo_identifier(identifier)
    except ValueError as exc:
        log.exception("invalid_identifier", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None

    try:
        settings = load_settings(strict=True)

        with BitbucketClient(settings) as client:
            client.get_repository(ref.project_key, ref.repo_slug)

            resolved_branch = branch
            if not resolved_branch:
                default = client.get_default_branch(ref.project_key, ref.repo_slug)
                if isinstance(default, dict):
                    resolved_branch = default.get("displayId") or default.get("id")

            clone_url = build_clone_url(
                ref,
                settings.get_url(),
                username=settings.username,
                token=settings.token,
            )

            cache_root = get_vds_cache_root()
            dest = target or cache_root / "repos" / f"{ref.project_key}-project" / ref.repo_slug

            result = clone_repo(
                ref,
                clone_url,
                dest,
                branch=resolved_branch,
                shallow=shallow,
                force_reclone=force,
            )

        payload = {
            "status": "success",
            "operation": result.operation,
            "project": ref.project_key,
            "repo": ref.repo_slug,
            "branch": result.branch,
            "path": str(result.path),
        }
        out.output_json(payload)

    except NotFoundError as exc:
        log.exception("repo_not_found", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except (VDSClientError, SettingsError) as exc:
        log.exception("bitbucket_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def archive(
    ctx: typer.Context,
    identifier: str = typer.Argument(
        ..., help="Repository identifier: PROJECT/repo, browse URL, clone URL, or SSH URL"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output archive path (default: VDS cache)"),
    format: str = typer.Option("zip", "--format", "-f", help="Archive format: zip, tar.gz, tgz, tar"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch/tag/commit to archive"),
    path: str | None = typer.Option(None, "--path", help="Limit archive to path prefix"),
    include_git: bool = typer.Option(False, "--include-git", help="Include .git directory (forces local-zip method)"),
) -> None:
    """Download a Bitbucket repository as an archive (zip or tar.gz)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    log = structlog.get_logger(__name__)

    try:
        ref = parse_repo_identifier(identifier)
    except ValueError as exc:
        log.exception("invalid_identifier", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None

    try:
        settings = load_settings(strict=True)
        cache_root = get_vds_cache_root()

        clone_url = build_clone_url(
            ref,
            settings.get_url(),
            username=settings.username,
            token=settings.token,
        )

        ext = "tar.gz" if format in ("tar.gz", "tgz") else format
        archive_path = output or (cache_root / "archives" / f"{ref.project_key}-{ref.repo_slug}.{ext}")
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        with BitbucketClient(settings) as client:
            result = archive_repo(
                ref,
                client,
                clone_url,
                cache_root,
                archive_path,
                format=format,
                at=branch,
                path=path,
                include_git=include_git,
            )

        payload = {
            "status": "success",
            "project": ref.project_key,
            "repo": ref.repo_slug,
            "archive_path": str(result.archive_path),
            "format": result.format,
            "size_bytes": result.size_bytes,
            "method": result.method,
        }
        out.output_json(payload)

    except NotFoundError as exc:
        log.exception("repo_not_found", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except (VDSClientError, SettingsError) as exc:
        log.exception("bitbucket_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except Exception as exc:
        log.exception("unexpected_error", message=str(exc))
        out.output_error(str(exc))
        raise typer.Exit(1) from None
