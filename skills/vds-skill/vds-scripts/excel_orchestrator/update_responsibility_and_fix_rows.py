"""
Update Responsibility and Fix Row Placement Issues

This script:
1. Updates responsibility for User Management Services, Config Platform, Billing Services to VDS
2. Checks and fixes row placement issues (rows 650-655)
3. Ensures proper sheet structure
"""

from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)


def update_responsibility_for_services(excel_path: Path):
    """Update responsibility for specific services to VDS."""
    wb = load_workbook(excel_path, data_only=False)

    # Update in Services Total sheet
    ws_services = wb["VDS_Est_Detail_Services_Total"]
    services_to_update = [
        "User Management Service",
        "Config Platform",
        "Billing Service",
    ]

    updated_services = []
    for row in range(2, 60):
        service_id = ws_services.cell(row, 1).value
        service_name = ws_services.cell(row, 2).value

        if service_name:
            name_clean = str(service_name).split(":")[0].strip()
            for target_service in services_to_update:
                if target_service.lower() in name_clean.lower():
                    ws_services.cell(row, 6, "VDS")
                    updated_services.append({"id": service_id, "name": name_clean, "row": row})
                    print(f"  ✓ Updated Service {service_id} ({name_clean}) → VDS in Services Total sheet")

    # Update in Task Breakdown sheet
    ws_tasks = wb["VDS_Task_Breakdown_Detailed"]

    # Get service IDs that need update
    service_ids_to_update = [s["id"] for s in updated_services]

    updated_tasks = 0
    for row in range(9, ws_tasks.max_row + 1):  # Start from row 9 (after summary)
        service_id = ws_tasks.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)
            if service_id_int in service_ids_to_update:
                current_resp = ws_tasks.cell(row, 3).value
                if current_resp != "VDS":
                    ws_tasks.cell(row, 3, "VDS")
                    updated_tasks += 1

    wb.save(excel_path)
    print(f"\n✅ Updated {len(updated_services)} services in Services Total sheet")
    print(f"✅ Updated {updated_tasks} tasks in Task Breakdown sheet")

    return updated_services


def check_and_fix_row_placement(excel_path: Path):
    """Check and fix row placement issues."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("\n=== Checking Row Placement ===")

    # Check for issues around rows 650-655
    issues_found = []

    for row in range(650, 656):
        service_id = ws.cell(row, 1).value
        ws.cell(row, 2).value
        task_name = ws.cell(row, 6).value

        # Check if row is empty or has inconsistent data
        if not service_id and not task_name:
            issues_found.append({"row": row, "issue": "Empty row", "action": "delete"})
        elif service_id and not task_name:
            issues_found.append({"row": row, "issue": "Service row without task", "action": "check"})
        elif not service_id and task_name:
            issues_found.append({"row": row, "issue": "Task without service ID", "action": "fix"})

    if issues_found:
        print(f"Found {len(issues_found)} potential issues:")
        for issue in issues_found:
            print(f"  Row {issue['row']}: {issue['issue']} → {issue['action']}")

        # Check if these are actually summary rows that got misplaced
        for row in range(650, 656):
            cell_value = ws.cell(row, 1).value
            if cell_value and ("TỔNG KẾT" in str(cell_value).upper() or "SUMMARY" in str(cell_value).upper()):
                print(f"\n⚠️ Found summary row at row {row} - should be at top!")
                # Delete misplaced summary rows
                ws.delete_rows(row)
                print(f"  ✓ Deleted misplaced summary row at {row}")
    else:
        print("✅ No row placement issues found in rows 650-655")

    # Check for any duplicate summary sections
    summary_rows = []
    for row in range(2, ws.max_row + 1):
        cell_value = ws.cell(row, 1).value
        if cell_value and ("TỔNG KẾT" in str(cell_value).upper() or "SUMMARY" in str(cell_value).upper()):
            summary_rows.append(row)

    if len(summary_rows) > 1:
        print(f"\n⚠️ Found {len(summary_rows)} summary sections at rows: {summary_rows}")
        print("  Keeping first one (at top), removing others...")
        for row in sorted(summary_rows[1:], reverse=True):
            # Delete all rows from this summary to next non-empty section
            delete_count = 0
            for check_row in range(row, min(row + 10, ws.max_row + 1)):
                next_cell = ws.cell(check_row + 1, 1).value
                if next_cell and isinstance(next_cell, (int, float)) and next_cell > 0:
                    break
                delete_count += 1
            if delete_count > 0:
                ws.delete_rows(row, delete_count)
                print(f"  ✓ Removed duplicate summary section starting at row {row}")

    # Ensure proper task ordering by service ID
    print("\n=== Verifying Task Ordering ===")
    current_service_id = None
    ordering_issues = []

    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            if current_service_id is not None and service_id_int < current_service_id:
                ordering_issues.append(
                    {
                        "row": row,
                        "service_id": service_id_int,
                        "previous": current_service_id,
                    }
                )

            current_service_id = service_id_int

    if ordering_issues:
        print(f"⚠️ Found {len(ordering_issues)} ordering issues")
        for issue in ordering_issues[:5]:
            print(f"  Row {issue['row']}: Service {issue['service_id']} appears after Service {issue['previous']}")
    else:
        print("✅ Task ordering is correct")

    wb.save(excel_path)
    return len(issues_found) + len(summary_rows) - 1 if len(summary_rows) > 1 else len(issues_found)


def main():
    """Main execution."""
    print("=" * 80)
    print("Update Responsibility and Fix Row Placement")
    print("=" * 80)

    # Step 1: Update responsibility
    print("\nStep 1: Updating responsibility for services...")
    updated_services = update_responsibility_for_services(EXCEL_PATH)

    # Step 2: Check and fix row placement
    print("\nStep 2: Checking and fixing row placement...")
    check_and_fix_row_placement(EXCEL_PATH)

    # Final verification
    print("\n=== Final Verification ===")
    wb = load_workbook(EXCEL_PATH, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Check responsibility updates
    print("\nResponsibility Updates:")
    for service in updated_services:
        service_id = service["id"]
        count = 0
        for row in range(9, ws.max_row + 1):
            if ws.cell(row, 1).value == service_id and ws.cell(row, 3).value == "VDS":
                count += 1
        print(f"  Service {service_id}: {count} tasks now have VDS responsibility")

    # Check rows 650-655
    print("\nRows 650-655 Status:")
    for row in range(650, 656):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value
        if service_id or task_name:
            print(f"  Row {row}: Service {service_id}, Task: {task_name[:40] if task_name else 'None'}...")
        else:
            print(f"  Row {row}: Empty")

    print("\n" + "=" * 80)
    print("Updates completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
