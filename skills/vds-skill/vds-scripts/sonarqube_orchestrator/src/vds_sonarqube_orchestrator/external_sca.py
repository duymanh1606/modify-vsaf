"""External SCA (Software Composition Analysis) integration via CLI tools.

This module provides dependency vulnerability scanning and SBOM generation
using external CLI tools (Snyk, Trivy, Syft) as an alternative to SonarQube's
native SCA features which require Enterprise Edition + Advanced Security.

Architecture:
    ExternalSCAClient -> subprocess -> External CLI tools (Snyk/Trivy/Syft)

Supported Tools:
    - Snyk CLI: Vulnerability scanning with remediation (free tier available)
    - Trivy: SBOM generation + CVE scanning (open source)
    - Syft: Comprehensive SBOM generation (open source)
    - Grype: Vulnerability scanner for SBOMs (open source, optional)

Example:
    >>> from vds_sonarqube_orchestrator.external_sca import ExternalSCAClient
    >>> from vds_sonarqube_orchestrator.config import load_settings
    >>> settings = load_settings()
    >>> client = ExternalSCAClient(settings)
    >>> tools = client.detect_available_tools()
    >>> if tools["trivy"].installed:
    ...     report = client.scan_dependencies(Path("."), tool="trivy")
    ...     print(f"Found {report.total_count} vulnerabilities")
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.config import SonarqubeSettings


class Severity(StrEnum):
    """Vulnerability severity levels (normalized across tools)."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_string(cls, value: str) -> Severity:
        """Convert string to Severity enum (case-insensitive)."""
        upper = value.upper().strip()
        if upper in ("CRITICAL", "BLOCKER"):
            return cls.CRITICAL
        if upper in ("HIGH", "MAJOR"):
            return cls.HIGH
        if upper in ("MEDIUM", "MODERATE", "MINOR"):
            return cls.MEDIUM
        if upper in ("LOW", "INFO"):
            return cls.LOW
        return cls.UNKNOWN


@dataclass
class ToolInfo:
    """Information about an installed SCA tool."""

    name: str
    installed: bool
    version: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "installed": self.installed,
            "version": self.version,
            "path": self.path,
        }


@dataclass
class Vulnerability:
    """Single vulnerability finding (normalized across tools)."""

    id: str  # CVE ID or tool-specific ID
    severity: Severity
    package_name: str
    installed_version: str
    fixed_version: str | None = None
    title: str = ""
    description: str = ""
    cvss_score: float | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "package_name": self.package_name,
            "installed_version": self.installed_version,
            "fixed_version": self.fixed_version,
            "title": self.title,
            "description": self.description,
            "cvss_score": self.cvss_score,
            "url": self.url,
        }


@dataclass
class VulnerabilityReport:
    """Normalized vulnerability report from any tool."""

    tool: str
    project_dir: str
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    scan_time_seconds: float = 0.0
    raw_output: dict[str, Any] = field(default_factory=dict)

    @property
    def total_count(self) -> int:
        """Total number of vulnerabilities."""
        return len(self.vulnerabilities)

    def count_by_severity(self, severity: Severity | str) -> int:
        """Count vulnerabilities by severity."""
        if isinstance(severity, str):
            severity = Severity.from_string(severity)
        return sum(1 for v in self.vulnerabilities if v.severity == severity)

    @property
    def summary(self) -> dict[str, int]:
        """Get vulnerability count by severity."""
        return {
            "critical": self.count_by_severity(Severity.CRITICAL),
            "high": self.count_by_severity(Severity.HIGH),
            "medium": self.count_by_severity(Severity.MEDIUM),
            "low": self.count_by_severity(Severity.LOW),
            "unknown": self.count_by_severity(Severity.UNKNOWN),
            "total": self.total_count,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tool": self.tool,
            "project_dir": self.project_dir,
            "summary": self.summary,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "scan_time_seconds": self.scan_time_seconds,
        }


@dataclass
class Component:
    """Single component in SBOM."""

    name: str
    version: str
    type: str = "library"  # library, application, framework, etc.
    purl: str | None = None  # Package URL
    licenses: list[str] = field(default_factory=list)
    supplier: str | None = None
    hashes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "type": self.type,
            "purl": self.purl,
            "licenses": self.licenses,
            "supplier": self.supplier,
            "hashes": self.hashes,
        }


