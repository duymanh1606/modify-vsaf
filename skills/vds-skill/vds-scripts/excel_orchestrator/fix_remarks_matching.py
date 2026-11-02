"""Fix remarks to match exact service names in each row."""

from openpyxl import load_workbook

# Map service names to their correct remarks
SERVICE_REMARKS_MAP = {
    # Extract key from service name and map to correct remark
    "agent business": "Mục tiêu: Phát triển Agent Business Service - Quản lý đại lý, agent profiles, commission management, agent portal",
    "analytics service": "Mục tiêu: Phát triển Analytics Service - Phân tích dữ liệu, reporting, dashboards, business intelligence, data aggregation",
    "authentication sync": "Mục tiêu: Phát triển Authentication Sync Process - Đồng bộ authentication, token management, session management, security",
    "auto underwriting": "Mục tiêu: Phát triển Auto Underwriting Process - Thẩm định tự động, automated underwriting rules, risk assessment, auto-approval",
    "billing service": "Mục tiêu: Phát triển Billing Service - Quản lý thu phí, billing cycles, invoice generation, payment tracking",
    "business rules engine": "Mục tiêu: Phát triển Business Rules Engine - Quản lý business rules, rule evaluation, multi-insurer rules, rule versioning",
    "centralized sync": "Mục tiêu: Phát triển Centralized Sync Service - Đồng bộ dữ liệu tập trung, data synchronization, conflict resolution",
    "cicd platform": "Mục tiêu: Phát triển CI/CD Platform - Continuous integration, continuous deployment, build pipelines, automated testing",
    "claim business": "Mục tiêu: Phát triển Claim Business Service - Quản lý bồi thường, claim processing, approval workflow, settlement",
    "cms be": "Mục tiêu: Phát triển CMS Backend Service - Quản lý nội dung, content management, configuration UI, business user interface",
    "config platform": "Mục tiêu: Phát triển Config Platform - Quản lý cấu hình, multi-insurer configurations, feature flags, environment settings",
    "customer business": "Mục tiêu: Phát triển Customer Business Service - Quản lý khách hàng, member management, customer profiles, relationships",
    "customer interface": "Mục tiêu: Phát triển Customer Interface - Giao diện khách hàng, customer portal, self-service, mobile app backend",
    "admin portal": "Mục tiêu: Phát triển Admin Portal - Giao diện quản trị, admin dashboard, system management, user management",
    "agent portal": "Mục tiêu: Phát triển Agent Portal - Giao diện đại lý, agent dashboard, sales management, commission tracking",
    "bff services": "Mục tiêu: Phát triển BFF Services - Backend for Frontend, API aggregation, composite operations, client-specific APIs",
    "carrier integration": "Mục tiêu: Phát triển Carrier Integration Service - Tích hợp với carriers, product synchronization, policy issuance, data exchange",
    "document service": "Mục tiêu: Phát triển Document Service - Quản lý tài liệu, certificate generation, document storage, document retrieval",
    "document management": "Mục tiêu: Phát triển Document Management Service - Quản lý tài liệu, document storage, document retrieval, document versioning, document templates",
    "gateway service": "Mục tiêu: Phát triển Gateway Service - API Gateway, routing, load balancing, rate limiting, API management",
    "intelligent recommendation": "Mục tiêu: Phát triển Intelligent Recommendation Service - Gợi ý sản phẩm thông minh, AI-powered recommendations, ML models, personalization",
    "intelligent filtering": "Mục tiêu: Phát triển Intelligent Filtering Service - Lọc thông minh, AI-powered filtering, semantic search, intelligent search",
    "targeted customer": "Mục tiêu: Phát triển Targeted Customer Service - Phân khúc khách hàng, customer segmentation, targeting rules, campaign management",
    "notification service": "Mục tiêu: Phát triển Notification Service - Gửi thông báo, email, SMS, push notifications, notification templates",
    "ocr service": "Mục tiêu: Phát triển OCR Service - Nhận dạng ký tự, document scanning, text extraction, image processing",
    "orchestrator": "Mục tiêu: Phát triển Orchestrator Service - Điều phối workflows, service orchestration, composite operations, transaction management",
    "payment service": "Mục tiêu: Phát triển Payment Service - Xử lý thanh toán, payment gateway integration, async callbacks, polling, timeout handling",
    "policy business": "Mục tiêu: Phát triển Policy Business Service - Quản lý chính sách bảo hiểm, issuance, renewal, cancellation, endorsement",
    "product catalog": "Mục tiêu: Phát triển Product Catalog Service - Quản lý sản phẩm bảo hiểm, multi-insurer products, product configuration, variations",
    "proposal business": "Mục tiêu: Phát triển Proposal Business Service - Quản lý đề xuất bảo hiểm, tính toán phí, validation, workflow approval",
    "rating engine": "Mục tiêu: Phát triển Rating Engine - Tính toán phí bảo hiểm, rating formulas, product pricing, premium calculation",
    "reconciliation service": "Mục tiêu: Phát triển Reconciliation Service - Đối soát, reconciliation logic, data matching, discrepancy resolution",
    "regulator service": "Mục tiêu: Phát triển Regulator Service - Tích hợp với cơ quan quản lý, regulatory reporting, compliance, audit",
    "renewal service": "Mục tiêu: Phát triển Renewal Service - Gia hạn bảo hiểm, renewal processing, renewal reminders, renewal automation",
    "security service": "Mục tiêu: Phát triển Security Service - Bảo mật, authentication, authorization, encryption, security policies",
    "observability service": "Mục tiêu: Phát triển Observability Service - Monitoring, logging, tracing, metrics, alerting, performance monitoring",
    "socialized insurance": "Mục tiêu: Phát triển Socialized Insurance Service - Bảo hiểm xã hội hóa, social insurance integration, government integration",
    "timeout process": "Mục tiêu: Phát triển Timeout Process Service - Xử lý timeout, async operations, retry logic, timeout handling",
    "user management": "Mục tiêu: Phát triển User Management Service - Quản lý người dùng, user profiles, roles, permissions, access control",
    "workflow service": "Mục tiêu: Phát triển Workflow Service - Quản lý Camunda workflows, BPMN processes, workflow automation, process orchestration",
    "underwriting": "Mục tiêu: Phát triển Underwriting Service - Thẩm định rủi ro, underwriting rules, risk assessment, approval",
    "data migration": "Mục tiêu: Phát triển Data Migration Service - Migration dữ liệu, data transformation, migration scripts, validation",
    "test platform": "Mục tiêu: Phát triển Test Platform - Testing infrastructure, test automation, test data management, test reporting",
    "content service": "Mục tiêu: Phát triển Content Service - Quản lý nội dung, content delivery, content storage, content management",
    "schedule service": "Mục tiêu: Phát triển Schedule Service - Lập lịch, scheduling, cron jobs, task scheduling, batch processing",
    "fraud detection": "Mục tiêu: Phát triển Fraud Detection Service - Phát hiện gian lận, fraud detection algorithms, risk scoring, fraud prevention",
}


def find_matching_remark(service_name):
    """Find matching remark for service name."""
    name_lower = service_name.lower()

    # Try exact matches first
    for key, remark in SERVICE_REMARKS_MAP.items():
        if key in name_lower:
            return remark

    # Try partial matches
    if "proposal" in name_lower:
        return SERVICE_REMARKS_MAP["proposal business"]
    elif "policy" in name_lower:
        return SERVICE_REMARKS_MAP["policy business"]
    elif "customer" in name_lower and "targeted" not in name_lower:
        return SERVICE_REMARKS_MAP["customer business"]
    elif "claim" in name_lower:
        return SERVICE_REMARKS_MAP["claim business"]
    elif "rating" in name_lower:
        return SERVICE_REMARKS_MAP["rating engine"]
    elif "underwriting" in name_lower:
        return SERVICE_REMARKS_MAP["underwriting"]
    elif "product" in name_lower and "catalog" in name_lower:
        return SERVICE_REMARKS_MAP["product catalog"]
    elif "rule" in name_lower and "engine" in name_lower:
        return SERVICE_REMARKS_MAP["business rules engine"]
    elif "config" in name_lower:
        return SERVICE_REMARKS_MAP["config platform"]
    elif "payment" in name_lower:
        return SERVICE_REMARKS_MAP["payment service"]
    elif "billing" in name_lower:
        return SERVICE_REMARKS_MAP["billing service"]
    elif "carrier" in name_lower or "insurer" in name_lower:
        return SERVICE_REMARKS_MAP.get(
            "insurer service",
            SERVICE_REMARKS_MAP.get("carrier integration", SERVICE_REMARKS_MAP.get("carrier")),
        )
    elif "orchestrator" in name_lower:
        return SERVICE_REMARKS_MAP["orchestrator"]
    elif "workflow" in name_lower:
        return SERVICE_REMARKS_MAP["workflow service"]
    elif "document" in name_lower:
        if "management" in name_lower:
            return SERVICE_REMARKS_MAP.get("document management", SERVICE_REMARKS_MAP["document service"])
        return SERVICE_REMARKS_MAP["document service"]
    elif "notification" in name_lower:
        if "spi" in name_lower:
            return SERVICE_REMARKS_MAP.get("notification spi", SERVICE_REMARKS_MAP["notification service"])
        return SERVICE_REMARKS_MAP["notification service"]
    elif "analytics" in name_lower:
        return SERVICE_REMARKS_MAP["analytics service"]
    elif "agent" in name_lower and "portal" not in name_lower:
        return SERVICE_REMARKS_MAP["agent business"]
    elif "cms" in name_lower:
        return SERVICE_REMARKS_MAP["cms be"]
    elif "intelligent recommendation" in name_lower:
        return SERVICE_REMARKS_MAP["intelligent recommendation"]
    elif "intelligent filtering" in name_lower:
        return SERVICE_REMARKS_MAP["intelligent filtering"]
    elif "targeted customer" in name_lower:
        return SERVICE_REMARKS_MAP["targeted customer"]

    return None


