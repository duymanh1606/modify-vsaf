from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_get_requires_issue_key(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that worklog get requires --issue-key."""
    runner = _runner()
    result = runner.invoke(app, ["worklog", "get"])
    assert result.exit_code != 0
    assert "--issue-key required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_get_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful worklog get."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_worklogs.return_value = {"worklogs": [{"id": "123", "timeSpent": "2h"}]}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["worklog", "get", "--issue-key", "NTTC-1"])
    assert result.exit_code == 0
    mock_adapter.get_worklogs.assert_called_once_with("NTTC-1")
    assert "NTTC-1" in result.stdout or "worklogs" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_add_requires_yes(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that worklog add requires --yes."""
    runner = _runner()
    result = runner.invoke(
        app,
        [
            "worklog",
            "add",
            "--issue-key",
            "NTTC-1",
            "--time-spent",
            "2h",
            "--comment",
            "Test",
        ],
    )
    assert result.exit_code != 0
    assert "Refusing to add worklog without --yes" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_add_requires_issue_key(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that worklog add requires --issue-key."""
    runner = _runner()
    result = runner.invoke(app, ["worklog", "add", "--time-spent", "2h", "--yes"])
    assert result.exit_code != 0
    assert "--issue-key required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_add_requires_time(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that worklog add requires --time-spent or --time-sec."""
    runner = _runner()
    result = runner.invoke(app, ["worklog", "add", "--issue-key", "NTTC-1", "--yes"])
    assert result.exit_code != 0
    assert "--time-spent or --time-sec required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_add_with_time_spent(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful worklog add with time-spent."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.issue_add_worklog.return_value = {"id": "123", "timeSpent": "2h"}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "worklog",
            "add",
            "--issue-key",
            "NTTC-1",
            "--time-spent",
            "2h",
            "--comment",
            "Test work",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.issue_add_worklog.assert_called_once_with(
        issue_key="NTTC-1",
        time_spent="2h",
        comment="Test work",
        started=None,
        time_sec=None,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_add_with_time_sec(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful worklog add with time-sec."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.issue_add_worklog.return_value = {
        "id": "123",
        "timeSpentSeconds": 7200,
    }
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "worklog",
            "add",
            "--issue-key",
            "NTTC-1",
            "--time-sec",
            "7200",
            "--started",
            "2025-11-12T10:00:00Z",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.issue_add_worklog.assert_called_once_with(
        issue_key="NTTC-1",
        time_spent="",
        comment=None,
        started="2025-11-12T10:00:00Z",
        time_sec=7200,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_updated_requires_since(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that worklog updated requires --since."""
    runner = _runner()
    result = runner.invoke(app, ["worklog", "updated"])
    assert result.exit_code != 0
    assert "--since required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_updated_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful worklog updated."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_updated_worklogs.return_value = {"values": [{"id": "123"}]}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["worklog", "updated", "--since", "2025-11-12 10:00:00"])
    assert result.exit_code == 0
    mock_adapter.get_updated_worklogs.assert_called_once_with("2025-11-12 10:00:00", expand=None)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_updated_with_expand(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test worklog updated with expand parameter."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_updated_worklogs.return_value = {"values": []}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "worklog",
            "updated",
            "--since",
            "2025-11-12 10:00:00",
            "--expand",
            "properties",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.get_updated_worklogs.assert_called_once_with("2025-11-12 10:00:00", expand="properties")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_deleted_requires_since(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that worklog deleted requires --since."""
    runner = _runner()
    result = runner.invoke(app, ["worklog", "deleted"])
    assert result.exit_code != 0
    assert "--since required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_deleted_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test successful worklog deleted."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_deleted_worklogs.return_value = {"values": [{"id": "123"}]}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["worklog", "deleted", "--since", "2025-11-12 10:00:00"])
    assert result.exit_code == 0
    mock_adapter.get_deleted_worklogs.assert_called_once_with("2025-11-12 10:00:00")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_unknown_action(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that unknown action raises error."""
    runner = _runner()
    result = runner.invoke(app, ["worklog", "unknown"])
    assert result.exit_code != 0
    assert "Unknown action" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_worklog_adapter_error(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    """Test that adapter errors are handled."""
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.get_worklogs.side_effect = VDSClientError("Adapter error")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["worklog", "get", "--issue-key", "NTTC-1"])
    assert result.exit_code != 0
    assert "Error" in result.stderr
