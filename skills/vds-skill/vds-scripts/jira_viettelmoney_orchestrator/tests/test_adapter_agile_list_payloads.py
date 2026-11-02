from unittest.mock import Mock, patch

from vds_jira_orchestrator.adapter import JiraAdapter


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_all_agile_boards_unwraps_values_list(mock_jira: Mock) -> None:
    client = Mock()
    client.get_all_agile_boards.return_value = {
        "maxResults": 50,
        "startAt": 0,
        "isLast": True,
        "values": [{"id": 1, "name": "NTTC Scrum Board"}],
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_all_agile_boards(project_key="NTTC", limit=50)

    assert result == [{"id": 1, "name": "NTTC Scrum Board"}]


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_issues_for_board_unwraps_issues_list(mock_jira: Mock) -> None:
    client = Mock()
    client.get_issues_for_board.return_value = {
        "startAt": 0,
        "maxResults": 50,
        "total": 1,
        "issues": [{"key": "NTTC-5705"}],
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_issues_for_board(1)

    assert result == [{"key": "NTTC-5705"}]


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_all_sprints_from_board_unwraps_values_list(mock_jira: Mock) -> None:
    client = Mock()
    client.get_all_sprints_from_board.return_value = {
        "maxResults": 50,
        "startAt": 0,
        "isLast": True,
        "values": [{"id": 101, "name": "Sprint 1"}],
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_all_sprints_from_board(1)

    assert result == [{"id": 101, "name": "Sprint 1"}]
