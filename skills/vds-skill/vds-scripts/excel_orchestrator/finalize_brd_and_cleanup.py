"""
Finalize BRD Coverage and Cleanup

This script:
1. Improves BRD references for all tasks
2. Ensures "Báo Cáo và Đối Soát" is properly referenced
3. Double-checks for duplicates and overlaps
4. Updates any missing BRD references
"""

import re
from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)
BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")


def improve_all_brd_references(excel_path: Path):
    """Improve BRD references for all tasks."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Comprehensive BRD keyword mapping
    brd_keyword_map = {
        # Section 3 - Customer
        "tài khoản": "3.1",
        "đăng ký": "3.1.1",
        "đăng nhập": "3.1.2",
        "đăng xuất": "3.1.3",
        "quên mật khẩu": "3.1.4",
        "quản lý thông tin": "3.2",
        "mua bảo hiểm": "3.3",
        "đề xuất": "3.3.1",
        "gợi ý": "3.3.1",
        "kế hoạch bảo vệ": "3.3.1",
        "chatbot": "3.3.2",
        "tùy chỉnh": "3.3.3",
        "so sánh": "3.3.4",
        "thanh toán": "3.3.5",
        "voucher": "3.3.8",
        "khuyến mãi": "3.3.8",
        "quản lý hợp đồng": "3.4",
        "xem chi tiết": "3.4.1",
        "gia hạn": "3.4.3",
        "tái tục": "3.4.3",
        "thay đổi hình thức": "3.4.3",
        "hủy hợp đồng": "3.4.4",
        "bồi thường": "3.5",
        "yêu cầu bồi thường": "3.5",
        # Section 4 - Admin
        "quản lý tài khoản quản trị": "4.1",
        "quản lý đối tác": "4.2",
        "quản lý sản phẩm": "4.3",
        "danh sách sản phẩm": "4.3.1",
        "nhóm sản phẩm": "4.3.1",
        "cấu hình sản phẩm": "4.3.2",
        "gói sản phẩm": "4.3.2",
        "quyền lợi": "4.3.3",
        "phí": "4.3.3",
        "quản lý khách hàng": "4.4",
        "quản lý hợp đồng": "4.5",
        "quản lý yêu cầu bồi thường": "4.6",
        "quản lý kênh bán": "4.7",
        "quản lý chiến dịch": "4.8",
        "quản lý nội dung": "4.9",
        "báo cáo": "4.10",
        "đối soát": "4.10",
        "reconcile": "4.10",
        "report": "4.10",
        "cảnh báo": "4.11",
    }

    updated_count = 0

    for row in range(9, ws.max_row + 1):
        task_name = ws.cell(row, 6).value
        service_name = ws.cell(row, 2).value
        current_brd_ref = ws.cell(row, 7).value

        if task_name:
            task_lower = str(task_name).lower()
            service_lower = str(service_name).lower() if service_name else ""
            combined_text = f"{task_lower} {service_lower}"

            # Find matching BRD references
            matched_refs = []
            for keyword, brd_ref in brd_keyword_map.items():
                if keyword in combined_text and brd_ref not in matched_refs:
                    matched_refs.append(brd_ref)

            # Special handling for Báo Cáo và Đối Soát
            if any(kw in combined_text for kw in ["báo cáo", "đối soát", "report", "reconcile"]):
                if "4.10" not in matched_refs:
                    matched_refs.append("4.10")

            # Update if we found references
            if matched_refs:
                new_ref = ", ".join(sorted(set(matched_refs))[:3])  # Sort and limit to 3

                # Update if missing or incomplete
                if not current_brd_ref or str(current_brd_ref) == "N/A" or len(str(current_brd_ref)) < 5:
                    ws.cell(row, 7, new_ref)
                    updated_count += 1
                else:
                    # Check if we need to add missing references
                    existing_refs = [r.strip() for r in str(current_brd_ref).split(",")]
                    new_refs_to_add = [r for r in matched_refs if r not in existing_refs]

                    if new_refs_to_add:
                        combined = sorted(set(existing_refs + new_refs_to_add))
                        ws.cell(row, 7, ", ".join(combined[:3]))
                        updated_count += 1

    wb.save(excel_path)
    print(f"✅ Improved BRD references for {updated_count} tasks")
    return updated_count


def verify_no_duplicates(excel_path: Path):
    """Verify no duplicate tasks exist."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    task_map = {}
    duplicates = []

    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and task_name:
            service_id_int = int(service_id)
            task_normalized = str(task_name).lower().strip()
            task_normalized = re.sub(r"[^\w\s]", "", task_normalized)
            task_normalized = " ".join(task_normalized.split())

            key = (service_id_int, task_normalized)
            if key in task_map:
                duplicates.append(
                    {
                        "service_id": service_id_int,
                        "task_name": task_name,
                        "rows": [task_map[key], row],
                    }
                )
            else:
                task_map[key] = row

    if duplicates:
        print(f"⚠️ Found {len(duplicates)} duplicates:")
        for dup in duplicates:
            print(f"  Service {dup['service_id']}: '{dup['task_name'][:50]}...' at rows {dup['rows']}")
        return False
    else:
        print("✅ No duplicates found")
        return True


