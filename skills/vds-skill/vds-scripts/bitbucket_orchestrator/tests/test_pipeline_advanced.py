from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_client() -> Mock:
    client = Mock()
    client.get_pipeline.return_value = {"uuid": "{pipeline}", "build_number": 42}
    client.list_pipeline_steps.return_value = [
        {"uuid": "{step}", "state": "COMPLETED", "duration_in_seconds": 120},
    ]
    client.get_pipeline_step.return_value = {"uuid": "{step}", "state": "COMPLETED"}
    client.get_pipeline_step_log.return_value = {"size": 10, "content": "log output"}
    client.stop_pipeline.return_value = {"status": "stopped", "pipeline_uuid": "{pipeline}"}
    return client


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_get_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pipeline-advanced",
            "get",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pipeline-uuid",
            "{pipeline}",
        ],
    )

    assert result.exit_code == 0
    assert "{pipeline}" in result.stdout
    mock_client.get_pipeline.assert_called_once_with("workspace", "repository", "{pipeline}")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_steps_success(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pipeline-advanced",
            "steps",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pipeline-uuid",
            "{pipeline}",
        ],
    )

    assert result.exit_code == 0
    assert "steps" in result.stdout
    mock_client.list_pipeline_steps.assert_called_once_with("workspace", "repository", "{pipeline}")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_step_success(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pipeline-advanced",
            "step",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pipeline-uuid",
            "{pipeline}",
            "--step-uuid",
            "{step}",
        ],
    )

    assert result.exit_code == 0
    mock_client.get_pipeline_step.assert_called_once_with("workspace", "repository", "{pipeline}", "{step}")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_log_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pipeline-advanced",
            "log",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pipeline-uuid",
            "{pipeline}",
            "--step-uuid",
            "{step}",
            "--start",
            "0",
            "--end",
            "50",
        ],
    )

    assert result.exit_code == 0
    assert "log output" in result.stdout
    mock_client.get_pipeline_step_log.assert_called_once_with(
        "workspace",
        "repository",
        "{pipeline}",
        "{step}",
        start=0,
        end=50,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_stop_requires_yes(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "pipeline-advanced",
            "stop",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pipeline-uuid",
            "{pipeline}",
        ],
    )

    assert result.exit_code != 0
    assert "Refusing to stop pipeline" in result.stdout or "Refusing to stop pipeline" in result.stderr
    mock_client.stop_pipeline.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_stop_success(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pipeline-advanced",
            "stop",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pipeline-uuid",
            "{pipeline}",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "stopped" in result.stdout
    mock_client.stop_pipeline.assert_called_once_with("workspace", "repository", "{pipeline}")


@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_requires_cloud(mock_load: Mock, runner: CliRunner) -> None:
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "pipeline-advanced",
            "get",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pipeline-uuid",
            "{pipeline}",
        ],
    )

    assert result.exit_code != 0
    assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pipeline_advanced_unknown_action(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "pipeline-advanced",
            "unknown",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
