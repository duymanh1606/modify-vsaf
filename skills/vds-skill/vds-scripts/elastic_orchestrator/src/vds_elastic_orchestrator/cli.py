"""CLI for VDS Elastic Orchestrator.

Provides command-line access to Elasticsearch via Kibana Console Proxy.

Usage:
    # Via direct script
    uv run vds-elastic ping
    uv run vds-elastic search --index "logs-*" --size 10

    # Via vds-cli router
    ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic -- ping
    ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic -- search --index "logs-*"

    # JSON-only mode (clean JSON output, no headers/decoration)
    uv run vds-elastic --json search --index "logs-*"
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from vds_cli_common.app import make_vds_app
from vds_cli_common.context import CLIContext
from vds_cli_common.output import OutputManager
from vds_cli_common.paths import get_shared_env_path
from vds_platform_core.logging import configure_structlog

from vds_elastic_orchestrator.client import KibanaElasticsearchClient
from vds_elastic_orchestrator.config import SettingsError, load_settings
from vds_elastic_orchestrator.errors import (
    AuthError,
    ClientPermissionError,
    VDSClientError,
)

configure_structlog()
app = make_vds_app(
    name="vds-elastic",
    help="VDS Elasticsearch CLI via Kibana Console Proxy",
    settings_factory=load_settings,
)


def _get_client() -> KibanaElasticsearchClient:
    """Load settings and create client."""
    settings = load_settings(strict=True)
    return KibanaElasticsearchClient(settings)


def _handle_elastic_error(exc: VDSClientError, out: OutputManager) -> None:
    """Handle Elastic errors with appropriate messages and hints."""
    error_data = {
        "error": True,
        "error_type": type(exc).__name__,
        "message": str(exc),
        "context": getattr(exc, "context", {}),
    }
    if isinstance(exc, ClientPermissionError):
        error_data["required_roles"] = exc.required_roles

    if isinstance(exc, AuthError):
        out.output_error(
            f"Authentication failed: {exc}",
            hint=f"Check VDS_ELASTIC_USER and VDS_ELASTIC_PASSWORD in {get_shared_env_path()}",
        )
    elif isinstance(exc, ClientPermissionError):
        roles = ", ".join(exc.required_roles) if exc.required_roles else "unknown"
        out.output_error(
            f"Permission denied: {exc}",
            hint=f"Required roles: {roles}. Current role 'viewer' may not have this permission.",
        )
    else:
        out.output_error(str(exc))

    out.output_json(error_data)
    raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Connectivity Commands
# -----------------------------------------------------------------------------


@app.command()
def ping(ctx: typer.Context) -> None:
    """Test connectivity to Elasticsearch via Kibana.

    Verifies that:
    1. Kibana is reachable
    2. Authentication works
    3. Elasticsearch responds via console proxy
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            success = client.ping()
            result = {
                "success": success,
                "kibana_url": client.config.kibana_url,
                "kibana_ip": client.config.kibana_ip,
                "user": client.config.user,
            }
            out.output_json(result)
            raise typer.Exit(0 if success else 1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        out.output_json({"success": False, "error": str(exc)})
        raise typer.Exit(1)


@app.command("kibana-status")
def kibana_status(ctx: typer.Context) -> None:
    """Check Kibana availability and status."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.kibana_status()
            out.output_json(result)
            raise typer.Exit(0 if "error" not in result else 1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


@app.command("user-info")
def user_info(ctx: typer.Context) -> None:
    """Show current user and roles."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.user_info()
            out.output_json(result)
            raise typer.Exit(0 if "error" not in result else 1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


# -----------------------------------------------------------------------------
# Search Commands
# -----------------------------------------------------------------------------


@app.command()
def search(
    ctx: typer.Context,
    index: Annotated[
        str | None,
        typer.Option(
            "--index",
            "-i",
            help="Index pattern (default: from config or '*')",
        ),
    ] = None,
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Inline JSON query DSL",
        ),
    ] = None,
    query_file: Annotated[
        Path | None,
        typer.Option(
            "--query-file",
            "-f",
            help="Path to JSON query file",
            exists=True,
            readable=True,
        ),
    ] = None,
    query_string: Annotated[
        str | None,
        typer.Option(
            "--qs",
            help="Lucene query string (e.g., 'error AND timeout')",
        ),
    ] = None,
    start: Annotated[
        str | None,
        typer.Option(
            "--start",
            help="Start time (ISO format or relative like 'now-1h')",
        ),
    ] = None,
    end: Annotated[
        str | None,
        typer.Option(
            "--end",
            help="End time (ISO format or relative like 'now')",
        ),
    ] = None,
    time_field: Annotated[
        str,
        typer.Option(
            "--time-field",
            help="Time field for range queries",
        ),
    ] = "@timestamp",
    size: Annotated[
        int,
        typer.Option(
            "--size",
            "-s",
            help="Number of results to return",
        ),
    ] = 10,
    from_offset: Annotated[
        int,
        typer.Option(
            "--from",
            help="Pagination offset",
        ),
    ] = 0,
    sort: Annotated[
        str | None,
        typer.Option(
            "--sort",
            help="Sort field and order (e.g., '@timestamp:desc', 'level:asc')",
        ),
    ] = None,
) -> None:
    """Search documents in Elasticsearch.

    Examples:
        # Match all documents
        vds-elastic search --index "logs-*" --size 5

        # Most recent errors (sorted by timestamp descending)
        vds-elastic search --qs "level:ERROR" --sort "@timestamp:desc" --size 10

        # With query DSL
        vds-elastic search --query '{"match": {"message": "error"}}'

        # With Lucene query string
        vds-elastic search --qs "level:ERROR AND timeout"

        # With time range
        vds-elastic search --start "2025-01-15T00:00:00Z" --end "2025-01-16T00:00:00Z"
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            query_dsl: dict = {}

            if query_file:
                with query_file.open() as f:
                    query_dsl = json.load(f)
            elif query:
                query_dsl = json.loads(query)
            elif query_string:
                query_dsl = {"query_string": {"query": query_string}}

            if start or end:
                range_filter = {time_field: {}}
                if start:
                    range_filter[time_field]["gte"] = start
                if end:
                    range_filter[time_field]["lte"] = end

                if query_dsl:
                    query_dsl = {
                        "bool": {
                            "must": [query_dsl] if query_dsl else [],
                            "filter": [{"range": range_filter}],
                        }
                    }
                else:
                    query_dsl = {"range": range_filter}

            sort_spec = None
            if sort:
                parts = sort.split(":")
                field = parts[0]
                order = parts[1] if len(parts) > 1 else "asc"
                sort_spec = [{field: order}]

            result = client.search(
                index=index,
                query=query_dsl if query_dsl else None,
                size=size,
                from_=from_offset,
                sort=sort_spec,
            )
            out.output_json(result)
            raise typer.Exit(0)

    except json.JSONDecodeError as exc:
        out.output_error(f"Invalid JSON query: {exc}")
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


@app.command()
def count(
    ctx: typer.Context,
    index: Annotated[
        str | None,
        typer.Option(
            "--index",
            "-i",
            help="Index pattern (default: from config or '*')",
        ),
    ] = None,
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Inline JSON query DSL",
        ),
    ] = None,
    query_string: Annotated[
        str | None,
        typer.Option(
            "--qs",
            help="Lucene query string",
        ),
    ] = None,
) -> None:
    """Count documents matching a query.

    Examples:
        # Count all documents
        vds-elastic count --index "logs-*"

        # Count with query
        vds-elastic count --qs "level:ERROR"
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            query_dsl: dict | None = None

            if query:
                query_dsl = json.loads(query)
            elif query_string:
                query_dsl = {"query_string": {"query": query_string}}

            result = client.count(index=index, query=query_dsl)
            out.output_json(result)
            raise typer.Exit(0)

    except json.JSONDecodeError as exc:
        out.output_error(f"Invalid JSON query: {exc}")
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


