"""
Create a summary sheet with main services and total effort per service.
- Source: VDS_Est_Detail_Target_State
- Output sheet: VDS_Est_Detail_Services_Total (overwrites if exists)
- Columns: #, Service Name, Total Hours, Total Days, Remark
- Keeps header styling from original Est Detail header.
"""

from copy import copy

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

SRC_SHEET = "VDS_Est_Detail_Target_State"
NEW_SHEET = "VDS_Est_Detail_Services_Total"
FILE_PATH = "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"


def main() -> None:
    wb = load_workbook(FILE_PATH, read_only=False)
    detail = wb[SRC_SHEET]

    # Remove old sheet if exists
    if NEW_SHEET in wb.sheetnames:
        idx = wb.sheetnames.index(NEW_SHEET)
        wb.remove(wb[NEW_SHEET])
    new_ws = wb.create_sheet(NEW_SHEET)

    # Copy header style from Est Detail header row 8 (same as source sheet)
    header_row_src = 8
    headers = ["#", "Task Name", "Coding Effort (hours)", "in days", "Remarks"]
    # Target columns: B,C,D,E,F (matching original positions for readability)
    target_cols = [2, 3, 4, 5, 6]

    for header, col in zip(headers, target_cols, strict=False):
        cell_src = detail.cell(header_row_src, col)
        cell_new = new_ws.cell(1, col)
        cell_new.value = header
        cell_new.font = copy(cell_src.font)
        cell_new.fill = copy(cell_src.fill)
        cell_new.alignment = Alignment(horizontal="center", vertical="center")

    # Borders and widths are not strictly needed for summary; column widths can be set
    new_ws.column_dimensions["B"].width = detail.column_dimensions["B"].width or 8
    new_ws.column_dimensions["C"].width = detail.column_dimensions["C"].width or 50
    new_ws.column_dimensions["D"].width = detail.column_dimensions["D"].width or 18
    new_ws.column_dimensions["E"].width = detail.column_dimensions["E"].width or 12
    new_ws.column_dimensions["F"].width = detail.column_dimensions["F"].width or 60

    # Iterate services and accumulate totals
    services = []
    current_service = None

    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col4 = detail.cell(row, 4).value
        col5 = detail.cell(row, 5).value
        col6 = detail.cell(row, 6).value

        if col3 and isinstance(col2, (int, float)):
            # New service row
            if current_service:
                services.append(current_service)
            current_service = {
                "section": int(col2),
                "name": str(col3),
                "remark": str(col6) if col6 else "",
                "hours": 0.0,
                "days": 0.0,
            }
        elif col3 and current_service:
            # Task row
            # Hours are in col4 (may be formula); days in col5
            days = float(col5) if isinstance(col5, (int, float)) else 0.0
            hours = float(col4) if isinstance(col4, (int, float)) else (days * 8)
            current_service["hours"] += hours
            current_service["days"] += days

    # Append last service
    if current_service:
        services.append(current_service)

    # Write services to new sheet starting row 2
    total_hours = 0.0
    total_days = 0.0
    for idx, svc in enumerate(services, start=2):
        new_ws.cell(idx, 2).value = svc["section"]
        new_ws.cell(idx, 3).value = svc["name"]
        new_ws.cell(idx, 4).value = round(svc["hours"], 1)
        new_ws.cell(idx, 5).value = round(svc["days"], 1)
        new_ws.cell(idx, 6).value = svc["remark"]

        total_hours += svc["hours"]
        total_days += svc["days"]

    # Total row
    total_row = len(services) + 2
    total_fill = PatternFill(start_color="FFF2F2F2", end_color="FFF2F2F2", fill_type="solid")
    bold_font = Font(bold=True)

    new_ws.cell(total_row, 3).value = "Tổng cộng"
    new_ws.cell(total_row, 3).font = bold_font
    new_ws.cell(total_row, 4).value = round(total_hours, 1)
    new_ws.cell(total_row, 4).font = bold_font
    new_ws.cell(total_row, 5).value = round(total_days, 1)
    new_ws.cell(total_row, 5).font = bold_font
    for col in [3, 4, 5, 6]:
        new_ws.cell(total_row, col).fill = total_fill

    wb.save(FILE_PATH)
    print(
        f"✅ Created sheet {NEW_SHEET} with {len(services)} services. Totals: {total_hours:.1f} hours / {total_days:.1f} days"
    )


if __name__ == "__main__":
    main()
