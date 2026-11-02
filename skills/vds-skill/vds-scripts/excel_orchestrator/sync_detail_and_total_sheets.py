"""
Sync VDS_Est_Detail_Target_State and VDS_Est_Detail_Services_Total sheets.
- Calculate correct totals from Detail sheet
- Update Services Total sheet with correct data
- Fix remarks: only service rows should have remarks, task rows should be empty
- Ensure all numbers match between sheets
"""

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

FILE_PATH = "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
DETAIL_SHEET = "VDS_Est_Detail_Target_State"
TOTAL_SHEET = "VDS_Est_Detail_Services_Total"


def get_service_totals(ws_detail):
    """Extract service totals from detail sheet."""
    services = {}

    for row in range(10, ws_detail.max_row + 1):
        col2 = ws_detail.cell(row, 2).value
        col3 = ws_detail.cell(row, 3).value
        col6 = ws_detail.cell(row, 6).value

        # Service header row
        if isinstance(col2, (int, float)) and col2 > 0 and col3:
            service_num = int(col2)
            service_name = str(col3).strip()
            remark = str(col6).strip() if col6 else ""

            # Calculate totals from tasks below
            total_days = 0.0
            total_hours = 0.0

            # Look ahead for tasks
            for task_row in range(row + 1, ws_detail.max_row + 1):
                task_col2 = ws_detail.cell(task_row, 2).value
                task_col3 = ws_detail.cell(task_row, 3).value
                task_col5 = ws_detail.cell(task_row, 5).value

                # Stop at next service
                if isinstance(task_col2, (int, float)) and task_col2 > 0:
                    break

                # Task row
                if task_col3 and isinstance(task_col5, (int, float)):
                    total_days += float(task_col5)
                    total_hours += float(task_col5) * 8

            services[service_num] = {
                "name": service_name,
                "days": total_days,
                "hours": total_hours,
                "remark": remark,
            }

    return services


def clean_remarks(ws_detail):
    """Clean remarks: only service rows should have remarks."""
    cleaned = 0

    for row in range(10, ws_detail.max_row + 1):
        col2 = ws_detail.cell(row, 2).value
        col3 = ws_detail.cell(row, 3).value
        col6 = ws_detail.cell(row, 6).value

        # Service row - keep remark if meaningful
        if isinstance(col2, (int, float)) and col2 > 0 and col3:
            service_name = str(col3).strip()
            remark = str(col6).strip() if col6 else ""

            # If remark is too short or looks like it belongs to a task, clear it
            if remark and (len(remark) < 10 or remark.startswith("Mục tiêu:")):
                ws_detail.cell(row, 6).value = None
                cleaned += 1
            # If no remark, add a default one based on service name
            elif not remark:
                # Extract main service name (before colon or parentheses)
                main_name = service_name.split(":")[0].split("(")[0].strip()
                ws_detail.cell(row, 6).value = f"Service for {main_name}"
                cleaned += 1

        # Task row - clear remark
        elif col3 and not isinstance(col2, (int, float)):
            if col6:
                ws_detail.cell(row, 6).value = None
                cleaned += 1

    return cleaned


def update_services_total_sheet(wb, services):
    """Update or create Services Total sheet with correct data."""
    # Remove old sheet if exists
    if TOTAL_SHEET in wb.sheetnames:
        wb.remove(wb[TOTAL_SHEET])

    ws_total = wb.create_sheet(TOTAL_SHEET)

    # Copy header style from Detail sheet
    ws_detail = wb[DETAIL_SHEET]
    header_row = 8

    # Headers
    headers = ["#", "Task Name", "Coding Effort (hours)", "in days", "Remarks"]
    for col_idx, header in enumerate(headers, start=1):
        cell = ws_total.cell(1, col_idx)
        cell.value = header

        # Copy style from detail sheet header
        src_cell = ws_detail.cell(header_row, col_idx + 1)  # Detail starts at col 2
        if src_cell.font:
            cell.font = Font(
                bold=src_cell.font.bold,
                size=src_cell.font.size,
                color=src_cell.font.color,
            )
        if src_cell.fill:
            cell.fill = PatternFill(patternType=src_cell.fill.patternType, fgColor=src_cell.fill.fgColor)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Set column widths
    ws_total.column_dimensions["A"].width = 8
    ws_total.column_dimensions["B"].width = 50
    ws_total.column_dimensions["C"].width = 25
    ws_total.column_dimensions["D"].width = 12
    ws_total.column_dimensions["E"].width = 40

    # Add service rows
    row = 2
    for service_num in sorted(services.keys()):
        service = services[service_num]

        ws_total.cell(row, 1).value = service_num
        ws_total.cell(row, 2).value = service["name"]
        ws_total.cell(row, 3).value = service["hours"]
        ws_total.cell(row, 4).value = service["days"]
        ws_total.cell(row, 5).value = service["remark"]

        # Format numbers
        ws_total.cell(row, 3).number_format = "0.0"
        ws_total.cell(row, 4).number_format = "0.0"

        # Copy font style from detail sheet service rows
        # Find corresponding row in detail sheet
        for detail_row in range(10, ws_detail.max_row + 1):
            detail_col2 = ws_detail.cell(detail_row, 2).value
            if isinstance(detail_col2, (int, float)) and int(detail_col2) == service_num:
                src_cell = ws_detail.cell(detail_row, 3)
                if src_cell.font:
                    ws_total.cell(row, 2).font = Font(
                        bold=src_cell.font.bold,
                        size=src_cell.font.size,
                        color=src_cell.font.color,
                    )
                break

        row += 1

    # Add totals row
    row += 1
    ws_total.cell(row, 2).value = "Total"
    ws_total.cell(row, 2).font = Font(bold=True)
    ws_total.cell(row, 3).value = f"=SUM(C2:C{row - 1})"
    ws_total.cell(row, 4).value = f"=SUM(D2:D{row - 1})"
    ws_total.cell(row, 3).number_format = "0.0"
    ws_total.cell(row, 4).number_format = "0.0"

    return row - 1  # Return number of services


def main():
    wb = load_workbook(FILE_PATH, read_only=False)
    ws_detail = wb[DETAIL_SHEET]

    print("=== Step 1: Cleaning remarks in Detail sheet ===")
    cleaned = clean_remarks(ws_detail)
    print(f"✅ Cleaned {cleaned} remark cells")

    print("\n=== Step 2: Calculating service totals from Detail sheet ===")
    services = get_service_totals(ws_detail)
    print(f"✅ Found {len(services)} services")

    print("\n=== Step 3: Updating Services Total sheet ===")
    service_count = update_services_total_sheet(wb, services)
    print(f"✅ Updated Services Total sheet with {service_count} services")

    # Verify totals match
    print("\n=== Step 4: Verifying totals ===")
    total_hours = sum(s["hours"] for s in services.values())
    total_days = sum(s["days"] for s in services.values())
    print(f"Detail sheet totals: {total_hours:.1f} hours, {total_days:.1f} days")

    # Find totals row in detail sheet
    for row in range(500, ws_detail.max_row + 1):
        col3 = ws_detail.cell(row, 3).value
        if isinstance(col3, str) and "total" in col3.lower():
            detail_total_hours = ws_detail.cell(row, 4).value
            detail_total_days = ws_detail.cell(row, 5).value
            print(f"Detail sheet formula totals: {detail_total_hours} hours, {detail_total_days} days")
            break

    wb.save(FILE_PATH)
    print("\n✅ All sheets synced and saved!")


if __name__ == "__main__":
    main()
