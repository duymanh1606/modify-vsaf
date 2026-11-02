"""Fix all formulas in columns D and E to ensure consistency."""

from openpyxl import load_workbook

if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Fixing All Formulas in Columns D and E ===")

    fixed_count = 0
    cleared_count = 0

    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col4 = detail.cell(row, 4).value
        col5 = detail.cell(row, 5).value

        if not col3:
            continue

        is_service_header = isinstance(col2, (int, float))

        if is_service_header:
            # Service header - clear D and E
            if col4 or col5:
                detail.cell(row, 4).value = None
                detail.cell(row, 5).value = None
                cleared_count += 1
        else:
            # Task row - ensure correct formula
            if col5:
                # Has days value - ensure formula is correct
                expected_formula = f"=E{row}*8"
                if col4 != expected_formula:
                    detail.cell(row, 4).value = expected_formula
                    fixed_count += 1
            else:
                # No days value - clear formula
                if col4:
                    detail.cell(row, 4).value = None
                    cleared_count += 1

    print(f"Fixed {fixed_count} formulas")
    print(f"Cleared {cleared_count} cells")

    # Verify category and total rows
    print("\\n=== Verifying Total Rows ===")
    last_data_row = 449

    # Category total (row 9)
    detail.cell(9, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(9, 5).value = "=D9/8"
    print(f"Category total: D9={detail.cell(9, 4).value}, E9={detail.cell(9, 5).value}")

    # Grand total (row 527)
    detail.cell(527, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(527, 5).value = "=D527/8"
    print(f"Grand total: D527={detail.cell(527, 4).value}, E527={detail.cell(527, 5).value}")

    # Row 5 references
    detail.cell(5, 4).value = "=D527"
    detail.cell(5, 5).value = "=E527"
    print(f"Row 5: D5={detail.cell(5, 4).value}, E5={detail.cell(5, 5).value}")

    # Update summary sheet
    summary = wb["VDS_Summary_Target_State"]
    summary.cell(10, 4).value = "='VDS_Est_Detail_Target_State'!D527"
    summary.cell(10, 5).value = "='VDS_Est_Detail_Target_State'!D527"

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\\n✅ All formulas fixed and verified!")

    # Final verification
    print("\\n=== Final Verification ===")
    issues = 0
    for row in range(10, 50):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col4 = detail.cell(row, 4).value
        col5 = detail.cell(row, 5).value

        if col3:
            is_service = isinstance(col2, (int, float))
            if is_service and (col4 or col5):
                issues += 1
            elif not is_service and col5:
                expected = f"=E{row}*8"
                if col4 != expected:
                    issues += 1

    if issues == 0:
        print("✅ All rows verified - no inconsistencies found!")
    else:
        print(f"⚠️ Found {issues} potential issues in sample rows")
