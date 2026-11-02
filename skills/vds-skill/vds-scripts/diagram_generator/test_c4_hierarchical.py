#!/usr/bin/env python3
"""Quick test for C4 hierarchical diagram generation."""

from vds_diagram_generator.c4_generator import C4Generator
from vds_diagram_generator.models import (
    ControllerInfo,
    EndpointInfo,
    FeignClientInfo,
    KafkaHandlerInfo,
    RepositoryInfo,
    ServiceAnalysis,
    ServiceInfo,
)


def test_l1_context():
    """Test L1 System Context diagram generation."""
    generator = C4Generator("/tmp/test-diagrams")
    content = generator.generate_l1_context_diagram("INSURANCE")

    # Verify key elements
    assert "@startuml" in content
    assert "C4_Context.puml" in content
    assert "Person(" in content
    assert "System(" in content
    assert "System_Ext(" in content
    assert "INSURANCE Platform" in content
    assert "SHOW_LEGEND()" in content
    print("✓ L1 Context diagram test passed")
    return content


def test_l2_container():
    """Test L2 Container diagram generation."""
    generator = C4Generator("/tmp/test-diagrams")
    content = generator.generate_l2_container_diagram("INSURANCE")

    # Verify key elements
    assert "@startuml" in content
    assert "C4_Container.puml" in content
    assert "Container(" in content
    assert "ContainerDb(" in content
    assert "ContainerQueue(" in content
    assert "System_Boundary(" in content
    print("✓ L2 Container diagram test passed")
    return content


def test_l3_component():
    """Test L3 Component diagram generation."""
    generator = C4Generator("/tmp/test-diagrams")

    # Create sample analysis
    analysis = ServiceAnalysis(
        service_name="insurance-policy-business",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="/api/v1/policies",
                endpoints=[
                    EndpointInfo(
                        method="GET", path="/api/v1/policies", method_name="getPolicies", service_method="findAll"
                    ),
                ],
            )
        ],
        services=[
            ServiceInfo(class_name="PolicyService", interface_name="IPolicyService", methods=["findAll", "create"])
        ],
        repositories=[
            RepositoryInfo(interface_name="PolicyRepository", entity_type="Policy", custom_methods=["findByCustomerId"])
        ],
        feign_clients=[
            FeignClientInfo(interface_name="PaymentClient", target_service="insurance-payment-service", methods=["pay"])
        ],
        kafka_handlers=[
            KafkaHandlerInfo(class_name="PolicyEventHandler", topics=["policy-events"], methods=["handle"])
        ],
    )

    content = generator.generate_l3_component_diagram(analysis)

    # Verify key elements
    assert "@startuml" in content
    assert "C4_Component.puml" in content
    assert "Component(" in content
    assert "ComponentDb(" in content
    assert "Container_Boundary(" in content
    assert "PolicyController" in content
    assert "PolicyService" in content
    print("✓ L3 Component diagram test passed")
    return content


def test_dynamic_diagram():
    """Test C4 Dynamic diagram generation."""
    generator = C4Generator("/tmp/test-diagrams")

    analysis = ServiceAnalysis(
        service_name="insurance-policy-business",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="/api/v1/policies",
                endpoints=[
                    EndpointInfo(
                        method="POST", path="/api/v1/policies", method_name="createPolicy", service_method="create"
                    ),
                ],
            )
        ],
        services=[ServiceInfo(class_name="PolicyService", methods=["create"])],
        repositories=[RepositoryInfo(interface_name="PolicyRepository", entity_type="Policy")],
        kafka_handlers=[KafkaHandlerInfo(class_name="PolicyEventHandler", topics=["policy-events"])],
    )

    content = generator.generate_c4_dynamic_diagram(analysis)

    # Verify key elements
    assert "@startuml" in content
    assert "C4_Dynamic.puml" in content
    assert "SHOW_INDEX()" in content
    assert "RelIndex(" in content
    assert "Rel_Back(" in content
    print("✓ Dynamic diagram test passed")
    return content


if __name__ == "__main__":
    print("Testing C4 Hierarchical Diagram Generation...")
    print()

    l1 = test_l1_context()
    l2 = test_l2_container()
    l3 = test_l3_component()
    dyn = test_dynamic_diagram()

    print()
    print("All tests passed! ✓")
    print()
    print("=== Sample L1 Output (first 800 chars) ===")
    print(l1[:800])
