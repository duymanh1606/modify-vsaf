"""
Apply phased buffers directly into existing sheets (no new sheets).
Actions:
- Remove VDS_Buffered_Summary if present.
- Compute base totals from VDS_Est_Detail_Target_State (data_only).
- Append buffered totals to:
    * VDS_Summary_Target_State (hours/days)
    * VDS_Est_Detail_Services_Total (hours/days)

Buffers:
- Phase 1: +35% (1.35x)
- Phase 1+2: +50% (1.50x)
- Phase 1+2+3: +54% (1.54x)
- Tech/Integration: +5% (1.05x)
- All-in incl. Tech: +59% (1.59x)
"""

from copy import copy

from openpyxl import load_workbook

FILE_PATH = "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
DETAIL_SHEET = "VDS_Est_Detail_Target_State"
SUMMARY_SHEET = "VDS_Summary_Target_State"
SERVICES_TOTAL_SHEET = "VDS_Est_Detail_Services_Total"
BUFFER_SHEET = "VDS_Buffered_Summary"

BUFFERS = [
    (
        "Phase 1 (+35%)",
        1.35,
        "Critical: Non-functional, Risk/Contingency, Deployment/DevOps",
    ),
    ("Phase 1+2 (+50%)", 1.50, "Add Documentation + Monitoring/Alerting"),
    ("Phase 1+2+3 (+54%)", 1.54, "Add Training/KT"),
    (
        "Tech/Integration (+5%)",
        1.05,
        "Hidden complexity: library upgrades, external integrations",
    ),
    ("All-in incl. Tech (+59%)", 1.59, "Phases + tech/integration buffer"),
]


def compute_base_totals() -> tuple[float, float]:
    wb = load_workbook(FILE_PATH, data_only=True)
    detail = wb[DETAIL_SHEET]
    total_days = 0.0
    total_hours = 0.0
    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col4 = detail.cell(row, 4).value
        col5 = detail.cell(row, 5).value
        if col3 and not isinstance(col2, (int, float)) and col5:
            days = float(col5) if isinstance(col5, (int, float)) else 0.0
            hours = float(col4) if isinstance(col4, (int, float)) else (days * 8)
            total_days += days
            total_hours += hours
    return round(total_days, 1), round(total_hours, 1)


def append_to_summary(wb, base_days: float, base_hours: float) -> None:
    ws = wb[SUMMARY_SHEET]
    start_row = ws.max_row + 2
    ws.cell(start_row, 2, "Buffers (phased)").font = copy(ws.cell(8, 3).font) if ws.cell(8, 3).font else None
    row = start_row + 1
    for label, mult, note in BUFFERS:
        ws.cell(row, 2, label)
        ws.cell(row, 4, round(base_hours * mult, 1))
        ws.cell(row, 5, round(base_days * mult, 1))
        ws.cell(row, 6, note)
        row += 1


def append_to_services_total(wb, base_days: float, base_hours: float) -> None:
    ws = wb[SERVICES_TOTAL_SHEET]
    # Find last used row (service totals already present)
    last_row = ws.max_row
    # Add spacer
    row = last_row + 2
    ws.cell(row, 3, "Buffered totals")
    ws.cell(row, 3).font = copy(ws.cell(1, 3).font) if ws.cell(1, 3).font else None
    row += 1
    for label, mult, _ in BUFFERS:
        ws.cell(row, 3, label)
        ws.cell(row, 4, round(base_hours * mult, 1))
        ws.cell(row, 5, round(base_days * mult, 1))
        row += 1


def main() -> None:
    base_days, base_hours = compute_base_totals()
    wb = load_workbook(FILE_PATH, read_only=False)

    # Remove buffered summary sheet if exists
    if BUFFER_SHEET in wb.sheetnames:
        wb.remove(wb[BUFFER_SHEET])

    if SUMMARY_SHEET not in wb.sheetnames:
        raise SystemExit(f"Missing sheet {SUMMARY_SHEET}")
    if SERVICES_TOTAL_SHEET not in wb.sheetnames:
        raise SystemExit(f"Missing sheet {SERVICES_TOTAL_SHEET}")

    append_to_summary(wb, base_days, base_hours)
    append_to_services_total(wb, base_days, base_hours)

    wb.save(FILE_PATH)
    print(
        f"✅ Updated buffers inline. Base={base_days} days / {base_hours} hours. Removed sheet {BUFFER_SHEET} if present."
    )


if __name__ == "__main__":
    main()
