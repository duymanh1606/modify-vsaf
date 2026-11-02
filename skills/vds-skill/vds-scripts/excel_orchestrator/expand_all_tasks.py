"""Expand all services into detailed tasks for VDS_Est_Detail_Target_State."""

import re

from openpyxl import load_workbook

# Task templates
STANDARD_TASKS = [
    ("Thiết kế API", "REST API endpoints: CRUD operations, search, filter, pagination"),
    (
        "Business Logic - Core",
        "Core business logic: validation, calculations, state management",
    ),
    (
        "Business Logic - Integration",
        "Integration logic: call external services, handle responses",
    ),
    ("Data Models", "Thiết kế schema: entities, relationships, indexes, constraints"),
    (
        "Database Layer",
        "Repository layer: JPA repositories, custom queries, transactions",
    ),
    (
        "Integration Points",
        "Tích hợp với các service khác: API clients, message handlers",
    ),
    (
        "Workflow Integration",
        "Tích hợp Camunda workflows (nếu có): BPMN flows, task handlers",
    ),
    (
        "Security & Error Handling",
        "Security: authentication, authorization. Error handling: exceptions, retry logic",
    ),
    ("Unit Test", "Unit test: service layer, repository layer, utility functions"),
    (
        "Integration Test",
        "Integration test: API tests, service integration, workflow tests",
    ),
]

SERVICE_TASKS = {
    "insurance-proposal-business": [
        (
            "Thiết kế API",
            "REST API: POST /proposals, GET /proposals/{id}, PUT /proposals/{id}, GET /proposals, DELETE /proposals/{id}",
        ),
        (
            "Logic - Khởi tạo Proposal",
            "Business logic: tạo proposal mới, validate input data, initialize proposal status",
        ),
        (
            "Logic - Tính phí",
            "Business logic: gọi Rating Engine, tính toán phí chi tiết, apply discount/promotion",
        ),
        (
            "Logic - Validation",
            "Business logic: validate dữ liệu proposal, kiểm tra business rules, eligibility check",
        ),
        (
            "Data Models",
            "Schema: Proposal, ProposalItem, ProposalStatus, ProposalHistory, relationships",
        ),
        (
            "Tích hợp Rating Engine",
            "Integration: gọi Rating Engine API, handle responses, error handling, retry logic",
        ),
        (
            "Tích hợp Product Catalog",
            "Integration: lấy thông tin sản phẩm, validate product availability",
        ),
        (
            "Tích hợp Customer Service",
            "Integration: validate customer info, check customer eligibility",
        ),
        (
            "Camunda Workflow",
            "Tích hợp Camunda: proposal approval workflow, rejection flow, cancellation flow",
        ),
        (
            "Unit Test",
            "Unit test: proposal business logic, API controllers, service methods",
        ),
        (
            "Integration Test",
            "Integration test: test với Rating Engine, Product Catalog, Customer Service, workflow",
        ),
    ],
    "insurance-policy-business": [
        (
            "Thiết kế API",
            "REST API: POST /policies (issue), PUT /policies/{id}/renew, PUT /policies/{id}/cancel, GET /policies",
        ),
        (
            "Logic - Issue Policy",
            "Business logic: issue policy từ proposal, generate policy number, create policy documents",
        ),
        (
            "Logic - Renew Policy",
            "Business logic: renewal logic, tính phí renewal, update policy term",
        ),
        (
            "Logic - Cancel Policy",
            "Business logic: cancellation rules, refund calculation, policy status update",
        ),
        (
            "Data Models",
            "Schema: Policy, PolicyItem, PolicyStatus, PolicyHistory, PolicyDocument, relationships",
        ),
        (
            "Tích hợp Proposal Service",
            "Integration: lấy proposal data, validate proposal status, convert proposal to policy",
        ),
        (
            "Tích hợp Payment Service",
            "Integration: trigger payment, handle payment confirmation, update policy status",
        ),
        (
            "Tích hợp Carrier APIs",
            "Integration: sync policy với carrier, handle carrier responses",
        ),
        (
            "Camunda Workflow",
            "Tích hợp Camunda: policy issuance flow, renewal workflow, cancellation workflow",
        ),
        (
            "Unit Test",
            "Unit test: policy operations, business logic validation, status transitions",
        ),
        (
            "Integration Test",
            "Integration test với Proposal, Payment, Carrier services, workflow tests",
        ),
    ],
    "insurance-customer-business": [
        (
            "Thiết kế API",
            "REST API: POST /customers, PUT /customers/{id}, GET /customers/{id}, GET /customers, POST /customers/{id}/members",
        ),
        (
            "Logic - Customer CRUD",
            "Business logic: create/update/read customer, validate customer data, duplicate check",
        ),
        (
            "Logic - Member Management",
            "Business logic: add/remove members, update member info, member relationships",
        ),
        (
            "Data Models",
            "Schema: Customer, Member, Address, ContactInfo, CustomerStatus, CustomerHistory, relationships",
        ),
        (
            "Tích hợp Identity Provider",
            "Integration: sync với identity provider, handle authentication events",
        ),
        (
            "Tích hợp Proposal/Policy",
            "Integration: validate customer khi tạo proposal/policy, get customer details",
        ),
        (
            "Unit Test",
            "Unit test: customer operations, member management, validation logic",
        ),
        (
            "Integration Test",
            "Integration test với Proposal, Policy services, identity provider",
        ),
    ],
    "insurance-claim-business": [
        (
            "Thiết kế API",
            "REST API: POST /claims, PUT /claims/{id}, PUT /claims/{id}/approve, PUT /claims/{id}/reject, GET /claims",
        ),
        (
            "Logic - Submit Claim",
            "Business logic: validate claim data, check policy status, calculate claim amount, validate coverage",
        ),
        (
            "Logic - Approval Workflow",
            "Business logic: approval workflow, settlement calculation, payment processing",
        ),
        (
            "Data Models",
            "Schema: Claim, ClaimItem, ClaimStatus, ClaimDocument, ClaimHistory, relationships với Policy",
        ),
        (
            "Tích hợp Policy Service",
            "Integration: validate policy, check coverage, get policy details, verify claim eligibility",
        ),
        (
            "Tích hợp Document Service",
            "Integration: upload/download claim documents, OCR processing, document validation",
        ),
        (
            "Tích hợp Payment Service",
            "Integration: process settlement payment, handle payment confirmation",
        ),
        (
            "Camunda Workflow",
            "Tích hợp Camunda: claim submission flow, approval workflow, settlement flow",
        ),
        ("Unit Test", "Unit test: claim operations, business logic, calculation logic"),
        (
            "Integration Test",
            "Integration test với Policy, Document, Payment services, workflow tests",
        ),
    ],
}


