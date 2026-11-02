from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from vds_brd_orchestrator.cli import app
from vds_brd_orchestrator.validator import REQUIRED_BRD_SECTIONS
from vds_cli_common import ExitCodes


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_cli_failure_on_missing_sections(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    _write(docs_root / "doc.md", "BRD 3.1\n")
    report = tmp_path / "report.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate",
            "--root",
            str(docs_root),
            "--report",
            str(report),
            "--min-coverage",
            "100",
        ],
    )

    assert report.exists()
    assert result.exit_code == ExitCodes.VALIDATION_ERROR


def test_cli_success(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    content = "\n".join(f"BRD {section}" for section in REQUIRED_BRD_SECTIONS)
    _write(docs_root / "doc.md", content)
    report = tmp_path / "report.json"

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--json-only", "validate", "--root", str(docs_root), "--report", str(report)],
    )

    assert report.exists()
    assert result.exit_code == ExitCodes.SUCCESS


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])

    assert result.exit_code == ExitCodes.SUCCESS
    assert "Usage" in result.stdout
