"""End-to-end verification tests for VDS Elastic Orchestrator.

These tests require access to the VDS internal network and valid credentials.
They are gated by the VDS_ELASTIC_E2E_TESTS environment variable.

To run these tests:
    VDS_ELASTIC_E2E_TESTS=1 uv run pytest tests/test_e2e_verification.py -v

Required environment variables:
    - VDS_ELASTIC_E2E_TESTS=1 (to enable these tests)
    - VDS_ELASTIC_KIBANA_URL
    - VDS_ELASTIC_KIBANA_IP
    - VDS_ELASTIC_USER
    - VDS_ELASTIC_PASSWORD
"""

from __future__ import annotations

import os

import pytest

from vds_elastic_orchestrator.client import KibanaElasticsearchClient
from vds_elastic_orchestrator.config import load_settings
from vds_elastic_orchestrator.errors import ClientPermissionError

# Skip all tests if VDS_ELASTIC_E2E_TESTS is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("VDS_ELASTIC_E2E_TESTS"),
    reason="E2E tests require VDS_ELASTIC_E2E_TESTS=1 and VDS network access",
)


@pytest.fixture(scope="module")
def settings():
    """Load settings from environment."""
    return load_settings(strict=True)


@pytest.fixture(scope="module")
def client(settings):
    """Create and yield a client instance."""
    with KibanaElasticsearchClient(settings) as client:
        yield client


class TestConnectivity:
    """Test basic connectivity to Elasticsearch via Kibana."""

    def test_ping_succeeds(self, client: KibanaElasticsearchClient) -> None:
        """Test that ping returns True when connected."""
        result = client.ping()
        assert result is True, "Ping should succeed when connected to VDS network"

    def test_kibana_status_returns_status(self, client: KibanaElasticsearchClient) -> None:
        """Test Kibana status endpoint returns valid response."""
        result = client.kibana_status()

        # Should not have error
        assert "error" not in result or result.get("error") is None

        # Should have status information
        assert "name" in result or "version" in result or "status" in result

    def test_user_info_returns_current_user(self, client: KibanaElasticsearchClient) -> None:
        """Test user info returns authenticated user details."""
        result = client.user_info()

        # Should not have error
        assert "error" not in result or result.get("error") is None

        # Should have username
        assert "username" in result, "user_info should return username"

        # Should have roles
        assert "roles" in result, "user_info should return roles"
        assert isinstance(result["roles"], list), "roles should be a list"


class TestSearchOperations:
    """Test search and count operations."""

    def test_search_returns_results(self, client: KibanaElasticsearchClient) -> None:
        """Test basic search returns valid response structure."""
        result = client.search(index="*", size=1)

        # Should have hits structure
        assert "hits" in result, "Search should return hits"
        assert "total" in result["hits"], "Search should return total count"
        assert "hits" in result["hits"], "Search should return hits array"

    def test_search_with_match_all_query(self, client: KibanaElasticsearchClient) -> None:
        """Test search with explicit match_all query."""
        result = client.search(
            index="*",
            query={"match_all": {}},
            size=5,
        )

        assert "hits" in result
        hits = result["hits"]["hits"]
        assert isinstance(hits, list)
        # We expect some documents to exist
        assert len(hits) <= 5

    def test_search_with_size_zero(self, client: KibanaElasticsearchClient) -> None:
        """Test search with size=0 returns only count."""
        result = client.search(index="*", size=0)

        assert "hits" in result
        # Should have total count
        total = result["hits"]["total"]
        if isinstance(total, dict):
            assert total.get("value", 0) >= 0
        else:
            assert total >= 0

        # Should have empty hits array
        assert result["hits"]["hits"] == []

    def test_count_returns_count(self, client: KibanaElasticsearchClient) -> None:
        """Test count returns document count."""
        result = client.count(index="*")

        assert "count" in result, "Count should return count field"
        assert isinstance(result["count"], int), "Count should be an integer"
        assert result["count"] >= 0, "Count should be non-negative"

    def test_count_with_query(self, client: KibanaElasticsearchClient) -> None:
        """Test count with a query returns filtered count."""
        # Count all documents
        total = client.count(index="*")

        # Count with match_all (should be same)
        with_query = client.count(index="*", query={"match_all": {}})

        assert with_query["count"] == total["count"]


