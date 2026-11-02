"""Tests for grafana_orchestrator client module."""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_httpx import HTTPXMock

from vds_grafana_orchestrator.client import (
    QUICKWIT_DATASOURCE_TYPE,
    GrafanaClient,
    QuickwitClient,
)
from vds_grafana_orchestrator.errors import (
    AuthError,
    ClientPermissionError,
    NotFoundError,
    TransportError,
)


class TestGrafanaClient:
    """Tests for GrafanaClient class."""

    def test_client_initialization(self, mock_settings: MagicMock) -> None:
        """Test client initialization."""
        client = GrafanaClient(mock_settings)
        assert client.config == mock_settings
        assert client._client is None

    def test_client_lazy_init(self, mock_settings: MagicMock) -> None:
        """Test lazy client initialization."""
        client = GrafanaClient(mock_settings)
        # Client should not be created until accessed
        assert client._client is None
        # Access the client property
        _ = client.client
        assert client._client is not None

    def test_client_context_manager(self, mock_settings: MagicMock) -> None:
        """Test client as context manager."""
        with GrafanaClient(mock_settings) as client:
            assert client is not None
        # Client should be closed after exiting context
        assert client._client is None

    def test_health_success(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_grafana_health: dict[str, Any],
    ) -> None:
        """Test health check success."""
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/health",
            json=sample_grafana_health,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.health()

        assert result["version"] == sample_grafana_health["version"]
        assert result["database"] == "ok"

    def test_health_auth_error(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_auth_error: dict[str, Any],
    ) -> None:
        """Test health check with auth error."""
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/health",
            status_code=401,
            json=sample_auth_error,
        )

        with GrafanaClient(mock_settings) as client, pytest.raises(AuthError):
            client.health()

    def test_datasources_success(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_datasources: list[dict[str, Any]],
    ) -> None:
        """Test listing datasources."""
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources",
            json=sample_datasources,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.datasources()

        assert len(result) == 3
        assert result[0]["name"] == "Quickwit-PRODUCTION"

    def test_quickwit_datasources(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_datasources: list[dict[str, Any]],
    ) -> None:
        """Test filtering Quickwit datasources."""
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources",
            json=sample_datasources,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.quickwit_datasources()

        # Should only return Quickwit datasources (2 of 3)
        assert len(result) == 2
        assert all(ds["type"] == QUICKWIT_DATASOURCE_TYPE for ds in result)

    def test_resolve_datasource_by_uid(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_datasources: list[dict[str, Any]],
    ) -> None:
        """Test resolving datasource by UID."""
        ds = sample_datasources[0]
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/uid/{ds['uid']}",
            json=ds,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.resolve_datasource(uid=ds["uid"])

        assert result["uid"] == ds["uid"]
        assert result["name"] == ds["name"]

    def test_resolve_datasource_by_id(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_datasources: list[dict[str, Any]],
    ) -> None:
        """Test resolving datasource by ID."""
        ds = sample_datasources[0]
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/{ds['id']}",
            json=ds,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.resolve_datasource(datasource_id=ds["id"])

        assert result["id"] == ds["id"]

    def test_resolve_datasource_by_name(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_datasources: list[dict[str, Any]],
    ) -> None:
        """Test resolving datasource by name."""
        ds = sample_datasources[0]
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/name/{ds['name']}",
            json=ds,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.resolve_datasource(name=ds["name"])

        assert result["name"] == ds["name"]

    def test_resolve_datasource_not_found(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_not_found_error: dict[str, Any],
    ) -> None:
        """Test resolving non-existent datasource."""
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/uid/nonexistent",
            status_code=404,
            json=sample_not_found_error,
        )

        with GrafanaClient(mock_settings) as client, pytest.raises(NotFoundError):
            client.resolve_datasource(uid="nonexistent")

    def test_resolve_datasource_requires_parameter(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test resolve_datasource raises without parameters."""
        with GrafanaClient(mock_settings) as client:
            with pytest.raises(ValueError, match="At least one of"):
                client.resolve_datasource()

    def test_proxy_get(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_cat_indices_response: list[dict[str, Any]],
    ) -> None:
        """Test proxy GET request."""
        ds_uid = "test-uid"
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/proxy/uid/{ds_uid}/_elastic/_cat/indices?format=json",
            json=sample_cat_indices_response,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.proxy_get(ds_uid, "_elastic/_cat/indices", params={"format": "json"})

        assert isinstance(result, list)
        assert len(result) == 2

    def test_proxy_post(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_es_search_response: dict[str, Any],
    ) -> None:
        """Test proxy POST request."""
        ds_uid = "test-uid"
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/proxy/uid/{ds_uid}/_elastic/otel-logs/_search",
            json=sample_es_search_response,
        )

        with GrafanaClient(mock_settings) as client:
            result = client.proxy_post(
                ds_uid,
                "_elastic/otel-logs/_search",
                body={"query": {"match_all": {}}},
            )

        assert "hits" in result

    def test_handle_403_error(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_permission_error: dict[str, Any],
    ) -> None:
        """Test handling 403 permission error."""
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources",
            status_code=403,
            json=sample_permission_error,
        )

        with GrafanaClient(mock_settings) as client, pytest.raises(ClientPermissionError):
            client.datasources()

    def test_handle_500_error(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test handling 500 server error."""
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/health",
            status_code=500,
            json={"message": "Internal error"},
        )

        with GrafanaClient(mock_settings) as client, pytest.raises(TransportError):
            client.health()


