"""
Update Task Breakdown Sheet with Vietnamese Content and Responsibility

This script:
1. Translates all task names, categories, and complexity levels to Vietnamese
2. Adds Responsibility column from services total sheet
3. Verifies BRD coverage thoroughly
4. Updates the VDS_Task_Breakdown_Detailed sheet
"""

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# File paths
EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)
BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")

# Vietnamese translations
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

COMPLEXITY_VI = {
    "Simple": "Đơn giản",
    "Medium": "Trung bình",
    "Complex": "Phức tạp",
    "Very Complex": "Rất phức tạp",
}

# Comprehensive Vietnamese task name translations
TASK_TRANSLATIONS = {
    # Standard tasks
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
    # BRD-specific - Purchase
    "Purchase Flow: Guest checkout and account creation during purchase": "Luồng Mua hàng: Guest checkout và tạo tài khoản khi mua",
    "Product Comparison: Real-time pricing and benefit comparison": "So sánh Sản phẩm: So sánh giá và quyền lợi real-time",
    "OCR Integration: Document reading and data extraction": "Tích hợp OCR: Đọc tài liệu và trích xuất dữ liệu",
    "Voucher/Promotion Engine: Auto-apply best voucher": "Engine Voucher/Khuyến mãi: Tự động áp dụng voucher tốt nhất",
    # BRD-specific - Renewal
    "Renewal Workflow Design: Design 4 different renewal types": "Thiết kế Workflow Gia hạn: Thiết kế 4 loại gia hạn khác nhau",
    "Renewal Workflow Implementation: Implement 4 renewal workflow types": "Triển khai Workflow Gia hạn: Triển khai 4 loại workflow gia hạn",
    "Auto-Renewal Logic: Different rules per renewal type": "Logic Tự động Gia hạn: Quy tắc khác nhau cho từng loại gia hạn",
    "Renewal Notification: SMS and email notification integration": "Thông báo Gia hạn: Tích hợp thông báo SMS và email",
    # BRD-specific - Claims
    "Claims State Machine Design: Design 8+ state transitions": "Thiết kế State Machine Bồi thường: Thiết kế 8+ trạng thái chuyển đổi",
    "Claims State Machine Implementation: Implement 8+ state transitions": "Triển khai State Machine Bồi thường: Triển khai 8+ trạng thái chuyển đổi",
    "Claim Submission Workflow: Document upload and validation": "Workflow Gửi Yêu cầu Bồi thường: Upload tài liệu và validation",
    "Customer Actions: Reject/accept with OTP/signature": "Hành động Khách hàng: Từ chối/chấp nhận với OTP/chữ ký",
    "Insurer Claim API Integration: Claim processing integration": "Tích hợp API Bồi thường Nhà bảo hiểm: Tích hợp xử lý bồi thường",
    "Payment Integration: Core Payment integration for claim payment": "Tích hợp Thanh toán: Tích hợp Core Payment cho thanh toán bồi thường",
    # BRD-specific - AI/Intelligent
    "ML Model Research: Research and select recommendation models": "Nghiên cứu ML Model: Nghiên cứu và chọn mô hình gợi ý",
    "Recommendation Engine: Implement ML-based recommendation": "Engine Gợi ý: Triển khai gợi ý dựa trên ML",
    "BI System Integration: Integration for customer data": "Tích hợp Hệ thống BI: Tích hợp dữ liệu khách hàng",
    "Customer Profiling Engine: ML-based customer profiling": "Engine Phân tích Khách hàng: Phân tích khách hàng dựa trên ML",
    "Dynamic Pricing Engine: Real-time pricing calculation": "Engine Tính giá Động: Tính toán giá real-time",
    "Risk Assessment Algorithms: Risk coefficient calculation": "Thuật toán Đánh giá Rủi ro: Tính toán hệ số rủi ro",
    "Pricing Formula Configuration: CMS-configurable pricing": "Cấu hình Công thức Giá: Tính giá có thể cấu hình qua CMS",
    # BRD-specific - Chatbot
    "NLP Integration: Natural language processing integration": "Tích hợp NLP: Tích hợp xử lý ngôn ngữ tự nhiên",
    "Conversation Flow: Design and implement conversation flows": "Luồng Hội thoại: Thiết kế và triển khai luồng hội thoại",
    "Knowledge Base: Build and maintain knowledge base": "Cơ sở Tri thức: Xây dựng và duy trì cơ sở tri thức",
    "Fallback Handling: Handle unknown queries gracefully": "Xử lý Fallback: Xử lý các truy vấn không xác định",
    # BRD-specific - Payment
    "Payment Gateway Integration: Multiple payment providers": "Tích hợp Payment Gateway: Nhiều nhà cung cấp thanh toán",
    "Auto-Payment Engine: Multi-source, priority-based auto-payment": "Engine Tự động Thanh toán: Tự động thanh toán đa nguồn, ưu tiên",
    "Partial Payment Processing: Support partial payments": "Xử lý Thanh toán Một phần: Hỗ trợ thanh toán một phần",
    "Refund Processing Workflow: Multiple cancellation types": "Workflow Xử lý Hoàn tiền: Nhiều loại hủy",
    "Payment Reconciliation: Automated and manual reconciliation": "Đối soát Thanh toán: Đối soát tự động và thủ công",
}


