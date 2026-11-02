from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import NotFoundError, VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_get_requires_id(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that dashboard get requires --dashboard-id."""
    runner = _runner()
    result = runner.invoke(app, ["dashboard", "get"])
    assert result.exit_code != 0
    assert "--dashboard-id required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_get_success_int(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful dashboard get with integer ID."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_dashboard.return_value = {"id": "10000", "name": "Test Dashboard"}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["dashboard", "get", "--dashboard-id", "10000"])
    assert result.exit_code == 0
    mock_adapter.get_dashboard.assert_called_once_with(10000)
    assert "Test Dashboard" in result.stdout or "10000" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_get_success_string(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful dashboard get with string ID."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_dashboard.return_value = {"id": "abc123", "name": "Test Dashboard"}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["dashboard", "get", "--dashboard-id", "abc123"])
    assert result.exit_code == 0
    mock_adapter.get_dashboard.assert_called_once_with("abc123")
    assert "Test Dashboard" in result.stdout or "abc123" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_list_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful dashboard list."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_dashboards.return_value = {
        "dashboards": [
            {"id": "10000", "name": "Dashboard 1"},
            {"id": "10001", "name": "Dashboard 2"},
        ]
    }
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["dashboard", "list"])
    assert result.exit_code == 0
    mock_adapter.get_dashboards.assert_called_once_with(filter="", start=0, limit=10)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_list_with_filter(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test dashboard list with filter and pagination."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_dashboards.return_value = {"dashboards": []}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["dashboard", "list", "--filter", "test", "--start", "10", "--limit", "20"])
    assert result.exit_code == 0
    mock_adapter.get_dashboards.assert_called_once_with(filter="test", start=10, limit=20)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_unknown_action(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that unknown action raises error."""
    runner = _runner()
    result = runner.invoke(app, ["dashboard", "unknown"])
    assert result.exit_code != 0
    assert "Unknown action" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_adapter_error(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that adapter errors are handled."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_dashboard.side_effect = VDSClientError("Adapter error")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["dashboard", "get", "--dashboard-id", "10000"])
    assert result.exit_code != 0
    assert "Error" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_dashboard_not_found(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that not found errors are handled."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_dashboard.side_effect = NotFoundError("Dashboard not found: 99999")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["dashboard", "get", "--dashboard-id", "99999"])
    assert result.exit_code != 0
    assert "Error" in result.stderr
