from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _configure_mocks(mock_settings_class: Mock, mock_adapter_class: Mock, adapter: Mock) -> None:
    settings = Mock()
    settings.base_url = "https://jira.example.com"
    settings.username = "user"
    settings.password = "pass"
    settings.token = None
    settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = settings
    mock_adapter_class.return_value = adapter


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_watcher_list(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    adapter.issue_get_watchers.return_value = {"watchCount": 2, "watchers": []}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(app, ["watcher", "list", "--issue-key", "NTTC-1"])

    assert result.exit_code == 0
    adapter.issue_get_watchers.assert_called_once_with("NTTC-1")
    assert "watchCount" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_watcher_add_requires_yes(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["watcher", "add", "--issue-key", "NTTC-2", "--account", "userAccount"],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stderr or "--yes required" in result.stdout
    adapter.issue_add_watcher.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_watcher_add_success(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "watcher",
            "add",
            "--issue-key",
            "NTTC-3",
            "--account",
            "userAccount",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.issue_add_watcher.assert_called_once_with("NTTC-3", "userAccount")
    assert "added" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_watcher_remove_success(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "watcher",
            "remove",
            "--issue-key",
            "NTTC-4",
            "--account",
            "userAccount",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.issue_delete_watcher.assert_called_once_with("NTTC-4", "userAccount")
    assert "removed" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_watcher_unknown_action(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["watcher", "unknown", "--issue-key", "NTTC-5"],
    )

    assert result.exit_code != 0
    assert "Unknown action" in result.stderr or "Unknown action" in result.stdout
