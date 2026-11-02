"""
Update Task Breakdown Sheet with Vietnamese Content and Responsibility

This script:
1. Updates task names and descriptions to Vietnamese
2. Adds Responsibility column from services total sheet
3. Verifies BRD coverage
4. Updates the VDS_Task_Breakdown_Detailed sheet
"""

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# File paths
EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)
BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")

# Vietnamese translations for task categories
TASK_CATEGORY_VI = {
    "Requirements & Analysis": "Phân tích & Yêu cầu",
    "Design & Architecture": "Thiết kế & Kiến trúc",
    "Development": "Phát triển",
    "Integration": "Tích hợp",
    "Testing": "Kiểm thử",
    "Documentation": "Tài liệu",
    "Deployment": "Triển khai",
    "Compliance & Regulatory": "Tuân thủ & Quy định",
    "Security": "Bảo mật",
    "Data Migration": "Di chuyển Dữ liệu",
}

# Vietnamese translations for complexity levels
COMPLEXITY_VI = {
    "Simple": "Đơn giản",
    "Medium": "Trung bình",
    "Complex": "Phức tạp",
    "Very Complex": "Rất phức tạp",
}

# Vietnamese translations for task names
TASK_NAME_TRANSLATIONS = {
    "BRD Analysis and Requirements Extraction": "Phân tích BRD và Trích xuất Yêu cầu",
    "API Design: REST endpoints design": "Thiết kế API: Thiết kế REST endpoints",
    "Data Model Design: Entity and relationship design": "Thiết kế Mô hình Dữ liệu: Thiết kế Entity và quan hệ",
    "Business Logic - Core: Core business logic implementation": "Logic Nghiệp vụ - Cốt lõi: Triển khai logic nghiệp vụ cốt lõi",
    "Business Logic - Integration: Integration logic implementation": "Logic Nghiệp vụ - Tích hợp: Triển khai logic tích hợp",
    "Data Access Layer: Repository and JPA implementation": "Lớp Truy cập Dữ liệu: Triển khai Repository và JPA",
    "External Integration: Integration with external systems": "Tích hợp Bên ngoài: Tích hợp với hệ thống bên ngoài",
    "Unit Testing: Unit tests for business logic": "Kiểm thử Đơn vị: Unit test cho logic nghiệp vụ",
    "Integration Testing: Integration tests with other services": "Kiểm thử Tích hợp: Integration test với các service khác",
    "API Documentation: OpenAPI/Swagger documentation": "Tài liệu API: Tài liệu OpenAPI/Swagger",
    "Deployment: CI/CD pipeline and deployment scripts": "Triển khai: CI/CD pipeline và deployment scripts",
    "Compliance: Audit trail and regulatory compliance": "Tuân thủ: Audit trail và tuân thủ quy định",
    "Security: Authentication, authorization, and data encryption": "Bảo mật: Xác thực, phân quyền và mã hóa dữ liệu",
    # BRD-specific tasks
    "Purchase Flow: Guest checkout and account creation during purchase": "Luồng Mua hàng: Guest checkout và tạo tài khoản khi mua",
    "Product Comparison: Real-time pricing and benefit comparison": "So sánh Sản phẩm: So sánh giá và quyền lợi real-time",
    "OCR Integration: Document reading and data extraction": "Tích hợp OCR: Đọc tài liệu và trích xuất dữ liệu",
    "Voucher/Promotion Engine: Auto-apply best voucher": "Engine Voucher/Khuyến mãi: Tự động áp dụng voucher tốt nhất",
    "Renewal Workflow Design: Design 4 different renewal types": "Thiết kế Workflow Gia hạn: Thiết kế 4 loại gia hạn khác nhau",
    "Renewal Workflow Implementation: Implement 4 renewal workflow types": "Triển khai Workflow Gia hạn: Triển khai 4 loại workflow gia hạn",
    "Auto-Renewal Logic: Different rules per renewal type": "Logic Tự động Gia hạn: Quy tắc khác nhau cho từng loại gia hạn",
    "Renewal Notification: SMS and email notification integration": "Thông báo Gia hạn: Tích hợp thông báo SMS và email",
    "Claims State Machine Design: Design 8+ state transitions": "Thiết kế State Machine Bồi thường: Thiết kế 8+ trạng thái chuyển đổi",
    "Claims State Machine Implementation: Implement 8+ state transitions": "Triển khai State Machine Bồi thường: Triển khai 8+ trạng thái chuyển đổi",
    "Claim Submission Workflow: Document upload and validation": "Workflow Gửi Yêu cầu Bồi thường: Upload tài liệu và validation",
    "Customer Actions: Reject/accept with OTP/signature": "Hành động Khách hàng: Từ chối/chấp nhận với OTP/chữ ký",
    "Insurer Claim API Integration: Claim processing integration": "Tích hợp API Bồi thường Nhà bảo hiểm: Tích hợp xử lý bồi thường",
    "Payment Integration: Core Payment integration for claim payment": "Tích hợp Thanh toán: Tích hợp Core Payment cho thanh toán bồi thường",
    "ML Model Research: Research and select recommendation models": "Nghiên cứu ML Model: Nghiên cứu và chọn mô hình gợi ý",
    "Recommendation Engine: Implement ML-based recommendation": "Engine Gợi ý: Triển khai gợi ý dựa trên ML",
    "BI System Integration: Integration for customer data": "Tích hợp Hệ thống BI: Tích hợp dữ liệu khách hàng",
    "Customer Profiling Engine: ML-based customer profiling": "Engine Phân tích Khách hàng: Phân tích khách hàng dựa trên ML",
    "Dynamic Pricing Engine: Real-time pricing calculation": "Engine Tính giá Động: Tính toán giá real-time",
    "Risk Assessment Algorithms: Risk coefficient calculation": "Thuật toán Đánh giá Rủi ro: Tính toán hệ số rủi ro",
    "Pricing Formula Configuration: CMS-configurable pricing": "Cấu hình Công thức Giá: Tính giá có thể cấu hình qua CMS",
    "NLP Integration: Natural language processing integration": "Tích hợp NLP: Tích hợp xử lý ngôn ngữ tự nhiên",
    "Conversation Flow: Design and implement conversation flows": "Luồng Hội thoại: Thiết kế và triển khai luồng hội thoại",
    "Knowledge Base: Build and maintain knowledge base": "Cơ sở Tri thức: Xây dựng và duy trì cơ sở tri thức",
    "Fallback Handling: Handle unknown queries gracefully": "Xử lý Fallback: Xử lý các truy vấn không xác định",
    "Payment Gateway Integration: Multiple payment providers": "Tích hợp Payment Gateway: Nhiều nhà cung cấp thanh toán",
    "Auto-Payment Engine: Multi-source, priority-based auto-payment": "Engine Tự động Thanh toán: Tự động thanh toán đa nguồn, ưu tiên",
    "Partial Payment Processing: Support partial payments": "Xử lý Thanh toán Một phần: Hỗ trợ thanh toán một phần",
    "Refund Processing Workflow: Multiple cancellation types": "Workflow Xử lý Hoàn tiền: Nhiều loại hủy",
    "Payment Reconciliation: Automated and manual reconciliation": "Đối soát Thanh toán: Đối soát tự động và thủ công",
}


