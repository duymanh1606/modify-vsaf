"""CLI tests for the archive command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.repo_ops import ArchiveResult, RepoRef


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


class TestArchiveCommand:
    """CLI integration tests for ``vds-cli bitbucket archive``."""

    @patch("vds_bitbucket_orchestrator.cli.archive_repo")
    @patch("vds_bitbucket_orchestrator.cli.build_clone_url")
    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_archive_success(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        mock_build_url: Mock,
        mock_archive: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
    ) -> None:
        mock_load.return_value = mock_settings
        client_mgr = MagicMock()
        mock_client_class.return_value = client_mgr
        mock_build_url.return_value = "http://test/scm/TEST/test-repo.git"

        ref = RepoRef(project_key="TEST", repo_slug="test-repo", source_format="shorthand")
        mock_archive.return_value = ArchiveResult(
            archive_path=Path("/tmp/test-repo.zip"),
            format="zip",
            size_bytes=12345,
            method="rest_api",
            ref=ref,
        )

        with runner.isolated_filesystem():
            result = runner.invoke(app, ["archive", "TEST/test-repo"])

        assert result.exit_code == 0
        assert '"format": "zip"' in result.stdout
        assert '"method": "rest_api"' in result.stdout
        assert '"size_bytes": 12345' in result.stdout

    @patch("vds_bitbucket_orchestrator.cli.archive_repo")
    @patch("vds_bitbucket_orchestrator.cli.build_clone_url")
    @patch("vds_bitbucket_orchestrator.cli.BitbucketClient")
    @patch("vds_bitbucket_orchestrator.cli.load_settings")
    def test_archive_with_options(
        self,
        mock_load: Mock,
        mock_client_class: Mock,
        mock_build_url: Mock,
        mock_archive: Mock,
        runner: CliRunner,
        mock_settings: BitbucketSettings,
    ) -> None:
        mock_load.return_value = mock_settings
        client_mgr = MagicMock()
        mock_client_class.return_value = client_mgr
        mock_build_url.return_value = "http://test/scm/TEST/test-repo.git"

        ref = RepoRef(project_key="TEST", repo_slug="test-repo", source_format="shorthand")
        mock_archive.return_value = ArchiveResult(
            archive_path=Path("/tmp/custom.tar.gz"),
            format="tar.gz",
            size_bytes=67890,
            method="local_zip",
            ref=ref,
        )

        with runner.isolated_filesystem():
            result = runner.invoke(
                app,
                [
                    "archive",
                    "TEST/test-repo",
                    "--output",
                    "/tmp/custom.tar.gz",
                    "--format",
                    "tar.gz",
                    "--branch",
                    "develop",
                    "--path",
                    "src/",
                ],
            )

        assert result.exit_code == 0
        mock_archive.assert_called_once()
        call_kwargs = mock_archive.call_args.kwargs
        assert call_kwargs["format"] == "tar.gz"
        assert call_kwargs["at"] == "develop"
        assert call_kwargs["path"] == "src/"

    def test_archive_invalid_identifier(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["archive", "not-valid"])
        assert result.exit_code != 0
