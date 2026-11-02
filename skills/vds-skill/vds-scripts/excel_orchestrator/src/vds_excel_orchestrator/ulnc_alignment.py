"""ULNC alignment helpers for VDS-owned ULNC output generation."""

from __future__ import annotations

import json
import math
import shutil
from collections import Counter
from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .errors import ExcelValidationError
from .target_state_status import resolve_insurance_docs_root, resolve_repo_root
from .validators import ExcelValidator

REQUIRED_ULNL_SHEETS = ("Tong hop", "NL Chuc nang", "NL Phi CN", "NL QTDL")
DEFAULT_OUTPUT_NAME = "vds-ulnc-aligned.xlsx"
DEFAULT_MAPPING_VERSION = "ulnc-align-v1"
BUFFER_MULTIPLIERS = {
    "base": 1.00,
    "phase1": 1.35,
    "phase1+2": 1.50,
    "phase1+2+3": 1.54,
    "all-in": 1.59,
}
NFR_CATEGORIES = (
    ("security", "Bảo mật", "Công việc bảo mật và an toàn thông tin"),
    ("performance", "Hiệu năng", "Công việc tối ưu hiệu năng và dung lượng"),
    ("observability", "Giám sát vận hành", "Công việc giám sát, logging, cảnh báo"),
    ("compliance", "Tuân thủ", "Công việc tuân thủ và kiểm soát quy định"),
    ("deployment/devops", "Triển khai/DevOps", "Công việc triển khai, CI/CD và vận hành"),
    ("integration", "Tích hợp", "Công việc tích hợp liên hệ thống và liên dịch vụ"),
)
QTDL_DEFAULT_ROWS = (
    ("Lập kế hoạch", "Hoạt động lập kế hoạch và phân rã công việc QTDL"),
    ("Theo dõi và báo cáo", "Hoạt động theo dõi tiến độ và báo cáo định kỳ QTDL"),
    ("Quản lý rủi ro và vấn đề", "Hoạt động quản lý rủi ro, vấn đề và phương án xử lý QTDL"),
)
NFR_TOTAL_RATIO = 0.12
QTDL_TOTAL_RATIO = 0.03
NFR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "security": ("bảo mật", "security", "oauth", "jwt", "secrets", "xác thực", "ủy quyền"),
    "performance": ("hiệu năng", "performance", "tối ưu", "throughput", "latency", "capacity"),
    "observability": (
        "giám sát",
        "observability",
        "logging",
        "log",
        "metrics",
        "alert",
        "grafana",
        "prometheus",
        "jaeger",
        "tracing",
    ),
    "compliance": ("tuân thủ", "compliance", "regulator", "audit", "kiểm soát", "policy"),
    "deployment/devops": ("triển khai", "devops", "ci/cd", "helm", "rollout", "migrations", "pipeline"),
    "integration": ("tích hợp", "integration", "kafka", "api", "spi", "gateway", "cross-service", "phụ thuộc"),
}


@dataclass(frozen=True)
class SourceRow:
    service: str
    task_id: str
    phase: str
    description: str
    effort_hours: float
    service_sheet_alias: str = ""
    source_row_index: int = 0


@dataclass(frozen=True)
class PresentationSummary:
    required_sheet_order_ok: bool
    merge_topology_ok: bool
    header_style_parity_pct: float
    strict_mode: bool
    failures: list[str]


@dataclass(frozen=True)
class WriteWindow:
    primary_start_row: int
    primary_end_row: int
    continuation_start_row: int


ULNL_WRITE_WINDOWS: dict[str, WriteWindow] = {
    # Reviewer-visible functional input block in reference template.
    "NL Chuc nang": WriteWindow(primary_start_row=8, primary_end_row=32, continuation_start_row=44),
    # Reviewer-visible NFR input block before total row.
    "NL Phi CN": WriteWindow(primary_start_row=10, primary_end_row=13, continuation_start_row=16),
    # Reviewer-visible QTDL input block before total row.
    "NL QTDL": WriteWindow(primary_start_row=10, primary_end_row=13, continuation_start_row=16),
}


def resolve_alignment_paths(
    current_ulnc: Path | None,
    reference_ulnl: Path | None,
    output: Path | None,
) -> tuple[Path, Path, Path]:
    """Resolve default input/output paths for ULNC alignment."""
    root = resolve_repo_root(Path(__file__).resolve())
    docs_root = resolve_insurance_docs_root(root)
    if current_ulnc is None:
        current_ulnc = docs_root / "projects/INSURANCE/analysis/target-state/target-ulnc/target-state-status-vi.xlsx"
    if reference_ulnl is None:
        reference_ulnl = docs_root / "projects/INSURANCE/analysis/reference/ulnc/ULNL_SAVING_CORE_Jan 2026.xlsx"
    if output is None:
        output = docs_root / "projects/INSURANCE/analysis/target-state/target-ulnc" / DEFAULT_OUTPUT_NAME
    return current_ulnc, reference_ulnl, output


def _validate_required_sheets(path: Path) -> None:
    wb = load_workbook(path, read_only=True, data_only=False)
    try:
        missing = [s for s in REQUIRED_ULNL_SHEETS if s not in wb.sheetnames]
        if missing:
            raise ExcelValidationError(
                "Reference workbook missing required ULNL sheets",
                context={"missing_sheets": missing, "path": str(path)},
            )
    finally:
        wb.close()


def _enforce_output_policy(output_path: Path, reference_path: Path) -> None:
    resolved_output = output_path.resolve()
    resolved_reference = reference_path.resolve()

    if resolved_output == resolved_reference:
        raise ExcelValidationError(
            "Output path must not overwrite reference workbook",
            context={"output": str(output_path), "reference": str(reference_path)},
        )

    if "/analysis/reference/" in str(resolved_output).replace("\\", "/"):
        raise ExcelValidationError(
            "Output path must not be inside reference directory",
            context={"output": str(output_path)},
        )


