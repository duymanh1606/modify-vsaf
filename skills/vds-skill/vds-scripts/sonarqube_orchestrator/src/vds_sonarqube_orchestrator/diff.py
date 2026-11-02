"""Diff analysis for comparing SonarQube analysis results between commits/branches."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.config import SonarqubeSettings

logger = structlog.get_logger(__name__)


class DiffError(Exception):
    """Base error for diff operations."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


@dataclass
class IssueDiff:
    """Difference in issues between two analysis points."""

    new_issues: list[dict[str, Any]] = field(default_factory=list)
    resolved_issues: list[dict[str, Any]] = field(default_factory=list)
    unchanged_issues: int = 0

    @property
    def new_count(self) -> int:
        return len(self.new_issues)

    @property
    def resolved_count(self) -> int:
        return len(self.resolved_issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_issues": self.new_issues,
            "resolved_issues": self.resolved_issues,
            "new_count": self.new_count,
            "resolved_count": self.resolved_count,
            "unchanged_issues": self.unchanged_issues,
        }


@dataclass
class MetricDiff:
    """Difference in a metric between two analysis points."""

    metric: str
    before_value: float | int | None
    after_value: float | int | None

    @property
    def delta(self) -> float | int | None:
        if self.before_value is None or self.after_value is None:
            return None
        return self.after_value - self.before_value

    @property
    def improved(self) -> bool | None:
        if self.delta is None:
            return None
        negative_is_good = self.metric in (
            "bugs",
            "vulnerabilities",
            "code_smells",
            "duplicated_lines_density",
        )
        return self.delta < 0 if negative_is_good else self.delta > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "delta": self.delta,
            "improved": self.improved,
        }


@dataclass
class AnalysisDiff:
    """Complete diff between two analysis points."""

    project_key: str
    before_ref: str
    after_ref: str
    issues: IssueDiff = field(default_factory=IssueDiff)
    metrics: list[MetricDiff] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_key": self.project_key,
            "before_ref": self.before_ref,
            "after_ref": self.after_ref,
            "issues": self.issues.to_dict(),
            "metrics": [m.to_dict() for m in self.metrics],
        }


class DiffAnalyzer:
    """Analyzer for comparing SonarQube analysis results."""

    def __init__(self, settings: SonarqubeSettings) -> None:
        self._settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            from vds_sonarqube_orchestrator.client import SonarqubeClient

            self._client = SonarqubeClient(self._settings)
        return self._client

    def compare_branches(
        self,
        project_key: str,
        before_branch: str,
        after_branch: str,
        metrics: list[str] | None = None,
    ) -> AnalysisDiff:
        """Compare analysis results between two branches."""
        if metrics is None:
            metrics = ["bugs", "vulnerabilities", "code_smells", "coverage"]

        client = self._get_client()

        with client:
            before_measures = client.get_measures(project_key, metrics, before_branch)
            after_measures = client.get_measures(project_key, metrics, after_branch)

            before_issues = client.get_issues(project_key=project_key, per_page=500)
            after_issues = client.get_issues(project_key=project_key, per_page=500)

        metric_diffs = []
        for metric in metrics:
            metric_diffs.append(
                MetricDiff(
                    metric=metric,
                    before_value=before_measures.get(metric),
                    after_value=after_measures.get(metric),
                )
            )

        before_keys = {i.get("key") for i in before_issues}
        after_keys = {i.get("key") for i in after_issues}

        new_keys = after_keys - before_keys
        resolved_keys = before_keys - after_keys

        issue_diff = IssueDiff(
            new_issues=[i for i in after_issues if i.get("key") in new_keys],
            resolved_issues=[i for i in before_issues if i.get("key") in resolved_keys],
            unchanged_issues=len(before_keys & after_keys),
        )

        return AnalysisDiff(
            project_key=project_key,
            before_ref=before_branch,
            after_ref=after_branch,
            issues=issue_diff,
            metrics=metric_diffs,
        )

    def compare_with_new_code(
        self,
        project_key: str,
        branch: str | None = None,
    ) -> AnalysisDiff:
        """Compare current state with new code period."""
        client = self._get_client()

        with client:
            issues = client.get_issues(
                project_key=project_key,
                statuses=["OPEN", "CONFIRMED", "REOPENED"],
                per_page=500,
            )

        new_issues = [i for i in issues if i.get("isNew", False)]
        existing_issues = [i for i in issues if not i.get("isNew", False)]

        issue_diff = IssueDiff(
            new_issues=new_issues,
            resolved_issues=[],
            unchanged_issues=len(existing_issues),
        )

        return AnalysisDiff(
            project_key=project_key,
            before_ref="baseline",
            after_ref=branch or "current",
            issues=issue_diff,
            metrics=[],
        )

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> DiffAnalyzer:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = [
    "DiffAnalyzer",
    "AnalysisDiff",
    "IssueDiff",
    "MetricDiff",
    "DiffError",
]
