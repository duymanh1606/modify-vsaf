from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.config import BitbucketSettings


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_settings() -> BitbucketSettings:
    """Create mock settings for testing."""
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


class TestBitbucketCLI:
    """Regression coverage for top-level Bitbucket CLI commands."""

    def test_version_option(self, runner: CliRunner) -> None:
        """`--version` should print the CLI version and exit cleanly."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "vds-bitbucket-orchestrator" in result.stdout

    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_projects_command_success(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
        sample_project_response: dict,
    ) -> None:
        """`projects` should call list_projects and emit JSON when --no-markdown is provided."""
        mock_load.return_value = mock_settings

        client_manager = MagicMock()
        client_instance = client_manager.__enter__.return_value
        client_instance.list_projects.return_value = [sample_project_response]
        mock_client_class.return_value = client_manager

        with runner.isolated_filesystem():
            result = runner.invoke(app, ["--report-dir", str(Path.cwd()), "projects", "--limit", "5"])
        assert result.exit_code == 0
        assert "Test Project" in result.stdout
        client_instance.list_projects.assert_called_once_with(limit=5)

    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_projects_command_handles_error(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
    ) -> None:
        """`projects` should exit non-zero when the client raises."""
        mock_load.return_value = mock_settings

        client_manager = MagicMock()
        client_instance = client_manager.__enter__.return_value
        client_instance.list_projects.side_effect = RuntimeError("boom")
        mock_client_class.return_value = client_manager

        with runner.isolated_filesystem():
            result = runner.invoke(app, ["projects"])

        assert result.exit_code != 0

    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_repositories_command_success(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
        sample_repository_response: dict,
    ) -> None:
        """`repositories` should call list_repositories with the provided project key."""
        mock_load.return_value = mock_settings

        client_manager = MagicMock()
        client_instance = client_manager.__enter__.return_value
        client_instance.list_repositories.return_value = [sample_repository_response]
        mock_client_class.return_value = client_manager

        with runner.isolated_filesystem():
            result = runner.invoke(app, ["--report-dir", str(Path.cwd()), "repositories", "TEST", "--limit", "7"])
        assert result.exit_code == 0
        assert "test-repo" in result.stdout
        client_instance.list_repositories.assert_called_once_with("TEST", limit=7)

    def test_repositories_missing_project_argument(self, runner: CliRunner) -> None:
        """`repositories` without the required project key should exit with usage error."""
        result = runner.invoke(app, ["repositories"])
        assert result.exit_code == 2
        assert "Missing argument 'PROJECT_KEY'" in (result.stdout or result.stderr)
