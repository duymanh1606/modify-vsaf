"""Unit tests for lint cli compliance report (FR-24)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner
from vds_cli.cli import app

runner = CliRunner()


@pytest.fixture
def mock_compliant_workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace tree that passes all compliance checks."""
    # Root pyproject.toml with vds-cli only + tool configs
    root = tmp_path
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "vds-scripts-workspace"\n'
        'version = "0.0.0"\n'
        "\n"
        "[project.scripts]\n"
        'vds-cli = "vds_cli.cli:app"\n'
        "\n"
        "[tool.ruff]\n"
        "line-length = 120\n"
        "\n"
        "[tool.mypy]\n"
        'python_version = "3.14"\n'
        "\n"
        "[tool.pytest.ini_options]\n"
        'addopts = "--cov-fail-under=80"\n',
        encoding="utf-8",
    )

    # vds_cli/pyproject.toml (package-level)
    vds_cli_root = root / "vds_cli"
    vds_cli_root.mkdir(parents=True, exist_ok=True)
    (vds_cli_root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "vds-cli"\n'
        'version = "0.0.0"\n'
        "\n"
        "[tool.pytest.ini_options]\n"
        'addopts = "--cov-fail-under=80"\n',
        encoding="utf-8",
    )

    # Create docs/agents/reference/cli-help-matrix.md with no drift
    docs_dir = root / "docs" / "agents" / "reference"
    docs_dir.mkdir(parents=True)
    docs_dir.joinpath("cli-help-matrix.md").write_text(
        "# Verified CLI help matrix\n\nUse `vds-cli` for all operations.\nDirect executables are internal.\n",
        encoding="utf-8",
    )

    # vds_cli package stub
    vds_cli_pkg = root / "vds_cli" / "src" / "vds_cli"
    vds_cli_pkg.mkdir(parents=True)
    (vds_cli_pkg / "__init__.py").write_text('__version__ = "4.0.0"\n', encoding="utf-8")
    (vds_cli_pkg / "router.py").write_text(
        "ORCHESTRATORS = {'jira': {}, 'confluence': {}}\n",
        encoding="utf-8",
    )
    (vds_cli_pkg / "cli.py").write_text(
        "import typer\napp = typer.Typer()\n",
        encoding="utf-8",
    )
    # Add commands subpackage
    cmd_dir = vds_cli_pkg / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    (cmd_dir / "__init__.py").write_text("", encoding="utf-8")
    (cmd_dir / "lint_cli.py").write_text("import typer\n", encoding="utf-8")

    # vds_cli_common stub
    vds_cli_common = root / "vds_cli_common" / "src" / "vds_cli_common"
    vds_cli_common.mkdir(parents=True)
    (vds_cli_common / "__init__.py").write_text("", encoding="utf-8")

    # platform_core stub
    plat = root / "platform_core" / "src" / "vds_platform_core"
    plat.mkdir(parents=True)
    (plat / "__init__.py").write_text("", encoding="utf-8")

    return root


def test_lint_cli_human_output(mock_compliant_workspace: Path) -> None:
    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli"])
    assert result.exit_code == 0
    assert "Compliance Report" in result.stdout or "router_entry_count" in result.stdout
    assert "PASS" in result.stdout or "Compliant" in result.stdout


def test_lint_cli_json_output(mock_compliant_workspace: Path) -> None:
    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["compliant"] is True
    assert data["summary"]["failed"] == 0
    assert any(f["check"] == "router_entry_count" for f in data["findings"])
    assert any(f["check"] == "alias_count" for f in data["findings"])
    assert any(f["check"] == "doc_drift" for f in data["findings"])


def test_lint_cli_fails_on_legacy_alias(mock_compliant_workspace: Path) -> None:
    """If a removed legacy alias is present, report should be non-compliant."""
    pp = mock_compliant_workspace / "pyproject.toml"
    text = pp.read_text(encoding="utf-8")
    text = text.replace(
        'vds-cli = "vds_cli.cli:app"',
        'vds-cli = "vds_cli.cli:app"\nmdformat-vds = "vds_cli.cli:app"',
    )
    pp.write_text(text, encoding="utf-8")

    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["compliant"] is False
    alias_finding = next(f for f in data["findings"] if f["check"] == "alias_count")
    assert alias_finding["ok"] is False
    assert "mdformat-vds" in alias_finding["detail"]


