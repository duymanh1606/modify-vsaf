"""Property tests for PNG generation.

**Feature: insurance-diagram-accuracy, Property 4: PNG Generation**
**Validates: Requirements 4.1, 4.2**

For any valid PUML file, rendering to PNG should produce a valid PNG file
that exists and has non-zero size.
"""

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# List of services that should have PNG files
SERVICES = [
    "insurance-policy-business",
    "insurance-claim-business",
    "insurance-customer-business",
    "insurance-proposal-business",
    "insurance-promotion-business",
    "insurance-payment-service",
    "insurance-payment-service-v2",
    "insurance-notification-spi",
    "insurance-job-scheduler",
    "insurance-centralized-sync-service",
    "insurance-ocr-service",
    "insurance-cms-be",
    "insurance-customer-webview",
    "insurance-insurer-service",
    "insurance-socialized-insurance-service",
    "insuremo-embedded-rule",
    "insurance-timeout-process",
    "insurance-renewal-process",
    "insurance-reconcile-process",
    "insurance-auto-underwriting-process",
    "insurance-authentication-sync-process",
    "insurance-common",
    "insurance-insuremo-common",
]

BASE_PATH = Path(__file__).parent.parent.parent.parent / "docs-nttc/projects/INSURANCE/analysis/current-state"


class TestPNGGeneration:
    """Property tests for PNG generation."""

    @given(service=st.sampled_from(SERVICES))
    @settings(max_examples=len(SERVICES))
    def test_sequence_diagram_png_exists(self, service: str):
        """Property: For any service, sequence diagram PNG should exist.

        **Feature: insurance-diagram-accuracy, Property 4: PNG Generation**
        **Validates: Requirements 4.1**
        """
        service_dir = BASE_PATH / service
        png_path = service_dir / f"{service}-sequence.png"

        assert png_path.exists(), f"Sequence PNG missing for {service}"
        assert png_path.stat().st_size > 0, f"Sequence PNG is empty for {service}"

    @given(service=st.sampled_from(SERVICES))
    @settings(max_examples=len(SERVICES))
    def test_component_diagram_png_exists(self, service: str):
        """Property: For any service, component diagram PNG should exist.

        **Feature: insurance-diagram-accuracy, Property 4: PNG Generation**
        **Validates: Requirements 4.1**
        """
        service_dir = BASE_PATH / service
        png_path = service_dir / f"{service}-component.png"

        assert png_path.exists(), f"Component PNG missing for {service}"
        assert png_path.stat().st_size > 0, f"Component PNG is empty for {service}"

    @given(service=st.sampled_from(SERVICES))
    @settings(max_examples=len(SERVICES))
    def test_png_is_valid_image(self, service: str):
        """Property: For any service, PNG files should be valid PNG images.

        **Feature: insurance-diagram-accuracy, Property 4: PNG Generation**
        **Validates: Requirements 4.2**
        """
        service_dir = BASE_PATH / service

        for diagram_type in ["sequence", "component"]:
            png_path = service_dir / f"{service}-{diagram_type}.png"
            if png_path.exists():
                # Check PNG magic bytes
                with open(png_path, "rb") as f:
                    header = f.read(8)
                    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
                    assert header[:4] == b"\x89PNG", f"Invalid PNG header for {service}-{diagram_type}"

    def test_all_services_have_both_diagrams(self):
        """Verify all services have both sequence and component PNG diagrams.

        **Feature: insurance-diagram-accuracy, Property 4: PNG Generation**
        **Validates: Requirements 4.1, 4.2**
        """
        missing = []
        for service in SERVICES:
            service_dir = BASE_PATH / service
            seq_png = service_dir / f"{service}-sequence.png"
            comp_png = service_dir / f"{service}-component.png"

            if not seq_png.exists():
                missing.append(f"{service}: sequence PNG")
            if not comp_png.exists():
                missing.append(f"{service}: component PNG")

        assert not missing, f"Missing PNG files: {missing}"
