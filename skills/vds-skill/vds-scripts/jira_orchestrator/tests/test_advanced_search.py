"""Tests for JIRA advanced search methods."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.adapter import AuthError, JiraAdapter, VDSClientError
from vds_jira_orchestrator.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Adapter method tests
# ---------------------------------------------------------------------------


@patch("vds_jira_orchestrator.adapter.Jira")
def test_search_issues_advanced_calls_client(mock_jira: MagicMock) -> None:
    """Test that search_issues_advanced calls the SDK client with pagination."""
    client = MagicMock()
    client.jql.return_value = {
        "issues": [{"key": "TEST-1"}, {"key": "TEST-2"}],
        "total": 2,
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.search_issues_advanced("project = TEST", start=10, limit=25, fields=["summary", "status"])

    client.jql.assert_called_once_with("project = TEST", fields="summary,status", start=10, limit=25)
    assert result["total"] == 2


@patch("vds_jira_orchestrator.adapter.Jira")
def test_search_issues_advanced_defaults(mock_jira: MagicMock) -> None:
    """Test that search_issues_advanced uses default parameters."""
    client = MagicMock()
    client.jql.return_value = {"issues": [], "total": 0}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    adapter.search_issues_advanced("project = TEST")

    client.jql.assert_called_once_with("project = TEST", fields="*all", start=0, limit=50)


@patch("vds_jira_orchestrator.adapter.Jira")
def test_search_issues_by_filter_calls_get_filter(mock_jira: MagicMock) -> None:
    """Test that search_issues_by_filter gets filter and uses its JQL."""
    client = MagicMock()
    client.get_filter.return_value = {
        "id": 10000,
        "name": "My Filter",
        "jql": "project = TEST AND status = Open",
    }
    client.jql.return_value = {"issues": [{"key": "TEST-1"}], "total": 1}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
    result = adapter.search_issues_by_filter(10000, start=0, limit=50)

    client.get_filter.assert_called_once_with(10000)
    client.jql.assert_called_once_with("project = TEST AND status = Open", fields="*all", start=0, limit=50)
    assert result["total"] == 1


@patch("vds_jira_orchestrator.adapter.Jira")
def test_search_issues_by_filter_no_jql(mock_jira: MagicMock) -> None:
    """Test that search_issues_by_filter raises error when filter has no JQL."""
    client = MagicMock()
    client.get_filter.return_value = {"id": 10000, "name": "My Filter", "jql": ""}
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    with pytest.raises(VDSClientError, match="does not have a JQL query"):
        adapter.search_issues_by_filter(10000)


@patch("vds_jira_orchestrator.adapter.Jira")
def test_search_issues_advanced_handles_error(mock_jira: MagicMock) -> None:
    """Test that search_issues_advanced handles errors."""
    client = MagicMock()
    client.jql.side_effect = Exception("401 unauthorized")
    mock_jira.return_value = client

    adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")

    with pytest.raises(AuthError):
        adapter.search_issues_advanced("project = TEST")


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_search_advanced_flag(mock_settings: MagicMock, mock_adapter_class: MagicMock) -> None:
    """Test search command with --advanced flag."""
    mock_adapter = MagicMock()
    mock_adapter.search_issues_advanced.return_value = {
        "issues": [{"key": "TEST-1"}],
        "total": 1,
    }
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        ["search", "project = TEST", "--advanced", "--start", "10", "--limit", "25"],
    )

    assert result.exit_code == 0
    mock_adapter.search_issues_advanced.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_search_with_start_uses_advanced(mock_settings: MagicMock, mock_adapter_class: MagicMock) -> None:
    """Test search command with --start automatically uses advanced search."""
    mock_adapter = MagicMock()
    mock_adapter.search_issues_advanced.return_value = {"issues": [], "total": 0}
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["search", "project = TEST", "--start", "5"])

    assert result.exit_code == 0
    mock_adapter.search_issues_advanced.assert_called_once()
    mock_adapter.jql.assert_not_called()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_search_by_filter_success(mock_settings: MagicMock, mock_adapter_class: MagicMock) -> None:
    """Test search-by-filter command success."""
    mock_adapter = MagicMock()
    mock_adapter.search_issues_by_filter.return_value = {
        "issues": [{"key": "TEST-1"}],
        "total": 1,
    }
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["search-by-filter", "10000", "--limit", "50"])

    assert result.exit_code == 0
    assert "TEST-1" in result.stdout
    mock_adapter.search_issues_by_filter.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_search_by_filter_with_pagination(mock_settings: MagicMock, mock_adapter_class: MagicMock) -> None:
    """Test search-by-filter command with pagination."""
    mock_adapter = MagicMock()
    mock_adapter.search_issues_by_filter.return_value = {"issues": [], "total": 0}
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["search-by-filter", "10000", "--start", "20", "--limit", "25"])

    assert result.exit_code == 0
    mock_adapter.search_issues_by_filter.assert_called_once_with(10000, start=20, limit=25, fields=None)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_search_by_filter_handles_error(mock_settings: MagicMock, mock_adapter_class: MagicMock) -> None:
    """Test search-by-filter command error handling."""
    mock_adapter = MagicMock()
    mock_adapter.search_issues_by_filter.side_effect = VDSClientError("Filter not found")
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["search-by-filter", "99999"])

    assert result.exit_code != 0
    assert "Error" in result.stdout or "Error" in result.stderr
