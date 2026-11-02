from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_bulk_update_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test successful bulk update."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.bulk_update_issue_field.return_value = {"updated": 2, "errors": []}

    result = runner.invoke(
        app,
        [
            "bulk-update",
            "--issue-keys",
            "TEST-1,TEST-2",
            "--fields",
            '{"summary":"Updated"}',
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "updated" in result.stdout
    mock_adapter.bulk_update_issue_field.assert_called_once_with(
        key_list=["TEST-1", "TEST-2"], fields='{"summary":"Updated"}'
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_bulk_update_with_file(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test bulk update with fields file."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.bulk_update_issue_field.return_value = {"updated": 1, "errors": []}

    with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"summary": "From file", "description": "Updated"}, f)
        fields_file = Path(f.name)

    try:
        result = runner.invoke(
            app,
            [
                "bulk-update",
                "--issue-keys",
                "TEST-1",
                "--fields-file",
                str(fields_file),
                "--yes",
            ],
        )
        assert result.exit_code == 0
        assert "updated" in result.stdout
        mock_adapter.bulk_update_issue_field.assert_called_once()
        call_args = mock_adapter.bulk_update_issue_field.call_args
        assert call_args[1]["key_list"] == ["TEST-1"]
        assert "summary" in call_args[1]["fields"]
    finally:
        fields_file.unlink()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_bulk_update_defaults_to_all(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test bulk update defaults to '*all' when no fields specified."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.bulk_update_issue_field.return_value = {"updated": 3, "errors": []}

    result = runner.invoke(
        app, ["bulk-update", "--issue-keys", "TEST-1,TEST-2,TEST-3", "--yes"]
    )
    assert result.exit_code == 0
    mock_adapter.bulk_update_issue_field.assert_called_once_with(
        key_list=["TEST-1", "TEST-2", "TEST-3"], fields="*all"
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_bulk_update_requires_yes(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test bulk update requires --yes."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        ["bulk-update", "--issue-keys", "TEST-1", "--fields", '{"summary":"Updated"}'],
    )
    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "Refusing" in result.stdout
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_bulk_update_requires_issue_keys(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test bulk update requires --issue-keys."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(app, ["bulk-update", "--yes"])
    assert result.exit_code != 0
    assert "--issue-keys" in result.stdout or "--issue-keys" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_bulk_update_invalid_json(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test bulk update with invalid JSON."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        ["bulk-update", "--issue-keys", "TEST-1", "--fields", "invalid json", "--yes"],
    )
    assert result.exit_code != 0
    assert "Invalid JSON" in result.stdout or "Invalid JSON" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_field_append_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test successful field append."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.issue_field_value_append.return_value = {
        "id": "10000",
        "value": "appended",
    }

    result = runner.invoke(
        app,
        [
            "field-append",
            "--issue-key",
            "TEST-1",
            "--field",
            "customfield_10000",
            "--value",
            '{"name":"value"}',
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "appended" in result.stdout
    mock_adapter.issue_field_value_append.assert_called_once_with(
        issue_id_or_key="TEST-1",
        field="customfield_10000",
        value={"name": "value"},
        notify_users=True,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_field_append_with_file(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test field append with value file."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.issue_field_value_append.return_value = {
        "id": "10001",
        "value": "appended",
    }

    with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"name": "from-file"}, f)
        value_file = Path(f.name)

    try:
        result = runner.invoke(
            app,
            [
                "field-append",
                "--issue-key",
                "TEST-1",
                "--field",
                "customfield_10000",
                "--value-file",
                str(value_file),
                "--yes",
            ],
        )
        assert result.exit_code == 0
        assert "appended" in result.stdout
        mock_adapter.issue_field_value_append.assert_called_once()
        call_args = mock_adapter.issue_field_value_append.call_args
        assert call_args[1]["issue_id_or_key"] == "TEST-1"
        assert call_args[1]["field"] == "customfield_10000"
        assert call_args[1]["value"] == {"name": "from-file"}
    finally:
        value_file.unlink()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_field_append_no_notify(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test field append with --no-notify."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.issue_field_value_append.return_value = {
        "id": "10002",
        "value": "appended",
    }

    result = runner.invoke(
        app,
        [
            "field-append",
            "--issue-key",
            "TEST-1",
            "--field",
            "customfield_10000",
            "--value",
            '{"name":"value"}',
            "--no-notify",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.issue_field_value_append.assert_called_once_with(
        issue_id_or_key="TEST-1",
        field="customfield_10000",
        value={"name": "value"},
        notify_users=False,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_field_append_requires_yes(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test field append requires --yes."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        [
            "field-append",
            "--issue-key",
            "TEST-1",
            "--field",
            "customfield_10000",
            "--value",
            '{"name":"value"}',
        ],
    )
    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "Refusing" in result.stdout
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_field_append_requires_value(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test field append requires --value or --value-file."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        [
            "field-append",
            "--issue-key",
            "TEST-1",
            "--field",
            "customfield_10000",
            "--yes",
        ],
    )
    assert result.exit_code != 0
    assert (
        "--value" in result.stdout
        or "--value" in result.stderr
        or "--value-file" in result.stdout
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_field_append_invalid_json(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test field append with invalid JSON."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        [
            "field-append",
            "--issue-key",
            "TEST-1",
            "--field",
            "customfield_10000",
            "--value",
            "invalid json",
            "--yes",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid JSON" in result.stdout or "Invalid JSON" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_field_append_non_dict_value(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test field append with non-dict value."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        [
            "field-append",
            "--issue-key",
            "TEST-1",
            "--field",
            "customfield_10000",
            "--value",
            '"string"',
            "--yes",
        ],
    )
    assert result.exit_code != 0
    assert "JSON object" in result.stdout or "JSON object" in result.stderr
