"""
Increase BRD Coverage by Adding Missing Tasks

This script:
1. Identifies uncovered BRD sections
2. Adds appropriate tasks for uncovered sections
3. Improves BRD references for existing tasks
4. Updates the Excel file
"""

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Border, Side

BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")
EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)

# Tasks to add for uncovered BRD sections
MISSING_TASKS = {
    # Section 3 - Customer Features
    "Hủy Hợp Đồng": {
        "services": ["Policy Business", "Contract Orchestrator"],
        "tasks": [
            {
                "category": "Phát triển",
                "name": "Workflow Hủy Hợp Đồng: Xử lý yêu cầu hủy hợp đồng",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "3.4.4",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Logic Tính toán Hoàn tiền: Tính toán số tiền hoàn lại khi hủy",
                "complexity": "Phức tạp",
                "base_effort": 6,
                "brd_ref": "3.4.4",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Tích hợp",
                "name": "Tích hợp Payment Service: Xử lý hoàn tiền khi hủy",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "3.4.4",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Tích hợp",
                "name": "Tích hợp Insurer API: Thông báo hủy hợp đồng cho nhà bảo hiểm",
                "complexity": "Trung bình",
                "base_effort": 4,
                "brd_ref": "3.4.4",
                "multiplier": "1.59x (base)",
            },
        ],
    },
    "Thay Đổi Hình Thức Gia Hạn": {
        "services": ["Renewal Process", "Policy Business"],
        "tasks": [
            {
                "category": "Phát triển",
                "name": "Workflow Thay đổi Hình thức Gia hạn: Cho phép khách hàng thay đổi hình thức gia hạn",
                "complexity": "Phức tạp",
                "base_effort": 7,
                "brd_ref": "3.4.3",
                "multiplier": "1.59x (base) × 1.3x (renewal)",
            },
            {
                "category": "Phát triển",
                "name": "Validation Logic: Kiểm tra điều kiện thay đổi hình thức gia hạn",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "3.4.3",
                "multiplier": "1.59x (base) × 1.3x (renewal)",
            },
            {
                "category": "Tích hợp",
                "name": "Tích hợp Notification: Thông báo thay đổi hình thức gia hạn",
                "complexity": "Trung bình",
                "base_effort": 3,
                "brd_ref": "3.4.3",
                "multiplier": "1.59x (base)",
            },
        ],
    },
    # Section 4 - Admin Features
    "Danh sách & nhóm sản phẩm": {
        "services": ["Product Catalog", "Cms Be"],
        "tasks": [
            {
                "category": "Phát triển",
                "name": "Quản lý Danh sách Sản phẩm: CRUD operations cho danh sách sản phẩm",
                "complexity": "Trung bình",
                "base_effort": 6,
                "brd_ref": "4.3.1",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Quản lý Nhóm Sản phẩm: Tạo và quản lý nhóm sản phẩm",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "4.3.1",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Gán Sản phẩm vào Nhóm: Logic gán sản phẩm vào các nhóm",
                "complexity": "Trung bình",
                "base_effort": 4,
                "brd_ref": "4.3.1",
                "multiplier": "1.59x (base)",
            },
        ],
    },
    "Cấu hình sản phẩm & gói": {
        "services": ["Product Catalog", "Business Rules Engine", "Cms Be"],
        "tasks": [
            {
                "category": "Phát triển",
                "name": "Cấu hình Sản phẩm: Thiết lập các tham số sản phẩm",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "4.3.2",
                "multiplier": "1.59x (base) × 1.3x (logic)",
            },
            {
                "category": "Phát triển",
                "name": "Cấu hình Gói Sản phẩm: Tạo và quản lý gói sản phẩm",
                "complexity": "Phức tạp",
                "base_effort": 7,
                "brd_ref": "4.3.2",
                "multiplier": "1.59x (base) × 1.3x (logic)",
            },
            {
                "category": "Phát triển",
                "name": "Validation Rules: Kiểm tra tính hợp lệ của cấu hình",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "4.3.2",
                "multiplier": "1.59x (base) × 1.3x (logic)",
            },
            {
                "category": "Tích hợp",
                "name": "Tích hợp Business Rules Engine: Áp dụng rules cho cấu hình",
                "complexity": "Trung bình",
                "base_effort": 4,
                "brd_ref": "4.3.2",
                "multiplier": "1.59x (base)",
            },
        ],
    },
    "Quyền lợi & phí": {
        "services": [
            "Product Catalog",
            "Business Rules Engine",
            "Rating Engine",
            "Cms Be",
        ],
        "tasks": [
            {
                "category": "Phát triển",
                "name": "Quản lý Quyền lợi: CRUD operations cho quyền lợi sản phẩm",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "4.3.3",
                "multiplier": "1.59x (base) × 1.3x (logic)",
            },
            {
                "category": "Phát triển",
                "name": "Quản lý Phí: Thiết lập và quản lý cấu trúc phí",
                "complexity": "Phức tạp",
                "base_effort": 7,
                "brd_ref": "4.3.3",
                "multiplier": "1.59x (base) × 1.3x (logic)",
            },
            {
                "category": "Phát triển",
                "name": "Công thức Tính phí: Thiết kế và triển khai công thức tính phí động",
                "complexity": "Rất phức tạp",
                "base_effort": 10,
                "brd_ref": "4.3.3",
                "multiplier": "1.59x (base) × 1.3x (logic) × 1.2x (dynamic pricing)",
            },
            {
                "category": "Tích hợp",
                "name": "Tích hợp Rating Engine: Sử dụng engine tính phí",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "4.3.3",
                "multiplier": "1.59x (base)",
            },
        ],
    },
    "Báo Cáo và Đối Soát": {
        "services": ["Analytics Service", "Reconcile Process", "Cms Be"],
        "tasks": [
            {
                "category": "Phát triển",
                "name": "Hệ thống Báo cáo: Tạo và quản lý các loại báo cáo",
                "complexity": "Phức tạp",
                "base_effort": 10,
                "brd_ref": "4.10",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Báo cáo Tùy chỉnh: Cho phép admin tạo báo cáo tùy chỉnh",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "4.10",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Xuất Báo cáo: Hỗ trợ xuất báo cáo nhiều định dạng (PDF, Excel, CSV)",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "4.10",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Đối Soát Tự động: Tự động đối soát dữ liệu giữa các hệ thống",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "4.10",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Đối Soát Thủ công: Giao diện cho admin đối soát thủ công",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "4.10",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Tích hợp",
                "name": "Tích hợp Reconcile Process: Sử dụng quy trình đối soát",
                "complexity": "Trung bình",
                "base_effort": 4,
                "brd_ref": "4.10",
                "multiplier": "1.59x (base)",
            },
        ],
    },
}


