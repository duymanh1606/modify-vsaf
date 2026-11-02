"""Update effort for complex services (Product Catalog, Rule Engine, Business Config) and add new services."""

from openpyxl import load_workbook
from openpyxl.styles import Font

# Multi-insurer complexity multiplier (very high due to multiple insurer products)
MULTI_INSURER_COMPLEXITY = 2.0  # 100% more effort - handling multiple insurers, product variations, frequent changes

# Technical tasks multiplier (research, adapt, migration)
TECHNICAL_TASK_MULTIPLIER = 1.5  # 50% more effort for research, adaptation, migration

# New services to add
NEW_SERVICES = [
    {
        "name": "Intelligent Recommendation Service (Dịch vụ Gợi ý Thông minh)",
        "description": "AI-powered recommendation engine for product suggestions, cross-sell, up-sell",
        "days": 20,  # Complex AI/ML integration
        "tasks": [
            (
                "Thiết kế API",
                "REST API: POST /recommendations, GET /recommendations/{id}, GET /recommendations",
            ),
            (
                "ML Model Integration",
                "Tích hợp ML models: product recommendation, customer segmentation, scoring",
            ),
            (
                "Data Pipeline",
                "Data pipeline: customer data, product data, interaction history, real-time processing",
            ),
            (
                "Business Logic - Recommendation",
                "Business logic: recommendation algorithms, scoring, ranking, filtering",
            ),
            (
                "Business Logic - Personalization",
                "Business logic: personalization engine, customer profiling, preference learning",
            ),
            (
                "Data Models",
                "Schema: Recommendation, CustomerProfile, ProductScore, InteractionHistory, RecommendationHistory",
            ),
            (
                "Tích hợp Product Catalog",
                "Integration: lấy product data, product features, availability",
            ),
            (
                "Tích hợp Customer Service",
                "Integration: customer data, purchase history, preferences",
            ),
            (
                "Tích hợp Analytics Service",
                "Integration: analytics data, customer behavior, trends",
            ),
            (
                "Unit Test",
                "Unit test: recommendation logic, ML model integration, scoring algorithms",
            ),
            (
                "Integration Test",
                "Integration test với Product Catalog, Customer Service, Analytics",
            ),
        ],
    },
    {
        "name": "Intelligent Filtering Service (Dịch vụ Lọc Thông minh)",
        "description": "AI-powered filtering and search service for products, customers, proposals",
        "days": 16,  # Complex filtering logic
        "tasks": [
            (
                "Thiết kế API",
                "REST API: POST /filter, GET /filter/{id}, POST /filter/search",
            ),
            (
                "Business Logic - Filtering",
                "Business logic: intelligent filtering algorithms, relevance scoring, ranking",
            ),
            (
                "Business Logic - Search",
                "Business logic: semantic search, fuzzy matching, auto-complete",
            ),
            ("Data Models", "Schema: Filter, FilterRule, SearchIndex, FilterHistory"),
            (
                "Tích hợp Product Catalog",
                "Integration: product search, product filtering",
            ),
            (
                "Tích hợp Customer Service",
                "Integration: customer search, customer filtering",
            ),
            (
                "Tích hợp Analytics Service",
                "Integration: search analytics, filter performance",
            ),
            (
                "Unit Test",
                "Unit test: filtering logic, search algorithms, relevance scoring",
            ),
            (
                "Integration Test",
                "Integration test với Product Catalog, Customer Service",
            ),
        ],
    },
    {
        "name": "Targeted Customer Service (Dịch vụ Khách hàng Mục tiêu)",
        "description": "Customer segmentation and targeting service for marketing campaigns",
        "days": 18,  # Complex segmentation
        "tasks": [
            (
                "Thiết kế API",
                "REST API: POST /segments, GET /segments, POST /targeting, GET /campaigns",
            ),
            (
                "Business Logic - Segmentation",
                "Business logic: customer segmentation algorithms, clustering, profiling",
            ),
            (
                "Business Logic - Targeting",
                "Business logic: targeting rules, campaign management, A/B testing",
            ),
            (
                "Data Models",
                "Schema: CustomerSegment, TargetingRule, Campaign, CampaignResult",
            ),
            (
                "Tích hợp Customer Service",
                "Integration: customer data, customer profiles, purchase history",
            ),
            (
                "Tích hợp Intelligent Recommendation",
                "Integration: recommendation data, customer preferences",
            ),
            (
                "Tích hợp Analytics Service",
                "Integration: campaign analytics, segmentation performance",
            ),
            (
                "Unit Test",
                "Unit test: segmentation logic, targeting rules, campaign management",
            ),
            (
                "Integration Test",
                "Integration test với Customer Service, Recommendation, Analytics",
            ),
        ],
    },
]

