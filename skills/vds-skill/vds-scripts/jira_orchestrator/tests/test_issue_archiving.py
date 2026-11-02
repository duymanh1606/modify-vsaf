from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.adapter import JiraAdapter, VDSClientError
from vds_jira_orchestrator.cli import app


@pytest.fixture
def mock_adapter() -> JiraAdapter:
    """Fixture for a JiraAdapter."""
    with patch("vds_jira_orchestrator.adapter.Jira") as mock_jira_class:
        mock_client = MagicMock()
        mock_jira_class.return_value = mock_client
        adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
        adapter._client = mock_client
        return adapter


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_settings_class() -> MagicMock:
    """Mock JiraSettings for CLI tests."""
    mock_settings = Mock()
    mock_settings.base_url = "https://jira.example.com"
    mock_settings.username = "testuser"
    mock_settings.password = "testpass"
    mock_settings.token = None
    mock_settings.require_basic_or_token = Mock()
    with patch("vds_jira_orchestrator.cli.JiraSettings") as mock_class:
        mock_class.return_value = mock_settings
        yield mock_class


@pytest.fixture
def mock_adapter_class() -> MagicMock:
    """Mock JiraAdapter for CLI tests."""
    with patch("vds_jira_orchestrator.cli.JiraAdapter") as mock_class:
        yield mock_class


# ---------------------------------------------------------------------------
# Adapter method tests
# ---------------------------------------------------------------------------


def test_issue_archive_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that issue_archive calls the SDK client."""
    mock_adapter._client.issue_archive.return_value = None
    mock_adapter.issue_archive("PROJ-1")
    mock_adapter._client.issue_archive.assert_called_once_with("PROJ-1")


def test_issue_archive_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that issue_archive handles errors from the SDK client."""
    mock_adapter._client.issue_archive.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.issue_archive("PROJ-1")


def test_issue_restore_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that issue_restore calls the SDK client."""
    mock_adapter._client.issue_restore.return_value = None
    mock_adapter.issue_restore("PROJ-1")
    mock_adapter._client.issue_restore.assert_called_once_with("PROJ-1")


def test_issue_restore_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that issue_restore handles errors from the SDK client."""
    mock_adapter._client.issue_restore.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.issue_restore("PROJ-1")


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


def test_issue_archive_success(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test successful issue archive."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.issue_archive.return_value = None

    result = runner.invoke(app, ["issue-archive", "--issue-key", "PROJ-1", "--yes"])
    assert result.exit_code == 0
    assert "archived" in result.stdout
    assert "PROJ-1" in result.stdout
    mock_adapter.issue_archive.assert_called_once_with("PROJ-1")


def test_issue_archive_requires_yes(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test issue archive requires --yes flag."""
    result = runner.invoke(app, ["issue-archive", "--issue-key", "PROJ-1"])
    assert result.exit_code != 0
    assert "Refusing to archive issue without --yes" in result.stderr
    mock_adapter_class.return_value.issue_archive.assert_not_called()


def test_issue_archive_requires_issue_key(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test issue archive requires --issue-key."""
    result = runner.invoke(app, ["issue-archive", "--yes"])
    assert result.exit_code != 0
    # Typer will show error about missing required option
    mock_adapter_class.return_value.issue_archive.assert_not_called()


def test_issue_restore_success(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test successful issue restore."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.issue_restore.return_value = None

    result = runner.invoke(app, ["issue-restore", "--issue-key", "PROJ-1", "--yes"])
    assert result.exit_code == 0
    assert "restored" in result.stdout
    assert "PROJ-1" in result.stdout
    mock_adapter.issue_restore.assert_called_once_with("PROJ-1")


def test_issue_restore_requires_yes(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test issue restore requires --yes flag."""
    result = runner.invoke(app, ["issue-restore", "--issue-key", "PROJ-1"])
    assert result.exit_code != 0
    assert "Refusing to restore issue without --yes" in result.stderr
    mock_adapter_class.return_value.issue_restore.assert_not_called()


def test_issue_restore_requires_issue_key(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test issue restore requires --issue-key."""
    result = runner.invoke(app, ["issue-restore", "--yes"])
    assert result.exit_code != 0
    # Typer will show error about missing required option
    mock_adapter_class.return_value.issue_restore.assert_not_called()


def test_issue_archive_cli_handles_error(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test issue archive CLI handles adapter errors."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.issue_archive.side_effect = VDSClientError("Issue not found")

    result = runner.invoke(app, ["issue-archive", "--issue-key", "PROJ-999", "--yes"])
    assert result.exit_code != 0
    assert "Issue not found" in result.stderr


def test_issue_restore_cli_handles_error(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test issue restore CLI handles adapter errors."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.issue_restore.side_effect = VDSClientError("Issue not found")

    result = runner.invoke(app, ["issue-restore", "--issue-key", "PROJ-999", "--yes"])
    assert result.exit_code != 0
    assert "Issue not found" in result.stderr
