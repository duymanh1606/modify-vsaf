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
    client.list_repository_issues.return_value = [
        {"id": 1, "title": "Bug", "state": "open"},
    ]
    client.get_repository_issue.return_value = {"id": 1, "title": "Bug"}
    client.create_repository_issue.return_value = {"id": 2, "title": "New issue"}
    client.update_repository_issue.return_value = {"id": 1, "title": "Updated"}
    return client


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_list_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "issue",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--query",
            'state = "open"',
            "--sort",
            "-updated_on",
        ],
    )

    assert result.exit_code == 0
    mock_client.list_repository_issues.assert_called_once_with(
        "workspace", "repository", query='state = "open"', sort="-updated_on"
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_get_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "issue",
            "get",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--issue-id",
            "1",
        ],
    )

    assert result.exit_code == 0
    mock_client.get_repository_issue.assert_called_once_with("workspace", "repository", "1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_create_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "issue",
            "create",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--title",
            "Bug",
            "--description",
            "Details",
            "--kind",
            "bug",
            "--priority",
            "critical",
        ],
    )

    assert result.exit_code == 0
    mock_client.create_repository_issue.assert_called_once_with(
        "workspace",
        "repository",
        "Bug",
        "Details",
        kind="bug",
        priority="critical",
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_create_requires_title(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "issue",
            "create",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code != 0
    mock_client.create_repository_issue.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_update_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "issue",
            "update",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--issue-id",
            "1",
            "--title",
            "Updated",
            "--state",
            "resolved",
        ],
    )

    assert result.exit_code == 0
    mock_client.update_repository_issue.assert_called_once_with(
        "workspace",
        "repository",
        "1",
        title="Updated",
        description=None,
        kind=None,
        priority=None,
        state="resolved",
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_update_requires_fields(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "issue",
            "update",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--issue-id",
            "1",
        ],
    )

    assert result.exit_code != 0
    mock_client.update_repository_issue.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_delete_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "issue",
            "delete",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--issue-id",
            "1",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.delete_repository_issue.assert_called_once_with("workspace", "repository", "1")


@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_issue_requires_cloud(mock_load: Mock, runner: CliRunner) -> None:
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "issue",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code != 0
    assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr
