"""Update effort estimation with detailed API and database development considerations."""

from openpyxl import load_workbook

# API counts per service (from TARGET_API_SCHEMA_COVERAGE_MATRIX.md and service specs)
API_COUNTS = {
    "proposal": 20,  # Very complex - many endpoints
    "policy": 9,  # Complex - policy operations
    "customer": 2,  # Simple - but complex business logic
    "member": 2,  # Simple
    "claim": 8,  # Complex - claim workflow
    "agent": 6,  # Medium
    "billing": 5,  # Medium
    "promotion": 2,  # Simple
    "payment": 5,  # Medium - but complex integration
    "carrier": 8,  # Complex - external integration
    "rating": 3,  # Simple API count but very complex logic
    "underwriting": 4,  # Medium
    "workflow": 2,  # Simple API but very complex Camunda
    "orchestrator": 10,  # Complex - orchestration
    "document": 4,  # Medium
    "notification": 3,  # Simple
    "analytics": 5,  # Medium
    "catalog": 8,  # Complex - product management
    "migration": 1,  # Simple API but very complex logic
    "test": 1,  # Simple
    "cicd": 1,  # Simple
    "security": 4,  # Medium
    "observability": 3,  # Simple
    "sync": 3,  # Simple
    "user": 4,  # Medium
    "crm": 5,  # Medium
    "schedule": 3,  # Simple
    "content": 4,  # Medium
    "ocr": 3,  # Simple
    "fraud": 4,  # Medium
    "rules": 3,  # Simple
    "renewal": 3,  # Simple
    "timeout": 1,  # Simple
    "reconcile": 3,  # Simple
    "regulator": 4,  # Medium
    "interface": 10,  # Complex - frontend APIs
    "portal": 8,  # Complex - portal APIs
    "bff": 12,  # Very complex - BFF aggregation
    "cms": 6,  # Medium
    "gateway": 5,  # Medium
    "socialized": 2,  # Simple
}

# API Complexity multipliers
API_COMPLEXITY_MULTIPLIERS = {
    "very_complex": 1.5,  # 16+ APIs
    "complex": 1.3,  # 9-15 APIs
    "medium": 1.2,  # 4-8 APIs
    "simple": 1.1,  # 1-3 APIs
}

# Business complication multipliers (based on domain complexity)
BUSINESS_COMPLICATION = {
    "proposal": 1.4,  # Complex rating, validation, workflow
    "policy": 1.3,  # Complex issuance, renewal, cancellation
    "claim": 1.5,  # Very complex - approval workflow, settlement
    "rating": 1.6,  # Very complex - rating formulas
    "underwriting": 1.4,  # Complex rules engine
    "workflow": 1.5,  # Very complex - Camunda BPMN
    "orchestrator": 1.4,  # Complex orchestration
    "payment": 1.3,  # Complex async flows
    "carrier": 1.3,  # Complex external integration
    "catalog": 1.2,  # Medium complexity
    "migration": 1.5,  # Very complex data transformation
    "bff": 1.3,  # Complex aggregation
    "standard": 1.1,  # Standard business logic
}

# SDLC Buffering factors (industry best practices)
# Based on: Requirements clarification, design review, code review, testing, deployment, risk mitigation
SDLC_BUFFER = {
    "api_development": 1.3,  # 30% buffer for API: design, validation, testing, documentation
    "database_development": 1.4,  # 40% buffer for DB: schema design, migration, testing, optimization
    "standard_development": 1.2,  # 20% buffer for standard tasks
}


def get_api_count(service_name):
    """Get API count for service."""
    service_lower = service_name.lower()
    for key, count in API_COUNTS.items():
        if key in service_lower:
            return count
    return 5  # Default medium complexity


def get_api_complexity_multiplier(api_count):
    """Get multiplier based on API count."""
    if api_count >= 16:
        return API_COMPLEXITY_MULTIPLIERS["very_complex"]
    elif api_count >= 9:
        return API_COMPLEXITY_MULTIPLIERS["complex"]
    elif api_count >= 4:
        return API_COMPLEXITY_MULTIPLIERS["medium"]
    else:
        return API_COMPLEXITY_MULTIPLIERS["simple"]


