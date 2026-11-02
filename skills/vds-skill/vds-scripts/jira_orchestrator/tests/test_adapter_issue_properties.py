from __future__ import annotations

from unittest.mock import MagicMock, patch

from vds_jira_orchestrator.adapter import JiraAdapter


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_issue_property_keys_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.get_issue_property_keys.return_value = {"keys": [{"key": "custom"}]}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    payload = adapter.get_issue_property_keys("NTTC-1")

    client.get_issue_property_keys.assert_called_once_with("NTTC-1")
    assert payload == {"keys": [{"key": "custom"}]}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_set_issue_property_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    mock_jira.return_value = client
    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    adapter.set_issue_property("NTTC-2", "custom.key", {"foo": "bar"})

    client.set_issue_property.assert_called_once_with("NTTC-2", "custom.key", {"foo": "bar"})


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_issue_property_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.get_issue_property.return_value = {"value": {"foo": "bar"}}
    mock_jira.return_value = client
    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    payload = adapter.get_issue_property("NTTC-3", "custom.key")

    client.get_issue_property.assert_called_once_with("NTTC-3", "custom.key")
    assert payload == {"value": {"foo": "bar"}}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_delete_issue_property_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    mock_jira.return_value = client
    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    adapter.delete_issue_property("NTTC-4", "custom.key")

    client.delete_issue_property.assert_called_once_with("NTTC-4", "custom.key")