def get_responsibility_map(excel_path: Path) -> dict[int, str]:
    """Get responsibility mapping from services total sheet."""
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["VDS_Est_Detail_Services_Total"]

    responsibility_map = {}
    for row in range(2, 60):
        service_id = ws.cell(row, 1).value
        responsibility = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)):
            responsibility_map[int(service_id)] = responsibility or "Unknown"

    return responsibility_map


def translate_text(text: str, translations: dict[str, str]) -> str:
    """Translate text using translation dictionary."""
    if not text:
        return text

    text_str = str(text).strip()

    # Direct match
    if text_str in translations:
        return translations[text_str]

    # Partial match (for task names that might have variations)
    for en_text, vi_text in translations.items():
        if en_text.lower() in text_str.lower() or text_str.lower() in en_text.lower():
            # Replace the matching part
            if en_text.lower() in text_str.lower():
                return text_str.replace(en_text, vi_text)

    return text_str


def update_sheet_with_vietnamese_and_responsibility(excel_path: Path):
    """Update task breakdown sheet with Vietnamese content and responsibility."""
    print("Updating task breakdown sheet...")

    wb = load_workbook(excel_path, data_only=False)

    if "VDS_Task_Breakdown_Detailed" not in wb.sheetnames:
        print("Error: VDS_Task_Breakdown_Detailed sheet not found!")
        return

    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Get responsibility map
    responsibility_map = get_responsibility_map(excel_path)
    print(f"Loaded responsibility for {len(responsibility_map)} services")

    # Check if Responsibility column exists
    current_headers = [ws.cell(1, col).value for col in range(1, 15)]
    has_responsibility = any("Trách nhiệm" in str(h) or "Responsibility" in str(h) for h in current_headers if h)

    if not has_responsibility:
        # Insert Responsibility column after Service Name (column B = 2)
        ws.insert_cols(3, 1)
        print("Inserted Responsibility column")

        # Update all headers
        headers_vi = [
            "ID Dịch vụ",
            "Tên Dịch vụ",
            "Trách nhiệm",
            "Danh mục Task",
            "ID Task",
            "Tên Task",
            "Tham chiếu BRD",
            "Mức độ Phức tạp",
            "Effort Cơ bản (Ngày)",
            "Hệ số Áp dụng",
            "Effort Cuối cùng (Ngày)",
            "Effort Cuối cùng (Giờ)",
            "Phụ thuộc",
            "Ghi chú",
        ]

        # Apply header styling
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for col_idx, header in enumerate(headers_vi, 1):
            cell = ws.cell(1, col_idx)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = border
    else:
        # Update existing headers to Vietnamese
        headers_vi = [
            "ID Dịch vụ",
            "Tên Dịch vụ",
            "Trách nhiệm",
            "Danh mục Task",
            "ID Task",
            "Tên Task",
            "Tham chiếu BRD",
            "Mức độ Phức tạp",
            "Effort Cơ bản (Ngày)",
            "Hệ số Áp dụng",
            "Effort Cuối cùng (Ngày)",
            "Effort Cuối cùng (Giờ)",
            "Phụ thuộc",
            "Ghi chú",
        ]
        for col_idx, header in enumerate(headers_vi, 1):
            if col_idx <= ws.max_column:
                ws.cell(1, col_idx, header)

    # Update data rows
    updated_count = 0
    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            # Add/update responsibility (column 3)
            responsibility = responsibility_map.get(int(service_id), "Unknown")
            ws.cell(row, 3, responsibility)

            # Translate task category (column 4)
            task_category = ws.cell(row, 4).value
            if task_category:
                translated_category = translate_text(task_category, TASK_CATEGORY_VI)
                ws.cell(row, 4, translated_category)

            # Translate task name (column 6)
            task_name = ws.cell(row, 6).value
            if task_name:
                translated_name = translate_text(task_name, TASK_TRANSLATIONS)
                ws.cell(row, 6, translated_name)

            # Translate complexity level (column 8)
            complexity = ws.cell(row, 8).value
            if complexity:
                translated_complexity = translate_text(complexity, COMPLEXITY_VI)
                ws.cell(row, 8, translated_complexity)

            # Apply borders to all cells
            border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row, col)
                if not cell.border:
                    cell.border = border

            updated_count += 1

    # Update summary section headers
    summary_row = None
    for row in range(ws.max_row - 10, ws.max_row + 1):
        if ws.cell(row, 1).value and "SUMMARY" in str(ws.cell(row, 1).value).upper():
            summary_row = row
            break

    if summary_row:
        summary_labels_vi = {
            "SUMMARY": "TỔNG KẾT",
            "Total Tasks:": "Tổng số Task:",
            "Total Base Effort (Days):": "Tổng Effort Cơ bản (Ngày):",
            "Total Final Effort (Days):": "Tổng Effort Cuối cùng (Ngày):",
            "Total Final Effort (Hours):": "Tổng Effort Cuối cùng (Giờ):",
            "Services Covered:": "Số Dịch vụ:",
        }

        for row in range(summary_row, ws.max_row + 1):
            label = ws.cell(row, 1).value
            if label and str(label) in summary_labels_vi:
                ws.cell(row, 1, summary_labels_vi[str(label)])

    # Update column widths
    ws.column_dimensions["A"].width = 12  # Service ID
    ws.column_dimensions["B"].width = 40  # Service Name
    ws.column_dimensions["C"].width = 15  # Responsibility
    ws.column_dimensions["D"].width = 25  # Task Category
    ws.column_dimensions["E"].width = 12  # Task ID
    ws.column_dimensions["F"].width = 60  # Task Name
    ws.column_dimensions["G"].width = 25  # BRD Reference
    ws.column_dimensions["H"].width = 18  # Complexity
    ws.column_dimensions["I"].width = 18  # Base Effort
    ws.column_dimensions["J"].width = 35  # Multiplier
    ws.column_dimensions["K"].width = 18  # Final Days
    ws.column_dimensions["L"].width = 18  # Final Hours
    ws.column_dimensions["M"].width = 30  # Dependencies
    ws.column_dimensions["N"].width = 60  # Notes

    wb.save(excel_path)
    print(f"Updated {updated_count} task rows with Vietnamese content and responsibility")


