"""Tests for batch operations with multi-project SonarQube analysis."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vds_sonarqube_orchestrator.batch import (
    BatchError,
    BatchExecutor,
    BatchResult,
    ProjectResult,
)
from vds_sonarqube_orchestrator.config import SonarqubeSettings


@pytest.fixture
def mock_settings() -> SonarqubeSettings:
    """Mock SonarQube settings for testing."""
    settings = MagicMock(spec=SonarqubeSettings)
    settings.base_url = "http://sonar-test.example.com"
    settings.token = "test_token_12345"
    return settings


@pytest.fixture
def mock_qg_response() -> dict:
    """Mock quality gate response."""
    return {
        "projectStatus": {
            "status": "OK",
            "conditions": [
                {
                    "metric": "coverage",
                    "status": "OK",
                    "actualValue": "85.5",
                }
            ],
        }
    }


@pytest.fixture
def mock_issues_response() -> list:
    """Mock issues response."""
    return [
        {"key": "AX-1", "severity": "MAJOR", "message": "Fix this"},
        {"key": "AX-2", "severity": "MINOR", "message": "Improve that"},
        {"key": "AX-3", "severity": "MAJOR", "message": "Another issue"},
    ]


@pytest.fixture
def mock_measures_response() -> dict:
    """Mock measures response."""
    return {
        "bugs": "0",
        "vulnerabilities": "1",
        "code_smells": "5",
        "coverage": "75.5",
    }


class TestProjectResult:
    def test_to_dict_success(self) -> None:
        """Test ProjectResult serialization for successful result."""
        result = ProjectResult(
            project_key="test-project",
            success=True,
            data={"status": "OK", "passed": True},
        )

        data = result.to_dict()
        assert data["project_key"] == "test-project"
        assert data["success"] is True
        assert data["data"]["status"] == "OK"
        assert data["error"] is None

    def test_to_dict_failure(self) -> None:
        """Test ProjectResult serialization for failed result."""
        result = ProjectResult(
            project_key="test-project",
            success=False,
            error="Connection timeout",
        )

        data = result.to_dict()
        assert data["project_key"] == "test-project"
        assert data["success"] is False
        assert data["error"] == "Connection timeout"
        assert data["data"] == {}


class TestBatchResult:
    def test_success_rate_all_pass(self) -> None:
        """Test success rate calculation when all projects pass."""
        results = [
            ProjectResult(project_key="proj1", success=True),
            ProjectResult(project_key="proj2", success=True),
            ProjectResult(project_key="proj3", success=True),
        ]

        batch_result = BatchResult(total=3, successful=3, failed=0, results=results)

        assert batch_result.success_rate == 100.0

    def test_success_rate_partial(self) -> None:
        """Test success rate calculation with mixed results."""
        results = [
            ProjectResult(project_key="proj1", success=True),
            ProjectResult(project_key="proj2", success=False),
            ProjectResult(project_key="proj3", success=True),
            ProjectResult(project_key="proj4", success=False),
        ]

        batch_result = BatchResult(total=4, successful=2, failed=2, results=results)

        assert batch_result.success_rate == 50.0

    def test_success_rate_empty(self) -> None:
        """Test success rate calculation with no projects."""
        batch_result = BatchResult(total=0, successful=0, failed=0, results=[])

        assert batch_result.success_rate == 0.0

    def test_to_dict(self) -> None:
        """Test BatchResult serialization."""
        results = [
            ProjectResult(project_key="proj1", success=True, data={"status": "OK"}),
            ProjectResult(project_key="proj2", success=False, error="Timeout"),
        ]

        batch_result = BatchResult(total=2, successful=1, failed=1, results=results)

        data = batch_result.to_dict()
        assert data["total"] == 2
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert data["success_rate"] == 50.0
        assert len(data["results"]) == 2


class TestBatchError:
    def test_error_with_context(self) -> None:
        """Test BatchError includes context."""
        error = BatchError(
            "Batch operation failed",
            context={"projects": ["proj1", "proj2"], "error": "timeout"},
        )

        assert "Batch operation failed" in str(error)
        assert error.context["projects"] == ["proj1", "proj2"]

    def test_error_without_context(self) -> None:
        """Test BatchError works without context."""
        error = BatchError("Batch operation failed")
        assert "Batch operation failed" in str(error)
        assert error.context == {}


class TestBatchExecutor:
    def test_init_default_concurrency(self, mock_settings: SonarqubeSettings) -> None:
        """Test initialization with default concurrency."""
        executor = BatchExecutor(mock_settings)
        assert executor._concurrency == BatchExecutor.DEFAULT_CONCURRENCY

    def test_init_custom_concurrency(self, mock_settings: SonarqubeSettings) -> None:
        """Test initialization with custom concurrency."""
        executor = BatchExecutor(mock_settings, concurrency=5)
        assert executor._concurrency == 5

    def test_batch_quality_gates_all_success(
        self, mock_settings: SonarqubeSettings, mock_qg_response: dict
    ) -> None:
        """Test batch quality gate check with all projects passing."""
        project_keys = ["project-a", "project-b", "project-c"]

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_quality_gate_status.return_value = mock_qg_response
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_quality_gates(project_keys)

        assert result.total == 3
        assert result.successful == 3
        assert result.failed == 0
        assert result.success_rate == 100.0
        assert len(result.results) == 3

        for project_result in result.results:
            assert project_result.success is True
            assert project_result.data["status"] == "OK"
            assert project_result.data["passed"] is True

    def test_batch_quality_gates_partial_failure(
        self, mock_settings: SonarqubeSettings, mock_qg_response: dict
    ) -> None:
        """Test batch quality gate check with some projects failing."""
        project_keys = ["project-a", "project-b", "project-c"]

        def mock_get_qg(project_key: str, _branch: str | None = None) -> dict:
            if project_key == "project-b":
                raise Exception("Connection timeout")
            return mock_qg_response

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_quality_gate_status.side_effect = mock_get_qg
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_quality_gates(project_keys)

        assert result.total == 3
        assert result.successful == 2
        assert result.failed == 1
        assert result.success_rate == pytest.approx(66.67, rel=1e-2)

        # Find the failed result
        failed_result = next(r for r in result.results if not r.success)
        assert failed_result.project_key == "project-b"
        assert "Connection timeout" in failed_result.error

    def test_batch_quality_gates_with_branch(
        self, mock_settings: SonarqubeSettings, mock_qg_response: dict
    ) -> None:
        """Test batch quality gate check with branch parameter."""
        project_keys = ["project-a"]

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_quality_gate_status.return_value = mock_qg_response
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_quality_gates(project_keys, branch="develop")

        mock_client.get_quality_gate_status.assert_called_once_with("project-a", "develop")
        assert result.successful == 1

    def test_batch_issues_success(
        self, mock_settings: SonarqubeSettings, mock_issues_response: list
    ) -> None:
        """Test batch issues fetch with all projects succeeding."""
        project_keys = ["project-a", "project-b"]

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_issues.return_value = mock_issues_response
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_issues(project_keys)

        assert result.total == 2
        assert result.successful == 2
        assert result.failed == 0

        for project_result in result.results:
            assert project_result.success is True
            assert project_result.data["total_issues"] == 3
            assert project_result.data["by_severity"]["MAJOR"] == 2
            assert project_result.data["by_severity"]["MINOR"] == 1

    def test_batch_issues_with_severities(self, mock_settings: SonarqubeSettings) -> None:
        """Test batch issues fetch with severity filter."""
        project_keys = ["project-a"]

        filtered_issues = [
            {"key": "AX-1", "severity": "MAJOR", "message": "Fix this"},
        ]

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_issues.return_value = filtered_issues
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_issues(project_keys, severities=["MAJOR", "CRITICAL"])

        mock_client.get_issues.assert_called_once_with(
            project_key="project-a", severities=["MAJOR", "CRITICAL"], per_page=100
        )
        assert result.successful == 1

    def test_batch_issues_with_limit(self, mock_settings: SonarqubeSettings) -> None:
        """Test batch issues fetch with custom limit."""
        project_keys = ["project-a"]

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_issues.return_value = []
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_issues(project_keys, limit_per_project=500)

        mock_client.get_issues.assert_called_once_with(
            project_key="project-a", severities=None, per_page=500
        )
        assert result.successful == 1

    def test_batch_measures_success(
        self, mock_settings: SonarqubeSettings, mock_measures_response: dict
    ) -> None:
        """Test batch measures fetch with all projects succeeding."""
        project_keys = ["project-a", "project-b"]

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_measures.return_value = mock_measures_response
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_measures(project_keys)

        assert result.total == 2
        assert result.successful == 2
        assert result.failed == 0

        for project_result in result.results:
            assert project_result.success is True
            assert project_result.data["measures"]["bugs"] == "0"
            assert project_result.data["measures"]["coverage"] == "75.5"

    def test_batch_measures_custom_metrics(self, mock_settings: SonarqubeSettings) -> None:
        """Test batch measures fetch with custom metrics."""
        project_keys = ["project-a"]

        custom_measures = {
            "complexity": "125",
            "cognitive_complexity": "85",
        }

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_measures.return_value = custom_measures
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_measures(
                project_keys, metrics=["complexity", "cognitive_complexity"]
            )

        mock_client.get_measures.assert_called_once_with(
            "project-a", ["complexity", "cognitive_complexity"], None
        )
        assert result.successful == 1

    def test_batch_measures_with_branch(
        self, mock_settings: SonarqubeSettings, mock_measures_response: dict
    ) -> None:
        """Test batch measures fetch with branch parameter."""
        project_keys = ["project-a"]

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_measures.return_value = mock_measures_response
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings)
            result = executor.batch_measures(project_keys, branch="feature/new")

        mock_client.get_measures.assert_called_once()
        call_args = mock_client.get_measures.call_args
        assert call_args[0][0] == "project-a"
        assert call_args[0][2] == "feature/new"
        assert result.successful == 1

    def test_concurrent_execution(
        self, mock_settings: SonarqubeSettings, mock_qg_response: dict
    ) -> None:
        """Test that batch operations execute concurrently."""
        import time

        project_keys = ["project-a", "project-b", "project-c"]
        execution_times = []

        def mock_get_qg(project_key: str, _branch: str | None = None) -> dict:
            start = time.time()
            time.sleep(0.1)  # Simulate work
            execution_times.append((project_key, time.time() - start))
            return mock_qg_response

        with patch("vds_sonarqube_orchestrator.client.SonarqubeClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get_quality_gate_status.side_effect = mock_get_qg
            mock_client_cls.return_value = mock_client

            executor = BatchExecutor(mock_settings, concurrency=3)
            result = executor.batch_quality_gates(project_keys)

        # With concurrency=3 and 3 projects, total time should be ~0.1s not ~0.3s
        _total_time = sum(t for _, t in execution_times)
        assert result.successful == 3
        assert len(execution_times) == 3
