"""
Comprehensive BRD Coverage Check and Duplicate/Overlap Detection

This script:
1. Checks for duplicate tasks (same task in same service)
2. Checks for overlapping tasks (same task in different services where it shouldn't be)
3. Analyzes BRD coverage
4. Identifies missing BRD sections
5. Adds tasks for uncovered sections
6. Improves BRD references
"""

import re
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)
BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")


def check_duplicates(excel_path: Path) -> list[dict]:
    """Check for duplicate tasks (same task name in same service)."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    duplicates = []
    task_map = {}  # {(service_id, task_name_normalized): [rows]}

    for row in range(9, ws.max_row + 1):  # Start from row 9 (after summary)
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and task_name:
            service_id_int = int(service_id)
            # Normalize task name
            task_normalized = str(task_name).lower().strip()
            task_normalized = re.sub(r"[^\w\s]", "", task_normalized)
            task_normalized = " ".join(task_normalized.split())

            key = (service_id_int, task_normalized)
            if key not in task_map:
                task_map[key] = []
            task_map[key].append(row)

    # Find duplicates
    for key, rows in task_map.items():
        if len(rows) > 1:
            service_id, task_name = key
            duplicates.append(
                {
                    "service_id": service_id,
                    "task_name": task_name,
                    "rows": rows,
                    "count": len(rows),
                }
            )

    return duplicates


def check_overlaps(excel_path: Path) -> list[dict]:
    """Check for overlapping tasks (BRD-specific tasks in wrong services)."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # BRD-specific tasks that should only be in specific services
    brd_specific_rules = {
        # Renewal tasks
        "thiết kế workflow gia hạn": ["Renewal Process", "Policy Business"],
        "triển khai workflow gia hạn": ["Renewal Process", "Policy Business"],
        "logic tự động gia hạn": ["Renewal Process", "Policy Business"],
        "thông báo gia hạn": ["Renewal Process", "Policy Business", "Notification Spi"],
        # Claims tasks
        "thiết kế state machine bồi thường": ["Claim Business"],
        "triển khai state machine bồi thường": ["Claim Business"],
        "workflow gửi yêu cầu bồi thường": ["Claim Business"],
        "hành động khách hàng": ["Claim Business"],
        "tích hợp api bồi thường nhà bảo hiểm": ["Claim Business", "Insurer Service"],
        "tích hợp thanh toán cho bồi thường": ["Claim Business", "Payment Service"],
        # Purchase/Proposal tasks
        "luồng mua hàng": ["Proposal Business", "Customer Business"],
        "so sánh sản phẩm": ["Proposal Business", "Product Catalog"],
        "tích hợp ocr": ["Proposal Business", "Ocr Service"],
        "engine voucher": ["Proposal Business", "Promotion Business"],
        # AI/Intelligent tasks
        "nghiên cứu ml model": [
            "Intelligent Recommendation Service",
            "Intelligent Filtering Service",
            "Targeted Customer Service",
        ],
        "engine gợi ý": ["Intelligent Recommendation Service"],
        "tích hợp hệ thống bi": [
            "Intelligent Recommendation Service",
            "Analytics Service",
        ],
        "engine phân tích khách hàng": ["Targeted Customer Service", "Crm Service"],
        "engine tính giá động": ["Rating Engine", "Proposal Business"],
        "thuật toán đánh giá rủi ro": [
            "Underwriting Engine",
            "Auto Underwriting Process",
        ],
        "cấu hình công thức giá": [
            "Rating Engine",
            "Product Catalog",
            "Business Rules Engine",
        ],
        # Chatbot tasks
        "tích hợp nlp": ["Chatbot Service"],
        "luồng hội thoại": ["Chatbot Service"],
        "cơ sở tri thức": ["Chatbot Service", "Document Management Service"],
        "xử lý fallback": ["Chatbot Service"],
        # Payment tasks
        "tích hợp payment gateway": ["Payment Service", "Payment Integration Hub"],
        "engine tự động thanh toán": ["Payment Service", "Billing Service"],
        "xử lý thanh toán một phần": ["Payment Service", "Billing Service"],
        "workflow xử lý hoàn tiền": ["Payment Service", "Billing Service"],
        "đối soát thanh toán": ["Payment Service", "Reconcile Process"],
    }

    overlaps = []

    # Get service names
    ws_services = wb["VDS_Est_Detail_Services_Total"]
    service_names = {}
    for row in range(2, 60):
        service_id = ws_services.cell(row, 1).value
        service_name = ws_services.cell(row, 2).value
        if service_id and isinstance(service_id, (int, float)) and service_name:
            name_clean = str(service_name).split(":")[0].strip()
            service_names[int(service_id)] = name_clean

    # Check each task
    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and task_name:
            service_id_int = int(service_id)
            service_name = service_names.get(service_id_int, "")
            task_lower = str(task_name).lower()

            # Check if it's a BRD-specific task
            for task_keyword, allowed_services in brd_specific_rules.items():
                if task_keyword in task_lower:
                    # Check if service is in allowed list
                    service_allowed = False
                    for allowed_service in allowed_services:
                        if allowed_service.lower() in service_name.lower():
                            service_allowed = True
                            break

                    if not service_allowed:
                        overlaps.append(
                            {
                                "row": row,
                                "service_id": service_id_int,
                                "service_name": service_name,
                                "task_name": task_name,
                                "task_keyword": task_keyword,
                                "allowed_services": allowed_services,
                            }
                        )
                    break  # Only check first match

    return overlaps


