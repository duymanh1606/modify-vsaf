from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_backlog_move_requires_yes(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    result = runner.invoke(app, ["backlog", "move", "--issues", "NTTC-1,NTTC-2"])
    assert result.exit_code != 0
    assert "Refusing to modify backlog without --yes" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_backlog_move_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["backlog", "move", "--issues", "NTTC-1,NTTC-2", "--yes"])
    assert result.exit_code == 0
    mock_adapter.move_issues_to_backlog.assert_called_once_with(["NTTC-1", "NTTC-2"])


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_backlog_move_trims_whitespace(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["backlog", "move", "--issues", "NTTC-1 , NTTC-2 ", "--yes"])
    assert result.exit_code == 0
    mock_adapter.move_issues_to_backlog.assert_called_once_with(["NTTC-1", "NTTC-2"])


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_backlog_add(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["backlog", "add", "--issues", "NTTC-1,NTTC-2", "--yes"])
    assert result.exit_code == 0
    mock_adapter.add_issues_to_backlog.assert_called_once_with(["NTTC-1", "NTTC-2"])


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_backlog_add_adapter_error(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.add_issues_to_backlog.side_effect = VDSClientError("kaboom")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["backlog", "add", "--issues", "NTTC-1", "--yes"])
    assert result.exit_code != 0
    assert "Error: kaboom" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_backlog_requires_issues(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    result = runner.invoke(app, ["backlog", "add", "--yes"])
    assert result.exit_code != 0
    assert "Missing option '--issues'" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_backlog_move_adapter_error(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.move_issues_to_backlog.side_effect = VDSClientError("boom")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["backlog", "move", "--issues", "NTTC-1", "--yes"])
    assert result.exit_code != 0
    assert "Error: boom" in result.stderr
