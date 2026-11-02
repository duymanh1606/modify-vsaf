"""Increase effort for customer service complexity, frontend work, and new technology development."""

from openpyxl import load_workbook

# Effort multipliers
CUSTOMER_SERVICE_MULTIPLIER = 1.4  # Customer service complexity
FRONTEND_MULTIPLIER = 1.5  # Frontend work (new tech + complexity)
NEW_TECH_MULTIPLIER = 1.2  # All tasks (developing with new technology)

# Combined multipliers
CUSTOMER_SERVICE_COMBINED = CUSTOMER_SERVICE_MULTIPLIER * NEW_TECH_MULTIPLIER  # 1.68x
FRONTEND_COMBINED = FRONTEND_MULTIPLIER * NEW_TECH_MULTIPLIER  # 1.8x
STANDARD_COMBINED = NEW_TECH_MULTIPLIER  # 1.2x

if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Increasing Effort for Complexity and New Technology ===")
    print(f"Customer Service: {CUSTOMER_SERVICE_COMBINED:.2f}x")
    print(f"Frontend: {FRONTEND_COMBINED:.2f}x")
    print(f"All Other Tasks: {STANDARD_COMBINED:.2f}x")

    # Identify services
    services = []
    current_service = None
    current_tasks = []

    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value

        if not col3:
            continue

        if isinstance(col2, (int, float)):
            # Save previous service
            if current_service:
                services.append(
                    {
                        "row": current_service["row"],
                        "name": current_service["name"],
                        "tasks": current_tasks.copy(),
                        "is_customer": current_service["is_customer"],
                        "is_frontend": current_service["is_frontend"],
                    }
                )

            # New service
            service_name_lower = str(col3).lower()
            is_customer = any(keyword in service_name_lower for keyword in ["customer", "member", "user management"])
            is_frontend = any(
                keyword in service_name_lower
                for keyword in [
                    "interface",
                    "portal",
                    "bff",
                    "cms",
                    "frontend",
                    "admin",
                    "agent",
                    "dashboard",
                ]
            )

            current_service = {
                "row": row,
                "name": str(col3),
                "is_customer": is_customer,
                "is_frontend": is_frontend,
            }
            current_tasks = []
        else:
            # Task
            if current_service:
                current_tasks.append(row)

    # Save last service
    if current_service:
        services.append(
            {
                "row": current_service["row"],
                "name": current_service["name"],
                "tasks": current_tasks.copy(),
                "is_customer": current_service["is_customer"],
                "is_frontend": current_service["is_frontend"],
            }
        )

    print(f"\\nFound {len(services)} services")

    # Apply multipliers
    customer_updated = 0
    frontend_updated = 0
    standard_updated = 0

    for svc in services:
        multiplier = STANDARD_COMBINED

        if svc["is_customer"]:
            multiplier = CUSTOMER_SERVICE_COMBINED
            customer_updated += 1
        elif svc["is_frontend"]:
            multiplier = FRONTEND_COMBINED
            frontend_updated += 1
        else:
            multiplier = STANDARD_COMBINED
            standard_updated += 1

        # Update all tasks for this service
        for task_row in svc["tasks"]:
            col5 = detail.cell(task_row, 5).value
            if col5:
                old_days = float(col5)
                new_days = round(old_days * multiplier, 1)
                detail.cell(task_row, 5).value = new_days
                detail.cell(task_row, 4).value = f"=E{task_row}*8"

    print("\\nUpdated services:")
    print(f"  Customer Service: {customer_updated} services")
    print(f"  Frontend: {frontend_updated} services")
    print(f"  Standard: {standard_updated} services")

    # Fix totals
    last_data_row = 449
    detail.cell(9, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(9, 5).value = "=D9/8"
    detail.cell(527, 4).value = f"=SUM(D10:D{last_data_row})"
    detail.cell(527, 5).value = "=D527/8"
    detail.cell(5, 4).value = "=D527"
    detail.cell(5, 5).value = "=E527"

    # Update summary
    summary = wb["VDS_Summary_Target_State"]
    summary.cell(10, 4).value = "='VDS_Est_Detail_Target_State'!D527"
    summary.cell(10, 5).value = "='VDS_Est_Detail_Target_State'!D527"

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\\n✅ Effort increased for complexity and new technology!")

    # Show sample updates
    print("\\n=== Sample Updates ===")
    for svc in services[:5]:
        if svc["tasks"]:
            first_task_row = svc["tasks"][0]
            old_val = detail.cell(first_task_row, 5).value
            multiplier = (
                CUSTOMER_SERVICE_COMBINED
                if svc["is_customer"]
                else (FRONTEND_COMBINED if svc["is_frontend"] else STANDARD_COMBINED)
            )
            print(f"  {svc['name'][:40]}: x{multiplier:.2f}")
