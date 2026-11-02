"""Pull Request Integration for SonarQube using Bitbucket Code Insights.

This module provides PR decoration capabilities by integrating SonarQube analysis
results with Bitbucket Code Insights API. It leverages the vds-bitbucket-orchestrator
for all Bitbucket API interactions.

Example:
    >>> from vds_sonarqube_orchestrator.pr import SonarqubePRDecorator
    >>> decorator = SonarqubePRDecorator(sonar_settings, bitbucket_settings)
    >>> decorator.decorate_pr("PROJECT", "repo-slug", 123)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from vds_bitbucket_orchestrator.client import BitbucketClient
    from vds_bitbucket_orchestrator.config import BitbucketSettings

    from vds_sonarqube_orchestrator.client import SonarqubeClient
    from vds_sonarqube_orchestrator.config import SonarqubeSettings

logger = structlog.get_logger(__name__)


class PRDecoratorError(Exception):
    """Base error for PR decoration operations."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class PRAnalysisTimeoutError(PRDecoratorError):
    """Raised when waiting for PR analysis times out."""


class PRNotFoundError(PRDecoratorError):
    """Raised when the specified PR is not found."""


@dataclass
class PRAnalysisStatus:
    """Status of a PR analysis task."""

    task_id: str
    status: str  # PENDING, IN_PROGRESS, SUCCESS, FAILED, CANCELED
    component_key: str | None = None
    analysis_id: str | None = None
    error_message: str | None = None
    submitted_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    @property
    def is_complete(self) -> bool:
        """Check if analysis is complete (success or failure)."""
        return self.status in ("SUCCESS", "FAILED", "CANCELED")

    @property
    def is_success(self) -> bool:
        """Check if analysis completed successfully."""
        return self.status == "SUCCESS"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "component_key": self.component_key,
            "analysis_id": self.analysis_id,
            "error_message": self.error_message,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "is_complete": self.is_complete,
            "is_success": self.is_success,
        }