def _first_header_row(path: Path, sheet_name: str, max_scan: int = 60) -> int:
    wb = load_workbook(path, read_only=True, data_only=False)
    try:
        ws = wb[sheet_name]
        max_col = min(ws.max_column, 30)
        for row in range(1, max_scan + 1):
            vals = [ws.cell(row, c).value for c in range(1, max_col + 1)]
            non_empty = sum(1 for value in vals if value not in (None, ""))
            text_cells = sum(1 for value in vals if isinstance(value, str) and value.strip())
            if non_empty >= 3 and text_cells >= 3:
                return row
        return 1
    finally:
        wb.close()


def _extract_profile(path: Path) -> dict[str, Any]:
    wb = load_workbook(path, read_only=False, data_only=False)
    try:
        sheet_positions = {name: idx for idx, name in enumerate(wb.sheetnames)}
        profile: dict[str, Any] = {"sheet_positions": sheet_positions, "sheets": {}}
        for sheet_name in REQUIRED_ULNL_SHEETS:
            ws = wb[sheet_name]
            header_row = _first_header_row(path, sheet_name)
            top_merges = sorted(str(merge) for merge in ws.merged_cells.ranges if merge.min_row <= 20)
            anchors: list[dict[str, Any]] = []
            for col in range(1, min(ws.max_column, 10) + 1):
                cell = ws.cell(header_row, col)
                anchors.append(
                    {
                        "col": col,
                        "style_id": int(cell.style_id),
                        "fill_type": cell.fill.fill_type,
                        "align": cell.alignment.horizontal,
                        "number_format": cell.number_format,
                        "font_bold": bool(cell.font.bold),
                    }
                )
            profile["sheets"][sheet_name] = {
                "header_row": header_row,
                "top_merges": top_merges,
                "anchors": anchors,
            }
        return profile
    finally:
        wb.close()


def _compare_presentation(reference: dict[str, Any], output: dict[str, Any], strict_mode: bool) -> PresentationSummary:
    failures: list[str] = []
    expected_order = sorted(REQUIRED_ULNL_SHEETS, key=lambda name: reference["sheet_positions"].get(name, 10_000))
    actual_order = sorted(REQUIRED_ULNL_SHEETS, key=lambda name: output["sheet_positions"].get(name, 10_000))
    required_sheet_order_ok = expected_order == actual_order
    if not required_sheet_order_ok:
        failures.append("required_sheet_order_mismatch")

    merge_topology_ok = True
    for sheet_name in REQUIRED_ULNL_SHEETS:
        ref_merges = reference["sheets"][sheet_name]["top_merges"]
        out_merges = output["sheets"][sheet_name]["top_merges"]
        if ref_merges != out_merges:
            merge_topology_ok = False
            failures.append(f"merge_topology_mismatch:{sheet_name}")

    total_checks = 0
    matched_checks = 0
    fields = ("style_id", "fill_type", "align", "number_format", "font_bold")
    for sheet_name in REQUIRED_ULNL_SHEETS:
        ref_anchors = reference["sheets"][sheet_name]["anchors"]
        out_anchors = output["sheets"][sheet_name]["anchors"]
        for ref_cell, out_cell in zip(ref_anchors, out_anchors, strict=False):
            for field in fields:
                total_checks += 1
                if ref_cell[field] == out_cell[field]:
                    matched_checks += 1
    parity = round((matched_checks / total_checks) * 100, 2) if total_checks else 100.0
    if parity < 95.0:
        failures.append("header_style_parity_below_threshold")

    return PresentationSummary(
        required_sheet_order_ok=required_sheet_order_ok,
        merge_topology_ok=merge_topology_ok,
        header_style_parity_pct=parity,
        strict_mode=strict_mode,
        failures=failures,
    )


def _find_dashboard_column(header: list[Any], aliases: tuple[str, ...]) -> int:
    for idx, value in enumerate(header, start=1):
        if not isinstance(value, str):
            continue
        normalized = value.strip().lower()
        for alias in aliases:
            if alias in normalized:
                return idx
    return 0


