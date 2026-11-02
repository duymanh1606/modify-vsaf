"""Tests for ULNC alignment core helpers."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook

from vds_excel_orchestrator.ulnc_alignment import (
    extract_source_contract,
    populate_ulnl_output,
    run_ulnc_align,
)


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


def _create_current_ulnc(path: Path) -> None:
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
    ws.append(["svc-a", "svc-a", "High", "Complete", "Implemented", "100%", 10.0, "Done"])
    ws.append(["svc-b", "svc-b", "High", "Complete", "Implemented", "100%", 8.0, "Done"])

    dep = wb.create_sheet("Cross-Service Dependencies")
    dep.append(["Service", "Type", "Dependency", "BRD Domain", "Source"])
    dep.append(["svc-a", "Cross-Service", "svc-b", "domain", "Cross-Service Dependencies"])
    wb.save(path)


def test_extract_source_contract(temp_dir: Path) -> None:
    current = temp_dir / "current.xlsx"
    _create_current_ulnc(current)
    snapshot = extract_source_contract(current)
    assert snapshot["service_count"] == 2
    assert snapshot["source_rows"] == 2
    assert snapshot["dependency_rows"] == 1
    assert snapshot["missing_headers"] == []
    assert snapshot["base_days"] == 18.0
    assert snapshot["base_hours"] == 144.0


def test_extract_source_contract_preserves_sheet_service_identity(temp_dir: Path) -> None:
    current = temp_dir / "current-service-identity.xlsx"
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
    ws.append(
        [
            "insurance-authentication-sync-process",
            "authentication-sync-process",
            "High",
            "Complete",
            "Implemented",
            "100%",
            1.0,
            "Done",
        ]
    )
    svc_sheet = wb.create_sheet("authentication-sync-process")
    svc_sheet.append(
        ["Mã công việc", "Giai đoạn", "Mô tả công việc", "Phụ thuộc", "Vai trò", "Ước tính (giờ)", "Trạng thái"]
    )
    svc_sheet.append(["T-1.1", "Thiết kế", "Task", "None", "Kiến trúc sư", 8.0, "Chờ"])
    wb.save(current)

    snapshot = extract_source_contract(current)
    assert snapshot["source_rows"] == 1
    row = snapshot["rows"][0]
    assert row["service"] == "authentication-sync-process"
    assert row["service_sheet_alias"] == "authentication-sync-process"
    assert row["service_canonical"] == "insurance-authentication-sync-process"


def test_populate_ulnl_output(temp_dir: Path) -> None:
    output = temp_dir / "output.xlsx"
    _create_reference_workbook(output)
    snapshot = {
        "rows": [
            {
                "service": "svc-a",
                "task_id": "T-1.1",
                "phase": "Thiết kế",
                "description": "Example task",
                "effort_hours": 80.0,
            }
        ],
        "base_hours": 80.0,
    }
    counts = populate_ulnl_output(output, snapshot)
    assert counts["functional_rows"] == 1
    assert counts["nonfunctional_rows"] == 6
    assert counts["qtdl_rows"] == 3
    assert "overflow" in counts
    for sheet_name in ("NL Chuc nang", "NL Phi CN", "NL QTDL"):
        assert sheet_name in counts["overflow"]
        sheet_overflow = counts["overflow"][sheet_name]
        assert sheet_overflow["strategy"] == "primary_window_then_continuation"
        assert sheet_overflow["primary_rows_used"] >= 0
        assert sheet_overflow["continuation_rows_used"] >= 0
        assert "continuation_rows_preview" in sheet_overflow
        assert isinstance(sheet_overflow["continuation_rows_preview"], list)
        assert sheet_overflow["overflowed"] is (
            sheet_overflow["continuation_rows_used"] > 0
        )
    assert "required_work_coverage" in counts
    assert "nfr_signals" in counts["required_work_coverage"]
    assert "readability" in counts
    assert counts["readability"]["NL Chuc nang"]["clipping_risk_rows"] == 0
    assert counts["overflow"]["NL Phi CN"]["placement_mode"] == "continuation_only_no_total_split"
    assert counts["overflow"]["NL Phi CN"]["primary_rows_used"] == 0
    assert counts["overflow"]["NL Phi CN"]["continuation_rows_preview"][:2] == [16, 17]
    assert counts["cleanup"]["NL Phi CN"]["cleared_primary_rows"] == [10, 11, 12, 13]
    assert counts["cleanup"]["NL QTDL"]["cleaned_formula_artifact_rows"] == []
    wb = load_workbook(output, read_only=True, data_only=True)
    try:
        nfn_ws = wb["NL Phi CN"]
        qtdl_ws = wb["NL QTDL"]
        assert any(
            nfn_ws.cell(row, 3).value == "Bảo mật"
            for row in range(1, nfn_ws.max_row + 1)
        )
        assert any(
            qtdl_ws.cell(row, 3).value == "Lập kế hoạch"
            for row in range(1, qtdl_ws.max_row + 1)
        )
    finally:
        wb.close()


def test_functional_continuation_rows_fill_full_content_columns(temp_dir: Path) -> None:
    output = temp_dir / "output-functional-overflow.xlsx"
    _create_reference_workbook(output)

    wb = load_workbook(output)
    try:
        fn_ws = wb["NL Chuc nang"]
        fn_ws.cell(8, 7, "=F8*0.1")
        fn_ws.cell(8, 8, "=G8+F8")
        fn_ws.cell(8, 9, "=H8")
        fn_ws.cell(8, 10, "=F8")
        for col in (7, 8, 9, 10):
            fn_ws.cell(8, col).number_format = "0.00"
        wb.save(output)
    finally:
        wb.close()

    snapshot_rows = [
        {
            "service": f"svc-{idx + 1}",
            "task_id": f"T-{idx + 1}",
            "phase": "Thiết kế",
            "description": f"Task {idx + 1}",
            "effort_hours": float(idx + 1),
        }
        for idx in range(30)
    ]
    counts = populate_ulnl_output(
        output,
        {
            "rows": snapshot_rows,
            "base_hours": float(sum(row["effort_hours"] for row in snapshot_rows)),
        },
    )

    fn_overflow = counts["overflow"]["NL Chuc nang"]
    assert fn_overflow["overflowed"] is True
    assert fn_overflow["continuation_rows_used"] == 5
    assert fn_overflow["continuation_rows_preview"] == [44, 45, 46, 47, 48]

    wb = load_workbook(output, read_only=False, data_only=False)
    try:
        fn_ws = wb["NL Chuc nang"]
        # Continuation row now stores full content payload (not sparse formula-only columns).
        assert fn_ws.cell(44, 1).value == 26
        assert fn_ws.cell(44, 2).value == "svc-26"
        assert fn_ws.cell(44, 3).value == "Thiết kế"
        assert isinstance(fn_ws.cell(44, 4).value, str)
        assert fn_ws.cell(44, 5).value == "svc-26::T-26"
        assert float(fn_ws.cell(44, 6).value) == 26.0
        assert float(fn_ws.cell(44, 7).value or 0.0) == 0.0
        assert float(fn_ws.cell(44, 10).value) == 26.0
        assert fn_ws.cell(44, 11).value == "NVJ1-NC"
        assert fn_ws.cell(44, 13).value == "Nâng cấp chức năng"
        assert fn_ws.cell(44, 14).value == "Không"
        assert fn_ws.cell(44, 19).value == fn_ws.cell(44, 10).value
        assert fn_ws.cell(44, 20).value == "svc-26::T-26"
        assert fn_ws.cell(44, 24).value == "N/A"
        assert float(fn_ws.cell(44, 25).value) == 0.0
        assert fn_ws.cell(44, 26).value == "svc-26"
        # Summary rows stay formula-driven and include continuation ranges.
        assert fn_ws.cell(36, 6).value == "=SUM(F8:F32,F44:F48)"
        assert fn_ws.cell(36, 10).value == "=SUM(J8:J32,J44:J48)"
    finally:
        wb.close()


def test_nonfunctional_contiguous_block_and_qtdl_formula_cleanup(temp_dir: Path) -> None:
    output = temp_dir / "output-cleanup.xlsx"
    _create_reference_workbook(output)

    wb = load_workbook(output)
    try:
        qtdl_ws = wb["NL QTDL"]
        qtdl_ws.cell(13, 3, "=E10")
        qtdl_ws.cell(13, 4, "=E11")
        qtdl_ws.cell(13, 5, "=SUM(E10:E12)")
        qtdl_ws.cell(14, 3, "=E10")
        qtdl_ws.cell(14, 4, "=E11")
        qtdl_ws.cell(14, 5, "=SUM(E10:E12)")
        wb.save(output)
    finally:
        wb.close()

    snapshot = {
        "rows": [
            {
                "service": "svc-a",
                "task_id": "T-1.1",
                "phase": "Thiết kế",
                "description": "Example task",
                "effort_hours": 80.0,
            }
        ],
        "base_hours": 80.0,
    }
    counts = populate_ulnl_output(output, snapshot)

    nfn_overflow = counts["overflow"]["NL Phi CN"]
    assert nfn_overflow["placement_mode"] == "continuation_only_no_total_split"
    assert nfn_overflow["primary_rows_used"] == 0
    assert nfn_overflow["continuation_rows_used"] == 6
    assert nfn_overflow["continuation_rows_preview"] == [16, 17, 18, 19, 20, 21]
    assert counts["cleanup"]["NL Phi CN"]["cleared_primary_rows"] == [10, 11, 12, 13]
    assert counts["cleanup"]["NL QTDL"]["cleaned_formula_artifact_rows"] == [13, 14]

    wb = load_workbook(output, read_only=False, data_only=False)
    try:
        nfn_ws = wb["NL Phi CN"]
        qtdl_ws = wb["NL QTDL"]

        for row in (10, 11, 12, 13):
            for col in (2, 3, 4, 5):
                assert nfn_ws.cell(row, col).value in (None, "")
        assert [nfn_ws.cell(row, 2).value for row in range(16, 22)] == [1, 2, 3, 4, 5, 6]

        expected_nfr_total = round(snapshot["base_hours"] * 0.12, 2)
        allocated_nfr_total = round(
            sum(float(nfn_ws.cell(row, 5).value or 0.0) for row in range(16, 22)),
            2,
        )
        assert allocated_nfr_total == expected_nfr_total
        assert float(nfn_ws.cell(14, 5).value) == expected_nfr_total

        for row in (13, 14):
            for col in (1, 2, 3, 4, 5):
                assert qtdl_ws.cell(row, col).value is None
    finally:
        wb.close()


def test_dimension_autofit_wraps_and_expands_for_long_content(temp_dir: Path) -> None:
    output = temp_dir / "output-dimensions.xlsx"
    _create_reference_workbook(output)
    long_desc = (
        "• Đây là mô tả rất dài để kiểm tra hiển thị trong sheet chức năng.\n"
        "• Dòng thứ hai tiếp tục kéo dài nhằm xác thực auto-fit row height và wrap text hoạt động đúng."
    )
    snapshot = {
        "rows": [
            {
                "service": "svc-long",
                "task_id": "T-1.1",
                "phase": "Thiết kế",
                "description": long_desc,
                "effort_hours": 12.0,
            }
        ],
        "base_hours": 12.0,
    }
    populate_ulnl_output(output, snapshot)

    wb = load_workbook(output, read_only=False, data_only=False)
    try:
        ws = wb["NL Chuc nang"]
        target_row = 8
        assert ws.cell(target_row, 5).value == "svc-long::T-1.1"
        assert (ws.row_dimensions[target_row].height or 0) > 15.0
        assert (ws.column_dimensions["D"].width or 0) >= 45.0
        assert ws.cell(target_row, 4).alignment.wrap_text is True
        assert ws.cell(target_row, 2).alignment.wrap_text is True
        assert ws.cell(target_row, 4).alignment.vertical == "top"
    finally:
        wb.close()


def test_run_ulnc_align_warn_mode(temp_dir: Path) -> None:
    current = temp_dir / "current.xlsx"
    reference = temp_dir / "reference.xlsx"
    output = temp_dir / "output.xlsx"
    _create_current_ulnc(current)
    _create_reference_workbook(reference)
    result = run_ulnc_align(
        current_ulnc=current,
        reference_ulnl=reference,
        output=output,
        project_name="TEST",
        strict_presentation=True,
        buffer_scenario="phase1+2+3",
        include_tech_buffer=False,
        apply_sdlc_buffer=False,
        coverage_policy="warn",
        min_functional_coverage=90.0,
        min_nonfunctional_categories=6,
        min_qtdl_rows=3,
    )
    assert result["mapping"]["mapped_rows"] == 2
    assert result["coverage"]["passed"] is True
    assert result["presentation"]["required_sheet_order_ok"] is True
    assert result["buffer_guidance"]["recommended"] == "phase1+2+3"
