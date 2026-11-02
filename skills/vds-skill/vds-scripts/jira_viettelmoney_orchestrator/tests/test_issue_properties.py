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


def _configure_mocks(
    mock_settings_class: Mock, mock_adapter_class: Mock, adapter: Mock
) -> None:
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
def test_issue_property_list(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    adapter.get_issue_property_keys.return_value = {"keys": [{"key": "custom.key"}]}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(app, ["issue-property", "list", "--issue-key", "NTTC-1"])

    assert result.exit_code == 0
    adapter.get_issue_property_keys.assert_called_once_with("NTTC-1")
    assert "custom.key" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_property_get(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    adapter.get_issue_property.return_value = {"value": {"foo": "bar"}}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-property",
            "get",
            "--issue-key",
            "NTTC-2",
            "--property-key",
            "custom.key",
        ],
    )

    assert result.exit_code == 0
    adapter.get_issue_property.assert_called_once_with("NTTC-2", "custom.key")
    assert "foo" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_property_set_requires_yes(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-property",
            "set",
            "--issue-key",
            "NTTC-3",
            "--property-key",
            "custom.key",
            "--value",
            '{"foo": "bar"}',
        ],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stderr or "--yes required" in result.stdout
    adapter.set_issue_property.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_property_set_with_value(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-property",
            "set",
            "--issue-key",
            "NTTC-4",
            "--property-key",
            "custom.key",
            "--value",
            '{"foo": "bar"}',
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.set_issue_property.assert_called_once_with(
        "NTTC-4", "custom.key", {"foo": "bar"}
    )
    assert "updated" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_property_set_with_file(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    data = {"foo": "bar"}
    data_file = tmp_path / "property.json"
    data_file.write_text(json.dumps(data))

    result = runner.invoke(
        app,
        [
            "issue-property",
            "set",
            "--issue-key",
            "NTTC-5",
            "--property-key",
            "custom.key",
            "--data-file",
            str(data_file),
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.set_issue_property.assert_called_once_with("NTTC-5", "custom.key", data)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_property_delete(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-property",
            "delete",
            "--issue-key",
            "NTTC-6",
            "--property-key",
            "custom.key",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.delete_issue_property.assert_called_once_with("NTTC-6", "custom.key")
    assert "deleted" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_property_unknown_action(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["issue-property", "unknown", "--issue-key", "NTTC-7"],
    )

    assert result.exit_code != 0
    assert "Unknown action" in result.stderr or "Unknown action" in result.stdout
