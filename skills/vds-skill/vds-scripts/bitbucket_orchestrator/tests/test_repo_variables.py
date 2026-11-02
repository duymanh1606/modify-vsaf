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
    client.list_repository_variables.return_value = [
        {"uuid": "{uuid}", "key": "API_TOKEN", "secured": True},
    ]
    client.get_repository_variable.return_value = {"uuid": "{uuid}", "key": "API_TOKEN", "secured": True}
    client.create_repository_variable.return_value = {"uuid": "{uuid}", "key": "API_TOKEN", "secured": True}
    client.update_repository_variable.return_value = {"uuid": "{uuid}", "key": "API_TOKEN", "secured": False}
    return client


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_list_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "repo-variables",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code == 0
    assert "API_TOKEN" in result.stdout
    mock_client.list_repository_variables.assert_called_once_with("workspace", "repository")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_get_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "repo-variables",
            "get",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--uuid",
            "{uuid}",
        ],
    )

    assert result.exit_code == 0
    mock_client.get_repository_variable.assert_called_once_with("workspace", "repository", "{uuid}")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_create_requires_yes(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "repo-variables",
            "create",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--key",
            "API_TOKEN",
            "--value",
            "secret",
        ],
    )

    assert result.exit_code != 0
    assert (
        "Refusing to create variable without --yes" in result.stdout
        or "Refusing to create variable without --yes" in result.stderr
    )
    mock_client.create_repository_variable.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_create_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "repo-variables",
            "create",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--key",
            "API_TOKEN",
            "--value",
            "secret",
            "--secured",
            "true",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.create_repository_variable.assert_called_once_with(
        "workspace",
        "repository",
        "API_TOKEN",
        "secret",
        secured=True,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_update_requires_fields(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "repo-variables",
            "update",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--uuid",
            "{uuid}",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "Provide at least one" in result.stdout or "Provide at least one" in result.stderr
    mock_client.update_repository_variable.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_update_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "repo-variables",
            "update",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--uuid",
            "{uuid}",
            "--value",
            "updated",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.update_repository_variable.assert_called_once_with(
        "workspace",
        "repository",
        "{uuid}",
        key=None,
        value="updated",
        secured=None,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_delete_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "repo-variables",
            "delete",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--uuid",
            "{uuid}",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.delete_repository_variable.assert_called_once_with("workspace", "repository", "{uuid}")


@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_variables_requires_cloud(mock_load: Mock, runner: CliRunner) -> None:
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "repo-variables",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code != 0
    assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr
