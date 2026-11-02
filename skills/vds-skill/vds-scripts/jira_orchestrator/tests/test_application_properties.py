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


def test_get_property_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that get_property calls the SDK client with correct parameters."""
    mock_adapter._client.get_property.return_value = {
        "key": "test.key",
        "value": "test_value",
    }
    result = mock_adapter.get_property(key="test.key")
    mock_adapter._client.get_property.assert_called_once_with(key="test.key", permission_level=None, key_filter=None)
    assert result["key"] == "test.key"


def test_get_property_with_filters(mock_adapter: JiraAdapter) -> None:
    """Test get_property with permission level and key filter."""
    mock_adapter._client.get_property.return_value = {
        "key": "test.key",
        "value": "test_value",
    }
    result = mock_adapter.get_property(key="test.key", permission_level="SYSTEM", key_filter="test.*")
    mock_adapter._client.get_property.assert_called_once_with(
        key="test.key", permission_level="SYSTEM", key_filter="test.*"
    )
    assert result["key"] == "test.key"


def test_get_property_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that get_property handles errors from the SDK client."""
    mock_adapter._client.get_property.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.get_property(key="test.key")


def test_set_property_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that set_property calls the SDK client."""
    mock_adapter._client.set_property.return_value = None
    mock_adapter.set_property("prop.id", "new_value")
    mock_adapter._client.set_property.assert_called_once_with("prop.id", "new_value")


def test_set_property_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that set_property handles errors from the SDK client."""
    mock_adapter._client.set_property.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.set_property("prop.id", "value")


def test_get_advanced_settings_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that get_advanced_settings calls the SDK client."""
    mock_adapter._client.get_advanced_settings.return_value = {
        "setting1": "value1",
        "setting2": "value2",
    }
    result = mock_adapter.get_advanced_settings()
    mock_adapter._client.get_advanced_settings.assert_called_once()
    assert "setting1" in result


def test_get_advanced_settings_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that get_advanced_settings handles errors from the SDK client."""
    mock_adapter._client.get_advanced_settings.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.get_advanced_settings()


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


def test_property_get_success(runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock) -> None:
    """Test successful property get."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_property.return_value = {"key": "test.key", "value": "test_value"}

    result = runner.invoke(app, ["property", "get", "--key", "test.key"])
    assert result.exit_code == 0
    assert "test.key" in result.stdout
    mock_adapter.get_property.assert_called_once_with(key="test.key", permission_level=None, key_filter=None)


def test_property_get_with_filters(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test property get with filters."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_property.return_value = {"key": "test.key", "value": "test_value"}

    result = runner.invoke(
        app,
        [
            "property",
            "get",
            "--key",
            "test.key",
            "--permission-level",
            "SYSTEM",
            "--key-filter",
            "test.*",
        ],
    )
    assert result.exit_code == 0
    mock_adapter.get_property.assert_called_once_with(key="test.key", permission_level="SYSTEM", key_filter="test.*")


def test_property_set_success(runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock) -> None:
    """Test successful property set."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.set_property.return_value = None

    result = runner.invoke(
        app,
        [
            "property",
            "set",
            "--property-id",
            "prop.id",
            "--value",
            "new_value",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    assert "set" in result.stdout
    mock_adapter.set_property.assert_called_once_with("prop.id", "new_value")


def test_property_set_requires_yes(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test property set requires --yes flag."""
    result = runner.invoke(app, ["property", "set", "--property-id", "prop.id", "--value", "new_value"])
    assert result.exit_code != 0
    assert "Refusing to set property without --yes" in result.stderr
    mock_adapter_class.return_value.set_property.assert_not_called()


def test_property_set_requires_property_id(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test property set requires --property-id."""
    result = runner.invoke(app, ["property", "set", "--value", "new_value", "--yes"])
    assert result.exit_code != 0
    assert "--property-id required for set" in result.stderr
    mock_adapter_class.return_value.set_property.assert_not_called()


def test_property_set_requires_value(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test property set requires --value."""
    result = runner.invoke(app, ["property", "set", "--property-id", "prop.id", "--yes"])
    assert result.exit_code != 0
    assert "--value required for set" in result.stderr
    mock_adapter_class.return_value.set_property.assert_not_called()


def test_settings_advanced_success(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test successful advanced settings get."""
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_adapter.get_advanced_settings.return_value = {
        "setting1": "value1",
        "setting2": "value2",
    }

    result = runner.invoke(app, ["settings", "advanced"])
    assert result.exit_code == 0
    assert "setting1" in result.stdout
    mock_adapter.get_advanced_settings.assert_called_once()


def test_property_invalid_action(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test property command with invalid action."""
    result = runner.invoke(app, ["property", "invalid"])
    assert result.exit_code != 0
    assert "Unknown action: invalid" in result.stderr


def test_settings_invalid_action(
    runner: CliRunner, mock_settings_class: MagicMock, mock_adapter_class: MagicMock
) -> None:
    """Test settings command with invalid action."""
    result = runner.invoke(app, ["settings", "invalid"])
    assert result.exit_code != 0
    assert "Unknown action: invalid" in result.stderr
