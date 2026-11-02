"""Restore all E values and rebuild D formulas correctly."""

from openpyxl import load_workbook

# Service effort mapping (days) - with complex service multipliers
SERVICE_EFFORT = {
    "proposal": 15.6,
    "policy": 13.0,
    "customer": 8.0,
    "claim": 16.8,
    "agent": 10.0,
    "billing": 10.0,
    "promotion": 8.0,
    "socialized": 10.0,
    "catalog": 12.0,
    "rating": 22.5,
    "underwriting": 13.4,
    "rules": 10.0,
    "document": 8.0,
    "analytics": 10.0,
    "fraud": 10.0,
    "ocr": 8.0,
    "orchestrator": 16.8,
    "workflow": 22.5,
    "renewal": 8.0,
    "timeout": 6.0,
    "reconcile": 8.0,
    "payment": 13.0,
    "payment hub": 15.6,
    "carrier": 13.0,
    "migration": 21.0,
    "sync": 8.0,
    "user": 8.0,
    "crm": 10.0,
    "schedule": 8.0,
    "content": 10.0,
    "security": 12.0,
    "observability": 12.0,
    "test": 15.0,
    "cicd": 10.0,
    "interface": 10.0,
    "portal": 12.0,
    "admin portal": 12.0,
    "bff": 10.0,
    "gateway": 12.0,
    "regulator": 10.0,
}


def distribute_hours(total_hours, num_tasks):
    """Distribute hours across tasks with weights."""
    if num_tasks <= 3:
        return [total_hours / num_tasks] * num_tasks
    weights = []
    for i in range(num_tasks):
        if i == 0:  # API
            weights.append(1.3)
        elif i < 4:  # Core logic
            weights.append(1.2)
        elif i < 7:  # Integration
            weights.append(1.0)
        else:  # Testing
            weights.append(0.8)
    total_weight = sum(weights)
    return [total_hours * w / total_weight for w in weights]


if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Restoring E Values ===")

    # Read services and tasks
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
                        "total_days": current_service["total_days"],
                        "tasks": current_tasks.copy(),
                    }
                )

            # New service - determine effort
            service_name_lower = str(col3).lower()
            total_days = 10.0  # Default

            for key, days in SERVICE_EFFORT.items():
                if key in service_name_lower:
                    total_days = days
                    break

            current_service = {"row": row, "name": str(col3), "total_days": total_days}
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
                "total_days": current_service["total_days"],
                "tasks": current_tasks.copy(),
            }
        )

    print(f"Found {len(services)} services")

    # Restore E values and rebuild D formulas
    restored = 0
    for svc in services:
        if len(svc["tasks"]) > 0:
            task_hours = distribute_hours(svc["total_days"] * 8, len(svc["tasks"]))
            for i, task_row in enumerate(svc["tasks"]):
                days = round(task_hours[i] / 8, 1)
                detail.cell(task_row, 5).value = days
                detail.cell(task_row, 4).value = f"=E{task_row}*8"
                restored += 1

    print(f"Restored {restored} E values and D formulas")

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
    print("\\n✅ All E values restored and D formulas rebuilt!")

    # Verification
    print("\\n=== Verification ===")
    tasks_with_e = 0
    for row in range(10, 50):
        col5 = detail.cell(row, 5).value
        col3 = detail.cell(row, 3).value
        col2 = detail.cell(row, 2).value
        if col3 and not isinstance(col2, (int, float)) and col5:
            tasks_with_e += 1

    print(f"Tasks with E values: {tasks_with_e}")
    if tasks_with_e > 0:
        print("✅ E values restored successfully!")
