"""Tests for Confluence cache management (Server-only)."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from confluence_orchestrator.cli import app
from confluence_orchestrator.errors import VDSClientError
from confluence_orchestrator.http import ConfluenceClient
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_settings():
    """Mock Confluence settings."""
    settings = MagicMock()
    settings.url_for.return_value = "http://confluence.digital.vn"
    settings.token_for.return_value = "test-token"
    settings.username = None
    settings.password = None
    settings.max_retries = 3
    settings.retry_backoff_factor = 0.5
    settings.default_server = "internal"
    settings.internal_token = "test-token"
    settings.external_token = None
    return settings


@pytest.fixture
def mock_sdk_client():
    """Mock SDK client."""
    client = MagicMock()
    client.clean_all_caches.return_value = None
    client.clean_package_cache.return_value = None
    client.request.return_value = MagicMock(json=lambda: {"stats": "data"})
    return client


@pytest.fixture
def server_client(mock_settings, mock_sdk_client):
    """Create ConfluenceClient in Server mode."""
    with patch("confluence_orchestrator.http.AtlassianConfluenceServer", return_value=mock_sdk_client):
        client = ConfluenceClient(mock_settings, server="internal")
        client._is_cloud = False
        return client


@pytest.fixture
def cloud_client(mock_settings, mock_sdk_client):
    """Create ConfluenceClient in Cloud mode."""
    with patch("confluence_orchestrator.http.AtlassianConfluenceCloud", return_value=mock_sdk_client):
        client = ConfluenceClient(mock_settings, server="internal")
        client._is_cloud = True
        return client


class TestGetCacheStatistics:
    """Tests for get_cache_statistics method."""

    def test_get_cache_statistics_success(self, server_client, mock_sdk_client):
        """Test successful cache statistics retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"cache_stats": {"hits": 100, "misses": 50}}
        mock_sdk_client.request.return_value = mock_response

        result = server_client.get_cache_statistics()

        assert result == {"cache_stats": {"hits": 100, "misses": 50}}
        mock_sdk_client.request.assert_called_once_with(method="GET", path="/rest/cache/1.0/stats")

    def test_get_cache_statistics_cloud_mode_error(self, cloud_client):
        """Test that get_cache_statistics raises error in Cloud mode."""
        with pytest.raises(VDSClientError, match="only available in Confluence Server"):
            cloud_client.get_cache_statistics()

    def test_get_cache_statistics_handles_response_dict(self, server_client, mock_sdk_client):
        """Test handling when request returns dict directly."""
        mock_sdk_client.request.return_value = {"cache_stats": {"hits": 100}}

        result = server_client.get_cache_statistics()

        assert result == {"cache_stats": {"hits": 100}}


class TestFlushCache:
    """Tests for flush_cache method."""

    def test_flush_cache_all_success(self, server_client, mock_sdk_client):
        """Test successful flush of all caches."""
        server_client.flush_cache()

        mock_sdk_client.clean_all_caches.assert_called_once()

    def test_flush_cache_specific_success(self, server_client, mock_sdk_client):
        """Test successful flush of specific cache."""
        server_client.flush_cache(cache_name="com.gliffy.cache.gon")

        mock_sdk_client.clean_package_cache.assert_called_once_with(cache_name="com.gliffy.cache.gon")

    def test_flush_cache_cloud_mode_error(self, cloud_client):
        """Test that flush_cache raises error in Cloud mode."""
        with pytest.raises(VDSClientError, match="only available in Confluence Server"):
            cloud_client.flush_cache()

    def test_flush_cache_specific_cloud_mode_error(self, cloud_client):
        """Test that flush_cache with cache_name raises error in Cloud mode."""
        with pytest.raises(VDSClientError, match="only available in Confluence Server"):
            cloud_client.flush_cache(cache_name="test-cache")


class TestGetCacheSize:
    """Tests for get_cache_size method."""

    def test_get_cache_size_success(self, server_client, mock_sdk_client):
        """Test successful cache size retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"total_size": "100MB", "cache_count": 10}
        mock_sdk_client.request.return_value = mock_response

        result = server_client.get_cache_size()

        assert result == {"total_size": "100MB", "cache_count": 10}
        mock_sdk_client.request.assert_called_once_with(method="GET", path="/rest/cache/1.0/size")

    def test_get_cache_size_cloud_mode_error(self, cloud_client):
        """Test that get_cache_size raises error in Cloud mode."""
        with pytest.raises(VDSClientError, match="only available in Confluence Server"):
            cloud_client.get_cache_size()

    def test_get_cache_size_handles_response_dict(self, server_client, mock_sdk_client):
        """Test handling when request returns dict directly."""
        mock_sdk_client.request.return_value = {"total_size": "50MB"}

        result = server_client.get_cache_size()

        assert result == {"total_size": "50MB"}


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummyCacheClient:
    def __init__(self, cloud: bool = False) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._is_cloud = cloud  # type: ignore[attr-defined]

    def get_cache_statistics(self) -> dict[str, Any]:
        if self._is_cloud:
            raise VDSClientError("Server-only feature")
        self.calls.append(("get_cache_statistics", (), {}))
        return {"cache_stats": {"hits": 100, "misses": 50}}

    def flush_cache(self, cache_name: str | None = None) -> None:
        if self._is_cloud:
            raise VDSClientError("Server-only feature")
        self.calls.append(("flush_cache", (cache_name,), {}))

    def get_cache_size(self) -> dict[str, Any]:
        if self._is_cloud:
            raise VDSClientError("Server-only feature")
        self.calls.append(("get_cache_size", (), {}))
        return {"total_size": "100MB", "cache_count": 10}


def test_cli_cache_statistics_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyCacheClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["cache", "statistics"])

    assert result.exit_code == 0
    assert "cache_statistics" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_cache_statistics"


def test_cli_cache_flush_all_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyCacheClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["cache", "flush", "--yes"])

    assert result.exit_code == 0
    assert "success" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "flush_cache"
    assert client.calls[0][1][0] is None  # cache_name is None


def test_cli_cache_flush_specific_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyCacheClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["cache", "flush", "--cache-name", "com.gliffy.cache", "--yes"])

    assert result.exit_code == 0
    assert "success" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "flush_cache"
    assert client.calls[0][1][0] == "com.gliffy.cache"


def test_cli_cache_flush_requires_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyCacheClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["cache", "flush"])

    assert result.exit_code != 0
    assert "--yes" in result.stdout or "--yes" in result.stderr or "without --yes" in result.stdout


def test_cli_cache_size_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyCacheClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["cache", "size"])

    assert result.exit_code == 0
    assert "cache_size" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_cache_size"


def test_cli_cache_cloud_mode_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyCacheClient(cloud=True)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["cache", "statistics"])

    assert result.exit_code != 0
    assert "Server-only" in result.stderr or "Server-only" in result.stdout


def test_cli_cache_invalid_action(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyCacheClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["cache", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
