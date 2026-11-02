from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_transitions_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful transitions get."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_issue_transitions.return_value = [
        {"id": "1", "name": "To Do"},
        {"id": "2", "name": "In Progress"},
    ]
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["transitions", "NTTC-1"])
    assert result.exit_code == 0
    mock_adapter.get_issue_transitions.assert_called_once_with("NTTC-1")
    assert "To Do" in result.stdout or "In Progress" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_transitions_adapter_error(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that adapter errors are handled."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_issue_transitions.side_effect = VDSClientError("Adapter error")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["transitions", "NTTC-1"])
    assert result.exit_code != 0
    assert "Error" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_changelog_get_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful changelog get."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_issue_changelog.return_value = {"histories": [{"id": "1", "created": "2025-11-12T10:00:00Z"}]}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["changelog", "get", "NTTC-1"])
    assert result.exit_code == 0
    mock_adapter.get_issue_changelog.assert_called_once_with("NTTC-1", start=None, limit=None)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_changelog_get_with_pagination(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test changelog get with pagination."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_issue_changelog.return_value = {"histories": []}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["changelog", "get", "NTTC-1", "--start", "10", "--limit", "20"])
    assert result.exit_code == 0
    mock_adapter.get_issue_changelog.assert_called_once_with("NTTC-1", start=10, limit=20)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_changelog_status_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful changelog status."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_issue_status_changelog.return_value = {"histories": [{"id": "1", "items": [{"field": "status"}]}]}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["changelog", "status", "NTTC-1"])
    assert result.exit_code == 0
    mock_adapter.get_issue_status_changelog.assert_called_once_with("NTTC-1")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_changelog_unknown_action(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that unknown action raises error."""
    runner = _runner()
    result = runner.invoke(app, ["changelog", "unknown", "NTTC-1"])
    assert result.exit_code != 0
    assert "Unknown action" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_changelog_adapter_error(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that adapter errors are handled."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_issue_changelog.side_effect = VDSClientError("Adapter error")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["changelog", "get", "NTTC-1"])
    assert result.exit_code != 0
    assert "Error" in result.stderr