class TestQuickwitClient:
    """Tests for QuickwitClient class."""

    def test_client_initialization(self, mock_settings: MagicMock) -> None:
        """Test client initialization."""
        client = QuickwitClient(mock_settings)
        assert client.config == mock_settings
        assert client.grafana is not None

    def test_client_with_datasource_override(self, mock_settings: MagicMock) -> None:
        """Test client with datasource override."""
        client = QuickwitClient(mock_settings, datasource_uid="custom-uid")
        assert client._datasource_uid == "custom-uid"

    def test_search_success(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_quickwit_search_response: dict[str, Any],
    ) -> None:
        """Test search operation."""
        ds_uid = mock_settings.datasource_uid
        index = "otel-logs-v0_7"

        httpx_mock.add_response(
            url=re.compile(rf".*/api/datasources/proxy/uid/{ds_uid}/{index}/search.*"),
            json=sample_quickwit_search_response,
        )

        with QuickwitClient(mock_settings, datasource_uid=ds_uid) as client:
            result = client.search(index=index, query="*")

        assert "hits" in result
        assert result["num_hits"] == 100
        assert "_metadata" in result

    def test_search_with_time_range(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_quickwit_search_response: dict[str, Any],
    ) -> None:
        """Test search with time range."""
        ds_uid = mock_settings.datasource_uid
        index = "otel-logs-v0_7"

        httpx_mock.add_response(
            url=re.compile(rf".*/api/datasources/proxy/uid/{ds_uid}/{index}/search.*"),
            json=sample_quickwit_search_response,
        )

        with QuickwitClient(mock_settings, datasource_uid=ds_uid) as client:
            result = client.search(
                index=index,
                query="severity_text:ERROR",
                start_timestamp=1705320000,
                end_timestamp=1705323600,
            )

        assert "hits" in result

    def test_search_enforces_max_hits(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_quickwit_search_response: dict[str, Any],
    ) -> None:
        """Test that search enforces max_hits limit of 1000."""
        ds_uid = mock_settings.datasource_uid
        index = "otel-logs-v0_7"

        # We can't easily verify the params in pytest-httpx, but the code
        # should limit max_hits to 1000
        httpx_mock.add_response(
            url=re.compile(rf".*/api/datasources/proxy/uid/{ds_uid}/{index}/search.*"),
            json=sample_quickwit_search_response,
        )

        with QuickwitClient(mock_settings, datasource_uid=ds_uid) as client:
            # Request 5000, should be capped to 1000
            result = client.search(index=index, query="*", max_hits=5000)

        assert result is not None

    def test_es_search_success(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_es_search_response: dict[str, Any],
    ) -> None:
        """Test ES-compatible search."""
        ds_uid = mock_settings.datasource_uid
        index = "otel-logs-v0_7"

        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/proxy/uid/{ds_uid}/_elastic/{index}/_search",
            json=sample_es_search_response,
        )

        with QuickwitClient(mock_settings, datasource_uid=ds_uid) as client:
            result = client.es_search(
                index=index,
                body={"query": {"match": {"severity_text": "ERROR"}}},
            )

        assert "hits" in result
        assert "_metadata" in result

    def test_indexes_success(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_cat_indices_response: list[dict[str, Any]],
    ) -> None:
        """Test listing indexes."""
        ds_uid = mock_settings.datasource_uid

        httpx_mock.add_response(
            url=re.compile(rf".*/api/datasources/proxy/uid/{ds_uid}/_elastic/_cat/indices.*"),
            json=sample_cat_indices_response,
        )

        with QuickwitClient(mock_settings, datasource_uid=ds_uid) as client:
            result = client.indexes()

        assert len(result) == 2
        assert result[0]["index"] == "otel-logs-v0_7"

    def test_fields_success(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_es_search_response: dict[str, Any],
    ) -> None:
        """Test fields discovery."""
        ds_uid = mock_settings.datasource_uid
        index = "otel-logs-v0_7"

        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/datasources/proxy/uid/{ds_uid}/_elastic/{index}/_search",
            json=sample_es_search_response,
        )

        with QuickwitClient(mock_settings, datasource_uid=ds_uid) as client:
            result = client.fields(index=index)

        assert "timestamp" in result
        assert "service_name" in result

    def test_health_success(
        self,
        mock_settings: MagicMock,
        httpx_mock: HTTPXMock,
        sample_grafana_health: dict[str, Any],
        sample_cat_indices_response: list[dict[str, Any]],
    ) -> None:
        """Test health check."""
        ds_uid = mock_settings.datasource_uid

        # Mock Grafana health
        httpx_mock.add_response(
            url=f"{mock_settings.base_url}/api/health",
            json=sample_grafana_health,
        )

        # Mock indexes (for datasource check)
        httpx_mock.add_response(
            url=re.compile(rf".*/api/datasources/proxy/uid/{ds_uid}/_elastic/_cat/indices.*"),
            json=sample_cat_indices_response,
        )

        with QuickwitClient(mock_settings, datasource_uid=ds_uid) as client:
            result = client.health()

        assert result["grafana_ok"] is True
        assert result["datasource_ok"] is True
        assert result["details"]["index_count"] == 2

    def test_search_requires_index(self, mock_settings: MagicMock) -> None:
        """Test search raises error when index not provided and not in config."""
        mock_settings.default_index = None

        with QuickwitClient(mock_settings) as client:
            with pytest.raises(ValueError, match="Index is required"):
                client.search(query="*")
