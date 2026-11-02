"""Tests for Confluence advanced CQL search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from confluence_orchestrator.cli import app
from confluence_orchestrator.config import ConfluenceSettings
from confluence_orchestrator.errors import VDSClientError
from confluence_orchestrator.http import ConfluenceClient
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_settings() -> ConfluenceSettings:
    """Mock ConfluenceSettings."""
    return ConfluenceSettings.model_validate(
        {
            "VDS_USERNAME": "test_user",
            "VDS_PASSWORD": "test_pass",
            "INTERNAL_CONFLUENCE_TOKEN": "token-int",
            "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
            "INTERNAL_CONFLUENCE_URL": "http://internal.confluence.com",
            "EXTERNAL_CONFLUENCE_URL": "http://external.confluence.com",
        }
    )


@pytest.fixture
def mock_sdk_client() -> MagicMock:
    """Mock the underlying AtlassianConfluenceServer client."""
    with patch("confluence_orchestrator.http.AtlassianConfluenceServer") as mock:
        yield mock.return_value


@pytest.fixture
def server_client(mock_settings: ConfluenceSettings, mock_sdk_client: MagicMock) -> ConfluenceClient:
    """Return a ConfluenceClient configured for server mode."""
    client = ConfluenceClient(mock_settings, server="internal")
    client._client = mock_sdk_client
    client._is_cloud = False
    client._with_retry = lambda operation, _: operation()
    return client


class TestCqlAdvanced:
    """Tests for cql_advanced method."""

    def test_cql_advanced_success(self, server_client: ConfluenceClient, mock_sdk_client: MagicMock) -> None:
        """Test successful advanced CQL search."""
        mock_sdk_client.get.return_value = {"results": [{"id": "123", "title": "Test Page"}], "size": 1}

        result = server_client.cql_advanced("type = page", limit=50, start=10, excerpt="highlighted")

        assert result["size"] == 1
        mock_sdk_client.get.assert_called_once()
        call_args = mock_sdk_client.get.call_args
        assert call_args[0][0] == "rest/api/search"
        params = call_args[1]["params"]
        assert params["limit"] == 50
        assert params["start"] == 10
        assert params["excerpt"] == "highlighted"

    def test_cql_advanced_with_expand(self, server_client: ConfluenceClient, mock_sdk_client: MagicMock) -> None:
        """Test advanced CQL search with expand option."""
        mock_sdk_client.get.return_value = {"results": [], "size": 0}

        server_client.cql_advanced("type = page", expand=["body.storage", "space"])

        params = mock_sdk_client.get.call_args[1]["params"]
        assert params["expand"] == "body.storage,space"

    def test_cql_advanced_defaults(self, server_client: ConfluenceClient, mock_sdk_client: MagicMock) -> None:
        """Test advanced CQL search with default parameters."""
        mock_sdk_client.get.return_value = {"results": [], "size": 0}

        server_client.cql_advanced("type = page")

        params = mock_sdk_client.get.call_args[1]["params"]
        assert params["limit"] == 25
        assert params["start"] == 0
        assert "excerpt" not in params


class TestSearchBySpaceAndType:
    """Tests for search_by_space_and_type method."""

    def test_search_by_space_and_type_space_only(
        self, server_client: ConfluenceClient, mock_sdk_client: MagicMock
    ) -> None:
        """Test search by space only."""
        mock_sdk_client.get.return_value = {"results": [], "size": 0}

        server_client.search_by_space_and_type(space_key="TEST")

        params = mock_sdk_client.get.call_args[1]["params"]
        assert 'space = "TEST"' in params["cql"]

    def test_search_by_space_and_type_type_only(
        self, server_client: ConfluenceClient, mock_sdk_client: MagicMock
    ) -> None:
        """Test search by content type only."""
        mock_sdk_client.get.return_value = {"results": [], "size": 0}

        server_client.search_by_space_and_type(content_type="page")

        params = mock_sdk_client.get.call_args[1]["params"]
        assert 'type = "page"' in params["cql"]

    def test_search_by_space_and_type_both(self, server_client: ConfluenceClient, mock_sdk_client: MagicMock) -> None:
        """Test search by both space and type."""
        mock_sdk_client.get.return_value = {"results": [], "size": 0}

        server_client.search_by_space_and_type(space_key="TEST", content_type="page")

        params = mock_sdk_client.get.call_args[1]["params"]
        assert 'space = "TEST"' in params["cql"]
        assert 'type = "page"' in params["cql"]
        assert " AND " in params["cql"]

    def test_search_by_space_and_type_requires_at_least_one(self, server_client: ConfluenceClient) -> None:
        """Test that search_by_space_and_type requires at least one parameter."""
        with pytest.raises(VDSClientError, match="At least one of space_key, content_type, or last_modified_after"):
            server_client.search_by_space_and_type()


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


class DummySearchClient:
    def __init__(self, cloud: bool = False) -> None:
        self.calls: list = []
        self._is_cloud = cloud  # type: ignore[attr-defined]

    def search_cql(self, cql: str, **kwargs: any) -> dict:
        self.calls.append(("search_cql", cql, kwargs))
        return {"results": [], "size": 0}

    def cql_advanced(self, cql: str, **kwargs: any) -> dict:
        self.calls.append(("cql_advanced", cql, kwargs))
        return {"results": [], "size": 0}

    def search_by_space_and_type(self, **kwargs: any) -> dict:
        self.calls.append(("search_by_space_and_type", kwargs))
        return {"results": [], "size": 0}


def test_cli_search_advanced_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test search command with --advanced flag."""
    client = DummySearchClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_content_client", lambda *args: client)

    result = runner.invoke(app, ["search", "--cql", "type = page", "--advanced", "--excerpt", "highlighted"])

    assert result.exit_code == 0
    assert len(client.calls) == 1
    assert client.calls[0][0] == "cql_advanced"
    assert client.calls[0][2].get("excerpt") == "highlighted"


def test_cli_search_by_space_type_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test search-by-space-type command success."""
    client = DummySearchClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_content_client", lambda *args: client)

    result = runner.invoke(app, ["search-by-space-type", "--space", "TEST", "--type", "page"])

    assert result.exit_code == 0
    assert len(client.calls) == 1
    assert client.calls[0][0] == "search_by_space_and_type"


def test_cli_search_by_space_type_requires_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test search-by-space-type command requires at least one parameter."""
    client = DummySearchClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_content_client", lambda *args: client)

    result = runner.invoke(app, ["search-by-space-type"])

    assert result.exit_code != 0
    assert (
        "--space" in result.stdout
        or "--type" in result.stdout
        or "At least one" in result.stdout
        or "--space" in result.stderr
        or "--type" in result.stderr
        or "At least one" in result.stderr
    )
