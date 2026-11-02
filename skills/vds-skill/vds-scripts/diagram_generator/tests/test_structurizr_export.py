"""Integration tests for Structurizr DSL + CLI tooling.

**Feature: insurance-diagram-accuracy, Property 6: Structurizr Integration**
**Validates: Requirements 19.2 (tests), 19.3 (backward compatibility), 19.4 (documentation readiness)**
"""

from __future__ import annotations

import stat
import tempfile
import time
from pathlib import Path

from vds_diagram_generator.models import (
    ControllerInfo,
    EndpointInfo,
    FeignClientInfo,
    KafkaHandlerInfo,
    RepositoryInfo,
    ServiceAnalysis,
    ServiceInfo,
)
from vds_diagram_generator.structurizr_cli import ExportFormat, StructurizrCLI, StructurizrExporter
from vds_diagram_generator.structurizr_generator import StructurizrDSLGenerator


def _sample_analysis() -> ServiceAnalysis:
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


class TestStructurizrDSLGenerator:
    def test_service_workspace_contains_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = StructurizrDSLGenerator(output_dir)
            workspace_path = generator.save_service_workspace(_sample_analysis(), output_dir=output_dir)

            content = workspace_path.read_text(encoding="utf-8")
            assert 'workspace "insurance-policy-business Architecture"' in content
            assert "model {" in content
            assert "views {" in content
            assert "styles {" in content

    def test_service_workspace_skips_rewrite_when_content_same(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = StructurizrDSLGenerator(output_dir)
            path = generator.save_service_workspace(_sample_analysis(), output_dir=output_dir)
            first_mtime = path.stat().st_mtime_ns
            time.sleep(0.01)  # ensure filesystem resolution window passes
            path = generator.save_service_workspace(_sample_analysis(), output_dir=output_dir)
            second_mtime = path.stat().st_mtime_ns
            assert first_mtime == second_mtime, "File should not be rewritten when DSL is unchanged"


def _create_fake_cli(tmpdir: Path) -> Path:
    """Create a lightweight Structurizr CLI stub that writes a dummy output file."""
    script_path = tmpdir / "structurizr-cli"
    script_path.write_text(
        """#!/usr/bin/env python3
import sys
from pathlib import Path

args = sys.argv[1:]
command = args[0] if args else ""
if command != "export":
    sys.exit(1)

def _value(flag):
    idx = args.index(flag)
    return args[idx + 1]

workspace = _value("-workspace")
fmt = _value("-format")
output = Path(_value("-output"))

output.mkdir(parents=True, exist_ok=True)
(output / "exported-diagram.puml").write_text("@startuml\\n@enduml", encoding="utf-8")
print(f\"Exported workspace={workspace} format={fmt}\")
""",
        encoding="utf-8",
    )
    script_path.chmod(stat.S_IRWXU)
    return script_path


class TestStructurizrCLIIntegration:
    def test_cli_export_success_with_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            generator = StructurizrDSLGenerator(base_dir)
            workspace_path = generator.save_service_workspace(_sample_analysis(), output_dir=base_dir / "dsl")
            fake_cli = _create_fake_cli(base_dir)

            cli = StructurizrCLI(cli_path=str(fake_cli))
            output_dir = base_dir / "exported"
            result = cli.export(workspace_path, output_dir, export_format=ExportFormat.C4_PLANTUML)

            assert result.success is True
            assert result.exported_files, "Expected exported files list"
            exported_file = result.exported_files[0]
            assert exported_file.exists()
            assert "@startuml" in exported_file.read_text(encoding="utf-8")

    def test_cli_export_handles_missing_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            generator = StructurizrDSLGenerator(base_dir)
            workspace_path = generator.save_service_workspace(_sample_analysis(), output_dir=base_dir / "dsl")

            cli = StructurizrCLI(cli_path=None)  # force auto-detect failure
            result = cli.export(workspace_path, base_dir / "exported")

            assert result.success is False
            assert "Structurizr CLI not found" in (result.error_message or "")


class TestStructurizrExporterEndToEnd:
    def test_exporter_generates_dsl_and_runs_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            fake_cli = _create_fake_cli(base_dir)
            exporter = StructurizrExporter(output_base_path=base_dir, cli_path=str(fake_cli))

            dsl_path, export_result = exporter.export_service(_sample_analysis(), export_format=ExportFormat.PLANTUML)

            assert dsl_path.exists()
            assert export_result is not None
            assert export_result.success
            assert export_result.exported_files
            assert export_result.exported_files[0].exists()

    def test_exporter_gracefully_handles_missing_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            exporter = StructurizrExporter(output_base_path=base_dir)

            dsl_path, export_result = exporter.export_service(_sample_analysis())

            assert dsl_path.exists()
            assert export_result is None, "Exporter should skip CLI when unavailable to preserve backward compatibility"
