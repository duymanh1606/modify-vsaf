"""CLI for VDS Grafana Orchestrator.

Provides command-line access to Quickwit logs via Grafana Datasource Proxy.

Usage:
    # Via direct script
    uv run vds-grafana health
    uv run vds-grafana search --index "otel-logs-v0_7" --query "level:ERROR"

    # Via vds-cli router
    ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- health
    ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- search --index "otel-logs-v0_7"

    # JSON-only mode (clean JSON output, no headers/decoration)
    uv run vds-grafana --json search --index "otel-logs-v0_7"
"""

from __future__ import annotations

import json
import time
from typing import Annotated, Any

import typer
from vds_cli_common.app import make_vds_app
from vds_cli_common.context import CLIContext
from vds_cli_common.output import OutputManager
from vds_cli_common.paths import get_shared_env_path
from vds_platform_core.logging import configure_structlog

from vds_grafana_orchestrator.client import QuickwitClient
from vds_grafana_orchestrator.config import SettingsError, load_settings
from vds_grafana_orchestrator.errors import (
    AuthError,
    ClientPermissionError,
    NotFoundError,
    VDSClientError,
)

configure_structlog()
app = make_vds_app(
    name="vds-grafana",
    help="VDS Grafana Logs CLI - Query Quickwit logs via Grafana Datasource Proxy",
    settings_factory=load_settings,
)

# Common option for datasource override
DatasourceOpt = Annotated[
    str | None,
    typer.Option("--datasource", "-d", help="Override datasource UID, ID, or name"),
]


def _get_client(datasource: str | None = None) -> QuickwitClient:
    """Load settings and create client."""
    settings = load_settings(strict=True)

    datasource_uid = None
    datasource_id = None
    datasource_name = None

    if datasource:
        try:
            datasource_id = int(datasource)
        except ValueError:
            if len(datasource) < 20 and "-" not in datasource:
                datasource_uid = datasource
            else:
                datasource_name = datasource

    return QuickwitClient(
        settings,
        datasource_uid=datasource_uid,
        datasource_id=datasource_id,
        datasource_name=datasource_name,
    )


def _handle_error(exc: VDSClientError, out: OutputManager) -> None:
    """Handle Grafana client errors with appropriate hints."""
    if isinstance(exc, AuthError):
        out.output_error(
            str(exc),
            hint="Check VDS_GRAFANA_USER/VDS_GRAFANA_PASSWORD or VDS_GRAFANA_TOKEN",
        )
    elif isinstance(exc, ClientPermissionError):
        out.output_error(
            str(exc),
            hint="Ensure your Grafana user has access to the datasource",
        )
    elif isinstance(exc, NotFoundError):
        out.output_error(
            str(exc),
            hint="Check VDS_GRAFANA_DATASOURCE_UID or use 'datasources' command to list available datasources",
        )
    else:
        out.output_error(str(exc))


# -----------------------------------------------------------------------------
# Health Commands
# -----------------------------------------------------------------------------


@app.command()
def health(
    ctx: typer.Context,
    datasource: DatasourceOpt = None,
) -> None:
    """Check connectivity to Grafana and Quickwit datasource.

    Verifies that:
    1. Grafana is reachable
    2. Authentication works
    3. Quickwit datasource is accessible
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client(datasource) as client:
            result = client.health()
            out.output_json(result)
            success = result.get("grafana_ok", False) and result.get("datasource_ok", False)
            raise typer.Exit(0 if success else 1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_GRAFANA_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        out.output_json({"success": False, "error": str(exc)})
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Datasource Commands
# -----------------------------------------------------------------------------


@app.command()
def datasources(
    ctx: typer.Context,
    datasource: DatasourceOpt = None,
    quickwit_only: Annotated[
        bool,
        typer.Option(
            "--quickwit-only",
            "-q",
            help="Show only Quickwit datasources",
        ),
    ] = True,
) -> None:
    """List available datasources.

    By default shows only Quickwit datasources. Use --no-quickwit-only to show all.
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client(datasource) as client:
            if quickwit_only:
                result = client.grafana.quickwit_datasources()
            else:
                result = client.grafana.datasources()

            out.output_json(result)

    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_GRAFANA_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Index Commands
# -----------------------------------------------------------------------------


