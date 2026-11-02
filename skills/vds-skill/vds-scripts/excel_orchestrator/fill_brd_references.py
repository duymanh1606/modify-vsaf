"""
Fill BRD References Correctly

This script:
1. Analyzes task names and service names to map to BRD sections
2. Replaces N/A with appropriate BRD references
3. Ensures all tasks have valid BRD references
"""

import re
from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)

# BRD Section Mapping
BRD_MAPPING = {
    # Customer Features (Section 3)
    "account": ["3.1", "3.Tài Khoản"],
    "đăng ký": ["3.1.1"],
    "đăng nhập": ["3.1.2"],
    "đăng xuất": ["3.1.3"],
    "quên mật khẩu": ["3.1.4"],
    "lấy lại mật khẩu": ["3.1.4"],
    "quản lý thông tin": ["3.2", "3.Quản Lý Thông Tin"],
    "cập nhật thông tin": ["3.2.1"],
    "thông tin thanh toán": ["3.2.2"],
    "mua bảo hiểm": ["3.3", "3.3.5", "3.Mua Bảo Hiểm"],
    "đề xuất sản phẩm": ["3.3.1"],
    "gợi ý sản phẩm": ["3.3.1"],
    "kế hoạch bảo vệ": ["3.3.1"],
    "chatbot": ["3.3.2"],
    "tùy chỉnh sản phẩm": ["3.3.3"],
    "cá nhân hóa": ["3.3.3"],
    "so sánh sản phẩm": ["3.3.4"],
    "lưu đơn hàng": ["3.3.6"],
    "sửa đơn hàng": ["3.3.6"],
    "hủy đơn hàng": ["3.3.6"],
    "mã giới thiệu": ["3.3.7"],
    "referral": ["3.3.7"],
    "mã giảm giá": ["3.3.8"],
    "voucher": ["3.3.8"],
    "thanh toán đơn hàng": ["3.3.9"],
    "payment": ["3.3.9"],
    "quản lý hợp đồng": ["3.4", "3.Quản lý hợp đồng bảo hiểm"],
    "xem hợp đồng": ["3.4.1"],
    "chi tiết hợp đồng": ["3.4.1"],
    "nhắc gia hạn": ["3.4.2", "3.Nhắc gia hạn"],
    "tái tục": ["3.4.2", "3.4.3"],
    "gia hạn": ["3.4.3", "3.4.4"],
    "thay đổi hình thức gia hạn": ["3.4.4"],
    "hủy hợp đồng": ["3.4.5"],
    "yêu cầu bồi thường": ["3.5"],
    "claims": ["3.5"],
    "bồi thường": ["3.5"],
    # Admin Features (Section 4)
    "quản trị viên": ["4.1"],
    "admin account": ["4.1"],
    "quản lý đối tác": ["4.2"],
    "partner": ["4.2"],
    "quản lý sản phẩm": ["4.3"],
    "product management": ["4.3"],
    "danh sách sản phẩm": ["4.3.1"],
    "nhóm sản phẩm": ["4.3.1"],
    "cấu hình sản phẩm": ["4.3.2"],
    "cấu hình gói": ["4.3.2"],
    "quyền lợi": ["4.3.3"],
    "phí": ["4.3.3"],
    "quản lý khách hàng": ["4.4"],
    "customer management": ["4.4"],
    "quản lý hợp đồng admin": ["4.5", "4.Quản Lý Hợp Đồng"],
    "quản lý yêu cầu bồi thường": ["4.6"],
    "ycbt": ["4.6"],
    "quản lý kênh bán": ["4.7"],
    "sales channel": ["4.7"],
    "quản lý chiến dịch": ["4.8"],
    "campaign": ["4.8"],
    "quản lý nội dung": ["4.9"],
    "content management": ["4.9"],
    "báo cáo": ["4.10"],
    "đối soát": ["4.10"],
    "reporting": ["4.10"],
    "cảnh báo": ["4.11", "4.Cảnh Báo"],
    "alert": ["4.11"],
    # Non-functional requirements
    "performance": ["NFR"],
    "scalability": ["NFR"],
    "security": ["NFR"],
    "compliance": ["NFR"],
    "accessibility": ["NFR"],
    "monitoring": ["NFR"],
    "observability": ["NFR"],
    "disaster recovery": ["NFR"],
    "backup": ["NFR"],
    "failover": ["NFR"],
    "testing": ["NFR"],
    "infrastructure": ["NFR"],
    "deployment": ["NFR"],
    "ci/cd": ["NFR"],
    "devops": ["NFR"],
}

# Service to BRD mapping
SERVICE_BRD_MAPPING = {
    "user management": ["4.1"],
    "config platform": ["4.3.2"],
    "billing": ["3.3.9"],
    "payment": ["3.3.9"],
    "product": ["4.3"],
    "policy": ["3.4", "4.5"],
    "claims": ["3.5", "4.6"],
    "customer": ["3.2", "4.4"],
    "agent": ["4.2"],
    "campaign": ["4.8"],
    "content": ["4.9"],
    "reporting": ["4.10"],
    "alert": ["4.11"],
    "observability": ["NFR"],
    "security": ["NFR"],
    "platform": ["NFR"],
    "infrastructure": ["NFR"],
    "testing": ["NFR"],
    "orchestrator": ["NFR"],
    "integration": ["NFR"],
}


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    if not text:
        return ""
    # Remove diacritics and convert to lowercase
    text = text.lower().strip()
    # Remove special characters
    text = re.sub(r"[^\w\s]", " ", text)
    # Normalize whitespace
    text = " ".join(text.split())
    return text


