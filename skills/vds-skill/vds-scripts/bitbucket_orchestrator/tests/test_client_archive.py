"""Tests for BitbucketClient.download_archive() method."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from vds_bitbucket_orchestrator.config import BitbucketSettings


@pytest.fixture
def mock_settings() -> BitbucketSettings:
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


class TestDownloadArchive:
    """BitbucketClient.download_archive() delegates to SDK."""

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_delegates_to_sdk(self, mock_bb_class: MagicMock, mock_settings: BitbucketSettings) -> None:
        from vds_bitbucket_orchestrator.client import BitbucketClient

        mock_sdk = mock_bb_class.return_value
        client = BitbucketClient(mock_settings)

        dest = io.BytesIO()
        client.download_archive("TEST", "repo", dest, at="master", format="zip")

        mock_sdk.download_repo_archive.assert_called_once_with(
            project_key="TEST",
            repository_slug="repo",
            dest_fd=dest,
            at="master",
            format="zip",
            path=None,
            prefix=None,
            chunk_size=8192,
        )

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_passes_path_and_prefix(self, mock_bb_class: MagicMock, mock_settings: BitbucketSettings) -> None:
        from vds_bitbucket_orchestrator.client import BitbucketClient

        mock_sdk = mock_bb_class.return_value
        client = BitbucketClient(mock_settings)

        dest = io.BytesIO()
        client.download_archive("PRJ", "my-repo", dest, format="tar.gz", path="src/", prefix="myprefix/")

        call_kwargs = mock_sdk.download_repo_archive.call_args.kwargs
        assert call_kwargs["path"] == "src/"
        assert call_kwargs["prefix"] == "myprefix/"
        assert call_kwargs["format"] == "tar.gz"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_error_handling(self, mock_bb_class: MagicMock, mock_settings: BitbucketSettings) -> None:
        from vds_bitbucket_orchestrator.client import BitbucketClient
        from vds_bitbucket_orchestrator.errors import VDSClientError

        mock_sdk = mock_bb_class.return_value
        mock_sdk.download_repo_archive.side_effect = Exception("404 Not Found")
        client = BitbucketClient(mock_settings)

        dest = io.BytesIO()
        with pytest.raises(VDSClientError):
            client.download_archive("TEST", "nonexistent", dest)
