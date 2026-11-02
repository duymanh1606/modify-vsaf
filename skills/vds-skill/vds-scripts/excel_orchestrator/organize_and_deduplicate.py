"""Organize content by category and subcategory, remove duplicates."""

import re
from collections import defaultdict

from openpyxl import load_workbook

# Service name mapping for generic names
SERVICE_NAME_MAP = {
    "Giao diện Khách hàng": "Customer Interface",
    "Cổng thông tin Đại lý": "Agent Portal",
    "Cổng quản trị nội bộ": "Internal Admin Portal",
    "BFF Khách hàng": "Customer BFF",
    "BFF Đại lý": "Agent BFF",
    "BFF Quản trị": "Admin BFF",
}

# Category grouping
CATEGORIES = {
    "Core Services": [
        "proposal",
        "policy",
        "customer",
        "claim",
        "agent",
        "billing",
        "promotion",
    ],
    "Engines": ["rating", "underwriting", "rules", "catalog", "analytics", "fraud"],
    "BFF Services": ["bff", "customer bff", "agent bff", "admin bff"],
    "Process Services": ["orchestrator", "workflow", "renewal", "timeout", "reconcile"],
    "Integration Services": ["carrier", "payment", "hub", "gateway"],
    "Infrastructure": [
        "ci/cd",
        "monitoring",
        "observability",
        "security",
        "migration",
        "test",
    ],
    "Other Services": [
        "ocr",
        "notification",
        "document",
        "socialized",
        "content",
        "schedule",
        "crm",
    ],
}


def extract_service_name(task_name):
    """Extract service name from task name."""
    if not task_name:
        return None

    task_str = str(task_name).strip()

    # Check for workstream in parentheses
    if "(" in task_str and ")" in task_str:
        match = re.search(r"\(([^)]+)\)", task_str)
        if match:
            workstream = match.group(1)
            # Try to map workstream to service name
            if workstream in SERVICE_NAME_MAP:
                return SERVICE_NAME_MAP[workstream]
            # Extract from workstream
            if "BFF" in workstream:
                return workstream
            if "Cổng" in workstream or "Giao diện" in workstream:
                return workstream

    # Try to extract insurance-xxx pattern
    if "insurance-" in task_str:
        match = re.search(r"insurance-([a-z-]+)", task_str)
        if match:
            return match.group(1).replace("-", " ").title()

    # Extract from beginning
    if task_str.startswith("  "):
        clean = task_str.replace("  ", "").strip()
        if "(" in clean:
            clean = clean.split("(")[0].strip()
        return clean

    return None


def get_category(service_name):
    """Get category for a service."""
    if not service_name:
        return "Other Services"

    service_lower = service_name.lower()
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in service_lower:
                return category
    return "Other Services"


if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Organizing and Deduplicating ===")

    # Read all services with their tasks
    services_data = []
    current_service = None
    current_tasks = []

    for row in range(10, 527):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col4 = detail.cell(row, 4).value
        col5 = detail.cell(row, 5).value

        if col3:
            task_str = str(col3).strip()
            # Service header
            if isinstance(col2, (int, float)):
                # Save previous service
                if current_service:
                    services_data.append(
                        {
                            "row": current_service["row"],
                            "section": current_service["section"],
                            "name": current_service["name"],
                            "days": current_service["days"],
                            "hours_formula": current_service["hours_formula"],
                            "tasks": current_tasks.copy(),
                        }
                    )
                # New service
                service_name = extract_service_name(task_str)
                category = get_category(service_name)
                current_service = {
                    "row": row,
                    "section": int(col2),
                    "name": task_str,
                    "service_name": service_name,
                    "category": category,
                    "days": col5,
                    "hours_formula": col4,
                }
                current_tasks = []
            else:
                # Task
                if current_service:
                    current_tasks.append(
                        {
                            "row": row,
                            "name": task_str,
                            "days": col5,
                            "hours_formula": col4,
                        }
                    )

    # Save last service
    if current_service:
        services_data.append(
            {
                "row": current_service["row"],
                "section": current_service["section"],
                "name": current_service["name"],
                "days": current_service["days"],
                "hours_formula": current_service["hours_formula"],
                "tasks": current_tasks.copy(),
            }
        )

    print(f"Found {len(services_data)} services")

    # Check for duplicates
    seen_services = {}
    duplicates = []
    unique_services = []

    for svc in services_data:
        # Create unique key from service name
        clean_name = svc["name"].split("(")[0].strip() if "(" in svc["name"] else svc["name"].strip()
        key = clean_name.lower()

        if key in seen_services:
            duplicates.append((seen_services[key], svc))
            print(f"  Duplicate: {svc['name'][:50]} (row {svc['row']})")
        else:
            seen_services[key] = svc
            unique_services.append(svc)

    print(f"\\nFound {len(duplicates)} duplicates, {len(unique_services)} unique services")

    # Organize by category
    print("\\n=== Organizing by Category ===")
    by_category = defaultdict(list)
    for svc in unique_services:
        category = get_category(svc.get("service_name", ""))
        by_category[category].append(svc)

    print(f"Categories: {list(by_category.keys())}")
    for category, svcs in by_category.items():
        print(f"  {category}: {len(svcs)} services")

    # Rebuild sheet organized by category
    print("\\n=== Rebuilding Sheet Organized by Category ===")

    # Clear data rows
    for row in range(10, 527):
        for col in range(1, 6):
            detail.cell(row, col).value = None

    # Write organized data
    current_row = 10
    section_num = 1

    # Sort categories
    category_order = [
        "Core Services",
        "Engines",
        "BFF Services",
        "Process Services",
        "Integration Services",
        "Infrastructure",
        "Other Services",
    ]

    for category in category_order:
        if category not in by_category:
            continue

        services = by_category[category]
        # Sort services within category
        services.sort(key=lambda x: x["name"])

        for svc in services:
            # Write service header
            detail.cell(current_row, 2).value = section_num
            detail.cell(current_row, 3).value = svc["name"]
            detail.cell(current_row, 4).value = svc["hours_formula"]
            detail.cell(current_row, 5).value = svc["days"]
            current_row += 1
            section_num += 1

            # Write tasks
            for task in svc["tasks"]:
                detail.cell(current_row, 2).value = None
                detail.cell(current_row, 3).value = task["name"]
                detail.cell(current_row, 4).value = task["hours_formula"]
                detail.cell(current_row, 5).value = task["days"]
                current_row += 1

    print(f"\\nRebuilt sheet: {section_num - 1} services, last row: {current_row - 1}")

    # Update formulas
    last_data_row = current_row - 1
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
    print("\\n✅ Organized by category and removed duplicates!")
