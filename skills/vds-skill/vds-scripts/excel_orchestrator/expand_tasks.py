"""Expand services into detailed tasks for VDS_Est_Detail_Target_State sheet."""

from openpyxl import load_workbook

# Standard task breakdown template for microservices
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
        "Security",
        "Security: authentication, authorization, input validation, data encryption",
    ),
    (
        "Error Handling",
        "Error handling: exception handling, retry logic, circuit breakers",
    ),
    ("Unit Test", "Unit test: service layer, repository layer, utility functions"),
    (
        "Integration Test",
        "Integration test: API tests, service integration, workflow tests",
    ),
]

# Service-specific task breakdowns
SERVICE_SPECIFIC_TASKS = {
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
            "Schema: Proposal, ProposalItem, ProposalStatus, ProposalHistory, relationships với Customer và Product",
        ),
        (
            "Tích hợp Rating Engine",
            "Integration: gọi Rating Engine API, handle responses, error handling, retry logic",
        ),
        (
            "Tích hợp Product Catalog",
            "Integration: lấy thông tin sản phẩm, validate product availability, get product details",
        ),
        (
            "Tích hợp Customer Service",
            "Integration: validate customer info, check customer eligibility, get customer details",
        ),
        (
            "Camunda Workflow",
            "Tích hợp Camunda: proposal approval workflow, rejection flow, cancellation flow, task handlers",
        ),
        (
            "Unit Test",
            "Unit test: proposal business logic, API controllers, service methods, validation rules",
        ),
        (
            "Integration Test",
            "Integration test: test với Rating Engine, Product Catalog, Customer Service, workflow end-to-end",
        ),
    ],
    "insurance-policy-business": [
        (
            "Thiết kế API",
            "REST API: POST /policies (issue), PUT /policies/{id}/renew, PUT /policies/{id}/cancel, GET /policies/{id}, GET /policies",
        ),
        (
            "Logic - Issue Policy",
            "Business logic: issue policy từ proposal, generate policy number, create policy documents, update status",
        ),
        (
            "Logic - Renew Policy",
            "Business logic: renewal logic, tính phí renewal, update policy term, handle renewal rules",
        ),
        (
            "Logic - Cancel Policy",
            "Business logic: cancellation rules, refund calculation, policy status update, cancellation workflow",
        ),
        (
            "Data Models",
            "Schema: Policy, PolicyItem, PolicyStatus, PolicyHistory, PolicyDocument, relationships với Proposal và Customer",
        ),
        (
            "Tích hợp Proposal Service",
            "Integration: lấy proposal data, validate proposal status, convert proposal to policy",
        ),
        (
            "Tích hợp Payment Service",
            "Integration: trigger payment, handle payment confirmation, update policy status based on payment",
        ),
        (
            "Tích hợp Carrier APIs",
            "Integration: sync policy với carrier, handle carrier responses, error handling",
        ),
        (
            "Camunda Workflow",
            "Tích hợp Camunda: policy issuance flow, renewal workflow, cancellation workflow, async callbacks",
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
            "Business logic: create/update/read customer, validate customer data, duplicate check, data validation",
        ),
        (
            "Logic - Member Management",
            "Business logic: add/remove members, update member info, member relationships, member validation",
        ),
        (
            "Data Models",
            "Schema: Customer, Member, Address, ContactInfo, CustomerStatus, CustomerHistory, relationships",
        ),
        (
            "Tích hợp Identity Provider",
            "Integration: sync với identity provider, handle authentication events, user provisioning",
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
            "Business logic: approval workflow, settlement calculation, payment processing, status updates",
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
            "Integration: process settlement payment, handle payment confirmation, update claim status",
        ),
        (
            "Camunda Workflow",
            "Tích hợp Camunda: claim submission flow, approval workflow, settlement flow, task handlers",
        ),
        ("Unit Test", "Unit test: claim operations, business logic, calculation logic"),
        (
            "Integration Test",
            "Integration test với Policy, Document, Payment services, workflow tests",
        ),
    ],
}


def get_task_breakdown(service_name: str) -> list:
    """Get detailed task breakdown for a service."""
    if service_name in SERVICE_SPECIFIC_TASKS:
        return SERVICE_SPECIFIC_TASKS[service_name]
    # Use standard template for other services
    return STANDARD_TASKS


def distribute_effort(total_hours: float, num_tasks: int) -> list:
    """Distribute total hours across tasks with weighted distribution."""
    # Weight distribution: API and Business Logic get more, Testing gets less

    # Calculate base hours per task
    base_hours = total_hours / num_tasks

    # Apply weights
    task_hours = []
    for i in range(num_tasks):
        # Simple distribution: first tasks get more (API, Logic), last tasks get less (Tests)
        if i < 2:
            weight = 1.3  # API and first logic task
        elif i < 5:
            weight = 1.1  # Core business logic
        elif i < 8:
            weight = 1.0  # Integration and data
        else:
            weight = 0.8  # Testing
        task_hours.append(base_hours * weight)

    # Normalize to total
    total_weighted = sum(task_hours)
    task_hours = [h * total_hours / total_weighted for h in task_hours]

    return task_hours


if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    # Read current services
    services = []
    for row in range(10, 57):
        task_name = detail.cell(row, 2).value
        hours = detail.cell(row, 3).value
        if task_name and hours:
            # Extract service name
            service_name = None
            task_str = str(task_name)
            if "insurance-" in task_str:
                # Extract service name from pattern like "Core - insurance-xxx (Workstream): Description"
                parts = task_str.split("(")
                if len(parts) > 0:
                    service_part = parts[0].strip()
                    if " - " in service_part:
                        service_name = service_part.split(" - ")[1].strip()

            if not service_name:
                # Try to extract from task name
                if "insurance-" in task_str:
                    start = task_str.find("insurance-")
                    end = task_str.find(" ", start)
                    if end == -1:
                        end = task_str.find("(", start)
                    if end == -1:
                        end = len(task_str)
                    service_name = task_str[start:end].strip()

            services.append(
                {
                    "row": row,
                    "task_name": task_name,
                    "service_name": service_name or f"service-{row}",
                    "hours": float(hours) if isinstance(hours, (int, float)) else 0,
                    "remarks": detail.cell(row, 5).value,
                }
            )

    print(f"Found {len(services)} services to expand")
    print(f"First service: {services[0]['service_name']} - {services[0]['hours']} hours")

    # Test task breakdown
    test_service = services[0]
    tasks = get_task_breakdown(test_service["service_name"])
    task_hours = distribute_effort(test_service["hours"], len(tasks))
    print(f"\\nTask breakdown for {test_service['service_name']}:")
    for i, (task_name, _task_desc) in enumerate(tasks):
        print(f"  {i + 1}. {task_name}: {task_hours[i]:.1f} hours")
