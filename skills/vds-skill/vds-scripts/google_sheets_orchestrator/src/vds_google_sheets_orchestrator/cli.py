"""Typer CLI app for Google Sheets orchestrator."""

from __future__ import annotations

import csv
import json
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import structlog
import typer
from rich.console import Console
from rich.table import Table
from vds_cli_common.paths import get_vds_cache_root

from .client import GoogleSheetsClient
from .config import load_settings
from .errors import GoogleSheetsError

APP_NAME = "vds-google-sheets-orchestrator"

app = typer.Typer(
    name=APP_NAME,
    help="Google Sheets orchestrator operations.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

_REPORT_DIR = get_vds_cache_root() / "vds-google-sheets-reports"
_cli_state: dict[str, Any] = {
    "report_dir": _REPORT_DIR,
    "markdown": True,
    "reports": True,
    "json_only": False,
}


def _emit_json(payload: dict[str, Any]) -> None:
    """Emit JSON to stdout."""
    text = json.dumps(payload, indent=2, sort_keys=True)
    if sys.stdout.isatty():
        typer.echo(text)
    else:
        sys.stdout.write(text + "\n")


def _write_report(action: str, payload: dict[str, Any], markdown_lines: list[str] | None = None) -> None:
    """Write report files when report output is enabled."""
    if not _cli_state.get("reports"):
        return
    report_dir: Path = _cli_state.get("report_dir", _REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    safe_action = action.replace(" ", "_").replace("-", "_").replace("/", "_")
    json_path = report_dir / f"{safe_action}_{timestamp}.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if _cli_state.get("markdown"):
        lines = markdown_lines or [
            f"# {action} report",
            "",
            "```json",
            json.dumps(payload, indent=2, sort_keys=True),
            "```",
        ]
        md_path = report_dir / f"{safe_action}_{timestamp}.md"
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _version_callback(value: bool | None) -> bool | None:
    """Print version and exit."""
    if value:
        try:
            version = metadata.version("vds-google-sheets-orchestrator")
        except metadata.PackageNotFoundError:
            version = "unknown"
        typer.echo(f"{APP_NAME} {version}")
        raise typer.Exit()
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
    report_dir: Path | None = typer.Option(None, help=f"Directory for run reports (default: {_REPORT_DIR})"),
    markdown: bool = typer.Option(True, help="Emit Markdown summaries alongside JSON reports"),
    reports: bool = typer.Option(True, "--reports/--no-reports", help="Write report files to report-dir"),
    json_only: bool = typer.Option(False, "--json-only", help="Emit JSON to stdout only (no Rich tables)"),
    structured_logs: bool = typer.Option(
        False,
        "--structured-logs/--no-structured-logs",
        help="Emit structured JSON logs to stderr",
    ),
) -> None:
    """Google Sheets orchestrator - read, write, and manage Google Sheets."""
    global _cli_state
    resolved = report_dir.resolve() if report_dir else _REPORT_DIR
    if json_only:
        markdown = False
        reports = False
    _cli_state = {
        "report_dir": resolved,
        "markdown": markdown,
        "reports": reports,
        "json_only": json_only,
    }
    if structured_logs:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    elif json_only:
        logging.basicConfig(level=logging.CRITICAL, stream=sys.stderr)
    else:
        logging.basicConfig(
            level=logging.INFO,
            stream=sys.stderr,
            format="%(levelname)s %(name)s: %(message)s",
        )


def _build_client(
    *,
    auth_method: str | None,
    credentials_path: Path | None,
    oauth_credentials_path: Path | None,
    api_key: str | None,
) -> GoogleSheetsClient:
    settings = load_settings()
    return GoogleSheetsClient(
        settings,
        auth_method=auth_method,
        credentials_path=credentials_path,
        oauth_credentials_path=oauth_credentials_path,
        api_key=api_key,
    )


def _load_values(values_json: str | None, values_file: Path | None) -> Sequence[Sequence[str]]:
    if values_file:
        raw = values_file.read_text(encoding="utf-8")
    elif values_json:
        raw = values_json
    else:
        raise typer.BadParameter("Provide --values-json or --values-file.")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON values: {exc}") from exc

    if not isinstance(data, list) or not all(isinstance(row, list) for row in data):
        raise typer.BadParameter("Values must be a JSON list of lists.")
    return data


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, GoogleSheetsError):
        payload = {"error": str(exc), "context": getattr(exc, "context", {})}
        _write_report("error", payload)
        if _cli_state.get("json_only"):
            _emit_json(payload)
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    raise exc


