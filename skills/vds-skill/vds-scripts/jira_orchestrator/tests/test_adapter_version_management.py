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
        adapter = JiraAdapter(url="https://jira.example.com", username="user", password="pass")
        adapter._client = mock_client
        return adapter


def test_get_project_versions_paginated_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that get_project_versions_paginated calls the SDK client with correct parameters."""
    mock_adapter._client.get_project_versions_paginated.return_value = {
        "values": [{"id": "10000", "name": "1.0.0"}],
        "startAt": 0,
        "maxResults": 25,
    }
    result = mock_adapter.get_project_versions_paginated(project_key="TEST")
    mock_adapter._client.get_project_versions_paginated.assert_called_once_with(
        "TEST",
        start=None,
        limit=None,
        order_by=None,
        expand=None,
        query=None,
        status=None,
    )
    assert "values" in result
    assert len(result["values"]) == 1


def test_get_project_versions_paginated_with_pagination(
    mock_adapter: JiraAdapter,
) -> None:
    """Test get_project_versions_paginated with pagination parameters."""
    mock_adapter._client.get_project_versions_paginated.return_value = {
        "values": [{"id": "10001", "name": "1.0.1"}],
        "startAt": 10,
        "maxResults": 20,
    }
    result = mock_adapter.get_project_versions_paginated(project_key="TEST", start=10, limit=20)
    mock_adapter._client.get_project_versions_paginated.assert_called_once_with(
        "TEST", start=10, limit=20, order_by=None, expand=None, query=None, status=None
    )
    assert result["startAt"] == 10


def test_get_project_versions_paginated_with_filtering(
    mock_adapter: JiraAdapter,
) -> None:
    """Test get_project_versions_paginated with filtering and sorting."""
    mock_adapter._client.get_project_versions_paginated.return_value = {
        "values": [{"id": "10002", "name": "2.0.0"}],
        "startAt": 0,
        "maxResults": 25,
    }
    result = mock_adapter.get_project_versions_paginated(
        project_key="TEST", order_by="name", query="2.0", status="released"
    )
    mock_adapter._client.get_project_versions_paginated.assert_called_once_with(
        "TEST",
        start=None,
        limit=None,
        order_by="name",
        expand=None,
        query="2.0",
        status="released",
    )
    assert len(result["values"]) == 1


def test_add_version_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that add_version calls the SDK client."""
    mock_adapter._client.add_version.return_value = {"id": "10000", "name": "1.0.0"}
    result = mock_adapter.add_version(key="TEST", project_id="10000", version="1.0.0")
    mock_adapter._client.add_version.assert_called_once_with(
        "TEST", "10000", "1.0.0", is_archived=False, is_released=False
    )
    assert result["name"] == "1.0.0"


def test_add_version_with_flags(mock_adapter: JiraAdapter) -> None:
    """Test add_version with archived and released flags."""
    mock_adapter._client.add_version.return_value = {
        "id": "10001",
        "name": "1.0.1",
        "archived": True,
        "released": True,
    }
    result = mock_adapter.add_version(
        key="TEST",
        project_id="10000",
        version="1.0.1",
        is_archived=True,
        is_released=True,
    )
    mock_adapter._client.add_version.assert_called_once_with(
        "TEST", "10000", "1.0.1", is_archived=True, is_released=True
    )
    assert result["archived"] is True


def test_add_version_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that add_version handles errors from the SDK client."""
    mock_adapter._client.add_version.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.add_version(key="TEST", project_id="10000", version="1.0.0")


def test_update_version_calls_client(mock_adapter: JiraAdapter) -> None:
    """Test that update_version calls the SDK client."""
    mock_adapter._client.update_version.return_value = {"id": "10000", "name": "1.0.1"}
    result = mock_adapter.update_version(version="10000", name="1.0.1")
    mock_adapter._client.update_version.assert_called_once_with(
        "10000",
        name="1.0.1",
        description=None,
        is_archived=None,
        is_released=None,
        start_date=None,
        release_date=None,
    )
    assert result["name"] == "1.0.1"


def test_update_version_partial_update(mock_adapter: JiraAdapter) -> None:
    """Test update_version with partial updates."""
    mock_adapter._client.update_version.return_value = {
        "id": "10000",
        "name": "1.0.0",
        "description": "Updated description",
        "archived": True,
    }
    result = mock_adapter.update_version(version="10000", description="Updated description", is_archived=True)
    mock_adapter._client.update_version.assert_called_once_with(
        "10000",
        name=None,
        description="Updated description",
        is_archived=True,
        is_released=None,
        start_date=None,
        release_date=None,
    )
    assert result["description"] == "Updated description"


def test_update_version_with_dates(mock_adapter: JiraAdapter) -> None:
    """Test update_version with start and release dates."""
    mock_adapter._client.update_version.return_value = {
        "id": "10000",
        "name": "1.0.0",
        "startDate": "2025-01-01",
        "releaseDate": "2025-01-31",
    }
    result = mock_adapter.update_version(version="10000", start_date="2025-01-01", release_date="2025-01-31")
    mock_adapter._client.update_version.assert_called_once_with(
        "10000",
        name=None,
        description=None,
        is_archived=None,
        is_released=None,
        start_date="2025-01-01",
        release_date="2025-01-31",
    )
    assert result["startDate"] == "2025-01-01"


def test_update_version_handles_error(mock_adapter: JiraAdapter) -> None:
    """Test that update_version handles errors from the SDK client."""
    mock_adapter._client.update_version.side_effect = Exception("API Error")
    with pytest.raises(VDSClientError, match="API Error"):
        mock_adapter.update_version(version="10000", name="1.0.1")