def get_service_id_by_name(excel_path: Path, service_name: str) -> int:
    """Get service ID by service name."""
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["VDS_Est_Detail_Services_Total"]

    for row in range(2, 60):
        name = ws.cell(row, 2).value
        service_id = ws.cell(row, 1).value

        if name and service_id:
            name_clean = str(name).split(":")[0].strip()
            if service_name.lower() in name_clean.lower() or name_clean.lower() in service_name.lower():
                return int(service_id)

    return None


def calculate_final_effort(base_effort: float, multiplier_str: str) -> tuple:
    """Calculate final effort from base effort and multiplier string."""
    multipliers = {
        "base": 1.59,
        "renewal": 1.3,
        "logic": 1.3,
        "dynamic pricing": 1.2,
        "workflow": 1.25,
        "ai": 1.4,
    }

    # Parse multiplier string
    total_multiplier = 1.0
    for key, value in multipliers.items():
        if key in multiplier_str.lower():
            total_multiplier *= value

    final_days = base_effort * total_multiplier
    final_hours = final_days * 8

    return final_days, final_hours, f"{total_multiplier:.2f}x"


def get_next_task_id(excel_path: Path, service_id: int) -> str:
    """Get next task ID for a service."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    max_task_num = 0
    for row in range(2, ws.max_row + 1):
        row_service_id = ws.cell(row, 1).value
        task_id = ws.cell(row, 5).value

        if row_service_id and isinstance(row_service_id, (int, float)) and int(row_service_id) == service_id:
            if task_id and isinstance(task_id, str):
                # Extract task number from S{id}-T{num}
                match = re.search(r"T(\d+)", str(task_id))
                if match:
                    task_num = int(match.group(1))
                    max_task_num = max(max_task_num, task_num)

    next_task_num = max_task_num + 1
    return f"S{service_id}-T{next_task_num:03d}"


def add_missing_tasks(excel_path: Path):
    """Add missing tasks for uncovered BRD sections."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Get service info
    ws_services = wb["VDS_Est_Detail_Services_Total"]
    service_info = {}
    for row in range(2, 60):
        service_id = ws_services.cell(row, 1).value
        service_name = ws_services.cell(row, 2).value
        responsibility = ws_services.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and service_name:
            name_clean = str(service_name).split(":")[0].strip()
            service_info[int(service_id)] = {
                "name": name_clean,
                "full_name": str(service_name).strip(),
                "responsibility": responsibility or "Unknown",
            }

    added_count = 0

    # Add tasks for each uncovered section
    for section_name, section_data in MISSING_TASKS.items():
        print(f"\nAdding tasks for: {section_name}")

        for service_name_pattern in section_data["services"]:
            # Find matching service
            service_id = None
            for sid, info in service_info.items():
                if service_name_pattern.lower() in info["name"].lower():
                    service_id = sid
                    break

            if not service_id:
                print(f"  ⚠️ Service not found: {service_name_pattern}")
                continue

            service_data = service_info[service_id]
            print(f"  ✓ Found service: {service_id} - {service_data['name']}")

            # Add tasks for this service
            for task_data in section_data["tasks"]:
                # Get next task ID
                task_id = get_next_task_id(excel_path, service_id)

                # Calculate final effort
                final_days, final_hours, multiplier_applied = calculate_final_effort(
                    task_data["base_effort"], task_data["multiplier"]
                )

                # Find next empty row
                next_row = ws.max_row + 1

                # Set values
                ws.cell(next_row, 1, service_id)  # Service ID
                ws.cell(next_row, 2, service_data["full_name"])  # Service Name
                ws.cell(next_row, 3, service_data["responsibility"])  # Responsibility
                ws.cell(next_row, 4, task_data["category"])  # Task Category
                ws.cell(next_row, 5, task_id)  # Task ID
                ws.cell(next_row, 6, task_data["name"])  # Task Name
                ws.cell(next_row, 7, task_data["brd_ref"])  # BRD Reference
                ws.cell(next_row, 8, task_data["complexity"])  # Complexity
                ws.cell(next_row, 9, task_data["base_effort"])  # Base Effort
                ws.cell(next_row, 10, task_data["multiplier"])  # Multiplier Applied
                ws.cell(next_row, 11, final_days)  # Final Days
                ws.cell(next_row, 12, final_hours)  # Final Hours
                ws.cell(next_row, 13, "")  # Dependencies
                ws.cell(next_row, 14, f"Added for BRD coverage: {section_name}")  # Notes

                # Apply formatting
                border = Border(
                    left=Side(style="thin"),
                    right=Side(style="thin"),
                    top=Side(style="thin"),
                    bottom=Side(style="thin"),
                )
                for col in range(1, 15):
                    cell = ws.cell(next_row, col)
                    cell.border = border

                added_count += 1
                print(f"    ✓ Added: {task_id} - {task_data['name'][:50]}...")

    wb.save(excel_path)
    print(f"\n✅ Added {added_count} tasks for uncovered BRD sections")


