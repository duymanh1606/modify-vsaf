"""
Add essential missing effort to estimation based on research and analysis.
Focuses on critical production-ready requirements only.
"""

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

FILE_PATH = "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
wb = load_workbook(FILE_PATH)

ws_detail = wb["VDS_Est_Detail_Target_State"]
ws_total = wb["VDS_Est_Detail_Services_Total"]

# Essential missing tasks - conservative estimates based on research
ESSENTIAL_TASKS = [
    # Cross-service integration testing (critical for microservices)
    {
        "service_id": "C",  # Platform-level
        "task_name": "Cross-Service Integration Testing: End-to-end integration tests across service boundaries",
        "days": 40.0,
        "remarks": "Platform-level: Critical business flows across multiple services",
    },
    # Performance testing (critical for insurance platform)
    {
        "service_id": "C",
        "task_name": "Performance Testing: Load testing for critical services (Rating Engine, Claims, Underwriting)",
        "days": 25.0,
        "remarks": "Platform-level: Focus on high-traffic services",
    },
    # E2E testing framework and critical flows
    {
        "service_id": "C",
        "task_name": "End-to-End Testing: E2E test framework setup and critical business flow tests",
        "days": 30.0,
        "remarks": "Platform-level: Critical user journeys",
    },
    # Infrastructure - CI/CD
    {
        "service_id": "C",
        "task_name": "CI/CD Pipeline Setup: Automated build, test, and deployment pipelines",
        "days": 20.0,
        "remarks": "Platform-level: Shared infrastructure",
    },
    # Infrastructure - Monitoring & Observability
    {
        "service_id": "C",
        "task_name": "Monitoring & Observability: Logging, metrics, distributed tracing setup",
        "days": 25.0,
        "remarks": "Platform-level: Shared monitoring infrastructure",
    },
    # API Documentation
    {
        "service_id": "C",
        "task_name": "API Documentation: OpenAPI/Swagger documentation generation and maintenance",
        "days": 15.0,
        "remarks": "Platform-level: Automated API documentation",
    },
    # Security testing basics
    {
        "service_id": "C",
        "task_name": "Security Testing: Basic security testing and vulnerability scanning",
        "days": 20.0,
        "remarks": "Platform-level: Security testing framework",
    },
    # Service mesh / API Gateway (if needed)
    {
        "service_id": "C",
        "task_name": "API Gateway & Service Mesh: Gateway setup and service mesh configuration",
        "days": 30.0,
        "remarks": "Platform-level: Service communication infrastructure",
    },
    # Compliance basics
    {
        "service_id": "C",
        "task_name": "Compliance & Audit: Audit trail implementation and compliance validation",
        "days": 25.0,
        "remarks": "Platform-level: Regulatory compliance framework",
    },
    # Data migration additional (validation, testing)
    {
        "service_id": "C",
        "task_name": "Data Migration Support: Data validation, migration testing, rollback procedures",
        "days": 20.0,
        "remarks": "Platform-level: Data migration support tasks",
    },
]

# Find the last row in detail sheet
last_row = ws_detail.max_row
next_row = last_row + 1

# Find service C row (Platform-level tasks)
service_c_row = None
for row in range(9, ws_detail.max_row + 1):
    col2 = ws_detail.cell(row, 2).value
    if col2 == "C" or (isinstance(col2, str) and col2.strip() == "C"):
        # Check if it's a service header (has remarks or is bold)
        col6 = ws_detail.cell(row, 6).value
        if col6 or ws_detail.cell(row, 2).font.bold:
            service_c_row = row
            break

# If no service C found, create it
if not service_c_row:
    service_c_row = next_row
    ws_detail.cell(service_c_row, 2).value = "C"
    ws_detail.cell(service_c_row, 2).font = Font(bold=True, size=11)
    ws_detail.cell(service_c_row, 3).value = "Platform-Level Infrastructure & Testing"
    ws_detail.cell(service_c_row, 3).font = Font(bold=True, size=11)
    ws_detail.cell(service_c_row, 6).value = "Platform-level infrastructure, testing, and compliance tasks"
    next_row = service_c_row + 1

# Insert essential tasks after service C header
insert_row = service_c_row + 1

# Shift existing rows down if needed
if insert_row <= ws_detail.max_row:
    ws_detail.insert_rows(insert_row, len(ESSENTIAL_TASKS))

# Add essential tasks
for idx, task in enumerate(ESSENTIAL_TASKS):
    row = insert_row + idx

    # Column 2: Service ID (empty for sub-tasks)
    ws_detail.cell(row, 2).value = ""

    # Column 3: Task Name
    ws_detail.cell(row, 3).value = task["task_name"]

    # Column 4: Hours (formula: Days * 8)
    ws_detail.cell(row, 4).value = f"=E{row}*8"

    # Column 5: Days
    ws_detail.cell(row, 5).value = task["days"]
    ws_detail.cell(row, 5).number_format = "0.00"

    # Column 6: Remarks
    ws_detail.cell(row, 6).value = task["remarks"]

