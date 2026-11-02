"""Tests for Bitbucket Cloud workspace CLI commands."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.errors import VDSClientError


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_client() -> Mock:
    """Create a mock client."""
    client = Mock()
    client.list_workspaces.return_value = [
        {"slug": "workspace1", "name": "Workspace 1"},
        {"slug": "workspace2", "name": "Workspace 2"},
    ]
    client.get_workspace.return_value = {"slug": "workspace1", "name": "Workspace 1", "uuid": "123"}
    client.get_workspace_permissions.return_value = [
        {"permission": "read", "user": {"display_name": "User 1"}},
    ]
    client.get_workspace_repository_permissions.return_value = [
        {"permission": "write", "repository": {"slug": "repo1"}},
    ]
    client.list_workspace_projects.return_value = [
        {"key": "PROJ1", "name": "Project 1"},
        {"key": "PROJ2", "name": "Project 2"},
    ]
    client.get_workspace_project.return_value = {"key": "PROJ1", "name": "Project 1"}
    return client


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_list_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    """Test workspace list command success."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(app, ["--no-markdown", "workspace", "list"])

    assert result.exit_code == 0
    assert "workspaces" in result.stdout or "workspace1" in result.stdout
    mock_client.list_workspaces.assert_called_once()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_list_requires_cloud_mode(mock_load: Mock, mock_build: Mock, runner: CliRunner) -> None:
    """Test workspace list command requires Cloud mode."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = False
    mock_load.return_value = mock_settings

    result = runner.invoke(app, ["workspace", "list"])

    assert result.exit_code != 0
    assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_get_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    """Test workspace get command success."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(app, ["--no-markdown", "workspace", "get", "--workspace-slug", "workspace1"])

    assert result.exit_code == 0
    assert "workspace" in result.stdout or "workspace1" in result.stdout
    mock_client.get_workspace.assert_called_once_with("workspace1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_get_missing_slug(mock_load: Mock, mock_build: Mock, runner: CliRunner) -> None:
    """Test workspace get command with missing workspace-slug."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings

    result = runner.invoke(app, ["workspace", "get"])

    assert result.exit_code != 0
    assert "workspace-slug required" in result.stdout or "workspace-slug required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_permissions_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    """Test workspace permissions command success."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(app, ["--no-markdown", "workspace", "permissions", "--workspace-slug", "workspace1"])

    assert result.exit_code == 0
    assert "permissions" in result.stdout
    mock_client.get_workspace_permissions.assert_called_once_with("workspace1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_permissions_with_repo(
    mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock
) -> None:
    """Test workspace permissions command with repo-slug."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app, ["--no-markdown", "workspace", "permissions", "--workspace-slug", "workspace1", "--repo-slug", "repo1"]
    )

    assert result.exit_code == 0
    assert "permissions" in result.stdout
    mock_client.get_workspace_repository_permissions.assert_called_once_with("workspace1", repo_slug="repo1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_projects_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    """Test workspace projects command success."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(app, ["--no-markdown", "workspace", "projects", "--workspace-slug", "workspace1"])

    assert result.exit_code == 0
    assert "projects" in result.stdout or "PROJ1" in result.stdout
    mock_client.list_workspace_projects.assert_called_once_with("workspace1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_project_success(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    """Test workspace project command success."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings
    mock_build.return_value.__enter__.return_value = mock_client

    result = runner.invoke(
        app, ["--no-markdown", "workspace", "project", "--workspace-slug", "workspace1", "--project-key", "PROJ1"]
    )

    assert result.exit_code == 0
    assert "project" in result.stdout or "PROJ1" in result.stdout
    mock_client.get_workspace_project.assert_called_once_with("workspace1", "PROJ1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_project_missing_key(mock_load: Mock, mock_build: Mock, runner: CliRunner) -> None:
    """Test workspace project command with missing project-key."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings

    result = runner.invoke(app, ["workspace", "project", "--workspace-slug", "workspace1"])

    assert result.exit_code != 0
    assert "project-key required" in result.stdout or "project-key required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_unknown_action(mock_load: Mock, mock_build: Mock, runner: CliRunner) -> None:
    """Test workspace command with unknown action."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings

    result = runner.invoke(app, ["workspace", "unknown"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_error_handling(mock_load: Mock, mock_build: Mock, runner: CliRunner, mock_client: Mock) -> None:
    """Test workspace command error handling."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = True
    mock_load.return_value = mock_settings
    mock_build.return_value.__enter__.return_value = mock_client
    mock_client.get_workspace.side_effect = VDSClientError("Workspace not found")

    result = runner.invoke(app, ["workspace", "get", "--workspace-slug", "nonexistent"])

    assert result.exit_code != 0
    assert "Error" in result.stdout or "Error" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_workspace_all_actions_require_cloud_mode(mock_load: Mock, mock_build: Mock, runner: CliRunner) -> None:
    """Test that all workspace actions require Cloud mode."""
    mock_settings = Mock()
    mock_settings.is_cloud_mode = False
    mock_load.return_value = mock_settings

    actions = ["list", "get", "permissions", "projects", "project"]
    for action in actions:
        args = ["workspace", action]
        if action != "list":
            args.extend(["--workspace-slug", "workspace1"])
        if action == "project":
            args.extend(["--project-key", "PROJ1"])

        result = runner.invoke(app, args)
        assert result.exit_code != 0, f"Action {action} should require Cloud mode"
        assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr
