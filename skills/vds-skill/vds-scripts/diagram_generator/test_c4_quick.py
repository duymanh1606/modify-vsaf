#!/usr/bin/env python3
"""Quick test for C4 generator hierarchical diagram generation."""

import sys

sys.path.insert(0, "src")

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
    assert "Rel(" in content
    assert "SHOW_LEGEND()" in content
    assert "@enduml" in content
    print("✓ L1 Context diagram generation works")
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
    print("✓ L2 Container diagram generation works")
    return content


def test_l3_component():
    """Test L3 Component diagram generation."""
    generator = C4Generator("/tmp/test-diagrams")

    analysis = ServiceAnalysis(
        service_name="insurance-policy-business",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="/api/v1/policies",
                endpoints=[
                    EndpointInfo(method="GET", path="/policies", method_name="getPolicies"),
                ],
            )
        ],
        services=[ServiceInfo(class_name="PolicyService", methods=["findAll", "create"])],
        repositories=[RepositoryInfo(interface_name="PolicyRepository", entity_type="Policy")],
        feign_clients=[FeignClientInfo(interface_name="PaymentClient", target_service="payment-service")],
        kafka_handlers=[KafkaHandlerInfo(class_name="PolicyEventHandler", topics=["policy-events"])],
    )

    content = generator.generate_l3_component_diagram(analysis)

    # Verify key elements
    assert "@startuml" in content
    assert "C4_Component.puml" in content
    assert "Component(" in content
    assert "ComponentDb(" in content
    assert "Container_Boundary(" in content
    print("✓ L3 Component diagram generation works")
    return content


def test_dynamic():
    """Test C4 Dynamic diagram generation."""
    generator = C4Generator("/tmp/test-diagrams")

    analysis = ServiceAnalysis(
        service_name="insurance-policy-business",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                endpoints=[
                    EndpointInfo(method="POST", path="/policies", method_name="createPolicy"),
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
    print("✓ Dynamic diagram generation works")
    return content


if __name__ == "__main__":
    print("Testing C4 Hierarchical Diagram Generation...")
    print()

    l1 = test_l1_context()
    l2 = test_l2_container()
    l3 = test_l3_component()
    dyn = test_dynamic()

    print()
    print("All tests passed!")
    print()
    print("=== Sample L1 Output (first 800 chars) ===")
    print(l1[:800])
