from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from vds_jira_orchestrator.adapter import JiraAdapter, AuthError


@patch("vds_jira_orchestrator.adapter.Jira")
def test_reindex_calls_client(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.reindex.return_value = {"taskId": 123}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.reindex()

    client.reindex.assert_called_once_with()
    assert result == {"taskId": 123}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_reindex_status_maps_error(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.reindex_status.side_effect = Exception("401 unauthorized")
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    with pytest.raises(AuthError):
        adapter.reindex_status()


@patch("vds_jira_orchestrator.adapter.Jira")
def test_move_issues_to_backlog(mock_jira: MagicMock) -> None:
    client = MagicMock()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.move_issues_to_backlog(["NTTC-1", "NTTC-2"])

    client.move_issues_to_backlog.assert_called_once_with(["NTTC-1", "NTTC-2"])
