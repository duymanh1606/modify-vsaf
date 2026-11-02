"""Clean remarks column - only service rows should have remarks, task rows should be empty."""

from openpyxl import load_workbook

if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx", read_only=False
    )
    detail = wb["VDS_Est_Detail_Target_State"]
    original = wb["Est Detail"]

    print("=== Cleaning Remarks Column ===")

    # Check original pattern
    print("\\nChecking original pattern...")
    original_task_has_remark = False
    for row in range(10, 50):
        col2 = original.cell(row, 2).value
        col3 = original.cell(row, 3).value
        col6 = original.cell(row, 6).value

        if col3 and not isinstance(col2, (int, float)):  # Task row
            if col6:
                original_task_has_remark = True
                print(f"  Row {row} (task): Has remark: {str(col6)[:50]}")
                break

    if not original_task_has_remark:
        print("  Original: Task rows do NOT have remarks")

    # Clean VDS sheet
    print("\\nCleaning VDS sheet...")
    cleaned_count = 0

    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col6 = detail.cell(row, 6).value

        if not col3:
            # Empty row - clear remark if any
            if col6:
                detail.cell(row, 6).value = None
                cleaned_count += 1
            continue

        # Check if this is a task row (not a service row)
        is_task_row = not isinstance(col2, (int, float))

        if is_task_row:
            # Task rows should NOT have remarks
            if col6:
                old_remark = str(col6)
                detail.cell(row, 6).value = None
                cleaned_count += 1
                print(f"  Row {row}: Removed remark from task: {str(col3)[:40]}")
                print(f"    Removed: {old_remark[:60]}")

    # Ensure service rows have remarks
    print("\\nVerifying service rows have remarks...")
    missing_remarks = []
    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col6 = detail.cell(row, 6).value

        if col3 and isinstance(col2, (int, float)):  # Service row
            if not col6:
                missing_remarks.append({"row": row, "service": str(col3)[:50]})

    if missing_remarks:
        print(f"  Found {len(missing_remarks)} service rows without remarks")
        for m in missing_remarks[:5]:
            print(f"    Row {m['row']}: {m['service']}")
    else:
        print("  All service rows have remarks")

    # Check for irrelevant data in service remarks
    print("\\nChecking for irrelevant data in service remarks...")
    irrelevant_count = 0
    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col6 = detail.cell(row, 6).value

        if col3 and isinstance(col2, (int, float)) and col6:  # Service row with remark
            remark = str(col6)
            service_name = str(col3).lower()

            # Check for common irrelevant patterns
            issues = []

            # Check if remark is too generic or doesn't match service
            if len(remark) < 30:
                issues.append("Too short")

            # Check if remark contains service name key words
            if "proposal" in service_name and "proposal" not in remark.lower() and "đề xuất" not in remark.lower():
                issues.append("Does not mention proposal")
            elif "policy" in service_name and "policy" not in remark.lower() and "chính sách" not in remark.lower():
                issues.append("Does not mention policy")
            elif (
                "customer" in service_name
                and "targeted" not in service_name
                and "customer" not in remark.lower()
                and "khách hàng" not in remark.lower()
            ):
                issues.append("Does not mention customer")

            # Check for placeholder text
            if "placeholder" in remark.lower() or "todo" in remark.lower() or "tbd" in remark.lower():
                issues.append("Contains placeholder text")

            if issues:
                irrelevant_count += 1
                print(f"  Row {row}: {str(col3)[:50]}")
                print(f"    Issues: {', '.join(issues)}")
                print(f"    Remark: {remark[:80]}")

    if irrelevant_count == 0:
        print("  No irrelevant data found")

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")

    print(f"\\n✅ Cleaned {cleaned_count} task rows (removed remarks)")
    print(f"✅ Checked {len(missing_remarks)} service rows for missing remarks")
    print("✅ Checked service remarks for irrelevant data")
