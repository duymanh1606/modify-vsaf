"""Tests for external SCA client with mocked subprocess calls."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vds_sonarqube_orchestrator.external_sca import (
    SBOM,
    Component,
    ExternalSCAClient,
    QualityGateResult,
    SCAError,
    Severity,
    ToolExecutionError,
    ToolInfo,
    ToolNotAvailableError,
    ToolOutputError,
    ToolTimeoutError,
    Vulnerability,
    VulnerabilityReport,
)


class TestSeverity:
    def test_from_string_critical(self) -> None:
        assert Severity.from_string("CRITICAL") == Severity.CRITICAL
        assert Severity.from_string("critical") == Severity.CRITICAL
        assert Severity.from_string("BLOCKER") == Severity.CRITICAL

    def test_from_string_high(self) -> None:
        assert Severity.from_string("HIGH") == Severity.HIGH
        assert Severity.from_string("MAJOR") == Severity.HIGH

    def test_from_string_medium(self) -> None:
        assert Severity.from_string("MEDIUM") == Severity.MEDIUM
        assert Severity.from_string("MODERATE") == Severity.MEDIUM
        assert Severity.from_string("MINOR") == Severity.MEDIUM

    def test_from_string_low(self) -> None:
        assert Severity.from_string("LOW") == Severity.LOW
        assert Severity.from_string("INFO") == Severity.LOW

    def test_from_string_unknown(self) -> None:
        assert Severity.from_string("INVALID") == Severity.UNKNOWN
        assert Severity.from_string("") == Severity.UNKNOWN


class TestToolInfo:
    def test_to_dict(self) -> None:
        info = ToolInfo(name="trivy", installed=True, version="0.50.0", path="/usr/bin/trivy")
        result = info.to_dict()
        assert result["name"] == "trivy"
        assert result["installed"] is True
        assert result["version"] == "0.50.0"
        assert result["path"] == "/usr/bin/trivy"


class TestVulnerability:
    def test_to_dict(self) -> None:
        vuln = Vulnerability(
            id="CVE-2024-1234",
            severity=Severity.HIGH,
            package_name="requests",
            installed_version="2.25.0",
            fixed_version="2.31.0",
            title="HTTP Request Smuggling",
            cvss_score=7.5,
        )
        result = vuln.to_dict()
        assert result["id"] == "CVE-2024-1234"
        assert result["severity"] == "HIGH"
        assert result["package_name"] == "requests"
        assert result["fixed_version"] == "2.31.0"


class TestVulnerabilityReport:
    def test_summary(self) -> None:
        vulns = [
            Vulnerability(
                id="CVE-1", severity=Severity.CRITICAL, package_name="p1", installed_version="1.0"
            ),
            Vulnerability(
                id="CVE-2", severity=Severity.HIGH, package_name="p2", installed_version="1.0"
            ),
            Vulnerability(
                id="CVE-3", severity=Severity.HIGH, package_name="p3", installed_version="1.0"
            ),
            Vulnerability(
                id="CVE-4", severity=Severity.MEDIUM, package_name="p4", installed_version="1.0"
            ),
        ]
        report = VulnerabilityReport(tool="trivy", project_dir="/test", vulnerabilities=vulns)

        assert report.total_count == 4
        assert report.count_by_severity(Severity.CRITICAL) == 1
        assert report.count_by_severity(Severity.HIGH) == 2
        assert report.count_by_severity("MEDIUM") == 1
        assert report.summary["critical"] == 1
        assert report.summary["high"] == 2
        assert report.summary["total"] == 4


class TestComponent:
    def test_to_dict(self) -> None:
        comp = Component(
            name="requests",
            version="2.31.0",
            type="library",
            purl="pkg:pypi/requests@2.31.0",
            licenses=["Apache-2.0"],
        )
        result = comp.to_dict()
        assert result["name"] == "requests"
        assert result["version"] == "2.31.0"
        assert result["licenses"] == ["Apache-2.0"]


class TestSBOM:
    def test_component_count(self) -> None:
        components = [
            Component(name="pkg1", version="1.0"),
            Component(name="pkg2", version="2.0"),
        ]
        sbom = SBOM(format="cyclonedx", tool="syft", project_dir="/test", components=components)
        assert sbom.component_count == 2


class TestQualityGateResult:
    def test_to_dict(self) -> None:
        result = QualityGateResult(
            passed=False,
            fail_threshold="HIGH",
            max_vulnerabilities=0,
            critical_count=1,
            high_count=5,
            medium_count=10,
            low_count=20,
            message="Quality gate FAILED",
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["fail_threshold"] == "HIGH"
        assert d["critical_count"] == 1


class TestSCAErrors:
    def test_sca_error_with_context(self) -> None:
        err = SCAError("Test error", context={"key": "value"})
        assert "Test error" in str(err)
        assert err.context["key"] == "value"

    def test_tool_not_available_error(self) -> None:
        err = ToolNotAvailableError("snyk", ["trivy", "grype"])
        assert "snyk" in str(err)
        assert "trivy" in str(err)
        assert err.requested == "snyk"
        assert err.available == ["trivy", "grype"]

    def test_tool_timeout_error(self) -> None:
        err = ToolTimeoutError("trivy", 300)
        assert "trivy" in str(err)
        assert "300" in str(err)
        assert err.tool == "trivy"
        assert err.timeout == 300

    def test_tool_execution_error(self) -> None:
        err = ToolExecutionError("snyk", 2, "Authentication failed")
        assert "snyk" in str(err)
        assert "2" in str(err)
        assert err.exit_code == 2

    def test_tool_output_error(self) -> None:
        err = ToolOutputError("trivy", "Invalid JSON")
        assert "trivy" in str(err)
        assert "Invalid JSON" in str(err)


class TestExternalSCAClient:
    @pytest.fixture
    def client(self) -> ExternalSCAClient:
        return ExternalSCAClient(None)

    def test_detect_available_tools_none_installed(self, client: ExternalSCAClient) -> None:
        with patch("shutil.which", return_value=None):
            tools = client.detect_available_tools()
            assert not tools["snyk"].installed
            assert not tools["trivy"].installed
            assert not tools["syft"].installed
            assert not tools["grype"].installed

    def test_detect_available_tools_trivy_installed(self, client: ExternalSCAClient) -> None:
        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                tools = client.detect_available_tools()
                assert tools["trivy"].installed
                assert tools["trivy"].version == "0.50.0"
                assert tools["trivy"].path == "/usr/bin/trivy"
                assert not tools["snyk"].installed

    def test_get_available_tool_auto_select(self, client: ExternalSCAClient) -> None:
        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                tool = client.get_available_tool()
                assert tool == "trivy"

    def test_get_available_tool_preferred(self, client: ExternalSCAClient) -> None:
        def mock_which(cmd: str) -> str | None:
            return f"/usr/bin/{cmd}" if cmd in ("snyk", "trivy") else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="1.0.0"):
                tool = client.get_available_tool(preferred="trivy")
                assert tool == "trivy"

    def test_get_available_tool_not_found(self, client: ExternalSCAClient) -> None:
        with patch("shutil.which", return_value=None):
            with pytest.raises(ToolNotAvailableError) as exc_info:
                client.get_available_tool()
            assert exc_info.value.requested == "any"

    def test_get_available_tool_preferred_not_found(self, client: ExternalSCAClient) -> None:
        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                with pytest.raises(ToolNotAvailableError) as exc_info:
                    client.get_available_tool(preferred="snyk")
                assert exc_info.value.requested == "snyk"

    def test_scan_with_trivy_success(self, client: ExternalSCAClient) -> None:
        trivy_output = {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-1234",
                            "Severity": "HIGH",
                            "PkgName": "requests",
                            "InstalledVersion": "2.25.0",
                            "FixedVersion": "2.31.0",
                            "Title": "HTTP vulnerability",
                        }
                    ]
                }
            ]
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(trivy_output)
        mock_result.stderr = ""

        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                with patch("subprocess.run", return_value=mock_result):
                    report = client.scan_dependencies(Path("/test/project"), tool="trivy")

        assert report.tool == "trivy"
        assert report.total_count == 1
        assert report.vulnerabilities[0].id == "CVE-2024-1234"
        assert report.vulnerabilities[0].severity == Severity.HIGH

    def test_scan_with_snyk_success(self, client: ExternalSCAClient) -> None:
        snyk_output = {
            "vulnerabilities": [
                {
                    "id": "SNYK-PYTHON-REQUESTS-1234",
                    "severity": "high",
                    "packageName": "requests",
                    "version": "2.25.0",
                    "fixedIn": ["2.31.0"],
                    "title": "HTTP Request Smuggling",
                }
            ]
        }

        mock_result = MagicMock()
        mock_result.returncode = 1  # Snyk returns 1 when vulns found
        mock_result.stdout = json.dumps(snyk_output)
        mock_result.stderr = ""

        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/snyk" if cmd == "snyk" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="1.0.0"):
                with patch("subprocess.run", return_value=mock_result):
                    report = client.scan_dependencies(Path("/test/project"), tool="snyk")

        assert report.tool == "snyk"
        assert report.total_count == 1
        assert report.vulnerabilities[0].severity == Severity.HIGH

    def test_scan_with_grype_success(self, client: ExternalSCAClient) -> None:
        grype_output = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-5678",
                        "severity": "Critical",
                    },
                    "artifact": {
                        "name": "flask",
                        "version": "1.0.0",
                    },
                }
            ]
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(grype_output)
        mock_result.stderr = ""

        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/grype" if cmd == "grype" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.70.0"):
                with patch("subprocess.run", return_value=mock_result):
                    report = client.scan_dependencies(Path("/test/project"), tool="grype")

        assert report.tool == "grype"
        assert report.total_count == 1
        assert report.vulnerabilities[0].severity == Severity.CRITICAL

    def test_scan_timeout(self, client: ExternalSCAClient) -> None:
        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("trivy", 300)):
                    with pytest.raises(ToolTimeoutError) as exc_info:
                        client.scan_dependencies(Path("/test/project"), tool="trivy")
                    assert exc_info.value.tool == "trivy"

    def test_generate_sbom_with_syft(self, client: ExternalSCAClient) -> None:
        sbom_output = {
            "components": [
                {
                    "name": "requests",
                    "version": "2.31.0",
                    "type": "library",
                    "purl": "pkg:pypi/requests@2.31.0",
                    "licenses": [{"license": {"id": "Apache-2.0"}}],
                }
            ],
            "metadata": {"component": {"name": "test-project"}},
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(sbom_output)
        mock_result.stderr = ""

        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/syft" if cmd == "syft" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.100.0"):
                with patch("subprocess.run", return_value=mock_result):
                    sbom = client.generate_sbom(Path("/test/project"), tool="syft")

        assert sbom.format == "cyclonedx"
        assert sbom.tool == "syft"
        assert sbom.component_count == 1
        assert sbom.components[0].name == "requests"

    def test_check_quality_gate_pass(self, client: ExternalSCAClient) -> None:
        trivy_output = {"Results": [{"Vulnerabilities": []}]}

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(trivy_output)
        mock_result.stderr = ""

        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                with patch("subprocess.run", return_value=mock_result):
                    result = client.check_quality_gate(Path("/test/project"), fail_threshold="HIGH")

        assert result.passed is True
        assert "PASSED" in result.message

    def test_check_quality_gate_fail(self, client: ExternalSCAClient) -> None:
        trivy_output = {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-1",
                            "Severity": "CRITICAL",
                            "PkgName": "p1",
                            "InstalledVersion": "1.0",
                        },
                        {
                            "VulnerabilityID": "CVE-2",
                            "Severity": "HIGH",
                            "PkgName": "p2",
                            "InstalledVersion": "1.0",
                        },
                    ]
                }
            ]
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(trivy_output)
        mock_result.stderr = ""

        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                with patch("subprocess.run", return_value=mock_result):
                    result = client.check_quality_gate(Path("/test/project"), fail_threshold="HIGH")

        assert result.passed is False
        assert result.critical_count == 1
        assert result.high_count == 1
        assert "FAILED" in result.message

    def test_get_installation_guide(self, client: ExternalSCAClient) -> None:
        guide = client.get_installation_guide()
        assert "Snyk" in guide
        assert "Trivy" in guide
        assert "Syft" in guide
        assert "Grype" in guide
        assert "brew install" in guide

    def test_parse_invalid_json(self, client: ExternalSCAClient) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json {"
        mock_result.stderr = ""

        def mock_which(cmd: str) -> str | None:
            return "/usr/bin/trivy" if cmd == "trivy" else None

        with patch("shutil.which", side_effect=mock_which):
            with patch.object(client, "_get_tool_version", return_value="0.50.0"):
                with patch("subprocess.run", return_value=mock_result):
                    with pytest.raises(ToolOutputError) as exc_info:
                        client.scan_dependencies(Path("/test/project"), tool="trivy")
                    assert exc_info.value.tool == "trivy"
