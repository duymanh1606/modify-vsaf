"""CLI for BRD coverage validation using Typer."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from vds_brd_orchestrator.validator import validate_brd_coverage, write_report
from vds_cli_common import (
    CLIContext,
    ErrorHandler,
    ExitCodes,
    OutputManager,
    create_version_callback,
)

APP_NAME = "vds-brd-orchestrator"
VALID_COMMANDS = ["validate"]

app = typer.Typer(
    name="vds-brd",
    help="BRD coverage validation for VDS documentation",
    rich_markup_mode="rich",
    invoke_without_command=True,
    no_args_is_help=False,
)

version_callback = create_version_callback(APP_NAME)


def _scripts_root() -> Path:
    """Return the vds-scripts root directory."""
    return Path(__file__).resolve().parents[3]


def _default_docs_root() -> Path:
    """Return default documentation root."""
    override = os.environ.get("VDS_INSURANCE_DOCS_ROOT")
    if override:
        return Path(override).expanduser()

    root = _scripts_root().parents[1]
    preferred = root / "WHO-project" / "insurance-document"
    if preferred.exists():
        return preferred

    matches = sorted(root.glob("*-project/insurance-document"))
    if matches:
        return matches[0]

    return preferred


def _default_report_path() -> Path:
    """Return default BRD coverage report path."""
    return _scripts_root() / "scripts" / "brd_coverage_report.json"


def _get_state(ctx: typer.Context) -> tuple[CLIContext, OutputManager, ErrorHandler]:
    if not isinstance(ctx.obj, dict):
        cli_ctx = CLIContext()
        output = OutputManager(cli_ctx)
        error_handler = ErrorHandler(output, valid_commands=VALID_COMMANDS)
        return cli_ctx, output, error_handler
    return ctx.obj["cli_ctx"], ctx.obj["output"], ctx.obj["error_handler"]


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
    json_only: Annotated[
        bool,
        typer.Option(
            "--json-only",
            "-j",
            help="Output clean JSON only",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress non-essential output",
        ),
    ] = False,
) -> None:
    cli_ctx = CLIContext.from_options(json_only=json_only, quiet=quiet)
    output = OutputManager(cli_ctx)
    error_handler = ErrorHandler(output, valid_commands=VALID_COMMANDS)
    ctx.obj = {"cli_ctx": cli_ctx, "output": output, "error_handler": error_handler}

    if ctx.invoked_subcommand is None:
        output.ctx.console.print(ctx.get_help())
        raise typer.Exit(ExitCodes.SUCCESS)


@app.command()
def validate(
    ctx: typer.Context,
    root: Annotated[
        Path | None,
        typer.Option(
            "--root",
            "-r",
            help="Documentation root to scan",
        ),
    ] = None,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Write JSON report to file",
        ),
    ] = None,
    min_coverage: Annotated[
        float,
        typer.Option(
            "--min-coverage",
            help="Minimum required coverage percentage (default 100)",
        ),
    ] = 100.0,
) -> None:
    """Validate BRD coverage across documentation.

    \b
    Examples:
        vds-brd validate
        vds-brd validate --root path/to/docs --report brd_coverage_report.json
    """
    cli_ctx, output, _error_handler = _get_state(ctx)

    docs_root = (root or _default_docs_root()).resolve()
    if not docs_root.exists():
        output.output_error(
            "Documentation root does not exist",
            hint=f"Check --root path: {docs_root}",
        )
        raise typer.Exit(ExitCodes.NOT_FOUND_ERROR)

    report_data = validate_brd_coverage(docs_root)
    if "error" in report_data:
        output.output_error(report_data["error"])
        raise typer.Exit(ExitCodes.GENERAL_ERROR)

    report_path = (report or _default_report_path()).resolve()
    try:
        write_report(report_path, report_data)
    except Exception as exc:  # pragma: no cover - defensive
        output.output_error(
            "Failed to write report",
            details={"path": str(report_path), "error": str(exc)},
        )
        raise typer.Exit(ExitCodes.GENERAL_ERROR) from exc

    if cli_ctx.json_only:
        output.output_json(report_data)
    elif not cli_ctx.quiet:
        output.ctx.console.print("BRD Coverage Validation")
        output.ctx.console.print(f"Docs root: {docs_root}")
        output.ctx.console.print(f"Coverage: {report_data['coverage_percentage']:.1f}%")
        output.ctx.console.print(f"Covered sections: {report_data['total_covered']}")
        output.ctx.console.print(f"Missing sections: {len(report_data['missing_sections'])}")
        output.ctx.console.print(f"Report: {report_path}")

    if report_data["coverage_percentage"] < min_coverage:
        output.output_error(
            "BRD coverage below required threshold",
            details={
                "coverage": report_data["coverage_percentage"],
                "minimum": min_coverage,
            },
        )
        raise typer.Exit(ExitCodes.VALIDATION_ERROR)
