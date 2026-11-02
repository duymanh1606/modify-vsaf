from __future__ import annotations

from unittest.mock import MagicMock, patch

from vds_jira_orchestrator.adapter import JiraAdapter


@patch("vds_jira_orchestrator.adapter.Jira")
def test_issue_get_watchers_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.issue_get_watchers.return_value = {
        "watchCount": 1,
        "watchers": [{"accountId": "123"}],
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    payload = adapter.issue_get_watchers("NTTC-1")

    client.issue_get_watchers.assert_called_once_with("NTTC-1")
    assert payload["watchCount"] == 1


@patch("vds_jira_orchestrator.adapter.Jira")
def test_issue_add_watcher_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.issue_add_watcher("NTTC-2", "userAccount")

    client.issue_add_watcher.assert_called_once_with("NTTC-2", "userAccount")


@patch("vds_jira_orchestrator.adapter.Jira")
def test_issue_delete_watcher_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.issue_delete_watcher("NTTC-3", "userAccount")

    client.issue_delete_watcher.assert_called_once_with("NTTC-3", "userAccount")
