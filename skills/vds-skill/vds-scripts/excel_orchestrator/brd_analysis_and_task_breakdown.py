"""
BRD Analysis and Detailed Task Breakdown Generator

This script:
1. Extracts requirements from BRD NTBH 2.0
2. Maps BRD requirements to services
3. Creates detailed task breakdowns with BRD references
4. Generates new Excel sheet: VDS_Task_Breakdown_Detailed
"""

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# File paths
BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")
EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)

# Task categories
TASK_CATEGORIES = [
    "Requirements & Analysis",
    "Design & Architecture",
    "Development",
    "Integration",
    "Testing",
    "Documentation",
    "Deployment",
    "Compliance & Regulatory",
    "Security",
    "Data Migration",
]

# Complexity levels
COMPLEXITY_LEVELS = ["Simple", "Medium", "Complex", "Very Complex"]

# Multipliers
MULTIPLIERS = {
    "base": 1.59,
    "ai": 1.4,
    "workflow": 1.25,
    "logic": 1.3,
    "multi_insurer": 2.0,
    "renewal_complexity": 1.3,
    "dynamic_pricing": 1.2,
    "claims_complexity": 1.25,
    "payment_complexity": 1.15,
    "product_comparison": 1.1,
    "compliance": 1.05,
    "performance": 1.05,
}


def extract_brd_requirements(brd_path: Path) -> dict:
    """Extract all requirements from BRD markdown file."""
    print("Extracting BRD requirements...")

    with open(brd_path, encoding="utf-8") as f:
        content = f.read()

    requirements = {
        "section3": {},  # Customer features
        "section4": {},  # Admin features
    }

    # Extract Section 3 (Customer features)
    section3_pattern = r"## \*\*MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO KHÁCH HÀNG\*\*(.*?)## \*\*MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN\*\*"
    section3_match = re.search(section3_pattern, content, re.DOTALL)

    if section3_match:
        section3_content = section3_match.group(1)

        # Extract main sections (## headings)
        main_sections = re.finditer(r"## \*\*(.*?)\*\*", section3_content)
        for main_match in main_sections:
            section_title = main_match.group(1).strip()
            start_pos = main_match.end()

            # Find next main section or end
            next_main = re.search(r"\n## \*\*", section3_content[start_pos:])
            if next_main:
                section_content = section3_content[start_pos : start_pos + next_main.start()]
            else:
                section_content = section3_content[start_pos:]

            # Extract subsections (### headings)
            subsections = {}
            sub_matches = re.finditer(r"### (.*?)(?=\n|$)", section_content, re.MULTILINE)
            for sub_match in sub_matches:
                sub_title = sub_match.group(1).strip()
                sub_start = sub_match.end()

                # Get content until next ### or end
                next_sub = re.search(r"\n### ", section_content[sub_start:])
                if next_sub:
                    sub_content = section_content[sub_start : sub_start + next_sub.start()]
                else:
                    sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            requirements["section3"][section_title] = {
                "content": section_content.strip(),
                "subsections": subsections,
            }

    # Extract Section 4 (Admin features)
    section4_pattern = r"## \*\*MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN\*\*(.*?)$"
    section4_match = re.search(section4_pattern, content, re.DOTALL)

    if section4_match:
        section4_content = section4_match.group(1)

        # Extract main sections
        main_sections = re.finditer(r"## \*\*(.*?)\*\*", section4_content)
        for main_match in main_sections:
            section_title = main_match.group(1).strip()
            start_pos = main_match.end()

            next_main = re.search(r"\n## \*\*", section4_content[start_pos:])
            if next_main:
                section_content = section4_content[start_pos : start_pos + next_main.start()]
            else:
                section_content = section4_content[start_pos:]

            # Extract subsections
            subsections = {}
            sub_matches = re.finditer(r"### (.*?)(?=\n|$)", section_content, re.MULTILINE)
            for sub_match in sub_matches:
                sub_title = sub_match.group(1).strip()
                sub_start = sub_match.end()

                next_sub = re.search(r"\n### ", section_content[sub_start:])
                if next_sub:
                    sub_content = section_content[sub_start : sub_start + next_sub.start()]
                else:
                    sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            requirements["section4"][section_title] = {
                "content": section_content.strip(),
                "subsections": subsections,
            }

    print(f"Extracted {len(requirements['section3'])} customer feature sections")
    print(f"Extracted {len(requirements['section4'])} admin feature sections")

    return requirements