@app.command()
def export(
    ctx: typer.Context,
    index: Annotated[
        str | None,
        typer.Option(
            "--index",
            "-i",
            help="Index pattern (default: from config or '*')",
        ),
    ] = None,
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Inline JSON query DSL",
        ),
    ] = None,
    query_file: Annotated[
        Path | None,
        typer.Option(
            "--query-file",
            "-f",
            help="Path to JSON query file",
            exists=True,
            readable=True,
        ),
    ] = None,
    query_string: Annotated[
        str | None,
        typer.Option(
            "--qs",
            help="Lucene query string (e.g., 'error AND timeout')",
        ),
    ] = None,
    output_file: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (default: stdout as ndjson)",
        ),
    ] = None,
    batch_size: Annotated[
        int,
        typer.Option(
            "--batch-size",
            "-b",
            help="Number of documents per scroll batch",
        ),
    ] = 1000,
    scroll_timeout: Annotated[
        str,
        typer.Option(
            "--scroll",
            help="Scroll context timeout (e.g., '5m', '10m')",
        ),
    ] = "5m",
    max_docs: Annotated[
        int | None,
        typer.Option(
            "--max",
            "-m",
            help="Maximum number of documents to export (default: all)",
        ),
    ] = None,
    source_only: Annotated[
        bool,
        typer.Option(
            "--source-only",
            help="Export only _source field (no metadata)",
        ),
    ] = False,
) -> None:
    """Export large datasets using scroll API.

    Streams documents as newline-delimited JSON (ndjson) format.
    Suitable for exporting millions of documents.

    Examples:
        # Export all documents to stdout
        vds-elastic export --index "logs-*"

        # Export to file
        vds-elastic export --index "logs-*" -o export.ndjson

        # Export with query and limit
        vds-elastic export --qs "level:ERROR" --max 10000 -o errors.ndjson

        # Export source only (no _id, _index metadata)
        vds-elastic export --index "logs-*" --source-only -o data.ndjson
    """
    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        with _get_client() as client:
            query_dsl: dict = {}

            if query_file:
                with query_file.open() as f:
                    query_dsl = json.load(f)
            elif query:
                query_dsl = json.loads(query)
            elif query_string:
                query_dsl = {"query_string": {"query": query_string}}

            output_ctx = (
                output_file.open("w") if output_file else contextlib.nullcontext(sys.stdout)
            )
            exported = 0

            with output_ctx as output:
                if not cli_ctx.json_only:
                    out.print(f"[cyan]Exporting from {index or '*'}...[/cyan]")

                for doc in client.scan(
                    index=index,
                    query=query_dsl if query_dsl else None,
                    size=batch_size,
                    scroll=scroll_timeout,
                ):
                    if max_docs and exported >= max_docs:
                        break

                    if source_only:
                        output.write(json.dumps(doc.get("_source", {})) + "\n")
                    else:
                        output.write(json.dumps(doc) + "\n")

                    exported += 1

                    if not cli_ctx.json_only and exported % 10000 == 0:
                        out.print(f"  Exported {exported:,} documents...")

                if not cli_ctx.json_only:
                    out.print(f"[green]✓ Export complete:[/green] {exported:,} documents")

            raise typer.Exit(0)

    except json.JSONDecodeError as exc:
        out.output_error(f"Invalid JSON query: {exc}")
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


