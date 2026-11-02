from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError


class TestBitbucketClientRepositoryVariables:
    """Tests for BitbucketClient repository variable operations."""

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
        repository.repository_variables = Mock()
        variable = Mock()
        variable.data = {"uuid": "{uuid}", "key": "API_TOKEN", "secured": False, "value": "secret"}
        repository.repository_variables.each.return_value = [variable]
        repository.repository_variables.get.return_value = variable
        repository.repository_variables.create.return_value = variable
        variable.update.return_value = variable
        return repository

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_list_repository_variables_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        variables = client.list_repository_variables("workspace", "repo")

        mock_bitbucket.cloud.repositories.get.assert_called_once_with("workspace", "repo")
        assert len(variables) == 1
        assert variables[0]["key"] == "API_TOKEN"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_repository_variable_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        variable = client.get_repository_variable("workspace", "repo", "{uuid}")

        repository.repository_variables.get.assert_called_once_with("{uuid}")
        assert variable["key"] == "API_TOKEN"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_create_repository_variable_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        result = client.create_repository_variable("workspace", "repo", "API_TOKEN", "secret", secured=True)

        repository.repository_variables.create.assert_called_once_with("API_TOKEN", "secret", True)
        assert result["key"] == "API_TOKEN"
        assert result["secured"] is False  # mocked data

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_update_repository_variable_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        result = client.update_repository_variable(
            "workspace",
            "repo",
            "{uuid}",
            key="NEW_TOKEN",
            value="new-secret",
            secured=False,
        )

        repository.repository_variables.get.assert_called_once_with("{uuid}")
        repository.repository_variables.get.return_value.update.assert_called_once_with(
            key="NEW_TOKEN", value="new-secret", secured=False
        )
        assert result["key"] == "API_TOKEN"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_update_repository_variable_requires_fields(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.update_repository_variable("workspace", "repo", "{uuid}")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_delete_repository_variable_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        client.delete_repository_variable("workspace", "repo", "{uuid}")

        repository.repository_variables.get.assert_called_once_with("{uuid}")
        repository.repository_variables.get.return_value.delete.assert_called_once_with()

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_repository_variable_operations_require_cloud(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(server_settings)

        with pytest.raises(VDSClientError):
            client.list_repository_variables("workspace", "repo")