def extract_service_name(task_name):
    if not task_name:
        return None
    task_str = str(task_name)
    if "insurance-" in task_str:
        match = re.search(r"insurance-[a-z-]+", task_str)
        if match:
            return match.group(0)
    return None


def get_tasks_for_service(service_name):
    if service_name and service_name in SERVICE_TASKS:
        return SERVICE_TASKS[service_name]
    return STANDARD_TASKS


def distribute_hours(total_hours, num_tasks):
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
    summary = wb["VDS_Summary_Target_State"]

    # Read current services
    services = []
    for row in range(10, 57):
        task_name = detail.cell(row, 2).value
        hours = detail.cell(row, 3).value
        if task_name and hours:
            service_name = extract_service_name(task_name)
            # Extract workstream
            workstream = None
            if "(" in str(task_name) and ")" in str(task_name):
                match = re.search(r"\(([^)]+)\)", str(task_name))
                if match:
                    workstream = match.group(1)

            services.append(
                {
                    "row": row,
                    "task_name": task_name,
                    "service_name": service_name,
                    "workstream": workstream,
                    "hours": float(hours) if isinstance(hours, (int, float)) else 0,
                    "remarks": detail.cell(row, 5).value,
                }
            )

    print(f"Found {len(services)} services to expand")

    # Clear existing data rows (10-56)
    print("Clearing existing data rows...")
    for row in range(10, 57):
        for col in range(1, 6):
            detail.cell(row, col).value = None

    # Insert detailed tasks starting from row 10
    current_row = 10
    task_count = 0

    for service in services:
        service_name = service["service_name"]
        tasks = get_tasks_for_service(service_name)
        task_hours = distribute_hours(service["hours"], len(tasks))

        # Add service header row (indented, like original format)
        detail.cell(current_row, 1).value = None
        service_display_name = (
            service_name.replace("insurance-", "").replace("-", " ").title() if service_name else "Service"
        )
        if service["workstream"]:
            detail.cell(current_row, 2).value = f"  {service_display_name} ({service['workstream']})"
        else:
            detail.cell(current_row, 2).value = f"  {service_display_name}"
        detail.cell(current_row, 3).value = service["hours"]
        detail.cell(current_row, 4).value = f"=C{current_row}/8"
        detail.cell(current_row, 5).value = service["remarks"]
        current_row += 1

        # Add detailed task rows
        for i, (task_name, task_desc) in enumerate(tasks):
            detail.cell(current_row, 1).value = task_count + 1
            detail.cell(current_row, 2).value = f"    {task_name}"
            detail.cell(current_row, 3).value = round(task_hours[i], 1)
            detail.cell(current_row, 4).value = f"=C{current_row}/8"
            detail.cell(current_row, 5).value = task_desc
            current_row += 1
            task_count += 1

    print(f"Created {task_count} detailed tasks across {len(services)} services")
    print(f"Last data row: {current_row - 1}")

    # Update total row
    total_row = current_row
    detail.cell(total_row, 2).value = "Total Coding & Unit Test Effort"
    detail.cell(total_row, 3).value = f"=SUM(C10:C{current_row - 1})"
    detail.cell(total_row, 4).value = f"=C{total_row}/8"

    # Update category total (row 9)
    detail.cell(9, 4).value = f"=SUM(D10:D{current_row - 1})"

    # Update row 5 formulas
    detail.cell(5, 4).value = f"=D{total_row}"
    detail.cell(5, 5).value = f"=E{total_row}"

    # Update summary sheet
    summary.cell(10, 4).value = f"='VDS_Est_Detail_Target_State'!C{total_row}"
    summary.cell(10, 5).value = f"='VDS_Est_Detail_Target_State'!C{total_row}"

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\n✅ Expanded all services into detailed tasks")
    print(f"✅ Updated formulas (total row: {total_row})")
