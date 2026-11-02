"""Property-based tests for component coverage.

**Feature: insurance-diagram-accuracy, Property 2: Component Coverage**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

For any service in the INSURANCE platform, the generated component diagram SHALL include
all controller classes, service implementation classes, and repository interfaces found
in the source code.
"""

import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st
from vds_diagram_generator.generator import PlantUMLGenerator
from vds_diagram_generator.models import (
    ControllerInfo,
    EndpointInfo,
    FeignClientInfo,
    KafkaHandlerInfo,
    RepositoryInfo,
    ServiceAnalysis,
    ServiceInfo,
)

# Strategies for generating test data
endpoint_strategy = st.builds(
    EndpointInfo,
    method=st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
    path=st.text(alphabet="abcdefghijklmnopqrstuvwxyz/-_{}", min_size=1, max_size=50).map(lambda s: "/" + s),
    method_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=3, max_size=30),
    service_method=st.none() | st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20),
)

controller_strategy = st.builds(
    ControllerInfo,
    class_name=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=30).map(
        lambda s: s + "Controller"
    ),
    base_path=st.text(alphabet="abcdefghijklmnopqrstuvwxyz/-", min_size=0, max_size=30),
    endpoints=st.lists(endpoint_strategy, min_size=1, max_size=5),
)

service_strategy = st.builds(
    ServiceInfo,
    class_name=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=30).map(
        lambda s: s + "ServiceImpl"
    ),
    interface_name=st.none()
    | st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25).map(
        lambda s: s + "Service"
    ),
    methods=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20), min_size=1, max_size=10),
    dependencies=st.lists(
        st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=20),
        min_size=0,
        max_size=5,
    ),
)

repository_strategy = st.builds(
    RepositoryInfo,
    interface_name=st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25
    ).map(lambda s: s + "Repository"),
    entity_type=st.none()
    | st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20),
    custom_methods=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25), min_size=0, max_size=5
    ),
)

feign_client_strategy = st.builds(
    FeignClientInfo,
    interface_name=st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25
    ).map(lambda s: s + "Client"),
    target_service=st.text(alphabet="abcdefghijklmnopqrstuvwxyz-", min_size=5, max_size=30),
    methods=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20), min_size=1, max_size=5),
)

kafka_handler_strategy = st.builds(
    KafkaHandlerInfo,
    class_name=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25).map(
        lambda s: s + "Handler"
    ),
    topics=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz.-_", min_size=5, max_size=30), min_size=1, max_size=3),
    methods=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20), min_size=1, max_size=3),
)

service_analysis_strategy = st.builds(
    ServiceAnalysis,
    service_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz-", min_size=10, max_size=40),
    controllers=st.lists(controller_strategy, min_size=1, max_size=3),
    services=st.lists(service_strategy, min_size=1, max_size=3),
    repositories=st.lists(repository_strategy, min_size=1, max_size=3),
    feign_clients=st.lists(feign_client_strategy, min_size=0, max_size=3),
    kafka_handlers=st.lists(kafka_handler_strategy, min_size=0, max_size=2),
)


class TestComponentCoverage:
    """Property tests for component coverage.

    **Feature: insurance-diagram-accuracy, Property 2: Component Coverage**
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_component_diagram_includes_all_controllers(self, analysis: ServiceAnalysis) -> None:
        """Property: All controller classes appear in the component diagram.

        **Validates: Requirements 2.1** - WHEN a component diagram is generated
        THEN the Diagram Generator SHALL include all actual controller classes.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())
        diagram = generator.generate_component_diagram(analysis)

        for controller in analysis.controllers:
            assert controller.class_name in diagram, (
                f"Controller {controller.class_name} not found in component diagram"
            )

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_component_diagram_includes_all_services(self, analysis: ServiceAnalysis) -> None:
        """Property: All service implementation classes appear in the component diagram.

        **Validates: Requirements 2.2** - WHEN a component diagram is generated
        THEN the Diagram Generator SHALL include all actual service implementation classes.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())
        diagram = generator.generate_component_diagram(analysis)

        for service in analysis.services:
            assert service.class_name in diagram, f"Service {service.class_name} not found in component diagram"

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_component_diagram_includes_all_repositories(self, analysis: ServiceAnalysis) -> None:
        """Property: All repository interfaces appear in the component diagram.

        **Validates: Requirements 2.3** - WHEN a component diagram is generated
        THEN the Diagram Generator SHALL include all repository interfaces.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())
        diagram = generator.generate_component_diagram(analysis)

        for repo in analysis.repositories:
            assert repo.interface_name in diagram, f"Repository {repo.interface_name} not found in component diagram"

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_component_diagram_includes_all_feign_clients(self, analysis: ServiceAnalysis) -> None:
        """Property: All Feign client interfaces appear in the component diagram.

        **Validates: Requirements 2.4** - WHEN a component diagram is generated
        THEN the Diagram Generator SHALL show actual external service dependencies.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())
        diagram = generator.generate_component_diagram(analysis)

        for feign in analysis.feign_clients:
            assert feign.interface_name in diagram, (
                f"Feign client {feign.interface_name} not found in component diagram"
            )

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_component_diagram_shows_database_connection(self, analysis: ServiceAnalysis) -> None:
        """Property: Component diagram shows database connection when repositories exist.

        **Validates: Requirements 2.3** - Repositories should connect to database.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())
        diagram = generator.generate_component_diagram(analysis)

        if analysis.repositories:
            assert "MariaDB" in diagram or "db" in diagram, (
                "Database connection not shown in component diagram with repositories"
            )
