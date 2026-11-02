from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
from vds_jira_orchestrator.adapter import JiraAdapter


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_createmeta_falls_back_to_rest_endpoint(mock_jira: MagicMock) -> None:
    client = MagicMock()
    client.issue_createmeta.side_effect = Exception("boom")
    client.resource_url.return_value = "https://jira.example.com/rest/api/2/issue"
    client.get.return_value = {"projects": []}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_createmeta("TEST", issuetype="Task", expand="projects.issuetypes.fields")

    client.get.assert_called_once_with(
        "https://jira.example.com/rest/api/2/issue/createmeta",
        params={
            "projectKeys": "TEST",
            "issuetypeNames": "Task",
            "expand": "projects.issuetypes.fields",
        },
    )
    assert result == {"projects": []}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_createmeta_falls_back_when_v2_unavailable(mock_jira: MagicMock) -> None:
    client = MagicMock()
    response = MagicMock()
    response.status_code = 404
    client.issue_createmeta_issuetypes.side_effect = requests.exceptions.HTTPError(response=response)
    client.issue_createmeta_fieldtypes.return_value = {}
    client.issue_createmeta.return_value = {"projects": []}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_createmeta("TEST", issuetype="Task", expand="projects.issuetypes.fields")

    client.issue_createmeta.assert_called_once()
    assert result == {"projects": []}
