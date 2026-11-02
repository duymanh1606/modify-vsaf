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
    client.list_pull_request_blockers.return_value = [
        {"uuid": "{blocker}", "message": "Fix tests", "reason": "QA"},
    ]
    client.add_pull_request_blocker.return_value = {"uuid": "{blocker}", "message": "Fix tests"}
    return client


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pr_blocker_list_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pr-blocker",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pull-request-id",
            "1",
            "--search",
            "reason = QA",
        ],
    )

    assert result.exit_code == 0
    mock_client.list_pull_request_blockers.assert_called_once_with("workspace", "repository", "1", query="reason = QA")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pr_blocker_add_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pr-blocker",
            "add",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pull-request-id",
            "1",
            "--message",
            "Fix tests",
            "--reason",
            "QA",
        ],
    )

    assert result.exit_code == 0
    mock_client.add_pull_request_blocker.assert_called_once_with(
        "workspace",
        "repository",
        "1",
        "Fix tests",
        reason="QA",
        severity=None,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pr_blocker_delete_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "pr-blocker",
            "delete",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pull-request-id",
            "1",
            "--blocker-uuid",
            "{blocker}",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.delete_pull_request_blocker.assert_called_once_with("workspace", "repository", "1", "{blocker}")


@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pr_blocker_requires_cloud(mock_load: Mock, runner: CliRunner) -> None:
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "pr-blocker",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pull-request-id",
            "1",
        ],
    )

    assert result.exit_code != 0
    assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pr_blocker_add_requires_message(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "pr-blocker",
            "add",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pull-request-id",
            "1",
        ],
    )

    assert result.exit_code != 0
    assert "message" in result.stdout or "message" in result.stderr
    mock_client.add_pull_request_blocker.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_pr_blocker_delete_requires_yes(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "pr-blocker",
            "delete",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--pull-request-id",
            "1",
            "--blocker-uuid",
            "{blocker}",
        ],
    )

    assert result.exit_code != 0
    assert (
        "Refusing to delete blocker without --yes" in result.stdout
        or "Refusing to delete blocker without --yes" in result.stderr
    )
    mock_client.delete_pull_request_blocker.assert_not_called()
