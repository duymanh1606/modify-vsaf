"""Command-line interface for Excel orchestrator."""

from __future__ import annotations

import contextlib
import json
import sys
from hashlib import sha256
from pathlib import Path

import typer
from openpyxl import load_workbook
from rich.console import Console
from rich.table import Table

from .converters import ExcelConverter
from .errors import ExcelOrchestratorError
from .excel_client import ExcelClient
from .formatters import CellFormatter
from .logging import configure_logging, get_logger
from .target_state_status import (
    generate_status_vi_xlsx,
    generate_status_xlsx,
    resolve_default_paths,
)
from .ulnc_alignment import resolve_alignment_paths, run_ulnc_align
from .validators import ExcelValidator

app = typer.Typer(name="vds-excel", help="Excel (.xlsx) file manipulation orchestrator")
console = Console()
logger = get_logger(__name__)


def _emit_json(payload: dict | list) -> None:
    """Emit JSON output."""
    text = json.dumps(payload, indent=2, default=str)
    if sys.stdout.isatty():
        console.print(text)
    else:
        sys.stdout.write(text + "\n")


def _compute_ordering_signature(output_file: Path) -> str:
    """Compute deterministic hash signature from aligned output row ordering."""
    wb = load_workbook(output_file, read_only=True, data_only=True)
    try:
        digest_rows: list[list[object]] = []
        for sheet_name in ("NL Chuc nang", "NL Phi CN", "NL QTDL"):
            if sheet_name not in wb.sheetnames:
                continue
            ws = wb[sheet_name]
            for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                values = list(row)
                while values and values[-1] is None:
                    values.pop()
                if not values:
                    continue
                digest_rows.append([sheet_name, row_idx, values])
        payload = json.dumps(digest_rows, ensure_ascii=False, default=str, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()
    finally:
        wb.close()


def _augment_alignment_report(result: dict[str, object]) -> dict[str, object]:
    """Inject remediation sections required by TSK-415 into result/report JSON."""
    mapping = result.get("mapping", {})
    source_snapshot = result.get("source_snapshot", {})

    source_rows = int(source_snapshot.get("source_rows", 0)) if isinstance(source_snapshot, dict) else 0
    functional_rows = int(mapping.get("functional_rows", 0)) if isinstance(mapping, dict) else 0
    nonfunctional_rows = int(mapping.get("nonfunctional_rows", 0)) if isinstance(mapping, dict) else 0
    qtdl_rows = int(mapping.get("qtdl_rows", 0)) if isinstance(mapping, dict) else 0
    mapped_rows = int(mapping.get("mapped_rows", functional_rows)) if isinstance(mapping, dict) else functional_rows
    unmapped_rows = (
        int(mapping.get("unmapped_rows", max(source_rows - mapped_rows, 0))) if isinstance(mapping, dict) else 0
    )

    overflow_details = mapping.get("overflow", {}) if isinstance(mapping, dict) else {}
    by_sheet = {
        "NL Chuc nang": int(overflow_details.get("NL Chuc nang", {}).get("continuation_rows_used", 0))
        if isinstance(overflow_details.get("NL Chuc nang"), dict)
        else 0,
        "NL Phi CN": int(overflow_details.get("NL Phi CN", {}).get("continuation_rows_used", 0))
        if isinstance(overflow_details.get("NL Phi CN"), dict)
        else 0,
        "NL QTDL": int(overflow_details.get("NL QTDL", {}).get("continuation_rows_used", 0))
        if isinstance(overflow_details.get("NL QTDL"), dict)
        else 0,
    }
    total_overflow_rows = sum(by_sheet.values())
    overflow = {
        "detected": total_overflow_rows > 0,
        "total_rows": total_overflow_rows,
        "by_sheet": by_sheet,
    }
    window_population = {
        "functional": {
            "sheet": "NL Chuc nang",
            "populated_rows": functional_rows,
            "overflow_rows": by_sheet["NL Chuc nang"],
        },
        "nonfunctional": {
            "sheet": "NL Phi CN",
            "populated_rows": nonfunctional_rows,
            "overflow_rows": by_sheet["NL Phi CN"],
        },
        "qtdl": {
            "sheet": "NL QTDL",
            "populated_rows": qtdl_rows,
            "overflow_rows": by_sheet["NL QTDL"],
        },
    }
    content_fidelity_checks = {
        "source_rows": source_rows,
        "mapped_rows": mapped_rows,
        "unmapped_rows": unmapped_rows,
        "checks": {
            "row_count_preserved": mapped_rows + unmapped_rows == source_rows,
            "no_unmapped_rows": unmapped_rows == 0,
        },
    }
    content_fidelity_checks["passed"] = all(content_fidelity_checks["checks"].values())

    output_file = Path(str(result["output_file"]))
    ordering_signature = {
        "algorithm": "sha256/sheet-row-values",
        "signature": _compute_ordering_signature(output_file),
        "deterministic_ordering": True,
    }

    remediation_sections: dict[str, object] = {
        "window_population": window_population,
        "overflow": overflow,
        "content_fidelity_checks": content_fidelity_checks,
        "ordering_signature": ordering_signature,
    }
    result.update(remediation_sections)

    report_file = Path(str(result["report_file"]))
    report_payload = json.loads(report_file.read_text(encoding="utf-8"))
    report_payload.update(remediation_sections)
    report_file.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


# Sheet operations

sheet_app = typer.Typer(name="sheet", help="Sheet operations")
app.add_typer(sheet_app)


@sheet_app.command("list")
def sheet_list(
    file: str = typer.Argument(..., help="Excel file path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all sheets in Excel file."""
    try:
        with ExcelClient(file, read_only=True) as client:
            client.open()
            sheets = client.list_sheets()

            if json_output:
                _emit_json({"sheets": sheets, "count": len(sheets)})
            else:
                table = Table(title="Sheets")
                table.add_column("Index", style="cyan")
                table.add_column("Name", style="magenta")
                for idx, name in enumerate(sheets, 1):
                    table.add_row(str(idx), name)
                console.print(table)

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@sheet_app.command("create")
def sheet_create(
    file: str = typer.Argument(..., help="Excel file path"),
    name: str = typer.Option(..., "--name", "-n", help="Sheet name"),
    index: int | None = typer.Option(None, "--index", "-i", help="Sheet index position"),
) -> None:
    """Create a new sheet."""
    try:
        ExcelValidator.validate_sheet_name(name)

        with ExcelClient(file) as client:
            if not Path(file).exists():
                client.create()
            else:
                client.open()

            client.create_sheet(name, index)
            client.save()
            console.print(f"[green]Sheet '{name}' created successfully[/green]")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@sheet_app.command("delete")
def sheet_delete(
    file: str = typer.Argument(..., help="Excel file path"),
    name: str = typer.Option(..., "--name", "-n", help="Sheet name"),
) -> None:
    """Delete a sheet."""
    try:
        with ExcelClient(file) as client:
            client.open()
            client.delete_sheet(name)
            client.save()
            console.print(f"[green]Sheet '{name}' deleted successfully[/green]")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@sheet_app.command("rename")
def sheet_rename(
    file: str = typer.Argument(..., help="Excel file path"),
    old_name: str = typer.Option(..., "--old", help="Current sheet name"),
    new_name: str = typer.Option(..., "--new", help="New sheet name"),
) -> None:
    """Rename a sheet."""
    try:
        ExcelValidator.validate_sheet_name(new_name)

        with ExcelClient(file) as client:
            client.open()
            client.rename_sheet(old_name, new_name)
            client.save()
            console.print(f"[green]Sheet renamed from '{old_name}' to '{new_name}'[/green]")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@sheet_app.command("copy")
def sheet_copy(
    file: str = typer.Argument(..., help="Excel file path"),
    source: str = typer.Option(..., "--source", "-s", help="Source sheet name"),
    target: str = typer.Option(..., "--target", "-t", help="Target sheet name"),
) -> None:
    """Copy a sheet."""
    try:
        ExcelValidator.validate_sheet_name(target)

        with ExcelClient(file) as client:
            client.open()
            client.copy_sheet(source, target)
            client.save()
            console.print(f"[green]Sheet '{source}' copied to '{target}'[/green]")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


# Cell operations

cell_app = typer.Typer(name="cell", help="Cell operations")
app.add_typer(cell_app)


@cell_app.command("get")
def cell_get(
    file: str = typer.Argument(..., help="Excel file path"),
    sheet: str = typer.Option(..., "--sheet", "-s", help="Sheet name"),
    cell: str = typer.Option(..., "--cell", "-c", help="Cell reference (e.g., A1)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get cell value."""
    try:
        ExcelValidator.validate_cell_ref(cell)

        with ExcelClient(file, read_only=True) as client:
            client.open()
            value = client.get_cell(sheet, cell)

            if json_output:
                _emit_json({"sheet": sheet, "cell": cell, "value": value})
            else:
                console.print(f"[cyan]Sheet:[/cyan] {sheet}")
                console.print(f"[cyan]Cell:[/cyan] {cell}")
                console.print(f"[green]Value:[/green] {value}")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@cell_app.command("set")
def cell_set(
    file: str = typer.Argument(..., help="Excel file path"),
    sheet: str = typer.Option(..., "--sheet", "-s", help="Sheet name"),
    cell: str = typer.Option(..., "--cell", "-c", help="Cell reference (e.g., A1)"),
    value: str = typer.Option(..., "--value", "-v", help="Value to set"),
) -> None:
    """Set cell value."""
    try:
        ExcelValidator.validate_cell_ref(cell)

        with ExcelClient(file) as client:
            if not Path(file).exists():
                client.create()
            else:
                client.open()

            # Try to convert value to appropriate type
            typed_value: str | int | float = value
            with contextlib.suppress(ValueError):
                typed_value = float(value) if "." in value else int(value)

            client.set_cell(sheet, cell, typed_value)
            client.save()
            console.print(f"[green]Cell {cell} set to {value}[/green]")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


# Range operations

range_app = typer.Typer(name="range", help="Range operations")
app.add_typer(range_app)


@range_app.command("read")
def range_read(
    file: str = typer.Argument(..., help="Excel file path"),
    sheet: str = typer.Option(..., "--sheet", "-s", help="Sheet name"),
    range_ref: str = typer.Option(..., "--range", "-r", help="Range reference (e.g., A1:C10)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Read range of cells."""
    try:
        ExcelValidator.validate_range_ref(range_ref)

        with ExcelClient(file, read_only=True) as client:
            client.open()
            data = client.read_range(sheet, range_ref)

            if json_output:
                _emit_json({"sheet": sheet, "range": range_ref, "data": data})
            else:
                table = Table(title=f"Range {range_ref}")
                for row in data:
                    table.add_row(*[str(cell) if cell is not None else "" for cell in row])
                console.print(table)

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@range_app.command("write")
def range_write(
    file: str = typer.Argument(..., help="Excel file path"),
    sheet: str = typer.Option(..., "--sheet", "-s", help="Sheet name"),
    start_cell: str = typer.Option(..., "--start", help="Starting cell (e.g., A1)"),
    data_file: str = typer.Option(..., "--data", help="JSON file with 2D array data"),
) -> None:
    """Write data to range of cells."""
    try:
        ExcelValidator.validate_cell_ref(start_cell)

        data_path = Path(data_file)
        if not data_path.exists():
            raise typer.BadParameter(f"Data file not found: {data_file}")

        with data_path.open() as f:
            data = json.load(f)

        if not isinstance(data, list) or not all(isinstance(row, list) for row in data):
            raise typer.BadParameter("Data must be a 2D array (list of lists)")

        with ExcelClient(file) as client:
            if not Path(file).exists():
                client.create()
            else:
                client.open()

            client.write_range(sheet, start_cell, data)
            client.save()
            console.print(f"[green]Data written to range starting at {start_cell}[/green]")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


# Format operations

format_app = typer.Typer(name="format", help="Formatting operations")
app.add_typer(format_app)


@format_app.command("apply")
def format_apply(
    file: str = typer.Argument(..., help="Excel file path"),
    sheet: str = typer.Option(..., "--sheet", "-s", help="Sheet name"),
    cell: str = typer.Option(..., "--cell", "-c", help="Cell reference (e.g., A1)"),
    font_name: str | None = typer.Option(None, "--font-name", help="Font name"),
    font_size: int | None = typer.Option(None, "--font-size", help="Font size"),
    bold: bool = typer.Option(False, "--bold", help="Bold text"),
    italic: bool = typer.Option(False, "--italic", help="Italic text"),
    fill_color: str | None = typer.Option(None, "--fill", help="Fill color (hex, e.g., FFFF00)"),
    align_h: str | None = typer.Option(None, "--align-h", help="Horizontal alignment (left/center/right)"),
    align_v: str | None = typer.Option(None, "--align-v", help="Vertical alignment (top/center/bottom)"),
    number_format: str | None = typer.Option(None, "--number-format", help="Number format (e.g., #,##0.00)"),
) -> None:
    """Apply formatting to a cell."""
    try:
        ExcelValidator.validate_cell_ref(cell)

        with ExcelClient(file) as client:
            client.open()
            sheet_obj = client.get_sheet(sheet)

            font_kwargs = {}
            if font_name:
                font_kwargs["name"] = font_name
            if font_size:
                font_kwargs["size"] = font_size
            if bold:
                font_kwargs["bold"] = True
            if italic:
                font_kwargs["italic"] = True

            if font_kwargs:
                CellFormatter.apply_font(sheet_obj, cell, **font_kwargs)

            if fill_color:
                CellFormatter.apply_fill(sheet_obj, cell, fill_color)

            if align_h or align_v:
                CellFormatter.apply_alignment(
                    sheet_obj,
                    cell,
                    horizontal=align_h or "general",
                    vertical=align_v or "bottom",
                )

            if number_format:
                CellFormatter.apply_number_format(sheet_obj, cell, number_format)

            client.save()
            console.print(f"[green]Formatting applied to cell {cell}[/green]")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


# Convert operations


@app.command("convert")
def convert(
    file: str = typer.Argument(..., help="Excel file path"),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    sheet: str | None = typer.Option(None, "--sheet", "-s", help="Sheet name (defaults to first)"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json/csv)"),
) -> None:
    """Convert Excel to JSON or CSV."""
    try:
        output_path = Path(output)

        if format.lower() == "json":
            ExcelConverter.to_json(file, sheet_name=sheet, output_path=output_path)
            console.print(f"[green]Converted to JSON: {output}[/green]")
        elif format.lower() == "csv":
            ExcelConverter.to_csv(file, sheet_name=sheet, output_path=output_path)
            console.print(f"[green]Converted to CSV: {output}[/green]")
        else:
            raise typer.BadParameter(f"Unsupported format: {format}. Use 'json' or 'csv'")

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


# Validate operations


@app.command("validate")
def validate(
    file: str = typer.Argument(..., help="Excel file path"),
    max_size_mb: int = typer.Option(100, "--max-size", help="Maximum file size in MB"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Validate Excel file structure."""
    try:
        result = ExcelValidator.validate_file(file, max_size_mb=max_size_mb)

        if json_output:
            _emit_json(result)
        else:
            table = Table(title="Validation Results")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_row("Valid", "✅ Yes" if result["valid"] else "❌ No")
            table.add_row("File Path", result["path"])
            table.add_row("Size (MB)", str(result["size_mb"]))
            table.add_row("Sheet Count", str(result["sheet_count"]))
            table.add_row("Sheet Names", ", ".join(result["sheet_names"]))
            console.print(table)

    except ExcelOrchestratorError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


# Target-state status workbook


@app.command("target-state-status")
def target_state_status(
    arch_root: Path | None = typer.Option(
        None,
        "--arch-root",
        help="Target-state architecture root (defaults to Insurance target-state architecture).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output Excel file path (defaults to target-state-status.xlsx under target-state).",
    ),
    brd_report: Path | None = typer.Option(
        None,
        "--brd-report",
        help="BRD coverage report JSON path (defaults to vds-scripts/scripts/brd_coverage_report.json).",
    ),
    audit_report: Path | None = typer.Option(
        None,
        "--audit-report",
        help="Audit report JSON path (defaults to auto-detected audit-results.json).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output summary as JSON"),
) -> None:
    """Generate target-state-status.xlsx from target-state task files."""
    try:
        resolved_arch_root, resolved_output, resolved_brd_report, resolved_audit_report = resolve_default_paths(
            arch_root, output, brd_report, audit_report
        )
        result = generate_status_xlsx(
            resolved_arch_root,
            resolved_output,
            resolved_brd_report,
            resolved_audit_report,
        )
        if json_output:
            _emit_json(result)
        else:
            console.print(f"[green]Generated:[/green] {result['output_file']}")
            console.print(
                f"[cyan]Task files:[/cyan] {result['task_files']}  "
                f"[cyan]Dependencies:[/cyan] {result['cross_dependencies']}"
            )
            if result["task_files"] == 0:
                console.print(
                    "[yellow]Warning:[/yellow] No task files were found. Check --arch-root path and file naming."
                )
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@app.command("target-state-status-vi")
def target_state_status_vi(
    arch_root: Path | None = typer.Option(
        None,
        "--arch-root",
        help="Target-state architecture root (defaults to Insurance target-state architecture).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output Excel file path (defaults to target-state-status-vi.xlsx under target-state).",
    ),
    brd_report: Path | None = typer.Option(
        None,
        "--brd-report",
        help="BRD coverage report JSON path (defaults to vds-scripts/scripts/brd_coverage_report.json).",
    ),
    audit_report: Path | None = typer.Option(
        None,
        "--audit-report",
        help="Audit report JSON path (defaults to auto-detected audit-results.json).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output summary as JSON"),
) -> None:
    """Generate target-state-status-vi.xlsx (Vietnamese) from target-state task files."""
    try:
        resolved_arch_root, resolved_output, resolved_brd_report, resolved_audit_report = resolve_default_paths(
            arch_root, output, brd_report, audit_report
        )
        if output is None:
            resolved_output = resolved_output.with_name("target-state-status-vi.xlsx")
        result = generate_status_vi_xlsx(
            resolved_arch_root,
            resolved_output,
            resolved_brd_report,
            resolved_audit_report,
        )
        if json_output:
            _emit_json(result)
        else:
            console.print(f"[green]Generated:[/green] {result['output_file']}")
            console.print(
                f"[cyan]Task files:[/cyan] {result['task_files']}  "
                f"[cyan]Dependencies:[/cyan] {result['cross_dependencies']}"
            )
            if result["task_files"] == 0:
                console.print(
                    "[yellow]Warning:[/yellow] No task files were found. Check --arch-root path and file naming."
                )
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


@app.command("ulnc-align")
def ulnc_align(
    current_ulnc: Path | None = typer.Option(
        None,
        "--current-ulnc",
        help="Current ULNC workbook path (defaults to target-state-status-vi.xlsx in target-ulnc).",
    ),
    reference_ulnl: Path | None = typer.Option(
        None,
        "--reference-ulnl",
        help="Reference ULNL workbook path (defaults to ULNL_SAVING_CORE_Jan 2026.xlsx).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output VDS ULNC workbook path (defaults to target-ulnc/vds-ulnc-aligned.xlsx).",
    ),
    project_name: str = typer.Option("INSURANCE", "--project-name", help="Project name in report metadata."),
    buffer_scenario: str = typer.Option(
        "base",
        "--buffer-scenario",
        help="Buffer scenario: base, phase1, phase1+2, phase1+2+3, all-in.",
    ),
    strict_presentation: bool = typer.Option(
        False,
        "--strict-presentation",
        help="Fail command when presentation parity checks fail.",
    ),
    apply_sdlc_buffer: bool = typer.Option(
        False, "--apply-sdlc-buffer", help="Enable optional SDLC overlay metadata in report settings."
    ),
    include_tech_buffer: bool = typer.Option(
        False, "--include-tech-buffer", help="Enable optional tech/integration reserve metadata."
    ),
    coverage_policy: str = typer.Option(
        "warn",
        "--coverage-policy",
        help="Coverage gate policy: warn or error.",
    ),
    min_functional_coverage: float = typer.Option(
        90.0,
        "--min-functional-coverage",
        help="Minimum functional coverage percentage.",
    ),
    min_nonfunctional_categories: int = typer.Option(
        6,
        "--min-nonfunctional-categories",
        help="Minimum non-functional category rows.",
    ),
    min_qtdl_rows: int = typer.Option(
        3,
        "--min-qtdl-rows",
        help="Minimum QTDL rows.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output summary as JSON"),
) -> None:
    """Generate VDS-owned ULNC output aligned to ULNL reference format/profile."""
    try:
        resolved_current_ulnc, resolved_reference_ulnl, resolved_output = resolve_alignment_paths(
            current_ulnc, reference_ulnl, output
        )
        result = run_ulnc_align(
            current_ulnc=resolved_current_ulnc,
            reference_ulnl=resolved_reference_ulnl,
            output=resolved_output,
            project_name=project_name,
            strict_presentation=strict_presentation,
            buffer_scenario=buffer_scenario,
            include_tech_buffer=include_tech_buffer,
            apply_sdlc_buffer=apply_sdlc_buffer,
            coverage_policy=coverage_policy,
            min_functional_coverage=min_functional_coverage,
            min_nonfunctional_categories=min_nonfunctional_categories,
            min_qtdl_rows=min_qtdl_rows,
        )
        result = _augment_alignment_report(result)
        if json_output:
            _emit_json(result)
        else:
            console.print(f"[green]Generated:[/green] {result['output_file']}")
            console.print(f"[cyan]Report:[/cyan] {result['report_file']}")
            cov = result["coverage"]
            console.print(
                "[cyan]Coverage:[/cyan] "
                f"functional={cov['functional_coverage_pct']}% "
                f"nfr={cov['nonfunctional_categories']} "
                f"qtdl={cov['qtdl_rows']} "
                f"passed={cov['passed']}"
            )
            pres = result["presentation"]
            console.print(
                "[cyan]Presentation:[/cyan] "
                f"order_ok={pres['required_sheet_order_ok']} "
                f"merge_ok={pres['merge_topology_ok']} "
                f"style_parity={pres['header_style_parity_pct']}%"
            )
            if result["warnings"]:
                console.print(f"[yellow]Warnings:[/yellow] {result['warnings']}")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


# Main entry point


def main() -> None:
    """Main entry point."""
    configure_logging()
    app()


if __name__ == "__main__":
    main()