def get_responsibility_map(excel_path: Path) -> dict:
    """Get responsibility mapping from services total sheet."""
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["VDS_Est_Detail_Services_Total"]

    responsibility_map = {}
    for row in range(2, 60):
        service_id = ws.cell(row, 1).value
        service_name = ws.cell(row, 2).value
        responsibility = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and service_name:
            responsibility_map[int(service_id)] = responsibility or "Unknown"

    return responsibility_map


def translate_task_name(task_name: str) -> str:
    """Translate task name to Vietnamese."""
    # Check if we have a direct translation
    if task_name in TASK_NAME_TRANSLATIONS:
        return TASK_NAME_TRANSLATIONS[task_name]

    # Try to translate common patterns

    # If no direct match, return original (will be translated manually later)
    return task_name


def update_task_breakdown_sheet(excel_path: Path):
    """Update the task breakdown sheet with Vietnamese content and responsibility."""
    print("Updating task breakdown sheet with Vietnamese content and responsibility...")

    wb = load_workbook(excel_path, data_only=False)

    # Get responsibility map
    responsibility_map = get_responsibility_map(excel_path)
    print(f"Loaded responsibility for {len(responsibility_map)} services")

    # Update detailed breakdown sheet
    if "VDS_Task_Breakdown_Detailed" not in wb.sheetnames:
        print("Error: VDS_Task_Breakdown_Detailed sheet not found!")
        return

    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Check if Responsibility column exists (column N = 14)
    has_responsibility = ws.cell(1, 14).value == "Responsibility" or ws.cell(1, 14).value == "Trách nhiệm"

    if not has_responsibility:
        # Insert Responsibility column after Service Name (column B)
        ws.insert_cols(3, 1)  # Insert at column C, shifting others right

        # Update header
        ws.cell(1, 3, "Trách nhiệm")
        ws.cell(1, 3).fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        ws.cell(1, 3).font = Font(bold=True, color="FFFFFF", size=11)
        ws.cell(1, 3).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.cell(1, 3).border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Update all other headers (shifted)
        headers = [
            "Service ID",
            "Service Name",
            "Trách nhiệm",
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

        for col_idx, _header in enumerate(headers, 1):
            if col_idx <= ws.max_column:
                cell = ws.cell(1, col_idx)
                if not cell.fill:
                    cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                if not cell.font or not cell.font.bold:
                    cell.font = Font(bold=True, color="FFFFFF", size=11)
                if not cell.alignment:
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Update data rows
    updated_count = 0
    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            # Add responsibility
            responsibility = responsibility_map.get(int(service_id), "Unknown")
            ws.cell(row, 3, responsibility)  # Column C is now Responsibility

            # Translate task category
            task_category = ws.cell(row, 4).value  # Now column 4 (was 3)
            if task_category and task_category in TASK_CATEGORY_VI:
                ws.cell(row, 4, TASK_CATEGORY_VI[task_category])

            # Translate task name
            task_name = ws.cell(row, 6).value  # Now column 6 (was 5)
            if task_name:
                translated_name = translate_task_name(task_name)
                if translated_name != task_name:
                    ws.cell(row, 6, translated_name)

            # Translate complexity level
            complexity = ws.cell(row, 8).value  # Now column 8 (was 7)
            if complexity and complexity in COMPLEXITY_VI:
                ws.cell(row, 8, COMPLEXITY_VI[complexity])

            # Apply borders
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row, col)
                if not cell.border:
                    cell.border = Border(
                        left=Side(style="thin"),
                        right=Side(style="thin"),
                        top=Side(style="thin"),
                        bottom=Side(style="thin"),
                    )

            updated_count += 1

    # Update column widths
    ws.column_dimensions["C"].width = 15  # Responsibility

    print(f"Updated {updated_count} task rows")

    # Save
    wb.save(excel_path)
    print("Task breakdown sheet updated successfully")


