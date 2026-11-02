from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_reindex_status(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.reindex_status.return_value = {"state": "IDLE"}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["reindex", "status"])
    assert result.exit_code == 0
    mock_adapter.reindex_status.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_reindex_start_requires_yes(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    result = runner.invoke(app, ["reindex", "start"])
    assert result.exit_code != 0
    assert "Refusing to start reindex without --yes" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_reindex_start_success(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.reindex.return_value = {"result": "OK"}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["reindex", "start", "--yes"])
    assert result.exit_code == 0
    mock_adapter.reindex.assert_called_once_with()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_reindex_with_type(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.reindex_with_type.return_value = {"result": "OK"}
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["reindex", "with-type", "--type", "BACKGROUND", "--yes"])
    assert result.exit_code == 0
    mock_adapter.reindex_with_type.assert_called_once_with("BACKGROUND")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_reindex_with_type_requires_type(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    result = runner.invoke(app, ["reindex", "with-type", "--yes"])
    assert result.exit_code != 0
    assert "--type required for with-type" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_reindex_status_adapter_error(mock_settings: Mock, mock_adapter_cls: Mock) -> None:
    runner = _runner()
    mock_adapter = Mock()
    mock_adapter.reindex_status.side_effect = VDSClientError("failure")
    mock_adapter_cls.return_value = mock_adapter

    result = runner.invoke(app, ["reindex", "status"])
    assert result.exit_code != 0
    assert "Error: failure" in result.stderr