@app.command()
def read(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    sheet_name: str = typer.Option("Sheet1", "--sheet-name", "-n"),
    range_name: str | None = typer.Option(None, "--range", "-r", help="Optional A1 range to limit output"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Read data from a worksheet."""
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        if range_name:
            data = client.read_range(spreadsheet_url, sheet_name, range_name)
        else:
            data = client.read_sheet(spreadsheet_url, sheet_name)
    except Exception as exc:
        _handle_error(exc)

    payload = {
        "rows": data,
        "count": len(data),
        "sheet_name": sheet_name,
        "range": range_name,
        "spreadsheet_url": spreadsheet_url,
    }
    _write_report("read", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
        return

    if not data:
        console.print("[yellow]No data found.[/yellow]")
        return

    table = Table(show_header=False)
    for row in data:
        table.add_row(*[str(cell) for cell in row])
    console.print(table)


@app.command(name="list-worksheets")
def list_worksheets(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """List worksheets in a spreadsheet."""
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        worksheets = client.list_worksheets(spreadsheet_url)
    except Exception as exc:
        _handle_error(exc)

    payload = {"worksheets": worksheets, "count": len(worksheets), "spreadsheet_url": spreadsheet_url}
    _write_report("list_worksheets", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
        return

    for name in worksheets:
        console.print(f"- {name}")


@app.command()
def write(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    sheet_name: str = typer.Option(..., "--sheet-name", "-n"),
    target_range: str = typer.Option(..., "--range", "-r"),
    values_json: str | None = typer.Option(None, "--values-json"),
    values_file: Path | None = typer.Option(None, "--values-file"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Write values to a range."""
    values = _load_values(values_json, values_file)
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        client.write_range(spreadsheet_url, sheet_name, target_range, values)
    except Exception as exc:
        _handle_error(exc)

    payload = {
        "status": "success",
        "range": target_range,
        "sheet_name": sheet_name,
        "spreadsheet_url": spreadsheet_url,
    }
    _write_report("write", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
    else:
        console.print("[green]Write completed.[/green]")


@app.command()
def append(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    sheet_name: str = typer.Option(..., "--sheet-name", "-n"),
    values_json: str | None = typer.Option(None, "--values-json"),
    values_file: Path | None = typer.Option(None, "--values-file"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Append rows to a worksheet."""
    values = _load_values(values_json, values_file)
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        client.append_rows(spreadsheet_url, sheet_name, values)
    except Exception as exc:
        _handle_error(exc)

    payload = {
        "status": "success",
        "rows_added": len(values),
        "sheet_name": sheet_name,
        "spreadsheet_url": spreadsheet_url,
    }
    _write_report("append", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
    else:
        console.print("[green]Append completed.[/green]")


@app.command()
def update(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    sheet_name: str = typer.Option(..., "--sheet-name", "-n"),
    target_range: str = typer.Option(..., "--range", "-r"),
    values_json: str | None = typer.Option(None, "--values-json"),
    values_file: Path | None = typer.Option(None, "--values-file"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Update values in a range (alias of write)."""
    values = _load_values(values_json, values_file)
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        client.write_range(spreadsheet_url, sheet_name, target_range, values)
    except Exception as exc:
        _handle_error(exc)

    payload = {
        "status": "success",
        "range": target_range,
        "sheet_name": sheet_name,
        "spreadsheet_url": spreadsheet_url,
    }
    _write_report("update", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
    else:
        console.print("[green]Update completed.[/green]")


@app.command()
def clear(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    sheet_name: str = typer.Option(..., "--sheet-name", "-n"),
    target_range: str = typer.Option(..., "--range", "-r"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Clear a range in a worksheet."""
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        client.clear_range(spreadsheet_url, sheet_name, target_range)
    except Exception as exc:
        _handle_error(exc)

    payload = {
        "status": "success",
        "range": target_range,
        "sheet_name": sheet_name,
        "spreadsheet_url": spreadsheet_url,
    }
    _write_report("clear", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
    else:
        console.print("[green]Clear completed.[/green]")


@app.command(name="create-spreadsheet")
def create_spreadsheet(
    title: str = typer.Option(..., "--title", "-t"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Create a new spreadsheet."""
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        url = client.create_spreadsheet(title)
    except Exception as exc:
        _handle_error(exc)

    payload = {"status": "success", "title": title, "url": url}
    _write_report("create_spreadsheet", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
    else:
        console.print(f"[green]Created spreadsheet:[/green] {url}")


@app.command(name="create-worksheet")
def create_worksheet(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    title: str = typer.Option(..., "--title", "-t"),
    rows: int = typer.Option(100, "--rows"),
    cols: int = typer.Option(26, "--cols"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Create a worksheet in an existing spreadsheet."""
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        client.create_worksheet(spreadsheet_url, title, rows=rows, cols=cols)
    except Exception as exc:
        _handle_error(exc)

    payload = {
        "status": "success",
        "title": title,
        "rows": rows,
        "cols": cols,
        "spreadsheet_url": spreadsheet_url,
    }
    _write_report("create_worksheet", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
    else:
        console.print("[green]Worksheet created.[/green]")


@app.command(name="delete-worksheet")
def delete_worksheet(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    sheet_name: str = typer.Option(..., "--sheet-name", "-n"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Delete a worksheet."""
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        client.delete_worksheet(spreadsheet_url, sheet_name)
    except Exception as exc:
        _handle_error(exc)

    payload = {
        "status": "success",
        "deleted": sheet_name,
        "spreadsheet_url": spreadsheet_url,
    }
    _write_report("delete_worksheet", payload)
    if _cli_state.get("json_only"):
        _emit_json(payload)
    else:
        console.print("[green]Worksheet deleted.[/green]")


@app.command()
def export(
    spreadsheet_url: str = typer.Option(..., "--spreadsheet-url", "-u"),
    sheet_name: str = typer.Option(..., "--sheet-name", "-n"),
    output_path: Path = typer.Option(..., "--output", "-o"),
    fmt: str = typer.Option("csv", "--format", "-f"),
    auth_method: str | None = typer.Option(None, "--auth-method", "-a"),
    credentials_path: Path | None = typer.Option(None, "--credentials-path"),
    oauth_credentials_path: Path | None = typer.Option(None, "--oauth-credentials-path"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Export a worksheet to CSV or XLSX."""
    fmt = fmt.lower()
    try:
        client = _build_client(
            auth_method=auth_method,
            credentials_path=credentials_path,
            oauth_credentials_path=oauth_credentials_path,
            api_key=api_key,
        )
        data = client.read_sheet(spreadsheet_url, sheet_name)
    except Exception as exc:
        _handle_error(exc)

    if fmt == "csv":
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for row in data:
                writer.writerow(row)
        payload = {"status": "success", "output_path": str(output_path), "format": "csv"}
        _write_report("export", payload)
        if _cli_state.get("json_only"):
            _emit_json(payload)
        else:
            console.print(f"[green]Exported CSV to {output_path}[/green]")
        return

    if fmt in {"xlsx", "excel"}:
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise typer.Exit("openpyxl is required for XLSX export.") from exc
        workbook = Workbook()
        worksheet = workbook.active
        for row in data:
            worksheet.append(list(row))
        workbook.save(output_path)
        payload = {"status": "success", "output_path": str(output_path), "format": "xlsx"}
        _write_report("export", payload)
        if _cli_state.get("json_only"):
            _emit_json(payload)
        else:
            console.print(f"[green]Exported XLSX to {output_path}[/green]")
        return

    raise typer.BadParameter("Format must be csv or xlsx.")
