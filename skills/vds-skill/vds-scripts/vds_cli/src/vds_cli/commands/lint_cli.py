"""FR-24 Compliance Report command for vds-cli.

vds-cli lint cli [--json]
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Annotated

import typer

from vds_cli.router import ORCHESTRATORS

lint_app = typer.Typer(help="Lint and compliance checks for the vds-cli platform.")

# Relative to the workspace root (vds-scripts/)
# vds_cli/src/vds_cli/commands/lint_cli.py -> 5 parents up -> workspace root
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent


def _root_pyproject() -> dict:
    path = SCRIPT_DIR / "pyproject.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def _count_orchestrators() -> int:
    return len(ORCHESTRATORS)


def _legacy_alias_count() -> tuple[int, list[str]]:
    """Return count of *removed* legacy aliases still present in root pyproject.toml.

    Internal orchestrator entry points (e.g. ``vds-audit``) are *not* aliases;
    they are router metadata used via ``uv run --project …`` and are expected
    to remain in their **package-level** ``[project.scripts]`` — never in the
    workspace root pyproject.toml. Only ``vds-cli`` itself is permitted there.
    """
    data = _root_pyproject()
    scripts = data.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return 0, []
    legacy = [name for name in scripts if name != "vds-cli"]
    return len(legacy), legacy


# Ordered list of direct executable names that must never appear as
# user-facing commands in cli-help-matrix.md.
_DIRECT_EXECUTABLES = [
    "vds-audit",
    "vds-spec",
    "vds-jira",
    "vds-confluence",
    "vds-bitbucket",
    "vds-git",
    "vds-elastic",
    "vds-sonarqube",
    "vds-grafana",
    "vds-schema",
    "vds-diagrams",
    "vds-excel",
    "vds-google-sheets",
    "vds-tasks",
    "vds-openapi",
    "vds-pdf",
    "vds-markdown",
    "vds-intellij",
    "vds-links",
    "vds-structure",
    "vds-lsp",
    "vds-brd",
    "vds-hexagonal",
    "vds-multi-agent",
    "vds-public-interface",
    "vds-metabase",
    "vds-mcp",
    "vds-research",
    "vds-memory",
    "vds-progress",
    "vds-circular-dependency",
    "vds-evolution",
    "vds-db-query",
]


def _check_doc_drift() -> tuple[int, list[str]]:
    """Scan cli-help-matrix.md for references to removed alias names or direct executable refs.

    Returns (issue_count, findings).
    """
    path = SCRIPT_DIR / "docs" / "agents" / "reference" / "cli-help-matrix.md"
    if not path.exists():
        return 1, ["cli-help-matrix.md not found"]

    text = path.read_text(encoding="utf-8")
    issues: list[str] = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip intentional warning blocks (quoted or list items)
        if stripped.startswith(">"):
            continue
        # Skip the explicit "Never invoke direct executables" warning lines
        if "never invoke" in stripped.lower() or "internal to the router" in stripped.lower():
            continue
        # Skip lines that are clearly warning users *not* to use direct executables.
        if "Never" in stripped or "never" in stripped:
            continue
        for alias in _DIRECT_EXECUTABLES:
            if f"`{alias}`" in stripped:
                issues.append(f"Line {line_no}: direct executable ref `{alias}`")

    return len(issues), issues


def _tool_config_status() -> list[dict]:
    """Check presence of [tool.ruff] and [tool.mypy] in root pyproject.toml."""
    data = _root_pyproject()
    tool_cfg = data.get("tool", {})
    checks: list[dict] = []
    for tool in ("ruff", "mypy"):
        present = tool in tool_cfg
        checks.append(
            {
                "name": f"pyproject [{tool}]",
                "ok": present,
                "detail": f"[tool.{tool}] {'found' if present else 'MISSING'}",
            }
        )
    return checks


def _find_fail_under(path: Path) -> float | None:
    """Parse a single pyproject.toml for coverage fail_under."""
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return None

    # 1. [tool.pytest.ini_options] addopts
    addopts = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", "")
    if isinstance(addopts, str):
        for part in addopts.split():
            if "--cov-fail-under=" in part:
                try:
                    return float(part.split("=", 1)[1])
                except ValueError:
                    pass

    # 2. [tool.pytest.ini_options] fail_under shorthand (non-standard but possible)
    fu = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("fail_under")
    if fu is not None:
        try:
            return float(fu)
        except (TypeError, ValueError):
            pass

    # 3. [tool.coverage.report] fail_under
    fu = data.get("tool", {}).get("coverage", {}).get("report", {}).get("fail_under")
    if fu is not None:
        try:
            return float(fu)
        except (TypeError, ValueError):
            pass

    return None


def _check_coverage_gate() -> dict:
    """Scan root and package pyproject.toml files for coverage fail_under.

    Returns a single check dict — passes if ANY scanned file contains a gate.
    """
    candidates = [SCRIPT_DIR / "pyproject.toml", SCRIPT_DIR / "vds_cli" / "pyproject.toml"]
    # Also check any workspace member that looks like it might have its own config
    for member_dir in sorted(SCRIPT_DIR.iterdir()):
        if member_dir.is_dir() and (member_dir / "pyproject.toml").exists() and member_dir.name not in {"vds_cli", ".venv", "__pycache__", "tmp"}:
                candidates.append(member_dir / "pyproject.toml")

    for path in candidates:
        val = _find_fail_under(path)
        if val is not None:
            return {
                "name": "coverage_gates",
                "ok": True,
                "detail": f"fail_under={val} in {path.relative_to(SCRIPT_DIR)}",
            }

    return {
        "name": "coverage_gates",
        "ok": False,
        "detail": "no fail_under found in any pyproject.toml",
    }


def _scan_cli_patterns() -> list[dict]:
    """Scan all */cli.py files for ad-hoc patterns.

    Flags:
      - ``sys.exit(``  (not ``typer.Exit``)
      - ``argparse``   (raw argparse instead of typer)
      - ``click``      (raw click instead of typer)
      - bare ``RuntimeError(``  (should be raised, not called)
    """
    findings: list[dict] = []
    cli_files = list(SCRIPT_DIR.rglob("*/cli.py"))
    for fp in cli_files:
        if "__pycache__" in fp.parts or ".venv" in fp.parts:
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = fp.relative_to(SCRIPT_DIR)
        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "sys.exit(" in stripped:
                findings.append(
                    {
                        "file": str(rel),
                        "line": line_no,
                        "pattern": "sys.exit(",
                        "context": stripped[:120],
                    }
                )
            # Heuristic: import argparse / from argparse import
            if re.search(r"(^|\s)(import\s+argparse|from\s+argparse\b)", stripped):
                findings.append(
                    {
                        "file": str(rel),
                        "line": line_no,
                        "pattern": "argparse",
                        "context": stripped[:120],
                    }
                )
            # Heuristic: import click / from click import (but not typer-related)
            if "click" in stripped and ("import" in stripped or stripped.startswith("from ")) and "typer" not in stripped:
                    # Skip docstrings/comments that happen to contain "click"
                    if stripped.startswith('"""') or stripped.startswith("'''") or stripped.startswith("#"):
                        continue
                    findings.append(
                        {
                            "file": str(rel),
                            "line": line_no,
                            "pattern": "click",
                            "context": stripped[:120],
                        }
                    )
            # Bare RuntimeError call (not raise)
            if "RuntimeError(" in stripped and "raise" not in stripped:
                findings.append(
                    {
                        "file": str(rel),
                        "line": line_no,
                        "pattern": "bare RuntimeError",
                        "context": stripped[:120],
                    }
                )
    return findings


def _build_report() -> dict:
    report: dict = {
        "compliant": True,
        "summary": {"total_checks": 0, "passed": 0, "failed": 0},
        "findings": [],
    }

    def _add_check(name: str, ok: bool, detail: str, items: list | None = None) -> None:
        finding: dict = {
            "check": name,
            "ok": ok,
            "detail": detail,
        }
        if items is not None:
            finding["items"] = items
        report["findings"].append(finding)
        report["summary"]["total_checks"] += 1
        if ok:
            report["summary"]["passed"] += 1
        else:
            report["summary"]["failed"] += 1
            report["compliant"] = False

    # 1. Router entry count
    router_count = _count_orchestrators()
    _add_check(
        "router_entry_count",
        router_count > 0,
        f"{router_count} orchestrator(s) in vds_cli/router.py",
    )

    # 2. Alias count
    alias_count, aliases = _legacy_alias_count()
    detail = f"{alias_count} legacy alias(es)"
    if aliases:
        detail += f": {', '.join(aliases)}"
    _add_check("alias_count", alias_count == 0, detail)

    # 3. Doc drift
    drift_count, drift_issues = _check_doc_drift()
    detail = f"{drift_count} doc drift issue(s) in cli-help-matrix.md"
    if drift_issues:
        detail += f" — {', '.join(drift_issues[:3])}"
        if len(drift_issues) > 3:
            detail += f" (+{len(drift_issues) - 3} more)"
    _add_check("doc_drift", drift_count == 0, detail)

    # 4. ruff / mypy config status
    for tc in _tool_config_status():
        _add_check(tc["name"], tc["ok"], tc["detail"])

    # 5. Coverage gate
    cg = _check_coverage_gate()
    _add_check(cg["name"], cg["ok"], cg["detail"])

    # 6. Ad-hoc CLI pattern detections
    patterns = _scan_cli_patterns()
    detail = f"{len(patterns)} ad-hoc pattern(s) across */cli.py"
    if patterns:
        examples = [f"{p['file']}:{p['line']} ({p['pattern']})" for p in patterns[:3]]
        detail += f" — {', '.join(examples)}"
        if len(patterns) > 3:
            detail += f" (+{len(patterns) - 3} more)"
    _add_check("cli_patterns", len(patterns) == 0, detail, items=patterns)

    return report


def _render_human(report: dict) -> None:
    max_width = 60
    typer.secho("vds-cli Compliance Report (FR-24)", fg=typer.colors.CYAN, bold=True)
    typer.echo()
    typer.echo(f"{'Check':<25} {'Status':<10} Detail")
    typer.echo("-" * 70)
    for finding in report["findings"]:
        status = "PASS" if finding["ok"] else "FAIL"
        color = typer.colors.GREEN if finding["ok"] else typer.colors.RED
        detail = finding["detail"]
        if len(detail) > max_width:
            detail = detail[: max_width - 3] + "..."
        typer.secho(f"{finding['check']:<25} {status:<10}", fg=typer.colors.WHITE, nl=False)
        typer.secho(detail, fg=color)
    typer.echo()
    s = report["summary"]
    if report["compliant"]:
        typer.secho(
            f"Compliant — {s['passed']}/{s['total_checks']} checks passed",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"Non-compliant — {s['failed']}/{s['total_checks']} checks failed",
            fg=typer.colors.RED,
        )


@lint_app.command("cli")
def lint_cli_cmd(
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON output."),
    ] = False,
) -> None:
    """Run compliance diagnostics against the vds-cli surface."""
    report = _build_report()
    if json_out:
        typer.echo(json.dumps(report, indent=2))
    else:
        _render_human(report)
    if not report["compliant"]:
        raise typer.Exit(1) from None
