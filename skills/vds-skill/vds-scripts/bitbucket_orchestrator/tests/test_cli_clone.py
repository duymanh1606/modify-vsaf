"""CLI tests for the clone command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.repo_ops import CloneResult, RepoRef


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_settings() -> BitbucketSettings:
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


class TestCloneCommand:
    """CLI integration tests for ``vds-cli bitbucket clone``."""

    @patch("vds_bitbucket_orchestrator.cli.clone_repo")
    @patch("vds_bitbucket_orchestrator.cli.build_clone_url")
    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_clone_success(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        mock_build_url: Mock,
        mock_clone: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
    ) -> None:
        mock_load.return_value = mock_settings
        client_mgr = MagicMock()
        client = client_mgr.__enter__.return_value
        client.get_repository.return_value = {"slug": "test-repo"}
        client.get_default_branch.return_value = {"displayId": "master"}
        mock_client_class.return_value = client_mgr
        mock_build_url.return_value = "http://test/scm/TEST/test-repo.git"

        ref = RepoRef(project_key="TEST", repo_slug="test-repo", source_format="shorthand")
        mock_clone.return_value = CloneResult(
            path=Path("/tmp/test"),
            operation="clone",
            branch="master",
            ref=ref,
        )

        with runner.isolated_filesystem():
            result = runner.invoke(app, ["clone", "TEST/test-repo"])

        assert result.exit_code == 0
        assert '"operation": "clone"' in result.stdout
        assert '"repo": "test-repo"' in result.stdout

    @patch("vds_bitbucket_orchestrator.cli.clone_repo")
    @patch("vds_bitbucket_orchestrator.cli.build_clone_url")
    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_clone_with_branch_and_shallow(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        mock_build_url: Mock,
        mock_clone: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
    ) -> None:
        mock_load.return_value = mock_settings
        client_mgr = MagicMock()
        client = client_mgr.__enter__.return_value
        client.get_repository.return_value = {"slug": "test-repo"}
        mock_client_class.return_value = client_mgr
        mock_build_url.return_value = "http://test/scm/TEST/test-repo.git"

        ref = RepoRef(project_key="TEST", repo_slug="test-repo", source_format="shorthand")
        mock_clone.return_value = CloneResult(
            path=Path("/tmp/test"),
            operation="clone",
            branch="develop",
            ref=ref,
        )

        with runner.isolated_filesystem():
            result = runner.invoke(app, ["clone", "TEST/test-repo", "--branch", "develop", "--shallow"])

        assert result.exit_code == 0
        mock_clone.assert_called_once()
        call_kwargs = mock_clone.call_args
        assert call_kwargs.kwargs.get("branch") == "develop"
        assert call_kwargs.kwargs.get("shallow") is True

    def test_clone_invalid_identifier(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["clone", "not-valid"])
        assert result.exit_code != 0

    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_clone_repo_not_found(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
    ) -> None:
        from vds_bitbucket_orchestrator.errors import NotFoundError

        mock_load.return_value = mock_settings
        client_mgr = MagicMock()
        client = client_mgr.__enter__.return_value
        client.get_repository.side_effect = NotFoundError("Repo not found")
        mock_client_class.return_value = client_mgr

        with runner.isolated_filesystem():
            result = runner.invoke(app, ["clone", "TEST/nonexistent"])

        assert result.exit_code != 0