# Update total formulas - find the total row
total_row = None
for row in range(ws_detail.max_row, 9, -1):
    col3 = ws_detail.cell(row, 3).value
    if col3 and "total" in str(col3).lower():
        total_row = row
        break

if total_row:
    # Update total formula to include new rows
    # Find the range
    start_row = 10  # First task row
    end_row = insert_row + len(ESSENTIAL_TASKS) - 1

    # Update hours total
    ws_detail.cell(total_row, 4).value = f"=SUM(D{start_row}:D{end_row})"

    # Update days total
    ws_detail.cell(total_row, 5).value = f"=SUM(E{start_row}:E{end_row})"

# Calculate total for new tasks
total_days = sum(task["days"] for task in ESSENTIAL_TASKS)
total_hours = total_days * 8

print("=== Added Essential Missing Effort ===\n")
print(f"Tasks Added: {len(ESSENTIAL_TASKS)}")
print(f"Total Days: {total_days:.1f}")
print(f"Total Hours: {total_hours:.1f}")
print("\nTasks:")
for task in ESSENTIAL_TASKS:
    print(f"  - {task['task_name']}: {task['days']:.1f} days")

# Update Services Total sheet - add Platform Infrastructure service
# Find if Platform Infrastructure already exists
platform_exists = False
platform_row = None
for row in range(2, ws_total.max_row + 1):
    col2 = ws_total.cell(row, 2).value
    if col2 and "platform" in str(col2).lower() and "infrastructure" in str(col2).lower():
        platform_exists = True
        platform_row = row
        break

if not platform_exists:
    # Find last service number
    last_service_num = 0
    for row in range(2, ws_total.max_row + 1):
        col1 = ws_total.cell(row, 1).value
        if isinstance(col1, (int, float)) and col1 > 0:
            last_service_num = max(last_service_num, int(col1))

    # Add new service
    new_row = ws_total.max_row + 1
    ws_total.cell(new_row, 1).value = last_service_num + 1
    ws_total.cell(new_row, 2).value = "Platform Infrastructure & Testing"
    ws_total.cell(new_row, 3).value = "Platform-level"
    ws_total.cell(new_row, 4).value = total_days
    ws_total.cell(new_row, 4).number_format = "0.00"
    ws_total.cell(new_row, 5).value = f"=D{new_row}*8"
    ws_total.cell(new_row, 6).value = "VDS"  # Platform infrastructure typically VDS responsibility

    # Copy formatting from previous row
    if ws_total.max_row > 2:
        prev_row = new_row - 1
        prev_cell = ws_total.cell(prev_row, 1)

        # Get font attributes
        font_name = prev_cell.font.name if prev_cell.font else "Calibri"
        font_size = prev_cell.font.size if prev_cell.font else 11
        font_bold = prev_cell.font.bold if prev_cell.font else False

        # Get fill attributes
        fill_type = prev_cell.fill.fill_type if prev_cell.fill else None
        fill_start_color = prev_cell.fill.start_color if prev_cell.fill else None

        # Get alignment
        align_horizontal = prev_cell.alignment.horizontal if prev_cell.alignment else None
        align_vertical = prev_cell.alignment.vertical if prev_cell.alignment else None

        # Apply formatting to all columns
        for col in range(1, 7):
            cell = ws_total.cell(new_row, col)
            cell.font = Font(name=font_name, size=font_size, bold=font_bold)
            if fill_type:
                cell.fill = PatternFill(fill_type=fill_type, start_color=fill_start_color)
            if align_horizontal:
                cell.alignment = Alignment(horizontal=align_horizontal, vertical=align_vertical)

    print(f"\nAdded to Services Total: Service {last_service_num + 1} - Platform Infrastructure & Testing")
else:
    # Update existing platform service
    ws_total.cell(platform_row, 4).value = total_days
    ws_total.cell(platform_row, 5).value = f"=D{platform_row}*8"
    print("\nUpdated Services Total: Platform Infrastructure & Testing")

# Update total row in Services Total
total_row_total = None
for row in range(ws_total.max_row, 2, -1):
    col2 = ws_total.cell(row, 2).value
    if col2 and "total" in str(col2).lower():
        total_row_total = row
        break

if total_row_total:
    # Update totals
    start_row_total = 2
    end_row_total = ws_total.max_row - 1  # Exclude total row

    ws_total.cell(total_row_total, 4).value = f"=SUM(D{start_row_total}:D{end_row_total})"
    ws_total.cell(total_row_total, 5).value = f"=SUM(E{start_row_total}:E{end_row_total})"

# Save workbook
wb.save(FILE_PATH)
print("\n✅ Essential missing effort added successfully!")
print(f"File saved: {FILE_PATH}")