@app.command()
def indexes(
    ctx: typer.Context,
    datasource: DatasourceOpt = None,
) -> None:
    """List available Quickwit indexes."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client(datasource) as client:
            result = client.indexes()
            out.output_json(result)

    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_GRAFANA_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


@app.command()
def fields(
    ctx: typer.Context,
    index: Annotated[
        str | None,
        typer.Option(
            "--index",
            "-i",
            help="Index to inspect (default from config)",
        ),
    ] = None,
    datasource: DatasourceOpt = None,
) -> None:
    """Show fields for an index (best-effort via sampling)."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client(datasource) as client:
            result = client.fields(index=index)
            out.output_json({"index": index or client.config.default_index, "fields": result})

    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_GRAFANA_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


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
            help="Index pattern (default from config)",
        ),
    ] = None,
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Quickwit query string",
        ),
    ] = "*",
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            "-s",
            help="Time range (e.g., '1h', '30m', '1d')",
        ),
    ] = None,
    from_ts: Annotated[
        int | None,
        typer.Option(
            "--from",
            help="Start timestamp (Unix seconds)",
        ),
    ] = None,
    to_ts: Annotated[
        int | None,
        typer.Option(
            "--to",
            help="End timestamp (Unix seconds)",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum results (default: 100, max: 1000)",
        ),
    ] = 100,
    datasource: DatasourceOpt = None,
) -> None:
    """Search logs using Quickwit REST API.

    Examples:
        # Search all logs in last hour
        vds-grafana search --index otel-logs-v0_7 --query "*" --since 1h

        # Search for errors
        vds-grafana search --query "severity_text:ERROR" --limit 50

        # Search with time range
        vds-grafana search --query "service_name:api-gateway" --from 1705320000 --to 1705323600
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client(datasource) as client:
            start_timestamp = from_ts
            end_timestamp = to_ts

            if since and not from_ts:
                now = int(time.time())
                seconds = _parse_duration(since)
                start_timestamp = now - seconds
                if not to_ts:
                    end_timestamp = now

            result = client.search(
                index=index,
                query=query,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                max_hits=limit,
            )
            out.output_json(result)

    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_GRAFANA_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)
    except ValueError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)


@app.command("es-search")
def es_search(
    ctx: typer.Context,
    index: Annotated[
        str | None,
        typer.Option(
            "--index",
            "-i",
            help="Index pattern",
        ),
    ] = None,
    query: Annotated[
        str | None,
        typer.Option(
            "--query",
            "-q",
            help="Inline JSON Query DSL",
        ),
    ] = None,
    query_file: Annotated[
        typer.FileText | None,
        typer.Option(
            "--query-file",
            "-f",
            help="Path to JSON file containing Query DSL",
        ),
    ] = None,
    size: Annotated[
        int,
        typer.Option(
            "--size",
            "-s",
            help="Number of results (default: 10)",
        ),
    ] = 10,
    datasource: DatasourceOpt = None,
) -> None:
    """Search using ES-compatible Query DSL.

    Examples:
        # Simple query string
        vds-grafana es-search --query '{"query": {"match": {"severity_text": "ERROR"}}}'

        # Query from file
        vds-grafana es-search --query-file query.json --size 100
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client(datasource) as client:
            body: dict[str, Any] | None = None
            if query:
                try:
                    body = json.loads(query)
                except json.JSONDecodeError as exc:
                    out.output_error(f"Invalid JSON in --query: {exc}")
                    raise typer.Exit(1)
            elif query_file:
                try:
                    body = json.load(query_file)
                except json.JSONDecodeError as exc:
                    out.output_error(f"Invalid JSON in query file: {exc}")
                    raise typer.Exit(1)

            result = client.es_search(index=index, body=body, size=size)
            out.output_json(result)

    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_GRAFANA_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def _parse_duration(duration: str) -> int:
    """Parse duration string like '1h', '30m', '1d' to seconds."""
    duration = duration.strip().lower()

    units = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
    }

    if not duration:
        raise ValueError("Empty duration string")

    unit = duration[-1]
    if unit not in units:
        raise ValueError(f"Unknown duration unit: {unit}. Use s/m/h/d/w")

    try:
        value = int(duration[:-1])
    except ValueError:
        raise ValueError(f"Invalid duration number: {duration[:-1]}")

    return value * units[unit]


# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app()
