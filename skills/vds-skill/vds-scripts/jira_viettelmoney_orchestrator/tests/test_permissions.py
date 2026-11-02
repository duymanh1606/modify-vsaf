"""Tests for JIRA permission CLI commands."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import VDSClientError


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_adapter() -> Mock:
    """Create a mock adapter."""
    adapter = Mock()
    adapter.get_all_permissions.return_value = [
        {"id": "ADMINISTER_PROJECTS", "name": "Administer Projects"},
        {"id": "BROWSE_PROJECTS", "name": "Browse Projects"},
    ]
    adapter.get_permissions.return_value = {
        "permissions": {
            "ADMINISTER_PROJECTS": {"havePermission": True},
            "BROWSE_PROJECTS": {"havePermission": True},
        }
    }
    adapter.get_project_permission_scheme.return_value = {
        "id": "10000",
        "name": "Default Permission Scheme",
        "permissions": [],
    }
    adapter.get_project_issue_security_scheme.return_value = {
        "id": "10000",
        "name": "Default Security Scheme",
        "levels": [],
    }
    return adapter


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permissions_all_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test permissions all command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["permissions", "all"])

    assert result.exit_code == 0
    assert "permissions" in result.stdout
    assert "ADMINISTER_PROJECTS" in result.stdout
    mock_adapter.get_all_permissions.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permissions_check_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test permissions check command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "permissions",
            "check",
            "--permissions",
            "ADMINISTER_PROJECTS,BROWSE_PROJECTS",
        ],
    )

    assert result.exit_code == 0
    assert "permissions" in result.stdout
    mock_adapter.get_permissions.assert_called_once_with(
        permissions=["ADMINISTER_PROJECTS", "BROWSE_PROJECTS"],
        project_key=None,
        issue_key=None,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permissions_check_with_project(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test permissions check command with project key."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "permissions",
            "check",
            "--permissions",
            "ADMINISTER_PROJECTS",
            "--project-key",
            "NTTC",
        ],
    )

    assert result.exit_code == 0
    mock_adapter.get_permissions.assert_called_once_with(
        permissions=["ADMINISTER_PROJECTS"],
        project_key="NTTC",
        issue_key=None,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permissions_check_with_issue(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test permissions check command with issue key."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "permissions",
            "check",
            "--permissions",
            "BROWSE_PROJECTS",
            "--issue-key",
            "NTTC-123",
        ],
    )

    assert result.exit_code == 0
    mock_adapter.get_permissions.assert_called_once_with(
        permissions=["BROWSE_PROJECTS"],
        project_key=None,
        issue_key="NTTC-123",
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permissions_check_missing_permissions(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test permissions check command with missing permissions."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["permissions", "check"])

    assert result.exit_code != 0
    assert (
        "permissions required" in result.stdout
        or "permissions required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permissions_unknown_action(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test permissions command with unknown action."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["permissions", "unknown"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permission_scheme_get_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test permission-scheme get command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["permission-scheme", "NTTC"])

    assert result.exit_code == 0
    assert "Default Permission Scheme" in result.stdout
    mock_adapter.get_project_permission_scheme.assert_called_once_with(
        "NTTC", expand=None
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permission_scheme_get_with_expand(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test permission-scheme get command with expand."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app, ["permission-scheme", "NTTC", "--expand", "permissions,user"]
    )

    assert result.exit_code == 0
    mock_adapter.get_project_permission_scheme.assert_called_once_with(
        "NTTC", expand="permissions,user"
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_security_scheme_get_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test issue-security-scheme get command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["issue-security-scheme", "NTTC"])

    assert result.exit_code == 0
    assert "Default Security Scheme" in result.stdout
    mock_adapter.get_project_issue_security_scheme.assert_called_once_with(
        "NTTC", only_levels=False
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_security_scheme_get_with_only_levels(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test issue-security-scheme get command with --only-levels."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["issue-security-scheme", "NTTC", "--only-levels"])

    assert result.exit_code == 0
    mock_adapter.get_project_issue_security_scheme.assert_called_once_with(
        "NTTC", only_levels=True
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_permissions_error_handling(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test permissions command error handling."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_all_permissions.side_effect = VDSClientError("Adapter error")

    result = runner.invoke(app, ["permissions", "all"])

    assert result.exit_code != 0
    assert "Error" in result.stdout or "Error" in result.stderr