if __name__ == "__main__":
    wb = load_workbook(
        "../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx",
        read_only=False,
    )
    detail = wb["VDS_Est_Detail_Target_State"]

    print("=== Fixing Remarks to Match Service Names ===")

    updated_count = 0
    services = []

    # Get all service rows
    for row in range(10, 482):
        col2 = detail.cell(row, 2).value
        col3 = detail.cell(row, 3).value

        if col3 and isinstance(col2, (int, float)):
            service_name = str(col3)
            correct_remark = find_matching_remark(service_name)

            if correct_remark:
                current_remark = detail.cell(row, 6).value
                if current_remark != correct_remark:
                    detail.cell(row, 6).value = correct_remark
                    updated_count += 1
                    services.append(
                        {
                            "row": row,
                            "name": service_name[:50],
                            "old": (str(current_remark)[:60] if current_remark else "None"),
                            "new": correct_remark[:60],
                        }
                    )
            else:
                # Generic remark if not found
                service_key = service_name.split(":")[0].strip().replace("  ", "")
                detail.cell(row, 6).value = f"Mục tiêu: Phát triển {service_key}"
                updated_count += 1
                services.append(
                    {
                        "row": row,
                        "name": service_name[:50],
                        "old": "None",
                        "new": f"Mục tiêu: Phát triển {service_key}"[:60],
                    }
                )

    wb.save("../../docs-nttc/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx")

    print(f"\n✅ Updated {updated_count} service remarks")

    if services:
        print("\nUpdated services:")
        for svc in services[:10]:  # First 10
            print(f"\nRow {svc['row']}: {svc['name']}")
            print(f"  Old: {svc['old']}")
            print(f"  New: {svc['new']}")
