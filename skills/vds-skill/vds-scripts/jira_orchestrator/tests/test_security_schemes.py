"""Tests for JIRA issue security scheme CLI commands."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import NotFoundError, VDSClientError


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_adapter() -> Mock:
    """Create a mock adapter."""
    adapter = Mock()
    adapter.get_issue_security_schemes.return_value = [
        {
            "id": "10000",
            "name": "Default Security Scheme",
            "description": "Default scheme",
        },
        {
            "id": "10001",
            "name": "Project Security Scheme",
            "description": "Project-specific scheme",
        },
    ]
    adapter.get_issue_security_scheme.return_value = {
        "id": "10000",
        "name": "Default Security Scheme",
        "description": "Default scheme",
        "levels": [{"id": "10000", "name": "Level 1"}],
    }
    return adapter


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_security_scheme_list_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test security-scheme list command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["security-scheme", "list"])

    assert result.exit_code == 0
    assert "security_schemes" in result.stdout
    assert "Default Security Scheme" in result.stdout
    mock_adapter.get_issue_security_schemes.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_security_scheme_get_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test security-scheme get command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["security-scheme", "get", "--scheme-id", "10000"])

    assert result.exit_code == 0
    assert "Default Security Scheme" in result.stdout
    mock_adapter.get_issue_security_scheme.assert_called_once_with("10000", only_levels=False)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_security_scheme_get_with_only_levels(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test security-scheme get command with --only-levels flag."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["security-scheme", "get", "--scheme-id", "10000", "--only-levels"])

    assert result.exit_code == 0
    mock_adapter.get_issue_security_scheme.assert_called_once_with("10000", only_levels=True)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_security_scheme_get_missing_id(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    """Test security-scheme get command with missing scheme-id."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["security-scheme", "get"])

    assert result.exit_code != 0
    assert "scheme-id required" in result.stdout or "scheme-id required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_security_scheme_unknown_action(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    """Test security-scheme command with unknown action."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["security-scheme", "unknown"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_security_scheme_error_handling(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test security-scheme command error handling."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_issue_security_scheme.side_effect = NotFoundError("Security scheme not found")

    result = runner.invoke(app, ["security-scheme", "get", "--scheme-id", "99999"])

    assert result.exit_code != 0
    assert "Error" in result.stdout or "Error" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_security_scheme_adapter_error(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test security-scheme command adapter error handling."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_issue_security_schemes.side_effect = VDSClientError("Adapter error")

    result = runner.invoke(app, ["security-scheme", "list"])

    assert result.exit_code != 0
    assert "Error" in result.stdout or "Error" in result.stderr