def get_business_complication(service_name):
    """Get business complication multiplier."""
    service_lower = service_name.lower()
    for key, mult in BUSINESS_COMPLICATION.items():
        if key in service_lower:
            return mult
    return BUSINESS_COMPLICATION["standard"]


if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Updating Effort with API and Database Complexity ===")

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
                        "tasks": current_tasks.copy(),
                    }
                )

            # New service
            current_service = {"row": row, "name": str(col3)}
            current_tasks = []
        else:
            # Task
            if current_service:
                current_tasks.append({"row": row, "name": str(col3)})

    # Save last service
    if current_service:
        services.append(
            {
                "row": current_service["row"],
                "name": current_service["name"],
                "tasks": current_tasks.copy(),
            }
        )

    print(f"Found {len(services)} services")

    # Update effort for each service
    updated_services = []

    for svc in services:
        service_name = svc["name"]
        api_count = get_api_count(service_name)
        api_multiplier = get_api_complexity_multiplier(api_count)
        business_multiplier = get_business_complication(service_name)

        # Identify task types
        api_tasks = []
        database_tasks = []
        other_tasks = []

        for task in svc["tasks"]:
            task_name_lower = task["name"].lower()
            if "api" in task_name_lower or "endpoint" in task_name_lower or "rest" in task_name_lower:
                api_tasks.append(task)
            elif (
                "database" in task_name_lower
                or "schema" in task_name_lower
                or "data model" in task_name_lower
                or "repository" in task_name_lower
            ):
                database_tasks.append(task)
            else:
                other_tasks.append(task)

        # Calculate multipliers
        api_task_multiplier = api_multiplier * business_multiplier * SDLC_BUFFER["api_development"]
        db_task_multiplier = business_multiplier * SDLC_BUFFER["database_development"]
        other_task_multiplier = business_multiplier * SDLC_BUFFER["standard_development"]

        # Update tasks
        for task in api_tasks:
            col5 = detail.cell(task["row"], 5).value
            if col5:
                old_days = float(col5)
                new_days = round(old_days * api_task_multiplier, 1)
                detail.cell(task["row"], 5).value = new_days
                detail.cell(task["row"], 4).value = f"=E{task['row']}*8"

        for task in database_tasks:
            col5 = detail.cell(task["row"], 5).value
            if col5:
                old_days = float(col5)
                new_days = round(old_days * db_task_multiplier, 1)
                detail.cell(task["row"], 5).value = new_days
                detail.cell(task["row"], 4).value = f"=E{task['row']}*8"

        for task in other_tasks:
            col5 = detail.cell(task["row"], 5).value
            if col5:
                old_days = float(col5)
                new_days = round(old_days * other_task_multiplier, 1)
                detail.cell(task["row"], 5).value = new_days
                detail.cell(task["row"], 4).value = f"=E{task['row']}*8"

        if api_tasks or database_tasks:
            updated_services.append(
                {
                    "name": service_name,
                    "api_count": api_count,
                    "api_tasks": len(api_tasks),
                    "db_tasks": len(database_tasks),
                    "api_mult": api_task_multiplier,
                    "db_mult": db_task_multiplier,
                    "business_mult": business_multiplier,
                }
            )

    print(f"\\nUpdated {len(updated_services)} services with API/database complexity")
    print("\\nSample updates:")
    for svc in updated_services[:10]:
        print(f"  {svc['name'][:50]}")
        print(f"    APIs: {svc['api_count']}, API tasks: {svc['api_tasks']}, DB tasks: {svc['db_tasks']}")
        print(
            f"    Multipliers: API={svc['api_mult']:.2f}x, DB={svc['db_mult']:.2f}x, Business={svc['business_mult']:.2f}x"
        )

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
    print("\\n✅ Effort updated with API and database complexity!")
