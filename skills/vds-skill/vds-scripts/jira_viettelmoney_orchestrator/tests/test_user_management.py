from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_search_success(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user search command success."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = MagicMock()
    mock_adapter.find_users.return_value = [
        {
            "accountId": "123",
            "displayName": "Test User",
            "emailAddress": "test@example.com",
        }
    ]
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["user", "search", "--query", "test@example.com"])

    assert result.exit_code == 0
    assert "Test User" in result.stdout
    assert "test@example.com" in result.stdout
    mock_adapter.find_users.assert_called_once_with(
        query="test@example.com", start=0, limit=50, include_inactive=False
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_search_with_pagination(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user search with pagination."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = MagicMock()
    mock_adapter.find_users.return_value = []
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "user",
            "search",
            "--query",
            "test",
            "--start",
            "10",
            "--limit",
            "20",
            "--include-inactive",
        ],
    )

    assert result.exit_code == 0
    mock_adapter.find_users.assert_called_once_with(
        query="test", start=10, limit=20, include_inactive=True
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_search_requires_query(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user search requires --query."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = MagicMock()

    result = runner.invoke(app, ["user", "search"])

    assert result.exit_code != 0
    assert "--query required" in result.stdout or "--query required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_groups_success_cloud(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user groups command success in Cloud mode."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://test.atlassian.net"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = MagicMock()
    mock_adapter.get_user_groups.return_value = [
        {"name": "jira-users"},
        {"name": "jira-administrators"},
    ]
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["user", "groups", "--account-id", "account-123"])

    assert result.exit_code == 0
    assert "jira-users" in result.stdout
    assert "jira-administrators" in result.stdout
    mock_adapter.get_user_groups.assert_called_once_with("account-123")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_groups_requires_account_id(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user groups requires --account-id."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://test.atlassian.net"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = MagicMock()

    result = runner.invoke(app, ["user", "groups"])

    assert result.exit_code != 0
    assert (
        "--account-id required" in result.stdout
        or "--account-id required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_groups_server_mode_error(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user groups raises error in Server mode."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = MagicMock()
    from vds_jira_orchestrator.adapter import VDSClientError

    mock_adapter.get_user_groups.side_effect = VDSClientError(
        "only available in Jira Cloud mode"
    )
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["user", "groups", "--account-id", "account-123"])

    assert result.exit_code != 0
    assert "Cloud mode" in result.stdout or "Cloud mode" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_deactivate_success(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user deactivate command success."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = MagicMock()
    mock_adapter.deactivate_user.return_value = None
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app, ["user", "deactivate", "--username", "testuser", "--yes"]
    )

    assert result.exit_code == 0
    assert "deactivated" in result.stdout
    assert "testuser" in result.stdout
    mock_adapter.deactivate_user.assert_called_once_with("testuser")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_deactivate_requires_yes(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user deactivate requires --yes flag."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = MagicMock()

    result = runner.invoke(app, ["user", "deactivate", "--username", "testuser"])

    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "Refusing" in result.stdout
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_deactivate_requires_username(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user deactivate requires --username."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = MagicMock()

    result = runner.invoke(app, ["user", "deactivate", "--yes"])

    assert result.exit_code != 0
    assert (
        "--username required" in result.stdout or "--username required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_user_invalid_action(
    mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test user command with invalid action."""
    runner = CliRunner()
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter_class.return_value = MagicMock()

    result = runner.invoke(app, ["user", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
