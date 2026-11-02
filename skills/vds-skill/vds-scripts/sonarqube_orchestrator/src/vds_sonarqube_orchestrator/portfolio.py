"""Portfolio-level aggregation for multi-project SonarQube analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.config import SonarqubeSettings

logger = structlog.get_logger(__name__)


class PortfolioError(Exception):
    """Base error for portfolio operations."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


@dataclass
class PortfolioMetrics:
    """Aggregated metrics across a portfolio of projects."""

    total_projects: int
    total_bugs: int = 0
    total_vulnerabilities: int = 0
    total_code_smells: int = 0
    average_coverage: float = 0.0
    projects_passing_qg: int = 0
    projects_failing_qg: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)
    by_project: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def quality_gate_pass_rate(self) -> float:
        if self.total_projects == 0:
            return 0.0
        return (self.projects_passing_qg / self.total_projects) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_projects": self.total_projects,
            "total_bugs": self.total_bugs,
            "total_vulnerabilities": self.total_vulnerabilities,
            "total_code_smells": self.total_code_smells,
            "average_coverage": self.average_coverage,
            "projects_passing_qg": self.projects_passing_qg,
            "projects_failing_qg": self.projects_failing_qg,
            "quality_gate_pass_rate": self.quality_gate_pass_rate,
            "by_severity": self.by_severity,
            "by_project": self.by_project,
        }


@dataclass
class TopIssue:
    """Common issue appearing across multiple projects."""

    rule: str
    message: str
    severity: str
    count: int
    projects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
            "count": self.count,
            "projects": self.projects,
        }


class PortfolioManager:
    """Manager for portfolio-level SonarQube analysis."""

    def __init__(self, settings: SonarqubeSettings) -> None:
        self._settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            from vds_sonarqube_orchestrator.client import SonarqubeClient

            self._client = SonarqubeClient(self._settings)
        return self._client

    def get_portfolio_metrics(
        self,
        project_keys: list[str],
        branch: str | None = None,
    ) -> PortfolioMetrics:
        """Get aggregated metrics for a portfolio of projects."""
        client = self._get_client()

        metrics = PortfolioMetrics(total_projects=len(project_keys))
        coverage_values: list[float] = []

        with client:
            for project_key in project_keys:
                try:
                    measures = client.get_measures(
                        project_key,
                        ["bugs", "vulnerabilities", "code_smells", "coverage"],
                        branch,
                    )
                    qg_status = client.get_quality_gate_status(project_key, branch)

                    bugs = int(measures.get("bugs", 0) or 0)
                    vulns = int(measures.get("vulnerabilities", 0) or 0)
                    smells = int(measures.get("code_smells", 0) or 0)
                    coverage = float(measures.get("coverage", 0) or 0)

                    metrics.total_bugs += bugs
                    metrics.total_vulnerabilities += vulns
                    metrics.total_code_smells += smells
                    if coverage > 0:
                        coverage_values.append(coverage)

                    project_status = qg_status.get("projectStatus", {})
                    if project_status.get("status") == "OK":
                        metrics.projects_passing_qg += 1
                    else:
                        metrics.projects_failing_qg += 1

                    metrics.by_project[project_key] = {
                        "bugs": bugs,
                        "vulnerabilities": vulns,
                        "code_smells": smells,
                        "coverage": coverage,
                        "quality_gate": project_status.get("status", "UNKNOWN"),
                    }

                except Exception as exc:
                    logger.warning("Failed to fetch metrics", project=project_key, error=str(exc))
                    metrics.by_project[project_key] = {"error": str(exc)}

        if coverage_values:
            metrics.average_coverage = sum(coverage_values) / len(coverage_values)

        return metrics

    def get_issues_by_severity(
        self,
        project_keys: list[str],
    ) -> dict[str, int]:
        """Get issue counts by severity across all projects."""
        client = self._get_client()
        severity_counts: dict[str, int] = {}

        with client:
            for project_key in project_keys:
                try:
                    issues = client.get_issues(project_key=project_key, per_page=500)
                    for issue in issues:
                        sev = issue.get("severity", "UNKNOWN")
                        severity_counts[sev] = severity_counts.get(sev, 0) + 1
                except Exception as exc:
                    logger.warning("Failed to fetch issues", project=project_key, error=str(exc))

        return severity_counts

    def get_top_issues(
        self,
        project_keys: list[str],
        limit: int = 10,
    ) -> list[TopIssue]:
        """Get most common issues across all projects."""
        client = self._get_client()
        rule_counts: dict[str, dict[str, Any]] = {}

        with client:
            for project_key in project_keys:
                try:
                    issues = client.get_issues(project_key=project_key, per_page=200)
                    for issue in issues:
                        rule = issue.get("rule", "")
                        if rule not in rule_counts:
                            rule_counts[rule] = {
                                "message": issue.get("message", "")[:100],
                                "severity": issue.get("severity", "UNKNOWN"),
                                "count": 0,
                                "projects": set(),
                            }
                        rule_counts[rule]["count"] += 1
                        rule_counts[rule]["projects"].add(project_key)
                except Exception as exc:
                    logger.warning("Failed to fetch issues", project=project_key, error=str(exc))

        sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1]["count"], reverse=True)

        return [
            TopIssue(
                rule=rule,
                message=data["message"],
                severity=data["severity"],
                count=data["count"],
                projects=list(data["projects"]),
            )
            for rule, data in sorted_rules[:limit]
        ]

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> PortfolioManager:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = [
    "PortfolioManager",
    "PortfolioMetrics",
    "TopIssue",
    "PortfolioError",
]