def analyze_brd_coverage(excel_path: Path, brd_path: Path) -> dict:
    """Analyze BRD coverage and identify gaps."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Read BRD
    with open(brd_path, encoding="utf-8") as f:
        brd_content = f.read()

    # Extract BRD sections
    section3_sections = re.findall(
        r"^## \*\*(.*?)\*\*",
        brd_content[
            brd_content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO KHÁCH HÀNG**") : brd_content.find(
                "# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN**"
            )
        ],
        re.MULTILINE,
    )

    section4_sections = re.findall(
        r"^## \*\*(.*?)\*\*",
        brd_content[brd_content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN**") :],
        re.MULTILINE,
    )

    # Clean section titles
    section3_sections = [re.sub(r"\*\*", "", s).strip() for s in section3_sections]
    section4_sections = [re.sub(r"\*\*", "", s).strip() for s in section4_sections]

    # Check BRD references in sheet
    brd_refs_found = set()
    tasks_by_brd = defaultdict(list)

    for row in range(9, ws.max_row + 1):
        brd_ref = ws.cell(row, 7).value
        task_name = ws.cell(row, 6).value
        service_id = ws.cell(row, 1).value

        if brd_ref and str(brd_ref) != "N/A":
            brd_refs_found.add(str(brd_ref))
            tasks_by_brd[str(brd_ref)].append({"row": row, "service_id": service_id, "task_name": task_name})

    # Map BRD sections to found references
    coverage = {"section3": {}, "section4": {}, "missing_sections": []}

    # Check Section 3
    for section in section3_sections:
        section_lower = section.lower()
        found = False
        matching_refs = []

        for brd_ref in brd_refs_found:
            if any(keyword in brd_ref.lower() for keyword in section_lower.split() if len(keyword) > 3):
                found = True
                matching_refs.append(brd_ref)

        coverage["section3"][section] = {
            "found": found,
            "refs": matching_refs,
            "task_count": sum(len(tasks_by_brd[ref]) for ref in matching_refs),
        }

        if not found:
            coverage["missing_sections"].append({"section": "3", "title": section, "type": "customer"})

    # Check Section 4
    for section in section4_sections:
        section_lower = section.lower()
        found = False
        matching_refs = []

        for brd_ref in brd_refs_found:
            if any(keyword in brd_ref.lower() for keyword in section_lower.split() if len(keyword) > 3):
                found = True
                matching_refs.append(brd_ref)

        coverage["section4"][section] = {
            "found": found,
            "refs": matching_refs,
            "task_count": sum(len(tasks_by_brd[ref]) for ref in matching_refs),
        }

        if not found:
            coverage["missing_sections"].append({"section": "4", "title": section, "type": "admin"})

    return coverage


def main():
    """Main execution."""
    print("=" * 80)
    print("Comprehensive BRD Coverage Check and Duplicate/Overlap Detection")
    print("=" * 80)

    # Step 1: Check duplicates
    print("\nStep 1: Checking for duplicate tasks...")
    duplicates = check_duplicates(EXCEL_PATH)
    if duplicates:
        print(f"⚠️ Found {len(duplicates)} duplicate task groups:")
        for dup in duplicates[:10]:
            print(
                f"  Service {dup['service_id']}: '{dup['task_name'][:50]}...' appears {dup['count']} times at rows {dup['rows'][:5]}"
            )
    else:
        print("✅ No duplicate tasks found")

    # Step 2: Check overlaps
    print("\nStep 2: Checking for overlapping tasks...")
    overlaps = check_overlaps(EXCEL_PATH)
    if overlaps:
        print(f"⚠️ Found {len(overlaps)} overlapping tasks:")
        for overlap in overlaps[:10]:
            print(f"  Row {overlap['row']}: Service {overlap['service_id']} ({overlap['service_name']})")
            print(f"    Task: {overlap['task_name'][:50]}...")
            print(f"    Should be in: {', '.join(overlap['allowed_services'])}")
    else:
        print("✅ No overlapping tasks found")

    # Step 3: Analyze BRD coverage
    print("\nStep 3: Analyzing BRD coverage...")
    coverage = analyze_brd_coverage(EXCEL_PATH, BRD_PATH)

    section3_covered = sum(1 for s in coverage["section3"].values() if s["found"])
    section4_covered = sum(1 for s in coverage["section4"].values() if s["found"])
    total_sections = len(coverage["section3"]) + len(coverage["section4"])
    total_covered = section3_covered + section4_covered

    print(f"  Section 3 (Customer): {section3_covered}/{len(coverage['section3'])} covered")
    print(f"  Section 4 (Admin): {section4_covered}/{len(coverage['section4'])} covered")
    print(f"  Total: {total_covered}/{total_sections} ({total_covered / total_sections * 100:.1f}%)")

    if coverage["missing_sections"]:
        print(f"\n⚠️ Missing BRD sections: {len(coverage['missing_sections'])}")
        for missing in coverage["missing_sections"]:
            print(f"  {missing['section']}. {missing['title']} ({missing['type']})")

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"  Duplicates: {len(duplicates)}")
    print(f"  Overlaps: {len(overlaps)}")
    print(f"  BRD Coverage: {total_covered}/{total_sections} ({total_covered / total_sections * 100:.1f}%)")
    print(f"  Missing Sections: {len(coverage['missing_sections'])}")

    return {"duplicates": duplicates, "overlaps": overlaps, "coverage": coverage}


if __name__ == "__main__":
    results = main()
