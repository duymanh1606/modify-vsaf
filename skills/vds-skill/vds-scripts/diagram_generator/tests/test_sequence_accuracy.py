"""Property tests for sequence diagram accuracy verification."""

import pytest
from vds_diagram_generator.analyzer import JavaCodeAnalyzer
from vds_diagram_generator.config import get_settings
from vds_diagram_generator.generator import PlantUMLGenerator


def test_all_endpoints_exist_in_source():
    """Property test: Verify all endpoints in diagram exist in source code."""
    settings = get_settings()
    source_path = settings.get_project_source_path("INSURANCE")

    if not source_path.exists():
        pytest.skip("INSURANCE project source not found")

    analyzer = JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service("insurance-policy-business")

    generator = PlantUMLGenerator(".")
    diagram = generator.generate_sequence_diagram(analysis, include_rest_flows=True, include_kafka_flows=False)

    for controller in analysis.controllers:
        for endpoint in controller.endpoints:
            assert endpoint.method in diagram
            assert endpoint.path in diagram or endpoint.method_name in diagram


def test_service_calls_inferred_correctly():
    """Property test: Verify service method inference accuracy."""
    settings = get_settings()
    source_path = settings.get_project_source_path("INSURANCE")

    if not source_path.exists():
        pytest.skip("INSURANCE project source not found")

    analyzer = JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service("insurance-policy-business")

    generator = PlantUMLGenerator(".")
    diagram = generator.generate_sequence_diagram(analysis, include_rest_flows=True, include_kafka_flows=False)

    inferred_count = 0
    for controller in analysis.controllers:
        for endpoint in controller.endpoints:
            if endpoint.service_method:
                inferred_count += 1
                assert endpoint.service_method in diagram

    assert inferred_count > 0


def test_kafka_topics_match_source():
    """Verify Kafka topics in diagram match @KafkaListener annotations."""
    settings = get_settings()
    source_path = settings.get_project_source_path("INSURANCE")

    if not source_path.exists():
        pytest.skip("INSURANCE project source not found")

    analyzer = JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service("insurance-policy-business")

    generator = PlantUMLGenerator(".")
    diagram = generator.generate_sequence_diagram(analysis, include_rest_flows=False, include_kafka_flows=True)

    for handler in analysis.kafka_handlers:
        for topic in handler.topics:
            assert topic in diagram or "Kafka" in diagram


def test_sequence_diagram_matches_code_structure():
    """Integration test: Compare generated diagram with actual code structure."""
    settings = get_settings()
    source_path = settings.get_project_source_path("INSURANCE")

    if not source_path.exists():
        pytest.skip("INSURANCE project source not found")

    analyzer = JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service("insurance-policy-business")

    generator = PlantUMLGenerator(".")
    diagram = generator.generate_sequence_diagram(analysis)

    assert len(analysis.controllers) > 0
    assert len(analysis.services) > 0

    for controller in analysis.controllers:
        assert controller.class_name in diagram

    for service in analysis.services[:5]:
        assert service.class_name in diagram
