"""Fill column F (Remarks) with functional descriptions and make color presentation consistent."""

from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# Service functional descriptions for remarks
SERVICE_REMARKS = {
    "Proposal Business": "Mục tiêu: Phát triển Proposal Business Service - Quản lý đề xuất bảo hiểm, tính toán phí, validation, workflow approval",
    "Policy Business": "Mục tiêu: Phát triển Policy Business Service - Quản lý chính sách bảo hiểm, issuance, renewal, cancellation, endorsement",
    "Customer Business": "Mục tiêu: Phát triển Customer Business Service - Quản lý khách hàng, member management, customer profiles, relationships",
    "Claim Business": "Mục tiêu: Phát triển Claim Business Service - Quản lý bồi thường, claim processing, approval workflow, settlement",
    "Rating Engine": "Mục tiêu: Phát triển Rating Engine - Tính toán phí bảo hiểm, rating formulas, product pricing, premium calculation",
    "Underwriting": "Mục tiêu: Phát triển Underwriting Service - Thẩm định rủi ro, underwriting rules, risk assessment, approval",
    "Product Catalog": "Mục tiêu: Phát triển Product Catalog Service - Quản lý sản phẩm bảo hiểm, multi-insurer products, product configuration, variations",
    "Business Rules Engine": "Mục tiêu: Phát triển Business Rules Engine - Quản lý business rules, rule evaluation, multi-insurer rules, rule versioning",
    "Config Platform": "Mục tiêu: Phát triển Config Platform - Quản lý cấu hình, multi-insurer configurations, feature flags, environment settings",
    "Payment Service": "Mục tiêu: Phát triển Payment Service - Xử lý thanh toán, payment gateway integration, async callbacks, polling, timeout handling",
    "Billing Service": "Mục tiêu: Phát triển Billing Service - Quản lý thu phí, billing cycles, invoice generation, payment tracking",
    "Carrier Integration": "Mục tiêu: Phát triển Carrier Integration Service - Tích hợp với carriers, product synchronization, policy issuance, data exchange",
    "Orchestrator": "Mục tiêu: Phát triển Orchestrator Service - Điều phối workflows, service orchestration, composite operations, transaction management",
    "Workflow Service": "Mục tiêu: Phát triển Workflow Service - Quản lý Camunda workflows, BPMN processes, workflow automation, process orchestration",
    "Document Service": "Mục tiêu: Phát triển Document Service - Quản lý tài liệu, certificate generation, document storage, document retrieval",
    "Notification Service": "Mục tiêu: Phát triển Notification Service - Gửi thông báo, email, SMS, push notifications, notification templates",
    "Analytics Service": "Mục tiêu: Phát triển Analytics Service - Phân tích dữ liệu, reporting, dashboards, business intelligence, data aggregation",
    "Agent Business": "Mục tiêu: Phát triển Agent Business Service - Quản lý đại lý, agent profiles, commission management, agent portal",
    "Cms Be": "Mục tiêu: Phát triển CMS Backend Service - Quản lý nội dung, content management, configuration UI, business user interface",
    "Customer Interface": "Mục tiêu: Phát triển Customer Interface - Giao diện khách hàng, customer portal, self-service, mobile app backend",
    "Admin Portal": "Mục tiêu: Phát triển Admin Portal - Giao diện quản trị, admin dashboard, system management, user management",
    "Agent Portal": "Mục tiêu: Phát triển Agent Portal - Giao diện đại lý, agent dashboard, sales management, commission tracking",
    "Bff Services": "Mục tiêu: Phát triển BFF Services - Backend for Frontend, API aggregation, composite operations, client-specific APIs",
    "Authentication Sync": "Mục tiêu: Phát triển Authentication Sync Process - Đồng bộ authentication, token management, session management, security",
    "User Management": "Mục tiêu: Phát triển User Management Service - Quản lý người dùng, user profiles, roles, permissions, access control",
    "Centralized Sync": "Mục tiêu: Phát triển Centralized Sync Service - Đồng bộ dữ liệu tập trung, data synchronization, conflict resolution",
    "Data Migration": "Mục tiêu: Phát triển Data Migration Service - Migration dữ liệu, data transformation, migration scripts, validation",
    "Security Service": "Mục tiêu: Phát triển Security Service - Bảo mật, authentication, authorization, encryption, security policies",
    "Observability Service": "Mục tiêu: Phát triển Observability Service - Monitoring, logging, tracing, metrics, alerting, performance monitoring",
    "Cicd Platform": "Mục tiêu: Phát triển CI/CD Platform - Continuous integration, continuous deployment, build pipelines, automated testing",
    "Test Platform": "Mục tiêu: Phát triển Test Platform - Testing infrastructure, test automation, test data management, test reporting",
    "Gateway Service": "Mục tiêu: Phát triển Gateway Service - API Gateway, routing, load balancing, rate limiting, API management",
    "Socialized Insurance": "Mục tiêu: Phát triển Socialized Insurance Service - Bảo hiểm xã hội hóa, social insurance integration, government integration",
    "Timeout Process": "Mục tiêu: Phát triển Timeout Process Service - Xử lý timeout, async operations, retry logic, timeout handling",
    "Reconciliation Service": "Mục tiêu: Phát triển Reconciliation Service - Đối soát, reconciliation logic, data matching, discrepancy resolution",
    "Regulator Service": "Mục tiêu: Phát triển Regulator Service - Tích hợp với cơ quan quản lý, regulatory reporting, compliance, audit",
    "Ocr Service": "Mục tiêu: Phát triển OCR Service - Nhận dạng ký tự, document scanning, text extraction, image processing",
    "Content Service": "Mục tiêu: Phát triển Content Service - Quản lý nội dung, content delivery, content storage, content management",
    "Schedule Service": "Mục tiêu: Phát triển Schedule Service - Lập lịch, scheduling, cron jobs, task scheduling, batch processing",
    "Fraud Detection": "Mục tiêu: Phát triển Fraud Detection Service - Phát hiện gian lận, fraud detection algorithms, risk scoring, fraud prevention",
    "Renewal Service": "Mục tiêu: Phát triển Renewal Service - Gia hạn bảo hiểm, renewal processing, renewal reminders, renewal automation",
    "Intelligent Recommendation": "Mục tiêu: Phát triển Intelligent Recommendation Service - Gợi ý sản phẩm thông minh, AI-powered recommendations, ML models, personalization",
    "Intelligent Filtering": "Mục tiêu: Phát triển Intelligent Filtering Service - Lọc thông minh, AI-powered filtering, semantic search, intelligent search",
    "Targeted Customer": "Mục tiêu: Phát triển Targeted Customer Service - Phân khúc khách hàng, customer segmentation, targeting rules, campaign management",
}


