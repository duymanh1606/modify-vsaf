from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from vds_jira_orchestrator.adapter import JiraAdapter
from vds_jira_orchestrator.errors import VDSClientError


@patch("vds_jira_orchestrator.adapter.Jira")
def test_transition_issue_uses_issue_transition(mock_jira: Mock) -> None:
    class Client:
        def __init__(self) -> None:
            self.get_issue_transitions = Mock(return_value=[{"id": 71, "name": "Cancelled"}])
            self.issue_transition = Mock()

    client = Client()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.transition_issue("NTTC-1", "Cancelled")

    client.get_issue_transitions.assert_called_once_with("NTTC-1")
    client.issue_transition.assert_called_once_with("NTTC-1", "Cancelled")


@patch("vds_jira_orchestrator.adapter.Jira")
def test_transition_issue_falls_back_to_set_issue_status_by_transition_name(mock_jira: Mock) -> None:
    class Client:
        def __init__(self) -> None:
            self.get_issue_transitions = Mock(return_value=[{"id": "11", "name": "Develop"}])
            self.set_issue_status_by_transition_name = Mock()

    client = Client()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.transition_issue("NTTC-2", "Develop")

    client.get_issue_transitions.assert_called_once_with("NTTC-2")
    client.set_issue_status_by_transition_name.assert_called_once_with("NTTC-2", "Develop")


@patch("vds_jira_orchestrator.adapter.Jira")
def test_transition_issue_falls_back_to_set_issue_status_by_transition_id(mock_jira: Mock) -> None:
    class Client:
        def __init__(self) -> None:
            self.get_issue_transitions = Mock(return_value=[{"id": 81, "name": "Pending"}])
            self.set_issue_status_by_transition_id = Mock()

    client = Client()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.transition_issue("NTTC-3", "Pending")

    client.get_issue_transitions.assert_called_once_with("NTTC-3")
    client.set_issue_status_by_transition_id.assert_called_once_with("NTTC-3", 81)


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_issue_transitions_falls_back_to_full_payload(mock_jira: Mock) -> None:
    class Client:
        def __init__(self) -> None:
            self.get_issue_transitions_full = Mock(
                return_value={"transitions": [{"id": "41", "name": "Assign OS", "to": {"name": "Assign OS"}}]}
            )

    client = Client()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    transitions = adapter.get_issue_transitions("NTTC-4")

    assert transitions[0]["name"] == "Assign OS"
    client.get_issue_transitions_full.assert_called_once_with("NTTC-4")


@patch("vds_jira_orchestrator.adapter.Jira")
def test_transition_issue_raises_when_transition_not_found(mock_jira: Mock) -> None:
    class Client:
        def __init__(self) -> None:
            self.get_issue_transitions = Mock(return_value=[{"id": 71, "name": "Cancelled"}])

    client = Client()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    with pytest.raises(VDSClientError):
        adapter.transition_issue("NTTC-5", "Done")