def get_service_list(excel_path: Path) -> list[dict]:
    """Get list of all services from Excel file."""
    print("Reading service list from Excel...")

    wb = load_workbook(excel_path, data_only=True)
    ws_services = wb["VDS_Est_Detail_Services_Total"]

    services = []
    for row in range(2, 100):
        service_id = ws_services.cell(row, 1).value
        service_name = ws_services.cell(row, 2).value
        responsibility = ws_services.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and service_name:
            services.append(
                {
                    "id": int(service_id),
                    "name": service_name,
                    "responsibility": responsibility or "Unknown",
                }
            )

    print(f"Found {len(services)} services")
    return services


def map_brd_to_services(requirements: dict, services: list[dict]) -> dict:
    """Map BRD requirements to services."""
    print("Mapping BRD requirements to services...")

    # Define mapping rules based on service names and BRD sections
    mapping = {}

    # Section 3 mappings (Customer features)
    section3_mappings = {
        "Tài Khoản": ["Customer Business", "User Management Service"],
        "Quản Lý Thông Tin": ["Customer Business"],
        "Mua Bảo Hiểm": [
            "Proposal Business",
            "Intelligent Recommendation Service",
            "Intelligent Filtering Service",
            "Chatbot Service",
            "Product Catalog",
            "Billing Service",
        ],
        "Quản lý hợp đồng bảo hiểm": [
            "Policy Business",
            "Renewal Process",
            "Contract Orchestrator",
        ],
        "Yêu Cầu Bồi Thường": ["Claim Business"],
    }

    # Section 4 mappings (Admin features)
    section4_mappings = {
        "Quản Lý Tài Khoản Quản Trị Viên": ["User Management Service", "CMS Backend"],
        "Quản Lý Đối Tác": ["CMS Backend"],
        "Quản Lý Sản Phẩm": ["Product Catalog", "CMS Backend"],
        "Quản Lý Khách Hàng": ["Customer Business", "CRM Service", "CMS Backend"],
        "Quản Lý Hợp Đồng": ["Policy Business", "CMS Backend"],
        "Quản Lý Yêu Cầu Bồi Thường (YCBT)": ["Claim Business", "CMS Backend"],
        "Quản Lý Kênh Bán": ["CMS Backend"],
        "Quản Lý Chiến Dịch": ["Promotion Business", "CMS Backend"],
        "Quản Lý Nội Dung": ["CMS Backend", "Document Management Service"],
        "Báo Cáo và Đối Soát": ["Analytics Service", "CMS Backend"],
        "Tính Năng: Cảnh Báo": ["Notification SPI", "CMS Backend"],
    }

    # Create service name lookup
    service_lookup = {s["name"]: s for s in services}

    # Map Section 3
    for brd_section, service_names in section3_mappings.items():
        for service_name in service_names:
            if service_name in service_lookup:
                service_id = service_lookup[service_name]["id"]
                if service_id not in mapping:
                    mapping[service_id] = {
                        "service": service_lookup[service_name],
                        "brd_sections": [],
                    }
                mapping[service_id]["brd_sections"].append(
                    {"section": "3", "subsection": brd_section, "type": "customer"}
                )

    # Map Section 4
    for brd_section, service_names in section4_mappings.items():
        for service_name in service_names:
            if service_name in service_lookup:
                service_id = service_lookup[service_name]["id"]
                if service_id not in mapping:
                    mapping[service_id] = {
                        "service": service_lookup[service_name],
                        "brd_sections": [],
                    }
                mapping[service_id]["brd_sections"].append({"section": "4", "subsection": brd_section, "type": "admin"})

    print(f"Mapped {len(mapping)} services to BRD requirements")
    return mapping


