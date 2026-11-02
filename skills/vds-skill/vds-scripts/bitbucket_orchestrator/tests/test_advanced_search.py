"""Tests for Bitbucket advanced code search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError

runner = CliRunner()


@pytest.fixture
def mock_settings() -> BitbucketSettings:
    """Create cloud-mode settings for testing."""
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.org",
        BITBUCKET_MODE="cloud",
        BITBUCKET_CLOUD_WORKSPACE="test-workspace",
    )


@pytest.fixture
def mock_sdk_client() -> MagicMock:
    """Mock SDK client."""
    client = MagicMock()
    client.search_code.return_value = {"values": [{"file": {"path": "test.py"}}], "size": 1}
    return client


@pytest.fixture
def mock_client(mock_settings: BitbucketSettings, mock_sdk_client: MagicMock) -> BitbucketClient:
    """Create a BitbucketClient with mocked SDK."""
    with patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket", return_value=mock_sdk_client):
        client = BitbucketClient(mock_settings)
        client._client = mock_sdk_client
        return client


class TestSearchCodeAdvanced:
    """Tests for search_code_advanced method."""

    def test_search_code_advanced_success(self, mock_client: BitbucketClient, mock_sdk_client: MagicMock) -> None:
        """Test successful advanced code search."""
        result = mock_client.search_code_advanced("team", "test query", page=1, limit=20)

        assert result["size"] == 1
        mock_sdk_client.search_code.assert_called_once()

    def test_search_code_advanced_with_repository_filter(
        self, mock_client: BitbucketClient, mock_sdk_client: MagicMock
    ) -> None:
        """Test advanced code search with repository filter."""
        mock_sdk_client.search_code.return_value = {
            "values": [
                {"file": {"path": "test.py"}, "repository": {"slug": "repo1"}},
                {"file": {"path": "test2.py"}, "repository": {"slug": "repo2"}},
            ],
            "size": 2,
        }

        result = mock_client.search_code_advanced("team", "test", repository="repo1")

        assert result["size"] == 1
        assert result["values"][0]["repository"]["slug"] == "repo1"

    def test_search_code_advanced_cloud_only(self) -> None:
        """Test that search_code_advanced raises error in Server mode."""
        server_settings = BitbucketSettings(
            VDS_USERNAME="test_user",
            VDS_PASSWORD="test_pass",
            BITBUCKET_TOKEN="test_token",
            BITBUCKET_BASE_URL="http://bitbucket.server.com",
            BITBUCKET_MODE="server",
        )
        with patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket"):
            client = BitbucketClient(server_settings)
            with pytest.raises(VDSClientError, match="only available in Bitbucket Cloud"):
                client.search_code_advanced("team", "test")

    def test_search_code_advanced_handles_error(self, mock_client: BitbucketClient, mock_sdk_client: MagicMock) -> None:
        """Test search_code_advanced error handling."""
        mock_sdk_client.search_code.side_effect = Exception("API error")

        with pytest.raises(VDSClientError, match="search_code_advanced"):
            mock_client.search_code_advanced("team", "test")


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


@patch("vds_bitbucket_orchestrator.cli.load_settings")
@patch("vds_bitbucket_orchestrator.cli._build_client")
def test_cli_code_advanced_search_advanced_success(mock_build_client: MagicMock, mock_load_settings: MagicMock) -> None:
    """Test code-advanced search-advanced command success."""
    mock_client = MagicMock()
    mock_client.search_code_advanced.return_value = {"values": [{"file": {"path": "test.py"}}], "size": 1}
    mock_build_client.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        ["code-advanced", "search-advanced", "--team", "workspace", "--search-query", "test", "--repository", "repo"],
    )

    assert result.exit_code == 0
    mock_client.search_code_advanced.assert_called_once()


@patch("vds_bitbucket_orchestrator.cli.load_settings")
@patch("vds_bitbucket_orchestrator.cli._build_client")
def test_cli_code_advanced_search_advanced_requires_team(
    mock_build_client: MagicMock, mock_load_settings: MagicMock
) -> None:
    """Test code-advanced search-advanced requires team."""
    result = runner.invoke(app, ["code-advanced", "search-advanced", "--search-query", "test"])

    assert result.exit_code != 0
    assert "--team required" in result.stdout or "--team required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli.load_settings")
@patch("vds_bitbucket_orchestrator.cli._build_client")
def test_cli_code_advanced_search_advanced_requires_query(
    mock_build_client: MagicMock, mock_load_settings: MagicMock
) -> None:
    """Test code-advanced search-advanced requires search query."""
    result = runner.invoke(app, ["code-advanced", "search-advanced", "--team", "workspace"])

    assert result.exit_code != 0
    assert "--search-query required" in result.stdout or "--search-query required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli.load_settings")
@patch("vds_bitbucket_orchestrator.cli._build_client")
def test_cli_code_advanced_search_advanced_cloud_only(
    mock_build_client: MagicMock, mock_load_settings: MagicMock
) -> None:
    """Test code-advanced search-advanced requires Cloud mode."""
    mock_settings = MagicMock()
    mock_settings.is_cloud_mode = False
    mock_load_settings.return_value = mock_settings

    result = runner.invoke(app, ["code-advanced", "search-advanced", "--team", "workspace", "--search-query", "test"])

    assert result.exit_code != 0
    assert "Cloud" in result.stdout or "Cloud" in result.stderr