@dataclass
class SBOM:
    """Software Bill of Materials."""

    format: str  # cyclonedx, spdx
    tool: str
    project_dir: str
    components: list[Component] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_output: dict[str, Any] = field(default_factory=dict)

    @property
    def component_count(self) -> int:
        """Total number of components."""
        return len(self.components)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "format": self.format,
            "tool": self.tool,
            "project_dir": self.project_dir,
            "component_count": self.component_count,
            "components": [c.to_dict() for c in self.components],
            "metadata": self.metadata,
        }


@dataclass
class QualityGateResult:
    """Dependency quality gate check result."""

    passed: bool
    fail_threshold: str
    max_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "fail_threshold": self.fail_threshold,
            "max_vulnerabilities": self.max_vulnerabilities,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "message": self.message,
        }


# -----------------------------------------------------------------------------
# Error Types
# -----------------------------------------------------------------------------


class SCAError(RuntimeError):
    """Base class for SCA-related errors."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ToolNotAvailableError(SCAError):
    """Raised when requested SCA tool is not installed."""

    def __init__(self, requested: str, available: list[str]) -> None:
        self.requested = requested
        self.available = available
        message = (
            f"Tool '{requested}' not found. "
            f"Available tools: {', '.join(available) if available else 'none'}\n"
            "Run 'vds-sonarqube sca-status --install-guide' for installation help."
        )
        super().__init__(message, context={"requested": requested, "available": available})


class ToolTimeoutError(SCAError):
    """Raised when SCA tool subprocess times out."""

    def __init__(self, tool: str, timeout: int) -> None:
        self.tool = tool
        self.timeout = timeout
        super().__init__(
            f"Tool '{tool}' timed out after {timeout} seconds",
            context={"tool": tool, "timeout": timeout},
        )


class ToolExecutionError(SCAError):
    """Raised when SCA tool fails to execute."""

    def __init__(self, tool: str, exit_code: int, stderr: str) -> None:
        self.tool = tool
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(
            f"Tool '{tool}' failed with exit code {exit_code}: {stderr[:500]}",
            context={"tool": tool, "exit_code": exit_code, "stderr": stderr},
        )


class ToolOutputError(SCAError):
    """Raised when tool output cannot be parsed."""

    def __init__(self, tool: str, message: str) -> None:
        self.tool = tool
        super().__init__(
            f"Failed to parse '{tool}' output: {message}",
            context={"tool": tool},
        )


# -----------------------------------------------------------------------------
# External SCA Client
# -----------------------------------------------------------------------------


class ExternalSCAClient:
    """External SCA tool client using subprocess pattern.

    This client wraps external CLI tools (Snyk, Trivy, Syft) for dependency
    vulnerability scanning and SBOM generation.

    Example:
        >>> client = ExternalSCAClient(settings)
        >>> tools = client.detect_available_tools()
        >>> report = client.scan_dependencies(Path("."))
        >>> sbom = client.generate_sbom(Path("."), format="cyclonedx")
    """

    # Tool priority for auto-selection (first available wins)
    TOOL_PRIORITY = ["snyk", "trivy", "syft", "grype"]

    # SBOM tool priority
    SBOM_TOOL_PRIORITY = ["syft", "trivy"]

    def __init__(self, settings: SonarqubeSettings | None = None) -> None:
        """Initialize the client with optional settings.

        Args:
            settings: Optional SonarqubeSettings for timeout configuration.
        """
        self.settings = settings
        self._timeout = 300  # Default 5 minutes
        self._preferred_tool: str | None = None

        # Load settings if provided
        if settings:
            # Use sca_timeout if available (will be added to config)
            self._timeout = getattr(settings, "sca_timeout", 300)
            self._preferred_tool = getattr(settings, "sca_tool", None)
            if self._preferred_tool == "auto":
                self._preferred_tool = None

    # -------------------------------------------------------------------------
    # Tool Detection
    # -------------------------------------------------------------------------

    def detect_available_tools(self) -> dict[str, ToolInfo]:
        """Detect which SCA tools are installed on the system.

        Returns:
            Dict mapping tool names to ToolInfo with installation status.
        """
        tools: dict[str, ToolInfo] = {}

        for tool_name in self.TOOL_PRIORITY:
            path = shutil.which(tool_name)
            installed = path is not None
            version = None

            if installed:
                version = self._get_tool_version(tool_name)

            tools[tool_name] = ToolInfo(
                name=tool_name,
                installed=installed,
                version=version,
                path=path,
            )

        return tools

    def _get_tool_version(self, tool: str) -> str | None:
        """Get version string for a tool."""
        try:
            result = subprocess.run(
                [tool, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse first line of version output
                output = result.stdout.strip()
                if output:
                    # Handle multi-line output (take first line)
                    first_line = output.split("\n")[0]
                    return first_line[:100]  # Limit length
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def get_available_tool(self, preferred: str | None = None) -> str:
        """Get the best available tool for scanning.

        Args:
            preferred: Optional preferred tool name.

        Returns:
            Name of the available tool.

        Raises:
            ToolNotAvailableError: If no tools are installed.
        """
        available = self.detect_available_tools()
        installed = [name for name, info in available.items() if info.installed]

        # Check preferred tool first
        if preferred and preferred != "auto":
            if preferred in installed:
                return preferred
            raise ToolNotAvailableError(preferred, installed)

        # Check settings preferred tool
        if self._preferred_tool and self._preferred_tool in installed:
            return self._preferred_tool

        # Auto-select by priority
        for tool in self.TOOL_PRIORITY:
            if tool in installed:
                return tool

        raise ToolNotAvailableError("any", installed)

    def get_available_sbom_tool(self, preferred: str | None = None) -> str:
        """Get the best available tool for SBOM generation.

        Args:
            preferred: Optional preferred tool name.

        Returns:
            Name of the available SBOM tool.

        Raises:
            ToolNotAvailableError: If no SBOM tools are installed.
        """
        available = self.detect_available_tools()
        installed = [name for name, info in available.items() if info.installed]
        sbom_installed = [t for t in self.SBOM_TOOL_PRIORITY if t in installed]

        if preferred and preferred != "auto":
            if preferred in sbom_installed:
                return preferred
            raise ToolNotAvailableError(preferred, sbom_installed)

        for tool in self.SBOM_TOOL_PRIORITY:
            if tool in sbom_installed:
                return tool

        raise ToolNotAvailableError("sbom-generator", sbom_installed)

    # -------------------------------------------------------------------------
    # Vulnerability Scanning
    # -------------------------------------------------------------------------

    def scan_dependencies(
        self,
        project_dir: Path,
        tool: str | None = None,
        severities: list[str] | None = None,
    ) -> VulnerabilityReport:
        """Scan dependencies for vulnerabilities using external CLI.

        Args:
            project_dir: Directory to scan.
            tool: Tool to use (snyk, trivy, grype). Auto-selects if None.
            severities: Optional severity filter (CRITICAL, HIGH, MEDIUM, LOW).

        Returns:
            VulnerabilityReport with scan results.

        Raises:
            ToolNotAvailableError: If requested tool is not installed.
            ToolTimeoutError: If scan times out.
            ToolExecutionError: If tool fails.
            ToolOutputError: If output cannot be parsed.
        """
        import time

        selected = self.get_available_tool(tool)
        start_time = time.time()

        if selected == "snyk":
            report = self._scan_with_snyk(project_dir, severities)
        elif selected == "trivy":
            report = self._scan_with_trivy(project_dir, severities)
        elif selected == "grype":
            report = self._scan_with_grype(project_dir, severities)
        else:
            raise ToolNotAvailableError(selected, self.TOOL_PRIORITY)

        report.scan_time_seconds = time.time() - start_time
        return report

    def _scan_with_snyk(
        self,
        project_dir: Path,
        severities: list[str] | None = None,
    ) -> VulnerabilityReport:
        """Run Snyk CLI: snyk test --json.

        Snyk exit codes:
            0 = success, no vulnerabilities
            1 = vulnerabilities found
            2 = failure (e.g., no supported files)
            3 = license issues
        """
        cmd = ["snyk", "test", "--json"]

        if severities:
            # Snyk uses --severity-threshold for minimum severity
            min_sev = min(
                severities, key=lambda s: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(s.upper())
            )
            cmd.append(f"--severity-threshold={min_sev.lower()}")

        cmd.append(str(project_dir))

        result = self._run_tool(cmd, allow_nonzero=[1, 3])
        return self._parse_snyk_output(result.stdout, project_dir)

    def _parse_snyk_output(self, output: str, project_dir: Path) -> VulnerabilityReport:
        """Parse Snyk JSON output to VulnerabilityReport."""
        try:
            data = json.loads(output) if output.strip() else {}
        except json.JSONDecodeError as e:
            raise ToolOutputError("snyk", f"Invalid JSON: {e}")

        vulnerabilities: list[Vulnerability] = []

        # Snyk returns vulnerabilities array
        vulns = data.get("vulnerabilities", [])
        for vuln in vulns:
            vulnerabilities.append(
                Vulnerability(
                    id=vuln.get("id", vuln.get("identifiers", {}).get("CVE", ["UNKNOWN"])[0]),
                    severity=Severity.from_string(vuln.get("severity", "UNKNOWN")),
                    package_name=vuln.get("packageName", vuln.get("name", "unknown")),
                    installed_version=vuln.get("version", "unknown"),
                    fixed_version=vuln.get("fixedIn", [None])[0] if vuln.get("fixedIn") else None,
                    title=vuln.get("title", ""),
                    description=vuln.get("description", "")[:500],
                    cvss_score=vuln.get("cvssScore"),
                    url=vuln.get("url"),
                )
            )

        return VulnerabilityReport(
            tool="snyk",
            project_dir=str(project_dir),
            vulnerabilities=vulnerabilities,
            raw_output=data,
        )

    def _scan_with_trivy(
        self,
        project_dir: Path,
        severities: list[str] | None = None,
    ) -> VulnerabilityReport:
        """Run Trivy: trivy filesystem --format json."""
        cmd = [
            "trivy",
            "filesystem",
            "--format",
            "json",
            "--quiet",
        ]

        if severities:
            cmd.extend(["--severity", ",".join(s.upper() for s in severities)])

        cmd.append(str(project_dir))

        result = self._run_tool(cmd, allow_nonzero=[1])
        return self._parse_trivy_output(result.stdout, project_dir)

    def _parse_trivy_output(self, output: str, project_dir: Path) -> VulnerabilityReport:
        """Parse Trivy JSON output to VulnerabilityReport."""
        try:
            data = json.loads(output) if output.strip() else {}
        except json.JSONDecodeError as e:
            raise ToolOutputError("trivy", f"Invalid JSON: {e}")

        vulnerabilities: list[Vulnerability] = []

        # Trivy returns Results array with Vulnerabilities
        results = data.get("Results", [])
        for result in results:
            for vuln in result.get("Vulnerabilities", []):
                vulnerabilities.append(
                    Vulnerability(
                        id=vuln.get("VulnerabilityID", "UNKNOWN"),
                        severity=Severity.from_string(vuln.get("Severity", "UNKNOWN")),
                        package_name=vuln.get("PkgName", "unknown"),
                        installed_version=vuln.get("InstalledVersion", "unknown"),
                        fixed_version=vuln.get("FixedVersion"),
                        title=vuln.get("Title", ""),
                        description=vuln.get("Description", "")[:500],
                        cvss_score=vuln.get("CVSS", {}).get("nvd", {}).get("V3Score"),
                        url=vuln.get("PrimaryURL"),
                    )
                )

        return VulnerabilityReport(
            tool="trivy",
            project_dir=str(project_dir),
            vulnerabilities=vulnerabilities,
            raw_output=data,
        )

    def _scan_with_grype(
        self,
        project_dir: Path,
        severities: list[str] | None = None,
    ) -> VulnerabilityReport:
        """Run Grype: grype dir:<path> -o json."""
        cmd = ["grype", f"dir:{project_dir}", "-o", "json", "--quiet"]

        if severities:
            # Grype uses --fail-on for severity threshold
            min_sev = min(
                severities, key=lambda s: ["low", "medium", "high", "critical"].index(s.lower())
            )
            cmd.extend(["--fail-on", min_sev.lower()])

        result = self._run_tool(cmd, allow_nonzero=[1])
        return self._parse_grype_output(result.stdout, project_dir)

    def _parse_grype_output(self, output: str, project_dir: Path) -> VulnerabilityReport:
        """Parse Grype JSON output to VulnerabilityReport."""
        try:
            data = json.loads(output) if output.strip() else {}
        except json.JSONDecodeError as e:
            raise ToolOutputError("grype", f"Invalid JSON: {e}")

        vulnerabilities: list[Vulnerability] = []

        # Grype returns matches array
        matches = data.get("matches", [])
        for match in matches:
            vuln_data = match.get("vulnerability", {})
            artifact = match.get("artifact", {})

            vulnerabilities.append(
                Vulnerability(
                    id=vuln_data.get("id", "UNKNOWN"),
                    severity=Severity.from_string(vuln_data.get("severity", "UNKNOWN")),
                    package_name=artifact.get("name", "unknown"),
                    installed_version=artifact.get("version", "unknown"),
                    fixed_version=vuln_data.get("fix", {}).get("versions", [None])[0],
                    title=vuln_data.get("description", "")[:100],
                    description=vuln_data.get("description", "")[:500],
                    cvss_score=None,  # Grype doesn't provide CVSS in standard output
                    url=vuln_data.get("dataSource"),
                )
            )

        return VulnerabilityReport(
            tool="grype",
            project_dir=str(project_dir),
            vulnerabilities=vulnerabilities,
            raw_output=data,
        )

    # -------------------------------------------------------------------------
    # SBOM Generation
    # -------------------------------------------------------------------------

    def generate_sbom(
        self,
        project_dir: Path,
        sbom_format: str = "cyclonedx",
        tool: str | None = None,
    ) -> SBOM:
        """Generate Software Bill of Materials.

        Args:
            project_dir: Directory to scan.
            sbom_format: Output format (cyclonedx, spdx).
            tool: Tool to use (syft, trivy). Auto-selects if None.

        Returns:
            SBOM with component inventory.

        Raises:
            ToolNotAvailableError: If requested tool is not installed.
            ToolTimeoutError: If generation times out.
            ToolOutputError: If output cannot be parsed.
        """
        selected = self.get_available_sbom_tool(tool)

        if selected == "syft":
            return self._sbom_with_syft(project_dir, sbom_format)
        elif selected == "trivy":
            return self._sbom_with_trivy(project_dir, sbom_format)
        else:
            raise ToolNotAvailableError(selected, self.SBOM_TOOL_PRIORITY)

    def _sbom_with_syft(self, project_dir: Path, sbom_format: str) -> SBOM:
        """Generate SBOM using Syft: syft <dir> -o cyclonedx-json."""
        format_map = {
            "cyclonedx": "cyclonedx-json",
            "spdx": "spdx-json",
        }
        output_format = format_map.get(sbom_format.lower(), "cyclonedx-json")

        cmd = ["syft", str(project_dir), "-o", output_format, "--quiet"]
        result = self._run_tool(cmd)

        return self._parse_sbom_output(result.stdout, project_dir, sbom_format, "syft")

    def _sbom_with_trivy(self, project_dir: Path, sbom_format: str) -> SBOM:
        """Generate SBOM using Trivy: trivy filesystem --format cyclonedx."""
        format_map = {
            "cyclonedx": "cyclonedx",
            "spdx": "spdx-json",
        }
        output_format = format_map.get(sbom_format.lower(), "cyclonedx")

        cmd = [
            "trivy",
            "filesystem",
            "--format",
            output_format,
            "--quiet",
            str(project_dir),
        ]
        result = self._run_tool(cmd)

        return self._parse_sbom_output(result.stdout, project_dir, sbom_format, "trivy")

    def _parse_sbom_output(
        self,
        output: str,
        project_dir: Path,
        sbom_format: str,
        tool: str,
    ) -> SBOM:
        """Parse SBOM JSON output (CycloneDX or SPDX format)."""
        try:
            data = json.loads(output) if output.strip() else {}
        except json.JSONDecodeError as e:
            raise ToolOutputError(tool, f"Invalid JSON: {e}")

        components: list[Component] = []

        # CycloneDX format
        if sbom_format.lower() == "cyclonedx":
            for comp in data.get("components", []):
                components.append(
                    Component(
                        name=comp.get("name", "unknown"),
                        version=comp.get("version", "unknown"),
                        type=comp.get("type", "library"),
                        purl=comp.get("purl"),
                        licenses=[
                            lic.get("license", {}).get("id", "")
                            for lic in comp.get("licenses", [])
                            if lic.get("license", {}).get("id")
                        ],
                        supplier=comp.get("supplier", {}).get("name"),
                        hashes={
                            h.get("alg", ""): h.get("content", "") for h in comp.get("hashes", [])
                        },
                    )
                )
        # SPDX format
        elif sbom_format.lower() == "spdx":
            for pkg in data.get("packages", []):
                components.append(
                    Component(
                        name=pkg.get("name", "unknown"),
                        version=pkg.get("versionInfo", "unknown"),
                        type="library",
                        purl=pkg.get("externalRefs", [{}])[0].get("referenceLocator")
                        if pkg.get("externalRefs")
                        else None,
                        licenses=[pkg.get("licenseConcluded", "")],
                        supplier=pkg.get("supplier"),
                    )
                )

        return SBOM(
            format=sbom_format,
            tool=tool,
            project_dir=str(project_dir),
            components=components,
            metadata=data.get("metadata", data.get("creationInfo", {})),
            raw_output=data,
        )

    # -------------------------------------------------------------------------
    # Quality Gate Check
    # -------------------------------------------------------------------------

    def check_quality_gate(
        self,
        project_dir: Path,
        fail_threshold: str = "HIGH",
        max_vulnerabilities: int = 0,
        tool: str | None = None,
    ) -> QualityGateResult:
        """Check dependency quality gate (fail on vulnerabilities).

        Args:
            project_dir: Directory to scan.
            fail_threshold: Minimum severity to fail (CRITICAL, HIGH, MEDIUM, LOW).
            max_vulnerabilities: Maximum allowed vulnerabilities (0 = fail on any).
            tool: Tool to use for scanning.

        Returns:
            QualityGateResult with pass/fail status.
        """
        report = self.scan_dependencies(project_dir, tool=tool)

        # Determine which severities count toward failure
        threshold_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        threshold_idx = threshold_order.index(fail_threshold.upper())
        failing_severities = threshold_order[threshold_idx:]

        # Count vulnerabilities at or above threshold
        failing_count = sum(
            1 for v in report.vulnerabilities if v.severity.value in failing_severities
        )

        passed = failing_count <= max_vulnerabilities

        base_message = f"Found {failing_count} vulnerabilities at {fail_threshold} or above."
        message = (
            f"Quality gate PASSED. {base_message}"
            if passed
            else f"Quality gate FAILED. {base_message}"
        )

        return QualityGateResult(
            passed=passed,
            fail_threshold=fail_threshold,
            max_vulnerabilities=max_vulnerabilities,
            critical_count=report.count_by_severity(Severity.CRITICAL),
            high_count=report.count_by_severity(Severity.HIGH),
            medium_count=report.count_by_severity(Severity.MEDIUM),
            low_count=report.count_by_severity(Severity.LOW),
            message=message,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _run_tool(
        self,
        cmd: list[str],
        allow_nonzero: list[int] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run external tool with timeout and error handling.

        Args:
            cmd: Command to run.
            allow_nonzero: List of non-zero exit codes to allow (e.g., [1] for vulns found).

        Returns:
            CompletedProcess with stdout/stderr.

        Raises:
            ToolTimeoutError: If command times out.
            ToolExecutionError: If command fails unexpectedly.
        """
        allow_nonzero = allow_nonzero or []
        tool = cmd[0]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )

            # Check exit code
            if result.returncode != 0 and result.returncode not in allow_nonzero:
                raise ToolExecutionError(tool, result.returncode, result.stderr)

            return result

        except subprocess.TimeoutExpired as e:
            raise ToolTimeoutError(tool, self._timeout) from e
        except FileNotFoundError:
            raise ToolNotAvailableError(tool, [])

    def get_installation_guide(self) -> str:
        """Get installation guide for SCA tools."""
        return """
# SCA Tool Installation Guide

## Snyk CLI (free tier available)
  macOS:   brew install snyk-cli
  npm:     npm install -g snyk
  Binary:  curl https://static.snyk.io/cli/latest/install | sh

  After install: snyk auth  # Login to Snyk

## Trivy (open source)
  macOS:   brew install trivy
  Linux:   curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
  Docker:  docker pull aquasec/trivy

## Syft (open source, SBOM generation)
  macOS:   brew install syft
  Linux:   curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

## Grype (open source, vulnerability scanner)
  macOS:   brew install grype
  Linux:   curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

Recommended minimum: Install at least Trivy (all-in-one) or Snyk (best remediation advice).
"""


__all__ = [
    "ExternalSCAClient",
    "Severity",
    "ToolInfo",
    "Vulnerability",
    "VulnerabilityReport",
    "Component",
    "SBOM",
    "QualityGateResult",
    "SCAError",
    "ToolNotAvailableError",
    "ToolTimeoutError",
    "ToolExecutionError",
    "ToolOutputError",
]
