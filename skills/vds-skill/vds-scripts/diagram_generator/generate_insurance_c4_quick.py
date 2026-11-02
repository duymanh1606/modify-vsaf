#!/usr/bin/env python3
"""Quick C4 diagram generator for INSURANCE platform.

Generates L1, L2, and L3 C4 diagrams without full code analysis.
Uses predefined service configurations for faster generation.

Usage:
    cd vds-scripts/diagram_generator
    uv run python generate_insurance_c4_quick.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vds_diagram_generator.c4_generator import C4_INCLUDES, C4DiagramType, C4Generator

# Configuration
OUTPUT_BASE_PATH = Path(__file__).parent.parent.parent / "docs-nttc" / "projects" / "INSURANCE" / "analysis"
C4_OUTPUT_PATH = OUTPUT_BASE_PATH / "c4-diagrams"


# Service component configurations (simplified for quick generation)
SERVICE_CONFIGS = {
    "insurance-policy-business": {
        "controllers": ["PolicyController", "CancelPolicyController", "PrivateCancelPolicyController"],
        "services": ["PolicyServiceImpl", "CancelPolicyServiceImpl", "PolicyRenewalServiceImpl", "CacheServiceImpl"],
        "repositories": ["PolicyPeriodRepository", "PolicyRenewalRepository", "RequestTrackingRepository"],
        "feign_clients": ["PaymentClient", "InsurerClient", "ProposalClient", "NotificationSpiClient"],
        "kafka_handlers": ["EventConsumerHandler", "EventConsumerRenewalHandler"],
        "description": "Policy lifecycle management",
    },
    "insurance-claim-business": {
        "controllers": ["ClaimController", "ClaimInternalController"],
        "services": ["ClaimServiceImpl", "ClaimProcessServiceImpl", "ClaimValidationService"],
        "repositories": ["ClaimRepository", "ClaimDocumentRepository", "ClaimHistoryRepository"],
        "feign_clients": ["PolicyClient", "InsurerClient", "NotificationClient"],
        "kafka_handlers": ["ClaimEventHandler"],
        "description": "Claims processing and management",
    },
    "insurance-proposal-business": {
        "controllers": ["ProposalController", "ProposalInternalController", "QuotationController"],
        "services": ["ProposalServiceImpl", "QuotationServiceImpl", "PremiumCalculationService"],
        "repositories": ["ProposalRepository", "QuotationRepository", "ProposalDocumentRepository"],
        "feign_clients": ["InsurerClient", "CustomerClient", "PaymentClient"],
        "kafka_handlers": ["ProposalEventHandler"],
        "description": "Proposal and quotation management",
    },
    "insurance-customer-business": {
        "controllers": ["CustomerController", "CustomerInternalController"],
        "services": ["CustomerServiceImpl", "CustomerValidationService", "CustomerSyncService"],
        "repositories": ["CustomerRepository", "CustomerDocumentRepository"],
        "feign_clients": ["EkycClient", "NotificationClient"],
        "kafka_handlers": ["CustomerEventHandler"],
        "description": "Customer management",
    },
    "insurance-promotion-business": {
        "controllers": ["PromotionController", "CampaignController"],
        "services": ["PromotionServiceImpl", "CampaignServiceImpl", "VoucherService"],
        "repositories": ["PromotionRepository", "CampaignRepository", "VoucherRepository"],
        "feign_clients": ["CustomerClient", "NotificationClient"],
        "kafka_handlers": [],
        "description": "Campaigns and promotions",
    },
    "insurance-payment-service": {
        "controllers": ["PaymentController", "PaymentCallbackController"],
        "services": ["PaymentServiceImpl", "PaymentProcessService", "RefundService"],
        "repositories": ["PaymentRepository", "PaymentTransactionRepository"],
        "feign_clients": ["PayApp2Client", "PolicyClient"],
        "kafka_handlers": ["PaymentEventHandler"],
        "description": "Payment processing",
    },
    "insurance-payment-service-v2": {
        "controllers": ["PaymentV2Controller", "PaymentCallbackV2Controller"],
        "services": ["PaymentV2ServiceImpl", "PaymentProcessV2Service"],
        "repositories": ["PaymentV2Repository", "TransactionV2Repository"],
        "feign_clients": ["PayApp2Client", "PolicyClient", "ProposalClient"],
        "kafka_handlers": ["PaymentV2EventHandler"],
        "description": "Payment processing v2",
    },
    "insurance-reconcile-process": {
        "controllers": ["ReconcileController"],
        "services": ["ReconcileServiceImpl", "ReconcileProcessService", "ReconcileReportService"],
        "repositories": ["ReconcileRepository", "ReconcileLogRepository"],
        "feign_clients": ["PaymentClient", "InsurerClient"],
        "kafka_handlers": ["ReconcileEventHandler"],
        "description": "Financial reconciliation",
    },
    "insurance-insurer-service": {
        "controllers": ["InsurerController", "InsurerCallbackController"],
        "services": ["InsurerServiceImpl", "InsurerIntegrationService", "InsurerMappingService"],
        "repositories": ["InsurerRepository", "InsurerConfigRepository"],
        "feign_clients": ["InsuremoClient", "PVIClient", "BaoVietClient"],
        "kafka_handlers": ["InsurerEventHandler"],
        "description": "Insurer partner integrations",
    },
    "insurance-notification-spi": {
        "controllers": ["NotificationController"],
        "services": ["NotificationServiceImpl", "SmsService", "PushNotificationService", "EmailService"],
        "repositories": ["NotificationRepository", "NotificationTemplateRepository"],
        "feign_clients": ["SmsGatewayClient", "PushGatewayClient"],
        "kafka_handlers": ["NotificationEventHandler"],
        "description": "Notification delivery",
    },
    "insurance-ocr-service": {
        "controllers": ["OcrController"],
        "services": ["OcrServiceImpl", "DocumentExtractionService", "IdCardOcrService"],
        "repositories": ["OcrResultRepository"],
        "feign_clients": ["OcrProviderClient"],
        "kafka_handlers": [],
        "description": "Document OCR processing",
    },
    "insurance-authentication-sync-process": {
        "controllers": ["AuthSyncController"],
        "services": ["AuthSyncServiceImpl", "TokenSyncService"],
        "repositories": ["AuthTokenRepository"],
        "feign_clients": ["AuthProviderClient"],
        "kafka_handlers": ["AuthSyncEventHandler"],
        "description": "Authentication synchronization",
    },
    "insurance-auto-underwriting-process": {
        "controllers": ["UnderwritingController"],
        "services": ["UnderwritingServiceImpl", "RiskAssessmentService", "AutoApprovalService"],
        "repositories": ["UnderwritingRepository", "RiskRuleRepository"],
        "feign_clients": ["InsurerClient", "CustomerClient"],
        "kafka_handlers": ["UnderwritingEventHandler"],
        "description": "Auto underwriting",
    },
    "insurance-centralized-sync-service": {
        "controllers": ["SyncController"],
        "services": ["SyncServiceImpl", "DataSyncService", "SyncSchedulerService"],
        "repositories": ["SyncLogRepository", "SyncConfigRepository"],
        "feign_clients": ["PolicyClient", "ClaimClient", "CustomerClient"],
        "kafka_handlers": ["SyncEventHandler"],
        "description": "Centralized data sync",
    },
    "insurance-renewal-process": {
        "controllers": ["RenewalController"],
        "services": ["RenewalServiceImpl", "RenewalNotificationService", "RenewalProcessService"],
        "repositories": ["RenewalRepository", "RenewalLogRepository"],
        "feign_clients": ["PolicyClient", "PaymentClient", "NotificationClient"],
        "kafka_handlers": ["RenewalEventHandler"],
        "description": "Policy renewal processing",
    },
    "insurance-timeout-process": {
        "controllers": ["TimeoutController"],
        "services": ["TimeoutServiceImpl", "TimeoutProcessService"],
        "repositories": ["TimeoutLogRepository"],
        "feign_clients": ["PolicyClient", "ProposalClient", "PaymentClient"],
        "kafka_handlers": ["TimeoutEventHandler"],
        "description": "Timeout handling",
    },
    "insurance-job-scheduler": {
        "controllers": ["JobController", "SchedulerController"],
        "services": ["JobServiceImpl", "SchedulerServiceImpl", "QuartzJobService"],
        "repositories": ["JobRepository", "JobLogRepository"],
        "feign_clients": [],
        "kafka_handlers": ["JobEventHandler"],
        "description": "Scheduled jobs (Quartz)",
    },
    "insurance-cms-be": {
        "controllers": ["CmsController", "ContentController", "ConfigController"],
        "services": ["CmsServiceImpl", "ContentServiceImpl", "ConfigServiceImpl"],
        "repositories": ["ContentRepository", "ConfigRepository"],
        "feign_clients": [],
        "kafka_handlers": [],
        "description": "Content management",
    },
    "insurance-customer-webview": {
        "controllers": ["WebviewController", "PolicyWebviewController"],
        "services": ["WebviewServiceImpl", "PolicyDisplayService"],
        "repositories": [],
        "feign_clients": ["PolicyClient", "ClaimClient", "CustomerClient"],
        "kafka_handlers": [],
        "description": "Customer web interface",
    },
    "insurance-common": {
        "controllers": [],
        "services": ["CommonUtilService", "ValidationService", "MappingService"],
        "repositories": [],
        "feign_clients": [],
        "kafka_handlers": [],
        "description": "Common utilities library",
    },
    "insurance-insuremo-common": {
        "controllers": [],
        "services": ["InsuremoMappingService", "InsuremoValidationService"],
        "repositories": [],
        "feign_clients": [],
        "kafka_handlers": [],
        "description": "Insuremo integration utilities",
    },
    "insuremo-embedded-rule": {
        "controllers": [],
        "services": ["RuleEngineService", "RuleValidationService"],
        "repositories": ["RuleRepository"],
        "feign_clients": [],
        "kafka_handlers": [],
        "description": "Embedded rule engine",
    },
    "insurance-socialized-insurance-service": {
        "controllers": ["SocialInsuranceController"],
        "services": ["SocialInsuranceServiceImpl", "SocialInsuranceProcessService"],
        "repositories": ["SocialInsuranceRepository"],
        "feign_clients": ["SocialInsuranceProviderClient"],
        "kafka_handlers": ["SocialInsuranceEventHandler"],
        "description": "Social insurance integration",
    },
}


def safe_alias(name: str) -> str:
    """Convert a name to a safe PlantUML alias."""
    return name.replace(".", "_").replace("-", "_").replace(" ", "_").lower()


def generate_l3_component_diagram(service_name: str, config: dict) -> str:
    """Generate L3 Component diagram for a service."""
    service_alias = safe_alias(service_name)
    title = f"{service_name} - Component Diagram (Level 3)"

    lines = [
        "@startuml",
        C4_INCLUDES[C4DiagramType.COMPONENT],
        "",
        f"title {title}",
        "",
    ]

    # External containers
    lines.append("' External Containers")
    lines.append('Container_Ext(api_gateway, "API Gateway", "Spring Cloud Gateway", "Routes requests")')
    lines.append('ContainerDb_Ext(mariadb, "MariaDB", "MariaDB", "Primary database")')
    lines.append('ContainerDb_Ext(redis, "Redis", "Redis", "Cache layer")')

    if config["kafka_handlers"]:
        lines.append('ContainerQueue_Ext(kafka, "Kafka", "Apache Kafka", "Event streaming")')

    if config["feign_clients"]:
        lines.append('System_Ext(external_services, "External Services", "Partner services")')

    lines.append("")

    # Container boundary
    lines.append(f'Container_Boundary({service_alias}, "{service_name}") {{')

    # Controllers
    if config["controllers"]:
        lines.append("    ' REST Controllers")
        for ctrl in config["controllers"]:
            alias = safe_alias(ctrl)
            lines.append(f'    Component({alias}, "{ctrl}", "Spring REST Controller", "Handles API requests")')

    # Services
    if config["services"]:
        lines.append("    ' Business Services")
        for svc in config["services"]:
            alias = safe_alias(svc)
            lines.append(f'    Component({alias}, "{svc}", "Spring Service", "Business logic")')

    # Repositories
    if config["repositories"]:
        lines.append("    ' Repositories")
        for repo in config["repositories"]:
            alias = safe_alias(repo)
            lines.append(f'    ComponentDb({alias}, "{repo}", "Spring Data JPA", "Data access")')

    # Feign clients
    if config["feign_clients"]:
        lines.append("    ' Feign Clients")
        for feign in config["feign_clients"]:
            alias = safe_alias(feign)
            lines.append(f'    Component({alias}, "{feign}", "Feign Client", "External calls")')

    # Kafka handlers
    if config["kafka_handlers"]:
        lines.append("    ' Kafka Handlers")
        for handler in config["kafka_handlers"]:
            alias = safe_alias(handler)
            lines.append(f'    Component({alias}, "{handler}", "Spring Kafka", "Event handling")')

    lines.append("}")
    lines.append("")

    # Relationships
    lines.append("' Relationships")

    # API Gateway -> Controllers
    for ctrl in config["controllers"]:
        ctrl_alias = safe_alias(ctrl)
        lines.append(f'Rel(api_gateway, {ctrl_alias}, "Routes requests", "REST")')

    # Controllers -> Services
    for ctrl in config["controllers"]:
        ctrl_alias = safe_alias(ctrl)
        for svc in config["services"][:2]:  # Limit connections
            svc_alias = safe_alias(svc)
            lines.append(f'Rel({ctrl_alias}, {svc_alias}, "Delegates to")')

    # Services -> Repositories
    for svc in config["services"][:2]:
        svc_alias = safe_alias(svc)
        for repo in config["repositories"]:
            repo_alias = safe_alias(repo)
            lines.append(f'Rel({svc_alias}, {repo_alias}, "Queries/Persists")')

    # Services -> Feign Clients
    for svc in config["services"][:1]:
        svc_alias = safe_alias(svc)
        for feign in config["feign_clients"]:
            feign_alias = safe_alias(feign)
            lines.append(f'Rel({svc_alias}, {feign_alias}, "Invokes")')

    # Kafka Handlers -> Services
    for handler in config["kafka_handlers"]:
        handler_alias = safe_alias(handler)
        if config["services"]:
            svc_alias = safe_alias(config["services"][0])
            lines.append(f'Rel({handler_alias}, {svc_alias}, "Processes events")')

    lines.append("")
    lines.append("' External Relationships")

    # Repositories -> Database
    for repo in config["repositories"]:
        repo_alias = safe_alias(repo)
        lines.append(f'Rel({repo_alias}, mariadb, "JDBC")')

    # Services -> Redis
    for svc in config["services"][:1]:
        svc_alias = safe_alias(svc)
        lines.append(f'Rel({svc_alias}, redis, "Caches")')

    # Feign Clients -> External
    for feign in config["feign_clients"]:
        feign_alias = safe_alias(feign)
        lines.append(f'Rel({feign_alias}, external_services, "HTTP/REST")')

    # Kafka Handlers -> Kafka
    for handler in config["kafka_handlers"]:
        handler_alias = safe_alias(handler)
        lines.append(f'Rel({handler_alias}, kafka, "Consumes")')

    lines.append("")
    lines.append("SHOW_LEGEND()")
    lines.append("@enduml")

    return "\n".join(lines)


def main():
    """Main entry point."""
    print("=" * 60)
    print("INSURANCE Platform C4 Diagram Generator (Quick)")
    print("=" * 60)

    # Create output directory
    C4_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {C4_OUTPUT_PATH}")

    # Initialize generator
    generator = C4Generator(OUTPUT_BASE_PATH)

    # Generate L1 System Context diagram
    print("\n📊 Generating L1 System Context diagram...")
    l1_path = generator.save_l1_context_diagram("INSURANCE", C4_OUTPUT_PATH, include_cross_platform=True)
    print(f"   ✅ Created: {l1_path.name}")

    # Generate L2 Container diagram
    print("\n📊 Generating L2 Container diagram...")
    l2_path = generator.save_l2_container_diagram("INSURANCE", C4_OUTPUT_PATH)
    print(f"   ✅ Created: {l2_path.name}")

    # Generate L3 Component diagrams
    print("\n📊 Generating L3 Component diagrams...")
    l3_paths = []
    for service_name, config in SERVICE_CONFIGS.items():
        content = generate_l3_component_diagram(service_name, config)
        filename = f"L3-{service_name}-components.puml"
        output_path = C4_OUTPUT_PATH / filename
        output_path.write_text(content, encoding="utf-8")
        l3_paths.append(output_path)
        print(f"   ✅ Created: {filename}")

    # Create README
    print("\n📝 Creating README.md...")
    readme_content = create_readme(l3_paths)
    readme_path = C4_OUTPUT_PATH / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    print("   ✅ Created: README.md")

    # Summary
    print("\n" + "=" * 60)
    print("✅ INSURANCE C4 Diagram Generation Complete!")
    print("=" * 60)
    print("\nGenerated diagrams:")
    print("  - L1 System Context: 1")
    print("  - L2 Container: 1")
    print(f"  - L3 Component: {len(l3_paths)}")
    print(f"  - Total: {2 + len(l3_paths)}")
    print(f"\nOutput location: {C4_OUTPUT_PATH}")

    return 0


def create_readme(l3_paths: list[Path]) -> str:
    """Create README content."""
    content = """# INSURANCE Platform - C4 Architecture Diagrams

