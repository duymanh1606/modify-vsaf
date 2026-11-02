"""Property-based tests for style consistency.

**Feature: insurance-diagram-accuracy, Property 3: Style Consistency**
**Validates: Requirements 3.1, 3.2, 3.3**

For any generated diagram, the PlantUML source SHALL include the standard style definitions
and follow the naming convention `{service-name}-{type}.puml`.
"""

import tempfile
from pathlib import Path

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
    endpoints=st.lists(endpoint_strategy, min_size=0, max_size=3),
)

service_strategy = st.builds(
    ServiceInfo,
    class_name=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=30).map(
        lambda s: s + "ServiceImpl"
    ),
    interface_name=st.none(),
    methods=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20), min_size=0, max_size=5),
    dependencies=st.lists(
        st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=20),
        min_size=0,
        max_size=3,
    ),
)

repository_strategy = st.builds(
    RepositoryInfo,
    interface_name=st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25
    ).map(lambda s: s + "Repository"),
    entity_type=st.none(),
    custom_methods=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25), min_size=0, max_size=3
    ),
)

feign_client_strategy = st.builds(
    FeignClientInfo,
    interface_name=st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25
    ).map(lambda s: s + "Client"),
    target_service=st.text(alphabet="abcdefghijklmnopqrstuvwxyz-", min_size=5, max_size=30),
    methods=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20), min_size=0, max_size=3),
)

kafka_handler_strategy = st.builds(
    KafkaHandlerInfo,
    class_name=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=5, max_size=25).map(
        lambda s: s + "Handler"
    ),
    topics=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz.-_", min_size=5, max_size=30), min_size=1, max_size=3),
    methods=st.lists(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=20), min_size=0, max_size=3),
)

service_analysis_strategy = st.builds(
    ServiceAnalysis,
    service_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz-", min_size=10, max_size=40),
    controllers=st.lists(controller_strategy, min_size=0, max_size=2),
    services=st.lists(service_strategy, min_size=0, max_size=2),
    repositories=st.lists(repository_strategy, min_size=0, max_size=2),
    feign_clients=st.lists(feign_client_strategy, min_size=0, max_size=2),
    kafka_handlers=st.lists(kafka_handler_strategy, min_size=0, max_size=1),
)


class TestStyleConsistency:
    """Property tests for style consistency.

    **Feature: insurance-diagram-accuracy, Property 3: Style Consistency**
    **Validates: Requirements 3.1, 3.2, 3.3**
    """

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_sequence_diagram_has_standard_style(self, analysis: ServiceAnalysis) -> None:
        """Property: Sequence diagrams include standard PlantUML styling.

        **Validates: Requirements 3.1** - WHEN diagrams are generated
        THEN the Diagram Generator SHALL use consistent PlantUML styling.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())
        diagram = generator.generate_sequence_diagram(analysis)

        # Check for standard style elements
        assert "!theme plain" in diagram, "Sequence diagram missing standard theme"
        assert "skinparam backgroundColor" in diagram, "Sequence diagram missing background color"
        assert "skinparam sequenceMessageAlign" in diagram, "Sequence diagram missing sequence styling"

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_component_diagram_has_standard_style(self, analysis: ServiceAnalysis) -> None:
        """Property: Component diagrams include standard PlantUML styling.

        **Validates: Requirements 3.1** - WHEN diagrams are generated
        THEN the Diagram Generator SHALL use consistent PlantUML styling.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())
        diagram = generator.generate_component_diagram(analysis)

        # Check for standard style elements
        assert "!theme plain" in diagram, "Component diagram missing standard theme"
        assert "skinparam backgroundColor" in diagram, "Component diagram missing background color"
        assert "skinparam componentStyle" in diagram, "Component diagram missing component styling"

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_diagrams_follow_naming_convention(self, analysis: ServiceAnalysis) -> None:
        """Property: Generated diagram files follow naming convention.

        **Validates: Requirements 3.2** - WHEN diagrams are generated
        THEN the Diagram Generator SHALL follow standard naming convention.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = PlantUMLGenerator(output_dir)
            seq_path, comp_path, _split_paths = generator.save_diagrams(analysis, output_dir)

            # Check naming convention
            expected_seq_name = f"{analysis.service_name}-sequence.puml"
            expected_comp_name = f"{analysis.service_name}-component.puml"

            assert seq_path.name == expected_seq_name, (
                f"Sequence diagram name {seq_path.name} doesn't match convention {expected_seq_name}"
            )
            assert comp_path.name == expected_comp_name, (
                f"Component diagram name {comp_path.name} doesn't match convention {expected_comp_name}"
            )

    @given(analysis=service_analysis_strategy)
    @settings(max_examples=100, deadline=None)
    def test_diagrams_have_title_with_service_name(self, analysis: ServiceAnalysis) -> None:
        """Property: Diagrams include title with service name.

        **Validates: Requirements 3.1** - Consistent styling includes proper titles.
        """
        generator = PlantUMLGenerator(tempfile.gettempdir())

        seq_diagram = generator.generate_sequence_diagram(analysis)
        comp_diagram = generator.generate_component_diagram(analysis)

        assert f"title {analysis.service_name}" in seq_diagram, "Sequence diagram missing service name in title"
        assert f"title {analysis.service_name}" in comp_diagram, "Component diagram missing service name in title"
