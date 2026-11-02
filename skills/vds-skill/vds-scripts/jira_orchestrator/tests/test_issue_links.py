"""Tests for Jira issue-link CLI command."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _configure_mocks(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    adapter: Mock,
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
def test_issue_link_create_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    adapter.create_issue_link.return_value = {"id": "10001"}
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "create",
            "--type",
            "Blocks",
            "--inward-issue",
            "NTTC-5804",
            "--outward-issue",
            "NTTC-5803",
            "--comment",
            "Runtime dependency",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.create_issue_link.assert_called_once_with(
        {
            "type": {"name": "Blocks"},
            "inwardIssue": {"key": "NTTC-5803"},
            "outwardIssue": {"key": "NTTC-5804"},
            "comment": {"body": "Runtime dependency"},
        }
    )
    assert '"status": "created"' in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_link_create_requires_yes(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "create",
            "--type",
            "Blocks",
            "--inward-issue",
            "NTTC-5804",
            "--outward-issue",
            "NTTC-5803",
        ],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr
    adapter.create_issue_link.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_link_create_dry_run(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "create",
            "--type",
            "Blocks",
            "--inward-issue",
            "NTTC-5804",
            "--outward-issue",
            "NTTC-5803",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert '"dry_run": true' in result.stdout
    adapter.create_issue_link.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_link_create_requires_fields(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "create",
            "--type",
            "Blocks",
            "--outward-issue",
            "NTTC-5803",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "--inward-issue required" in result.stdout or "--inward-issue required" in result.stderr
    adapter.create_issue_link.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_link_delete_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "delete",
            "--link-id",
            "305933",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    adapter.remove_issue_link.assert_called_once_with(305933)
    assert '"status": "deleted"' in result.stdout


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_link_delete_requires_yes(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "delete",
            "--link-id",
            "305933",
        ],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr
    adapter.remove_issue_link.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_link_delete_dry_run(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "delete",
            "--link-id",
            "305933",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert '"dry_run": true' in result.stdout
    adapter.remove_issue_link.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_issue_link_delete_requires_link_id(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
) -> None:
    adapter = Mock()
    _configure_mocks(mock_settings_class, mock_adapter_class, adapter)

    result = runner.invoke(
        app,
        [
            "issue-link",
            "delete",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "--link-id required" in result.stdout or "--link-id required" in result.stderr
    adapter.remove_issue_link.assert_not_called()
