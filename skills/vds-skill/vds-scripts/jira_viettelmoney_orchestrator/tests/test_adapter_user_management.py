from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from vds_jira_orchestrator.adapter import JiraAdapter, VDSClientError


@patch("vds_jira_orchestrator.adapter.Jira")
def test_find_users_calls_client(mock_jira: MagicMock) -> None:
    """Test that find_users calls the SDK client."""
    client = MagicMock()
    client.user_find_by_user_string.return_value = [
        {
            "accountId": "123",
            "displayName": "Test User",
            "emailAddress": "test@example.com",
        }
    ]
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.find_users(query="test@example.com")

    client.user_find_by_user_string.assert_called_once_with(
        query="test@example.com", start=0, limit=50, include_inactive_users=False
    )
    assert len(result) == 1
    assert result[0]["accountId"] == "123"


@patch("vds_jira_orchestrator.adapter.Jira")
def test_find_users_with_pagination(mock_jira: MagicMock) -> None:
    """Test that find_users passes pagination parameters."""
    client = MagicMock()
    client.user_find_by_user_string.return_value = []
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    adapter.find_users(query="test", start=10, limit=20, include_inactive=True)

    client.user_find_by_user_string.assert_called_once_with(
        query="test", start=10, limit=20, include_inactive_users=True
    )


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_user_groups_cloud_mode(mock_jira: MagicMock) -> None:
    """Test that get_user_groups works in Cloud mode."""
    client = MagicMock()
    client.get_user_groups.return_value = [
        {"name": "jira-users"},
        {"name": "jira-administrators"},
    ]
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://test.atlassian.net", username="user", password="pass"
    )
    result = adapter.get_user_groups("account-123")

    client.get_user_groups.assert_called_once_with("account-123")
    assert len(result) == 2
    assert result[0]["name"] == "jira-users"


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_user_groups_server_mode_raises_error(mock_jira: MagicMock) -> None:
    """Test that get_user_groups raises error in Server/DC mode."""
    client = MagicMock()
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )

    with pytest.raises(VDSClientError, match="only available in Jira Cloud mode"):
        adapter.get_user_groups("account-123")

    client.get_user_groups.assert_not_called()


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_user_groups_explicit_cloud_mode(mock_jira: MagicMock) -> None:
    """Test that get_user_groups works with explicit cloud=True."""
    client = MagicMock()
    client.get_user_groups.return_value = [{"name": "jira-users"}]
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass", cloud=True
    )
    result = adapter.get_user_groups("account-123")

    client.get_user_groups.assert_called_once_with("account-123")
    assert len(result) == 1


@patch("vds_jira_orchestrator.adapter.Jira")
def test_deactivate_user_calls_client(mock_jira: MagicMock) -> None:
    """Test that deactivate_user calls the SDK client."""
    client = MagicMock()
    client.user_deactivate.return_value = None
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    adapter.deactivate_user("testuser")

    client.user_deactivate.assert_called_once_with("testuser")


@patch("vds_jira_orchestrator.adapter.Jira")
def test_deactivate_user_handles_error(mock_jira: MagicMock) -> None:
    """Test that deactivate_user handles errors correctly."""
    client = MagicMock()
    client.user_deactivate.side_effect = Exception("User not found")
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )

    with pytest.raises(VDSClientError):
        adapter.deactivate_user("nonexistent")
