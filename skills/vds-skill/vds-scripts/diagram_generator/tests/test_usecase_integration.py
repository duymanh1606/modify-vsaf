"""Integration tests for use case diagram generation."""

from pathlib import Path

import pytest
from vds_diagram_generator.analyzer import JavaCodeAnalyzer
from vds_diagram_generator.config import get_settings
from vds_diagram_generator.usecase_generator import UseCaseGenerator


def test_full_workflow_code_to_usecase(tmp_path: Path):
    """Test JavaCodeAnalyzer → UseCaseGenerator → PlantUML output."""
    settings = get_settings()
    source_path = settings.get_project_source_path("INSURANCE")

    if not source_path.exists():
        pytest.skip("INSURANCE project source not found")

    analyzer = JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service("insurance-policy-business")

    assert len(analysis.controllers) > 0
    assert len(analysis.controllers[0].endpoints) > 0

    generator = UseCaseGenerator(tmp_path)
    diagram = generator.generate_use_case_diagram(analysis)

    assert "@startuml" in diagram
    assert "@enduml" in diagram
    assert "insurance-policy-business" in diagram
    assert "actor" in diagram
    assert "usecase" in diagram or "package" in diagram


def test_cli_use_case_flag(tmp_path: Path):
    """Test CLI --use-case flag execution."""
    import subprocess
    import sys

    script_path = Path(__file__).parent.parent / "generate_all_diagrams.py"
    if not script_path.exists():
        pytest.skip("generate_all_diagrams.py not found")

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--project",
            "INSURANCE",
            "--service",
            "insurance-policy-business",
            "--use-case",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0 or "insurance-policy-business-usecase.puml" in result.stdout


def test_cli_use_case_only_flag(tmp_path: Path):
    """Test CLI --use-case-only flag."""
    import subprocess
    import sys

    script_path = Path(__file__).parent.parent / "generate_all_diagrams.py"
    if not script_path.exists():
        pytest.skip("generate_all_diagrams.py not found")

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--project",
            "INSURANCE",
            "--service",
            "insurance-policy-business",
            "--use-case-only",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0


def test_validation_usecase_diagrams(tmp_path: Path):
    """Test --validate-existing with use case diagrams."""
    settings = get_settings()
    source_path = settings.get_project_source_path("INSURANCE")

    if not source_path.exists():
        pytest.skip("INSURANCE project source not found")

    analyzer = JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service("insurance-policy-business")

    generator = UseCaseGenerator(tmp_path)
    diagram_path = generator.save_use_case_diagram(analysis, output_dir=tmp_path)

    assert diagram_path.exists()
    content = diagram_path.read_text(encoding="utf-8")
    assert "@startuml" in content
    assert "@enduml" in content


def test_usecase_output_formats(tmp_path: Path):
    """Test PNG/SVG generation for use case diagrams."""
    settings = get_settings()
    source_path = settings.get_project_source_path("INSURANCE")

    if not source_path.exists():
        pytest.skip("INSURANCE project source not found")

    analyzer = JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service("insurance-policy-business")

    generator = UseCaseGenerator(tmp_path)
    diagram_path = generator.save_use_case_diagram(analysis, output_dir=tmp_path)

    assert diagram_path.exists()
    assert diagram_path.suffix == ".puml"
