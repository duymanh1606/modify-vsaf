"""Tests for Bitbucket fork operations."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError

runner = CliRunner()


@pytest.fixture
def mock_settings() -> BitbucketSettings:
    """Create server-mode settings for testing."""
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


@pytest.fixture
def mock_sdk_client() -> MagicMock:
    """Mock SDK client."""
    client = MagicMock()
    client.fork_repository.return_value = {"slug": "repo-fork", "name": "Repository Fork"}
    client.fork_repository_new_project.return_value = {"slug": "new-repo", "name": "New Repository"}
    client.repo_list.return_value = [
        {"slug": "repo-fork", "name": "Repository Fork"},
        {"slug": "repo-fork-2", "name": "Repository Fork 2"},
    ]
    return client


@pytest.fixture
def mock_client(mock_settings: BitbucketSettings, mock_sdk_client: MagicMock) -> BitbucketClient:
    """Create a BitbucketClient with mocked SDK."""
    with patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket", return_value=mock_sdk_client):
        client = BitbucketClient(mock_settings)
        client._client = mock_sdk_client
        return client


class TestForkRepository:
    """Tests for fork_repository method."""

    def test_fork_repository_same_project(self, mock_client: BitbucketClient, mock_sdk_client: MagicMock) -> None:
        """Test forking repository within same project."""
        result = mock_client.fork_repository("PROJ", "repo", new_repository_slug="repo-fork")

        assert result == {"slug": "repo-fork", "name": "Repository Fork"}
        mock_sdk_client.fork_repository.assert_called_once_with("PROJ", "repo", "repo-fork")

    def test_fork_repository_same_project_default_name(
        self, mock_client: BitbucketClient, mock_sdk_client: MagicMock
    ) -> None:
        """Test forking repository within same project with default name."""
        result = mock_client.fork_repository("PROJ", "repo")

        assert result == {"slug": "repo-fork", "name": "Repository Fork"}
        mock_sdk_client.fork_repository.assert_called_once_with("PROJ", "repo", "repo-fork")

    def test_fork_repository_new_project(self, mock_client: BitbucketClient, mock_sdk_client: MagicMock) -> None:
        """Test forking repository to new project."""
        result = mock_client.fork_repository("PROJ", "repo", new_project_key="NEWPROJ", new_repository_slug="new-repo")

        assert result == {"slug": "new-repo", "name": "New Repository"}
        mock_sdk_client.fork_repository_new_project.assert_called_once_with("PROJ", "repo", "NEWPROJ", "new-repo")

    def test_fork_repository_new_project_default_name(
        self, mock_client: BitbucketClient, mock_sdk_client: MagicMock
    ) -> None:
        """Test forking repository to new project with default name."""
        result = mock_client.fork_repository("PROJ", "repo", new_project_key="NEWPROJ")

        assert result == {"slug": "new-repo", "name": "New Repository"}
        mock_sdk_client.fork_repository_new_project.assert_called_once_with("PROJ", "repo", "NEWPROJ", "repo")

    def test_fork_repository_handles_error(self, mock_client: BitbucketClient, mock_sdk_client: MagicMock) -> None:
        """Test fork_repository error handling."""
        mock_sdk_client.fork_repository.side_effect = Exception("Repository already exists")

        with pytest.raises(VDSClientError, match="fork_repository"):
            mock_client.fork_repository("PROJ", "repo", new_repository_slug="repo-fork")


class TestGetForkedRepositories:
    """Tests for get_forked_repositories method."""

    def test_get_forked_repositories_success(self, mock_client: BitbucketClient, mock_sdk_client: MagicMock) -> None:
        """Test getting forked repositories."""
        result = mock_client.get_forked_repositories("PROJ", "repo")

        assert len(result) == 2
        assert result[0]["slug"] == "repo-fork"
        mock_sdk_client.repo_list.assert_called_once()

    def test_get_forked_repositories_empty(self, mock_client: BitbucketClient, mock_sdk_client: MagicMock) -> None:
        """Test getting forked repositories when none exist."""
        mock_sdk_client.repo_list.return_value = []

        result = mock_client.get_forked_repositories("PROJ", "repo")

        assert result == []

    def test_get_forked_repositories_handles_error(
        self, mock_client: BitbucketClient, mock_sdk_client: MagicMock
    ) -> None:
        """Test get_forked_repositories error handling."""
        mock_sdk_client.repo_list.side_effect = Exception("Project not found")

        with pytest.raises(VDSClientError, match="get_forked_repositories"):
            mock_client.get_forked_repositories("PROJ", "repo")


class TestForkCLI:
    """Tests for fork CLI commands."""

    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    @patch("vds_bitbucket_orchestrator.cli._build_client")
    def test_fork_create_success(self, mock_build_client: Mock, mock_load_settings: Mock) -> None:
        """Test fork create command success."""
        mock_client = MagicMock()
        mock_client.fork_repository.return_value = {"slug": "repo-fork", "name": "Repository Fork"}
        mock_build_client.return_value.__enter__.return_value = mock_client

        result = runner.invoke(app, ["fork", "create", "PROJ", "repo", "--new-repo", "repo-fork", "--yes"])

        assert result.exit_code == 0
        assert "success" in result.stdout
        mock_client.fork_repository.assert_called_once_with("PROJ", "repo", None, "repo-fork")

    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    @patch("vds_bitbucket_orchestrator.cli._build_client")
    def test_fork_create_new_project(self, mock_build_client: Mock, mock_load_settings: Mock) -> None:
        """Test fork create command with new project."""
        mock_client = MagicMock()
        mock_client.fork_repository.return_value = {"slug": "new-repo", "name": "New Repository"}
        mock_build_client.return_value.__enter__.return_value = mock_client

        result = runner.invoke(
            app, ["fork", "create", "PROJ", "repo", "--new-project", "NEWPROJ", "--new-repo", "new-repo", "--yes"]
        )

        assert result.exit_code == 0
        assert "success" in result.stdout
        mock_client.fork_repository.assert_called_once_with("PROJ", "repo", "NEWPROJ", "new-repo")

    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    @patch("vds_bitbucket_orchestrator.cli._build_client")
    def test_fork_create_requires_yes(self, mock_build_client: Mock, mock_load_settings: Mock) -> None:
        """Test fork create requires --yes flag."""
        result = runner.invoke(app, ["fork", "create", "PROJ", "repo", "--new-repo", "repo-fork"])

        assert result.exit_code != 0
        assert "--yes" in result.stdout or "without --yes" in result.stdout or "Refusing" in result.stdout

    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    @patch("vds_bitbucket_orchestrator.cli._build_client")
    def test_fork_list_success(self, mock_build_client: Mock, mock_load_settings: Mock) -> None:
        """Test fork list command success."""
        mock_client = MagicMock()
        mock_client.get_forked_repositories.return_value = [
            {"slug": "repo-fork", "name": "Repository Fork"},
            {"slug": "repo-fork-2", "name": "Repository Fork 2"},
        ]
        mock_build_client.return_value.__enter__.return_value = mock_client

        result = runner.invoke(app, ["fork", "list", "PROJ", "repo"])

        assert result.exit_code == 0
        assert "forks" in result.stdout
        assert "count" in result.stdout
        mock_client.get_forked_repositories.assert_called_once_with("PROJ", "repo")

    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    @patch("vds_bitbucket_orchestrator.cli._build_client")
    def test_fork_invalid_action(self, mock_build_client: Mock, mock_load_settings: Mock) -> None:
        """Test fork command with invalid action."""
        result = runner.invoke(app, ["fork", "invalid", "PROJ", "repo"])

        assert result.exit_code != 0
        assert "Unknown action" in result.stdout or "Unknown action" in result.stderr

    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    @patch("vds_bitbucket_orchestrator.cli._build_client")
    def test_fork_create_handles_error(self, mock_build_client: Mock, mock_load_settings: Mock) -> None:
        """Test fork create command error handling."""
        mock_client = MagicMock()
        mock_client.fork_repository.side_effect = VDSClientError("Repository already exists")
        mock_build_client.return_value.__enter__.return_value = mock_client

        result = runner.invoke(app, ["fork", "create", "PROJ", "repo", "--new-repo", "repo-fork", "--yes"])

        assert result.exit_code != 0
        assert "Error" in result.stdout or "Error" in result.stderr
