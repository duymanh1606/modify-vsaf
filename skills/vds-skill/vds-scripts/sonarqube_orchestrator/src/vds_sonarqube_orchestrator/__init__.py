"""VDS SonarQube Orchestrator - Code quality scanning and issue management.

Provides:
    - SonarqubeClient: Wrapper for python-sonarqube-api
    - SonarqubeScanner: Local scan orchestration (Maven/sonar-scanner)
    - load_settings(): Configuration loading from the shared VDS env layer
    - CLI: vds-sonarqube or vds-cli sonarqube --

Example:
    >>> from vds_sonarqube_orchestrator import SonarqubeClient, load_settings
    >>> settings = load_settings()
    >>> with SonarqubeClient(settings) as client:
    ...     health = client.ping()
    ...     print(health)
"""

from __future__ import annotations

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from vds_platform_core.http.errors import register_http_error_mapping

__version__ = "0.2.0"

from .errors import SERVICE_NAME as _SERVICE_NAME

for _status, _error_cls in (
    (401, AuthError),
    (403, ClientPermissionError),
    (404, NotFoundError),
    (409, ConflictError),
    (429, RateLimitError),
):
    register_http_error_mapping(_SERVICE_NAME, _status, _error_cls)
del _status, _error_cls


def __getattr__(name: str) -> object:
    if name == "SonarqubeClient":
        from vds_sonarqube_orchestrator.client import SonarqubeClient

        return SonarqubeClient
    if name == "SonarqubeScanner":
        from vds_sonarqube_orchestrator.scanner import SonarqubeScanner

        return SonarqubeScanner
    if name == "load_settings":
        from vds_sonarqube_orchestrator.config import load_settings

        return load_settings
    if name == "SonarqubeSettings":
        from vds_sonarqube_orchestrator.config import SonarqubeSettings

        return SonarqubeSettings
    if name == "SettingsError":
        from vds_sonarqube_orchestrator.config import SettingsError

        return SettingsError
    if name == "ExternalSCAClient":
        from vds_sonarqube_orchestrator.external_sca import ExternalSCAClient

        return ExternalSCAClient
    if name == "SCAError":
        from vds_sonarqube_orchestrator.external_sca import SCAError

        return SCAError
    if name == "ToolNotAvailableError":
        from vds_sonarqube_orchestrator.external_sca import ToolNotAvailableError

        return ToolNotAvailableError
    if name == "VulnerabilityReport":
        from vds_sonarqube_orchestrator.external_sca import VulnerabilityReport

        return VulnerabilityReport
    if name == "SBOM":
        from vds_sonarqube_orchestrator.external_sca import SBOM

        return SBOM
    if name == "SonarqubePRDecorator":
        from vds_sonarqube_orchestrator.pr import SonarqubePRDecorator

        return SonarqubePRDecorator
    if name == "PRDecorationResult":
        from vds_sonarqube_orchestrator.pr import PRDecorationResult

        return PRDecorationResult
    if name == "PRDecoratorError":
        from vds_sonarqube_orchestrator.pr import PRDecoratorError

        return PRDecoratorError
    if name == "BatchExecutor":
        from vds_sonarqube_orchestrator.batch import BatchExecutor

        return BatchExecutor
    if name == "BatchResult":
        from vds_sonarqube_orchestrator.batch import BatchResult

        return BatchResult
    if name == "SonarqubeReportGenerator":
        from vds_sonarqube_orchestrator.reports import SonarqubeReportGenerator

        return SonarqubeReportGenerator
    if name == "ReportError":
        from vds_sonarqube_orchestrator.reports import ReportError

        return ReportError
    if name == "WebhookManager":
        from vds_sonarqube_orchestrator.webhooks import WebhookManager

        return WebhookManager
    if name == "WebhookError":
        from vds_sonarqube_orchestrator.webhooks import WebhookError

        return WebhookError
    if name == "DiffAnalyzer":
        from vds_sonarqube_orchestrator.diff import DiffAnalyzer

        return DiffAnalyzer
    if name == "AnalysisDiff":
        from vds_sonarqube_orchestrator.diff import AnalysisDiff

        return AnalysisDiff
    if name == "PortfolioManager":
        from vds_sonarqube_orchestrator.portfolio import PortfolioManager

        return PortfolioManager
    if name == "PortfolioMetrics":
        from vds_sonarqube_orchestrator.portfolio import PortfolioMetrics

        return PortfolioMetrics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "SonarqubeClient",
    "SonarqubeScanner",
    "load_settings",
    "SonarqubeSettings",
    "SettingsError",
    "ExternalSCAClient",
    "SCAError",
    "ToolNotAvailableError",
    "VulnerabilityReport",
    "SBOM",
    "SonarqubePRDecorator",
    "PRDecorationResult",
    "PRDecoratorError",
    "BatchExecutor",
    "BatchResult",
    "SonarqubeReportGenerator",
    "ReportError",
    "WebhookManager",
    "WebhookError",
    "DiffAnalyzer",
    "AnalysisDiff",
    "PortfolioManager",
    "PortfolioMetrics",
]
