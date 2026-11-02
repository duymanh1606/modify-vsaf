"""Tests for KibanaElasticsearchClient.

Tests cover:
- Client initialization and configuration
- Request formatting for Kibana Console Proxy
- Response handling and error conversion
- Retry logic for transient errors
- Core operations (ping, search, count)
- Admin operations (info, health, indices)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from vds_elastic_orchestrator.client import KibanaElasticsearchClient, _is_retryable_status
from vds_elastic_orchestrator.config import ElasticSettings
from vds_elastic_orchestrator.errors import (
    AuthError,
    ClientPermissionError,
    ClientTimeoutError,
    ResponseError,
    TransportError,
    VDSClientError,
)


@pytest.fixture
def mock_settings() -> ElasticSettings:
    """Create mock ElasticSettings for testing."""
    return ElasticSettings(
        kibana_url="log.digital.vn",
        kibana_ip="10.207.56.26",
        user="testuser",
        password_secret="testpass",
        connect_timeout=5.0,
        request_timeout=10.0,
        max_retries=2,
        retry_backoff=0.1,
        verify_certs=False,
        default_index="logs-*",
        default_size=10,
    )


@pytest.fixture
def client(mock_settings: ElasticSettings) -> KibanaElasticsearchClient:
    """Create a KibanaElasticsearchClient instance for testing."""
    return KibanaElasticsearchClient(mock_settings)


class TestIsRetryableStatus:
    """Tests for _is_retryable_status helper function."""

    def test_retryable_502(self):
        """Test that 502 is retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 502
        assert _is_retryable_status(response) is True

    def test_retryable_503(self):
        """Test that 503 is retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 503
        assert _is_retryable_status(response) is True

    def test_retryable_504(self):
        """Test that 504 is retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 504
        assert _is_retryable_status(response) is True

    def test_not_retryable_200(self):
        """Test that 200 is not retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        assert _is_retryable_status(response) is False

    def test_not_retryable_400(self):
        """Test that 400 is not retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 400
        assert _is_retryable_status(response) is False

    def test_not_retryable_401(self):
        """Test that 401 is not retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 401
        assert _is_retryable_status(response) is False

    def test_not_retryable_403(self):
        """Test that 403 is not retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 403
        assert _is_retryable_status(response) is False

    def test_not_retryable_500(self):
        """Test that 500 is not retryable."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 500
        assert _is_retryable_status(response) is False


class TestClientInitialization:
    """Tests for client initialization."""

    def test_lazy_client_initialization(self, client: KibanaElasticsearchClient):
        """Test that HTTP client is lazily initialized."""
        assert client._client is None
        # Access client property to trigger initialization
        _ = client.client
        assert client._client is not None

    def test_client_configuration(self, mock_settings: ElasticSettings):
        """Test that client is configured correctly."""
        with KibanaElasticsearchClient(mock_settings) as client:
            http_client = client.client
            assert http_client.base_url == httpx.URL("https://10.207.56.26")
            assert http_client.headers["Host"] == "log.digital.vn"
            assert http_client.headers["kbn-xsrf"] == "true"
            assert http_client.headers["Content-Type"] == "application/json"

    def test_context_manager_closes_client(self, mock_settings: ElasticSettings):
        """Test that context manager properly closes the client."""
        with KibanaElasticsearchClient(mock_settings) as client:
            _ = client.client  # Force initialization
            assert client._client is not None
        # After context exit, client should be closed
        assert client._client is None

    def test_manual_close(self, client: KibanaElasticsearchClient):
        """Test manual close method."""
        _ = client.client  # Force initialization
        assert client._client is not None
        client.close()
        assert client._client is None


class TestPing:
    """Tests for ping method."""

    def test_ping_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test successful ping."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F&method=GET",
            status_code=200,
            json={"cluster_name": "test", "version": {"number": "8.11.0"}},
        )

        result = client.ping()
        assert result is True
        client.close()

    def test_ping_failure(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test ping failure."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F&method=GET",
            status_code=401,
            json={"error": "Unauthorized"},
        )

        result = client.ping()
        assert result is False
        client.close()


class TestSearch:
    """Tests for search method."""

    def test_search_default_query(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test search with default match_all query."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_search&method=POST",
            status_code=200,
            json={
                "took": 5,
                "hits": {
                    "total": {"value": 100, "relation": "eq"},
                    "hits": [{"_id": "1", "_source": {"message": "test"}}],
                },
            },
        )

        result = client.search()
        assert result["took"] == 5
        assert result["hits"]["total"]["value"] == 100
        client.close()

    def test_search_with_custom_query(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test search with custom query."""
        httpx_mock.add_response(
            method="POST",
            status_code=200,
            json={"took": 10, "hits": {"total": {"value": 50}, "hits": []}},
        )

        result = client.search(
            index="custom-index",
            query={"match": {"message": "error"}},
            size=20,
        )
        assert result["took"] == 10
        client.close()

    def test_search_permission_denied(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test search with permission denied error."""
        httpx_mock.add_response(
            method="POST",
            status_code=403,
            json={
                "error": {
                    "type": "security_exception",
                    "reason": "no permissions for indices:data/read/search",
                }
            },
        )

        with pytest.raises(ClientPermissionError) as exc_info:
            client.search(index="restricted-*")

        assert "Permission denied" in str(exc_info.value)
        client.close()

    def test_search_query_error(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test search with invalid query."""
        httpx_mock.add_response(
            method="POST",
            status_code=400,
            json={
                "error": {
                    "type": "parsing_exception",
                    "reason": "Unknown query [invalid_query]",
                }
            },
        )

        with pytest.raises(VDSClientError) as exc_info:
            client.search(query={"invalid_query": {}})

        assert "Query error" in str(exc_info.value)
        client.close()


class TestCount:
    """Tests for count method."""

    def test_count_default(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test count with default settings."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_count&method=POST",
            status_code=200,
            json={"count": 1500000, "_shards": {"total": 5, "successful": 5}},
        )

        result = client.count()
        assert result["count"] == 1500000
        client.close()

    def test_count_with_query(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test count with query filter."""
        httpx_mock.add_response(
            method="POST",
            status_code=200,
            json={"count": 500},
        )

        result = client.count(index="app-logs", query={"term": {"level": "ERROR"}})
        assert result["count"] == 500
        client.close()


class TestKibanaStatus:
    """Tests for kibana_status method."""

    def test_kibana_status_available(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test Kibana status check when available."""
        httpx_mock.add_response(
            method="GET",
            url="https://10.207.56.26/api/status",
            status_code=200,
            json={
                "status": {
                    "overall": {"level": "available"},
                },
            },
        )

        result = client.kibana_status()
        assert result["status"]["overall"]["level"] == "available"
        client.close()

    def test_kibana_status_error(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test Kibana status check when unavailable."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

        result = client.kibana_status()
        assert "error" in result
        client.close()


class TestUserInfo:
    """Tests for user_info method."""

    def test_user_info_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test user info retrieval."""
        httpx_mock.add_response(
            method="GET",
            url="https://10.207.56.26/internal/security/me",
            status_code=200,
            json={
                "username": "dev",
                "roles": ["viewer", "viewer-save-search"],
                "full_name": "Dev User",
            },
        )

        result = client.user_info()
        assert result["username"] == "dev"
        assert "viewer" in result["roles"]
        client.close()


class TestAdminOperations:
    """Tests for admin operations that may require monitor privilege."""

    def test_info_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test cluster info retrieval."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F&method=GET",
            status_code=200,
            json={
                "cluster_name": "production",
                "version": {"number": "8.11.0"},
            },
        )

        result = client.info()
        assert result["cluster_name"] == "production"
        client.close()

    def test_info_permission_denied(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test cluster info with permission denied."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F&method=GET",
            status_code=403,
            json={"error": {"type": "security_exception"}},
        )

        with pytest.raises(ClientPermissionError):
            client.info()
        client.close()

    def test_health_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test cluster health retrieval."""
        httpx_mock.add_response(
            method="POST",
            status_code=200,
            json={
                "status": "green",
                "number_of_nodes": 3,
                "active_primary_shards": 100,
            },
        )

        result = client.health()
        assert result["status"] == "green"
        client.close()

    def test_cat_indices_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test cat indices retrieval."""
        httpx_mock.add_response(
            method="POST",
            status_code=200,
            json=[
                {"index": "logs-2025.01.15", "health": "green", "docs.count": "1000000"},
                {"index": "logs-2025.01.16", "health": "green", "docs.count": "500000"},
            ],
        )

        result = client.cat_indices("logs-*")
        assert len(result) == 2
        assert result[0]["index"] == "logs-2025.01.15"
        client.close()


class TestErrorHandling:
    """Tests for error handling."""

    def test_auth_error_401(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test 401 error is converted to AuthError."""
        httpx_mock.add_response(
            method="POST",
            status_code=401,
            json={"error": "Unauthorized"},
        )

        with pytest.raises(AuthError) as exc_info:
            client.info()

        assert "Authentication failed" in str(exc_info.value)
        client.close()

    def test_permission_error_403(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test 403 error is converted to ClientPermissionError."""
        httpx_mock.add_response(
            method="POST",
            status_code=403,
            json={"error": {"type": "security_exception"}},
        )

        with pytest.raises(ClientPermissionError) as exc_info:
            client.health()

        assert exc_info.value.context.get("required_roles") is not None
        client.close()

    def test_response_error_500(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test 500 error is converted to ResponseError."""
        httpx_mock.add_response(
            method="POST",
            status_code=500,
            json={"error": "Internal server error"},
        )

        with pytest.raises(ResponseError) as exc_info:
            client.info()

        assert exc_info.value.context["status_code"] == 500
        client.close()

    def test_timeout_error(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test timeout is converted to ClientTimeoutError."""
        httpx_mock.add_exception(httpx.ReadTimeout("Read timed out"))

        with pytest.raises(ClientTimeoutError):
            client.info()
        client.close()

    def test_connection_error(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test connection error is converted to TransportError."""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

        with pytest.raises(TransportError):
            client.info()
        client.close()


class TestGetMapping:
    """Tests for get_mapping method."""

    def test_get_mapping_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test index mapping retrieval."""
        httpx_mock.add_response(
            method="POST",
            status_code=200,
            json={
                "logs-2025.01.15": {
                    "mappings": {
                        "properties": {
                            "message": {"type": "text"},
                            "@timestamp": {"type": "date"},
                        }
                    }
                }
            },
        )

        result = client.get_mapping("logs-2025.01.15")
        assert "logs-2025.01.15" in result
        assert "mappings" in result["logs-2025.01.15"]
        client.close()


class TestGetDocument:
    """Tests for get_document method."""

    def test_get_document_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test single document retrieval by ID."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-2025.01.15%2F_doc%2Fdoc123&method=GET",
            status_code=200,
            json={
                "_index": "logs-2025.01.15",
                "_id": "doc123",
                "_version": 1,
                "found": True,
                "_source": {
                    "message": "Test log message",
                    "@timestamp": "2025-01-15T10:00:00Z",
                },
            },
        )

        result = client.get_document("logs-2025.01.15", "doc123")
        assert result["_id"] == "doc123"
        assert result["found"] is True
        assert result["_source"]["message"] == "Test log message"
        client.close()

    def test_get_document_with_source_filter(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test document retrieval with source field filter."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs%2F_doc%2Fdoc456%3F_source%3Dmessage%2Clevel&method=GET",
            status_code=200,
            json={
                "_index": "logs",
                "_id": "doc456",
                "found": True,
                "_source": {"message": "Test", "level": "INFO"},
            },
        )

        result = client.get_document("logs", "doc456", source=["message", "level"])
        assert result["found"] is True
        assert "message" in result["_source"]
        client.close()

    def test_get_document_not_found(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test document retrieval when not found."""
        httpx_mock.add_response(
            method="POST",
            status_code=200,  # Kibana proxy returns 200, ES error in body
            json={
                "_index": "logs",
                "_id": "missing",
                "found": False,
            },
        )

        result = client.get_document("logs", "missing")
        assert result["found"] is False
        client.close()


class TestMget:
    """Tests for mget (multi-get) method."""

    def test_mget_with_ids(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test multi-get with simple ID list."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs%2F_mget&method=POST",
            status_code=200,
            json={
                "docs": [
                    {"_index": "logs", "_id": "doc1", "found": True, "_source": {"msg": "one"}},
                    {"_index": "logs", "_id": "doc2", "found": True, "_source": {"msg": "two"}},
                ]
            },
        )

        result = client.mget(index="logs", ids=["doc1", "doc2"])
        assert len(result["docs"]) == 2
        assert result["docs"][0]["_id"] == "doc1"
        assert result["docs"][1]["_id"] == "doc2"
        client.close()

    def test_mget_with_docs(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test multi-get with full doc specifications."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_mget&method=POST",
            status_code=200,
            json={
                "docs": [
                    {"_index": "logs", "_id": "doc1", "found": True},
                    {"_index": "metrics", "_id": "doc2", "found": False},
                ]
            },
        )

        result = client.mget(
            docs=[
                {"_index": "logs", "_id": "doc1"},
                {"_index": "metrics", "_id": "doc2"},
            ]
        )
        assert len(result["docs"]) == 2
        assert result["docs"][0]["found"] is True
        assert result["docs"][1]["found"] is False
        client.close()

    def test_mget_requires_ids_or_docs(self, client: KibanaElasticsearchClient):
        """Test that mget raises error without ids or docs."""
        with pytest.raises(ValueError, match="Either 'ids' or 'docs' must be provided"):
            client.mget(index="logs")
        client.close()


class TestFieldCaps:
    """Tests for field_caps method."""

    def test_field_caps_default(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test field capabilities with defaults."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F%2A%2F_field_caps&method=POST",
            status_code=200,
            json={
                "indices": ["logs-2025.01.15", "logs-2025.01.16"],
                "fields": {
                    "message": {
                        "text": {"type": "text", "searchable": True, "aggregatable": False}
                    },
                    "@timestamp": {
                        "date": {"type": "date", "searchable": True, "aggregatable": True}
                    },
                },
            },
        )

        result = client.field_caps()
        assert "fields" in result
        assert "message" in result["fields"]
        assert "@timestamp" in result["fields"]
        client.close()

    def test_field_caps_with_specific_fields(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test field capabilities with specific field list."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_field_caps&method=POST",
            status_code=200,
            json={
                "indices": ["logs-2025.01.15"],
                "fields": {
                    "level": {
                        "keyword": {"type": "keyword", "searchable": True, "aggregatable": True}
                    },
                },
            },
        )

        result = client.field_caps(index="logs-*", fields=["level"])
        assert "level" in result["fields"]
        client.close()


class TestMsearch:
    """Tests for msearch (multi-search) method."""

    def test_msearch_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test multi-search with multiple queries."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_msearch&method=POST",
            status_code=200,
            json={
                "responses": [
                    {
                        "hits": {
                            "total": {"value": 100, "relation": "eq"},
                            "hits": [{"_id": "1"}],
                        }
                    },
                    {
                        "hits": {
                            "total": {"value": 50, "relation": "eq"},
                            "hits": [{"_id": "2"}],
                        }
                    },
                ]
            },
        )

        result = client.msearch(
            [
                ({"index": "logs-*"}, {"query": {"match": {"level": "ERROR"}}}),
                ({"index": "metrics-*"}, {"query": {"range": {"value": {"gt": 100}}}}),
            ]
        )
        assert len(result["responses"]) == 2
        assert result["responses"][0]["hits"]["total"]["value"] == 100
        assert result["responses"][1]["hits"]["total"]["value"] == 50
        client.close()

    def test_msearch_with_default_index(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test multi-search with default index."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_msearch&method=POST",
            status_code=200,
            json={
                "responses": [
                    {"hits": {"total": {"value": 10}, "hits": []}},
                ]
            },
        )

        result = client.msearch(
            [({}, {"query": {"match_all": {}}})],
            index="logs-*",
        )
        assert len(result["responses"]) == 1
        client.close()


class TestSearchAfter:
    """Tests for search_after pagination."""

    def test_search_with_search_after(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test search with search_after for deep pagination."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_search&method=POST",
            status_code=200,
            json={
                "hits": {
                    "total": {"value": 100, "relation": "eq"},
                    "hits": [
                        {"_id": "doc2", "sort": [1705401600000, "doc2"]},
                    ],
                }
            },
        )

        result = client.search(
            index="logs-*",
            size=10,
            sort=[{"@timestamp": "asc"}, {"_id": "asc"}],
            search_after=[1705315200000, "doc1"],
        )
        assert "hits" in result
        client.close()

    def test_search_after_requires_sort(self, client: KibanaElasticsearchClient):
        """Test that search_after raises error without sort."""
        with pytest.raises(ValueError, match="search_after requires a 'sort' parameter"):
            client.search(
                index="logs-*",
                search_after=[1705315200000, "doc1"],
            )
        client.close()


class TestScrollApi:
    """Tests for scroll API methods."""

    def test_scroll_search_starts_scroll(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test initiating a scroll search."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_search%3Fscroll%3D5m&method=POST",
            status_code=200,
            json={
                "_scroll_id": "DXF1ZXJ5QW5kRmV0Y2g=",
                "hits": {
                    "total": {"value": 1000, "relation": "eq"},
                    "hits": [{"_id": "doc1", "_source": {"msg": "test"}}],
                },
            },
        )

        result = client.scroll_search(index="logs-*", size=100)
        assert "_scroll_id" in result
        assert result["_scroll_id"] == "DXF1ZXJ5QW5kRmV0Y2g="
        assert len(result["hits"]["hits"]) == 1
        client.close()

    def test_scroll_continues_pagination(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test continuing a scroll."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_search%2Fscroll&method=POST",
            status_code=200,
            json={
                "_scroll_id": "DXF1ZXJ5QW5kRmV0Y2g=_v2",
                "hits": {
                    "total": {"value": 1000, "relation": "eq"},
                    "hits": [{"_id": "doc101", "_source": {"msg": "test"}}],
                },
            },
        )

        result = client.scroll("DXF1ZXJ5QW5kRmV0Y2g=")
        assert "_scroll_id" in result
        assert len(result["hits"]["hits"]) == 1
        client.close()

    def test_clear_scroll_single_id(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test clearing a single scroll context."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_search%2Fscroll&method=DELETE",
            status_code=200,
            json={"succeeded": True, "num_freed": 1},
        )

        result = client.clear_scroll("DXF1ZXJ5QW5kRmV0Y2g=")
        assert result["succeeded"] is True
        client.close()

    def test_clear_scroll_multiple_ids(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test clearing multiple scroll contexts."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_search%2Fscroll&method=DELETE",
            status_code=200,
            json={"succeeded": True, "num_freed": 3},
        )

        result = client.clear_scroll(["scroll1", "scroll2", "scroll3"])
        assert result["num_freed"] == 3
        client.close()


class TestScan:
    """Tests for the scan helper generator."""

    def test_scan_yields_all_documents(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test that scan yields all documents across batches."""
        # First batch
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_search%3Fscroll%3D5m&method=POST",
            status_code=200,
            json={
                "_scroll_id": "scroll_1",
                "hits": {
                    "total": {"value": 3, "relation": "eq"},
                    "hits": [
                        {"_id": "doc1", "_source": {"n": 1}},
                        {"_id": "doc2", "_source": {"n": 2}},
                    ],
                },
            },
        )
        # Second batch
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_search%2Fscroll&method=POST",
            status_code=200,
            json={
                "_scroll_id": "scroll_2",
                "hits": {
                    "total": {"value": 3, "relation": "eq"},
                    "hits": [{"_id": "doc3", "_source": {"n": 3}}],
                },
            },
        )
        # Third batch (empty - terminates)
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_search%2Fscroll&method=POST",
            status_code=200,
            json={
                "_scroll_id": "scroll_3",
                "hits": {"total": {"value": 3, "relation": "eq"}, "hits": []},
            },
        )
        # Cleanup
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_search%2Fscroll&method=DELETE",
            status_code=200,
            json={"succeeded": True, "num_freed": 1},
        )

        docs = list(client.scan(index="logs-*", size=2))
        assert len(docs) == 3
        assert docs[0]["_id"] == "doc1"
        assert docs[1]["_id"] == "doc2"
        assert docs[2]["_id"] == "doc3"
        client.close()

    def test_scan_cleans_up_on_early_exit(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test that scan clears scroll context even on early exit."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2Flogs-%2A%2F_search%3Fscroll%3D5m&method=POST",
            status_code=200,
            json={
                "_scroll_id": "scroll_1",
                "hits": {
                    "total": {"value": 100, "relation": "eq"},
                    "hits": [
                        {"_id": "doc1", "_source": {"n": 1}},
                        {"_id": "doc2", "_source": {"n": 2}},
                    ],
                },
            },
        )
        # Cleanup should still be called
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_search%2Fscroll&method=DELETE",
            status_code=200,
            json={"succeeded": True, "num_freed": 1},
        )

        # Only get first doc then break
        for doc in client.scan(index="logs-*"):
            assert doc["_id"] == "doc1"
            break

        client.close()


class TestCatAliases:
    """Tests for cat_aliases method."""

    def test_cat_aliases_success(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test listing aliases successfully."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_cat%2Faliases%2F%2A%3Fformat%3Djson&method=GET",
            status_code=200,
            json=[
                {
                    "alias": "logs",
                    "index": "logs-2025.01",
                    "filter": "-",
                    "routing.index": "-",
                    "routing.search": "-",
                },
                {
                    "alias": "metrics",
                    "index": "metrics-2025.01",
                    "filter": "-",
                    "routing.index": "-",
                    "routing.search": "-",
                },
            ],
        )

        result = client.cat_aliases()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["alias"] == "logs"
        assert result[1]["alias"] == "metrics"
        client.close()

    def test_cat_aliases_with_pattern(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test listing aliases with a pattern filter."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_cat%2Faliases%2Flogs%2A%3Fformat%3Djson&method=GET",
            status_code=200,
            json=[
                {
                    "alias": "logs",
                    "index": "logs-2025.01",
                    "filter": "-",
                    "routing.index": "-",
                    "routing.search": "-",
                },
            ],
        )

        result = client.cat_aliases(pattern="logs*")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["alias"] == "logs"
        client.close()

    def test_cat_aliases_permission_denied(self, client: KibanaElasticsearchClient, httpx_mock):
        """Test cat_aliases returns 403 for viewer role."""
        httpx_mock.add_response(
            method="POST",
            url="https://10.207.56.26/api/console/proxy?path=%2F_cat%2Faliases%2F%2A%3Fformat%3Djson&method=GET",
            status_code=200,
            json={
                "error": {
                    "root_cause": [
                        {
                            "type": "security_exception",
                            "reason": "action [cluster:monitor/aliases] is unauthorized",
                        }
                    ],
                    "type": "security_exception",
                    "reason": "action [cluster:monitor/aliases] is unauthorized",
                },
                "status": 403,
            },
        )

        with pytest.raises(ClientPermissionError):
            client.cat_aliases()
        client.close()
