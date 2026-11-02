from __future__ import annotations

import json
from pathlib import Path
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
def test_remote_link_list_success(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    adapter.get_issue_remote_links.return_value = [{"id": 1}, {"id": 2}]
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(app, ["remote-link", "list", "--issue-key", "NTTC-1"])

    assert result.exit_code == 0
    adapter.get_issue_remote_links.assert_called_once_with("NTTC-1")
    assert "remote_links" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_get_success(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    adapter.get_issue_remote_link_by_id.return_value = {"id": 5}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["remote-link", "get", "--issue-key", "NTTC-2", "--remote-link-id", "5"],
    )

    assert result.exit_code == 0
    adapter.get_issue_remote_link_by_id.assert_called_once_with("NTTC-2", 5)
    assert "id" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_create_requires_yes(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "remote-link",
            "create",
            "--issue-key",
            "NTTC-3",
            "--url",
            "https://example.com",
        ],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stderr or "--yes required" in result.stdout
    adapter.create_or_update_issue_remote_link.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_create_success(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    adapter.create_or_update_issue_remote_link.return_value = {"id": 10}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "remote-link",
            "create",
            "--issue-key",
            "NTTC-4",
            "--url",
            "https://example.com",
            "--title",
            "Sample",
            "--relationship",
            "relates to",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.create_or_update_issue_remote_link.assert_called_once()
    call_args = adapter.create_or_update_issue_remote_link.call_args[0]
    assert call_args[0] == "NTTC-4"
    payload = call_args[1]
    assert payload["object"]["url"] == "https://example.com"
    assert payload["object"]["title"] == "Sample"
    assert payload["relationship"] == "relates to"


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_create_with_data_file(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    adapter = Mock()
    adapter.create_or_update_issue_remote_link.return_value = {"id": 11}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    data = {"object": {"url": "https://example.com", "title": "From file"}}
    data_file = tmp_path / "remote_link.json"
    data_file.write_text(json.dumps(data))

    result = runner.invoke(
        app,
        [
            "remote-link",
            "create",
            "--issue-key",
            "NTTC-5",
            "--data-file",
            str(data_file),
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.create_or_update_issue_remote_link.assert_called_once_with("NTTC-5", data)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_update_success(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    adapter.update_issue_remote_link_by_id.return_value = {"updated": True}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "remote-link",
            "update",
            "--issue-key",
            "NTTC-6",
            "--remote-link-id",
            "14",
            "--url",
            "https://example.com/updated",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.update_issue_remote_link_by_id.assert_called_once_with(
        "NTTC-6",
        14,
        {"object": {"url": "https://example.com/updated"}},
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_delete_success(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "remote-link",
            "delete",
            "--issue-key",
            "NTTC-7",
            "--remote-link-id",
            "20",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.delete_issue_remote_link_by_id.assert_called_once_with("NTTC-7", 20)
    assert "deleted" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_update_requires_id(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "remote-link",
            "update",
            "--issue-key",
            "NTTC-8",
            "--url",
            "https://example.com",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "remote-link-id required" in result.stderr or "remote-link-id required" in result.stdout
    adapter.update_issue_remote_link_by_id.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_application_validation(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "remote-link",
            "create",
            "--issue-key",
            "NTTC-9",
            "--url",
            "https://example.com",
            "--application-type",
            "com.atlassian.confluence",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "application-type and --application-name must be provided together" in result.stderr or result.stdout
    adapter.create_or_update_issue_remote_link.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_remote_link_unknown_action(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["remote-link", "unknown", "--issue-key", "NTTC-10"],
    )

    assert result.exit_code != 0
    assert "Unknown action" in result.stderr or "Unknown action" in result.stdout