def _normalize_text_cell(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _allocate_hours_by_weights(total_hours: float, weights: list[float]) -> list[float]:
    if total_hours <= 0 or not weights:
        return [0.0 for _ in weights]
    normalized = [max(weight, 0.0) for weight in weights]
    if sum(normalized) <= 0:
        normalized = [1.0 for _ in weights]
    total_weight = sum(normalized)
    raw = [total_hours * (weight / total_weight) for weight in normalized]
    rounded = [round(value, 2) for value in raw]
    delta = round(total_hours - sum(rounded), 2)
    if rounded:
        rounded[-1] = round(rounded[-1] + delta, 2)
    return rounded


def _phase_effort_distribution(phase: str, effort_hours: float) -> tuple[float, float, float, float]:
    normalized = phase.strip().lower()
    if "thiết kế" in normalized:
        return effort_hours, 0.0, 0.0, 0.0
    if "triển khai" in normalized:
        return 0.0, effort_hours, 0.0, 0.0
    if "kiểm thử" in normalized:
        return 0.0, 0.0, effort_hours, 0.0
    if "tích hợp" in normalized:
        return 0.0, 0.0, 0.0, effort_hours
    return 0.0, effort_hours, 0.0, 0.0


def _build_required_work_coverage(source_snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = source_snapshot.get("rows", [])
    signals: dict[str, dict[str, Any]] = {}
    for category_code, category_label, _ in NFR_CATEGORIES:
        keywords = NFR_KEYWORDS.get(category_code, ())
        matched_rows = 0
        matched_hours = 0.0
        for row in rows:
            description = str(row.get("description", "")).strip().lower()
            if description and any(keyword in description for keyword in keywords):
                matched_rows += 1
                matched_hours += float(row.get("effort_hours", 0.0))
        signals[category_code] = {
            "label": category_label,
            "matched_rows": matched_rows,
            "matched_hours": round(matched_hours, 2),
        }

    phase_counts = Counter(str(row.get("phase", "")).strip() or "unspecified" for row in rows)
    qtdl_factors = {
        "service_count": int(source_snapshot.get("service_count", 0)),
        "dependency_rows": int(source_snapshot.get("dependency_rows", 0)),
        "phase_coverage_count": sum(
            1 for phase in ("Thiết kế", "Triển khai", "Kiểm thử", "Tích hợp") if phase_counts.get(phase, 0) > 0
        ),
    }
    return {
        "nfr_signals": signals,
        "qtdl_factors": qtdl_factors,
    }


def extract_source_contract(current_ulnc: Path) -> dict[str, Any]:
    """Extract source contract snapshot from current ULNC workbook."""
    wb = load_workbook(current_ulnc, read_only=True, data_only=True)
    try:
        if "Executive Dashboard" not in wb.sheetnames:
            raise ExcelValidationError(
                "Current ULNC workbook missing Executive Dashboard sheet",
                context={"path": str(current_ulnc)},
            )
        ws = wb["Executive Dashboard"]
        header = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        service_col = _find_dashboard_column(header, ("service name", "tên dịch vụ"))
        sheet_col = _find_dashboard_column(header, ("sheet name", "tên sheet"))
        days_col = _find_dashboard_column(header, ("effort estimate (days)", "ước tính công (ngày)"))

        missing_headers: list[str] = []
        if service_col == 0:
            missing_headers.append("Service Name/Tên dịch vụ")
        if days_col == 0:
            missing_headers.append("Effort Estimate (Days)/Ước tính công (ngày)")

        source_rows: list[SourceRow] = []
        service_sheets = [
            name for name in wb.sheetnames if name not in {"Executive Dashboard", "Cross-Service Dependencies"}
        ]
        dashboard_services: list[dict[str, Any]] = []
        canonical_by_sheet: dict[str, str] = {}
        if service_col > 0:
            for row in range(2, ws.max_row + 1):
                canonical_name = _normalize_text_cell(ws.cell(row, service_col).value)
                sheet_alias = _normalize_text_cell(ws.cell(row, sheet_col).value) if sheet_col > 0 else ""
                if not canonical_name and not sheet_alias:
                    continue
                if not canonical_name:
                    canonical_name = sheet_alias
                if not sheet_alias:
                    sheet_alias = canonical_name

                dashboard_services.append(
                    {
                        "dashboard_row_index": row,
                        "canonical_name": canonical_name,
                        "sheet_alias": sheet_alias,
                    }
                )
                if sheet_alias and sheet_alias not in canonical_by_sheet:
                    canonical_by_sheet[sheet_alias] = canonical_name
                if canonical_name and canonical_name not in canonical_by_sheet:
                    canonical_by_sheet[canonical_name] = canonical_name

        ordered_service_sheets: list[str] = []
        seen_sheet_names: set[str] = set()
        service_sheet_set = set(service_sheets)
        for entry in dashboard_services:
            sheet_alias = entry["sheet_alias"]
            if sheet_alias in service_sheet_set and sheet_alias not in seen_sheet_names:
                ordered_service_sheets.append(sheet_alias)
                seen_sheet_names.add(sheet_alias)

        for sheet_name in sorted(service_sheets, key=str.casefold):
            if sheet_name not in seen_sheet_names:
                ordered_service_sheets.append(sheet_name)
                seen_sheet_names.add(sheet_name)

        for sheet_name in ordered_service_sheets:
            sheet = wb[sheet_name]
            for row in range(2, sheet.max_row + 1):
                task_id = sheet.cell(row, 1).value
                phase = sheet.cell(row, 2).value
                description = sheet.cell(row, 3).value
                effort = sheet.cell(row, 6).value
                if not isinstance(task_id, str) or not task_id.strip().startswith("T-"):
                    continue
                effort_hours = float(effort) if isinstance(effort, (int, float)) else 0.0
                source_rows.append(
                    SourceRow(
                        # Keep source sheet identity as primary service key to preserve
                        # target-state content 1:1 in trace fields (service::task).
                        service=sheet_name,
                        task_id=task_id.strip(),
                        phase=phase.strip() if isinstance(phase, str) else "",
                        description=description.strip() if isinstance(description, str) else "",
                        effort_hours=effort_hours,
                        service_sheet_alias=sheet_name,
                        source_row_index=row,
                    )
                )

        if not source_rows:
            dashboard_row_index: dict[tuple[str, str], int] = {
                (entry["canonical_name"], entry["sheet_alias"]): int(entry["dashboard_row_index"])
                for entry in dashboard_services
            }
            for row in range(2, ws.max_row + 1):
                if service_col == 0:
                    break
                service_value = ws.cell(row, service_col).value
                if not isinstance(service_value, str) or not service_value.strip():
                    continue
                canonical_name = service_value.strip()
                sheet_alias = _normalize_text_cell(ws.cell(row, sheet_col).value) if sheet_col > 0 else canonical_name
                if not sheet_alias:
                    sheet_alias = canonical_name
                effort_days = 0.0
                if days_col > 0 and isinstance(ws.cell(row, days_col).value, (int, float)):
                    effort_days = float(ws.cell(row, days_col).value)
                source_rows.append(
                    SourceRow(
                        service=canonical_name,
                        task_id=f"SVC-{row}",
                        phase="",
                        description=f"Khối lượng công việc tổng hợp cho dịch vụ {canonical_name}",
                        effort_hours=round(effort_days * 8.0, 2),
                        service_sheet_alias=sheet_alias,
                        source_row_index=dashboard_row_index.get((canonical_name, sheet_alias), row),
                    )
                )

        dependency_rows = 0
        if "Cross-Service Dependencies" in wb.sheetnames:
            dep_ws = wb["Cross-Service Dependencies"]
            for row in range(2, dep_ws.max_row + 1):
                if any(dep_ws.cell(row, c).value not in (None, "") for c in range(1, 6)):
                    dependency_rows += 1

        base_hours = round(sum(row.effort_hours for row in source_rows), 2)
        base_days = round(base_hours / 8.0, 2)
        return {
            "service_count": len({row.service for row in source_rows}),
            "source_rows": len(source_rows),
            "dependency_rows": dependency_rows,
            "missing_headers": missing_headers,
            "base_days": base_days,
            "base_hours": base_hours,
            "rows": [
                {
                    "service": row.service,
                    "service_canonical": canonical_by_sheet.get(
                        row.service_sheet_alias or row.service,
                        row.service,
                    ),
                    "service_sheet_alias": row.service_sheet_alias,
                    "task_id": row.task_id,
                    "phase": row.phase,
                    "description": row.description,
                    "effort_hours": row.effort_hours,
                    "source_row_index": row.source_row_index,
                }
                for row in source_rows
            ],
        }
    finally:
        wb.close()


def _first_appendable_row(ws: Worksheet) -> int:
    row = ws.max_row + 2
    while isinstance(ws.cell(row, 2), MergedCell):
        row += 1
    return row


def _resolve_write_window(sheet_name: str) -> WriteWindow:
    window = ULNL_WRITE_WINDOWS.get(sheet_name)
    if window is None:
        raise ExcelValidationError(
            "Missing ULNL write window configuration",
            context={"sheet_name": sheet_name, "configured_sheets": sorted(ULNL_WRITE_WINDOWS)},
        )
    return window


def _iter_primary_rows(ws: Worksheet, *, start_row: int, end_row: int, id_col: int = 2) -> list[int]:
    rows: list[int] = []
    for row in range(start_row, end_row + 1):
        if isinstance(ws.cell(row, id_col), MergedCell):
            continue
        rows.append(row)
    return rows


def _next_continuation_row(ws: Worksheet, *, start_row: int, columns: tuple[int, ...]) -> int:
    cursor = max(start_row, 1)
    while True:
        if any(isinstance(ws.cell(cursor, col), MergedCell) for col in columns):
            cursor += 1
            continue
        if any(ws.cell(cursor, col).value not in (None, "") for col in columns):
            cursor += 1
            continue
        return cursor


def _allocate_target_rows(
    ws: Worksheet,
    *,
    sheet_name: str,
    row_count: int,
    writable_columns: tuple[int, ...],
) -> tuple[list[int], dict[str, Any]]:
    window = _resolve_write_window(sheet_name)
    primary_rows = _iter_primary_rows(
        ws,
        start_row=window.primary_start_row,
        end_row=window.primary_end_row,
    )
    primary_capacity = len(primary_rows)
    placement_mode = "primary_then_continuation"
    if sheet_name == "NL Phi CN" and row_count > primary_capacity:
        # Keep NL Phi CN categories contiguous below total row to avoid split display.
        primary_used = 0
        continuation_needed = row_count
        placement_mode = "continuation_only_no_total_split"
    else:
        primary_used = min(row_count, primary_capacity)
        continuation_needed = max(row_count - primary_capacity, 0)
    continuation_rows: list[int] = []
    cursor = window.continuation_start_row
    for _ in range(continuation_needed):
        next_row = _next_continuation_row(
            ws,
            start_row=cursor,
            columns=writable_columns,
        )
        continuation_rows.append(next_row)
        cursor = next_row + 1

    continuation_preview_limit = 50
    continuation_preview = continuation_rows[:continuation_preview_limit]
    return primary_rows[:primary_used] + continuation_rows, {
        "sheet": sheet_name,
        "strategy": "primary_window_then_continuation",
        "placement_mode": placement_mode,
        "primary_window": {
            "start_row": window.primary_start_row,
            "end_row": window.primary_end_row,
            "capacity": primary_capacity,
        },
        "primary_rows_used": primary_used,
        "continuation_start_row": window.continuation_start_row,
        "continuation_rows_used": len(continuation_rows),
        "continuation_rows_preview": continuation_preview,
        "continuation_rows_preview_limit": continuation_preview_limit,
        "continuation_rows_truncated": len(continuation_rows) > continuation_preview_limit,
        "overflowed": len(continuation_rows) > 0,
    }


def _apply_functional_computed_presentation(
    ws: Worksheet,
    *,
    continuation_rows: list[int],
    template_row: int,
    computed_columns: tuple[int, ...] = (7, 8, 9, 10),
) -> None:
    """Replicate computed-column formula/style behavior for continuation rows."""
    if not continuation_rows:
        return

    for target_row in continuation_rows:
        for col in computed_columns:
            template_cell = ws.cell(template_row, col)
            target_cell = ws.cell(target_row, col)
            target_cell._style = copy(template_cell._style)
            value = template_cell.value
            if isinstance(value, str) and value.startswith("="):
                target_cell.value = Translator(value, origin=template_cell.coordinate).translate_formula(
                    target_cell.coordinate
                )
            else:
                target_cell.value = value


def _clear_cells(ws: Worksheet, *, rows: list[int], columns: tuple[int, ...]) -> None:
    for row in rows:
        for col in columns:
            ws.cell(row, col).value = None


def _cleanup_qtdl_formula_artifacts(
    ws: Worksheet,
    *,
    start_row: int,
    end_row: int,
    work_item_code_col: int = 2,
    clear_columns: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> list[int]:
    cleaned_rows: list[int] = []
    for row in range(start_row, end_row + 1):
        code_value = ws.cell(row, work_item_code_col).value
        has_code = isinstance(code_value, str) and bool(code_value.strip())
        if has_code:
            continue
        if _normalize_text_cell(ws.cell(row, 4).value).casefold() == "tổng":
            continue
        has_formula_artifact = any(
            isinstance(ws.cell(row, col).value, str) and ws.cell(row, col).value.startswith("=")
            for col in clear_columns
        )
        if not has_formula_artifact:
            continue
        for col in clear_columns:
            ws.cell(row, col).value = None
        cleaned_rows.append(row)
    return cleaned_rows


def _max_line_length(value: Any) -> int:
    if value in (None, ""):
        return 0
    text = str(value)
    return max((len(line) for line in text.splitlines()), default=0)


def _estimate_wrapped_lines(value: Any, width_chars: float) -> int:
    if value in (None, ""):
        return 1
    text = str(value)
    effective_width = max(int(width_chars) - 2, 8)
    lines = 0
    for line in text.splitlines() or [""]:
        lines += max(1, math.ceil(len(line) / effective_width))
    return max(lines, 1)


def _fit_sheet_dimensions(
    ws: Worksheet,
    *,
    target_rows: list[int],
    column_bounds: dict[int, tuple[float, float]],
    wrap_columns: tuple[int, ...],
    row_height_columns: tuple[int, ...],
    top_align_columns: tuple[int, ...] = (),
    min_row_height: float = 15.0,
    max_row_height: float = 180.0,
    line_height: float = 15.0,
) -> None:
    if not target_rows:
        return

    rows = sorted(set(target_rows))

    # Adjust column widths with bounded auto-fit and keep existing wider widths.
    for col, (min_width, max_width) in column_bounds.items():
        observed_max = 0
        for row in rows:
            observed_max = max(observed_max, _max_line_length(ws.cell(row, col).value))
        candidate = max(min_width, min(max_width, float(observed_max + 2)))
        letter = get_column_letter(col)
        current = ws.column_dimensions[letter].width
        current_width = float(current) if isinstance(current, (int, float)) else 0.0
        ws.column_dimensions[letter].width = round(max(current_width, candidate), 2)

    width_cache = {
        col: (
            float(ws.column_dimensions[get_column_letter(col)].width)
            if isinstance(ws.column_dimensions[get_column_letter(col)].width, (int, float))
            else 20.0
        )
        for col in row_height_columns
    }

    for row in rows:
        max_lines = 1
        for col in wrap_columns:
            cell = ws.cell(row, col)
            align = copy(cell.alignment)
            align.wrap_text = True
            if align.vertical in (None, ""):
                align.vertical = "top"
            cell.alignment = align
        for col in top_align_columns:
            cell = ws.cell(row, col)
            align = copy(cell.alignment)
            align.vertical = "top"
            cell.alignment = align
        for col in row_height_columns:
            max_lines = max(max_lines, _estimate_wrapped_lines(ws.cell(row, col).value, width_cache[col]))
        ws.row_dimensions[row].height = round(
            min(max_row_height, max(min_row_height, max_lines * line_height)),
            2,
        )


def _collect_functional_rows(ws: Worksheet) -> list[int]:
    rows: list[int] = []
    for row in range(1, ws.max_row + 1):
        trace = ws.cell(row, 5).value
        if isinstance(trace, str) and "::" in trace:
            rows.append(row)
    return rows


def _collect_categorized_rows(ws: Worksheet, labels: set[str]) -> list[int]:
    rows: list[int] = []
    for row in range(1, ws.max_row + 1):
        label = ws.cell(row, 3).value
        code = ws.cell(row, 2).value
        if isinstance(label, str) and label.strip() in labels and code not in (None, ""):
            rows.append(row)
    return rows


def _apply_functional_summary_formulas(ws: Worksheet, mapped_rows: list[int]) -> None:
    """Keep summary block (rows 36-43) formula-driven while including continuation rows."""
    if not mapped_rows:
        return
    primary_start = 8
    primary_end = 32
    continuation_start = 44
    max_row = max(mapped_rows)
    has_continuation = max_row >= continuation_start
    for col in range(6, 11):  # F..J
        letter = get_column_letter(col)
        if has_continuation:
            ws.cell(36, col).value = (
                f"=SUM({letter}{primary_start}:{letter}{primary_end},{letter}{continuation_start}:{letter}{max_row})"
            )
        else:
            ws.cell(36, col).value = f"=SUM({letter}{primary_start}:{letter}{primary_end})"


def _evaluate_readability(
    ws: Worksheet,
    *,
    target_rows: list[int],
    row_height_columns: tuple[int, ...],
) -> dict[str, Any]:
    if not target_rows:
        return {
            "checked_rows": 0,
            "clipping_risk_rows": 0,
            "clipping_risk_preview": [],
            "max_height_rows": 0,
        }

    clipping: list[int] = []
    max_height_rows = 0
    for row in target_rows:
        row_height = float(ws.row_dimensions[row].height or 15.0)
        if row_height >= 180.0:
            max_height_rows += 1
        needed_lines = 1
        for col in row_height_columns:
            letter = get_column_letter(col)
            width = ws.column_dimensions[letter].width
            width_chars = float(width) if isinstance(width, (int, float)) else 20.0
            needed_lines = max(
                needed_lines,
                _estimate_wrapped_lines(ws.cell(row, col).value, width_chars),
            )
        needed_height = needed_lines * 15.0
        if row_height + 1.0 < needed_height:
            clipping.append(row)

    return {
        "checked_rows": len(target_rows),
        "clipping_risk_rows": len(clipping),
        "clipping_risk_preview": clipping[:20],
        "max_height_rows": max_height_rows,
    }


def _populate_functional_sheet(ws: Worksheet, source_rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    window = _resolve_write_window(ws.title)
    primary_rows = _iter_primary_rows(
        ws,
        start_row=window.primary_start_row,
        end_row=window.primary_end_row,
    )

    if not source_rows:
        _allocated_rows, overflow = _allocate_target_rows(
            ws,
            sheet_name=ws.title,
            row_count=0,
            writable_columns=(2, 3, 4, 5, 6),
        )
        return 0, overflow

    target_rows, overflow = _allocate_target_rows(
        ws,
        sheet_name=ws.title,
        row_count=len(source_rows),
        writable_columns=(2, 3, 4, 5, 6),
    )
    written = 0
    template_row = primary_rows[0] if primary_rows else target_rows[0]
    for idx, (target_row, row) in enumerate(zip(target_rows, source_rows, strict=False), start=1):
        effort_hours = round(float(row.get("effort_hours", 0.0)), 2)
        phase = str(row.get("phase", "Phát triển mới") or "Phát triển mới")
        service_name = str(row.get("service", "")).strip()
        service_alias = str(row.get("service_sheet_alias", "")).strip()
        task_id = str(row.get("task_id", "")).strip()
        description = row.get("description", f"Triển khai hạng mục cho dịch vụ {service_name}")
        trace = f"{service_name}::{task_id}".strip(":")
        fn_code = "NVJ1-NC"
        unit_test_flag = "Có" if "kiểm thử" in phase.strip().lower() else "Không"
        solution_h, dev_h, unit_test_h, test_h = _phase_effort_distribution(phase, effort_hours)
        total_post_reuse = round(solution_h + dev_h + unit_test_h + test_h, 2)
        o, p, q, r = solution_h, dev_h, unit_test_h, test_h
        total_pre_reuse = round(o + p + q + r, 2)

        # Keep row style consistent with reference template row.
        for col in range(1, 27):
            ws.cell(target_row, col)._style = copy(ws.cell(template_row, col)._style)
            ws.cell(target_row, col).value = None

        ws.cell(target_row, 1, idx)  # TT
        ws.cell(target_row, 2, service_name or service_alias)  # Yêu cầu nâng cấp
        ws.cell(target_row, 3, phase)  # Tên chức năng (phase label)
        ws.cell(
            target_row,
            4,
            description,
        )
        ws.cell(target_row, 5, trace)  # Loại xử lý/trace
        ws.cell(target_row, 6, solution_h)  # Giải pháp
        ws.cell(target_row, 7, dev_h)  # Phát triển
        ws.cell(target_row, 8, unit_test_h)  # Unit test
        ws.cell(target_row, 9, test_h)  # Kiểm thử
        ws.cell(target_row, 10, total_post_reuse)  # Tổng nỗ lực (manhours)
        ws.cell(target_row, 11, fn_code)  # Mã chức năng
        ws.cell(target_row, 12, row.get("source_row_index", 0))  # source row id
        ws.cell(target_row, 13, "Nâng cấp chức năng")  # Tên loại chức năng
        ws.cell(target_row, 14, unit_test_flag)  # Có unit test hay không?
        ws.cell(target_row, 15, o)
        ws.cell(target_row, 16, p)
        ws.cell(target_row, 17, q)
        ws.cell(target_row, 18, r)
        ws.cell(target_row, 19, total_pre_reuse)
        ws.cell(target_row, 20, trace)  # Chi tiết tái sử dụng / trace
        ws.cell(target_row, 21, 0.0)
        ws.cell(target_row, 22, 0.0)
        ws.cell(target_row, 23, 0.0)
        ws.cell(target_row, 24, "N/A")
        ws.cell(target_row, 25, 0.0)
        ws.cell(target_row, 26, service_alias or service_name)
        written += 1

    return written, overflow


def _populate_nonfunctional_sheet(
    ws: Worksheet, base_hours: float, required_work: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    target_rows, overflow = _allocate_target_rows(
        ws,
        sheet_name=ws.title,
        row_count=len(NFR_CATEGORIES),
        writable_columns=(2, 3, 4, 5),
    )
    written = 0
    total_nfr_hours = round(base_hours * NFR_TOTAL_RATIO, 2) if base_hours > 0 else 0.0
    nfr_signals = required_work.get("nfr_signals", {})
    weights = []
    for category_code, _, _ in NFR_CATEGORIES:
        signal = nfr_signals.get(category_code, {})
        matched_hours = float(signal.get("matched_hours", 0.0))
        matched_rows = int(signal.get("matched_rows", 0))
        weights.append(matched_hours if matched_hours > 0 else float(matched_rows or 1))
    category_hours = _allocate_hours_by_weights(total_nfr_hours, weights)

    for idx, (target_row, (category, category_label, description)) in enumerate(
        zip(target_rows, NFR_CATEGORIES, strict=False), start=1
    ):
        signal = nfr_signals.get(category, {})
        matched_rows = int(signal.get("matched_rows", 0))
        ws.cell(target_row, 2, idx)
        ws.cell(target_row, 3, category_label)
        ws.cell(target_row, 4, f"{description} (bao phủ {matched_rows} hạng mục từ target-state)")
        ws.cell(target_row, 5, category_hours[idx - 1] if idx - 1 < len(category_hours) else 0.0)
        written += 1
    return written, overflow


def _populate_qtdl_sheet(ws: Worksheet, base_hours: float, required_work: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    target_rows, overflow = _allocate_target_rows(
        ws,
        sheet_name=ws.title,
        row_count=len(QTDL_DEFAULT_ROWS),
        writable_columns=(2, 3, 4, 5),
    )
    written = 0
    total_qtdl_hours = round(base_hours * QTDL_TOTAL_RATIO, 2) if base_hours > 0 else 0.0
    qtdl_factors = required_work.get("qtdl_factors", {})
    dependency_rows = int(qtdl_factors.get("dependency_rows", 0))
    service_count = int(qtdl_factors.get("service_count", 0))
    # Planning and risk rows get more share when dependency/services are high.
    weights = [
        1.0 + (service_count / 100.0),
        1.0,
        1.0 + (dependency_rows / 200.0),
    ]
    row_hours = _allocate_hours_by_weights(total_qtdl_hours, weights)
    for idx, (target_row, (label, description)) in enumerate(
        zip(target_rows, QTDL_DEFAULT_ROWS, strict=False), start=1
    ):
        ws.cell(target_row, 2, idx)
        ws.cell(target_row, 3, label)
        ws.cell(
            target_row,
            4,
            f"{description} (dịch vụ: {service_count}, phụ thuộc: {dependency_rows})",
        )
        ws.cell(target_row, 5, row_hours[idx - 1] if idx - 1 < len(row_hours) else 0.0)
        written += 1
    return written, overflow


def populate_ulnl_output(output_path: Path, source_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Populate required ULNL sheets in the output workbook."""
    wb = load_workbook(output_path, read_only=False, data_only=False)
    try:
        fn_ws = wb["NL Chuc nang"]
        nfn_ws = wb["NL Phi CN"]
        qtdl_ws = wb["NL QTDL"]
        required_work = _build_required_work_coverage(source_snapshot)
        functional_rows, functional_overflow = _populate_functional_sheet(fn_ws, source_snapshot["rows"])
        nonfunctional_rows, nonfunctional_overflow = _populate_nonfunctional_sheet(
            nfn_ws, source_snapshot["base_hours"], required_work
        )
        qtdl_rows, qtdl_overflow = _populate_qtdl_sheet(qtdl_ws, source_snapshot["base_hours"], required_work)
        nfr_rows_cleared: list[int] = []
        if nonfunctional_overflow.get("placement_mode") == "continuation_only_no_total_split":
            nfr_window = _resolve_write_window("NL Phi CN")
            nfr_rows_to_clear = _iter_primary_rows(
                nfn_ws,
                start_row=nfr_window.primary_start_row,
                end_row=nfr_window.primary_end_row,
            )
            _clear_cells(nfn_ws, rows=nfr_rows_to_clear, columns=(1, 2, 3, 4, 5))
            nfr_rows_cleared = nfr_rows_to_clear

        qtdl_window = _resolve_write_window("NL QTDL")
        qtdl_rows_cleaned = _cleanup_qtdl_formula_artifacts(
            qtdl_ws,
            start_row=qtdl_window.primary_start_row,
            end_row=qtdl_window.primary_end_row + 1,
        )

        functional_rows_to_fit = _collect_functional_rows(fn_ws)
        _fit_sheet_dimensions(
            fn_ws,
            target_rows=functional_rows_to_fit,
            column_bounds={
                2: (24.0, 40.0),
                3: (12.0, 24.0),
                4: (45.0, 110.0),
                5: (22.0, 55.0),
                6: (8.0, 14.0),
                7: (8.0, 14.0),
                8: (8.0, 14.0),
                9: (8.0, 14.0),
                10: (10.0, 16.0),
                11: (10.0, 16.0),
                13: (18.0, 30.0),
                20: (22.0, 55.0),
                26: (20.0, 40.0),
            },
            wrap_columns=(2, 4, 5, 20),
            row_height_columns=(2, 4, 5, 20),
            top_align_columns=(2, 3, 4, 5, 13, 20, 26),
        )
        _apply_functional_summary_formulas(fn_ws, functional_rows_to_fit)

        nfr_rows_to_fit = _collect_categorized_rows(
            nfn_ws,
            labels={label for _, label, _ in NFR_CATEGORIES},
        )
        _fit_sheet_dimensions(
            nfn_ws,
            target_rows=nfr_rows_to_fit,
            column_bounds={
                2: (6.0, 10.0),
                3: (18.0, 32.0),
                4: (40.0, 95.0),
                5: (10.0, 16.0),
            },
            wrap_columns=(3, 4),
            row_height_columns=(4,),
            top_align_columns=(3, 4),
        )

        qtdl_rows_to_fit = _collect_categorized_rows(
            qtdl_ws,
            labels={label for label, _ in QTDL_DEFAULT_ROWS},
        )
        _fit_sheet_dimensions(
            qtdl_ws,
            target_rows=qtdl_rows_to_fit,
            column_bounds={
                2: (6.0, 10.0),
                3: (18.0, 34.0),
                4: (40.0, 95.0),
                5: (10.0, 16.0),
            },
            wrap_columns=(3, 4),
            row_height_columns=(4,),
            top_align_columns=(3, 4),
        )

        readability = {
            "NL Chuc nang": _evaluate_readability(
                fn_ws,
                target_rows=functional_rows_to_fit,
                row_height_columns=(2, 4, 5, 20),
            ),
            "NL Phi CN": _evaluate_readability(
                nfn_ws,
                target_rows=nfr_rows_to_fit,
                row_height_columns=(4,),
            ),
            "NL QTDL": _evaluate_readability(
                qtdl_ws,
                target_rows=qtdl_rows_to_fit,
                row_height_columns=(4,),
            ),
        }

        # Keep reference summary anchors aligned with our generated totals.
        nfr_hours = round(source_snapshot["base_hours"] * NFR_TOTAL_RATIO, 2)
        qtdl_hours = round(source_snapshot["base_hours"] * QTDL_TOTAL_RATIO, 2)
        # NL Chuc nang summary block (rows 36-43) remains formula-driven.
        # J36 continues to feed Tong hop!E13 through formula chain.
        nfn_ws.cell(14, 5, nfr_hours)  # Preserve explicit total anchor used by D6/E14 chain
        qtdl_ws.cell(15, 5, qtdl_hours)  # Preserve explicit total anchor used by Tong hop!E15

        wb.save(output_path)
        return {
            "functional_rows": functional_rows,
            "nonfunctional_rows": nonfunctional_rows,
            "qtdl_rows": qtdl_rows,
            "overflow": {
                "NL Chuc nang": functional_overflow,
                "NL Phi CN": nonfunctional_overflow,
                "NL QTDL": qtdl_overflow,
            },
            "cleanup": {
                "NL Phi CN": {
                    "cleared_primary_rows": nfr_rows_cleared,
                },
                "NL QTDL": {
                    "cleaned_formula_artifact_rows": qtdl_rows_cleaned,
                },
            },
            "required_work_coverage": required_work,
            "readability": readability,
        }
    finally:
        wb.close()


def _build_buffer_scenarios(base_hours: float) -> dict[str, dict[str, float]]:
    scenarios: dict[str, dict[str, float]] = {}
    for scenario, multiplier in BUFFER_MULTIPLIERS.items():
        hours = round(base_hours * multiplier, 2)
        scenarios[scenario] = {
            "multiplier": multiplier,
            "total_hours": hours,
            "total_md": round(hours / 8.0, 2),
        }
    return scenarios


def _compute_coverage(
    *,
    source_rows: int,
    mapped_functional_rows: int,
    nonfunctional_rows: int,
    qtdl_rows: int,
    min_functional_coverage: float,
    min_nonfunctional_categories: int,
    min_qtdl_rows: int,
) -> dict[str, Any]:
    functional_coverage = round((mapped_functional_rows / source_rows) * 100, 2) if source_rows > 0 else 0.0
    checks = {
        "functional_coverage_ok": functional_coverage >= min_functional_coverage,
        "nonfunctional_categories_ok": nonfunctional_rows >= min_nonfunctional_categories,
        "qtdl_rows_ok": qtdl_rows >= min_qtdl_rows,
    }
    return {
        "functional_coverage_pct": functional_coverage,
        "nonfunctional_categories": nonfunctional_rows,
        "qtdl_rows": qtdl_rows,
        "thresholds": {
            "min_functional_coverage_pct": min_functional_coverage,
            "min_nonfunctional_categories": min_nonfunctional_categories,
            "min_qtdl_rows": min_qtdl_rows,
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def run_ulnc_align(
    *,
    current_ulnc: Path,
    reference_ulnl: Path,
    output: Path,
    project_name: str,
    strict_presentation: bool,
    buffer_scenario: str,
    include_tech_buffer: bool,
    apply_sdlc_buffer: bool,
    coverage_policy: str,
    min_functional_coverage: float,
    min_nonfunctional_categories: int,
    min_qtdl_rows: int,
) -> dict[str, Any]:
    """Run ULNC alignment using reference template as baseline."""
    if buffer_scenario not in BUFFER_MULTIPLIERS:
        raise ExcelValidationError(
            "Invalid buffer scenario",
            context={"buffer_scenario": buffer_scenario, "allowed": sorted(BUFFER_MULTIPLIERS)},
        )
    if coverage_policy not in {"warn", "error"}:
        raise ExcelValidationError(
            "Invalid coverage policy",
            context={"coverage_policy": coverage_policy, "allowed": ["warn", "error"]},
        )

    ExcelValidator.validate_file(current_ulnc)
    ExcelValidator.validate_file(reference_ulnl)
    _validate_required_sheets(reference_ulnl)
    _enforce_output_policy(output, reference_ulnl)

    source_snapshot = extract_source_contract(current_ulnc)
    if source_snapshot["missing_headers"]:
        raise ExcelValidationError(
            "Current ULNC workbook is missing required headers",
            context={"missing_headers": source_snapshot["missing_headers"]},
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(reference_ulnl, output)
    mapping_counts = populate_ulnl_output(output, source_snapshot)

    reference_profile = _extract_profile(reference_ulnl)
    output_profile = _extract_profile(output)
    presentation = _compare_presentation(
        reference=reference_profile,
        output=output_profile,
        strict_mode=strict_presentation,
    )
    if strict_presentation and presentation.failures:
        raise ExcelValidationError(
            "Strict presentation validation failed",
            context={
                "failures": presentation.failures,
                "header_style_parity_pct": presentation.header_style_parity_pct,
            },
        )

    coverage = _compute_coverage(
        source_rows=source_snapshot["source_rows"],
        mapped_functional_rows=mapping_counts["functional_rows"],
        nonfunctional_rows=mapping_counts["nonfunctional_rows"],
        qtdl_rows=mapping_counts["qtdl_rows"],
        min_functional_coverage=min_functional_coverage,
        min_nonfunctional_categories=min_nonfunctional_categories,
        min_qtdl_rows=min_qtdl_rows,
    )
    coverage_failures = [name for name, passed in coverage["checks"].items() if not passed]
    phase_counts = Counter(row.get("phase", "").strip() or "unspecified" for row in source_snapshot["rows"])
    required_phases = {"Thiết kế", "Triển khai", "Kiểm thử", "Tích hợp"}
    missing_phases = sorted(phase for phase in required_phases if phase_counts.get(phase, 0) == 0)
    phase_coverage = {
        "phase_counts": dict(phase_counts),
        "required_phases_present": len(missing_phases) == 0,
        "missing_required_phases": missing_phases,
    }
    if not phase_coverage["required_phases_present"]:
        coverage_failures.append("required_phase_coverage_missing")

    if coverage_policy == "error" and coverage_failures:
        raise ExcelValidationError(
            "Coverage policy failed",
            context={"coverage_failures": coverage_failures, "coverage": coverage},
        )

    scenarios = _build_buffer_scenarios(source_snapshot["base_hours"])
    selected_scenario = scenarios[buffer_scenario]
    buffer_guidance = {
        "minimum": "phase1",
        "recommended": "phase1+2+3",
        "upper_reserve": "all-in",
        "notes": [
            "phase1 dùng cho mức dự phòng tối thiểu khi chốt kế hoạch triển khai",
            "phase1+2+3 dùng cho kế hoạch an toàn với dư địa cho rủi ro và phát sinh",
            "all-in dùng cho bối cảnh có độ bất định cao hoặc thay đổi liên tục",
        ],
    }

    report = {
        "project_name": project_name,
        "mapping_version": DEFAULT_MAPPING_VERSION,
        "output_file": str(output),
        "source_file": str(current_ulnc),
        "reference_file": str(reference_ulnl),
        "required_sheets": list(REQUIRED_ULNL_SHEETS),
        "settings": {
            "strict_presentation": strict_presentation,
            "buffer_scenario": buffer_scenario,
            "include_tech_buffer": include_tech_buffer,
            "apply_sdlc_buffer": apply_sdlc_buffer,
            "coverage_policy": coverage_policy,
        },
        "source_snapshot": {
            "service_count": source_snapshot["service_count"],
            "source_rows": source_snapshot["source_rows"],
            "dependency_rows": source_snapshot["dependency_rows"],
            "base_days": source_snapshot["base_days"],
            "base_hours": source_snapshot["base_hours"],
        },
        "mapping": {
            "mapped_rows": mapping_counts["functional_rows"],
            "unmapped_rows": max(source_snapshot["source_rows"] - mapping_counts["functional_rows"], 0),
            "unmapped_items": [],
            "functional_rows": mapping_counts["functional_rows"],
            "nonfunctional_rows": mapping_counts["nonfunctional_rows"],
            "qtdl_rows": mapping_counts["qtdl_rows"],
            "overflow": mapping_counts.get("overflow", {}),
            "cleanup": mapping_counts.get("cleanup", {}),
            "required_work_coverage": mapping_counts.get("required_work_coverage", {}),
            "readability": mapping_counts.get("readability", {}),
        },
        "coverage": coverage,
        "phase_coverage": phase_coverage,
        "selected_scenario": selected_scenario,
        "scenarios": scenarios,
        "buffer_guidance": buffer_guidance,
        "presentation": {
            "required_sheet_order_ok": presentation.required_sheet_order_ok,
            "merge_topology_ok": presentation.merge_topology_ok,
            "header_style_parity_pct": presentation.header_style_parity_pct,
            "strict_mode": presentation.strict_mode,
            "failures": presentation.failures,
        },
        "warnings": [],
    }

    if coverage_failures and coverage_policy == "warn":
        report["warnings"].append({"code": "coverage_policy_warn", "details": coverage_failures})
    overflow_sheets = [
        sheet_name for sheet_name, overflow in mapping_counts.get("overflow", {}).items() if overflow.get("overflowed")
    ]
    if overflow_sheets:
        report["warnings"].append(
            {
                "code": "write_window_overflow",
                "details": {
                    "sheets": overflow_sheets,
                    "strategy": "primary_window_then_continuation",
                },
            }
        )
    if buffer_scenario != "base":
        report["warnings"].append(
            {
                "code": "buffer_applied_non_base",
                "details": {
                    "buffer_scenario": buffer_scenario,
                    "multiplier": selected_scenario["multiplier"],
                    "note": "Effort output is scaled from source base effort due to selected buffer scenario.",
                },
            }
        )

    report_path = output.with_suffix(".alignment-report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["report_file"] = str(report_path)
    return report
