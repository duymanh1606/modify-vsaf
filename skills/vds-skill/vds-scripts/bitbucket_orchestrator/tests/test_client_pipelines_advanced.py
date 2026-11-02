from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import VDSClientError


class TestBitbucketClientPipelinesAdvanced:
    """Tests for BitbucketClient advanced pipeline operations."""

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
        pipeline = Mock()
        pipeline.data = {"uuid": "{pipeline}", "build_number": 42}
        pipelines = Mock()
        pipelines.get.return_value = pipeline
        pipeline.steps.return_value = []
        repository.pipelines = pipelines
        return repository

    def _mock_repository_with_step(self) -> Mock:
        repository = Mock()
        pipeline = Mock()
        pipeline.data = {"uuid": "{pipeline}", "build_number": 42}

        step = Mock()
        step.data = {"uuid": "{step}", "state": "COMPLETED", "duration_in_seconds": 120}
        pipeline.steps.return_value = [step]
        pipeline.step.return_value = step
        step.log.return_value = b"log output"

        pipelines = Mock()
        pipelines.get.return_value = pipeline
        repository.pipelines = pipelines
        return repository

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_pipeline_success(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        pipeline = client.get_pipeline("workspace", "repo", "{pipeline}")

        repository.pipelines.get.assert_called_once_with("{pipeline}")
        assert pipeline["build_number"] == 42

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_list_pipeline_steps_success(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository_with_step()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        steps = client.list_pipeline_steps("workspace", "repo", "{pipeline}")

        assert len(steps) == 1
        assert steps[0]["state"] == "COMPLETED"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_pipeline_step_success(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository_with_step()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        step = client.get_pipeline_step("workspace", "repo", "{pipeline}", "{step}")

        pipeline = repository.pipelines.get.return_value
        pipeline.step.assert_called_once_with("{step}")
        assert step["uuid"] == "{step}"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_pipeline_step_log_success(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository_with_step()
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        payload = client.get_pipeline_step_log("workspace", "repo", "{pipeline}", "{step}")

        assert payload["content"] == "log output"
        assert payload["size"] == len("log output")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_get_pipeline_step_log_with_range(
        self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository_with_step()
        step = repository.pipelines.get.return_value.step.return_value
        step.log.return_value = ("100", b"partial")
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        payload = client.get_pipeline_step_log("workspace", "repo", "{pipeline}", "{step}", start=0, end=50)

        assert payload["size"] == 100
        assert payload["content"] == "partial"
        assert payload["range_start"] == 0
        assert payload["range_end"] == 50

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_stop_pipeline_success(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository()
        pipeline = repository.pipelines.get.return_value
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        payload = client.stop_pipeline("workspace", "repo", "{pipeline}")

        pipeline.stop.assert_called_once_with()
        assert payload["status"] == "stopped"

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_pipeline_operations_require_cloud(
        self, mock_bitbucket_class: Mock, server_settings: BitbucketSettings
    ) -> None:
        client = BitbucketClient(server_settings)

        with pytest.raises(VDSClientError):
            client.get_pipeline("workspace", "repo", "{pipeline}")

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_pipeline_step_requires_fields(self, mock_bitbucket_class: Mock, cloud_settings: BitbucketSettings) -> None:
        client = BitbucketClient(cloud_settings)
        mock_bitbucket = Mock()
        mock_bitbucket.cloud = Mock()
        repository = self._mock_repository_with_step()
        pipeline = repository.pipelines.get.return_value
        pipeline.steps.return_value = []
        pipeline.step.side_effect = Exception("API error")
        mock_bitbucket.cloud.repositories.get.return_value = repository
        client._client = mock_bitbucket

        with pytest.raises(VDSClientError):
            client.get_pipeline_step("workspace", "repo", "{pipeline}", "{step}")
