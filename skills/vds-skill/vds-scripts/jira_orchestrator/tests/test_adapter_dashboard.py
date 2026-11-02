from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from vds_jira_orchestrator.adapter import AuthError, JiraAdapter, NotFoundError


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboard_calls_client(mock_jira: MagicMock) -> None:
    """Test that get_dashboard calls the SDK client."""
    client = MagicMock()
    client.get_dashboard.return_value = {"id": "10000", "name": "Test Dashboard"}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_dashboard("10000")

    client.get_dashboard.assert_called_once_with("10000")
    assert result == {"id": "10000", "name": "Test Dashboard"}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboard_with_int_id(mock_jira: MagicMock) -> None:
    """Test that get_dashboard works with integer ID."""
    client = MagicMock()
    client.get_dashboard.return_value = {"id": 10000, "name": "Test Dashboard"}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_dashboard(10000)

    client.get_dashboard.assert_called_once_with(10000)
    assert result == {"id": 10000, "name": "Test Dashboard"}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboard_not_found(mock_jira: MagicMock) -> None:
    """Test that get_dashboard raises NotFoundError when dashboard is not found."""
    client = MagicMock()
    client.get_dashboard.return_value = None
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    with pytest.raises(NotFoundError, match="Dashboard not found: 99999"):
        adapter.get_dashboard("99999")


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboard_maps_error(mock_jira: MagicMock) -> None:
    """Test that get_dashboard maps authentication errors."""
    client = MagicMock()
    client.get_dashboard.side_effect = Exception("401 unauthorized")
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    with pytest.raises(AuthError):
        adapter.get_dashboard("10000")


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboards_calls_client(mock_jira: MagicMock) -> None:
    """Test that get_dashboards calls the SDK client."""
    client = MagicMock()
    client.get_dashboards.return_value = {
        "dashboards": [
            {"id": "10000", "name": "Dashboard 1"},
            {"id": "10001", "name": "Dashboard 2"},
        ]
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_dashboards()

    client.get_dashboards.assert_called_once_with(filter="", start=0, limit=10)
    assert len(result["dashboards"]) == 2


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboards_with_filter(mock_jira: MagicMock) -> None:
    """Test that get_dashboards works with filter and pagination."""
    client = MagicMock()
    client.get_dashboards.return_value = {"dashboards": []}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_dashboards(filter="test", start=10, limit=20)

    client.get_dashboards.assert_called_once_with(filter="test", start=10, limit=20)
    assert result == {"dashboards": []}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboards_returns_empty_dict_when_none(mock_jira: MagicMock) -> None:
    """Test that get_dashboards returns empty dict when client returns None."""
    client = MagicMock()
    client.get_dashboards.return_value = None
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.get_dashboards()

    assert result == {}


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_dashboards_maps_error(mock_jira: MagicMock) -> None:
    """Test that get_dashboards maps authentication errors."""
    client = MagicMock()
    client.get_dashboards.side_effect = Exception("401 unauthorized")
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    with pytest.raises(AuthError):
        adapter.get_dashboards()
