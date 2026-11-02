"""Fix presentation format and increase effort for complex services."""

from openpyxl import load_workbook

# Services with complex logic that need more effort
COMPLEX_SERVICES = {
    "proposal": 1.3,  # Complex rating, validation, workflow
    "policy": 1.3,  # Complex issuance, renewal, cancellation logic
    "claim": 1.4,  # Complex approval workflow, settlement calculation
    "rating": 1.5,  # Very complex - rating formulas, calculations
    "underwriting": 1.4,  # Complex rules engine, validation
    "workflow": 1.5,  # Very complex - Camunda integration, BPMN flows
    "orchestrator": 1.4,  # Complex orchestration logic
    "payment": 1.3,  # Complex payment flows, async callbacks, retry logic
    "carrier": 1.3,  # Complex integration patterns
    "migration": 1.4,  # Complex data transformation
    "camunda": 1.5,  # Very complex workflow engine
}

if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Fixing Presentation Format and Formulas ===")

    # Fix all formulas - they should reference their own row
    print("\\nFixing formulas...")
    fixed_count = 0
    for row in range(10, 450):
        col4 = detail.cell(row, 4).value
        col5 = detail.cell(row, 5).value

        # Fix hours formula - should be =E{row}*8
        if col4 and isinstance(col4, str) and "=" in col4:
            detail.cell(row, 4).value = f"=E{row}*8"
            fixed_count += 1

        # Service headers shouldn't have formulas if they don't have days
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        if isinstance(col2, (int, float)) and col3:
            # Service header - check if it has days
            if not col5 or col5 == 0:
                detail.cell(row, 4).value = None

    print(f"Fixed {fixed_count} formulas")

    # Identify and increase effort for complex services
    print("\\n=== Identifying Complex Services ===")
    services_updated = []

    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col5 = detail.cell(row, 5).value

        if isinstance(col2, (int, float)) and col3:
            # Service header
            service_name_lower = str(col3).lower()
            multiplier = 1.0

            # Check if this service needs more effort
            for key, mult in COMPLEX_SERVICES.items():
                if key in service_name_lower:
                    multiplier = mult
                    break

            if multiplier > 1.0:
                # Increase effort for this service and all its tasks
                if col5:
                    new_days = round(float(col5) * multiplier, 1)
                    detail.cell(row, 5).value = new_days
                    detail.cell(row, 4).value = f"=E{row}*8"
                    services_updated.append((row, str(col3)[:50], col5, new_days, multiplier))

                    # Find and update all tasks for this service
                    task_row = row + 1
                    while task_row < 450:
                        task_col2 = detail.cell(task_row, 2).value
                        task_col3 = detail.cell(task_row, 3).value
                        task_col5 = detail.cell(task_row, 5).value

                        # Check if still in same service (no new section number)
                        if isinstance(task_col2, (int, float)):
                            break

                        if task_col3 and task_col5:
                            new_task_days = round(float(task_col5) * multiplier, 1)
                            detail.cell(task_row, 5).value = new_task_days
                            detail.cell(task_row, 4).value = f"=E{task_row}*8"

                        task_row += 1

    print(f"\\nUpdated {len(services_updated)} complex services:")
    for row, name, old_days, new_days, mult in services_updated[:10]:
        print(f"  Row {row}: {name[:45]}")
        print(f"    {old_days} -> {new_days} days (x{mult})")

    # Update totals
    last_data_row = 449
    detail.cell(9, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(527, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(527, 5).value = "=D527/8"
    detail.cell(5, 4).value = "=D527"
    detail.cell(5, 5).value = "=E527"

    # Update summary
    summary = wb["VDS_Summary_Target_State"]
    summary.cell(10, 4).value = "='VDS_Est_Detail_Target_State'!D527"
    summary.cell(10, 5).value = "='VDS_Est_Detail_Target_State'!D527"

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\\n✅ Fixed presentation format and increased effort for complex services!")
