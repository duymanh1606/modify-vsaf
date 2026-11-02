"""Batch operations for multi-project SonarQube analysis."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.config import SonarqubeSettings

logger = structlog.get_logger(__name__)


class BatchError(Exception):
    """Base error for batch operations."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


@dataclass
class ProjectResult:
    """Result for a single project in batch operation."""

    project_key: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_key": self.project_key,
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


@dataclass
class BatchResult:
    """Aggregated result of batch operation."""

    total: int
    successful: int
    failed: int
    results: list[ProjectResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.successful / self.total * 100) if self.total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.success_rate,
            "results": [r.to_dict() for r in self.results],
        }


class BatchExecutor:
    """Executor for batch multi-project SonarQube operations."""

    DEFAULT_CONCURRENCY = 3

    def __init__(
        self,
        settings: SonarqubeSettings,
        concurrency: int | None = None,
    ) -> None:
        self._settings = settings
        self._concurrency = concurrency or self.DEFAULT_CONCURRENCY

    def batch_quality_gates(
        self,
        project_keys: list[str],
        branch: str | None = None,
    ) -> BatchResult:
        """Check quality gates for multiple projects in parallel."""
        from vds_sonarqube_orchestrator.client import SonarqubeClient

        results: list[ProjectResult] = []

        def check_project(project_key: str) -> ProjectResult:
            try:
                with SonarqubeClient(self._settings) as client:
                    qg_status = client.get_quality_gate_status(project_key, branch)
                    project_status = qg_status.get("projectStatus", {})
                    status = project_status.get("status", "UNKNOWN")
                    return ProjectResult(
                        project_key=project_key,
                        success=True,
                        data={
                            "status": status,
                            "passed": status == "OK",
                            "conditions": project_status.get("conditions", []),
                        },
                    )
            except Exception as exc:
                logger.warning("Quality gate check failed", project=project_key, error=str(exc))
                return ProjectResult(project_key=project_key, success=False, error=str(exc))

        with ThreadPoolExecutor(max_workers=self._concurrency) as executor:
            futures = {executor.submit(check_project, pk): pk for pk in project_keys}
            for future in as_completed(futures):
                results.append(future.result())

        successful = sum(1 for r in results if r.success)
        return BatchResult(
            total=len(project_keys),
            successful=successful,
            failed=len(project_keys) - successful,
            results=results,
        )

    def batch_issues(
        self,
        project_keys: list[str],
        severities: list[str] | None = None,
        limit_per_project: int = 100,
    ) -> BatchResult:
        """Fetch issues for multiple projects in parallel."""
        from vds_sonarqube_orchestrator.client import SonarqubeClient

        results: list[ProjectResult] = []

        def fetch_issues(project_key: str) -> ProjectResult:
            try:
                with SonarqubeClient(self._settings) as client:
                    issues = client.get_issues(
                        project_key=project_key,
                        severities=severities,
                        per_page=limit_per_project,
                    )
                    severity_counts: dict[str, int] = {}
                    for issue in issues:
                        sev = issue.get("severity", "UNKNOWN")
                        severity_counts[sev] = severity_counts.get(sev, 0) + 1

                    return ProjectResult(
                        project_key=project_key,
                        success=True,
                        data={
                            "total_issues": len(issues),
                            "by_severity": severity_counts,
                            "issues": issues,
                        },
                    )
            except Exception as exc:
                logger.warning("Issues fetch failed", project=project_key, error=str(exc))
                return ProjectResult(project_key=project_key, success=False, error=str(exc))

        with ThreadPoolExecutor(max_workers=self._concurrency) as executor:
            futures = {executor.submit(fetch_issues, pk): pk for pk in project_keys}
            for future in as_completed(futures):
                results.append(future.result())

        successful = sum(1 for r in results if r.success)
        return BatchResult(
            total=len(project_keys),
            successful=successful,
            failed=len(project_keys) - successful,
            results=results,
        )

    def batch_measures(
        self,
        project_keys: list[str],
        metrics: list[str] | None = None,
        branch: str | None = None,
    ) -> BatchResult:
        """Fetch measures for multiple projects in parallel."""
        from vds_sonarqube_orchestrator.client import SonarqubeClient

        if metrics is None:
            metrics = ["bugs", "vulnerabilities", "code_smells", "coverage"]

        results: list[ProjectResult] = []

        def fetch_measures(project_key: str) -> ProjectResult:
            try:
                with SonarqubeClient(self._settings) as client:
                    measures = client.get_measures(project_key, metrics, branch)
                    return ProjectResult(
                        project_key=project_key,
                        success=True,
                        data={"measures": measures},
                    )
            except Exception as exc:
                logger.warning("Measures fetch failed", project=project_key, error=str(exc))
                return ProjectResult(project_key=project_key, success=False, error=str(exc))

        with ThreadPoolExecutor(max_workers=self._concurrency) as executor:
            futures = {executor.submit(fetch_measures, pk): pk for pk in project_keys}
            for future in as_completed(futures):
                results.append(future.result())

        successful = sum(1 for r in results if r.success)
        return BatchResult(
            total=len(project_keys),
            successful=successful,
            failed=len(project_keys) - successful,
            results=results,
        )


__all__ = ["BatchExecutor", "BatchResult", "ProjectResult", "BatchError"]
