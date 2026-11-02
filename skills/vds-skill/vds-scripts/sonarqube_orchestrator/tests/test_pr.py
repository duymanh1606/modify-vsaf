"""Tests for PR decoration using Bitbucket Code Insights API.

Tests mock Bitbucket API calls to verify PR decoration functionality
without requiring real Bitbucket server access.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from vds_sonarqube_orchestrator.config import SonarqubeSettings
from vds_sonarqube_orchestrator.pr import (
    PRAnalysisStatus,
    PRAnalysisTimeoutError,
    PRDecorationResult,
    PRDecoratorError,
    PRNotFoundError,
    SonarqubePRDecorator,
)


@pytest.fixture
def mock_sonar_settings() -> SonarqubeSettings:
    """Mock SonarQube settings for testing."""
    settings = MagicMock(spec=SonarqubeSettings)
    settings.base_url = "http://sonar-test.example.com"
    settings.token = "test_token_12345"
    settings.project_key = "test-project"
    return settings


@pytest.fixture
def mock_bitbucket_settings() -> MagicMock:
    """Mock Bitbucket settings for testing."""
    settings = MagicMock()
    settings.is_cloud_mode = True
    return settings


@pytest.fixture
def mock_sonar_results() -> dict[str, Any]:
    """Mock SonarQube analysis results."""
    return {
        "issues": [
            {
                "key": "AX-GH1-JK2-LM3",
                "rule": "java:S117",
                "severity": "MINOR",
                "type": "CODE_SMELL",
                "message": "Remove this logging statement",
                "component": "com/example:src/main.java:42",
                "line": 42,
            },
            {
                "key": "AX-GH1-JK2-LM4",
                "rule": "java:S106",
                "severity": "MAJOR",
                "type": "CODE_SMELL",
                "message": "Use try-with-resources",
                "component": "com/example:src/main.java:100",
                "line": 100,
            },
        ],
        "bugs": "0",
        "vulnerabilities": "1",
        "code_smells": "5",
        "coverage": "75.5",
        "quality_gate": {
            "projectStatus": {
                "status": "OK",
                "conditions": [{"metricKey": "coverage", "actualValue": "75.5", "status": "OK"}],
            }
        },
    }


@pytest.fixture
def mock_pr_response() -> dict[str, Any]:
    """Mock Bitbucket PR response."""
    return {
        "id": "12345",
        "version": 1,
        "state": "OPEN",
        "fromRef": {
            "id": "ref-1",
            "displayId": "feature-branch",
            "latestCommit": "abc123def456",
        },
        "toRef": {
            "id": "ref-2",
            "displayId": "main",
        },
    }


class TestSonarqubePRDecorator:
    """Tests for SonarqubePRDecorator class."""

    def test_init(
        self, mock_sonar_settings: SonarqubeSettings, mock_bitbucket_settings: MagicMock
    ) -> None:
        """Test initialization."""
        decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)
        assert decorator._sonar_settings == mock_sonar_settings
        assert decorator._bitbucket_settings == mock_bitbucket_settings

    def test_decorate_pr_success(
        self,
        mock_sonar_settings: SonarqubeSettings,
        mock_bitbucket_settings: MagicMock,
        mock_sonar_results: dict[str, Any],
        mock_pr_response: dict[str, Any],
    ) -> None:
        """Test successful PR decoration."""
        decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

        # Mock the client getter methods
        mock_sonar_client = MagicMock()
        mock_sonar_client.get_quality_gate_status.return_value = mock_sonar_results["quality_gate"]
        mock_sonar_client.get_issues.return_value = mock_sonar_results["issues"]
        mock_sonar_client.get_measures.return_value = {
            "bugs": mock_sonar_results["bugs"],
            "vulnerabilities": mock_sonar_results["vulnerabilities"],
            "code_smells": mock_sonar_results["code_smells"],
            "coverage": mock_sonar_results["coverage"],
        }
        mock_sonar_client.__enter__ = MagicMock(return_value=mock_sonar_client)
        mock_sonar_client.__exit__ = MagicMock(return_value=False)

        mock_bb_client = MagicMock()
        mock_bb_client.get_pull_request.return_value = mock_pr_response
        mock_bb_client.create_code_insights_report.return_value = True
        mock_bb_client.add_code_insights_annotations_to_report.return_value = True

        # Patch the internal client getters
        with (
            patch.object(decorator, "_get_sonar_client", return_value=mock_sonar_client),
            patch.object(decorator, "_get_bitbucket_client", return_value=mock_bb_client),
        ):
            # Execute
            result = decorator.decorate_pr(
                project_key="INSURANCE",
                repo_slug="insurance-policy-business",
                pr_id=12345,
                sonar_project_key="insurance-policy-business",
            )

        # Verify result
        assert result.success is True
        assert result.report_key == "sonarqube-quality-gate"
        assert result.annotations_count == 2
        assert result.quality_gate_status == "OK"

        # Verify Bitbucket calls
        mock_bb_client.get_pull_request.assert_called_once_with(
            "INSURANCE", "insurance-policy-business", 12345
        )
        mock_bb_client.create_code_insights_report.assert_called_once()
        mock_bb_client.add_code_insights_annotations_to_report.assert_called_once()

    def test_decorate_pr_with_quality_gate_failed(
        self,
        mock_sonar_settings: SonarqubeSettings,
        mock_bitbucket_settings: MagicMock,
        mock_sonar_results: dict[str, Any],
        mock_pr_response: dict[str, Any],
    ) -> None:
        """Test PR decoration when quality gate fails."""
        # Setup QG failed
        failed_results = mock_sonar_results.copy()
        failed_results["quality_gate"]["projectStatus"]["status"] = "ERROR"

        decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

        # Mock the client getter methods
        mock_sonar_client = MagicMock()
        mock_sonar_client.get_quality_gate_status.return_value = failed_results["quality_gate"]
        mock_sonar_client.get_issues.return_value = failed_results["issues"]
        mock_sonar_client.get_measures.return_value = {
            "bugs": failed_results["bugs"],
            "vulnerabilities": failed_results["vulnerabilities"],
            "code_smells": failed_results["code_smells"],
            "coverage": failed_results["coverage"],
        }
        mock_sonar_client.__enter__ = MagicMock(return_value=mock_sonar_client)
        mock_sonar_client.__exit__ = MagicMock(return_value=False)

        mock_bb_client = MagicMock()
        mock_bb_client.get_pull_request.return_value = mock_pr_response
        mock_bb_client.create_code_insights_report.return_value = True
        mock_bb_client.add_code_insights_annotations_to_report.return_value = True

        # Patch the internal client getters
        with (
            patch.object(decorator, "_get_sonar_client", return_value=mock_sonar_client),
            patch.object(decorator, "_get_bitbucket_client", return_value=mock_bb_client),
        ):
            result = decorator.decorate_pr(
                project_key="INSURANCE",
                repo_slug="insurance-policy-business",
                pr_id=12345,
                sonar_project_key="insurance-policy-business",
            )

        # Verify result shows failed status
        assert result.success is True  # Decoration succeeded even if QG failed
        assert result.quality_gate_status == "ERROR"

    def test_decorate_pr_not_found(
        self,
        mock_sonar_settings: SonarqubeSettings,
        mock_bitbucket_settings: MagicMock,
    ) -> None:
        """Test PR decoration when PR is not found."""
        decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

        # Mock the client getter methods
        mock_bb_client = MagicMock()
        mock_bb_client.get_pull_request.return_value = None

        with patch.object(decorator, "_get_bitbucket_client", return_value=mock_bb_client):
            with pytest.raises(PRNotFoundError) as exc_info:
                decorator.decorate_pr(
                    project_key="INSURANCE",
                    repo_slug="insurance-policy-business",
                    pr_id=99999,
                )

            assert "not found" in str(exc_info.value)

    def test_decorate_pr_missing_project_key(
        self,
        mock_sonar_settings: SonarqubeSettings,
        mock_bitbucket_settings: MagicMock,
    ) -> None:
        """Test PR decoration when project key is not configured."""
        mock_sonar_settings.project_key = None

        decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

        # Mock the client getter methods
        mock_bb_client = MagicMock()
        mock_bb_client.get_pull_request.return_value = {"id": "123"}

        with patch.object(decorator, "_get_bitbucket_client", return_value=mock_bb_client):
            with pytest.raises(PRDecoratorError) as exc_info:
                decorator.decorate_pr(
                    project_key="INSURANCE",
                    repo_slug="insurance-policy-business",
                    pr_id=12345,
                )

            assert "project key is required" in str(exc_info.value)

    def test_build_metrics_data(
        self, mock_sonar_settings: SonarqubeSettings, mock_bitbucket_settings: MagicMock
    ) -> None:
        """Test metrics data building for Code Insights."""
        decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

        measures = {
            "bugs": "0",
            "vulnerabilities": "1",
            "code_smells": "5",
            "coverage": "75.5",
        }
        project_status = {
            "conditions": [{"metricKey": "coverage", "actualValue": "75.5", "status": "OK"}]
        }

        metrics = decorator._build_metrics_data(measures, project_status)

        assert len(metrics) == 5  # 4 metrics + 1 condition
        assert metrics[0]["title"] == "Bugs"
        assert metrics[0]["type"] == "NUMBER"
        assert metrics[0]["value"] == 0
        assert metrics[3]["title"] == "Coverage"
        assert metrics[3]["type"] == "PERCENTAGE"
        assert metrics[3]["value"] == 75.5

    def test_build_annotations(
        self, mock_sonar_settings: SonarqubeSettings, mock_bitbucket_settings: MagicMock
    ) -> None:
        """Test annotation building for Code Insights."""
        mock_sonar_settings.base_url = "http://sonar-test.example.com"
        decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

        issues = [
            {
                "key": "AX-123",
                "severity": "MAJOR",
                "type": "CODE_SMELL",
                "message": "Fix this issue",
                "component": "test-project:com/example/Main.java",
                "line": 50,
            }
        ]

        annotations = decorator._build_annotations(issues, "test-project")

        assert len(annotations) == 1
        assert annotations[0].severity == "MEDIUM"  # Mapped from MAJOR
        assert annotations[0].path == "com/example/Main.java"
        assert annotations[0].line == 50
        assert (
            annotations[0].link
            == "http://sonar-test.example.com/project/issues?id=test-project&issues=AX-123"
        )

    def test_get_pr_analysis_status(
        self,
        mock_sonar_settings: SonarqubeSettings,
        mock_bitbucket_settings: MagicMock,
    ) -> None:
        """Test getting PR analysis status."""
        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_sonar_client_cls:
            mock_sonar_client = MagicMock()
            mock_sonar_client.get_ce_activity.return_value = [
                {
                    "id": "AU-TpxcA-i5",
                    "status": "SUCCESS",
                    "componentKey": "test-project",
                    "analysisId": "analysis-123",
                    "submittedAt": "2025-01-01T00:00:00+0000",
                }
            ]
            mock_sonar_client.__enter__ = MagicMock(return_value=mock_sonar_client)
            mock_sonar_client.__exit__ = MagicMock(return_value=False)
            mock_sonar_client_cls.return_value = mock_sonar_client

            decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

            status = decorator.get_pr_analysis_status("test-project")

            assert status is not None
            assert status.task_id == "AU-TpxcA-i5"
            assert status.status == "SUCCESS"
            assert status.is_complete is True
            assert status.is_success is True

    def test_get_pr_analysis_status_no_tasks(
        self,
        mock_sonar_settings: SonarqubeSettings,
        mock_bitbucket_settings: MagicMock,
    ) -> None:
        """Test getting PR analysis status when no tasks found."""
        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_sonar_client_cls:
            mock_sonar_client = MagicMock()
            mock_sonar_client.get_ce_activity.return_value = []
            mock_sonar_client.__enter__ = MagicMock(return_value=mock_sonar_client)
            mock_sonar_client.__exit__ = MagicMock(return_value=False)
            mock_sonar_client_cls.return_value = mock_sonar_client

            decorator = SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings)

            status = decorator.get_pr_analysis_status("test-project")

            assert status is None

    def test_context_manager(
        self, mock_sonar_settings: SonarqubeSettings, mock_bitbucket_settings: MagicMock
    ) -> None:
        """Test using decorator as context manager."""
        with SonarqubePRDecorator(mock_sonar_settings, mock_bitbucket_settings) as decorator:
            assert decorator is not None
        # Client should be closed after exiting


class TestPRAnalysisStatus:
    """Tests for PRAnalysisStatus dataclass."""

    def test_to_dict(self) -> None:
        """Test PRAnalysisStatus serialization."""
        status = PRAnalysisStatus(
            task_id="AU-TpxcA-i5",
            status="SUCCESS",
            component_key="test-project",
            analysis_id="analysis-123",
        )

        data = status.to_dict()

        assert data["task_id"] == "AU-TpxcA-i5"
        assert data["status"] == "SUCCESS"
        assert data["is_complete"] is True
        assert data["is_success"] is True

    def test_is_complete(self) -> None:
        """Test is_complete property."""
        success_status = PRAnalysisStatus(task_id="1", status="SUCCESS")
        assert success_status.is_complete is True

        pending_status = PRAnalysisStatus(task_id="2", status="IN_PROGRESS")
        assert pending_status.is_complete is False

    def test_is_success(self) -> None:
        """Test is_success property."""
        success_status = PRAnalysisStatus(task_id="1", status="SUCCESS")
        assert success_status.is_success is True

        failed_status = PRAnalysisStatus(task_id="2", status="FAILED")
        assert failed_status.is_success is False


class TestPRDecorationResult:
    """Tests for PRDecorationResult dataclass."""

    def test_to_dict(self) -> None:
        """Test PRDecorationResult serialization."""
        result = PRDecorationResult(
            success=True,
            report_key="sonarqube-quality-gate",
            report_url="http://example.com",
            annotations_count=5,
            quality_gate_status="OK",
            metrics={"bugs": 0, "coverage": 80.0},
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["report_key"] == "sonarqube-quality-gate"
        assert data["report_url"] == "http://example.com"
        assert data["annotations_count"] == 5
        assert data["quality_gate_status"] == "OK"


class TestPRDecoratorError:
    """Tests for PRDecoratorError exception."""

    def test_error_with_context(self) -> None:
        """Test PRDecoratorError includes context."""
        error = PRDecoratorError(
            "Failed to decorate PR",
            context={"pr_id": "12345", "error": "Bitbucket API error"},
        )

        assert "Failed to decorate PR" in str(error)
        assert error.context["pr_id"] == "12345"

    def test_error_without_context(self) -> None:
        """Test PRDecoratorError works without context."""
        error = PRDecoratorError("Failed to decorate PR")
        assert "Failed to decorate PR" in str(error)


class TestPRAnalysisTimeoutError:
    """Tests for PRAnalysisTimeoutError exception."""

    def test_timeout_error(self) -> None:
        """Test PRAnalysisTimeoutError includes context."""
        error = PRAnalysisTimeoutError(
            "Analysis timed out", context={"project_key": "test", "elapsed": 300}
        )

        assert "timed out" in str(error)
        assert error.context["elapsed"] == 300


class TestPRNotFoundError:
    """Tests for PRNotFoundError exception."""

    def test_not_found_error(self) -> None:
        """Test PRNotFoundError includes context."""
        error = PRNotFoundError("PR not found", context={"project": "test", "pr_id": 999})

        assert "not found" in str(error)
        assert error.context["pr_id"] == 999
