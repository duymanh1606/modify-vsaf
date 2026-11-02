"""
Check for Overlaps and Ensure Complete BRD Coverage

This script:
1. Identifies duplicate/overlapping tasks
2. Verifies all BRD requirements are covered
3. Adds missing BRD references to existing tasks
4. Adds tasks for uncovered BRD sections
5. Updates the Excel file
"""

import re
from pathlib import Path

from openpyxl import load_workbook

BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")
EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)


def extract_brd_requirements_complete(brd_path: Path) -> dict:
    """Extract all BRD requirements with complete structure."""
    with open(brd_path, encoding="utf-8") as f:
        content = f.read()

    requirements = {
        "section3": {},  # Customer features
        "section4": {},  # Admin features
    }

    # Extract Section 3
    section3_start = content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO KHÁCH HÀNG**")
    section4_start = content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN**")

    if section3_start >= 0 and section4_start >= 0:
        section3_content = content[section3_start:section4_start]

        # Find all main sections (##)
        main_sections = list(re.finditer(r"^## (.*?)(?=\n|$)", section3_content, re.MULTILINE))

        for i, match in enumerate(main_sections):
            section_title = match.group(1).strip()
            section_title = re.sub(r"\*\*", "", section_title).strip()

            start = match.end()
            if i + 1 < len(main_sections):
                next_match = main_sections[i + 1]
                section_content = section3_content[start : next_match.start()]
            else:
                section_content = section3_content[start:]

            # Extract subsections (###)
            subsections = {}
            sub_matches = list(re.finditer(r"^### (.*?)(?=\n|$)", section_content, re.MULTILINE))

            for j, sub_match in enumerate(sub_matches):
                sub_title = sub_match.group(1).strip()
                sub_title = re.sub(r"\*\*", "", sub_title).strip()

                sub_start = sub_match.end()
                if j + 1 < len(sub_matches):
                    next_sub = sub_matches[j + 1]
                    sub_content = section_content[sub_start : next_sub.start()]
                else:
                    next_main = re.search(r"\n## ", section_content[sub_start:])
                    if next_main:
                        sub_content = section_content[sub_start : sub_start + next_main.start()]
                    else:
                        sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            requirements["section3"][section_title] = {
                "subsections": subsections,
                "content": section_content.strip(),
            }

    # Extract Section 4
    if section4_start >= 0:
        section4_content = content[section4_start:]

        main_sections = list(re.finditer(r"^## (.*?)(?=\n|$)", section4_content, re.MULTILINE))

        for i, match in enumerate(main_sections):
            section_title = match.group(1).strip()
            section_title = re.sub(r"\*\*", "", section_title).strip()

            start = match.end()
            if i + 1 < len(main_sections):
                next_match = main_sections[i + 1]
                section_content = section4_content[start : next_match.start()]
            else:
                section_content = section4_content[start:]

            subsections = {}
            sub_matches = list(re.finditer(r"^### (.*?)(?=\n|$)", section_content, re.MULTILINE))

            for j, sub_match in enumerate(sub_matches):
                sub_title = sub_match.group(1).strip()
                sub_title = re.sub(r"\*\*", "", sub_title).strip()

                sub_start = sub_match.end()
                if j + 1 < len(sub_matches):
                    next_sub = sub_matches[j + 1]
                    sub_content = section_content[sub_start : next_sub.start()]
                else:
                    next_main = re.search(r"\n## ", section_content[sub_start:])
                    if next_main:
                        sub_content = section_content[sub_start : sub_start + next_main.start()]
                    else:
                        sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            requirements["section4"][section_title] = {
                "subsections": subsections,
                "content": section_content.strip(),
            }

    return requirements


