"""Fix VDS_Est_Detail_Target_State presentation to match original Est Detail format."""

from openpyxl import load_workbook

if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Fixing Column Structure ===")
    print("Original format: Col2=#, Col3=Task Name, Col4=Hours formula (=E*8), Col5=Days (input)")
    print("Current format: Col1=#, Col2=Task Name, Col3=Hours, Col4=Days formula, Col5=Remarks")
    print("")
    print("Fixing to match original...")

    # Read all data rows (10 to 526)
    data_rows = []
    for row in range(10, 527):
        col1 = detail.cell(row, 1).value  # Current #
        col2 = detail.cell(row, 2).value  # Current Task Name
        col3 = detail.cell(row, 3).value  # Current Hours
        col4 = detail.cell(row, 4).value  # Current Days formula
        col5 = detail.cell(row, 5).value  # Current Remarks

        if col2 or col3:
            # Calculate days from hours if hours is a number
            days_value = None
            if isinstance(col3, (int, float)) and col3 > 0:
                days_value = round(col3 / 8, 1)

            data_rows.append(
                {
                    "row": row,
                    "number": col1,  # Will go to Col 2
                    "task_name": col2,  # Will go to Col 3
                    "hours": col3,  # Will be calculated in Col 4
                    "days": days_value,  # Will go to Col 5
                    "remarks": col5,  # Will be part of task name
                }
            )

    print(f"Found {len(data_rows)} data rows to fix")

    # Clear columns 1-5 for data rows
    print("Clearing existing data...")
    for row in range(10, 527):
        for col in range(1, 6):
            detail.cell(row, col).value = None

    # Rebuild with correct structure
    print("Rebuilding with correct column structure...")
    for _i, data in enumerate(data_rows):
        row = data["row"]

        # Col 1: Empty
        detail.cell(row, 1).value = None

        # Col 2: # (numbering)
        if data["number"]:
            detail.cell(row, 2).value = data["number"]
        else:
            detail.cell(row, 2).value = None

        # Col 3: Task Name (description)
        task_name = data["task_name"]
        if data["remarks"] and task_name:
            # Combine task name and remarks if needed
            task_name = f"{task_name}: {data['remarks']}"
        detail.cell(row, 3).value = task_name

        # Col 4: Hours formula (=E*8 - calculates from days)
        if data["days"]:
            detail.cell(row, 4).value = f"=E{row}*8"
        else:
            detail.cell(row, 4).value = None

        # Col 5: Days (actual number - this is the input)
        detail.cell(row, 5).value = data["days"]

    # Fix category total row (row 9)
    print("Fixing category total row (row 9)...")
    detail.cell(9, 1).value = None
    detail.cell(9, 2).value = "C"  # Category marker
    detail.cell(9, 3).value = "GIAI ĐOẠN TRIỂN KHAI BUSINESS"
    # Find last data row
    last_data_row = 526
    detail.cell(9, 4).value = f"=SUM(D10:D{last_data_row})"  # Sum hours
    detail.cell(9, 5).value = "=D9/8"  # Calculate days from hours

    # Fix total row (row 527)
    print("Fixing total row (row 527)...")
    detail.cell(527, 1).value = None
    detail.cell(527, 2).value = None
    detail.cell(527, 3).value = "Total Coding & Unit Test Effort"
    detail.cell(527, 4).value = f"=SUM(D10:D{last_data_row})"  # Sum hours
    detail.cell(527, 5).value = "=D527/8"  # Calculate days from hours

    # Fix row 5 formulas
    print("Fixing row 5 formulas...")
    detail.cell(5, 4).value = "=D527"  # Total hours
    detail.cell(5, 5).value = "=E527"  # Total days

    # Update summary sheet
    print("Updating summary sheet references...")
    summary = wb["VDS_Summary_Target_State"]
    summary.cell(10, 4).value = "='VDS_Est_Detail_Target_State'!D527"  # Total hours
    summary.cell(10, 5).value = "='VDS_Est_Detail_Target_State'!D527"  # Total hours

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\\n✅ Fixed presentation to match original format!")
    print("✅ Column structure: Col2=#, Col3=Task Name, Col4=Hours formula (=E*8), Col5=Days (input)")
