from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from vds_jira_orchestrator.adapter import JiraAdapter, VDSClientError


@pytest.fixture
def mock_adapter() -> JiraAdapter:
    """Fixture for a JiraAdapter."""
    with patch("vds_jira_orchestrator.adapter.Jira") as mock_jira_class:
        mock_client = MagicMock()
        mock_jira_class.return_value = mock_client
        adapter = JiraAdapter(
            url="https://jira.example.com", username="user", password="pass"
        )
        adapter._client = mock_client
        return adapter


def test_bulk_update_issue_field_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that bulk_update_issue_field calls the SDK client with correct parameters."""
    mock_adapter._client.bulk_update_issue_field.return_value = {
        "updated": 2,
        "errors": [],
    }
    result = mock_adapter.bulk_update_issue_field(
        key_list=["TEST-1", "TEST-2"], fields="*all"
    )
    mock_adapter._client.bulk_update_issue_field.assert_called_once_with(
        ["TEST-1", "TEST-2"], fields="*all"
    )
    assert result["updated"] == 2


def test_bulk_update_issue_field_with_fields(mock_adapter: JiraAdapter) -> None:
    """Test bulk_update_issue_field with specific fields."""
    mock_adapter._client.bulk_update_issue_field.return_value = {
        "updated": 1,
        "errors": [],
    }
    fields_json = '{"summary": "Updated summary"}'
    result = mock_adapter.bulk_update_issue_field(
        key_list=["TEST-1"], fields=fields_json
    )
    mock_adapter._client.bulk_update_issue_field.assert_called_once_with(
        ["TEST-1"], fields=fields_json
    )
    assert result["updated"] == 1


def test_bulk_update_issue_field_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that bulk_update_issue_field handles errors from the SDK client."""
    mock_adapter._client.bulk_update_issue_field.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.bulk_update_issue_field(key_list=["TEST-1"], fields="*all")


def test_issue_field_value_append_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that issue_field_value_append calls the SDK client with correct parameters."""
    mock_adapter._client.issue_field_value_append.return_value = {
        "id": "10000",
        "value": "appended",
    }
    value_dict = {"name": "test-value"}
    result = mock_adapter.issue_field_value_append(
        issue_id_or_key="TEST-1", field="customfield_10000", value=value_dict
    )
    mock_adapter._client.issue_field_value_append.assert_called_once_with(
        "TEST-1", "customfield_10000", value_dict, notify_users=True
    )
    assert result["id"] == "10000"


def test_issue_field_value_append_with_notify_false(mock_adapter: JiraAdapter) -> None:
    """Test issue_field_value_append with notify_users=False."""
    mock_adapter._client.issue_field_value_append.return_value = {
        "id": "10001",
        "value": "appended",
    }
    value_dict = {"name": "another-value"}
    result = mock_adapter.issue_field_value_append(
        issue_id_or_key="TEST-2",
        field="customfield_10000",
        value=value_dict,
        notify_users=False,
    )
    mock_adapter._client.issue_field_value_append.assert_called_once_with(
        "TEST-2", "customfield_10000", value_dict, notify_users=False
    )
    assert result["id"] == "10001"


def test_issue_field_value_append_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that issue_field_value_append handles errors from the SDK client."""
    mock_adapter._client.issue_field_value_append.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.issue_field_value_append(
            issue_id_or_key="TEST-1", field="customfield_10000", value={"name": "value"}
        )