## Overview

This directory contains C4 model architecture diagrams for the INSURANCE Platform using PlantUML with the [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) library.

## C4 Model Levels

| Level | Name | Description | Audience |
|-------|------|-------------|----------|
| 1 | System Context | Shows the system and its relationships with users and external systems | Everyone |
| 2 | Container | Zooms into the system showing containers (applications, data stores) | Technical people |
| 3 | Component | Zooms into a container showing its internal components | Developers |

## Diagram Files

### Level 1 - System Context
| File | Description |
|------|-------------|
| [L1-insurance-platform-context.puml](L1-insurance-platform-context.puml) | Overall system context showing INSURANCE Platform and external systems |

### Level 2 - Container
| File | Description |
|------|-------------|
| [L2-insurance-platform-containers.puml](L2-insurance-platform-containers.puml) | All 23 microservices and infrastructure components |

### Level 3 - Component (per service)
| File | Service | Description |
|------|---------|-------------|
"""

    for path in sorted(l3_paths):
        service_name = path.stem.replace("L3-", "").replace("-components", "")
        desc = SERVICE_CONFIGS.get(service_name, {}).get("description", "Internal components")
        content += f"| [{path.name}]({path.name}) | {service_name} | {desc} |\n"

    content += f"""
## How to Render

### Using PlantUML Online Server
1. Go to https://www.plantuml.com/plantuml/uml/
2. Paste the diagram content
3. View/download the rendered diagram

### Using VS Code
1. Install the "PlantUML" extension
2. Open any `.puml` file
3. Press `Alt+D` to preview

### Using CLI
```bash
plantuml *.puml
```

## Cross-Project Consistency

These diagrams follow the same C4 patterns established in the SAVING Platform:
- See `docs-nttc/projects/SAVING/analysis/c4-diagrams/` for reference
- Consistent styling and element usage across VDS platforms

## Diagram Statistics

| Level | Count | Status |
|-------|-------|--------|
| Level 1 - Context | 1 | ✅ Complete |
| Level 2 - Container | 1 | ✅ Complete |
| Level 3 - Component | {len(l3_paths)} | ✅ Complete |
| **Total** | **{2 + len(l3_paths)}** | **100%** |

---
**Last Updated**: 2025-11-28
"""
    return content


if __name__ == "__main__":
    sys.exit(main())
