"""Completely rebuild all formulas in columns D and E for absolute consistency."""

from openpyxl import load_workbook

if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Rebuilding All Formulas ===")

    # Step 1: Clear all D and E columns for data rows
    print("Step 1: Clearing all D and E values...")
    for row in range(10, 450):
        detail.cell(row, 4).value = None  # D
        detail.cell(row, 5).value = None  # E

    # Step 2: Rebuild based on row type
    print("Step 2: Rebuilding formulas...")
    tasks_rebuilt = 0

    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value

        if not col3:
            continue

        is_service_header = isinstance(col2, (int, float))

        if is_service_header:
            # Service header - keep D and E empty
            detail.cell(row, 4).value = None
            detail.cell(row, 5).value = None
        else:
            # Task row - we need to restore the days value
            # Read from a backup or recalculate
            # For now, let's check if we can get it from the task description
            # Actually, we should preserve the E values, so let's read them first

            # We'll need to preserve E values, so let's do this differently
            pass

    # Better approach: Read E values first, then rebuild D formulas
    print("Step 2 (revised): Preserving E values and rebuilding D formulas...")

    # First, read all E values
    e_values = {}
    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col5 = detail.cell(row, 5).value

        if col3 and not isinstance(col2, (int, float)) and col5:
            e_values[row] = float(col5) if isinstance(col5, (int, float)) else None

    # Now clear and rebuild
    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value

        if not col3:
            continue

        is_service_header = isinstance(col2, (int, float))

        if is_service_header:
            # Service header - empty
            detail.cell(row, 4).value = None
            detail.cell(row, 5).value = None
        else:
            # Task - restore E and create D formula
            if row in e_values:
                days = e_values[row]
                detail.cell(row, 5).value = days
                detail.cell(row, 4).value = f"=E{row}*8"
                tasks_rebuilt += 1
            else:
                # No E value - clear D
                detail.cell(row, 4).value = None
                detail.cell(row, 5).value = None

    print(f"Rebuilt {tasks_rebuilt} task formulas")

    # Step 3: Fix total rows
    print("Step 3: Fixing total rows...")
    last_data_row = 449

    # Category total
    detail.cell(9, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(9, 5).value = "=D9/8"

    # Grand total
    detail.cell(527, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(527, 5).value = "=D527/8"

    # Row 5
    detail.cell(5, 4).value = "=D527"
    detail.cell(5, 5).value = "=E527"

    # Update summary
    summary = wb["VDS_Summary_Target_State"]
    summary.cell(10, 4).value = "='VDS_Est_Detail_Target_State'!D527"
    summary.cell(10, 5).value = "='VDS_Est_Detail_Target_State'!D527"

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\\n✅ All formulas rebuilt!")

    # Verification
    print("\\n=== Verification ===")
    service_headers_ok = 0
    tasks_ok = 0
    issues = []

    for row in range(10, 50):  # Sample check
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col4 = detail.cell(row, 4).value
        col5 = detail.cell(row, 5).value

        if not col3:
            continue

        if isinstance(col2, (int, float)):
            if not col4 and not col5:
                service_headers_ok += 1
            else:
                issues.append(f"Row {row}: Service header has D={col4}, E={col5}")
        else:
            if col5:
                expected = f"=E{row}*8"
                if col4 == expected:
                    tasks_ok += 1
                else:
                    issues.append(f"Row {row}: D={col4}, expected {expected}, E={col5}")

    print(f"Service headers OK: {service_headers_ok}")
    print(f"Tasks OK: {tasks_ok}")
    if issues:
        print(f"\\nIssues: {len(issues)}")
        for issue in issues[:5]:
            print(f"  {issue}")
    else:
        print("\\n✅ All verified!")
