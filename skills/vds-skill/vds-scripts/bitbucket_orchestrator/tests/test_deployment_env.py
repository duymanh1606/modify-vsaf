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
    client.list_deployment_environments.return_value = [
        {"uuid": "{env}", "name": "Prod", "category": "production"},
    ]
    client.get_deployment_environment.return_value = {"uuid": "{env}", "name": "Prod", "category": "production"}
    client.list_deployment_environment_variables.return_value = [
        {"uuid": "{var}", "key": "API_URL", "secured": False},
    ]
    client.create_deployment_environment_variable.return_value = {"uuid": "{var}", "key": "API_URL", "secured": False}
    client.update_deployment_environment_variable.return_value = {"uuid": "{var}", "key": "API_URL", "secured": True}
    return client


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_list_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "deployment-env",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code == 0
    assert "Prod" in result.stdout or "deployment_environments" in result.stdout
    mock_client.list_deployment_environments.assert_called_once_with("workspace", "repository")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_get_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "--no-markdown",
            "deployment-env",
            "get",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--env-uuid",
            "{env}",
        ],
    )

    assert result.exit_code == 0
    mock_client.get_deployment_environment.assert_called_once_with("workspace", "repository", "{env}")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_vars_list_success(
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
            "deployment-env",
            "vars",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--env-uuid",
            "{env}",
            "--pagelen",
            "20",
        ],
    )

    assert result.exit_code == 0
    mock_client.list_deployment_environment_variables.assert_called_once_with(
        "workspace", "repository", "{env}", pagelen=20
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_vars_create_requires_yes(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "deployment-env",
            "vars",
            "create",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--env-uuid",
            "{env}",
            "--key",
            "API_URL",
            "--value",
            "https://",
        ],
    )

    assert result.exit_code != 0
    assert (
        "Refusing to create variable without --yes" in result.stdout
        or "Refusing to create variable without --yes" in result.stderr
    )
    mock_client.create_deployment_environment_variable.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_vars_create_success(
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
            "deployment-env",
            "vars",
            "create",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--env-uuid",
            "{env}",
            "--key",
            "API_URL",
            "--value",
            "https://",
            "--secured",
            "true",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.create_deployment_environment_variable.assert_called_once_with(
        "workspace",
        "repository",
        "{env}",
        "API_URL",
        "https://",
        secured=True,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_vars_update_requires_fields(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "deployment-env",
            "vars",
            "update",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--env-uuid",
            "{env}",
            "--var-uuid",
            "{var}",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "Provide at least one" in result.stdout or "Provide at least one" in result.stderr
    mock_client.update_deployment_environment_variable.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_vars_update_success(
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
            "deployment-env",
            "vars",
            "update",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--env-uuid",
            "{env}",
            "--var-uuid",
            "{var}",
            "--value",
            "rotate",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.update_deployment_environment_variable.assert_called_once_with(
        "workspace",
        "repository",
        "{env}",
        "{var}",
        key=None,
        value="rotate",
        secured=None,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_vars_delete_success(
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
            "deployment-env",
            "vars",
            "delete",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
            "--env-uuid",
            "{env}",
            "--var-uuid",
            "{var}",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.delete_deployment_environment_variable.assert_called_once_with(
        "workspace", "repository", "{env}", "{var}"
    )


@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_requires_cloud(mock_load: Mock, runner: CliRunner) -> None:
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "deployment-env",
            "list",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code != 0
    assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_deployment_env_unknown_action(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app,
        [
            "deployment-env",
            "unknown",
            "--workspace",
            "workspace",
            "--repo-slug",
            "repository",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
