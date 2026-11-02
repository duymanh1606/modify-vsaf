from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_list_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test successful version list."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_project_versions_paginated.return_value = {
        "values": [{"id": "10000", "name": "1.0.0"}, {"id": "10001", "name": "1.0.1"}],
        "startAt": 0,
        "maxResults": 25,
    }

    result = runner.invoke(app, ["version", "list", "--project-key", "TEST"])
    assert result.exit_code == 0
    assert "1.0.0" in result.stdout
    assert "1.0.1" in result.stdout
    mock_adapter.get_project_versions_paginated.assert_called_once_with(
        project_key="TEST",
        start=None,
        limit=None,
        order_by=None,
        query=None,
        status=None,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_list_with_pagination(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version list with pagination."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_project_versions_paginated.return_value = {
        "values": [{"id": "10002", "name": "2.0.0"}],
        "startAt": 10,
        "maxResults": 20,
    }

    result = runner.invoke(
        app,
        ["version", "list", "--project-key", "TEST", "--start", "10", "--limit", "20"],
    )
    assert result.exit_code == 0
    assert "2.0.0" in result.stdout
    mock_adapter.get_project_versions_paginated.assert_called_once_with(
        project_key="TEST", start=10, limit=20, order_by=None, query=None, status=None
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_list_with_filtering(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version list with filtering and sorting."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_project_versions_paginated.return_value = {
        "values": [{"id": "10003", "name": "3.0.0"}],
        "startAt": 0,
        "maxResults": 25,
    }

    result = runner.invoke(
        app,
        [
            "version",
            "list",
            "--project-key",
            "TEST",
            "--order-by",
            "name",
            "--query",
            "3.0",
            "--status",
            "released",
        ],
    )
    assert result.exit_code == 0
    assert "3.0.0" in result.stdout
    mock_adapter.get_project_versions_paginated.assert_called_once_with(
        project_key="TEST",
        start=None,
        limit=None,
        order_by="name",
        query="3.0",
        status="released",
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_list_requires_project_key(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version list requires --project-key."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(app, ["version", "list"])
    assert result.exit_code != 0
    assert (
        "--project-key required" in result.stdout
        or "--project-key required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_create_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test successful version create."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.add_version.return_value = {"id": "10000", "name": "1.0.0"}

    result = runner.invoke(
        app,
        [
            "version",
            "create",
            "--project-key",
            "TEST",
            "--project-id",
            "10000",
            "--name",
            "1.0.0",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "1.0.0" in result.stdout
    mock_adapter.add_version.assert_called_once_with(
        key="TEST",
        project_id="10000",
        version="1.0.0",
        is_archived=False,
        is_released=False,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_create_with_flags(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version create with archived and released flags."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.add_version.return_value = {
        "id": "10001",
        "name": "1.0.1",
        "archived": True,
        "released": True,
    }

    result = runner.invoke(
        app,
        [
            "version",
            "create",
            "--project-key",
            "TEST",
            "--project-id",
            "10000",
            "--name",
            "1.0.1",
            "--archived",
            "--released",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.add_version.assert_called_once_with(
        key="TEST",
        project_id="10000",
        version="1.0.1",
        is_archived=True,
        is_released=True,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_create_requires_yes(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version create requires --yes."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        [
            "version",
            "create",
            "--project-key",
            "TEST",
            "--project-id",
            "10000",
            "--name",
            "1.0.0",
        ],
    )
    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "Refusing" in result.stdout
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_create_requires_project_key(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version create requires --project-key."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app, ["version", "create", "--project-id", "10000", "--name", "1.0.0", "--yes"]
    )
    assert result.exit_code != 0
    assert (
        "--project-key required" in result.stdout
        or "--project-key required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_create_requires_project_id(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version create requires --project-id."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app, ["version", "create", "--project-key", "TEST", "--name", "1.0.0", "--yes"]
    )
    assert result.exit_code != 0
    assert (
        "--project-id required" in result.stdout
        or "--project-id required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_create_requires_name(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version create requires --name."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app,
        [
            "version",
            "create",
            "--project-key",
            "TEST",
            "--project-id",
            "10000",
            "--yes",
        ],
    )
    assert result.exit_code != 0
    assert "--name required" in result.stdout or "--name required" in result.stderr


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_update_success(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test successful version update."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.update_version.return_value = {"id": "10000", "name": "1.0.1"}

    result = runner.invoke(
        app, ["version", "update", "--version-id", "10000", "--name", "1.0.1", "--yes"]
    )
    assert result.exit_code == 0
    assert "1.0.1" in result.stdout
    mock_adapter.update_version.assert_called_once_with(
        version="10000",
        name="1.0.1",
        description=None,
        is_archived=None,
        is_released=None,
        start_date=None,
        release_date=None,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_update_partial(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version update with partial fields."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.update_version.return_value = {
        "id": "10000",
        "name": "1.0.0",
        "description": "Updated",
        "archived": True,
    }

    result = runner.invoke(
        app,
        [
            "version",
            "update",
            "--version-id",
            "10000",
            "--description",
            "Updated",
            "--archived",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.update_version.assert_called_once_with(
        version="10000",
        name=None,
        description="Updated",
        is_archived=True,
        is_released=None,
        start_date=None,
        release_date=None,
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_update_with_dates(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version update with dates."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    mock_adapter = Mock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.update_version.return_value = {
        "id": "10000",
        "startDate": "2025-01-01",
        "releaseDate": "2025-01-31",
    }

    result = runner.invoke(
        app,
        [
            "version",
            "update",
            "--version-id",
            "10000",
            "--start-date",
            "2025-01-01",
            "--release-date",
            "2025-01-31",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.update_version.assert_called_once_with(
        version="10000",
        name=None,
        description=None,
        is_archived=None,
        is_released=None,
        start_date="2025-01-01",
        release_date="2025-01-31",
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_update_requires_yes(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version update requires --yes."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(
        app, ["version", "update", "--version-id", "10000", "--name", "1.0.1"]
    )
    assert result.exit_code != 0
    assert (
        "--yes" in result.stdout
        or "--yes" in result.stderr
        or "Refusing" in result.stdout
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_update_requires_version_id(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version update requires --version-id."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(app, ["version", "update", "--name", "1.0.1", "--yes"])
    assert result.exit_code != 0
    assert (
        "--version-id required" in result.stdout
        or "--version-id required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_update_requires_fields(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test version update requires at least one update field."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(app, ["version", "update", "--version-id", "10000", "--yes"])
    assert result.exit_code != 0
    assert (
        "At least one update field required" in result.stdout
        or "At least one update field required" in result.stderr
    )


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_version_invalid_action(
    mock_settings_class: Mock, mock_adapter_class: Mock, runner: CliRunner
) -> None:
    """Test invalid action for version command."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    mock_settings_class.return_value = mock_settings
    result = runner.invoke(app, ["version", "invalid"])
    assert result.exit_code != 0
    assert (
        "Unknown action: invalid" in result.stdout
        or "Unknown action: invalid" in result.stderr
    )
