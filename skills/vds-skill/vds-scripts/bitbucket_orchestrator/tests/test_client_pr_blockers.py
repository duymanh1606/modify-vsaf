from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError


class TestBitbucketClientPullRequestBlockers:
    """Tests for BitbucketClient pull request blocker operations."""

    @pytest.fixture
    def cloud_settings(self) -> BitbucketSettings:
        return BitbucketSettings(
            BITBUCKET_TOKEN="token",
            BITBUCKET_MODE="cloud",
            BITBUCKET_CLOUD_WORKSPACE="workspace",
        )

    @pytest.fixture
    def server_settings(self) -> BitbucketSettings:
        return BitbucketSettings(
            VDS_USERNAME="user",
            VDS_PASSWORD="pass",
            BITBUCKET_BASE_URL="https://example.com",
            BITBUCKET_MODE="server",
        )

    def _mock_repository(self) -> Mock:
        repository = Mock()
        pull_request = Mock()
        pull_request.get.return_value = {"values": [{"uuid": "{blocker}", "message": "Fix tests"}]}
        pull_request.post.return_value = {"uuid": "{blocker}", "message": "Fix tests"}
        repository.pullrequests.get.return_value = pull_request
        return repository

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_list_pull_request_blockers_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        blockers = client.list_pull_request_blockers("workspace", "repo", 1, query='state = "OPEN"')

        repository.pullrequests.get.assert_called_once_with(1)
        pull_request = repository.pullrequests.get.return_value
        pull_request.get.assert_called_once_with("blockers", params={"q": 'state = "OPEN"'})
        assert blockers[0]["message"] == "Fix tests"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_add_pull_request_blocker_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        blocker = client.add_pull_request_blocker("workspace", "repo", 1, "Needs QA", reason="QA failure")

        pull_request = repository.pullrequests.get.return_value
        pull_request.post.assert_called_once_with(
            "blockers",
            {"message": "Needs QA", "reason": "QA failure"},
        )
        assert blocker["uuid"] == "{blocker}"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_delete_pull_request_blocker_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        client.delete_pull_request_blocker("workspace", "repo", 1, "{blocker}")

        pull_request = repository.pullrequests.get.return_value
        pull_request.delete.assert_called_once_with("blockers/{blocker}")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_add_pull_request_blocker_requires_message(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)

        with pytest.raises(VDSClientError):
            client.add_pull_request_blocker("workspace", "repo", 1, "")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_delete_pull_request_blocker_requires_uuid(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)

        with pytest.raises(VDSClientError):
            client.delete_pull_request_blocker("workspace", "repo", 1, "")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_pull_request_blocker_operations_require_cloud(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(server_settings)

        with pytest.raises(VDSClientError):
            client.list_pull_request_blockers("workspace", "repo", 1)
