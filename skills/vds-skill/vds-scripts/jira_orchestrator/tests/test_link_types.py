"""Tests for JIRA issue link type CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import NotFoundError


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_adapter() -> Mock:
    """Create a mock adapter."""
    adapter = Mock()
    adapter.get_issue_link_types.return_value = [
        {
            "id": "10000",
            "name": "Blocks",
            "inward": "is blocked by",
            "outward": "blocks",
        },
        {
            "id": "10001",
            "name": "Relates",
            "inward": "relates to",
            "outward": "relates to",
        },
    ]
    adapter.get_issue_link_type.return_value = {
        "id": "10000",
        "name": "Blocks",
        "inward": "is blocked by",
        "outward": "blocks",
    }
    adapter.create_issue_link_type.return_value = {
        "id": "10002",
        "name": "Tests",
        "inward": "is tested by",
        "outward": "tests",
    }
    adapter.update_issue_link_type.return_value = {
        "id": "10000",
        "name": "Blocks Updated",
        "inward": "is blocked by",
        "outward": "blocks",
    }
    return adapter


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_list_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test link-type list command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["link-type", "list"])

    assert result.exit_code == 0
    assert "link_types" in result.stdout
    assert "Blocks" in result.stdout
    mock_adapter.get_issue_link_types.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_get_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test link-type get command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["link-type", "get", "--link-type-id", "10000"])

    assert result.exit_code == 0
    assert "Blocks" in result.stdout
    mock_adapter.get_issue_link_type.assert_called_once_with("10000")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_get_missing_id(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    """Test link-type get command with missing link-type-id."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["link-type", "get"])

    assert result.exit_code != 0
    assert "link-type-id required" in result.stdout or "link-type-id required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_create_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test link-type create command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "link-type",
            "create",
            "--name",
            "Tests",
            "--inward",
            "is tested by",
            "--outward",
            "tests",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "Tests" in result.stdout
    mock_adapter.create_issue_link_type.assert_called_once_with(
        {"name": "Tests", "inward": "is tested by", "outward": "tests"}
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_create_with_data_file(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
    tmp_path: Path,
) -> None:
    """Test link-type create command with data file."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    data_file = tmp_path / "link_type.json"
    data_file.write_text('{"name": "Tests", "inward": "is tested by", "outward": "tests"}')

    result = runner.invoke(app, ["link-type", "create", "--data-file", str(data_file), "--yes"])

    assert result.exit_code == 0
    assert "Tests" in result.stdout
    mock_adapter.create_issue_link_type.assert_called_once_with(
        {"name": "Tests", "inward": "is tested by", "outward": "tests"}
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_create_requires_yes(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    """Test link-type create command requires --yes flag."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(
        app,
        [
            "link-type",
            "create",
            "--name",
            "Tests",
            "--inward",
            "is tested by",
            "--outward",
            "tests",
        ],
    )

    assert result.exit_code != 0
    assert "without --yes" in result.stdout or "without --yes" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_create_missing_params(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test link-type create command with missing parameters."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["link-type", "create", "--name", "Tests", "--yes"])

    assert result.exit_code != 0
    assert "required" in result.stdout or "required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_update_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test link-type update command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "link-type",
            "update",
            "--link-type-id",
            "10000",
            "--name",
            "Blocks Updated",
            "--inward",
            "is blocked by",
            "--outward",
            "blocks",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "Blocks Updated" in result.stdout
    mock_adapter.update_issue_link_type.assert_called_once_with(
        "10000",
        {"name": "Blocks Updated", "inward": "is blocked by", "outward": "blocks"},
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_update_requires_yes(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    """Test link-type update command requires --yes flag."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(
        app,
        [
            "link-type",
            "update",
            "--link-type-id",
            "10000",
            "--name",
            "Blocks Updated",
            "--inward",
            "is blocked by",
            "--outward",
            "blocks",
        ],
    )

    assert result.exit_code != 0
    assert "without --yes" in result.stdout or "without --yes" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_delete_success(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test link-type delete command success."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["link-type", "delete", "--link-type-id", "10000", "--yes"])

    assert result.exit_code == 0
    assert "deleted" in result.stdout
    mock_adapter.delete_issue_link_type.assert_called_once_with("10000")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_delete_requires_yes(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    """Test link-type delete command requires --yes flag."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["link-type", "delete", "--link-type-id", "10000"])

    assert result.exit_code != 0
    assert "without --yes" in result.stdout or "without --yes" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_unknown_action(mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
    """Test link-type command with unknown action."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings

    result = runner.invoke(app, ["link-type", "unknown"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_link_type_error_handling(
    mock_settings_class: Mock,
    mock_adapter_class: Mock,
    runner: CliRunner,
    mock_adapter: Mock,
) -> None:
    """Test link-type command error handling."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "test"
    mock_settings.password = "test"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_issue_link_type.side_effect = NotFoundError("Link type not found")

    result = runner.invoke(app, ["link-type", "get", "--link-type-id", "99999"])

    assert result.exit_code != 0
    assert "Error" in result.stdout or "Error" in result.stderr