def generate_tasks_for_service(service: dict, brd_mapping: dict, requirements: dict) -> list[dict]:
    """Generate detailed tasks for a service based on BRD requirements."""
    service_id = service["id"]
    service_name = service["name"]

    tasks = []
    task_counter = 1

    # Get BRD sections for this service
    brd_sections = brd_mapping.get(service_id, {}).get("brd_sections", [])

    # Determine multipliers based on service type
    multipliers = ["base"]  # Base buffer always applied

    if any(
        "Intelligent" in service_name
        or "Chatbot" in service_name
        or "Recommendation" in service_name
        or "Filtering" in service_name
        for s in [service_name]
    ):
        multipliers.append("ai")

    if any(
        "Process" in service_name or "Orchestrator" in service_name or "Workflow" in service_name
        for s in [service_name]
    ):
        multipliers.append("workflow")

    if "Renewal" in service_name:
        multipliers.append("renewal_complexity")

    if "Claim" in service_name:
        multipliers.append("claims_complexity")

    if "Billing" in service_name or "Payment" in service_name:
        multipliers.append("payment_complexity")

    if "Intelligent Filtering" in service_name:
        multipliers.append("dynamic_pricing")

    if "Proposal" in service_name:
        multipliers.append("product_comparison")

    if "Insurer" in service_name:
        multipliers.append("multi_insurer")

    # Standard task template for all services
    standard_tasks = [
        {
            "category": "Requirements & Analysis",
            "name": "BRD Analysis and Requirements Extraction",
            "brd_ref": (
                ", ".join([f"{s['section']}.{s['subsection'][:20]}" for s in brd_sections[:3]])
                if brd_sections
                else "N/A"
            ),
            "complexity": "Medium",
            "base_effort": 3,
            "notes": f"Analyze BRD requirements for {service_name}",
        },
        {
            "category": "Design & Architecture",
            "name": "API Design: REST endpoints design",
            "brd_ref": "N/A",
            "complexity": "Medium",
            "base_effort": 4,
            "notes": "Design RESTful API endpoints",
        },
        {
            "category": "Design & Architecture",
            "name": "Data Model Design: Entity and relationship design",
            "brd_ref": "N/A",
            "complexity": "Medium",
            "base_effort": 3,
            "notes": "Design database schema",
        },
        {
            "category": "Development",
            "name": "Business Logic: Core business logic implementation",
            "brd_ref": (", ".join([f"{s['section']}" for s in brd_sections[:2]]) if brd_sections else "N/A"),
            "complexity": "Complex",
            "base_effort": 15,
            "notes": f"Implement core business logic for {service_name}",
        },
        {
            "category": "Development",
            "name": "Data Access Layer: Repository and JPA implementation",
            "brd_ref": "N/A",
            "complexity": "Medium",
            "base_effort": 5,
            "notes": "Implement data access layer",
        },
        {
            "category": "Integration",
            "name": "External Integration: Integration with external systems",
            "brd_ref": "N/A",
            "complexity": "Complex",
            "base_effort": 8,
            "notes": "Integrate with external APIs",
        },
        {
            "category": "Testing",
            "name": "Unit Testing: Unit tests for business logic",
            "brd_ref": "N/A",
            "complexity": "Medium",
            "base_effort": 5,
            "notes": "Write and execute unit tests",
        },
        {
            "category": "Testing",
            "name": "Integration Testing: Integration tests with other services",
            "brd_ref": "N/A",
            "complexity": "Complex",
            "base_effort": 6,
            "notes": "Write and execute integration tests",
        },
        {
            "category": "Documentation",
            "name": "API Documentation: OpenAPI/Swagger documentation",
            "brd_ref": "N/A",
            "complexity": "Simple",
            "base_effort": 2,
            "notes": "Generate API documentation",
        },
        {
            "category": "Deployment",
            "name": "Deployment: CI/CD pipeline and deployment scripts",
            "brd_ref": "N/A",
            "complexity": "Medium",
            "base_effort": 3,
            "notes": "Setup deployment automation",
        },
    ]

    # Add service-specific tasks based on BRD requirements
    if brd_sections:
        for brd_section in brd_sections:
            brd_section["section"]
            subsection = brd_section["subsection"]

            # Add BRD-specific tasks
            if "Mua Bảo Hiểm" in subsection:
                standard_tasks.append(
                    {
                        "category": "Development",
                        "name": "Purchase Flow: Implement purchase workflow with guest checkout",
                        "brd_ref": "3.3.5",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "notes": "Guest checkout and account creation during purchase",
                    }
                )

            if "Gia Hạn" in subsection or "Tái Tục" in subsection:
                standard_tasks.append(
                    {
                        "category": "Development",
                        "name": "Renewal Workflows: Implement 4 renewal types",
                        "brd_ref": "3.4.3",
                        "complexity": "Very Complex",
                        "base_effort": 12,
                        "notes": "Four different renewal workflow types",
                    }
                )

            if "Bồi Thường" in subsection:
                standard_tasks.append(
                    {
                        "category": "Development",
                        "name": "Claims State Machine: Implement 8+ state transitions",
                        "brd_ref": "3.5",
                        "complexity": "Very Complex",
                        "base_effort": 15,
                        "notes": "Complex state machine with multiple transitions",
                    }
                )

    # Add compliance and security tasks (cross-cutting)
    standard_tasks.extend(
        [
            {
                "category": "Compliance & Regulatory",
                "name": "Compliance: Audit trail and regulatory compliance",
                "brd_ref": "N/A",
                "complexity": "Medium",
                "base_effort": 3,
                "notes": "Implement audit trails and compliance features",
            },
            {
                "category": "Security",
                "name": "Security: Authentication, authorization, and data encryption",
                "brd_ref": "N/A",
                "complexity": "Medium",
                "base_effort": 4,
                "notes": "Implement security features",
            },
        ]
    )

    # Process tasks and add metadata
    for task in standard_tasks:
        # Calculate final effort with multipliers
        base_effort = task["base_effort"]
        final_multiplier = 1.0

        for mult_name in multipliers:
            if mult_name in MULTIPLIERS:
                final_multiplier *= MULTIPLIERS[mult_name]

        final_effort_days = round(base_effort * final_multiplier, 2)
        final_effort_hours = round(final_effort_days * 8, 2)

        multiplier_str = " × ".join([f"{MULTIPLIERS.get(m, 1.0):.2f}x" for m in multipliers])

        tasks.append(
            {
                "service_id": service_id,
                "service_name": service_name,
                "task_id": f"S{service_id}-T{task_counter:03d}",
                "task_category": task["category"],
                "task_name": task["name"],
                "brd_reference": task["brd_ref"],
                "complexity_level": task["complexity"],
                "base_effort_days": base_effort,
                "multiplier_applied": multiplier_str,
                "final_effort_days": final_effort_days,
                "final_effort_hours": final_effort_hours,
                "dependencies": "",
                "notes": task["notes"],
            }
        )

        task_counter += 1

    return tasks


