"""Tests for JIRA filter management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.adapter import JiraAdapter, NotFoundError
from vds_jira_orchestrator.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Adapter method tests
# ---------------------------------------------------------------------------


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_filters_calls_client(mock_jira: MagicMock) -> None:
    """Test that get_filters calls the SDK client."""
    client = MagicMock()
    client.resource_url.return_value = "https://jira.example.com/rest/api/2/filter"
    client.get.return_value = {
        "values": [{"id": 10000, "name": "Filter 1"}, {"id": 10001, "name": "Filter 2"}]
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.get_filters()

    assert len(result) == 2
    assert result[0]["id"] == 10000


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_filters_with_owner(mock_jira: MagicMock) -> None:
    """Test that get_filters filters by owner."""
    client = MagicMock()
    client.resource_url.return_value = "https://jira.example.com/rest/api/2/filter"
    client.get.return_value = {
        "values": [{"id": 10000, "name": "My Filter", "owner": {"name": "user"}}]
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    adapter.get_filters(owner="user")

    client.get.assert_called_once()
    assert "username" in str(client.get.call_args)


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_filter_calls_client(mock_jira: MagicMock) -> None:
    """Test that get_filter calls the SDK client."""
    client = MagicMock()
    client.get_filter.return_value = {
        "id": 10000,
        "name": "Test Filter",
        "jql": "project = TEST",
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.get_filter(10000)

    client.get_filter.assert_called_once_with(10000)
    assert result["id"] == 10000


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_filter_not_found(mock_jira: MagicMock) -> None:
    """Test that get_filter raises NotFoundError when filter is not found."""
    client = MagicMock()
    client.get_filter.return_value = None
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )

    with pytest.raises(NotFoundError, match="Filter not found: 99999"):
        adapter.get_filter(99999)


@patch("vds_jira_orchestrator.adapter.Jira")
def test_create_filter_calls_client(mock_jira: MagicMock) -> None:
    """Test that create_filter calls the SDK client."""
    client = MagicMock()
    client.create_filter.return_value = {
        "id": 10000,
        "name": "New Filter",
        "jql": "project = TEST",
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.create_filter(
        name="New Filter", jql="project = TEST", description="Test filter"
    )

    client.create_filter.assert_called_once_with(
        name="New Filter",
        jql="project = TEST",
        description="Test filter",
        favourite=False,
    )
    assert result["id"] == 10000


@patch("vds_jira_orchestrator.adapter.Jira")
def test_create_filter_with_favourite(mock_jira: MagicMock) -> None:
    """Test that create_filter can mark filter as favourite."""
    client = MagicMock()
    client.create_filter.return_value = {
        "id": 10000,
        "name": "Favourite Filter",
        "favourite": True,
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.create_filter(
        name="Favourite Filter", jql="project = TEST", favourite=True
    )

    client.create_filter.assert_called_once_with(
        name="Favourite Filter", jql="project = TEST", description=None, favourite=True
    )
    assert result["favourite"] is True


@patch("vds_jira_orchestrator.adapter.Jira")
def test_update_filter_calls_client(mock_jira: MagicMock) -> None:
    """Test that update_filter calls the SDK client."""
    client = MagicMock()
    client.get_filter.return_value = {
        "id": 10000,
        "name": "Old Name",
        "jql": "project = TEST",
    }
    client.update_filter.return_value = {
        "id": 10000,
        "name": "New Name",
        "jql": "project = TEST",
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.update_filter(filter_id=10000, name="New Name")

    client.update_filter.assert_called_once()
    assert result["name"] == "New Name"


@patch("vds_jira_orchestrator.adapter.Jira")
def test_update_filter_with_jql(mock_jira: MagicMock) -> None:
    """Test that update_filter can update JQL."""
    client = MagicMock()
    client.update_filter.return_value = {
        "id": 10000,
        "name": "Filter",
        "jql": "project = NEW",
    }
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.update_filter(filter_id=10000, jql="project = NEW")

    client.update_filter.assert_called_once()
    assert result["jql"] == "project = NEW"


@patch("vds_jira_orchestrator.adapter.Jira")
def test_delete_filter_calls_client(mock_jira: MagicMock) -> None:
    """Test that delete_filter calls the SDK client."""
    client = MagicMock()
    client.delete_filter.return_value = None
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    adapter.delete_filter(10000)

    client.delete_filter.assert_called_once_with(10000)


@patch("vds_jira_orchestrator.adapter.Jira")
def test_get_filters_handles_list_response(mock_jira: MagicMock) -> None:
    """Test that get_filters handles list response format."""
    client = MagicMock()
    client.resource_url.return_value = "https://jira.example.com/rest/api/2/filter"
    client.get.return_value = [{"id": 10000, "name": "Filter 1"}]
    mock_jira.return_value = client

    adapter = JiraAdapter(
        url="https://jira.example.com", username="user", password="pass"
    )
    result = adapter.get_filters()

    assert len(result) == 1
    assert result[0]["id"] == 10000


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_list_success(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter list CLI command success."""
    mock_adapter = MagicMock()
    mock_adapter.get_filters.return_value = [{"id": 10000, "name": "Filter 1"}]
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["filter", "list"])

    assert result.exit_code == 0
    assert "filters" in result.stdout
    mock_adapter.get_filters.assert_called_once_with(owner=None)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_list_with_owner(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter list CLI command with owner filter."""
    mock_adapter = MagicMock()
    mock_adapter.get_filters.return_value = [{"id": 10000, "name": "My Filter"}]
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["filter", "list", "--owner", "user"])

    assert result.exit_code == 0
    mock_adapter.get_filters.assert_called_once_with(owner="user")


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_get_success(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter get CLI command success."""
    mock_adapter = MagicMock()
    mock_adapter.get_filter.return_value = {
        "id": 10000,
        "name": "Test Filter",
        "jql": "project = TEST",
    }
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["filter", "get", "--filter-id", "10000"])

    assert result.exit_code == 0
    assert "10000" in result.stdout
    mock_adapter.get_filter.assert_called_once_with(10000)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_get_requires_id(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter get CLI command requires filter ID."""
    result = runner.invoke(app, ["filter", "get"])

    assert result.exit_code != 0
    assert (
        "--filter-id required" in result.stdout
        or "--filter-id required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_create_success(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter create CLI command success."""
    mock_adapter = MagicMock()
    mock_adapter.create_filter.return_value = {
        "id": 10000,
        "name": "New Filter",
        "jql": "project = TEST",
    }
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app,
        [
            "filter",
            "create",
            "--name",
            "New Filter",
            "--jql",
            "project = TEST",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_adapter.create_filter.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_create_requires_yes(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter create CLI command requires --yes flag."""
    result = runner.invoke(
        app, ["filter", "create", "--name", "New Filter", "--jql", "project = TEST"]
    )

    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "without --yes" in result.stdout
        or "without --yes" in result.stderr
        or "Refusing" in result.stdout
        or "Refusing" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_create_requires_name(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter create CLI command requires name."""
    result = runner.invoke(
        app, ["filter", "create", "--jql", "project = TEST", "--yes"]
    )

    assert result.exit_code != 0
    assert "--name required" in result.stdout or "--name required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_create_requires_jql(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter create CLI command requires JQL."""
    result = runner.invoke(app, ["filter", "create", "--name", "New Filter", "--yes"])

    assert result.exit_code != 0
    assert "--jql required" in result.stdout or "--jql required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_update_success(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter update CLI command success."""
    mock_adapter = MagicMock()
    mock_adapter.get_filter.return_value = {
        "id": 10000,
        "name": "Old Name",
        "jql": "project = TEST",
    }
    mock_adapter.update_filter.return_value = {
        "id": 10000,
        "name": "New Name",
        "jql": "project = TEST",
    }
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(
        app, ["filter", "update", "--filter-id", "10000", "--name", "New Name", "--yes"]
    )

    assert result.exit_code == 0
    mock_adapter.update_filter.assert_called_once()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_update_requires_yes(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter update CLI command requires --yes flag."""
    result = runner.invoke(
        app, ["filter", "update", "--filter-id", "10000", "--name", "New Name"]
    )

    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "without --yes" in result.stdout
        or "without --yes" in result.stderr
        or "Refusing" in result.stdout
        or "Refusing" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_update_requires_field(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter update CLI command requires at least one field."""
    result = runner.invoke(app, ["filter", "update", "--filter-id", "10000", "--yes"])

    assert result.exit_code != 0
    assert "At least one" in result.stdout or "At least one" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_delete_success(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter delete CLI command success."""
    mock_adapter = MagicMock()
    mock_adapter.delete_filter.return_value = None
    mock_adapter_class.return_value = mock_adapter

    result = runner.invoke(app, ["filter", "delete", "--filter-id", "10000", "--yes"])

    assert result.exit_code == 0
    assert "success" in result.stdout
    mock_adapter.delete_filter.assert_called_once_with(10000)


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_delete_requires_yes(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter delete CLI command requires --yes flag."""
    result = runner.invoke(app, ["filter", "delete", "--filter-id", "10000"])

    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "without --yes" in result.stdout
        or "without --yes" in result.stderr
        or "Refusing" in result.stdout
        or "Refusing" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_cli_filter_invalid_action(
    mock_settings: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test filter CLI command with invalid action."""
    result = runner.invoke(app, ["filter", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
