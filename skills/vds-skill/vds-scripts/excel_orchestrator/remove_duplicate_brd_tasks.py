"""
Remove Duplicate BRD-Specific Tasks

This script removes BRD-specific tasks that were incorrectly added to services
that shouldn't have them. Standard tasks (like API Design, Unit Testing) are
kept in all services as they are legitimate.
"""

from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)

# BRD-specific tasks that should only be in specific services
BRD_SPECIFIC_TASKS = {
    # Renewal tasks - should only be in Renewal Process, Policy Business
    "thiết kế workflow gia hạn": ["Renewal Process", "Policy Business"],
    "triển khai workflow gia hạn": ["Renewal Process", "Policy Business"],
    "logic tự động gia hạn": ["Renewal Process", "Policy Business"],
    "thông báo gia hạn": ["Renewal Process", "Policy Business", "Notification Spi"],
    # Claims tasks - should only be in Claim Business
    "thiết kế state machine bồi thường": ["Claim Business"],
    "triển khai state machine bồi thường": ["Claim Business"],
    "workflow gửi yêu cầu bồi thường": ["Claim Business"],
    "hành động khách hàng": ["Claim Business"],
    "tích hợp api bồi thường nhà bảo hiểm": ["Claim Business", "Insurer Service"],
    "tích hợp thanh toán cho bồi thường": ["Claim Business", "Payment Service"],
    # Purchase/Proposal tasks - should only be in Proposal Business, Product Catalog
    "luồng mua hàng": ["Proposal Business", "Customer Business"],
    "so sánh sản phẩm": ["Proposal Business", "Product Catalog"],
    "tích hợp ocr": ["Proposal Business", "Ocr Service"],
    "engine voucher": ["Proposal Business", "Promotion Business"],
    # AI/Intelligent tasks - should only be in specific services
    "nghiên cứu ml model": [
        "Intelligent Recommendation Service",
        "Intelligent Filtering Service",
        "Targeted Customer Service",
    ],
    "engine gợi ý": ["Intelligent Recommendation Service"],
    "tích hợp hệ thống bi": ["Intelligent Recommendation Service", "Analytics Service"],
    "engine phân tích khách hàng": ["Targeted Customer Service", "Crm Service"],
    "engine tính giá động": ["Rating Engine", "Proposal Business"],
    "thuật toán đánh giá rủi ro": ["Underwriting Engine", "Auto Underwriting Process"],
    "cấu hình công thức giá": [
        "Rating Engine",
        "Product Catalog",
        "Business Rules Engine",
    ],
    # Chatbot tasks - should only be in Chatbot Service
    "tích hợp nlp": ["Chatbot Service"],
    "luồng hội thoại": ["Chatbot Service"],
    "cơ sở tri thức": ["Chatbot Service", "Document Management Service"],
    "xử lý fallback": ["Chatbot Service"],
    # Payment tasks - should only be in Payment services
    "tích hợp payment gateway": ["Payment Service", "Payment Integration Hub"],
    "engine tự động thanh toán": ["Payment Service", "Billing Service"],
    "xử lý thanh toán một phần": ["Payment Service", "Billing Service"],
    "workflow xử lý hoàn tiền": ["Payment Service", "Billing Service"],
    "đối soát thanh toán": ["Payment Service", "Reconcile Process"],
}


def should_keep_task(task_name: str, service_name: str) -> bool:
    """Check if task should be kept for this service."""
    task_lower = task_name.lower() if task_name else ""
    service_lower = service_name.lower() if service_name else ""

    # Check if it's a BRD-specific task
    for task_keyword, allowed_services in BRD_SPECIFIC_TASKS.items():
        if task_keyword in task_lower:
            # Check if service is in allowed list
            return any(allowed_service.lower() in service_lower for allowed_service in allowed_services)

    # Not a BRD-specific task - keep it (standard tasks)
    return True


def remove_duplicate_brd_tasks():
    """Remove duplicate BRD-specific tasks."""
    wb = load_workbook(EXCEL_PATH, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    rows_to_delete = []
    removed_count = 0

    # Scan all rows
    for row in range(2, ws.max_row + 1):
        service_name = ws.cell(row, 2).value
        task_name = ws.cell(row, 6).value

        if service_name and task_name and not should_keep_task(task_name, service_name):
            rows_to_delete.append(row)
            removed_count += 1

    # Delete rows in reverse order to maintain row numbers
    print(f"Found {removed_count} duplicate BRD-specific tasks to remove")

    for row in reversed(rows_to_delete):
        ws.delete_rows(row)

    # Update task IDs for remaining tasks
    current_service_id = None
    task_counter = 1

    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            if service_id_int != current_service_id:
                current_service_id = service_id_int
                task_counter = 1

            task_id = f"S{service_id_int}-T{task_counter:03d}"
            ws.cell(row, 5, task_id)
            task_counter += 1

    wb.save(EXCEL_PATH)
    print(f"Removed {removed_count} duplicate tasks")
    print("Updated task IDs for remaining tasks")
    print(f"Total tasks remaining: {ws.max_row - 1}")


if __name__ == "__main__":
    print("=" * 80)
    print("Remove Duplicate BRD-Specific Tasks")
    print("=" * 80)

    remove_duplicate_brd_tasks()

    print("\n" + "=" * 80)
    print("Cleanup completed!")
    print("=" * 80)
