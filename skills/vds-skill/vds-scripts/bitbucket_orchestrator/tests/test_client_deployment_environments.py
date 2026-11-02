from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError


class TestBitbucketClientDeploymentEnvironments:
    """Tests for BitbucketClient deployment environment operations."""

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
        deployment_environments = Mock()
        environment = Mock()
        environment.data = {"uuid": "{env}", "name": "Prod", "category": "production"}
        deployment_environments.each.return_value = [environment]
        deployment_environments.get.return_value = environment
        repository.deployment_environments = deployment_environments

        env_variables = Mock()
        variable = Mock()
        variable.data = {"uuid": "{var}", "key": "API_URL", "secured": False}
        env_variables.each.return_value = [variable]
        env_variables.get.return_value = variable
        env_variables.create.return_value = variable
        environment.deployment_environment_variables = env_variables
        return repository

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_list_deployment_environments_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        environments = client.list_deployment_environments("workspace", "repo")

        mock_bitbucket.cloud.repositories.get.assert_called_once_with("workspace", "repo")
        assert len(environments) == 1
        assert environments[0]["name"] == "Prod"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_deployment_environment_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        environment = client.get_deployment_environment("workspace", "repo", "{env}")

        repository.deployment_environments.get.assert_called_once_with("{env}")
        assert environment["uuid"] == "{env}"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_list_deployment_environment_variables_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        variables = client.list_deployment_environment_variables("workspace", "repo", "{env}", pagelen=5)

        repository.deployment_environments.get.assert_called_once_with("{env}")
        environment = repository.deployment_environments.get.return_value
        environment.deployment_environment_variables.each.assert_called_once_with(pagelen=5)
        assert variables[0]["key"] == "API_URL"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_create_deployment_environment_variable_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        result = client.create_deployment_environment_variable("workspace", "repo", "{env}", "API_URL", "https://")

        repository.deployment_environments.get.assert_called_once_with("{env}")
        env = repository.deployment_environments.get.return_value
        env.deployment_environment_variables.create.assert_called_once_with("API_URL", "https://", False)
        assert result["key"] == "API_URL"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_update_deployment_environment_variable_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        result = client.update_deployment_environment_variable(
            "workspace", "repo", "{env}", "{var}", value="rotate", secured=True
        )

        env = repository.deployment_environments.get.return_value
        env.deployment_environment_variables.get.assert_called_once_with("{var}")
        env.deployment_environment_variables.get.return_value.update.assert_called_once_with(
            value="rotate", secured=True
        )
        assert result["key"] == "API_URL"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_update_deployment_environment_variable_requires_fields(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.update_deployment_environment_variable("workspace", "repo", "{env}", "{var}")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_delete_deployment_environment_variable_success(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        client.delete_deployment_environment_variable("workspace", "repo", "{env}", "{var}")

        env = repository.deployment_environments.get.return_value
        env.deployment_environment_variables.get.assert_called_once_with("{var}")
        env.deployment_environment_variables.get.return_value.delete.assert_called_once_with()

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_deployment_environment_operations_require_cloud(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(server_settings)

        with pytest.raises(VDSClientError):
            client.list_deployment_environments("workspace", "repo")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_deployment_environment_methods_handle_error(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        repository.deployment_environments.each.side_effect = Exception("API error")
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.list_deployment_environments("workspace", "repo")
