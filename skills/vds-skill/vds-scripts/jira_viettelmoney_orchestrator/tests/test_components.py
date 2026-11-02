from __future__ import annotations

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
def test_component_get_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    adapter.get_component.return_value = {"id": 10, "name": "Comp"}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(app, ["component", "get", "--component-id", "10"])

    assert result.exit_code == 0
    adapter.get_component.assert_called_once_with("10")
    assert "Comp" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_component_create_requires_yes(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["component", "create", "--project-key", "NTTC", "--name", "Comp"],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stderr or "--yes required" in result.stdout
    adapter.create_component.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_component_create_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    adapter.create_component.return_value = {"id": 11}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["component", "create", "--project-key", "NTTC", "--name", "Comp", "--yes"],
    )

    assert result.exit_code == 0
    adapter.create_component.assert_called_once()
    payload = adapter.create_component.call_args[0][0]
    assert payload["project"] == "NTTC"
    assert payload["name"] == "Comp"


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_component_list_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    adapter.get_project.return_value = {"components": [{"id": "10", "name": "Core"}]}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(app, ["component", "list", "--project-key", "NTTC"])

    assert result.exit_code == 0
    adapter.get_project.assert_called_once_with("NTTC", expand="components")
    assert "Core" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_component_update_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    adapter.update_component.return_value = {"id": 12, "name": "Updated"}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["component", "update", "--component-id", "12", "--name", "Updated", "--yes"],
    )

    assert result.exit_code == 0
    adapter.update_component.assert_called_once_with({"name": "Updated"}, "12")
    assert "Updated" in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_component_delete_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        ["component", "delete", "--component-id", "13", "--yes"],
    )

    assert result.exit_code == 0
    adapter.delete_component.assert_called_once_with("13")
    assert "deleted" in result.stdout