def get_service_remark(service_name):
    """Get remark for service."""
    for key, remark in SERVICE_REMARKS.items():
        if key.lower() in service_name.lower():
            return remark
    return None


if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]
    original = wb["Est Detail"]

    print("=== Filling Remarks and Making Colors Consistent ===")

    # Get color scheme from original
    header_fill_color = original.cell(8, 6).fill.fgColor.rgb if original.cell(8, 6).fill.fgColor.rgb else "FFC6D9F0"
    total_fill_color = original.cell(9, 6).fill.fgColor.rgb if original.cell(9, 6).fill.fgColor.rgb else "FFF2F2F2"

    # Create fill objects
    header_fill = PatternFill(start_color=header_fill_color, end_color=header_fill_color, fill_type="solid")
    total_fill = PatternFill(start_color=total_fill_color, end_color=total_fill_color, fill_type="solid")

    # Apply colors to VDS sheet
    print("\\nStep 1: Applying color scheme...")
    detail.cell(8, 6).fill = header_fill  # Header row
    detail.cell(9, 6).fill = total_fill  # Total row

    # Fill remarks for services
    print("\\nStep 2: Filling remarks for services...")
    services_filled = 0

    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value

        if col3 and isinstance(col2, (int, float)):
            # Service header row
            service_name = str(col3)
            remark = get_service_remark(service_name)

            if remark:
                detail.cell(row, 6).value = remark
                services_filled += 1
            else:
                # Generic remark if not found
                detail.cell(row, 6).value = f"Mục tiêu: Phát triển {service_name.split(':')[0].strip()}"
                services_filled += 1

    print(f"Filled remarks for {services_filled} services")

    # Apply consistent fill to all rows (same as original)
    print("\\nStep 3: Applying consistent fill to all rows...")
    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col6_fill = detail.cell(row, 6).fill

        # Task rows should have no fill (like original)
        if not isinstance(col2, (int, float)) and col6_fill.patternType:
            detail.cell(row, 6).fill = PatternFill()  # Clear fill

    # Ensure total row has fill
    detail.cell(527, 6).fill = total_fill

    # Also apply to category total row if it exists
    if detail.cell(9, 6).value:  # If row 9 is a total row
        detail.cell(9, 6).fill = total_fill

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")
    print("\\n✅ Remarks filled and colors made consistent!")

    # Summary
    print("\\n=== Summary ===")
    print(f"Services with remarks: {services_filled}")
    print("Color scheme: Consistent with original Est Detail sheet")