def get_all_tasks_from_sheet(excel_path: Path) -> tuple[dict, list]:
    """Get all tasks and identify overlaps."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    tasks_by_service = {}
    all_tasks = []
    task_signatures = {}  # For overlap detection

    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        service_name = ws.cell(row, 2).value
        responsibility = ws.cell(row, 3).value
        task_category = ws.cell(row, 4).value
        task_id = ws.cell(row, 5).value
        task_name = ws.cell(row, 6).value
        brd_ref = ws.cell(row, 7).value
        complexity = ws.cell(row, 8).value
        base_effort = ws.cell(row, 9).value
        multiplier = ws.cell(row, 10).value
        final_days = ws.cell(row, 11).value
        final_hours = ws.cell(row, 12).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            if service_id_int not in tasks_by_service:
                tasks_by_service[service_id_int] = {
                    "name": service_name,
                    "responsibility": responsibility,
                    "tasks": [],
                }

            task_data = {
                "row": row,
                "task_id": task_id,
                "task_name": task_name,
                "category": task_category,
                "brd_ref": brd_ref,
                "complexity": complexity,
                "base_effort": base_effort,
                "multiplier": multiplier,
                "final_days": final_days,
                "final_hours": final_hours,
            }

            tasks_by_service[service_id_int]["tasks"].append(task_data)
            all_tasks.append(
                {
                    "service_id": service_id_int,
                    "service_name": service_name,
                    **task_data,
                }
            )

            # Create signature for overlap detection (normalized task name)
            task_sig = str(task_name).lower().strip()
            task_sig = re.sub(r"[^\w\s]", "", task_sig)
            task_sig = " ".join(task_sig.split())

            if task_sig not in task_signatures:
                task_signatures[task_sig] = []
            task_signatures[task_sig].append(
                {
                    "row": row,
                    "service_id": service_id_int,
                    "service_name": service_name,
                    "task_name": task_name,
                    "task_id": task_id,
                }
            )

    # Find overlaps (same task name in different services)
    overlaps = []
    for sig, occurrences in task_signatures.items():
        if len(occurrences) > 1:
            # Check if it's a legitimate overlap (same task in multiple services)
            # vs standard tasks that should appear in all services
            service_ids = [occ["service_id"] for occ in occurrences]
            if len(set(service_ids)) > 1:
                # Check if it's a standard task that should be in all services
                standard_tasks = [
                    "phân tích brd",
                    "thiết kế api",
                    "thiết kế mô hình dữ liệu",
                    "logic nghiệp vụ",
                    "kiểm thử đơn vị",
                    "kiểm thử tích hợp",
                    "tài liệu api",
                    "triển khai",
                    "tuân thủ",
                    "bảo mật",
                ]
                is_standard = any(std in sig for std in standard_tasks)

                if not is_standard:
                    overlaps.append({"signature": sig, "occurrences": occurrences})

    return tasks_by_service, overlaps, all_tasks


def map_brd_to_services_improved(requirements: dict, services: list[dict]) -> dict:
    """Improved BRD to service mapping."""

    # Enhanced mapping with more keywords
    service_keywords = {
        # Customer features
        "Tài Khoản": ["Customer Business", "User Management Service", "Authentication"],
        "Đăng Ký": ["Customer Business", "User Management Service"],
        "Đăng Nhập": ["Customer Business", "User Management Service", "Authentication"],
        "Quản Lý Thông Tin": ["Customer Business", "User Management Service"],
        "Mua Bảo Hiểm": [
            "Proposal Business",
            "Product Catalog",
            "Intelligent Recommendation",
            "Intelligent Filtering",
            "Chatbot Service",
        ],
        "Đề xuất": [
            "Intelligent Recommendation Service",
            "Intelligent Filtering Service",
        ],
        "Chatbot": ["Chatbot Service"],
        "So sánh": ["Proposal Business", "Product Catalog"],
        "Thanh Toán": ["Payment Service", "Billing Service"],
        "Gia Hạn": ["Renewal Process", "Policy Business"],
        "Tái Tục": ["Renewal Process", "Policy Business"],
        "Hủy Hợp Đồng": ["Policy Business", "Contract Orchestrator"],
        "Bồi Thường": ["Claim Business"],
        "Yêu Cầu Bồi Thường": ["Claim Business"],
        # Admin features
        "Quản Lý Tài Khoản Quản Trị Viên": ["User Management Service", "Cms Be"],
        "Quản Lý Đối Tác": ["Partner Management Service", "Cms Be"],
        "Quản Lý Sản Phẩm": ["Product Catalog", "Cms Be"],
        "Danh sách & nhóm sản phẩm": ["Product Catalog", "Cms Be"],
        "Cấu hình sản phẩm & gói": [
            "Product Catalog",
            "Cms Be",
            "Business Rules Engine",
        ],
        "Quyền lợi & phí": ["Product Catalog", "Cms Be", "Business Rules Engine"],
        "Quản Lý Khách Hàng": ["Customer Business", "Crm Service", "Cms Be"],
        "Quản Lý Hợp Đồng": ["Policy Business", "Cms Be"],
        "Quản Lý Yêu Cầu Bồi Thường": ["Claim Business", "Cms Be"],
        "Quản Lý Kênh Bán": ["Sales Channel Management Service", "Cms Be"],
        "Quản Lý Chiến Dịch": ["Promotion Business", "Cms Be"],
        "Quản Lý Nội Dung": ["Cms Be", "Document Management Service"],
        "Báo Cáo": ["Analytics Service", "Cms Be"],
        "Báo Cáo và Đối Soát": ["Analytics Service", "Reconcile Process", "Cms Be"],
        "Cảnh Báo": ["Notification Spi", "Cms Be"],
    }

    mapping = {}

    # Map Section 3
    for section_title, section_data in requirements["section3"].items():
        section_num = "3"

        # Find matching services
        matched_services = set()
        for keyword, service_patterns in service_keywords.items():
            if keyword.lower() in section_title.lower():
                for service in services:
                    service_name_lower = service["name"].lower()
                    for pattern in service_patterns:
                        pattern_lower = pattern.lower()
                        if (
                            pattern_lower in service_name_lower
                            or service_name_lower in pattern_lower
                            or any(word in service_name_lower for word in pattern_lower.split() if len(word) > 3)
                        ):
                            matched_services.add(service["id"])

        # Also check subsections
        for sub_title in section_data["subsections"]:
            for keyword, service_patterns in service_keywords.items():
                if keyword.lower() in sub_title.lower():
                    for service in services:
                        service_name_lower = service["name"].lower()
                        for pattern in service_patterns:
                            pattern_lower = pattern.lower()
                            if (
                                pattern_lower in service_name_lower
                                or service_name_lower in pattern_lower
                                or any(word in service_name_lower for word in pattern_lower.split() if len(word) > 3)
                            ):
                                matched_services.add(service["id"])

        # Add to mapping
        for service_id in matched_services:
            if service_id not in mapping:
                mapping[service_id] = {
                    "service": next(s for s in services if s["id"] == service_id),
                    "brd_sections": [],
                }

            # Check if already added
            if not any(
                s["section"] == section_num and s["subsection"] == section_title
                for s in mapping[service_id]["brd_sections"]
            ):
                mapping[service_id]["brd_sections"].append(
                    {
                        "section": section_num,
                        "subsection": section_title,
                        "type": "customer",
                        "subsections": list(section_data["subsections"].keys()),
                    }
                )

    # Map Section 4
    for section_title, section_data in requirements["section4"].items():
        section_num = "4"

        matched_services = set()
        for keyword, service_patterns in service_keywords.items():
            if keyword.lower() in section_title.lower():
                for service in services:
                    service_name_lower = service["name"].lower()
                    for pattern in service_patterns:
                        pattern_lower = pattern.lower()
                        if (
                            pattern_lower in service_name_lower
                            or service_name_lower in pattern_lower
                            or any(word in service_name_lower for word in pattern_lower.split() if len(word) > 3)
                        ):
                            matched_services.add(service["id"])

        for service_id in matched_services:
            if service_id not in mapping:
                mapping[service_id] = {
                    "service": next(s for s in services if s["id"] == service_id),
                    "brd_sections": [],
                }

            if not any(
                s["section"] == section_num and s["subsection"] == section_title
                for s in mapping[service_id]["brd_sections"]
            ):
                mapping[service_id]["brd_sections"].append(
                    {
                        "section": section_num,
                        "subsection": section_title,
                        "type": "admin",
                        "subsections": list(section_data["subsections"].keys()),
                    }
                )

    return mapping


def add_missing_brd_references(excel_path: Path, requirements: dict, mapping: dict):
    """Add missing BRD references to existing tasks."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    updated_count = 0

    # Get service to BRD mapping
    service_brd_map = {}
    for service_id, data in mapping.items():
        service_brd_map[service_id] = []
        for brd_section in data["brd_sections"]:
            ref = f"{brd_section['section']}.{brd_section['subsection'][:30]}"
            service_brd_map[service_id].append(ref)

    # Update tasks with missing BRD references
    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value
        current_brd_ref = ws.cell(row, 7).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            # Get BRD references for this service
            if service_id_int in service_brd_map:
                brd_refs = service_brd_map[service_id_int]

                # Check if task name matches BRD keywords
                task_lower = str(task_name).lower()

                # Map task to BRD section
                matched_refs = []
                for ref in brd_refs:
                    ref_lower = ref.lower()
                    # Check if task relates to this BRD section
                    if any(keyword in task_lower for keyword in ["gia hạn", "tái tục", "renewal"]):
                        if any(keyword in ref_lower for keyword in ["gia hạn", "tái tục", "renewal"]):
                            matched_refs.append(ref)
                    elif any(keyword in task_lower for keyword in ["bồi thường", "claim"]):
                        if any(keyword in ref_lower for keyword in ["bồi thường", "claim"]):
                            matched_refs.append(ref)
                    elif any(keyword in task_lower for keyword in ["mua", "purchase", "proposal"]):
                        if any(keyword in ref_lower for keyword in ["mua", "purchase"]):
                            matched_refs.append(ref)
                    elif any(keyword in task_lower for keyword in ["tài khoản", "account", "đăng"]):
                        if any(keyword in ref_lower for keyword in ["tài khoản", "account"]):
                            matched_refs.append(ref)

                # Update BRD reference if missing or incomplete
                if matched_refs:
                    new_ref = ", ".join(matched_refs[:3])  # Limit to 3 references
                    if not current_brd_ref or str(current_brd_ref) == "N/A" or len(str(current_brd_ref)) < 5:
                        ws.cell(row, 7, new_ref)
                        updated_count += 1
                    elif not any(ref in str(current_brd_ref) for ref in matched_refs):
                        # Append new references
                        existing_refs = str(current_brd_ref).split(", ")
                        combined = list(set(existing_refs + matched_refs[:2]))
                        ws.cell(row, 7, ", ".join(combined[:3]))
                        updated_count += 1

    wb.save(excel_path)
    print(f"Updated {updated_count} tasks with BRD references")