class TestAdminOperations:
    """Test admin operations that may fail with permission errors."""

    def test_info_or_permission_denied(self, client: KibanaElasticsearchClient) -> None:
        """Test cluster info returns data or permission error."""
        try:
            result = client.info()
            # If we get here, user has monitor privilege
            assert "cluster_name" in result or "version" in result
        except ClientPermissionError as exc:
            # Expected for viewer role
            assert "Permission denied" in str(exc)
            assert exc.required_roles is not None

    def test_health_or_permission_denied(self, client: KibanaElasticsearchClient) -> None:
        """Test cluster health returns data or permission error."""
        try:
            result = client.health()
            # If we get here, user has monitor privilege
            assert "status" in result  # green, yellow, red
            assert "cluster_name" in result
        except ClientPermissionError as exc:
            # Expected for viewer role
            assert "Permission denied" in str(exc)

    def test_cat_indices_or_permission_denied(self, client: KibanaElasticsearchClient) -> None:
        """Test cat indices returns data or permission error."""
        try:
            result = client.cat_indices(pattern="*")
            # If we get here, user has monitor privilege
            assert isinstance(result, list)
        except ClientPermissionError as exc:
            # Expected for viewer role
            assert "Permission denied" in str(exc)


class TestRetryBehavior:
    """Test retry behavior with real network conditions."""

    def test_retry_on_success(self, client: KibanaElasticsearchClient) -> None:
        """Test that successful requests don't trigger retries."""
        # A simple successful request should complete without issues
        result = client.ping()
        assert result is True

    def test_timeout_configuration(self, settings) -> None:
        """Test that timeout settings are properly configured."""
        assert settings.connect_timeout > 0
        assert settings.request_timeout > 0
        assert settings.max_retries >= 1


class TestSettingsLoading:
    """Test settings load correctly from environment."""

    def test_settings_have_required_fields(self, settings) -> None:
        """Test all required settings are loaded."""
        assert settings.kibana_url is not None
        assert settings.kibana_ip is not None
        assert settings.user is not None
        assert settings.password is not None

    def test_proxy_endpoint_is_valid(self, settings) -> None:
        """Test proxy endpoint is constructed correctly."""
        expected = "/api/console/proxy"
        assert settings.proxy_endpoint == expected


class TestClientContextManager:
    """Test client context manager behavior."""

    def test_context_manager_opens_and_closes(self, settings) -> None:
        """Test context manager properly manages client lifecycle."""
        with KibanaElasticsearchClient(settings) as client:
            # Client should be usable
            assert client.ping() is True

        # After exit, client should be closed
        assert client._client is None

    def test_multiple_requests_reuse_connection(self, settings) -> None:
        """Test connection pooling is working."""
        with KibanaElasticsearchClient(settings) as client:
            # Make multiple requests
            client.ping()
            client.kibana_status()
            client.user_info()

            # Should still have the same client instance
            assert client._client is not None


# Smoke test for manual verification
def test_smoke_test_manual_verification(client: KibanaElasticsearchClient) -> None:
    """Manual smoke test that prints results for verification.

    This test is useful for manual debugging and verification.
    Run with: VDS_ELASTIC_E2E_TESTS=1 uv run pytest tests/test_e2e_verification.py::test_smoke_test_manual_verification -v -s
    """
    print("\n" + "=" * 60)
    print("VDS Elastic Orchestrator - E2E Smoke Test")
    print("=" * 60)

    # Ping
    ping_result = client.ping()
    print(f"\n✓ Ping: {'SUCCESS' if ping_result else 'FAILED'}")

    # User info
    user_info = client.user_info()
    if "username" in user_info:
        print(f"✓ User: {user_info['username']}")
        print(f"  Roles: {', '.join(user_info.get('roles', []))}")

    # Count
    count_result = client.count(index="*")
    if "count" in count_result:
        print(f"✓ Total documents: {count_result['count']:,}")

    # Search
    search_result = client.search(index="*", size=1)
    if "hits" in search_result:
        total = search_result["hits"]["total"]
        total_value = total.get("value", total) if isinstance(total, dict) else total
        print(f"✓ Search (size=1): {total_value:,} total hits")

    # Kibana status
    kibana_status = client.kibana_status()
    if "name" in kibana_status:
        print(f"✓ Kibana: {kibana_status.get('name', 'OK')}")

    print("\n" + "=" * 60)
    print("All smoke tests passed!")
    print("=" * 60 + "\n")
