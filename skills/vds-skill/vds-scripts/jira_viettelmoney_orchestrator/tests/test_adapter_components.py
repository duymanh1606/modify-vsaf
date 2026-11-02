from __future__ import annotations

from unittest.mock import MagicMock, patch

from vds_jira_orchestrator.adapter import JiraAdapter


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_component_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.component.return_value = {"id": 10, "name": "Comp"}
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    payload = adapter.get_component(10)

    client.component.assert_called_once_with(10)
    assert payload["id"] == 10


@patch("vds_jira_orchestrator.adapter.Jira")
def test_create_component_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.create_component.return_value = {"id": 11}
    mock_jira.return_value = client
    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )

    payload = {"name": "NewComp", "projectKey": "NTTC"}
    result = adapter.create_component(payload)

    client.create_component.assert_called_once_with(payload)
    assert result["id"] == 11


@patch("vds_jira_orchestrator.adapter.Jira")
def test_update_component_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.update_component.return_value = {"id": 12, "name": "Updated"}
    mock_jira.return_value = client
    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )

    result = adapter.update_component(12, {"name": "Updated"})

    client.update_component.assert_called_once_with(12, {"name": "Updated"})
    assert result["name"] == "Updated"


@patch("vds_jira_orchestrator.adapter.Jira")
def test_delete_component_calls_sdk(mock_jira: MagicMock) -> None:
    client = MagicMock()
    mock_jira.return_value = client
    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )

    adapter.delete_component("13")

    client.delete_component.assert_called_once_with("13")