def add_missing_tasks_for_uncovered_brd(excel_path: Path, requirements: dict, mapping: dict):
    """Add tasks for uncovered BRD sections."""
    wb = load_workbook(excel_path, data_only=False)
    wb["VDS_Task_Breakdown_Detailed"]

    # Find uncovered sections
    uncovered_sections = []

    # Check Section 3
    for section_title, section_data in requirements["section3"].items():
        covered = False
        for _service_id, data in mapping.items():
            for brd_section in data["brd_sections"]:
                if brd_section["subsection"] == section_title:
                    covered = True
                    break
            if covered:
                break

        if not covered:
            uncovered_sections.append(
                {
                    "section": "3",
                    "title": section_title,
                    "type": "customer",
                    "subsections": list(section_data["subsections"].keys()),
                }
            )

    # Check Section 4
    for section_title, section_data in requirements["section4"].items():
        covered = False
        for _service_id, data in mapping.items():
            for brd_section in data["brd_sections"]:
                if brd_section["subsection"] == section_title:
                    covered = True
                    break
            if covered:
                break

        if not covered:
            uncovered_sections.append(
                {
                    "section": "4",
                    "title": section_title,
                    "type": "admin",
                    "subsections": list(section_data["subsections"].keys()),
                }
            )

    print(f"\nUncovered BRD sections: {len(uncovered_sections)}")
    for section in uncovered_sections:
        print(f"  - {section['section']}. {section['title']} ({section['type']})")

    # Add tasks for uncovered sections (this would require identifying the right services)
    # For now, we'll just report them

    return uncovered_sections