def test_lint_cli_fails_on_doc_drift(mock_compliant_workspace: Path) -> None:
    md = mock_compliant_workspace / "docs" / "agents" / "reference" / "cli-help-matrix.md"
    md.write_text(
        "# Verified CLI help matrix\n\nRun `vds-audit` directly for speed.\n",
        encoding="utf-8",
    )

    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    drift = next(f for f in data["findings"] if f["check"] == "doc_drift")
    assert drift["ok"] is False
    assert "vds-audit" in drift["detail"]


def test_lint_cli_fails_on_missing_tool_config(mock_compliant_workspace: Path) -> None:
    pp = mock_compliant_workspace / "pyproject.toml"
    text = pp.read_text(encoding="utf-8")
    # Remove tool.ruff and tool.mypy
    lines = [ln for ln in text.splitlines() if not ln.startswith("[tool.ruff]") and not ln.startswith("[tool.mypy]")]
    # Also strip ruff keys under it and mypy keys
    filtered: list[str] = []
    skip = False
    for ln in lines:
        if ln.startswith("[tool.ruff") or ln.startswith("[tool.mypy"):
            skip = True
            continue
        if skip and ln.startswith("["):
            skip = False
        if skip:
            continue
        filtered.append(ln)
    pp.write_text("\n".join(filtered) + "\n", encoding="utf-8")

    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    ruff_finding = next(f for f in data["findings"] if f["check"] == "pyproject [ruff]")
    mypy_finding = next(f for f in data["findings"] if f["check"] == "pyproject [mypy]")
    assert ruff_finding["ok"] is False
    assert mypy_finding["ok"] is False


def test_lint_cli_fails_on_cli_patterns(mock_compliant_workspace: Path) -> None:
    # Inject a cli.py with sys.exit(
    cli = mock_compliant_workspace / "vds_cli" / "src" / "vds_cli" / "cli.py"
    cli.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")

    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    pat = next(f for f in data["findings"] if f["check"] == "cli_patterns")
    assert pat["ok"] is False
    assert "sys.exit(" in pat["detail"]


def test_lint_cli_detects_argparse(mock_compliant_workspace: Path) -> None:
    cli = mock_compliant_workspace / "vds_cli" / "src" / "vds_cli" / "cli.py"
    cli.write_text("import argparse\n", encoding="utf-8")

    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    data = json.loads(result.stdout)
    pat = next(f for f in data["findings"] if f["check"] == "cli_patterns")
    assert pat["ok"] is False
    assert "argparse" in pat["detail"]


def test_lint_cli_detects_click(mock_compliant_workspace: Path) -> None:
    cli = mock_compliant_workspace / "vds_cli" / "src" / "vds_cli" / "cli.py"
    cli.write_text("import click\n", encoding="utf-8")

    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    data = json.loads(result.stdout)
    pat = next(f for f in data["findings"] if f["check"] == "cli_patterns")
    assert pat["ok"] is False
    assert "click" in pat["detail"]


def test_lint_cli_detects_bare_runtimeerror(mock_compliant_workspace: Path) -> None:
    cli = mock_compliant_workspace / "vds_cli" / "src" / "vds_cli" / "cli.py"
    cli.write_text("RuntimeError('oops')\n", encoding="utf-8")

    with patch("vds_cli.commands.lint_cli.SCRIPT_DIR", mock_compliant_workspace):
        result = runner.invoke(app, ["lint", "cli", "--json"])
    data = json.loads(result.stdout)
    pat = next(f for f in data["findings"] if f["check"] == "cli_patterns")
    assert pat["ok"] is False
    assert "RuntimeError" in pat["detail"]
