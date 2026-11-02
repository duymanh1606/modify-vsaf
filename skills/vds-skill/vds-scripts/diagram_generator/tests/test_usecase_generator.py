"""Property tests for use case diagram generation."""

from vds_diagram_generator.models import (
    ControllerInfo,
    EndpointInfo,
    FeignClientInfo,
    ServiceAnalysis,
)
from vds_diagram_generator.usecase_generator import UseCaseGenerator


def test_actor_extraction_from_feign_clients():
    """Verify external actors extracted from Feign clients."""
    analysis = ServiceAnalysis(
        service_name="test-service",
        controllers=[],
        services=[],
        repositories=[],
        feign_clients=[
            FeignClientInfo(interface_name="PaymentClient", target_service="payment-service", methods=[]),
            FeignClientInfo(interface_name="NotificationClient", target_service="notification-service", methods=[]),
        ],
        kafka_handlers=[],
    )

    generator = UseCaseGenerator(".")
    actors = generator._extract_actors(analysis)

    actor_names = {actor[0] for actor in actors}
    assert "Client" in actor_names
    assert "payment-service" in actor_names
    assert "notification-service" in actor_names


def test_actor_extraction_from_controllers():
    """Verify internal actors from controller names."""
    analysis = ServiceAnalysis(
        service_name="test-service",
        controllers=[
            ControllerInfo(class_name="PolicyController", base_path="", endpoints=[], dependencies=[]),
            ControllerInfo(class_name="AdminController", base_path="", endpoints=[], dependencies=[]),
        ],
        services=[],
        repositories=[],
        feign_clients=[],
        kafka_handlers=[],
    )

    generator = UseCaseGenerator(".")
    actors = generator._extract_actors(analysis)

    actor_names = {actor[0] for actor in actors}
    assert "Client" in actor_names
    assert "Policy" in actor_names
    assert "Admin" in actor_names


def test_default_client_actor():
    """Verify 'Client' actor always present."""
    analysis = ServiceAnalysis(
        service_name="test-service",
        controllers=[],
        services=[],
        repositories=[],
        feign_clients=[],
        kafka_handlers=[],
    )

    generator = UseCaseGenerator(".")
    actors = generator._extract_actors(analysis)

    actor_names = {actor[0] for actor in actors}
    assert "Client" in actor_names
    assert len(actors) == 1


def test_use_case_extraction_from_endpoints():
    """Verify endpoint → use case mapping."""
    analysis = ServiceAnalysis(
        service_name="test-service",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="",
                endpoints=[
                    EndpointInfo(method="GET", path="/policy/{id}", method_name="getPolicy"),
                    EndpointInfo(method="POST", path="/policy", method_name="createPolicy"),
                ],
                dependencies=[],
            ),
        ],
        services=[],
        repositories=[],
        feign_clients=[],
        kafka_handlers=[],
    )

    generator = UseCaseGenerator(".")
    use_cases = generator._extract_use_cases(analysis, group_by="controller")

    assert "PolicyController" in use_cases
    use_case_names = {uc[0] for uc in use_cases["PolicyController"]}
    assert "GET /policy/{id}" in use_case_names
    assert "POST /policy" in use_case_names


def test_use_case_grouping_by_controller():
    """Verify grouping works correctly."""
    analysis = ServiceAnalysis(
        service_name="test-service",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="",
                endpoints=[EndpointInfo(method="GET", path="/policy", method_name="getPolicy")],
                dependencies=[],
            ),
            ControllerInfo(
                class_name="AdminController",
                base_path="",
                endpoints=[EndpointInfo(method="GET", path="/admin", method_name="getAdmin")],
                dependencies=[],
            ),
        ],
        services=[],
        repositories=[],
        feign_clients=[],
        kafka_handlers=[],
    )

    generator = UseCaseGenerator(".")
    use_cases = generator._extract_use_cases(analysis, group_by="controller")

    assert "PolicyController" in use_cases
    assert "AdminController" in use_cases
    assert len(use_cases["PolicyController"]) == 1
    assert len(use_cases["AdminController"]) == 1


def test_relationship_mapping():
    """Verify actor → use case relationships."""
    analysis = ServiceAnalysis(
        service_name="test-service",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="",
                endpoints=[
                    EndpointInfo(
                        method="GET",
                        path="/policy",
                        method_name="getPolicy",
                        service_method="getPolicyById",
                        service_class="PolicyService",
                    ),
                ],
                dependencies=[],
            ),
        ],
        services=[],
        repositories=[],
        feign_clients=[],
        kafka_handlers=[],
    )

    generator = UseCaseGenerator(".")
    actors = generator._extract_actors(analysis)
    use_cases = generator._extract_use_cases(analysis, group_by="controller")
    relationships = generator._generate_relationships(analysis, actors, use_cases)

    rel_str = " ".join(relationships)
    assert "Policy -->" in rel_str or "Client -->" in rel_str
    assert "GET /policy" in rel_str or "GET__policy" in rel_str


def test_plantuml_syntax_valid():
    """Verify generated PlantUML syntax is valid."""
    analysis = ServiceAnalysis(
        service_name="test-service",
        controllers=[
            ControllerInfo(
                class_name="PolicyController",
                base_path="",
                endpoints=[EndpointInfo(method="GET", path="/policy", method_name="getPolicy")],
                dependencies=[],
            ),
        ],
        services=[],
        repositories=[],
        feign_clients=[],
        kafka_handlers=[],
    )

    generator = UseCaseGenerator(".")
    diagram = generator.generate_use_case_diagram(analysis)

    assert "@startuml" in diagram
    assert "@enduml" in diagram
    assert "title" in diagram
    assert "actor" in diagram
    assert "usecase" in diagram or "package" in diagram