def find_brd_reference(task_name: str, service_name: str, category: str) -> str:
    """Find appropriate BRD reference for a task."""
    task_normalized = normalize_text(task_name)
    service_normalized = normalize_text(service_name)
    category_normalized = normalize_text(category)

    combined_text = f"{task_normalized} {service_normalized} {category_normalized}"

    matched_refs = set()

    # Check task name keywords
    for keyword, refs in BRD_MAPPING.items():
        if keyword in task_normalized or keyword in combined_text:
            matched_refs.update(refs)

    # Check service name keywords
    for keyword, refs in SERVICE_BRD_MAPPING.items():
        if keyword in service_normalized:
            matched_refs.update(refs)

    # Check category
    if "kiểm thử" in category_normalized or "testing" in category_normalized:
        matched_refs.add("NFR")
    if "bảo mật" in category_normalized or "security" in category_normalized:
        matched_refs.add("NFR")
    if "triển khai" in category_normalized or "deployment" in category_normalized:
        matched_refs.add("NFR")
    if "infrastructure" in category_normalized or "infrastructure" in service_normalized:
        matched_refs.add("NFR")

    # If no matches found, check for generic patterns
    if not matched_refs:
        if any(word in task_normalized for word in ["phân tích", "thiết kế", "phát triển", "tích hợp", "tài liệu"]):
            # These are standard SDLC tasks, check service context
            if "platform" in service_normalized or "infrastructure" in service_normalized:
                matched_refs.add("NFR")
            else:
                # Try to infer from service name
                for keyword, refs in SERVICE_BRD_MAPPING.items():
                    if keyword in service_normalized:
                        matched_refs.update(refs)
                        break

    # If still no matches, use NFR for infrastructure/platform tasks
    if not matched_refs:
        if any(
            word in service_normalized
            for word in [
                "platform",
                "infrastructure",
                "testing",
                "observability",
                "security",
                "orchestrator",
                "integration",
            ]
        ):
            matched_refs.add("NFR")
        else:
            # Default to NFR for standard tasks without clear BRD mapping
            matched_refs.add("NFR")

    # Filter out invalid references (too short, single letters, etc.)
    valid_refs = []
    for ref in matched_refs:
        ref_clean = ref.strip()
        # Skip invalid references
        if len(ref_clean) <= 1 and ref_clean not in ["NFR"]:
            continue
        # Skip single letters
        if len(ref_clean) == 1 and ref_clean.isalpha():
            continue
        valid_refs.append(ref_clean)

    # Return sorted, comma-separated references (max 3)
    sorted_refs = sorted(set(valid_refs))
    return ", ".join(sorted_refs[:3]) if sorted_refs else "NFR"


def fill_brd_references(excel_path: Path):
    """Fill BRD references for all tasks."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("=" * 80)
    print("Filling BRD References")
    print("=" * 80)

    updated_count = 0
    n_a_replaced = 0

    for row in range(9, ws.max_row + 1):
        task_id = ws.cell(row, 5).value
        task_name = ws.cell(row, 6).value
        current_brd_ref = ws.cell(row, 7).value
        service_name = ws.cell(row, 2).value
        category = ws.cell(row, 4).value

        if task_id and task_name:
            # Check if needs update
            needs_update = False

            if not current_brd_ref or str(current_brd_ref).strip() == "":
                needs_update = True
            elif str(current_brd_ref).upper() == "N/A":
                needs_update = True
                n_a_replaced += 1

            if needs_update:
                new_brd_ref = find_brd_reference(
                    str(task_name),
                    str(service_name) if service_name else "",
                    str(category) if category else "",
                )

                ws.cell(row, 7, new_brd_ref)
                updated_count += 1

    wb.save(excel_path)

    print(f"\n✅ Updated {updated_count} BRD references")
    print(f"   Replaced N/A: {n_a_replaced}")

    return updated_count


def verify_brd_references(excel_path: Path):
    """Verify all BRD references are filled."""
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("\n" + "=" * 80)
    print("Verifying BRD References")
    print("=" * 80)

    empty_refs = []
    n_a_refs = []
    valid_refs = []

    for row in range(9, ws.max_row + 1):
        task_id = ws.cell(row, 5).value
        brd_ref = ws.cell(row, 7).value

        if task_id:
            if not brd_ref or str(brd_ref).strip() == "":
                empty_refs.append(row)
            elif str(brd_ref).upper() == "N/A":
                n_a_refs.append(row)
            else:
                valid_refs.append(row)

    print("\nBRD Reference Status:")
    print(f"  Empty: {len(empty_refs)}")
    print(f"  N/A: {len(n_a_refs)}")
    print(f"  Valid: {len(valid_refs)}")

    if empty_refs or n_a_refs:
        print(f"\n⚠️ Still have {len(empty_refs) + len(n_a_refs)} tasks without BRD references")
    else:
        print("\n✅ All tasks have BRD references!")

    # Count unique references
    unique_refs = set()
    for row in valid_refs:
        ref = ws.cell(row, 7).value
        if ref:
            refs = str(ref).split(",")
            for r in refs:
                unique_refs.add(r.strip())

    print(f"\nUnique BRD References: {len(unique_refs)}")
    print("  Top references:")
    ref_count = {}
    for row in valid_refs:
        ref = ws.cell(row, 7).value
        if ref:
            refs = str(ref).split(",")
            for r in refs:
                ref_clean = r.strip()
                ref_count[ref_clean] = ref_count.get(ref_clean, 0) + 1

    for ref, count in sorted(ref_count.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"    {ref}: {count} tasks")


def main():
    """Main execution."""
    print("=" * 80)
    print("Fill BRD References")
    print("=" * 80)

    # Step 1: Fill BRD references
    fill_brd_references(EXCEL_PATH)

    # Step 2: Verify
    verify_brd_references(EXCEL_PATH)

    print("\n" + "=" * 80)
    print("✅ BRD reference filling completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