@dataclass
class CodeInsightsAnnotation:
    """Annotation for Bitbucket Code Insights."""

    path: str
    line: int
    message: str
    severity: str  # LOW, MEDIUM, HIGH
    link: str | None = None
    external_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Bitbucket API format."""
        result: dict[str, Any] = {
            "path": self.path,
            "line": self.line,
            "message": self.message,
            "severity": self.severity,
        }
        if self.link:
            result["link"] = self.link
        if self.external_id:
            result["externalId"] = self.external_id
        return result


@dataclass
class PRDecorationResult:
    """Result of PR decoration operation."""

    success: bool
    report_key: str
    report_url: str | None = None
    annotations_count: int = 0
    quality_gate_status: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "report_key": self.report_key,
            "report_url": self.report_url,
            "annotations_count": self.annotations_count,
            "quality_gate_status": self.quality_gate_status,
            "metrics": self.metrics,
            "error_message": self.error_message,
        }


class SonarqubePRDecorator:
    """Decorator for Pull Requests using Bitbucket Code Insights.

    Integrates SonarQube analysis results with Bitbucket PRs by:
    1. Fetching quality gate status and issues from SonarQube
    2. Creating Code Insights reports on Bitbucket
    3. Adding annotations for individual issues

    Note: Requires Bitbucket Cloud mode for Code Insights API support.
    """

    REPORT_KEY = "sonarqube-quality-gate"
    REPORT_TITLE = "SonarQube Quality Gate"
    REPORT_REPORTER = "SonarQube"

    def __init__(
        self,
        sonar_settings: SonarqubeSettings,
        bitbucket_settings: BitbucketSettings,
    ) -> None:
        """Initialize the PR decorator.

        Args:
            sonar_settings: SonarQube configuration settings.
            bitbucket_settings: Bitbucket configuration settings.
        """
        self._sonar_settings = sonar_settings
        self._bitbucket_settings = bitbucket_settings
        self._sonar_client: SonarqubeClient | None = None
        self._bitbucket_client: BitbucketClient | None = None

    def _get_sonar_client(self) -> SonarqubeClient:
        """Get or create SonarQube client."""
        if self._sonar_client is None:
            from vds_sonarqube_orchestrator.client import SonarqubeClient

            self._sonar_client = SonarqubeClient(self._sonar_settings)
        return self._sonar_client

    def _get_bitbucket_client(self) -> BitbucketClient:
        """Get or create Bitbucket client."""
        if self._bitbucket_client is None:
            from vds_bitbucket_orchestrator.client import BitbucketClient

            self._bitbucket_client = BitbucketClient(self._bitbucket_settings)
        return self._bitbucket_client

    def decorate_pr(
        self,
        project_key: str,
        repo_slug: str,
        pr_id: int,
        sonar_project_key: str | None = None,
        branch: str | None = None,
    ) -> PRDecorationResult:
        """Decorate a PR with SonarQube analysis results.

        Args:
            project_key: Bitbucket project key.
            repo_slug: Repository slug.
            pr_id: Pull request ID.
            sonar_project_key: SonarQube project key (defaults to settings).
            branch: Branch name for analysis (defaults to PR source branch).

        Returns:
            PRDecorationResult with decoration status and details.

        Raises:
            PRNotFoundError: If the PR is not found.
            PRDecoratorError: If decoration fails.
        """
        sonar_key = sonar_project_key or self._sonar_settings.project_key
        if not sonar_key:
            raise PRDecoratorError("SonarQube project key is required")

        bb_client = self._get_bitbucket_client()
        sonar_client = self._get_sonar_client()

        try:
            # Get PR details
            pr = bb_client.get_pull_request(project_key, repo_slug, pr_id)
            if not pr:
                raise PRNotFoundError(
                    f"PR #{pr_id} not found",
                    {"project": project_key, "repo": repo_slug, "pr_id": pr_id},
                )

            # Get commit ID from PR
            commit_id = pr.get("fromRef", {}).get("latestCommit")
            if not commit_id:
                raise PRDecoratorError("Could not get commit ID from PR")

            # Get branch name if not provided
            if not branch:
                branch = pr.get("fromRef", {}).get("displayId")

            # Fetch SonarQube data
            with sonar_client:
                qg_status = sonar_client.get_quality_gate_status(sonar_key, branch)
                issues = sonar_client.get_issues(
                    project_key=sonar_key,
                    statuses=["OPEN", "CONFIRMED", "REOPENED"],
                    per_page=100,
                )
                measures = sonar_client.get_measures(
                    sonar_key,
                    ["bugs", "vulnerabilities", "code_smells", "coverage"],
                    branch,
                )

            # Determine quality gate result
            project_status = qg_status.get("projectStatus", {})
            qg_result = project_status.get("status", "UNKNOWN")
            report_result = "PASSED" if qg_result == "OK" else "FAILED"

            # Build metrics data for Code Insights
            metrics_data = self._build_metrics_data(measures, project_status)

            # Create Code Insights report
            report_url = f"{self._sonar_settings.base_url}/dashboard?id={sonar_key}"
            if branch:
                report_url += f"&branch={branch}"

            bb_client.create_code_insights_report(
                project_key=project_key,
                repo_slug=repo_slug,
                commit_id=commit_id,
                report_key=self.REPORT_KEY,
                title=self.REPORT_TITLE,
                reporter=self.REPORT_REPORTER,
                result=report_result,
                details=f"Quality Gate: {qg_result}",
                link=report_url,
                data=metrics_data,
            )

            # Add annotations for issues
            annotations = self._build_annotations(issues, sonar_key)
            if annotations:
                bb_client.add_code_insights_annotations_to_report(
                    project_key=project_key,
                    repo_slug=repo_slug,
                    commit_id=commit_id,
                    report_key=self.REPORT_KEY,
                    annotations=[a.to_dict() for a in annotations],
                )

            logger.info(
                "PR decorated successfully",
                project=project_key,
                repo=repo_slug,
                pr_id=pr_id,
                quality_gate=qg_result,
                annotations=len(annotations),
            )

            return PRDecorationResult(
                success=True,
                report_key=self.REPORT_KEY,
                report_url=report_url,
                annotations_count=len(annotations),
                quality_gate_status=qg_result,
                metrics=measures,
            )

        except PRDecoratorError:
            raise
        except Exception as exc:
            logger.exception("PR decoration failed", error=str(exc))
            raise PRDecoratorError(f"Failed to decorate PR: {exc}") from exc

    def get_pr_analysis_status(
        self,
        project_key: str,
        _branch: str | None = None,
    ) -> PRAnalysisStatus | None:
        """Get the status of the latest analysis for a project/branch.

        Args:
            project_key: SonarQube project key.
            branch: Branch name (optional).

        Returns:
            PRAnalysisStatus or None if no analysis found.
        """
        sonar_client = self._get_sonar_client()

        with sonar_client:
            # Use CE activity API to get latest task
            tasks = sonar_client.get_ce_activity(project_key, limit=1)

        if not tasks:
            return None

        task = tasks[0]
        return PRAnalysisStatus(
            task_id=task.get("id", ""),
            status=task.get("status", "UNKNOWN"),
            component_key=task.get("componentKey"),
            analysis_id=task.get("analysisId"),
            error_message=task.get("errorMessage"),
            submitted_at=task.get("submittedAt"),
            started_at=task.get("startedAt"),
            finished_at=task.get("executedAt"),
        )

    def wait_for_analysis(
        self,
        project_key: str,
        branch: str | None = None,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> PRAnalysisStatus:
        """Wait for PR analysis to complete.

        Args:
            project_key: SonarQube project key.
            branch: Branch name (optional).
            timeout: Maximum wait time in seconds.
            poll_interval: Time between status checks in seconds.

        Returns:
            Final PRAnalysisStatus.

        Raises:
            PRAnalysisTimeoutError: If analysis doesn't complete within timeout.
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise PRAnalysisTimeoutError(
                    f"Analysis did not complete within {timeout} seconds",
                    {"project_key": project_key, "branch": branch, "elapsed": elapsed},
                )

            status = self.get_pr_analysis_status(project_key, branch)
            if status and status.is_complete:
                return status

            logger.debug(
                "Waiting for analysis",
                project_key=project_key,
                status=status.status if status else "UNKNOWN",
                elapsed=elapsed,
            )

            time.sleep(poll_interval)

    def _build_metrics_data(
        self,
        measures: dict[str, Any],
        project_status: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build Code Insights data array from SonarQube measures."""
        data = []

        # Add key metrics
        metric_configs = [
            ("bugs", "Bugs", "NUMBER"),
            ("vulnerabilities", "Vulnerabilities", "NUMBER"),
            ("code_smells", "Code Smells", "NUMBER"),
            ("coverage", "Coverage", "PERCENTAGE"),
        ]

        for metric_key, title, data_type in metric_configs:
            if metric_key in measures:
                value = measures[metric_key]
                # Convert to appropriate type
                if data_type == "PERCENTAGE":
                    value = float(value) if value else 0.0
                else:
                    value = int(value) if value else 0

                data.append(
                    {
                        "title": title,
                        "type": data_type,
                        "value": value,
                    }
                )

        # Add quality gate conditions
        conditions = project_status.get("conditions", [])
        for cond in conditions[:5]:  # Limit to 5 conditions
            metric = cond.get("metricKey", cond.get("metric", ""))
            value = cond.get("actualValue", cond.get("value", ""))
            status = cond.get("status", "")

            if metric and value:
                data.append(
                    {
                        "title": f"{metric} ({status})",
                        "type": "TEXT",
                        "value": str(value),
                    }
                )

        return data

    def _build_annotations(
        self,
        issues: list[dict[str, Any]],
        sonar_project_key: str,
    ) -> list[CodeInsightsAnnotation]:
        """Build Code Insights annotations from SonarQube issues."""
        annotations = []

        # Map SonarQube severity to Code Insights severity
        severity_map = {
            "BLOCKER": "HIGH",
            "CRITICAL": "HIGH",
            "MAJOR": "MEDIUM",
            "MINOR": "LOW",
            "INFO": "LOW",
        }

        for issue in issues[:100]:  # Limit to 100 annotations
            component = issue.get("component", "")
            # Extract file path from component (format: project:path/to/file.java)
            path = component.split(":", 1)[1] if ":" in component else component

            line = issue.get("line", 1)
            message = issue.get("message", "")
            severity = severity_map.get(issue.get("severity", "INFO"), "LOW")
            issue_key = issue.get("key", "")

            # Build link to issue in SonarQube
            link = f"{self._sonar_settings.base_url}/project/issues?id={sonar_project_key}&issues={issue_key}"

            annotations.append(
                CodeInsightsAnnotation(
                    path=path,
                    line=line,
                    message=message[:450] if len(message) > 450 else message,
                    severity=severity,
                    link=link,
                    external_id=issue_key,
                )
            )

        return annotations

    def close(self) -> None:
        """Close any open connections."""
        if self._sonar_client:
            self._sonar_client.close()
            self._sonar_client = None
        # Bitbucket client doesn't need explicit closing

    def __enter__(self) -> SonarqubePRDecorator:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()


__all__ = [
    "SonarqubePRDecorator",
    "PRDecorationResult",
    "PRAnalysisStatus",
    "PRDecoratorError",
    "PRAnalysisTimeoutError",
    "PRNotFoundError",
    "CodeInsightsAnnotation",
]
