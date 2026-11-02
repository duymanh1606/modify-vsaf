from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError


class TestBitbucketClientIssues:
    """Tests for BitbucketClient repository issue operations."""

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
        issues = Mock()
        issue = Mock()
        issue.data = {"id": 1, "title": "Bug", "state": "open"}
        issues.each.return_value = [issue]
        issues.create.return_value = issue
        issues.get.return_value = issue
        repository.issues = issues
        return repository

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_list_repository_issues_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        issues = client.list_repository_issues("workspace", "repo", query='state = "open"', sort="-updated_on")

        repository.issues.each.assert_called_once_with(q='state = "open"', sort="-updated_on")
        assert issues[0]["title"] == "Bug"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_create_repository_issue_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        issue = client.create_repository_issue(
            "workspace", "repo", "Bug found", "Details", kind="bug", priority="critical"
        )

        repository.issues.create.assert_called_once_with("Bug found", "Details", "bug", "critical")
        assert issue["id"] == 1

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_create_repository_issue_requires_title(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)

        with pytest.raises(VDSClientError):
            client.create_repository_issue("workspace", "repo", "")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_repository_issue_success(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        issue = client.get_repository_issue("workspace", "repo", 1)

        repository.issues.get.assert_called_once_with(1)
        assert issue["id"] == 1

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_update_repository_issue_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        issue = client.update_repository_issue(
            "workspace",
            "repo",
            1,
            title="New Title",
            kind="enhancement",
            priority="minor",
            state="resolved",
            description="Updated details",
        )

        issue_obj = repository.issues.get.return_value
        issue_obj.update.assert_called_once_with(
            title="New Title",
            kind="enhancement",
            priority="minor",
            state="resolved",
            content={"raw": "Updated details"},
        )
        assert issue["id"] == 1

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_update_repository_issue_requires_fields(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)

        with pytest.raises(VDSClientError):
            client.update_repository_issue("workspace", "repo", 1)

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_delete_repository_issue_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        client.delete_repository_issue("workspace", "repo", 1)

        repository.issues.get.assert_called_once_with(1)
        repository.issues.get.return_value.delete.assert_called_once_with()

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_issue_operations_require_cloud(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(server_settings)

        with pytest.raises(VDSClientError):
            client.list_repository_issues("workspace", "repo")
