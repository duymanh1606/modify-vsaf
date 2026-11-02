from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from vds_jira_orchestrator.adapter import JiraAdapter
from vds_jira_orchestrator.errors import VDSClientError


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_permissions_uses_official_get_permissions(mock_jira: Mock) -> None:
    class Client:
        def __init__(self) -> None:
            self.get_permissions = Mock(return_value={"permissions": {}})

    client = Client()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.get_permissions(permissions=["BROWSE_PROJECTS", "ADMINISTER_PROJECTS"], project_key="NTTC")

    client.get_permissions.assert_called_once_with(
        permissions="BROWSE_PROJECTS,ADMINISTER_PROJECTS",
        project_id=None,
        project_key="NTTC",
        issue_id=None,
        issue_key=None,
    )


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_permissions_raises_when_not_supported(mock_jira: Mock) -> None:
    class Client:
        pass

    client = Client()
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    with pytest.raises(VDSClientError):
        adapter.get_permissions(permissions=["BROWSE_PROJECTS"])
