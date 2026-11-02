"""
Create a buffered summary sheet with phased buffers.
- Source: VDS_Est_Detail_Target_State (reads actual values, data_only)
- Output sheet: VDS_Buffered_Summary (overwrites if exists)
- Scenarios:
    * Base
    * Phase 1 (+35%) – critical gaps
    * Phase 1+2 (+50%) – critical + important
    * Phase 1+2+3 (+54%) – critical + important + optional
    * Tech/Integration buffer (+5%) – optional hidden complexity
    * All-in including tech (+59%)
"""

from openpyxl import load_workbook

SRC_SHEET = "VDS_Est_Detail_Target_State"
NEW_SHEET = "VDS_Buffered_Summary"
FILE_PATH = "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"


def compute_base_totals(wb):
    """Sum days/hours from detail sheet (data_only)."""
    detail = wb[SRC_SHEET]
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


def add_row(ws, row_idx, label, multiplier, base_days, base_hours, note=""):
    days = round(base_days * multiplier, 1)
    hours = round(base_hours * multiplier, 1)
    ws.cell(row_idx, 1, label)
    ws.cell(row_idx, 2, days)
    ws.cell(row_idx, 3, hours)
    ws.cell(row_idx, 4, note)


def main() -> None:
    wb = load_workbook(FILE_PATH, read_only=False, data_only=True)
    if SRC_SHEET not in wb.sheetnames:
        raise SystemExit(f"Missing sheet {SRC_SHEET}")

    base_days, base_hours = compute_base_totals(wb)

    # Remove old sheet if exists
    if NEW_SHEET in wb.sheetnames:
        ws_old = wb[NEW_SHEET]
        wb.remove(ws_old)
    ws = wb.create_sheet(NEW_SHEET)

    # Headers
    ws.cell(1, 1, "Scenario")
    ws.cell(1, 2, "Days")
    ws.cell(1, 3, "Hours")
    ws.cell(1, 4, "Notes")

    row = 2
    add_row(ws, row, "Base", 1.0, base_days, base_hours, "Current estimation")
    row += 1
    add_row(
        ws,
        row,
        "Phase 1 (+35%)",
        1.35,
        base_days,
        base_hours,
        "Critical gaps: Non-functional, Risk/Contingency, Deployment/DevOps",
    )
    row += 1
    add_row(
        ws,
        row,
        "Phase 1+2 (+50%)",
        1.50,
        base_days,
        base_hours,
        "Add Documentation + Monitoring/Alerting",
    )
    row += 1
    add_row(ws, row, "Phase 1+2+3 (+54%)", 1.54, base_days, base_hours, "Add Training/KT")
    row += 1
    add_row(
        ws,
        row,
        "Tech/Integration buffer (+5%)",
        1.05,
        base_days,
        base_hours,
        "Hidden complexity: library upgrades, external integrations",
    )
    row += 1
    add_row(
        ws,
        row,
        "All-in incl. Tech (+59%)",
        1.59,
        base_days,
        base_hours,
        "Phase1+2+3 plus tech/integration buffer",
    )

    wb.save(FILE_PATH)
    print(
        f"✅ Created {NEW_SHEET}: base={base_days} days / {base_hours} hours; all-in={round(base_days * 1.59, 1)} days"
    )


if __name__ == "__main__":
    main()