def create_task_breakdown_sheet(excel_path: Path, all_tasks: list[dict]):
    """Create the new VDS_Task_Breakdown_Detailed sheet."""
    print(f"Creating task breakdown sheet with {len(all_tasks)} tasks...")

    wb = load_workbook(excel_path)

    # Remove sheet if exists
    if "VDS_Task_Breakdown_Detailed" in wb.sheetnames:
        wb.remove(wb["VDS_Task_Breakdown_Detailed"])

    ws = wb.create_sheet("VDS_Task_Breakdown_Detailed", 0)

    # Define headers
    headers = [
        "Service ID",
        "Service Name",
        "Task Category",
        "Task ID",
        "Task Name",
        "BRD Reference",
        "Complexity Level",
        "Base Effort (Days)",
        "Multiplier Applied",
        "Final Effort (Days)",
        "Final Effort (Hours)",
        "Dependencies",
        "Notes",
    ]

    # Write headers
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    # Write data
    for row_idx, task in enumerate(all_tasks, 2):
        ws.cell(row=row_idx, column=1, value=task["service_id"]).border = border
        ws.cell(row=row_idx, column=2, value=task["service_name"]).border = border
        ws.cell(row=row_idx, column=3, value=task["task_category"]).border = border
        ws.cell(row=row_idx, column=4, value=task["task_id"]).border = border
        ws.cell(row=row_idx, column=5, value=task["task_name"]).border = border
        ws.cell(row=row_idx, column=6, value=task["brd_reference"]).border = border
        ws.cell(row=row_idx, column=7, value=task["complexity_level"]).border = border
        ws.cell(row=row_idx, column=8, value=task["base_effort_days"]).border = border
        ws.cell(row=row_idx, column=9, value=task["multiplier_applied"]).border = border
        ws.cell(row=row_idx, column=10, value=task["final_effort_days"]).border = border
        ws.cell(row=row_idx, column=11, value=task["final_effort_hours"]).border = border
        ws.cell(row=row_idx, column=12, value=task["dependencies"]).border = border
        ws.cell(row=row_idx, column=13, value=task["notes"]).border = border

        # Format numbers
        ws.cell(row=row_idx, column=8).number_format = "0.00"
        ws.cell(row=row_idx, column=10).number_format = "0.00"
        ws.cell(row=row_idx, column=11).number_format = "0.00"

    # Auto-adjust column widths
    column_widths = {
        "A": 12,  # Service ID
        "B": 35,  # Service Name
        "C": 25,  # Task Category
        "D": 12,  # Task ID
        "E": 50,  # Task Name
        "F": 20,  # BRD Reference
        "G": 18,  # Complexity Level
        "H": 18,  # Base Effort
        "I": 30,  # Multiplier Applied
        "J": 18,  # Final Effort Days
        "K": 18,  # Final Effort Hours
        "L": 30,  # Dependencies
        "M": 50,  # Notes
    }

    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    # Freeze first row
    ws.freeze_panes = "A2"

    # Add summary section
    summary_row = len(all_tasks) + 3
    ws.cell(row=summary_row, column=1, value="SUMMARY").font = Font(bold=True, size=12)
    ws.cell(row=summary_row + 1, column=1, value="Total Tasks:").font = Font(bold=True)
    ws.cell(row=summary_row + 1, column=2, value=len(all_tasks))
    ws.cell(row=summary_row + 2, column=1, value="Total Base Effort (Days):").font = Font(bold=True)
    ws.cell(row=summary_row + 2, column=2, value=f"=SUM(H2:H{len(all_tasks) + 1})")
    ws.cell(row=summary_row + 3, column=1, value="Total Final Effort (Days):").font = Font(bold=True)
    ws.cell(row=summary_row + 3, column=2, value=f"=SUM(J2:J{len(all_tasks) + 1})")
    ws.cell(row=summary_row + 4, column=1, value="Total Final Effort (Hours):").font = Font(bold=True)
    ws.cell(row=summary_row + 4, column=2, value=f"=SUM(K2:K{len(all_tasks) + 1})")

    wb.save(excel_path)
    print(f"Created VDS_Task_Breakdown_Detailed sheet with {len(all_tasks)} tasks")


def main():
    """Main execution function."""
    print("=" * 80)
    print("BRD Analysis and Task Breakdown Generator")
    print("=" * 80)

    # Step 1: Extract BRD requirements
    requirements = extract_brd_requirements(BRD_PATH)

    # Step 2: Get service list
    services = get_service_list(EXCEL_PATH)

    # Step 3: Map BRD to services
    brd_mapping = map_brd_to_services(requirements, services)

    # Step 4: Generate tasks for all services
    all_tasks = []
    for service in services:
        tasks = generate_tasks_for_service(service, brd_mapping, requirements)
        all_tasks.extend(tasks)

    print(f"\nGenerated {len(all_tasks)} tasks across {len(services)} services")

    # Step 5: Create Excel sheet
    create_task_breakdown_sheet(EXCEL_PATH, all_tasks)

    print("\n" + "=" * 80)
    print("Task breakdown generation completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