def main():
    """Main execution."""
    print("=" * 80)
    print("Check Overlaps and Ensure Complete BRD Coverage")
    print("=" * 80)

    # Step 1: Extract BRD requirements
    print("\nStep 1: Extracting BRD requirements...")
    requirements = extract_brd_requirements_complete(BRD_PATH)
    print(f"  Section 3: {len(requirements['section3'])} sections")
    print(f"  Section 4: {len(requirements['section4'])} sections")

    # Step 2: Get all services
    print("\nStep 2: Reading services...")
    wb = load_workbook(EXCEL_PATH, data_only=True)
    ws_services = wb["VDS_Est_Detail_Services_Total"]
    services = []
    for row in range(2, 60):
        service_id = ws_services.cell(row, 1).value
        service_name = ws_services.cell(row, 2).value
        responsibility = ws_services.cell(row, 6).value
        if service_id and isinstance(service_id, (int, float)) and service_name:
            services.append(
                {
                    "id": int(service_id),
                    "name": str(service_name).split(":")[0].strip(),
                    "responsibility": responsibility or "Unknown",
                }
            )
    print(f"  Found {len(services)} services")

    # Step 3: Check for overlaps
    print("\nStep 3: Checking for overlaps...")
    tasks_by_service, overlaps, all_tasks = get_all_tasks_from_sheet(EXCEL_PATH)
    print(f"  Total tasks: {len(all_tasks)}")
    print(f"  Potential overlaps: {len(overlaps)}")

    if overlaps:
        print("\n  Overlaps found:")
        for i, overlap in enumerate(overlaps[:10], 1):  # Show first 10
            print(f"    {i}. '{overlap['signature'][:60]}...'")
            for occ in overlap["occurrences"]:
                print(f"       - Service {occ['service_id']}: {occ['service_name']} (Row {occ['row']})")

    # Step 4: Map BRD to services
    print("\nStep 4: Mapping BRD to services...")
    mapping = map_brd_to_services_improved(requirements, services)
    print(f"  Services with BRD mapping: {len(mapping)}")

    # Step 5: Add missing BRD references
    print("\nStep 5: Adding missing BRD references...")
    add_missing_brd_references(EXCEL_PATH, requirements, mapping)

    # Step 6: Identify uncovered sections
    print("\nStep 6: Identifying uncovered BRD sections...")
    uncovered = add_missing_tasks_for_uncovered_brd(EXCEL_PATH, requirements, mapping)

    print("\n" + "=" * 80)
    print("Analysis completed!")
    print("=" * 80)
    print("\nSummary:")
    print(f"  - Total tasks: {len(all_tasks)}")
    print(f"  - Overlaps found: {len(overlaps)}")
    print(f"  - Uncovered BRD sections: {len(uncovered)}")
    print(f"  - Services with BRD mapping: {len(mapping)}")


if __name__ == "__main__":
    main()
