from pathlib import Path

from vds_diagram_generator.mermaid_generator import MermaidGenerator
from vds_diagram_generator.models import (
    ControllerInfo,
    EndpointInfo,
    KafkaHandlerInfo,
    RepositoryInfo,
    ServiceAnalysis,
    ServiceInfo,
)


def _sample_analysis() -> ServiceAnalysis:
    return ServiceAnalysis(
        service_name="sample-service",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="/policy",
                endpoints=[
                    EndpointInfo(
                        method="GET",
                        path="/policy/{id}",
                        method_name="getPolicy",
                        service_method="fetchPolicy",
                        service_class="PolicyServiceImpl",
                    )
                ],
            )
        ],
        services=[
            ServiceInfo(
                class_name="PolicyServiceImpl",
                interface_name="PolicyService",
                methods=["fetchPolicy"],
                dependencies=[],
            )
        ],
        repositories=[
            RepositoryInfo(
                interface_name="PolicyRepository",
                entity_type="Policy",
                custom_methods=["findById"],
            )
        ],
        feign_clients=[],
        kafka_handlers=[
            KafkaHandlerInfo(
                class_name="EventConsumerHandler",
                topics=["policy-event"],
                methods=["processEvent"],
            )
        ],
    )


def test_mermaid_sequence_diagram_contains_participants(tmp_path: Path) -> None:
    analysis = _sample_analysis()
    generator = MermaidGenerator(tmp_path)

    content = generator.generate_sequence_diagram(analysis)

    assert "sequenceDiagram" in content
    assert 'participant PolicyController as "PolicyController <<Controller>>"' in content
    assert "Client->>PolicyController" in content
    assert "Kafka->>EventConsumerHandler" in content


def test_mermaid_files_written(tmp_path: Path) -> None:
    analysis = _sample_analysis()
    generator = MermaidGenerator(tmp_path)

    seq_path, comp_path = generator.save_diagrams(analysis, tmp_path)

    assert seq_path.exists()
    assert comp_path.exists()
    assert seq_path.suffix == ".mmd"
    assert comp_path.suffix == ".mmd"
    assert "graph TD" in comp_path.read_text(encoding="utf-8")
