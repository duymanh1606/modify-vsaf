"""Property tests for C4 diagram generation.

**Feature: insurance-diagram-accuracy, Property 5: C4 Compliance**
**Validates: Requirements 17.1, 17.4, 19.1**

Ensures the C4 generator emits valid C4-PlantUML syntax, preserves hierarchy
relationships, and covers every architectural element from the analysis graph.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

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


def _sample_analysis() -> ServiceAnalysis:
    """Create a representative service analysis graph for testing."""

    controller = ControllerInfo(
        class_name="PolicyController",
        base_path="/policy",
        endpoints=[
            EndpointInfo(method="GET", path="/policy/{id}", method_name="getPolicy", service_method="findPolicy"),
        ],
    )
    service = ServiceInfo(
        class_name="PolicyServiceImpl",
        interface_name="PolicyService",
        methods=["findPolicy"],
        dependencies=["PolicyRepository"],
    )
    repository = RepositoryInfo(
        interface_name="PolicyRepository",
        entity_type="PolicyEntity",
        custom_methods=["findByPolicyNumber"],
    )
    feign = FeignClientInfo(
        interface_name="InsurerClient",
        target_service="insurer-service",
        methods=["getInsurer"],
    )
    kafka_handler = KafkaHandlerInfo(
        class_name="PolicyEventHandler",
        topics=["policy.events"],
        methods=["handlePolicyEvent"],
    )

    return ServiceAnalysis(
        service_name="insurance-policy-business",
        controllers=[controller],
        services=[service],
        repositories=[repository],
        feign_clients=[feign],
        kafka_handlers=[kafka_handler],
    )


class TestC4SyntaxCorrectness:
    """Tests for Property 5: C4 Compliance (task 19.1)."""

    def test_c4_component_diagram_contains_required_macros(self) -> None:
        """C4 component diagrams shall include stdlib header, legend, and boundaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = C4Generator(Path(tmpdir))
            diagram = generator.generate_l3_component_diagram(_sample_analysis())

        assert "@startuml" in diagram
        assert (
            "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml" in diagram
        )
        assert "Container_Boundary" in diagram
        assert "SHOW_LEGEND()" in diagram
        assert "@enduml" in diagram

    def test_c4_dynamic_diagram_enables_sequence_index(self) -> None:
        """Dynamic diagrams shall provide SHOW_INDEX() for numbered flows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = C4Generator(Path(tmpdir))
            diagram = generator.generate_c4_dynamic_diagram(_sample_analysis())

        assert (
            "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Dynamic.puml" in diagram
        )
        assert "SHOW_INDEX()" in diagram
        # Ensure numbered RelIndex entries exist
        assert "RelIndex(" in diagram

    def test_c4_hierarchy_generation_outputs_expected_files(self) -> None:
        """Full hierarchical generation shall emit L1, L2, L3, and dynamic diagrams."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            output_dir = base_path / "c4-diagrams"
            generator = C4Generator(base_path)
            result = generator.generate_all_hierarchical_diagrams(
                platform="INSURANCE",
                analyses=[_sample_analysis()],
                output_dir=output_dir,
            )

            assert set(result.keys()) == {"l1_context", "l2_container", "l3_component", "dynamic"}
            assert len(result["l1_context"]) == 1
            assert len(result["l2_container"]) == 1
            assert len(result["l3_component"]) == 1
            assert len(result["dynamic"]) == 1

            expected_files = {
                "L1-insurance-platform-context.puml",
                "L2-insurance-platform-containers.puml",
                "L3-insurance-policy-business-components.puml",
                "insurance-policy-business-c4-dynamic.puml",
            }
            actual_files = {p.name for p in output_dir.iterdir()}
            assert expected_files <= actual_files, (
                f"Generated files mismatch.\nExpected at least: {expected_files}\nActual: {actual_files}"
            )

    def test_c4_component_diagram_covers_all_elements(self) -> None:
        """Every analyzed element SHALL appear in the L3 component diagram."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = C4Generator(Path(tmpdir))
            diagram = generator.generate_l3_component_diagram(_sample_analysis())

        assert "PolicyController" in diagram
        assert "PolicyServiceImpl" in diagram
        assert "PolicyRepository" in diagram
        assert "InsurerClient" in diagram
        assert "PolicyEventHandler" in diagram
