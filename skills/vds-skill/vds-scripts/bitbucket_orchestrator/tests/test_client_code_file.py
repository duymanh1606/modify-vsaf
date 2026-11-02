from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings


class TestBitbucketClientCodeFile:
    """Tests for file content retrieval."""

    @pytest.fixture
    def server_settings(self) -> BitbucketSettings:
        return BitbucketSettings(
            VDS_USERNAME="test_user",
            VDS_PASSWORD="test_pass",
            BITBUCKET_BASE_URL="https://bitbucket.test.com",
            BITBUCKET_MODE="server",
        )

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_content_of_file_decodes_bytes(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(server_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.get_content_of_file.return_value = b"hello world"
        client._client = mock_bitbucket

        result = client.get_content_of_file("PRJ", "repo", "README.md")

        assert result == "hello world"