def verify_brd_coverage_detailed(excel_path: Path, brd_path: Path):
    """Perform detailed BRD coverage verification."""
    print("\n" + "=" * 80)
    print("BRD Coverage Verification")
    print("=" * 80)

    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Read BRD
    with open(brd_path, encoding="utf-8") as f:
        brd_content = f.read()

    # Extract BRD sections
    section3_sections = re.findall(
        r"## \*\*(.*?)\*\*",
        brd_content[
            brd_content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO KHÁCH HÀNG**") : brd_content.find(
                "# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN**"
            )
        ],
    )

    section4_sections = re.findall(
        r"## \*\*(.*?)\*\*",
        brd_content[brd_content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN**") :],
    )

    print("\nBRD Sections Found:")
    print(f"  Section 3 (Customer): {len(section3_sections)} sections")
    print(f"  Section 4 (Admin): {len(section4_sections)} sections")

    # Check BRD references in sheet
    brd_refs = set()
    tasks_by_brd = {}

    for row in range(2, ws.max_row + 1):
        brd_ref = ws.cell(row, 7).value  # BRD Reference column
        task_name = ws.cell(row, 6).value
        service_id = ws.cell(row, 1).value

        if brd_ref and str(brd_ref) != "N/A":
            brd_refs.add(str(brd_ref))
            if str(brd_ref) not in tasks_by_brd:
                tasks_by_brd[str(brd_ref)] = []
            tasks_by_brd[str(brd_ref)].append({"service_id": service_id, "task": task_name})

    print(f"\nBRD References in Sheet: {len(brd_refs)}")
    print(f"Tasks with BRD references: {sum(len(tasks) for tasks in tasks_by_brd.values())}")

    # Check responsibility distribution
    print("\nResponsibility Distribution:")
    responsibility_stats = {}
    for row in range(2, ws.max_row + 1):
        responsibility = ws.cell(row, 3).value
        base_effort = ws.cell(row, 9).value or 0
        final_effort = ws.cell(row, 11).value or 0

        if responsibility:
            if responsibility not in responsibility_stats:
                responsibility_stats[responsibility] = {
                    "tasks": 0,
                    "base_days": 0,
                    "final_days": 0,
                }
            responsibility_stats[responsibility]["tasks"] += 1
            if isinstance(base_effort, (int, float)):
                responsibility_stats[responsibility]["base_days"] += base_effort
            if isinstance(final_effort, (int, float)):
                responsibility_stats[responsibility]["final_days"] += final_effort

    for resp, stats in sorted(responsibility_stats.items()):
        print(f"  {resp}:")
        print(f"    Tasks: {stats['tasks']}")
        print(f"    Base Effort: {stats['base_days']:.2f} days")
        print(f"    Final Effort: {stats['final_days']:.2f} days ({stats['final_days'] * 8:.0f} hours)")

    # Check key BRD requirements coverage
    print("\nKey BRD Requirements Coverage:")
    key_requirements = {
        "Tài Khoản": ["Đăng Ký", "Đăng Nhập"],
        "Mua Bảo Hiểm": ["Đề xuất", "Chatbot", "Tùy chỉnh", "So sánh", "Thanh Toán"],
        "Gia Hạn": ["Gia hạn", "Tái tục"],
        "Bồi Thường": ["Bồi thường", "Yêu cầu"],
    }

    for req_category, keywords in key_requirements.items():
        coverage_count = 0
        for brd_ref in brd_refs:
            if any(keyword.lower() in brd_ref.lower() for keyword in keywords):
                coverage_count += len(tasks_by_brd.get(brd_ref, []))
        print(f"  {req_category}: {coverage_count} tasks")


def main():
    """Main execution."""
    print("=" * 80)
    print("Update Task Breakdown with Vietnamese and Responsibility")
    print("=" * 80)

    # Step 1: Update sheet
    update_sheet_with_vietnamese_and_responsibility(EXCEL_PATH)

    # Step 2: Verify BRD coverage
    verify_brd_coverage_detailed(EXCEL_PATH, BRD_PATH)

    print("\n" + "=" * 80)
    print("Update completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