def improve_brd_references(excel_path: Path):
    """Improve BRD references for existing tasks."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # BRD section mappings for better references
    brd_improvements = {
        "gia hạn": "3.4.3",
        "tái tục": "3.4.3",
        "renewal": "3.4.3",
        "bồi thường": "3.5",
        "claim": "3.5",
        "mua bảo hiểm": "3.3",
        "purchase": "3.3",
        "proposal": "3.3",
        "tài khoản": "3.1",
        "account": "3.1",
        "đăng ký": "3.1.1",
        "đăng nhập": "3.1.2",
        "quản lý thông tin": "3.2",
        "hủy hợp đồng": "3.4.4",
        "cancel": "3.4.4",
        "quản lý sản phẩm": "4.3",
        "product": "4.3",
        "quản lý đối tác": "4.2",
        "partner": "4.2",
        "quản lý khách hàng": "4.4",
        "customer": "4.4",
        "quản lý hợp đồng": "4.5",
        "policy": "4.5",
        "báo cáo": "4.10",
        "report": "4.10",
        "đối soát": "4.10",
        "reconcile": "4.10",
    }

    updated_count = 0

    for row in range(2, ws.max_row + 1):
        task_name = ws.cell(row, 6).value
        current_brd_ref = ws.cell(row, 7).value

        if task_name:
            task_lower = str(task_name).lower()

            # Find matching BRD references
            matched_refs = []
            for keyword, brd_ref in brd_improvements.items():
                if keyword in task_lower and brd_ref not in matched_refs:
                    matched_refs.append(brd_ref)

            # Update if we found better references
            if matched_refs:
                new_ref = ", ".join(matched_refs[:3])  # Limit to 3

                # Only update if current reference is missing or too generic
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
    print(f"✅ Improved BRD references for {updated_count} tasks")


def main():
    """Main execution."""
    print("=" * 80)
    print("Increase BRD Coverage")
    print("=" * 80)

    # Step 1: Add missing tasks
    print("\nStep 1: Adding missing tasks for uncovered BRD sections...")
    add_missing_tasks(EXCEL_PATH)

    # Step 2: Improve BRD references
    print("\nStep 2: Improving BRD references for existing tasks...")
    improve_brd_references(EXCEL_PATH)

    print("\n" + "=" * 80)
    print("BRD coverage increased successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
