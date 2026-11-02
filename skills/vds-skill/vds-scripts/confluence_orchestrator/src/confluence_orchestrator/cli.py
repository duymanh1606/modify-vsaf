"""Typer CLI wrapper for Confluence operations during the native Python implementations."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import structlog
import typer
from vds_platform_core.logging import configure_structlog

from .config import ConfluenceSettings, load_settings
from .content import ContentClient
from .content_v2 import ContentClientV2
from .crawl_tree import CrawlOptions, crawl_tree_to_disk
from .errors import VDSClientError
from .eventing import Poller
from .http import ConfluenceClient
from .orchestration import BatchRunner, WebhookClient
from .reporting import RunSummary, write_reports
from .tree_copier import CopyOptions, TreeCopier

# ---------------------------------------------------------------------------
# Typer setup & logging
# ---------------------------------------------------------------------------

app = typer.Typer(add_completion=False, help="Confluence operations orchestrator")
content_app = typer.Typer(help="Native Confluence API commands")
batch_app = typer.Typer(help="Batch polling utilities (REST v1)")
webhook_app = typer.Typer(help="Webhook management (REST v1)")
app.add_typer(content_app, name="content")
app.add_typer(batch_app, name="batch-native")
app.add_typer(webhook_app, name="webhook-native")

# Logger will be configured in main() callback
logger = logging.getLogger("confluence_cli")

# ---------------------------------------------------------------------------
# Paths and legacy script mapping
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parents[3]
_DEFAULT_REPORT_DIR = (_SCRIPTS_DIR / "reports" / "confluence_runs").resolve()


@dataclass(slots=True)
class CLIContext:
    report_dir: Path
    markdown: bool
    api_version: str
    reports: bool


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _normalise_server(server: str | None, settings: ConfluenceSettings) -> str:
    return server.lower() if server else settings.default_server.lower()


def _infer_server_from_root_ref(root_ref: str, settings: ConfluenceSettings) -> str | None:
    root_ref = (root_ref or "").strip()
    if not root_ref:
        return None

    parsed = urlparse(root_ref)
    if not parsed.scheme or not parsed.netloc:
        return None

    target = parsed.netloc.lower()
    internal = urlparse(str(settings.internal_url)).netloc.lower()
    external = urlparse(str(settings.external_url)).netloc.lower()

    if target == internal:
        return "internal"
    if target == external:
        return "external"
    return None


def _build_env(server: str, settings: ConfluenceSettings) -> dict:
    token = settings.token_for(server)
    if not token and not (settings.username and settings.password):
        raise VDSClientError(
            f"Credentials for server '{server}' are missing. Provide VDS_USERNAME+VDS_PASSWORD as the primary auth mechanism or tokens "
            "(INTERNAL_CONFLUENCE_TOKEN/EXTERNAL_CONFLUENCE_TOKEN) as fallback.",
            context={"server": server},
        )
    env = os.environ.copy()
    env.update(
        {
            "CONFLUENCE_SERVER": server,
            "CONFLUENCE_TOKEN": token or "",
            "CONFLUENCE_URL": str(settings.url_for(server)),
            "INTERNAL_CONFLUENCE_TOKEN": settings.internal_token or "",
            "EXTERNAL_CONFLUENCE_TOKEN": settings.external_token or "",
        }
    )
    return env


def _build_http_client(settings: ConfluenceSettings, server: str) -> ConfluenceClient:
    return ConfluenceClient(settings, server=server)


def _get_cli_ctx(ctx: typer.Context) -> CLIContext:
    cli_ctx = ctx.obj
    if not isinstance(cli_ctx, CLIContext):
        raise RuntimeError("CLI context not initialised")
    return cli_ctx


def _ensure_v1_api(_ctx: typer.Context, _command: str) -> None:
    """Legacy command guard - redirects to native implementations."""
    settings = load_settings(strict=False)
    if settings is None:
        typer.echo("Error: configuration not found", err=True)
        raise typer.Exit(code=1) from None


def _build_content_client(
    settings: ConfluenceSettings,
    server: str,
    api_version: str,
):
    http_client = _build_http_client(settings, server)
    if not http_client.supports_api_version(api_version):
        raise VDSClientError(
            f"API version '{api_version}' is not supported for server '{server}'.",
            context={"server": server, "api_version": api_version},
        )
    if api_version == "v1":
        return ContentClient(http_client)
    if api_version == "v2":
        return ContentClientV2(http_client)
    raise VDSClientError(f"Unsupported API version '{api_version}'")


def _record_summary(
    ctx: typer.Context,
    *,
    command: str,
    args: list[str],
    server: str,
    exit_code: int,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    cli_ctx = _get_cli_ctx(ctx)
    summary = RunSummary(
        command=command,
        args=args,
        server=server,
        exit_code=exit_code,
        duration_ms=int((finished_at - started_at).total_seconds() * 1000),
        started_at=started_at,
        finished_at=finished_at,
    )
    if cli_ctx.reports:
        write_reports(summary, base_dir=cli_ctx.report_dir, include_markdown=cli_ctx.markdown)


def _emit_json(payload: object) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if sys.stdout.isatty():
        typer.echo(text)
    else:
        sys.stdout.write(text + "\n")


def _expand_option(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def _content_summary_args(
    *, cql: str | None = None, limit: int | None = None, start: int | None = None, space: str | None = None
) -> list[str]:
    parts: list[str] = []
    if cql is not None:
        parts.append(cql)
    if limit is not None:
        parts.append(f"limit={limit}")
    if start is not None:
        parts.append(f"start={start}")
    if space is not None:
        parts.append(f"space={space}")
    return parts


def _read_text_file(path: Path) -> str:
    if not path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    if path.is_dir():
        raise typer.BadParameter(f"Expected file but found directory: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise typer.BadParameter(f"Unable to read file {path}: {exc}") from exc


def _parse_json_option(value: str | None, option_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON for {option_name}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise typer.BadParameter(f"{option_name} must decode to a JSON object")
    return parsed


def _parent_context(ctx: typer.Context) -> typer.Context:
    return cast("typer.Context", ctx.parent or ctx)


# ---------------------------------------------------------------------------
# Typer callbacks & native commands
# ---------------------------------------------------------------------------


@app.callback()
def main(
    ctx: typer.Context,
    report_dir: Path | None = typer.Option(
        None, help="Directory for run reports (default: <vds-scripts>/reports/confluence_runs)"
    ),
    markdown: bool = typer.Option(True, help="Emit Markdown summaries alongside JSON reports"),
    reports: bool = typer.Option(True, "--reports/--no-reports", help="Persist run reports to disk"),
    json_only: bool = typer.Option(
        False,
        "--json-only",
        help="Emit JSON to stdout only (disables reports and markdown)",
    ),
    api_version: str = typer.Option("v1", "--api-version", "-A", help="Select REST API version (v1 or v2)"),
    structured_logs: bool = typer.Option(
        False, "--structured-logs/--no-structured-logs", help="Emit structured JSON logs to stderr"
    ),
) -> None:
    resolved = report_dir.resolve() if report_dir else _DEFAULT_REPORT_DIR
    version = api_version.lower()
    if version not in {"v1", "v2"}:
        raise typer.BadParameter("api-version must be one of: v1, v2")
    if json_only:
        markdown = False
        reports = False

    # Configure logging/structlog
    if structured_logs or json_only:
        configure_structlog(
            json_logs=structured_logs, quiet=json_only and not structured_logs, cache_logger=structured_logs
        )
    if structured_logs:
        global logger
        logger = structlog.get_logger("confluence_cli")  # type: ignore[assignment]

    ctx.obj = CLIContext(report_dir=resolved, markdown=markdown, api_version=version, reports=reports)


@app.command("templates")
def cmd_templates(
    ctx: typer.Context,
    args: list[str] | None = typer.Argument(
        None, help="Additional arguments for template operations", show_default=False, metavar="ARGS"
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of templates to list"),
    space_key: str | None = typer.Option(None, "--space", "-k", help="Space key filter"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Native Python template management"""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_content_client(settings, server_key, parent_ctx.obj.api_version)

        # Use native Python implementation
        if hasattr(client, "list_templates"):
            result = client.list_templates(space_key=space_key)
        else:
            result = {"templates": [], "message": "Templates API not available for this server"}

        if json_output:
            _emit_json(result)
        else:
            templates_payload = []
            if isinstance(result, dict):
                templates_payload = (
                    result.get("blueprints")
                    or result.get("templates")
                    or result.get("results")
                    or result.get("contentTemplates")
                    or []
                )
            elif isinstance(result, list):
                templates_payload = result

            count = len(templates_payload)
            typer.echo(f"Found {count} templates:")
            for template in templates_payload[:limit]:
                if isinstance(template, dict):
                    name = template.get("name", "Unknown")
                    template_id = template.get("templateId") or template.get("id") or template.get("uuid") or "Unknown"
                else:
                    name = str(template)
                    template_id = "Unknown"
                typer.echo(f"  - {name} (ID: {template_id})")

        exit_code = 0
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="templates",
            args=args or [],
            server=server_key,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )

        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None

    except Exception as exc:
        logger.exception("templates_command_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


@app.command("batch")
def cmd_batch(
    _ctx: typer.Context,
    _args: list[str] | None = typer.Argument(
        None, help="Use 'confluence content batch --help' for available subcommands", show_default=False, metavar="ARGS"
    ),
    _server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Legacy batch command - use 'confluence content batch' subcommands instead."""
    typer.echo("Error: The 'batch' command is deprecated. Use 'confluence content batch' subcommands:", err=True)
    typer.echo("  confluence content batch scan --cql '<query>' [options]", err=True)
    typer.echo("  confluence content batch snapshot --cql '<query>' [options]", err=True)
    raise typer.Exit(code=1) from None


@app.command("webhooks")
def cmd_webhooks(
    ctx: typer.Context,
    args: list[str] | None = typer.Argument(
        None, help="Additional arguments for webhook operations", show_default=False, metavar="ARGS"
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    list_webhooks: bool = typer.Option(False, "--list", "-l", help="List existing webhooks"),
    create_name: str | None = typer.Option(None, "--name", "-n", help="Webhook name"),
    create_url: str | None = typer.Option(None, "--url", "-u", help="Webhook URL"),
    create_event: str | None = typer.Option(None, "--event", "-e", help="Event type"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Native Python webhook management"""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)

    server_key = "internal"
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        webhook_client = WebhookClient(_build_http_client(settings, server_key))

        if list_webhooks or (not create_name and not create_url and not create_event):
            # List webhooks
            result = webhook_client.list()
            if json_output or not sys.stdout.isatty():
                _emit_json(result)
            else:
                result_payload = result if isinstance(result, dict) else {"webhooks": result}
                webhooks_raw = result_payload.get("webhooks", [])
                webhooks = (
                    [item for item in webhooks_raw if isinstance(item, dict)] if isinstance(webhooks_raw, list) else []
                )
                count = len(webhooks)
                typer.echo(f"Found {count} webhooks:")
                for webhook in webhooks:
                    name = webhook.get("name", "Unknown")
                    url = webhook.get("url", "Unknown")
                    events = webhook.get("events", [])
                    typer.echo(f"  - {name}: {url} (events: {', '.join(events)})")

        elif create_name and create_url and create_event:
            # Create webhook
            result = webhook_client.create(name=create_name, url=create_url, events=[create_event])
            if json_output or not sys.stdout.isatty():
                _emit_json(result)
            else:
                webhook_id = result.get("id", "Unknown")
                typer.echo(f"Created webhook '{create_name}' with ID: {webhook_id}")

        else:
            typer.echo(
                "Error: Either use --list to list webhooks or provide --name, --url, and --event to create", err=True
            )
            raise typer.Exit(code=1) from None

        exit_code = 0
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="webhooks",
            args=args or [],
            server=server_key,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )

        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None

    except Exception as exc:
        logger.exception("webhooks_command_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


@app.command("search")
def cmd_search(
    ctx: typer.Context,
    args: list[str] | None = typer.Argument(
        None, help="Additional arguments for CQL search", show_default=False, metavar="ARGS"
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    cql: str = typer.Option(..., "--cql", "-q", help="CQL query string"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of results"),
    start: int = typer.Option(0, "--start", help="Pagination start"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions"),
    excerpt: str | None = typer.Option(None, "--excerpt", help="Excerpt strategy (e.g., 'highlighted', 'indexed')"),
    advanced: bool = typer.Option(False, "--advanced", help="Use advanced CQL search with additional options"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Native Python CQL search. Use --advanced for additional options like excerpt."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    server_key = "internal"

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_content_client(settings, server_key, parent_ctx.obj.api_version)

        # Use native Python implementation
        expand_list = _expand_option(expand) if expand else None
        if advanced or excerpt:
            result = client.cql_advanced(cql, limit=limit, start=start, expand=expand_list, excerpt=excerpt)
        else:
            result = client.search_cql(cql, limit=limit, start=start, expand=expand_list)

        if json_output or not sys.stdout.isatty():
            _emit_json(result)
        else:
            results = result.get("results", [])
            count = len(results)
            total = result.get("size", 0)
            typer.echo(f"Found {count} of {total} results for CQL: {cql}")
            for item in results:
                title = item.get("title", "Unknown")
                page_id = item.get("id", "Unknown")
                space = item.get("space", {}).get("key", "Unknown")
                typer.echo(f"  - {title} (ID: {page_id}, Space: {space})")

        exit_code = 0
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="search",
            args=args or [],
            server=server_key,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )

        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None

    except Exception as exc:
        logger.exception("search_command_failed: %s", exc)


@content_app.command("child-pages")
def cmd_child_pages(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Parent page ID"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Get child pages using the direct API endpoint (faster than CQL)."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    server_key = "internal"

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_content_client(settings, server_key, parent_ctx.obj.api_version)
        expand_list = _expand_option(expand)

        results = client.get_child_pages(page_id, expand=expand_list)

        if json_output or not sys.stdout.isatty():
            _emit_json(results)
        else:
            count = len(results)
            typer.echo(f"Found {count} child pages for {page_id}:")
            for item in results:
                title = item.get("title", "Unknown")
                child_id = item.get("id", "Unknown")
                typer.echo(f"  - {title} (ID: {child_id})")

    except Exception as exc:
        exit_code = 1
        logger.exception("child_pages_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="child-pages",
            args=[page_id],
            server=server_key if "server_key" in locals() else "internal",
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("search-by-space-type")
def cmd_search_by_space_type(
    ctx: typer.Context,
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    space_key: str | None = typer.Option(None, "--space", help="Space key to filter by"),
    content_type: str | None = typer.Option(None, "--type", help="Content type (e.g., 'page', 'blogpost', 'comment')"),
    limit: int = typer.Option(25, "--limit", "-l", help="Number of results"),
    start: int = typer.Option(0, "--start", help="Pagination start"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Search by space and/or content type (helper that builds CQL automatically)."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    server_key = "internal"

    try:
        if not space_key and not content_type:
            raise typer.BadParameter("At least one of --space or --type must be provided")

        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_content_client(settings, server_key, parent_ctx.obj.api_version)

        expand_list = _expand_option(expand) if expand else None
        result = client.search_by_space_and_type(
            space_key=space_key,
            content_type=content_type,
            limit=limit,
            start=start,
            expand=expand_list,
        )

        if json_output or not sys.stdout.isatty():
            _emit_json(result)
        else:
            results = result.get("results", [])
            count = len(results)
            total = result.get("size", 0)
            typer.echo(f"Found {count} of {total} results")
            for item in results:
                title = item.get("title", "Unknown")
                page_id = item.get("id", "Unknown")
                space = item.get("space", {}).get("key", "Unknown")
                item_type = item.get("type", "Unknown")
                typer.echo(f"  - {title} (ID: {page_id}, Space: {space}, Type: {item_type})")

        exit_code = 0
    except (typer.BadParameter, Exception) as exc:
        exit_code = 1
        logger.exception("search_by_space_type_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        args_list: list[str] = []
        if space_key:
            args_list.append(f"space={space_key}")
        if content_type:
            args_list.append(f"type={content_type}")
        _record_summary(
            parent_ctx,
            command="search-by-space-type",
            args=args_list,
            server=server_key,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("attachments")
def cmd_attachments(
    ctx: typer.Context,
    args: list[str] | None = typer.Argument(
        None, help="Additional arguments for attachment operations", show_default=False, metavar="ARGS"
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    page_id: str | None = typer.Option(None, "--page", "-p", help="Page ID for attachments"),
    list_attachments: bool = typer.Option(False, "--list", "-l", help="List attachments for page"),
    upload_file: str | None = typer.Option(None, "--upload", "-f", help="File to upload"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Upload comment"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Native Python attachment management"""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_content_client(settings, server_key, parent_ctx.obj.api_version)

        if list_attachments or (page_id and not upload_file):
            # List attachments
            if not page_id:
                typer.echo("Error: --page ID required for listing attachments", err=True)
                raise typer.Exit(code=1) from None

            result = client.list_attachments(page_id)
            if json_output or not sys.stdout.isatty():
                _emit_json(result)
            else:
                attachments = result.get("results", [])
                count = len(attachments)
                typer.echo(f"Found {count} attachments for page {page_id}:")
                for attachment in attachments:
                    name = attachment.get("title", "Unknown")
                    size = attachment.get("size", 0)
                    typer.echo(f"  - {name} ({size} bytes)")

        elif upload_file and page_id:
            # Upload attachment
            file_path = Path(upload_file)
            if not file_path.exists():
                typer.echo(f"Error: File not found: {upload_file}", err=True)
                raise typer.Exit(code=1) from None

            result = client.upload_attachment(page_id, file_path, comment=comment)
            if json_output or not sys.stdout.isatty():
                _emit_json(result)
            else:
                attachment_id = result.get("id", "Unknown")
                typer.echo(f"Uploaded attachment '{file_path.name}' with ID: {attachment_id}")

        else:
            typer.echo("Error: Either use --list with --page or provide --page and --upload", err=True)
            raise typer.Exit(code=1) from None

        exit_code = 0
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="attachments",
            args=args or [],
            server=server_key,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )

        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None

    except Exception as exc:
        logger.exception("attachments_command_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


@app.command("space-permissions")
def cmd_space_permissions(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: get, set, remove"),
    space_key: str = typer.Option(..., "--space-key", "-k", help="Confluence space key"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    user_key: str | None = typer.Option(None, "--user", "-u", help="User key for user-targeted operations"),
    group_name: str | None = typer.Option(None, "--group", "-g", help="Group name for group-targeted operations"),
    anonymous: bool = typer.Option(False, "--anonymous", help="Target anonymous permissions"),
    operations: list[str] = typer.Option(
        [],
        "--operation",
        "-o",
        help="Space permission operation key (repeatable, e.g., administer, read)",
    ),
    permissions_file: Path | None = typer.Option(
        None,
        "--permissions-file",
        help="JSON object/array with bulk permission definitions (target.type: user|group|anonymous, operations: [...])",
    ),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Manage Confluence space permissions."""

    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        resolved_operations = operations or None
        args_summary = [
            action,
            f"space={space_key}",
            f"user={user_key}",
            f"group={group_name}",
            f"anonymous={anonymous}",
            f"operations={operations}",
            f"permissions_file={permissions_file}",
        ]

        if action == "get":
            result = client.get_space_permissions(space_key)
            result_payload = {"space": space_key, "permissions": result}

        elif action == "set":
            if not yes:
                raise typer.BadParameter("--yes required for write operations")

            targets = [bool(user_key), bool(group_name), anonymous, bool(permissions_file)]
            if sum(1 for flag in targets if flag) != 1:
                raise typer.BadParameter(
                    "Provide exactly one of --user, --group, --anonymous, or --permissions-file for set action"
                )

            if permissions_file:
                file_content = _read_text_file(permissions_file)
                try:
                    parsed = json.loads(file_content)
                except json.JSONDecodeError as exc:
                    raise typer.BadParameter(f"Invalid JSON in permissions file: {exc}") from exc

                if isinstance(parsed, dict):
                    items: list[dict[str, Any]] = [parsed]
                elif isinstance(parsed, list):
                    if not all(isinstance(item, dict) for item in parsed):
                        raise typer.BadParameter("--permissions-file list entries must be JSON objects")
                    items = parsed  # type: ignore[assignment]
                else:
                    raise typer.BadParameter("--permissions-file must contain a JSON object or array")

                result = client.set_permissions_to_multiple_items_for_space(space_key, items)
                result_payload = {"space": space_key, "bulk": True, "items_processed": len(items), "result": result}

            elif user_key:
                if not resolved_operations:
                    raise typer.BadParameter("At least one --operation required when setting user permissions")
                result = client.set_permissions_to_user_for_space(
                    space_key,
                    user_key,
                    operations=resolved_operations,
                )
                result_payload = {
                    "space": space_key,
                    "target": {"type": "user", "key": user_key},
                    "operations": resolved_operations,
                    "result": result,
                }

            elif group_name:
                if not resolved_operations:
                    raise typer.BadParameter("At least one --operation required when setting group permissions")
                result = client.set_permissions_to_group_for_space(
                    space_key,
                    group_name,
                    operations=resolved_operations,
                )
                result_payload = {
                    "space": space_key,
                    "target": {"type": "group", "name": group_name},
                    "operations": resolved_operations,
                    "result": result,
                }

            elif anonymous:
                if not resolved_operations:
                    raise typer.BadParameter("At least one --operation required when setting anonymous permissions")
                result = client.set_permissions_to_anonymous_for_space(
                    space_key,
                    operations=resolved_operations,
                )
                result_payload = {
                    "space": space_key,
                    "target": {"type": "anonymous"},
                    "operations": resolved_operations,
                    "result": result,
                }

        elif action == "remove":
            if not yes:
                raise typer.BadParameter("--yes required for write operations")

            targets = [bool(user_key), bool(group_name), anonymous]
            if sum(1 for flag in targets if flag) != 1:
                raise typer.BadParameter("Provide exactly one of --user, --group, or --anonymous for remove action")

            if user_key:
                result = client.remove_permissions_from_user_for_space(space_key, user_key)
                result_payload = {
                    "space": space_key,
                    "target": {"type": "user", "key": user_key},
                    "result": result,
                }

            elif group_name:
                result = client.remove_permissions_from_group_for_space(space_key, group_name)
                result_payload = {
                    "space": space_key,
                    "target": {"type": "group", "name": group_name},
                    "result": result,
                }

            elif anonymous:
                result = client.remove_permissions_from_anonymous_for_space(space_key)
                result_payload = {
                    "space": space_key,
                    "target": {"type": "anonymous"},
                    "result": result,
                }

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("space_permissions_command_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("space_permissions_command_unexpected")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="space-permissions",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("space-management")
def cmd_space_management(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: archive, trash-list, trash-remove"),
    space_key: str = typer.Option(..., "--space-key", "-k", help="Confluence space key"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    cursor: str | None = typer.Option(None, "--cursor", help="Pagination cursor for trash-list"),
    limit: int = typer.Option(50, "--limit", help="Limit for trash-list (max 100)"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions for trash-list"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Manage Confluence space lifecycle operations."""

    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        if limit < 1 or limit > 100:
            raise typer.BadParameter("--limit must be between 1 and 100")

        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        expand_value = expand if expand else None
        args_summary = [
            action,
            f"space={space_key}",
            f"cursor={cursor}",
            f"limit={limit}",
            f"expand={expand_value}",
        ]

        if action == "archive":
            if not yes:
                raise typer.BadParameter("--yes required for archive")
            result = client.archive_space(space_key)
            result_payload = {"space": space_key, "action": "archive", "result": result}

        elif action == "trash-list":
            result = client.get_trashed_contents_by_space(
                space_key,
                cursor=cursor,
                expand=expand_value,
                limit=limit,
            )
            result_payload = {
                "space": space_key,
                "action": "trash-list",
                "result": result,
            }

        elif action == "trash-remove":
            if not yes:
                raise typer.BadParameter("--yes required for trash-remove")
            result = client.remove_trashed_contents_by_space(space_key)
            result_payload = {"space": space_key, "action": "trash-remove", "result": result}

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("space_management_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("space_management_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="space-management",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("group")
def cmd_group(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: list, members"),
    group_name: str | None = typer.Option(None, "--group", "-g", help="Group name (for members)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    start: int = typer.Option(0, "--start", help="Start index for pagination"),
    limit: int = typer.Option(1000, "--limit", help="Limit for pagination (max 1000)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Manage Confluence groups."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        if limit < 1 or limit > 1000:
            raise typer.BadParameter("--limit must be between 1 and 1000")

        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        args_summary = [action, f"start={start}", f"limit={limit}"]

        if action == "list":
            result = client.get_all_groups(start=start, limit=limit)
            result_payload = {"count": len(result), "groups": result}

        elif action == "members":
            if not group_name:
                raise typer.BadParameter("--group required for members action")
            args_summary.append(f"group={group_name}")
            result = client.get_group_members(group_name, start=start, limit=limit)
            result_payload = {"group": group_name, "count": len(result), "members": result}

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("group_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("group_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="group",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("user")
def cmd_user(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: get, password, group-add, group-remove"),
    username: str | None = typer.Option(None, "--username", "-u", help="Username"),
    userkey: str | None = typer.Option(None, "--userkey", help="User key"),
    group_name: str | None = typer.Option(None, "--group", "-g", help="Group name (for group-add/group-remove)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    expand: str | None = typer.Option(None, "--expand", help="Comma-separated fields to expand (for get)"),
    new_password: str | None = typer.Option(None, "--new-password", help="New password (for password)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Manage Confluence users."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        args_summary = [action]

        if action == "get":
            if not username and not userkey:
                raise typer.BadParameter("Provide --username or --userkey for get action")
            if username and userkey:
                raise typer.BadParameter("Provide either --username or --userkey, not both")
            expand_value = expand if expand else None
            args_summary.append(f"username={username}" if username else f"userkey={userkey}")
            if expand_value:
                args_summary.append(f"expand={expand_value}")

            if username:
                result = client.get_user_details_by_username(username, expand=expand_value)
            else:
                assert userkey is not None
                result = client.get_user_details_by_userkey(userkey, expand=expand_value)
            result_payload = {"user": result}

        elif action == "password":
            if not yes:
                raise typer.BadParameter("--yes required for password change")
            if not username:
                raise typer.BadParameter("--username required for password action")
            if not new_password:
                raise typer.BadParameter("--new-password required for password action")
            args_summary.append(f"username={username}")
            client.change_user_password(username, new_password)
            result_payload = {"username": username, "status": "password_changed"}

        elif action == "group-add":
            if not yes:
                raise typer.BadParameter("--yes required for group-add")
            if not username:
                raise typer.BadParameter("--username required for group-add")
            if not group_name:
                raise typer.BadParameter("--group required for group-add")
            args_summary.append(f"username={username}")
            args_summary.append(f"group={group_name}")
            client.add_user_to_group(username, group_name)
            result_payload = {"username": username, "group": group_name, "status": "added"}

        elif action == "group-remove":
            if not yes:
                raise typer.BadParameter("--yes required for group-remove")
            if not username:
                raise typer.BadParameter("--username required for group-remove")
            if not group_name:
                raise typer.BadParameter("--group required for group-remove")
            args_summary.append(f"username={username}")
            args_summary.append(f"group={group_name}")
            client.remove_user_from_group(username, group_name)
            result_payload = {"username": username, "group": group_name, "status": "removed"}

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("user_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("user_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="user",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("export")
def cmd_export(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: page, space"),
    page_id: str | None = typer.Option(None, "--page-id", help="Page ID (for page)"),
    space_key: str | None = typer.Option(None, "--space-key", "-k", help="Space key (for space)"),
    export_type: str | None = typer.Option(None, "--export-type", help="Export type: pdf, html, xml (for space)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path (for page PDF)"),
    api_version: str | None = typer.Option(
        None, "--api-version", help="API version: cloud, server (for page, auto-detected if not specified)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Export Confluence pages or spaces."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        args_summary = [action]

        if action == "page":
            if not page_id:
                raise typer.BadParameter("--page-id required for page action")
            args_summary.append(f"page_id={page_id}")
            if api_version:
                args_summary.append(f"api_version={api_version}")

            pdf_bytes = client.export_page(page_id, api_version=api_version)

            if output:
                output.write_bytes(pdf_bytes)
                result_payload = {"page_id": page_id, "output_file": str(output), "size_bytes": len(pdf_bytes)}
                typer.echo(f"Exported page {page_id} to {output} ({len(pdf_bytes)} bytes)")
            else:
                # Write to stdout as binary
                sys.stdout.buffer.write(pdf_bytes)
                result_payload = {"page_id": page_id, "size_bytes": len(pdf_bytes), "format": "pdf"}

        elif action == "space":
            if not space_key:
                raise typer.BadParameter("--space-key required for space action")
            if not export_type:
                raise typer.BadParameter("--export-type required for space action")
            if export_type not in ("pdf", "html", "xml"):
                raise typer.BadParameter("--export-type must be one of: pdf, html, xml")
            args_summary.append(f"space_key={space_key}")
            args_summary.append(f"export_type={export_type}")

            download_url = client.get_space_export(space_key, export_type)
            result_payload = {"space_key": space_key, "export_type": export_type, "download_url": download_url}

            if json_output or not sys.stdout.isatty():
                _emit_json(result_payload)
            else:
                typer.echo(f"Space export URL: {download_url}")

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        # For page action, JSON output only if explicitly requested or output file specified
        if action == "page" and (json_output or output) and json_output:
            _emit_json(result_payload)

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("export_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("export_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="export",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("crawl-tree")
def cmd_crawl_tree(
    ctx: typer.Context,
    root: str = typer.Argument(..., help="Root page reference (numeric ID, ?pageId= URL, or /display/<SPACE>/<Title>)"),
    output_dir: Path = typer.Option(..., "--out", "-o", help="Output directory for downloaded pages/attachments"),
    depth: int = typer.Option(
        3,
        "--depth",
        "--crawl-max-depth",
        min=0,
        max=20,
        help="Recursive child-page crawl depth (0 = only root).",
    ),
    include_attachments: bool = typer.Option(
        True,
        "--include-attachments/--no-include-attachments",
        help="Download attachments for each visited page",
    ),
    emit_corpus: bool = typer.Option(
        False,
        "--emit-corpus/--no-emit-corpus",
        help="Emit `corpus.jsonl` chunked by headings for LLM ingestion",
    ),
    emit_link_graph: bool = typer.Option(
        False,
        "--emit-link-graph/--no-emit-link-graph",
        help="Emit `link-graph.json` (normalized outbound links) for doc↔code alignment",
    ),
    emit_tables: bool = typer.Option(
        False,
        "--emit-tables",
        help="Emit `tables.jsonl` (extracted HTML tables) for downstream analysis",
    ),
    emit_mentions: bool = typer.Option(
        False,
        "--emit-mentions",
        help="Emit `mentions.jsonl` (cross-system refs: Confluence/Jira/Bitbucket/external/email) for downstream analysis",
    ),
    body_format: str = typer.Option(
        "view",
        "--body-format",
        help="Body representation to store/analyze: view|export_view|storage (default: view)",
    ),
    chunk_max_chars: int = typer.Option(
        4000,
        "--chunk-max-chars",
        help="Max characters per corpus chunk (emit-corpus only). Oversized heading chunks are split into ordered subchunks (0 disables splitting).",
    ),
    cache_mode: str = typer.Option(
        "read-write",
        "--cache-mode",
        help="Compatibility cache mode flag (off|read|read-write|refresh) for downstream orchestrators.",
    ),
    cache_ttl_hours: int | None = typer.Option(
        None,
        "--cache-ttl-hours",
        min=1,
        help="Compatibility cache TTL (hours) for downstream orchestrators.",
    ),
    incremental: bool = typer.Option(
        True,
        "--incremental/--no-incremental",
        help="Compatibility incremental mode flag; enables resume semantics by default.",
    ),
    incremental_overlap_minutes: int = typer.Option(
        5,
        "--incremental-overlap-minutes",
        min=0,
        help="Incremental crawl overlap window in minutes for last-modified high-water mark refresh.",
    ),
    full_reconciliation_interval_days: int = typer.Option(
        7,
        "--full-reconciliation-interval-days",
        min=1,
        help="Interval in days for full reconciliation sweep when incremental mode is enabled.",
    ),
    content_root: Path | None = typer.Option(
        None,
        "--content-root",
        help="Compatibility content root for downstream orchestrators (diagnostic metadata only).",
    ),
    project_storage_key: str | None = typer.Option(
        None,
        "--project-storage-key",
        help="Compatibility project storage namespace key (diagnostic metadata only).",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Resume from previous crawl state; skip unchanged pages (TSK-188)",
    ),
    max_nodes: int | None = typer.Option(
        500,
        "--max-nodes",
        "--crawl-max-nodes",
        min=1,
        help="Safety limit: max pages to process before stopping (default: 500).",
    ),
    page_concurrency: int = typer.Option(
        5,
        "--page-concurrency",
        "--crawl-concurrency",
        min=1,
        help="Bounded page fetch concurrency (default: 5).",
    ),
    staged_mode: str = typer.Option(
        "off",
        "--staged-mode",
        "--staged-crawl-mode",
        help="Optional staged crawl mode: off|structure-first (default: off).",
    ),
    rate_limit_budget: int = typer.Option(
        50000,
        "--rate-limit-budget",
        min=100,
        help="Hourly Confluence API points budget used for proactive crawl throttling.",
    ),
    bundle: bool = typer.Option(
        False,
        "--bundle",
        help="Create zip bundle of all artifacts for offline handoff (TSK-189)",
    ),
    manifest_path: Path | None = typer.Option(
        None,
        "--manifest",
        help="Optional manifest file path (default: <out>/crawl_manifest.json)",
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Crawl a Confluence page tree and download content + attachments to disk."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    server_key: str | None = None
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []

    try:
        settings = load_settings(strict=True)
        if server is None:
            inferred = _infer_server_from_root_ref(root, settings)
            if inferred:
                server = inferred
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        body_format = (body_format or "view").strip().lower().replace("-", "_")
        if body_format not in {"view", "export_view", "storage"}:
            raise typer.BadParameter("--body-format must be one of: view, export_view, storage")
        cache_mode = (cache_mode or "read-write").strip().lower()
        if cache_mode not in {"off", "read", "read-write", "refresh"}:
            raise typer.BadParameter("--cache-mode must be one of: off, read, read-write, refresh")
        staged_mode = (staged_mode or "off").strip().lower().replace("-", "_")
        if staged_mode not in {"off", "structure_first"}:
            raise typer.BadParameter("--staged-mode must be one of: off, structure-first")
        if chunk_max_chars < 0:
            raise typer.BadParameter("--chunk-max-chars must be >= 0")
        effective_resume = bool(resume or incremental)

        args_summary = [
            root,
            f"depth={depth}",
            f"out={output_dir!s}",
            f"attachments={include_attachments}",
            f"body_format={body_format}",
            f"chunk_max_chars={chunk_max_chars}",
            f"resume={resume}",
            f"incremental={incremental}",
            f"incremental_overlap_minutes={incremental_overlap_minutes}",
            f"full_reconciliation_interval_days={full_reconciliation_interval_days}",
            f"effective_resume={effective_resume}",
            f"cache_mode={cache_mode}",
            f"cache_ttl_hours={cache_ttl_hours}",
            f"content_root={content_root}",
            f"project_storage_key={project_storage_key}",
            f"max_nodes={max_nodes}",
            f"page_concurrency={page_concurrency}",
            f"staged_mode={staged_mode}",
            f"rate_limit_budget={rate_limit_budget}",
            f"bundle={bundle}",
        ]

        runtime_event_logger = logging.getLogger("confluence_cli.crawl_tree")

        def _runtime_event_sink(event_name: str, payload: dict[str, Any]) -> None:
            runtime_event_logger.info(
                "crawl_tree_runtime_event %s %s",
                event_name,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )

        result_payload = crawl_tree_to_disk(
            http=client,
            root_ref=root,
            output_dir=output_dir,
            options=CrawlOptions(
                max_depth=depth,
                include_attachments=include_attachments,
                emit_corpus=emit_corpus,
                emit_link_graph=emit_link_graph,
                emit_tables=emit_tables,
                emit_mentions=emit_mentions,
                body_format=body_format,
                chunk_max_chars=None if chunk_max_chars == 0 else chunk_max_chars,
                resume=effective_resume,
                max_nodes=max_nodes,
                page_concurrency=page_concurrency,
                staged_mode=staged_mode,
                incremental_cql=incremental,
                incremental_overlap_minutes=incremental_overlap_minutes,
                full_reconciliation_interval_days=full_reconciliation_interval_days,
                rate_limit_budget=rate_limit_budget,
                runtime_event_sink=_runtime_event_sink,
                bundle=bundle,
            ),
            manifest_path=manifest_path,
        )
        result_payload["cache"] = {
            "mode": cache_mode,
            "ttl_hours": cache_ttl_hours,
            "incremental": incremental,
            "incremental_overlap_minutes": incremental_overlap_minutes,
            "full_reconciliation_interval_days": full_reconciliation_interval_days,
            "effective_resume": effective_resume,
            "content_root": str(content_root) if content_root else None,
            "project_storage_key": project_storage_key,
        }

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            root_id = result_payload.get("root_page_id")
            pages = 1 + len(result_payload.get("child_pages") or [])
            atts = len(result_payload.get("attachments") or [])
            resume_state = result_payload.get("resume_state") or {}
            skipped = resume_state.get("skipped_unchanged", 0)
            typer.echo(f"Crawled {pages} page(s), downloaded {atts} attachment(s). Root: {root_id}.")
            if skipped > 0:
                typer.echo(f"Skipped {skipped} unchanged page(s) (resume mode).")
            if max_nodes and not resume_state.get("completed", True):
                typer.echo(f"Stopped at max_nodes={max_nodes}. Use --resume to continue.")
            typer.echo(f"Output: {result_payload.get('out_dir')}")
            if result_payload.get("bundle_path"):
                typer.echo(f"Bundle: {result_payload.get('bundle_path')}")

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("crawl_tree_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("crawl_tree_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="crawl-tree",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("draft")
def cmd_draft(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: get, list, remove"),
    page_id: str | None = typer.Option(None, "--page-id", help="Page ID (for get/remove)"),
    space_key: str | None = typer.Option(None, "--space-key", "-k", help="Space key (for list)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    limit: int = typer.Option(25, "--limit", help="Limit for list (max 100)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (for remove)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Manage Confluence draft pages (Server-only)."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        if limit < 1 or limit > 100:
            raise typer.BadParameter("--limit must be between 1 and 100")

        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        args_summary = [action]

        if action == "get":
            if not page_id:
                raise typer.BadParameter("--page-id required for get action")
            args_summary.append(f"page_id={page_id}")
            result = client.get_draft_page_by_id(page_id)
            result_payload = {"draft_page": result}

        elif action == "list":
            if not space_key:
                raise typer.BadParameter("--space-key required for list action")
            args_summary.append(f"space_key={space_key}")
            args_summary.append(f"limit={limit}")
            result = client.get_all_draft_pages_from_space(space_key, limit=limit)
            result_payload = {"space": space_key, "count": len(result), "drafts": result}

        elif action == "remove":
            if not yes:
                raise typer.BadParameter("--yes required for remove action")
            if not page_id:
                raise typer.BadParameter("--page-id required for remove action")
            args_summary.append(f"page_id={page_id}")
            client.remove_page_as_draft(page_id)
            result_payload = {"page_id": page_id, "status": "removed"}

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("draft_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("draft_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="draft",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("history")
def cmd_history(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: get, version, remove"),
    page_id: str | None = typer.Option(None, "--page-id", help="Page ID"),
    version: int | None = typer.Option(None, "--version", help="Version number (for version/remove)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (for remove)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Manage Confluence page history and versioning."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        args_summary = [action]

        if action == "get":
            if not page_id:
                raise typer.BadParameter("--page-id required for get action")
            args_summary.append(f"page_id={page_id}")
            result = client.history(page_id)
            result_payload = {"page_id": page_id, "history": result}

        elif action == "version":
            if not page_id:
                raise typer.BadParameter("--page-id required for version action")
            if version is None:
                raise typer.BadParameter("--version required for version action")
            args_summary.append(f"page_id={page_id}")
            args_summary.append(f"version={version}")
            result = client.get_content_history_by_version_number(page_id, version)
            result_payload = {"page_id": page_id, "version": version, "content": result}

        elif action == "remove":
            if not yes:
                raise typer.BadParameter("--yes required for remove action (experimental feature)")
            if not page_id:
                raise typer.BadParameter("--page-id required for remove action")
            if version is None:
                raise typer.BadParameter("--version required for remove action")
            args_summary.append(f"page_id={page_id}")
            args_summary.append(f"version={version}")
            typer.echo("Warning: remove_content_history is an experimental feature", err=True)
            client.remove_content_history(page_id, version)
            result_payload = {"page_id": page_id, "version": version, "status": "removed"}

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("history_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("history_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="history",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("cache")
def cmd_cache(
    ctx: typer.Context,
    action: str = typer.Argument(..., help="Action: statistics, flush, size"),
    cache_name: str | None = typer.Option(None, "--cache-name", help="Cache name (for flush)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation (for flush)"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Manage Confluence cache (Server-only)."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    args_summary: list[str] = []
    server_key: str | None = None
    settings: ConfluenceSettings | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        args_summary = [action]

        if action == "statistics":
            result = client.get_cache_statistics()
            result_payload = {"cache_statistics": result}
        elif action == "flush":
            if not yes:
                raise typer.BadParameter("Refusing to flush cache without --yes")
            if cache_name:
                args_summary.append(f"cache_name={cache_name}")
            client.flush_cache(cache_name=cache_name)
            result_payload = {"status": "success", "cache_flushed": cache_name or "all"}
        elif action == "size":
            result = client.get_cache_size()
            result_payload = {"cache_size": result}
        else:
            raise typer.BadParameter(f"Unknown action: {action}")

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("cache_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("cache_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="cache",
            args=args_summary,
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@app.command("get")
def cmd_get(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    expand: str | None = typer.Option(
        None, "--expand", "-e", help="Comma separated expansions (e.g., 'body.storage,version')"
    ),
    format: str | None = typer.Option(None, "--format", "-f", help="Output format (storage|editor|view)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Get Confluence content by page ID."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "get")
    started_at = datetime.now(UTC)
    settings = load_settings(strict=True)
    server_key = _normalise_server(server, settings)

    try:
        client = ContentClientV2(_build_http_client(settings, server_key))
        content = client.get_content(page_id, expand=_expand_option(expand), format=format)

        if content:
            _emit_json(content)
        else:
            typer.echo(f"Content not found: {page_id}", err=True)
            raise typer.Exit(code=1) from None

        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="get",
            args=[page_id],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )

    except Exception as exc:
        logger.exception("get_command_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None


# ---------------------------------------------------------------------------
# Native content commands
# ---------------------------------------------------------------------------


@batch_app.command("scan")
def batch_scan(
    ctx: typer.Context,
    cql: str = typer.Option(..., "--cql", "-q", help="CQL query string"),
    limit: int = typer.Option(25, "--limit", help="Number of results per request"),
    max_results: int | None = typer.Option(None, "--max-results", help="Total results to fetch"),
    start: int = typer.Option(0, "--start", help="Pagination start offset"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "batch.scan")
    started_at = datetime.now(UTC)
    settings = load_settings(strict=True)
    server_key = _normalise_server(server, settings)
    runner = BatchRunner(_build_http_client(settings, server_key), expand=_expand_option(expand))
    results: list[dict[str, Any]] = []
    for item in runner.scan(cql, limit=limit, max_results=max_results, start=start):
        results.append(item)
    metrics = runner.last_metrics
    payload: dict[str, Any] = {
        "cql": cql,
        "count": len(results),
        "limit": limit,
        "maxResults": max_results,
        "start": start,
        "results": results,
    }
    if metrics is not None:
        payload["metrics"] = {
            "requests": metrics.requests,
            "pagesProcessed": metrics.pages_processed,
            "durationSeconds": metrics.duration_seconds,
        }
    if json_output or not sys.stdout.isatty():
        _emit_json(payload)
    else:
        typer.echo(
            f"Scanned {payload['count']} results (requests={payload['metrics']['requests'] if 'metrics' in payload else '?'})"
        )
    finished_at = datetime.now(UTC)
    _record_summary(
        parent_ctx,
        command="batch.scan",
        args=[cql, f"limit={limit}", f"start={start}"],
        server=server_key,
        exit_code=0,
        started_at=started_at,
        finished_at=finished_at,
    )


@batch_app.command("snapshot")
def batch_snapshot(
    ctx: typer.Context,
    cql: str = typer.Option(..., "--cql", "-q", help="CQL query string"),
    limit: int = typer.Option(25, "--limit", help="Number of results per request"),
    max_results: int | None = typer.Option(None, "--max-results", help="Total results to fetch"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "batch.snapshot")
    started_at = datetime.now(UTC)
    settings = load_settings(strict=True)
    server_key = _normalise_server(server, settings)
    runner = BatchRunner(_build_http_client(settings, server_key))
    payload = runner.snapshot(cql, limit=limit, max_results=max_results, expand=_expand_option(expand))
    _emit_json(payload)
    finished_at = datetime.now(UTC)
    _record_summary(
        parent_ctx,
        command="batch.snapshot",
        args=[cql, f"limit={limit}"],
        server=server_key,
        exit_code=0,
        started_at=started_at,
        finished_at=finished_at,
    )


@batch_app.command("poll")
def batch_poll(
    ctx: typer.Context,
    cql: str = typer.Option(..., "--cql", "-q", help="Base CQL query (will be augmented with lastmodified filter)"),
    state_file: Path = typer.Option(..., "--state-file", help="Path to persistent cursor file (JSON)"),
    limit: int = typer.Option(25, "--limit", help="Page size per request"),
    max_results: int | None = typer.Option(None, "--max-results", help="Max results this run"),
    expand: str | None = typer.Option(
        "version", "--expand", help="Comma separated expansions (default includes 'version')"
    ),
    out_jsonl: Path | None = typer.Option(None, "--out-jsonl", help="Write results to JSONL (one object per line)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "batch.poll")
    started_at = datetime.now(UTC)
    server_key = "internal"
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)
        poller = Poller(client)
        expand_list = _expand_option(expand) or ["version"]
        count = poller.poll_once(
            base_cql=cql,
            state_file=state_file,
            limit=limit,
            max_results=max_results,
            expand=expand_list,
            out_jsonl=out_jsonl,
        )
        typer.echo(f"Polled {count} items")
    except Exception as exc:
        logger.exception("batch.poll failed", extra={"cql": cql})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="batch.poll",
            args=[cql, f"limit={limit}", f"out={str(out_jsonl) if out_jsonl else '-'}"],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@webhook_app.command("create")
def webhook_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Webhook name"),
    url: str = typer.Option(..., "--url", help="Destination URL"),
    event: list[str] = typer.Option(["page_created"], "--event", "-e", help="Event identifier"),
    active: bool = typer.Option(True, "--active/--inactive", help="Toggle webhook activation"),
    filters: str | None = typer.Option(None, "--filters", help="JSON object filters"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "webhook.create")
    started_at = datetime.now(UTC)
    settings = load_settings(strict=True)
    server_key = _normalise_server(server, settings)
    client = WebhookClient(_build_http_client(settings, server_key))
    payload = client.create(
        name=name,
        url=url,
        events=event,
        active=active,
        filters=_parse_json_option(filters, "--filters"),
    )
    if json_output:
        _emit_json(payload)
    else:
        typer.echo(f"Created webhook {payload.get('id')}")
    finished_at = datetime.now(UTC)
    _record_summary(
        parent_ctx,
        command="webhook.create",
        args=[name, f"events={len(event)}"],
        server=server_key,
        exit_code=0,
        started_at=started_at,
        finished_at=finished_at,
    )


@webhook_app.command("list")
def webhook_list(
    ctx: typer.Context,
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "webhook.list")
    started_at = datetime.now(UTC)
    settings = load_settings(strict=True)
    server_key = _normalise_server(server, settings)
    client = WebhookClient(_build_http_client(settings, server_key))
    payload = client.list()
    if json_output:
        _emit_json(payload)
    else:
        typer.echo(f"{len(payload)} webhooks")
    finished_at = datetime.now(UTC)
    _record_summary(
        parent_ctx,
        command="webhook.list",
        args=[f"count={len(payload)}"],
        server=server_key,
        exit_code=0,
        started_at=started_at,
        finished_at=finished_at,
    )


@webhook_app.command("delete")
def webhook_delete(
    ctx: typer.Context,
    webhook_id: str = typer.Argument(..., help="Webhook identifier"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "webhook.delete")
    started_at = datetime.now(UTC)
    settings = load_settings(strict=True)
    server_key = _normalise_server(server, settings)
    client = WebhookClient(_build_http_client(settings, server_key))
    client.delete(webhook_id)
    typer.echo(f"Deleted webhook {webhook_id}")
    finished_at = datetime.now(UTC)
    _record_summary(
        parent_ctx,
        command="webhook.delete",
        args=[webhook_id],
        server=server_key,
        exit_code=0,
        started_at=started_at,
        finished_at=finished_at,
    )


@content_app.command("page")
def content_page(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Fetch a Confluence page by ID."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        cli_ctx = _get_cli_ctx(parent_ctx)
        client = _build_content_client(settings, server_key, cli_ctx.api_version)
        expand_list = _expand_option(expand)
        payload = client.get_page(page_id, expand=expand_list)
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.page failed", extra={"page_id": page_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.page",
            args=[page_id],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("search")
def content_search(
    ctx: typer.Context,
    cql: str = typer.Argument(..., help="CQL query string"),
    limit: int = typer.Option(25, "--limit", help="Number of results"),
    start: int = typer.Option(0, "--start", help="Pagination start"),
    expand: str | None = typer.Option(None, "--expand", help="Comma separated expansions"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Search Confluence pages by CQL query."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    server_key: str = ""
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        cli_ctx = _get_cli_ctx(parent_ctx)
        client = _build_content_client(settings, server_key, cli_ctx.api_version)
        expand_list = _expand_option(expand)
        payload = client.search_cql(cql, limit=limit, start=start, expand=expand_list)
        _emit_json(payload)
    except Exception as exc:
        exit_code = 1
        logger.exception("content.search failed", extra={"cql": cql})
        # Provide targeted guidance for CQL auth failures
        from .errors import AuthError  # local import to avoid top-level cycles

        if isinstance(exc, AuthError):
            typer.echo("Error: Authentication failed for CQL search.", err=True)
            typer.echo("Hint: We default to Basic auth (VDS_USERNAME/PASSWORD). If using token, ensure:", err=True)
            typer.echo("  - Token has permission to use CQL (/rest/api/*search)", err=True)
            typer.echo("  - Or set VDS_USERNAME/VDS_PASSWORD to use Basic auth", err=True)
            typer.echo(
                "  - Quick check: curl -u \"$VDS_USERNAME:$VDS_PASSWORD\" 'http://confluence.digital.vn/rest/api/search?cql=type=page&limit=1'",
                err=True,
            )
        else:
            typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.search",
            args=_content_summary_args(cql=cql, limit=limit, start=start),
            server=server_key,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@content_app.command("templates")
def content_templates(
    ctx: typer.Context,
    space_key: str | None = typer.Option(None, "--space", help="Space key"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """List available Confluence page templates."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        cli_ctx = _get_cli_ctx(parent_ctx)
        client = _build_content_client(settings, server_key, cli_ctx.api_version)
        if hasattr(client, "list_templates"):
            payload = client.list_templates(space_key=space_key)
        else:
            payload = {"templates": [], "message": "Templates API not available for this server"}
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.templates failed", extra={"space": space_key})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.templates",
            args=_content_summary_args(space=space_key or "*"),
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("create-page")
def content_create_page(
    ctx: typer.Context,
    space_key: str = typer.Option(..., "--space", "-S", help="Space key to create the page in"),
    title: str = typer.Option(..., "--title", "-t", help="Page title"),
    body_file: Path = typer.Option(
        ..., "--body-file", exists=True, file_okay=True, dir_okay=False, help="Path to storage-format body"
    ),
    parent_id: str | None = typer.Option(None, "--parent", help="Ancestor page id"),
    representation: str = typer.Option(
        "storage", "--representation", help="Content representation (storage, wiki, view)"
    ),
    status: str = typer.Option("current", "--status", help="Target page status (current, draft)"),
    notify_watchers: bool = typer.Option(
        False, "--notify-watchers/--no-notify-watchers", help="Send notifications to watchers"
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Create a new Confluence page."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.create-page")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        body = _read_text_file(body_file)
        payload = client.create_page(
            space_key=space_key,
            title=title,
            body=body,
            parent_id=parent_id,
            representation=representation,
            status=status,
            notify_watchers=notify_watchers,
        )
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.create-page failed", extra={"space": space_key, "title": title})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.create-page",
            args=[f"space={space_key}", f"title={title}"],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("update-page")
def content_update_page(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    title: str | None = typer.Option(None, "--title", help="New page title"),
    body_file: Path | None = typer.Option(
        None, "--body-file", exists=True, file_okay=True, dir_okay=False, help="Path to storage-format body"
    ),
    space_key: str | None = typer.Option(None, "--space", help="Move page to this space"),
    version: int | None = typer.Option(None, "--version", help="Explicit version number"),
    representation: str = typer.Option("storage", "--representation", help="Content representation for --body-file"),
    minor_edit: bool = typer.Option(False, "--minor-edit/--no-minor-edit", help="Mark version as minor edit"),
    message: str | None = typer.Option(None, "--message", help="Version comment"),
    status: str = typer.Option("current", "--status", help="Target page status"),
    notify_watchers: bool = typer.Option(
        False, "--notify-watchers/--no-notify-watchers", help="Send notifications to watchers"
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Update an existing Confluence page."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.update-page")
    if body_file is None and title is None and space_key is None:
        raise typer.BadParameter("Provide at least one of --title, --body-file or --space")
    body = _read_text_file(body_file) if body_file else None
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        payload = client.update_page(
            page_id,
            title=title,
            body=body,
            space_key=space_key,
            representation=representation,
            version=version,
            minor_edit=minor_edit,
            message=message,
            status=status,
            notify_watchers=notify_watchers,
        )
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.update-page failed", extra={"page_id": page_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        args = [page_id]
        if version is not None:
            args.append(f"version={version}")
        if title is not None:
            args.append(f"title={title}")
        _record_summary(
            parent_ctx,
            command="content.update-page",
            args=args,
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("delete-page")
def content_delete_page(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    status: str = typer.Option("current", "--status", help="Specify current or draft"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Delete a Confluence page."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.delete-page")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        client.delete_page(page_id, status=status)
        typer.echo(f"Deleted page {page_id} (status={status})")
    except Exception as exc:
        logger.exception("content.delete-page failed", extra={"page_id": page_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.delete-page",
            args=[page_id, f"status={status}"],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("add-attachment")
def content_add_attachment(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    file_path: Path = typer.Option(..., "--file", exists=True, file_okay=True, dir_okay=False, help="File to upload"),
    filename: str | None = typer.Option(None, "--filename", help="Override uploaded filename"),
    content_type: str | None = typer.Option(None, "--content-type", help="MIME type for the attachment"),
    comment: str | None = typer.Option(None, "--comment", help="Attachment comment"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Add an attachment to a Confluence page."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.add-attachment")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        payload = client.upload_attachment(
            page_id,
            str(file_path),
            filename=filename,
            content_type=content_type,
            comment=comment,
        )
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.add-attachment failed", extra={"page_id": page_id, "file": str(file_path)})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.add-attachment",
            args=[page_id, file_path.name],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("download-attachment")
def content_download_attachment(
    ctx: typer.Context,
    attachment_id: str = typer.Argument(..., help="Attachment ID"),
    output_path: Path = typer.Option(
        ..., "--out", "-o", file_okay=True, dir_okay=True, help="Output file path or directory"
    ),
    filename: str | None = typer.Option(None, "--filename", help="Override downloaded filename"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Download a Confluence attachment by ID to a local file."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.download-attachment")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        output = client.download_attachment(attachment_id, output_path, filename=filename)
        _emit_json({"attachment_id": attachment_id, "output_path": str(output)})
    except Exception as exc:
        logger.exception("content.download-attachment failed", extra={"attachment_id": attachment_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.download-attachment",
            args=[attachment_id, str(output_path)],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("add-comment")
def content_add_comment(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    body: str | None = typer.Option(None, "--body", help="Comment body in Confluence storage format"),
    body_file: Path | None = typer.Option(
        None, "--body-file", exists=True, file_okay=True, dir_okay=False, help="Path to file containing comment body"
    ),
    parent_id: str | None = typer.Option(
        None,
        "--parent-id",
        help="Optional parent comment ID to create a threaded reply instead of a top-level comment",
    ),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Add a comment to a Confluence page."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.add-comment")
    started_at = datetime.now(UTC)

    if bool(body) == bool(body_file):
        raise typer.BadParameter("Provide either --body or --body-file")

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        if body is not None:
            comment_body = body
        else:
            assert body_file is not None
            comment_body = _read_text_file(body_file)
        payload = client.add_comment(page_id, comment_body, parent_id=parent_id)
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.add-comment failed", extra={"page_id": page_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.add-comment",
            args=[page_id],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("update-attachment")
def content_update_attachment(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    attachment_id: str = typer.Argument(..., help="Attachment ID"),
    file_path: Path = typer.Option(..., "--file", exists=True, file_okay=True, dir_okay=False, help="Replacement file"),
    filename: str | None = typer.Option(None, "--filename", help="Override uploaded filename"),
    content_type: str | None = typer.Option(None, "--content-type", help="MIME type for the attachment"),
    comment: str | None = typer.Option(None, "--comment", help="Attachment comment"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Update an existing attachment on a Confluence page."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.update-attachment")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        payload = client.update_attachment(
            page_id,
            attachment_id,
            str(file_path),
            filename=filename,
            content_type=content_type,
            comment=comment,
        )
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.update-attachment failed", extra={"page_id": page_id, "attachment_id": attachment_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.update-attachment",
            args=[page_id, attachment_id],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("delete-attachment")
def content_delete_attachment(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    attachment_id: str | None = typer.Argument(None, help="Attachment ID"),
    version: int | None = typer.Option(None, "--version", help="Delete a specific attachment version"),
    filename: str | None = typer.Option(None, "--filename", help="Attachment filename (delete all versions)"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Delete an attachment from a Confluence page."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.delete-attachment")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        if not attachment_id and not filename:
            raise typer.BadParameter("Provide either attachment_id or --filename")

        client = ContentClient(_build_http_client(settings, server_key))
        client.delete_attachment(page_id, attachment_id=attachment_id, version=version, filename=filename)
        target = filename or attachment_id
        typer.echo(f"Deleted attachment {target} from page {page_id}")
    except Exception as exc:
        logger.exception("content.delete-attachment failed", extra={"page_id": page_id, "attachment_id": attachment_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.delete-attachment",
            args=[
                page_id,
                filename or attachment_id or "<unspecified>",
                f"version={version}" if version is not None else "all_versions",
            ],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("ancestors")
def content_ancestors(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Get page ancestors (parent pages)."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    server_key: str | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        result = client.get_page_ancestors(page_id)
        result_payload = {"page_id": page_id, "count": len(result), "ancestors": result}

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("content.ancestors_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("content.ancestors_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="content.ancestors",
            args=[page_id],
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@content_app.command("move")
def content_move(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    target_title: str = typer.Option(..., "--target-title", help="Target page title to move under"),
    position: str = typer.Option("append", "--position", help="Position: append, before, after"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    yes: bool = typer.Option(False, "--yes", help="Confirm move operation"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Move page to a new location."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    server_key: str | None = None

    try:
        if not yes:
            raise typer.BadParameter("--yes required for move operation")
        if position not in ("append", "before", "after"):
            raise typer.BadParameter("--position must be one of: append, before, after")

        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        result = client.move_page(page_id, target_title, position=position)
        result_payload = {"page_id": page_id, "target_title": target_title, "position": position, "result": result}

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("content.move_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("content.move_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="content.move",
            args=[page_id, f"target={target_title}", f"position={position}"],
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@content_app.command("tables")
def content_tables(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Extract tables from page."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    server_key: str | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        result = client.get_tables_from_page(page_id)
        result_payload = {"page_id": page_id, "count": len(result), "tables": result}

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("content.tables_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("content.tables_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="content.tables",
            args=[page_id],
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@content_app.command("regex")
def content_regex(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    pattern: str = typer.Option(..., "--pattern", help="Regex pattern to match"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Extract regex matches from page."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    server_key: str | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        result = client.scrap_regex_from_page(page_id, pattern)
        result_payload = {"page_id": page_id, "pattern": pattern, "count": len(result), "matches": result}

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("content.regex_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("content.regex_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="content.regex",
            args=[page_id, f"pattern={pattern}"],
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@content_app.command("restrictions")
def content_restrictions(
    ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON payload"),
) -> None:
    """Get all restrictions for content."""
    parent_ctx = _parent_context(ctx)
    started_at = datetime.now(UTC)
    exit_code = 0
    result_payload: dict[str, Any] = {}
    server_key: str | None = None

    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = _build_http_client(settings, server_key)

        result = client.get_all_restrictions_for_content(page_id)
        result_payload = {"page_id": page_id, "restrictions": result}

        if json_output or not sys.stdout.isatty():
            _emit_json(result_payload)
        else:
            typer.echo(json.dumps(result_payload, indent=2, sort_keys=True))

    except (VDSClientError, typer.BadParameter) as exc:
        exit_code = 1
        logger.exception("content.restrictions_failed: %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    except Exception as exc:  # pragma: no cover - unexpected errors
        exit_code = 1
        logger.exception("content.restrictions_unexpected_error")
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        server_label = server_key or (server.lower() if server else "internal")
        _record_summary(
            parent_ctx,
            command="content.restrictions",
            args=[page_id],
            server=server_label,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if exit_code != 0:
            raise typer.Exit(code=exit_code) from None


@content_app.command("create-template")
def content_create_template(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Template name"),
    body_file: Path = typer.Option(
        ..., "--body-file", exists=True, file_okay=True, dir_okay=False, help="Path to storage-format body"
    ),
    template_type: str = typer.Option("page", "--type", help="Template type (page or other supported types)"),
    space_key: str | None = typer.Option(None, "--space", help="Limit template to space key"),
    description: str | None = typer.Option(None, "--description", help="Template description"),
    representation: str = typer.Option("storage", "--representation", help="Content representation"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Create a new Confluence page template."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.create-template")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        body = _read_text_file(body_file)
        payload = client.create_template(
            name=name,
            body=body,
            template_type=template_type,
            space_key=space_key,
            description=description,
            representation=representation,
        )
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.create-template failed", extra={"name": name, "space": space_key})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        args = [name, f"type={template_type}"]
        if space_key:
            args.append(f"space={space_key}")
        _record_summary(
            parent_ctx,
            command="content.create-template",
            args=args,
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("update-template")
def content_update_template(
    ctx: typer.Context,
    template_id: str = typer.Argument(..., help="Template identifier"),
    name: str | None = typer.Option(None, "--name", help="Template name"),
    body_file: Path | None = typer.Option(
        None, "--body-file", exists=True, file_okay=True, dir_okay=False, help="Path to storage-format body"
    ),
    description: str | None = typer.Option(None, "--description", help="Template description"),
    template_type: str | None = typer.Option(None, "--type", help="Template type"),
    representation: str = typer.Option("storage", "--representation", help="Representation for --body-file"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Update an existing Confluence page template."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.update-template")
    if name is None and body_file is None and description is None and template_type is None:
        raise typer.BadParameter("Provide at least one of --name, --body-file, --description, or --type")
    body = _read_text_file(body_file) if body_file else None
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        payload = client.update_template(
            template_id,
            name=name,
            body=body,
            description=description,
            representation=representation,
            template_type=template_type,
        )
        _emit_json(payload)
    except Exception as exc:
        logger.exception("content.update-template failed", extra={"template_id": template_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        args = [template_id]
        if name:
            args.append(f"name={name}")
        _record_summary(
            parent_ctx,
            command="content.update-template",
            args=args,
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


@content_app.command("delete-template")
def content_delete_template(
    ctx: typer.Context,
    template_id: str = typer.Argument(..., help="Template identifier"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
) -> None:
    """Delete a Confluence page template."""
    parent_ctx = _parent_context(ctx)
    _ensure_v1_api(parent_ctx, "content.delete-template")
    started_at = datetime.now(UTC)
    try:
        settings = load_settings(strict=True)
        server_key = _normalise_server(server, settings)
        client = ContentClient(_build_http_client(settings, server_key))
        client.delete_template(template_id)
        typer.echo(f"Deleted template {template_id}")
    except Exception as exc:
        logger.exception("content.delete-template failed", extra={"template_id": template_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.delete-template",
            args=[template_id],
            server=server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@app.command("env")
def cmd_env(_ctx: typer.Context) -> None:
    """Show Confluence connection environment variable status."""
    settings = load_settings(strict=False)
    typer.echo(
        f"Default server: {settings.default_server}\n"
        f"Internal URL: {settings.internal_url}\n"
        f"External URL: {settings.external_url}\n"
        f"Internal token set: {bool(settings.internal_token)}\n"
        f"External token set: {bool(settings.external_token)}"
    )


# ---------------------------------------------------------------------------
# Sync Commands (delegate to standalone scripts)
# ---------------------------------------------------------------------------

sync_app = typer.Typer(help="Sync attachments from local files to Confluence")
app.add_typer(sync_app, name="sync")


@sync_app.command("pngs")
def cmd_sync_pngs(
    _ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    directory: Path = typer.Option(..., "--dir", "-d", help="Directory containing PNG files"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    pattern: str | None = typer.Option(None, "--pattern", "-p", help="Filter PNG files by pattern"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Comment for attachment updates"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-confirm without prompting"),
) -> None:
    """Sync local PNG files with Confluence page attachments."""
    import subprocess
    import sys

    # Project root for confluence_orchestrator (where sync scripts live)
    script_path = Path(__file__).resolve().parents[2] / "sync_png_attachments.py"
    if not script_path.exists():
        typer.echo(f"Error: Sync script not found: {script_path}", err=True)
        raise typer.Exit(code=1) from None

    cmd = [
        sys.executable,
        str(script_path),
        "sync",
        page_id,
        "--dir",
        str(directory),
    ]
    if server:
        cmd.extend(["--server", server])
    if pattern:
        cmd.extend(["--pattern", pattern])
    if dry_run:
        cmd.append("--dry-run")
    if comment:
        cmd.extend(["--comment", comment])
    if yes:
        cmd.append("--yes")

    result = subprocess.run(cmd, check=False)
    raise typer.Exit(code=result.returncode) from None


@sync_app.command("pdfs")
def cmd_sync_pdfs(
    _ctx: typer.Context,
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    directory: Path = typer.Option(..., "--dir", "-d", help="Directory containing PDF files"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    pattern: str | None = typer.Option(None, "--pattern", "-p", help="Filter PDF files by pattern"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Comment for attachment updates"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-confirm without prompting"),
) -> None:
    """Sync local PDF files with Confluence page attachments.

    This command delegates to the standalone sync_pdfs_to_confluence.py script.
    For markdown-to-PDF sync, use the PDF orchestrator: vds-cli pdf -- md2pdf
    """
    import subprocess
    import sys

    # Look for script in confluence_orchestrator/ directory (standard location)
    script_path = Path(__file__).resolve().parents[2] / "sync_pdfs_to_confluence.py"

    if not script_path.exists():
        typer.echo(
            f"Error: Sync script not found: {script_path}\n"
            "Note: Ensure sync_pdfs_to_confluence.py exists in confluence_orchestrator/ directory.",
            err=True,
        )
        raise typer.Exit(code=1) from None

    cmd = [
        sys.executable,
        str(script_path),
        "sync",
        page_id,
        "--dir",
        str(directory),
    ]
    if server:
        cmd.extend(["--server", server])
    if pattern:
        cmd.extend(["--pattern", pattern])
    if dry_run:
        cmd.append("--dry-run")
    if comment:
        cmd.extend(["--comment", comment])
    if yes:
        cmd.append("--yes")

    result = subprocess.run(cmd, check=False)
    raise typer.Exit(code=result.returncode) from None


# ---------------------------------------------------------------------------
# content copy-tree
# ---------------------------------------------------------------------------


@content_app.command("copy-tree")
def content_copy_tree(
    ctx: typer.Context,
    source_page_id: str = typer.Argument(..., help="Source root page ID"),
    target_page_id: str = typer.Option(..., "--target-page-id", help="Target root page ID"),
    source_server: str = typer.Option(
        "external", "--source-server", help="Source Confluence server (internal|external)"
    ),
    target_server: str = typer.Option(
        "internal", "--target-server", help="Target Confluence server (internal|external)"
    ),
    source_space: str | None = typer.Option(
        None, "--source-space", help="Source space key (auto-detected from source page if omitted)"
    ),
    target_space: str = typer.Option(..., "--target-space", help="Target space key"),
    skip_attachments: bool = typer.Option(False, "--skip-attachments", help="Skip attachment copy"),
    skip_labels: bool = typer.Option(False, "--skip-labels", help="Skip label copy"),
    skip_link_remap: bool = typer.Option(False, "--skip-link-remap", help="Skip link remapping"),
    max_depth: int | None = typer.Option(None, "--max-depth", help="Max BFS depth (0=root only; max: 100)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report what would be copied without writing"),
) -> None:
    """Copy a Confluence page tree from one space/server to another."""
    parent_ctx = _parent_context(ctx)
    if max_depth is not None and max_depth > 100:
        raise typer.BadParameter("--max-depth cannot exceed 100 (NFR-05)")
    started_at = datetime.now(UTC)
    source_server_key: str = ""
    try:
        settings = load_settings(strict=True)
        source_server_key = _normalise_server(source_server, settings)
        target_server_key = _normalise_server(target_server, settings)
        source_client = ContentClient(_build_http_client(settings, source_server_key))
        target_client = ContentClient(_build_http_client(settings, target_server_key))
        if source_space:
            resolved_source_space = source_space
        else:
            src_page = source_client.get_page(source_page_id, expand=["space"])
            space_info = src_page.get("space")
            if not isinstance(space_info, dict) or not space_info.get("key"):
                raise VDSClientError(
                    f"Cannot determine source space key from page {source_page_id}. Pass --source-space explicitly.",
                    context={"source_page_id": source_page_id},
                )
            resolved_source_space = str(space_info["key"])
        options = CopyOptions(
            skip_attachments=skip_attachments,
            skip_labels=skip_labels,
            skip_link_remap=skip_link_remap,
            dry_run=dry_run,
            max_depth=max_depth,
        )
        copier = TreeCopier(source_client, target_client, target_space, resolved_source_space, options)
        result = copier.copy_tree(source_page_id, target_page_id)
        _emit_json(asdict(result))
    except Exception as exc:
        logger.exception("content.copy-tree failed", extra={"source_page_id": source_page_id})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    else:
        finished_at = datetime.now(UTC)
        _record_summary(
            parent_ctx,
            command="content.copy-tree",
            args=[source_page_id, f"target={target_page_id}", f"target_space={target_space}"],
            server=source_server_key,
            exit_code=0,
            started_at=started_at,
            finished_at=finished_at,
        )


if __name__ == "__main__":
    app()
