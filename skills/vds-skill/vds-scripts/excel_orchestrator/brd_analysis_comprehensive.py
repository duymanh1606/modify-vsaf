"""
Comprehensive BRD Analysis and Task Breakdown Generator

This script performs comprehensive analysis:
1. Extracts all BRD requirements systematically
2. Maps BRD requirements to all 47 services accurately
3. Generates detailed task breakdowns with BRD references
4. Creates new Excel sheet: VDS_Task_Breakdown_Detailed
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


def get_all_services(excel_path: Path) -> list[dict]:
    """Get complete list of all 47 services from Excel."""
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["VDS_Est_Detail_Services_Total"]

    services = []
    for row in range(2, 60):
        service_id = ws.cell(row, 1).value
        service_name = ws.cell(row, 2).value
        responsibility = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and service_name:
            # Clean service name (remove Vietnamese description if present)
            name_clean = str(service_name).split(":")[0].strip()

            services.append(
                {
                    "id": int(service_id),
                    "name": name_clean,
                    "full_name": str(service_name).strip(),
                    "responsibility": responsibility or "Unknown",
                }
            )

    return services


def extract_brd_sections(brd_path: Path) -> dict:
    """Extract BRD sections with their content."""
    with open(brd_path, encoding="utf-8") as f:
        content = f.read()

    brd_data = {
        "section3": {},  # Customer features
        "section4": {},  # Admin features
    }

    # Extract Section 3 - Customer features
    # Find the start and end positions
    section3_start_match = re.search(r"# \*\*MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO KHÁCH HÀNG\*\*", content)
    section4_start_match = re.search(r"# \*\*MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN\*\*", content)

    if section3_start_match and section4_start_match:
        section3_start_pos = section3_start_match.end()
        section4_start_pos = section4_start_match.start()
        section3_content = content[section3_start_pos:section4_start_pos]

        # Extract all main sections (## headings) - these are the main feature groups
        # Only match ## (not ###) for main sections
        section_matches = list(re.finditer(r"^## (?!##)(.*?)(?=\n|$)", section3_content, re.MULTILINE))

        # Filter out matches that are actually ### (three hashes)
        main_sections = []
        for match in section_matches:
            # Check if the line actually starts with ## (not ###)
            match_start = match.start()
            # Find the start of the line
            line_start = section3_content.rfind("\n", 0, match_start) + 1
            line_prefix = section3_content[line_start:match_start]
            # Count # characters before the match
            hash_count = line_prefix.count("#")
            if hash_count == 0:  # Line starts with ##
                main_sections.append(match)

        for i, match in enumerate(main_sections):
            section_line = match.group(1).strip()
            # Remove markdown formatting
            section_title = re.sub(r"\*\*", "", section_line).strip()

            # Skip if it's not a real section
            if not section_title or len(section_title) < 3:
                continue

            start = match.end()

            # Get content until next ## heading (main section) or end of section 3
            if i + 1 < len(main_sections):
                next_match = main_sections[i + 1]
                section_content = section3_content[start : next_match.start()]
            else:
                section_content = section3_content[start:]

            # Extract subsections (### headings) within this main section
            subsections = {}
            # Only find ### that are within this section's content
            sub_matches = list(re.finditer(r"^### (.*?)(?=\n|$)", section_content, re.MULTILINE))

            for j, sub_match in enumerate(sub_matches):
                sub_line = sub_match.group(1).strip()
                sub_title = re.sub(r"\*\*", "", sub_line).strip()

                if not sub_title or len(sub_title) < 3:
                    continue

                sub_start = sub_match.end()

                # Get content until next ### or ## (next main section)
                if j + 1 < len(sub_matches):
                    next_sub = sub_matches[j + 1]
                    sub_content = section_content[sub_start : next_sub.start()]
                else:
                    # Check if there's a ## after this subsection
                    next_main = re.search(r"\n## ", section_content[sub_start:])
                    if next_main:
                        sub_content = section_content[sub_start : sub_start + next_main.start()]
                    else:
                        sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            brd_data["section3"][section_title] = {
                "content": section_content.strip(),
                "subsections": subsections,
            }

    # Extract Section 4 - Admin features
    # Pattern: # **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN**
    section4_match = re.search(
        r"# \*\*MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN\*\*(.*?)$",
        content,
        re.DOTALL,
    )

    if section4_match:
        section4_content = section4_match.group(1)

        # Extract main sections (## headings)
        sections = re.finditer(r"## \*\*(.*?)\*\*", section4_content)
        for match in sections:
            section_title = match.group(1).strip()
            start = match.end()

            # Get content until next ## or end
            next_section = re.search(r"\n## \*\*", section4_content[start:])
            if next_section:
                section_content = section4_content[start : start + next_section.start()]
            else:
                section_content = section4_content[start:]

            # Extract subsections (### headings)
            subsections = {}
            sub_matches = re.finditer(r"### (.*?)(?=\n|$)", section_content, re.MULTILINE)
            for sub_match in sub_matches:
                sub_title = sub_match.group(1).strip()
                sub_title = re.sub(r"\*\*", "", sub_title).strip()
                sub_start = sub_match.end()

                next_sub = re.search(r"\n### |\n## \*\*", section_content[sub_start:])
                if next_sub:
                    sub_content = section_content[sub_start : sub_start + next_sub.start()]
                else:
                    sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            brd_data["section4"][section_title] = {
                "content": section_content.strip(),
                "subsections": subsections,
            }

    return brd_data


def map_brd_to_services(services: list[dict], brd_data: dict) -> dict:
    """Map BRD sections to services based on service names and functionality."""

    # Service name patterns for matching - map BRD sections to service name patterns
    service_mappings = {
        # Section 3 - Customer Features
        "Tài Khoản": ["Customer Business", "User Management Service"],
        "Quản Lý Thông Tin": ["Customer Business"],
        "Mua Bảo Hiểm": [
            "Proposal Business",
            "Intelligent Recommendation Service",
            "Intelligent Filtering Service",
            "Chatbot Service",
            "Product Catalog",
            "Billing Service",
            "Payment Service",
            "OCR Service",
            "Promotion Business",
        ],
        "Quản lý hợp đồng bảo hiểm": [
            "Policy Business",
            "Renewal Process",
            "Contract Orchestrator",
        ],
        "Gia Hạn": ["Renewal Process", "Policy Business"],
        "Tái Tục": ["Renewal Process", "Policy Business"],
        "Yêu Cầu Bồi Thường": ["Claim Business"],
        # Section 4 - Admin Features
        "Quản Lý Tài Khoản Quản Trị Viên": ["User Management Service", "Cms Be"],
        "Quản Lý Đối Tác": ["Partner Management Service", "Cms Be"],
        "Quản Lý Sản Phẩm": ["Product Catalog", "Cms Be"],
        "Quản Lý Khách Hàng": ["Customer Business", "Crm Service", "Cms Be"],
        "Quản Lý Hợp Đồng": ["Policy Business", "Cms Be"],
        "Quản Lý Yêu Cầu Bồi Thường": ["Claim Business", "Cms Be"],
        "Quản Lý Kênh Bán": ["Sales Channel Management Service", "Cms Be"],
        "Quản Lý Chiến Dịch": ["Promotion Business", "Cms Be"],
        "Quản Lý Nội Dung": ["Cms Be", "Document Management Service"],
        "Báo Cáo": ["Analytics Service", "Cms Be"],
        "Cảnh Báo": ["Notification Spi", "Cms Be"],
    }

    # Create service lookup by name
    service_lookup = {}
    for service in services:
        # Try multiple name variations
        name_variations = [
            service["name"],
            service["name"].lower(),
            service["name"].replace(" ", "").lower(),
        ]
        for name_var in name_variations:
            service_lookup[name_var] = service

    # Build mapping
    mapping = {}

    # Map Section 3 - check both exact match and partial match
    for brd_section_title in brd_data["section3"]:
        # Try to find matching mapping
        matched_patterns = []
        for pattern, service_names in service_mappings.items():
            if pattern.lower() in brd_section_title.lower() or brd_section_title.lower() in pattern.lower():
                matched_patterns.extend(service_names)

        # Also check for specific keywords
        if "Tài Khoản" in brd_section_title or "Đăng" in brd_section_title:
            matched_patterns.extend(["Customer Business", "User Management Service"])
        if "Mua" in brd_section_title or "Bảo Hiểm" in brd_section_title:
            matched_patterns.extend(
                [
                    "Proposal Business",
                    "Product Catalog",
                    "Intelligent Recommendation Service",
                ]
            )
        if "Gia Hạn" in brd_section_title or "Tái Tục" in brd_section_title:
            matched_patterns.extend(["Renewal Process", "Policy Business"])
        if "Bồi Thường" in brd_section_title:
            matched_patterns.extend(["Claim Business"])

        # Remove duplicates
        matched_patterns = list(set(matched_patterns))

        for service_name_pattern in matched_patterns:
            for service in services:
                service_name_lower = service["name"].lower()
                pattern_lower = service_name_pattern.lower()

                # More flexible matching
                if (
                    pattern_lower in service_name_lower
                    or service_name_lower in pattern_lower
                    or any(word in service_name_lower for word in pattern_lower.split() if len(word) > 3)
                ):
                    service_id = service["id"]
                    if service_id not in mapping:
                        mapping[service_id] = {"service": service, "brd_sections": []}
                    # Avoid duplicates
                    if not any(s["subsection"] == brd_section_title for s in mapping[service_id]["brd_sections"]):
                        mapping[service_id]["brd_sections"].append(
                            {
                                "section": "3",
                                "subsection": brd_section_title,
                                "type": "customer",
                            }
                        )

    # Map Section 4
    for brd_section_title in brd_data["section4"]:
        matched_patterns = []
        for pattern, service_names in service_mappings.items():
            if pattern.lower() in brd_section_title.lower() or brd_section_title.lower() in pattern.lower():
                matched_patterns.extend(service_names)

        # Keyword matching for Section 4
        if "Tài Khoản" in brd_section_title:
            matched_patterns.extend(["User Management Service", "Cms Be"])
        if "Đối Tác" in brd_section_title:
            matched_patterns.extend(["Partner Management Service", "Cms Be"])
        if "Sản Phẩm" in brd_section_title:
            matched_patterns.extend(["Product Catalog", "Cms Be"])
        if "Khách Hàng" in brd_section_title:
            matched_patterns.extend(["Customer Business", "Crm Service", "Cms Be"])
        if "Hợp Đồng" in brd_section_title:
            matched_patterns.extend(["Policy Business", "Cms Be"])
        if "Bồi Thường" in brd_section_title:
            matched_patterns.extend(["Claim Business", "Cms Be"])
        if "Kênh Bán" in brd_section_title:
            matched_patterns.extend(["Sales Channel Management Service", "Cms Be"])
        if "Chiến Dịch" in brd_section_title:
            matched_patterns.extend(["Promotion Business", "Cms Be"])
        if "Nội Dung" in brd_section_title:
            matched_patterns.extend(["Cms Be", "Document Management Service"])
        if "Báo Cáo" in brd_section_title:
            matched_patterns.extend(["Analytics Service", "Cms Be"])
        if "Cảnh Báo" in brd_section_title:
            matched_patterns.extend(["Notification Spi", "Cms Be"])

        matched_patterns = list(set(matched_patterns))

        for service_name_pattern in matched_patterns:
            for service in services:
                service_name_lower = service["name"].lower()
                pattern_lower = service_name_pattern.lower()

                if (
                    pattern_lower in service_name_lower
                    or service_name_lower in pattern_lower
                    or any(word in service_name_lower for word in pattern_lower.split() if len(word) > 3)
                ):
                    service_id = service["id"]
                    if service_id not in mapping:
                        mapping[service_id] = {"service": service, "brd_sections": []}
                    if not any(s["subsection"] == brd_section_title for s in mapping[service_id]["brd_sections"]):
                        mapping[service_id]["brd_sections"].append(
                            {
                                "section": "4",
                                "subsection": brd_section_title,
                                "type": "admin",
                            }
                        )

    return mapping


def determine_multipliers(service_name: str) -> list[str]:
    """Determine which multipliers apply to a service."""
    multipliers = ["base"]  # Always apply base buffer

    service_lower = service_name.lower()

    # AI/Intelligent services
    if any(x in service_lower for x in ["intelligent", "chatbot", "recommendation", "filtering", "targeted"]):
        multipliers.append("ai")

    # Workflow services
    if any(
        x in service_lower
        for x in [
            "process",
            "orchestrator",
            "workflow",
            "renewal",
            "reconcile",
            "timeout",
        ]
    ):
        multipliers.append("workflow")

    # Complex logic services
    if any(x in service_lower for x in ["rules engine", "fraud", "analytics", "rating", "underwriting"]):
        multipliers.append("logic")

    # Multi-insurer
    if "insurer" in service_lower:
        multipliers.append("multi_insurer")

    # Specific complexity multipliers
    if "renewal" in service_lower:
        multipliers.append("renewal_complexity")

    if "claim" in service_lower:
        multipliers.append("claims_complexity")

    if any(x in service_lower for x in ["billing", "payment"]):
        multipliers.append("payment_complexity")

    if "intelligent filtering" in service_lower:
        multipliers.append("dynamic_pricing")

    if "proposal" in service_lower:
        multipliers.append("product_comparison")

    # Cross-cutting (apply to all)
    multipliers.append("compliance")
    multipliers.append("performance")

    return multipliers


def generate_standard_tasks(service: dict, brd_sections: list[dict], multipliers: list[str]) -> list[dict]:
    """Generate standard task template for a service."""
    tasks = []
    task_counter = 1
    service_id = service["id"]
    service_name = service["name"]

    # Base tasks for all services
    base_tasks = [
        {
            "category": "Requirements & Analysis",
            "name": "BRD Analysis and Requirements Extraction",
            "complexity": "Medium",
            "base_effort": 3,
            "brd_ref": "",
        },
        {
            "category": "Design & Architecture",
            "name": "API Design: REST endpoints design",
            "complexity": "Medium",
            "base_effort": 4,
            "brd_ref": "",
        },
        {
            "category": "Design & Architecture",
            "name": "Data Model Design: Entity and relationship design",
            "complexity": "Medium",
            "base_effort": 3,
            "brd_ref": "",
        },
        {
            "category": "Development",
            "name": "Business Logic - Core: Core business logic implementation",
            "complexity": "Complex",
            "base_effort": 15,
            "brd_ref": "",
        },
        {
            "category": "Development",
            "name": "Business Logic - Integration: Integration logic implementation",
            "complexity": "Complex",
            "base_effort": 8,
            "brd_ref": "",
        },
        {
            "category": "Development",
            "name": "Data Access Layer: Repository and JPA implementation",
            "complexity": "Medium",
            "base_effort": 5,
            "brd_ref": "",
        },
        {
            "category": "Integration",
            "name": "External Integration: Integration with external systems",
            "complexity": "Complex",
            "base_effort": 8,
            "brd_ref": "",
        },
        {
            "category": "Testing",
            "name": "Unit Testing: Unit tests for business logic",
            "complexity": "Medium",
            "base_effort": 5,
            "brd_ref": "",
        },
        {
            "category": "Testing",
            "name": "Integration Testing: Integration tests with other services",
            "complexity": "Complex",
            "base_effort": 6,
            "brd_ref": "",
        },
        {
            "category": "Documentation",
            "name": "API Documentation: OpenAPI/Swagger documentation",
            "complexity": "Simple",
            "base_effort": 2,
            "brd_ref": "",
        },
        {
            "category": "Deployment",
            "name": "Deployment: CI/CD pipeline and deployment scripts",
            "complexity": "Medium",
            "base_effort": 3,
            "brd_ref": "",
        },
        {
            "category": "Compliance & Regulatory",
            "name": "Compliance: Audit trail and regulatory compliance",
            "complexity": "Medium",
            "base_effort": 3,
            "brd_ref": "",
        },
        {
            "category": "Security",
            "name": "Security: Authentication, authorization, and data encryption",
            "complexity": "Medium",
            "base_effort": 4,
            "brd_ref": "",
        },
    ]

    # Add BRD-specific tasks based on mapped sections
    brd_specific_tasks = []

    for brd_section in brd_sections:
        section_num = brd_section["section"]
        subsection = brd_section["subsection"]

        # Generate BRD reference
        f"{section_num}.{subsection[:20]}"

        if "Mua Bảo Hiểm" in subsection or "Purchase" in subsection:
            brd_specific_tasks.extend(
                [
                    {
                        "category": "Development",
                        "name": "Purchase Flow: Guest checkout and account creation during purchase",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.3.5",
                    },
                    {
                        "category": "Development",
                        "name": "Product Comparison: Real-time pricing and benefit comparison",
                        "complexity": "Complex",
                        "base_effort": 6,
                        "brd_ref": "3.3.4",
                    },
                    {
                        "category": "Integration",
                        "name": "OCR Integration: Document reading and data extraction",
                        "complexity": "Medium",
                        "base_effort": 5,
                        "brd_ref": "3.3.5",
                    },
                    {
                        "category": "Development",
                        "name": "Voucher/Promotion Engine: Auto-apply best voucher",
                        "complexity": "Medium",
                        "base_effort": 4,
                        "brd_ref": "3.3.8",
                    },
                ]
            )

        if "Gia Hạn" in subsection or "Tái Tục" in subsection or "Renewal" in subsection:
            brd_specific_tasks.extend(
                [
                    {
                        "category": "Design & Architecture",
                        "name": "Renewal Workflow Design: Design 4 different renewal types",
                        "complexity": "Very Complex",
                        "base_effort": 8,
                        "brd_ref": "3.4.3",
                    },
                    {
                        "category": "Development",
                        "name": "Renewal Workflow Implementation: Implement 4 renewal workflow types",
                        "complexity": "Very Complex",
                        "base_effort": 15,
                        "brd_ref": "3.4.3",
                    },
                    {
                        "category": "Development",
                        "name": "Auto-Renewal Logic: Different rules per renewal type",
                        "complexity": "Complex",
                        "base_effort": 10,
                        "brd_ref": "3.4.3",
                    },
                    {
                        "category": "Integration",
                        "name": "Renewal Notification: SMS and email notification integration",
                        "complexity": "Medium",
                        "base_effort": 4,
                        "brd_ref": "3.4.2",
                    },
                ]
            )

        if "Bồi Thường" in subsection or "Claim" in subsection:
            brd_specific_tasks.extend(
                [
                    {
                        "category": "Design & Architecture",
                        "name": "Claims State Machine Design: Design 8+ state transitions",
                        "complexity": "Very Complex",
                        "base_effort": 10,
                        "brd_ref": "3.5",
                    },
                    {
                        "category": "Development",
                        "name": "Claims State Machine Implementation: Implement 8+ state transitions",
                        "complexity": "Very Complex",
                        "base_effort": 18,
                        "brd_ref": "3.5",
                    },
                    {
                        "category": "Development",
                        "name": "Claim Submission Workflow: Document upload and validation",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.5",
                    },
                    {
                        "category": "Development",
                        "name": "Customer Actions: Reject/accept with OTP/signature",
                        "complexity": "Medium",
                        "base_effort": 5,
                        "brd_ref": "3.5",
                    },
                    {
                        "category": "Integration",
                        "name": "Insurer Claim API Integration: Claim processing integration",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.5",
                    },
                    {
                        "category": "Integration",
                        "name": "Payment Integration: Core Payment integration for claim payment",
                        "complexity": "Medium",
                        "base_effort": 5,
                        "brd_ref": "3.5",
                    },
                ]
            )

        if "Đề xuất" in subsection or "Recommendation" in subsection:
            brd_specific_tasks.extend(
                [
                    {
                        "category": "Development",
                        "name": "ML Model Research: Research and select recommendation models",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.3.1",
                    },
                    {
                        "category": "Development",
                        "name": "Recommendation Engine: Implement ML-based recommendation",
                        "complexity": "Very Complex",
                        "base_effort": 12,
                        "brd_ref": "3.3.1",
                    },
                    {
                        "category": "Integration",
                        "name": "BI System Integration: Integration for customer data",
                        "complexity": "Medium",
                        "base_effort": 5,
                        "brd_ref": "3.3.1",
                    },
                ]
            )

        if "Tùy chỉnh" in subsection or "Personalization" in subsection or "Filtering" in subsection:
            brd_specific_tasks.extend(
                [
                    {
                        "category": "Development",
                        "name": "Customer Profiling Engine: ML-based customer profiling",
                        "complexity": "Very Complex",
                        "base_effort": 10,
                        "brd_ref": "3.3.3",
                    },
                    {
                        "category": "Development",
                        "name": "Dynamic Pricing Engine: Real-time pricing calculation",
                        "complexity": "Very Complex",
                        "base_effort": 12,
                        "brd_ref": "3.3.3",
                    },
                    {
                        "category": "Development",
                        "name": "Risk Assessment Algorithms: Risk coefficient calculation",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.3.3",
                    },
                    {
                        "category": "Integration",
                        "name": "BI System Integration: Customer data integration",
                        "complexity": "Medium",
                        "base_effort": 5,
                        "brd_ref": "3.3.3",
                    },
                    {
                        "category": "Development",
                        "name": "Pricing Formula Configuration: CMS-configurable pricing",
                        "complexity": "Medium",
                        "base_effort": 4,
                        "brd_ref": "3.3.3",
                    },
                ]
            )

        if "Chatbot" in subsection:
            brd_specific_tasks.extend(
                [
                    {
                        "category": "Development",
                        "name": "NLP Integration: Natural language processing integration",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.3.2",
                    },
                    {
                        "category": "Development",
                        "name": "Conversation Flow: Design and implement conversation flows",
                        "complexity": "Complex",
                        "base_effort": 10,
                        "brd_ref": "3.3.2",
                    },
                    {
                        "category": "Development",
                        "name": "Knowledge Base: Build and maintain knowledge base",
                        "complexity": "Medium",
                        "base_effort": 6,
                        "brd_ref": "3.3.2",
                    },
                    {
                        "category": "Development",
                        "name": "Fallback Handling: Handle unknown queries gracefully",
                        "complexity": "Medium",
                        "base_effort": 4,
                        "brd_ref": "3.3.2",
                    },
                ]
            )

        if "Thanh Toán" in subsection or "Payment" in subsection:
            brd_specific_tasks.extend(
                [
                    {
                        "category": "Integration",
                        "name": "Payment Gateway Integration: Multiple payment providers",
                        "complexity": "Complex",
                        "base_effort": 10,
                        "brd_ref": "3.3.9",
                    },
                    {
                        "category": "Development",
                        "name": "Auto-Payment Engine: Multi-source, priority-based auto-payment",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.3.9",
                    },
                    {
                        "category": "Development",
                        "name": "Partial Payment Processing: Support partial payments",
                        "complexity": "Medium",
                        "base_effort": 5,
                        "brd_ref": "3.3.9",
                    },
                    {
                        "category": "Development",
                        "name": "Refund Processing Workflow: Multiple cancellation types",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.3.9",
                    },
                    {
                        "category": "Development",
                        "name": "Payment Reconciliation: Automated and manual reconciliation",
                        "complexity": "Complex",
                        "base_effort": 8,
                        "brd_ref": "3.3.9",
                    },
                ]
            )

    # Combine base tasks and BRD-specific tasks
    all_task_templates = base_tasks + brd_specific_tasks

    # Update BRD references for base tasks if we have BRD sections
    if brd_sections:
        brd_refs = [f"{s['section']}.{s['subsection'][:15]}" for s in brd_sections[:2]]
        for task in base_tasks:
            if not task["brd_ref"]:
                task["brd_ref"] = ", ".join(brd_refs) if brd_refs else "N/A"

    # Generate tasks with multipliers applied
    for task_template in all_task_templates:
        base_effort = task_template["base_effort"]

        # Calculate final multiplier
        final_multiplier = 1.0
        multiplier_str_parts = []

        for mult_name in multipliers:
            if mult_name in MULTIPLIERS:
                mult_value = MULTIPLIERS[mult_name]
                final_multiplier *= mult_value
                if mult_name != "base":  # Don't show base in multiplier string
                    multiplier_str_parts.append(f"{mult_value:.2f}x")

        multiplier_str = "1.59x" + (" × " + " × ".join(multiplier_str_parts) if multiplier_str_parts else "")

        final_effort_days = round(base_effort * final_multiplier, 2)
        final_effort_hours = round(final_effort_days * 8, 2)

        tasks.append(
            {
                "service_id": service_id,
                "service_name": service_name,
                "task_id": f"S{service_id}-T{task_counter:03d}",
                "task_category": task_template["category"],
                "task_name": task_template["name"],
                "brd_reference": task_template["brd_ref"] or "N/A",
                "complexity_level": task_template["complexity"],
                "base_effort_days": base_effort,
                "multiplier_applied": multiplier_str,
                "final_effort_days": final_effort_days,
                "final_effort_hours": final_effort_hours,
                "dependencies": "",
                "notes": (
                    f"BRD: {', '.join([s['subsection'][:30] for s in brd_sections[:2]])}" if brd_sections else ""
                ),
            }
        )

        task_counter += 1

    return tasks


def create_detailed_breakdown_sheet(excel_path: Path, all_tasks: list[dict]):
    """Create the VDS_Task_Breakdown_Detailed sheet."""
    print(f"Creating detailed breakdown sheet with {len(all_tasks)} tasks...")

    wb = load_workbook(excel_path)

    # Remove existing sheet if present
    if "VDS_Task_Breakdown_Detailed" in wb.sheetnames:
        wb.remove(wb["VDS_Task_Breakdown_Detailed"])

    ws = wb.create_sheet("VDS_Task_Breakdown_Detailed", 0)

    # Headers
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

    # Style definitions
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Write headers
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
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

        # Alignment
        ws.cell(row=row_idx, column=1).alignment = center_align
        ws.cell(row=row_idx, column=4).alignment = center_align
        ws.cell(row=row_idx, column=7).alignment = center_align
        ws.cell(row=row_idx, column=8).alignment = center_align
        ws.cell(row=row_idx, column=10).alignment = center_align
        ws.cell(row=row_idx, column=11).alignment = center_align

    # Column widths
    column_widths = {
        "A": 12,
        "B": 40,
        "C": 25,
        "D": 12,
        "E": 60,
        "F": 25,
        "G": 18,
        "H": 18,
        "I": 35,
        "J": 18,
        "K": 18,
        "L": 30,
        "M": 60,
    }

    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    # Freeze first row
    ws.freeze_panes = "A2"

    # Add summary
    summary_start = len(all_tasks) + 3
    ws.cell(row=summary_start, column=1, value="SUMMARY").font = Font(bold=True, size=14)

    summary_data = [
        ("Total Tasks:", f"=COUNTA(E2:E{len(all_tasks) + 1})"),
        ("Total Base Effort (Days):", f"=SUM(H2:H{len(all_tasks) + 1})"),
        ("Total Final Effort (Days):", f"=SUM(J2:J{len(all_tasks) + 1})"),
        ("Total Final Effort (Hours):", f"=SUM(K2:K{len(all_tasks) + 1})"),
        ("", ""),
        (
            "Services Covered:",
            f"=SUMPRODUCT(1/COUNTIF(A2:A{len(all_tasks) + 1},A2:A{len(all_tasks) + 1}))",
        ),
    ]

    for idx, (label, formula) in enumerate(summary_data, summary_start + 1):
        ws.cell(row=idx, column=1, value=label).font = Font(bold=True)
        if formula:
            ws.cell(row=idx, column=2, value=formula)
            ws.cell(row=idx, column=2).number_format = "0.00"

    wb.save(excel_path)
    print("Created VDS_Task_Breakdown_Detailed sheet")


def main():
    """Main execution."""
    print("=" * 80)
    print("BRD Analysis and Comprehensive Task Breakdown Generator")
    print("=" * 80)

    # Step 1: Get all services
    print("\nStep 1: Reading services from Excel...")
    services = get_all_services(EXCEL_PATH)
    print(f"Found {len(services)} services")

    # Step 2: Extract BRD requirements
    print("\nStep 2: Extracting BRD requirements...")
    brd_data = extract_brd_sections(BRD_PATH)
    print(f"Section 3: {len(brd_data['section3'])} sections")
    print(f"Section 4: {len(brd_data['section4'])} sections")

    # Step 3: Map BRD to services
    print("\nStep 3: Mapping BRD requirements to services...")
    brd_mapping = map_brd_to_services(services, brd_data)
    print(f"Mapped {len(brd_mapping)} services to BRD requirements")

    # Step 4: Generate tasks for all services
    print("\nStep 4: Generating tasks for all services...")
    all_tasks = []

    for service in services:
        service_id = service["id"]
        brd_sections = brd_mapping.get(service_id, {}).get("brd_sections", [])
        multipliers = determine_multipliers(service["name"])

        tasks = generate_standard_tasks(service, brd_sections, multipliers)
        all_tasks.extend(tasks)

        if service_id <= 5:  # Show first 5 for debugging
            print(f"  Service {service_id}: {len(tasks)} tasks, multipliers: {', '.join(multipliers)}")

    print(f"\nGenerated {len(all_tasks)} total tasks")

    # Step 5: Create Excel sheet
    print("\nStep 5: Creating detailed breakdown sheet...")
    create_detailed_breakdown_sheet(EXCEL_PATH, all_tasks)

    print("\n" + "=" * 80)
    print("Task breakdown generation completed successfully!")
    print("=" * 80)
    print("\nSummary:")
    print(f"  - Services processed: {len(services)}")
    print(f"  - Total tasks generated: {len(all_tasks)}")
    print("  - New sheet created: VDS_Task_Breakdown_Detailed")


if __name__ == "__main__":
    main()
