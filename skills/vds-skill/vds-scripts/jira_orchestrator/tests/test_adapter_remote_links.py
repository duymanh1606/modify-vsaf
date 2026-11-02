from __future__ import annotations

from unittest.mock import MagicMock, patch

from vds_jira_orchestrator.adapter import JiraAdapter


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_issue_remote_links_returns_list(mock_jira: MagicMock) -> None:
    """Ensure get_issue_remote_links proxies to SDK and normalises response."""
    client = MagicMock()
    client.get_issue_remote_links.return_value = [{"id": 1}, {"id": 2}]
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_issue_remote_links("NTTC-1")

    client.get_issue_remote_links.assert_called_once_with("NTTC-1")
    assert result == [{"id": 1}, {"id": 2}]


@patch("vds_jira_orchestrator.adapter.Jira")
def test_create_or_update_issue_remote_link_calls_sdk(mock_jira: MagicMock) -> None:
    """Ensure create_or_update_issue_remote_link delegates to SDK."""
    client = MagicMock()
    client.create_or_update_issue_remote_links.return_value = {"created": True}
    mock_jira.return_value = client
    payload = {"object": {"url": "https://example.com"}}

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.create_or_update_issue_remote_link("NTTC-2", payload)

    client.create_or_update_issue_remote_links.assert_called_once_with("NTTC-2", payload)
    assert result == {"created": True}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_issue_remote_link_by_id_calls_sdk(mock_jira: MagicMock) -> None:
    """Ensure get_issue_remote_link_by_id delegates to SDK."""
    client = MagicMock()
    client.get_issue_remote_link_by_id.return_value = {"id": 5}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_issue_remote_link_by_id("NTTC-3", 5)

    client.get_issue_remote_link_by_id.assert_called_once_with("NTTC-3", 5)
    assert result == {"id": 5}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_update_issue_remote_link_by_id_calls_sdk(mock_jira: MagicMock) -> None:
    """Ensure update_issue_remote_link_by_id delegates to SDK."""
    client = MagicMock()
    client.update_issue_remote_link_by_id.return_value = {"updated": True}
    mock_jira.return_value = client
    payload = {"object": {"url": "https://example.com/updated"}}

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.update_issue_remote_link_by_id("NTTC-4", "abc", payload)

    client.update_issue_remote_link_by_id.assert_called_once_with("NTTC-4", "abc", payload)
    assert result == {"updated": True}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_delete_issue_remote_link_by_id_calls_sdk(mock_jira: MagicMock) -> None:
    """Ensure delete_issue_remote_link_by_id delegates to SDK."""
    client = MagicMock()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.delete_issue_remote_link_by_id("NTTC-5", 9)

    client.delete_issue_remote_link_by_id.assert_called_once_with("NTTC-5", 9)