def verify_no_overlaps(excel_path: Path):
    """Verify no overlapping BRD-specific tasks."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Get service names
    ws_services = wb["VDS_Est_Detail_Services_Total"]
    service_names = {}
    for row in range(2, 60):
        service_id = ws_services.cell(row, 1).value
        service_name = ws_services.cell(row, 2).value
        if service_id and isinstance(service_id, (int, float)) and service_name:
            name_clean = str(service_name).split(":")[0].strip()
            service_names[int(service_id)] = name_clean

    brd_specific_rules = {
        "thiết kế workflow gia hạn": ["Renewal Process", "Policy Business"],
        "triển khai workflow gia hạn": ["Renewal Process", "Policy Business"],
        "logic tự động gia hạn": ["Renewal Process", "Policy Business"],
        "thiết kế state machine bồi thường": ["Claim Business"],
        "triển khai state machine bồi thường": ["Claim Business"],
        "workflow gửi yêu cầu bồi thường": ["Claim Business"],
        "nghiên cứu ml model": [
            "Intelligent Recommendation Service",
            "Intelligent Filtering Service",
            "Targeted Customer Service",
        ],
        "engine gợi ý": ["Intelligent Recommendation Service"],
        "tích hợp nlp": ["Chatbot Service"],
        "luồng hội thoại": ["Chatbot Service"],
        "tích hợp payment gateway": ["Payment Service", "Payment Integration Hub"],
    }

    overlaps = []

    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and task_name:
            service_id_int = int(service_id)
            service_name = service_names.get(service_id_int, "")
            task_lower = str(task_name).lower()

            for task_keyword, allowed_services in brd_specific_rules.items():
                if task_keyword in task_lower:
                    service_allowed = any(allowed.lower() in service_name.lower() for allowed in allowed_services)
                    if not service_allowed:
                        overlaps.append(
                            {
                                "row": row,
                                "service_id": service_id_int,
                                "service_name": service_name,
                                "task_name": task_name,
                            }
                        )
                    break

    if overlaps:
        print(f"⚠️ Found {len(overlaps)} overlaps:")
        for overlap in overlaps[:5]:
            print(f"  Row {overlap['row']}: Service {overlap['service_id']} ({overlap['service_name']})")
            print(f"    Task: {overlap['task_name'][:50]}...")
        return False
    else:
        print("✅ No overlaps found")
        return True


def main():
    """Main execution."""
    print("=" * 80)
    print("Finalize BRD Coverage and Cleanup")
    print("=" * 80)

    # Step 1: Improve BRD references
    print("\nStep 1: Improving BRD references...")
    updated_count = improve_all_brd_references(EXCEL_PATH)

    # Step 2: Verify no duplicates
    print("\nStep 2: Verifying no duplicates...")
    no_duplicates = verify_no_duplicates(EXCEL_PATH)

    # Step 3: Verify no overlaps
    print("\nStep 3: Verifying no overlaps...")
    no_overlaps = verify_no_overlaps(EXCEL_PATH)

    # Step 4: Final BRD coverage check
    print("\nStep 4: Final BRD coverage check...")
    wb = load_workbook(EXCEL_PATH, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    tasks_with_brd = 0
    tasks_without_brd = 0
    brd_refs = set()

    for row in range(9, ws.max_row + 1):
        brd_ref = ws.cell(row, 7).value
        if brd_ref and str(brd_ref) != "N/A" and len(str(brd_ref)) > 3:
            tasks_with_brd += 1
            refs = str(brd_ref).split(",")
            for ref in refs:
                ref_clean = ref.strip()
                if ref_clean:
                    brd_refs.add(ref_clean)
        else:
            tasks_without_brd += 1

    total_tasks = tasks_with_brd + tasks_without_brd
    coverage_pct = (tasks_with_brd / total_tasks * 100) if total_tasks > 0 else 0

    print(f"  Tasks with BRD references: {tasks_with_brd}/{total_tasks} ({coverage_pct:.1f}%)")
    print(f"  Unique BRD references: {len(brd_refs)}")

    # Check for 4.10 (Báo Cáo và Đối Soát)
    has_4_10 = any("4.10" in ref for ref in brd_refs)
    if has_4_10:
        print("  ✅ Báo Cáo và Đối Soát (4.10) is referenced")
    else:
        print("  ⚠️ Báo Cáo và Đối Soát (4.10) not found in references")

    print("\n" + "=" * 80)
    print("Finalization completed!")
    print("=" * 80)
    print("\nSummary:")
    print(f"  BRD references updated: {updated_count}")
    print(f"  No duplicates: {'✅' if no_duplicates else '⚠️'}")
    print(f"  No overlaps: {'✅' if no_overlaps else '⚠️'}")
    print(f"  BRD coverage: {coverage_pct:.1f}%")


if __name__ == "__main__":
    main()