# -----------------------------------------------------------------------------
# Admin Commands (require monitor privilege)
# -----------------------------------------------------------------------------


@app.command()
def info(ctx: typer.Context) -> None:
    """Get cluster info (requires monitor privilege).

    Note: This command may fail with 403 for 'viewer' role users.
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.info()
            out.output_json(result)
            raise typer.Exit(0)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


@app.command()
def health(ctx: typer.Context) -> None:
    """Get cluster health (requires monitor privilege).

    Note: This command may fail with 403 for 'viewer' role users.
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.health()
            out.output_json(result)
            raise typer.Exit(0)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


@app.command()
def indices(
    ctx: typer.Context,
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="Index pattern to filter",
        ),
    ] = "*",
) -> None:
    """List indices (requires monitor privilege).

    Note: This command may fail with 403 for 'viewer' role users.
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.cat_indices(pattern)
            out.output_json(result)
            raise typer.Exit(0)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


@app.command()
def aliases(
    ctx: typer.Context,
    pattern: Annotated[
        str,
        typer.Option(
            "--pattern",
            "-p",
            help="Alias name pattern to filter",
        ),
    ] = "*",
) -> None:
    """List index aliases (requires monitor privilege).

    Note: This command may fail with 403 for 'viewer' role users.
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.cat_aliases(pattern)
            out.output_json(result)
            raise typer.Exit(0)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_ELASTIC_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_elastic_error(exc, out)


if __name__ == "__main__":
    app()
