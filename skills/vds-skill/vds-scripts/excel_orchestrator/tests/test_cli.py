"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook, load_workbook
from typer.testing import CliRunner

from vds_excel_orchestrator.cli import app

runner = CliRunner()


def _parse_json(output: str) -> dict:
    """Parse JSON from output, skipping potential log lines."""
    # Find the start and end of the JSON block
    start = output.find("{")
    end = output.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(output[start : end + 1])
        except json.JSONDecodeError:
            pass

    # Fallback to line-by-line if simple bracket search fails
    lines = output.strip().splitlines()
    for i in range(len(lines)):
        try:
            return json.loads("\n".join(lines[i:]))
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("No JSON found in output", output, 0)


def _read_report(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_sheet_list(temp_excel_file: Path) -> None:
    """Test sheet list command."""
    result = runner.invoke(app, ["sheet", "list", str(temp_excel_file)])
    assert result.exit_code == 0
    assert "Sheet" in result.stdout


def test_sheet_list_json(temp_excel_file: Path) -> None:
    """Test sheet list command with JSON output."""
    result = runner.invoke(app, ["sheet", "list", str(temp_excel_file), "--json"])
    assert result.exit_code == 0
    data = _parse_json(result.stdout)
    assert "sheets" in data
    assert isinstance(data["sheets"], list)


def test_cell_get(temp_excel_file: Path) -> None:
    """Test cell get command."""
    result = runner.invoke(
        app, ["cell", "get", str(temp_excel_file), "--sheet", "Sheet", "--cell", "A1"]
    )
    assert result.exit_code == 0
    assert "Test" in result.stdout or "Value" in result.stdout


def test_validate(temp_excel_file: Path) -> None:
    """Test validate command."""
    result = runner.invoke(app, ["validate", str(temp_excel_file)])
    assert result.exit_code == 0
    assert "Valid" in result.stdout or "valid" in result.stdout.lower()


def test_validate_json(temp_excel_file: Path) -> None:
    """Test validate command with JSON output."""
    result = runner.invoke(app, ["validate", str(temp_excel_file), "--json"])
    assert result.exit_code == 0
    data = _parse_json(result.stdout)
    assert "valid" in data
    assert data["valid"] is True


def _create_reference_workbook(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tong hop"
    ws.merge_cells("A1:D1")
    ws["A1"] = "Summary"
    ws["A8"] = "STT"
    ws["B8"] = "Cong viec"
    ws["C8"] = "Dien giai"
    ws["D8"] = "No luc (MD)"

    ws_fn = wb.create_sheet("NL Chuc nang")
    ws_fn.merge_cells("A1:E1")
    ws_fn["A6"] = "Loai Xu ly"
    ws_fn["B6"] = "Tong no luc"
    ws_fn["C6"] = "Chuc nang"

    ws_nfn = wb.create_sheet("NL Phi CN")
    ws_nfn.merge_cells("A1:E1")
    ws_nfn["A6"] = "Tong no luc"
    ws_nfn["B6"] = "Dien giai"
    ws_nfn["C6"] = "Gia tri"

    ws_qtdl = wb.create_sheet("NL QTDL")
    ws_qtdl.merge_cells("A1:E1")
    ws_qtdl["A6"] = "Tong no luc"
    ws_qtdl["B6"] = "Dien giai"
    ws_qtdl["C6"] = "Gia tri"

    wb.save(path)


def _create_current_ulnc_workbook(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Executive Dashboard"
    ws.append(
        [
            "Service Name",
            "Sheet Name",
            "Priority",
            "Docs Status",
            "Code Status",
            "BRD Coverage",
            "Effort Estimate (Days)",
            "Status",
        ]
    )
    ws.append(["svc-a", "svc-a", "High", "Complete", "Implemented", "100%", 10.5, "Done"])
    ws.append(["svc-b", "svc-b", "High", "Complete", "Implemented", "100%", 7.5, "Done"])
    wb.save(path)


def _create_empty_current_ulnc_workbook(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Executive Dashboard"
    ws.append(
        [
            "Service Name",
            "Sheet Name",
            "Priority",
            "Docs Status",
            "Code Status",
            "BRD Coverage",
            "Effort Estimate (Days)",
            "Status",
        ]
    )
    wb.save(path)


def test_ulnc_align_json(temp_dir: Path) -> None:
    """Test ulnc-align command with JSON output."""
    current = temp_dir / "current-ulnc.xlsx"
    reference = temp_dir / "reference-ulnl.xlsx"
    output = temp_dir / "vds-ulnc-aligned.xlsx"
    _create_current_ulnc_workbook(current)
    _create_reference_workbook(reference)

    result = runner.invoke(
        app,
        [
            "ulnc-align",
            "--current-ulnc",
            str(current),
            "--reference-ulnl",
            str(reference),
            "--output",
            str(output),
            "--strict-presentation",
            "--json",
        ],
    )
    assert result.exit_code == 0
    data = _parse_json(result.stdout)
    assert data["output_file"] == str(output)
    assert Path(data["output_file"]).exists()
    assert Path(data["report_file"]).exists()
    assert data["presentation"]["required_sheet_order_ok"] is True
    assert data["presentation"]["merge_topology_ok"] is True
    assert data["presentation"]["header_style_parity_pct"] >= 95.0
    assert data["settings"]["buffer_scenario"] == "base"
    assert data["selected_scenario"]["multiplier"] == 1.0
    assert data["selected_scenario"]["total_hours"] > 0
    assert data["buffer_guidance"]["minimum"] == "phase1"
    assert data["coverage"]["passed"] is True
    assert data["mapping"]["mapped_rows"] == 2
    assert "required_work_coverage" in data["mapping"]
    assert "nfr_signals" in data["mapping"]["required_work_coverage"]
    assert "readability" in data["mapping"]
    assert data["mapping"]["readability"]["NL Chuc nang"]["clipping_risk_rows"] == 0
    assert data["mapping"]["overflow"]["NL Phi CN"]["placement_mode"] == "continuation_only_no_total_split"
    assert data["mapping"]["overflow"]["NL Phi CN"]["primary_rows_used"] == 0
    assert data["mapping"]["overflow"]["NL Phi CN"]["continuation_rows_preview"][:2] == [16, 17]
    assert "window_population" in data
    assert data["window_population"]["functional"]["sheet"] == "NL Chuc nang"
    assert data["window_population"]["functional"]["populated_rows"] == data["mapping"]["functional_rows"]
    assert data["window_population"]["functional"]["overflow_rows"] >= 0
    assert "overflow" in data
    assert data["overflow"]["total_rows"] >= 0
    assert data["overflow"]["detected"] is (data["overflow"]["total_rows"] > 0)
    assert "content_fidelity_checks" in data
    assert data["content_fidelity_checks"]["checks"]["row_count_preserved"] is True
    assert data["content_fidelity_checks"]["checks"]["no_unmapped_rows"] is True
    assert data["content_fidelity_checks"]["passed"] is True
    assert "ordering_signature" in data
    assert data["ordering_signature"]["algorithm"] == "sha256/sheet-row-values"
    assert len(data["ordering_signature"]["signature"]) == 64
    assert data["ordering_signature"]["deterministic_ordering"] is True

    report = _read_report(data["report_file"])
    assert "window_population" in report
    assert "overflow" in report
    assert "content_fidelity_checks" in report
    assert "ordering_signature" in report
    assert report["ordering_signature"]["signature"] == data["ordering_signature"]["signature"]

    wb = load_workbook(output, read_only=True, data_only=False)
    try:
        nfn_ws = wb["NL Phi CN"]
        qtdl_ws = wb["NL QTDL"]
        assert [nfn_ws.cell(row, 2).value for row in range(16, 22)] == [1, 2, 3, 4, 5, 6]
        for row in (10, 11, 12, 13):
            for col in (2, 3, 4, 5):
                assert nfn_ws.cell(row, col).value in (None, "")
        for row in (13, 14):
            for col in (1, 2, 3, 4, 5):
                assert qtdl_ws.cell(row, col).value is None
    finally:
        wb.close()


def test_ulnc_align_rejects_reference_output_path(temp_dir: Path) -> None:
    """Test ulnc-align blocks output inside reference path."""
    current = temp_dir / "current-ulnc.xlsx"
    reference = temp_dir / "analysis" / "reference" / "ulnc" / "reference-ulnl.xlsx"
    reference.parent.mkdir(parents=True, exist_ok=True)
    _create_current_ulnc_workbook(current)
    _create_reference_workbook(reference)

    result = runner.invoke(
        app,
        [
            "ulnc-align",
            "--current-ulnc",
            str(current),
            "--reference-ulnl",
            str(reference),
            "--output",
            str(reference.parent / "vds-ulnc-aligned.xlsx"),
            "--strict-presentation",
        ],
    )
    assert result.exit_code != 0


def test_ulnc_align_generates_required_sheets(temp_dir: Path) -> None:
    """Test generated workbook keeps required sheets."""
    current = temp_dir / "current-ulnc.xlsx"
    reference = temp_dir / "reference-ulnl.xlsx"
    output = temp_dir / "vds-ulnc-aligned.xlsx"
    _create_current_ulnc_workbook(current)
    _create_reference_workbook(reference)

    result = runner.invoke(
        app,
        [
            "ulnc-align",
            "--current-ulnc",
            str(current),
            "--reference-ulnl",
            str(reference),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0
    wb = load_workbook(output, read_only=True)
    try:
        for name in ["Tong hop", "NL Chuc nang", "NL Phi CN", "NL QTDL"]:
            assert name in wb.sheetnames
    finally:
        wb.close()


def test_ulnc_align_coverage_policy_error_fails(temp_dir: Path) -> None:
    """Test coverage policy error exits non-zero when coverage fails."""
    current = temp_dir / "current-empty-ulnc.xlsx"
    reference = temp_dir / "reference-ulnl.xlsx"
    output = temp_dir / "vds-ulnc-aligned.xlsx"
    _create_empty_current_ulnc_workbook(current)
    _create_reference_workbook(reference)

    result = runner.invoke(
        app,
        [
            "ulnc-align",
            "--current-ulnc",
            str(current),
            "--reference-ulnl",
            str(reference),
            "--output",
            str(output),
            "--coverage-policy",
            "error",
        ],
    )
    assert result.exit_code != 0


def test_ulnc_align_coverage_policy_warn_emits_warning(temp_dir: Path) -> None:
    """Test coverage policy warn keeps exit zero and emits warnings in JSON."""
    current = temp_dir / "current-empty-ulnc.xlsx"
    reference = temp_dir / "reference-ulnl.xlsx"
    output = temp_dir / "vds-ulnc-aligned.xlsx"
    _create_empty_current_ulnc_workbook(current)
    _create_reference_workbook(reference)

    result = runner.invoke(
        app,
        [
            "ulnc-align",
            "--current-ulnc",
            str(current),
            "--reference-ulnl",
            str(reference),
            "--output",
            str(output),
            "--coverage-policy",
            "warn",
            "--json",
        ],
    )
    assert result.exit_code == 0
    data = _parse_json(result.stdout)
    assert data["coverage"]["passed"] is False
    assert data["warnings"]


def test_ulnc_align_ordering_signature_is_stable_across_runs(temp_dir: Path) -> None:
    """Test deterministic ordering signal remains stable for identical inputs."""
    current = temp_dir / "current-ulnc.xlsx"
    reference = temp_dir / "reference-ulnl.xlsx"
    output_one = temp_dir / "vds-ulnc-aligned-1.xlsx"
    output_two = temp_dir / "vds-ulnc-aligned-2.xlsx"
    _create_current_ulnc_workbook(current)
    _create_reference_workbook(reference)

    result_one = runner.invoke(
        app,
        [
            "ulnc-align",
            "--current-ulnc",
            str(current),
            "--reference-ulnl",
            str(reference),
            "--output",
            str(output_one),
            "--json",
        ],
    )
    assert result_one.exit_code == 0
    data_one = _parse_json(result_one.stdout)

    result_two = runner.invoke(
        app,
        [
            "ulnc-align",
            "--current-ulnc",
            str(current),
            "--reference-ulnl",
            str(reference),
            "--output",
            str(output_two),
            "--json",
        ],
    )
    assert result_two.exit_code == 0
    data_two = _parse_json(result_two.stdout)

    assert data_one["ordering_signature"]["signature"] == data_two["ordering_signature"]["signature"]
