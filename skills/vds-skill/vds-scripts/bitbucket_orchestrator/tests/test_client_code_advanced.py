from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError


class TestBitbucketClientCodeAdvanced:
    """Test suite for BitbucketClient advanced code operations."""

    @pytest.fixture
    def server_settings(self) -> BitbucketSettings:
        """Create server mode settings for testing."""
        return BitbucketSettings(
            VDS_USERNAME="test_user",
            VDS_PASSWORD="test_pass",
            BITBUCKET_BASE_URL="https://bitbucket.test.com",
            BITBUCKET_MODE="server",
        )

    @pytest.fixture
    def cloud_settings(self) -> BitbucketSettings:
        """Create cloud mode settings for testing."""
        return BitbucketSettings(
            BITBUCKET_TOKEN="test_token",
            BITBUCKET_MODE="cloud",
            BITBUCKET_CLOUD_WORKSPACE="test_workspace",
        )

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_file_list_success(self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings) -> None:
        """Test successful file list retrieval."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_file_list.return_value = [{"path": "file1.py"}, {"path": "file2.py"}]
        client._client = mock_bitbucket

        result = client.get_file_list("PRJ", "repo", sub_folder="src", query="*.py", start=0, limit=100)

        mock_bitbucket.get_file_list.assert_called_once_with(
            "PRJ", "repo", sub_folder="src", query="*.py", start=0, limit=100
        )
        assert len(result) == 2
        assert result[0]["path"] == "file1.py"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_file_list_returns_empty_list(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        """Test that get_file_list returns empty list when client returns None."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_file_list.return_value = None
        client._client = mock_bitbucket

        result = client.get_file_list("PRJ", "repo")

        assert result == []

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_file_list_handles_error(self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings) -> None:
        """Test that get_file_list handles errors."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_file_list.side_effect = Exception("API error")
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.get_file_list("PRJ", "repo")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_commit_info_success(self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings) -> None:
        """Test successful commit info retrieval."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_commit_info.return_value = {"id": "abc123", "message": "Test commit"}
        client._client = mock_bitbucket

        result = client.get_commit_info("PRJ", "repo", "abc123", path="file.py")

        mock_bitbucket.get_commit_info.assert_called_once_with("PRJ", "repo", "abc123", path="file.py")
        assert result["id"] == "abc123"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_commit_info_handles_error(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        """Test that get_commit_info handles errors."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_commit_info.side_effect = Exception("API error")
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.get_commit_info("PRJ", "repo", "abc123")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_commit_changes_with_commit_id(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        """Test successful commit changes retrieval with commit_id."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_commit_changes.return_value = {"changes": []}
        client._client = mock_bitbucket

        result = client.get_commit_changes("PRJ", "repo", commit_id="abc123", merges="exclude")

        mock_bitbucket.get_commit_changes.assert_called_once_with(
            "PRJ", "repo", hash_newest=None, merges="exclude", commit_id="abc123"
        )
        assert result == {"changes": []}

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_commit_changes_with_hash_newest(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        """Test successful commit changes retrieval with hash_newest."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_commit_changes.return_value = {"changes": []}
        client._client = mock_bitbucket

        result = client.get_commit_changes("PRJ", "repo", hash_newest="def456", merges="include")

        mock_bitbucket.get_commit_changes.assert_called_once_with(
            "PRJ", "repo", hash_newest="def456", merges="include", commit_id=None
        )
        assert result == {"changes": []}

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_commit_changes_handles_error(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        """Test that get_commit_changes handles errors."""
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_commit_changes.side_effect = Exception("API error")
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.get_commit_changes("PRJ", "repo", commit_id="abc123")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_search_code_requires_cloud_mode(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        """Test that search_code requires Cloud mode."""
        client = BitbucketClient(server_settings)

        with pytest.raises(VDSClientError, match="Code search is only available in Bitbucket Cloud mode"):
            client.search_code("workspace", "test query")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_search_code_success(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        """Test successful code search in Cloud mode."""
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.search_code.return_value = {"values": [{"file": {"path": "file.py"}}]}
        client._client = mock_bitbucket

        result = client.search_code("workspace", "def test", page=1, limit=20)

        mock_bitbucket.search_code.assert_called_once_with("workspace", "def test", page=1, limit=20)
        assert "values" in result
        assert len(result["values"]) == 1

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_search_code_handles_error(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        """Test that search_code handles errors."""
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.search_code.side_effect = Exception("API error")
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.search_code("workspace", "test query")