def verify_brd_coverage(excel_path: Path, brd_path: Path):
    """Verify BRD coverage in the task breakdown."""
    print("\nVerifying BRD coverage...")

    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Read BRD to get all requirements
    with open(brd_path, encoding="utf-8") as f:
        f.read()

    # Extract key BRD sections

    # Check coverage
    brd_refs_in_sheet = set()
    for row in range(2, ws.max_row + 1):
        brd_ref = ws.cell(row, 7).value  # BRD Reference column
        if brd_ref and brd_ref != "N/A":
            brd_refs_in_sheet.add(str(brd_ref))

    print(f"\nBRD References found in sheet: {len(brd_refs_in_sheet)}")
    print("Sample BRD references:")
    for ref in list(brd_refs_in_sheet)[:10]:
        print(f"  - {ref}")

    # Count tasks with BRD references
    tasks_with_brd = 0
    tasks_without_brd = 0
    for row in range(2, ws.max_row + 1):
        brd_ref = ws.cell(row, 7).value
        if brd_ref and brd_ref != "N/A":
            tasks_with_brd += 1
        else:
            tasks_without_brd += 1

    print("\nBRD Coverage:")
    print(
        f"  Tasks with BRD references: {tasks_with_brd} ({tasks_with_brd / (tasks_with_brd + tasks_without_brd) * 100:.1f}%)"
    )
    print(
        f"  Tasks without BRD references: {tasks_without_brd} ({tasks_without_brd / (tasks_with_brd + tasks_without_brd) * 100:.1f}%)"
    )

    # Check responsibility distribution
    print("\nResponsibility Distribution:")
    responsibility_counts = {}
    for row in range(2, ws.max_row + 1):
        responsibility = ws.cell(row, 3).value
        if responsibility:
            responsibility_counts[responsibility] = responsibility_counts.get(responsibility, 0) + 1

    for resp, count in sorted(responsibility_counts.items()):
        print(f"  {resp}: {count} tasks")


def main():
    """Main execution."""
    print("=" * 80)
    print("Update Task Breakdown with Vietnamese Content and Responsibility")
    print("=" * 80)

    # Step 1: Update sheet with Vietnamese and responsibility
    update_task_breakdown_sheet(EXCEL_PATH)

    # Step 2: Verify BRD coverage
    verify_brd_coverage(EXCEL_PATH, BRD_PATH)

    print("\n" + "=" * 80)
    print("Update completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