if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Updating Complex Services and Adding New Services ===")

    # Step 1: Increase effort for Product Catalog, Rule Engine, Business Config
    print("\\nStep 1: Increasing effort for complex services...")

    complex_services = [
        "Product Catalog",
        "Business Rules Engine",
        "Config Platform",
        "Business Configuration",
    ]
    updated_services = []

    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value

        if col3 and isinstance(col2, (int, float)):
            service_name = str(col3)
            is_complex = any(svc in service_name for svc in complex_services)

            if is_complex:
                # Find all tasks for this service
                task_rows = []
                task_row = row + 1
                while task_row < 450:
                    task_col2 = detail.cell(task_row, 2).value
                    task_col5 = detail.cell(task_row, 5).value

                    if isinstance(task_col2, (int, float)):
                        break

                    if task_col5:
                        task_rows.append(task_row)

                    task_row += 1

                # Update all tasks with multi-insurer complexity
                for task_row in task_rows:
                    col5 = detail.cell(task_row, 5).value
                    if col5:
                        old_days = float(col5)
                        new_days = round(old_days * MULTI_INSURER_COMPLEXITY, 1)
                        detail.cell(task_row, 5).value = new_days
                        detail.cell(task_row, 4).value = f"=E{task_row}*8"

                updated_services.append(
                    {
                        "name": service_name,
                        "tasks": len(task_rows),
                        "multiplier": MULTI_INSURER_COMPLEXITY,
                    }
                )

    print(f"Updated {len(updated_services)} complex services:")
    for svc in updated_services:
        print(f"  {svc['name'][:50]}: {svc['tasks']} tasks × {svc['multiplier']}x")

    # Step 2: Increase effort for technical tasks (research, adapt, migration)
    print("\\nStep 2: Increasing effort for technical tasks...")

    technical_keywords = [
        "research",
        "adapt",
        "migration",
        "migrate",
        "technical",
        "integration",
        "workflow integration",
    ]
    technical_updated = 0

    for row in range(10, 450):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value
        col5 = detail.cell(row, 5).value

        if col3 and not isinstance(col2, (int, float)) and col5:
            task_name_lower = str(col3).lower()
            is_technical = any(kw in task_name_lower for kw in technical_keywords)

            if is_technical:
                old_days = float(col5)
                new_days = round(old_days * TECHNICAL_TASK_MULTIPLIER, 1)
                detail.cell(row, 5).value = new_days
                detail.cell(row, 4).value = f"=E{row}*8"
                technical_updated += 1

    print(f"Updated {technical_updated} technical tasks")

    # Step 3: Find last data row and add new services
    print("\\nStep 3: Adding new services...")

    # Find last data row
    last_data_row = 449
    for row in range(449, 10, -1):
        col3 = detail.cell(row, 3).value
        if col3:
            last_data_row = row
            break

    print(f"Last data row: {last_data_row}")

    # Find next section number
    max_section = 0
    for row in range(10, last_data_row + 1):
        col2 = detail.cell(row, 2).value
        if isinstance(col2, (int, float)):
            max_section = max(max_section, int(col2))

    next_section = max_section + 1
    current_row = last_data_row + 1

    # Add new services
    for new_svc in NEW_SERVICES:
        # Service header
        detail.cell(current_row, 2).value = next_section
        detail.cell(current_row, 3).value = f"  {new_svc['name']}: Mới hoàn toàn"
        detail.cell(current_row, 3).font = Font(bold=True, size=12, name="Calibri")  # Service header font
        detail.cell(current_row, 4).value = None
        detail.cell(current_row, 5).value = None
        current_row += 1
        next_section += 1

        # Add tasks
        total_hours = new_svc["days"] * 8
        num_tasks = len(new_svc["tasks"])

        # Distribute hours
        if num_tasks <= 3:
            task_hours = [total_hours / num_tasks] * num_tasks
        else:
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
            task_hours = [total_hours * w / total_weight for w in weights]

        for i, (task_name, task_desc) in enumerate(new_svc["tasks"]):
            days = round(task_hours[i] / 8, 1)
            detail.cell(current_row, 2).value = None
            detail.cell(current_row, 3).value = f"    {task_name}: {task_desc}"
            detail.cell(current_row, 3).font = Font(bold=False, size=11, name="Calibri")  # Task font
            detail.cell(current_row, 4).value = f"=E{current_row}*8"
            detail.cell(current_row, 5).value = days
            current_row += 1

    new_last_row = current_row - 1
    print(f"Added {len(NEW_SERVICES)} new services, new last row: {new_last_row}")

    # Update totals
    detail.cell(9, 4).value = f"=SUM(D10:D{new_last_row})"
    detail.cell(9, 5).value = "=D9/8"
    detail.cell(527, 4).value = f"=SUM(D10:D{new_last_row})"
    detail.cell(527, 5).value = "=D527/8"
    detail.cell(5, 4).value = "=D527"
    detail.cell(5, 5).value = "=E527"

    # Update summary
    summary = wb["VDS_Summary_Target_State"]
    summary.cell(10, 4).value = "='VDS_Est_Detail_Target_State'!D527"
    summary.cell(10, 5).value = "='VDS_Est_Detail_Target_State'!D527"

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\\n✅ Updated complex services and added new services!")

    # Summary
    print("\\n=== Summary ===")
    print(f"Complex services updated: {len(updated_services)} (×{MULTI_INSURER_COMPLEXITY}x)")
    print(f"Technical tasks updated: {technical_updated} (×{TECHNICAL_TASK_MULTIPLIER}x)")
    print(f"New services added: {len(NEW_SERVICES)}")
    for svc in NEW_SERVICES:
        print(f"  - {svc['name']}: {svc['days']} days")
