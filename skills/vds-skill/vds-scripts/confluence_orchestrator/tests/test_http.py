from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from confluence_orchestrator.config import ConfluenceSettings
from confluence_orchestrator.errors import (
    AuthError,
    ConflictError,
    VDSClientError,
)
from confluence_orchestrator.http import (
    ConfluenceClient,
    ConfluenceHttpClient,
    _build_lastmodified_cql_clause,
    _build_space_type_lastmodified_cql,
)


@pytest.fixture()
def base_settings() -> ConfluenceSettings:
    return ConfluenceSettings.model_validate(
        {
            "VDS_USERNAME": "user",
            "VDS_PASSWORD": "pass",
            "INTERNAL_CONFLUENCE_TOKEN": "token-int",
            "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
        }
    )


def make_client(settings: ConfluenceSettings, handler: httpx.MockTransport) -> ConfluenceHttpClient:
    client = httpx.Client(
        base_url=str(settings.internal_url),
        transport=handler,
        headers={"Authorization": "Bearer token-int", "Accept": "application/json"},
    )
    return ConfluenceHttpClient(settings, client=client)


def test_successful_request(monkeypatch: pytest.MonkeyPatch, base_settings: ConfluenceSettings) -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(200, json={"ok": True})

    client = make_client(base_settings, httpx.MockTransport(handler))
    response = client.request("GET", "/rest/api/content/123")
    assert response.status_code == 200
    assert attempts["count"] == 1


def test_conflict_raises(base_settings: ConfluenceSettings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409)

    client = make_client(base_settings, httpx.MockTransport(handler))

    with pytest.raises(ConflictError):
        client.request("POST", "/rest/api/content/123")


def test_missing_token_raises(base_settings: ConfluenceSettings) -> None:
    stripped_settings = base_settings.model_copy(update={"internal_token": None})
    with pytest.raises(AuthError):
        ConfluenceHttpClient(stripped_settings)


def _make_stub_confluence_client() -> ConfluenceClient:
    client = ConfluenceClient.__new__(ConfluenceClient)
    client._log = MagicMock()
    client._client = MagicMock()
    client._settings = MagicMock()
    client._server = "internal"
    client._max_retries = 0
    client._retry_backoff_factor = 0.0
    client._retry_max_wait = 30.0
    client._degraded = False
    return client


def test_probe_reachable_uses_search_cql_with_explicit_start() -> None:
    client = _make_stub_confluence_client()
    calls: list[tuple[str, int, int]] = []

    def fake_search_cql(
        cql: str, limit: int = 25, start: int = 0, expand: list[str] | None = None, **kwargs: object
    ) -> dict[str, object]:
        calls.append((cql, limit, start))
        return {"results": [], "start": start, "limit": limit}

    client.search_cql = fake_search_cql  # type: ignore[method-assign]

    result = client.probe_reachable()

    assert result["start"] == 0
    assert calls == [("type=page", 1, 0)]


def test_incremental_cql_helpers_apply_overlap_buffer() -> None:
    clause = _build_lastmodified_cql_clause("2026-02-24T10:00:00Z", overlap_minutes=15)
    assert clause == 'lastmodified >= "2026-02-24 09:45"'

    cql = _build_space_type_lastmodified_cql(
        space_key="OPS",
        content_type="page",
        last_modified_after="2026-02-24T10:00:00+00:00",
        overlap_minutes=5,
    )
    assert cql == 'space = "OPS" AND type = "page" AND lastmodified >= "2026-02-24 09:55" ORDER BY lastmodified ASC'


def test_search_by_space_and_type_includes_incremental_clause() -> None:
    client = _make_stub_confluence_client()
    captured: dict[str, str] = {}

    def fake_cql_advanced(
        cql: str,
        *,
        limit: int = 25,
        start: int = 0,
        expand: list[str] | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        captured["cql"] = cql
        return {"ok": True, "limit": limit, "start": start, "expand": expand, **kwargs}

    client.cql_advanced = fake_cql_advanced  # type: ignore[method-assign]
    result = client.search_by_space_and_type(
        space_key="ENG",
        content_type="page",
        last_modified_after="2026-02-24T10:00:00Z",
        overlap_minutes=10,
        limit=10,
        start=5,
        expand=["body.storage"],
    )

    assert (
        captured["cql"]
        == 'space = "ENG" AND type = "page" AND lastmodified >= "2026-02-24 09:50" ORDER BY lastmodified ASC'
    )
    assert result["ok"] is True


def test_delete_attachment_all_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_stub_confluence_client()
    client._client.get_attachment_history.return_value = [{"number": 1}, {"number": 2}]
    client._client.get_attachments.return_value = {"results": [{"id": "att-1", "title": "file.pdf"}]}

    client.delete_attachment_by_id("123", "att-1")

    client._client.delete_attachment_by_id.assert_any_call("att-1", 2)
    client._client.delete_attachment_by_id.assert_any_call("att-1", 1)
    assert client._client.delete_attachment_by_id.call_count == 2


def test_delete_attachment_specific_version(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_stub_confluence_client()
    client._client.get_attachment_history.return_value = [{"number": 1}, {"number": 2}]

    client.delete_attachment_by_id("123", "att-1", version=1)

    client._client.delete_attachment_by_id.assert_called_once_with("att-1", 1)


def test_delete_attachment_requires_version_when_history_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_stub_confluence_client()
    client._client.get_attachment_history.return_value = []
    client._client.get_attachments.return_value = {"results": []}

    with pytest.raises(VDSClientError):
        client.delete_attachment_by_id("123", "att-1")


def test_get_child_pages_passes_expand_to_sdk() -> None:
    client = _make_stub_confluence_client()
    client._client.get_page_child_by_type.return_value = {"results": [{"id": "1"}]}

    result = client.get_child_pages("123", expand=["body.storage"])

    assert result == [{"id": "1"}]
    client._client.get_page_child_by_type.assert_called_once_with(
        "123",
        type="page",
        start=0,
        limit=100,
        expand="body.storage",
    )


def test_get_child_pages_paginates_until_short_page() -> None:
    client = _make_stub_confluence_client()
    first_page = [{"id": str(i)} for i in range(100)]
    second_page = [{"id": "last"}]
    client._client.get_page_child_by_type.side_effect = [
        {"results": first_page},
        {"results": second_page},
    ]

    result = client.get_child_pages("123", expand=["body.storage"])

    assert len(result) == 101
    assert result[-1]["id"] == "last"
    assert client._client.get_page_child_by_type.call_count == 2
    first_call = client._client.get_page_child_by_type.call_args_list[0]
    second_call = client._client.get_page_child_by_type.call_args_list[1]
    assert first_call.kwargs["start"] == 0
    assert second_call.kwargs["start"] == 100
    assert first_call.kwargs["limit"] == 100
    assert second_call.kwargs["limit"] == 100
    assert first_call.kwargs["expand"] == "body.storage"
    assert second_call.kwargs["expand"] == "body.storage"


def test_get_child_pages_stops_on_repeated_next_start() -> None:
    client = _make_stub_confluence_client()
    looping_page = [{"id": str(i)} for i in range(100)]
    client._client.get_page_child_by_type.return_value = {
        "results": looping_page,
        "_links": {"next": "/rest/api/content/123/child/page?start=0&limit=100"},
    }

    result = client.get_child_pages("123")

    assert len(result) == 100
    client._client.get_page_child_by_type.assert_called_once()


def test_get_attachments_stops_on_repeated_next_start() -> None:
    client = _make_stub_confluence_client()
    looping_page = [{"id": f"att-{i}"} for i in range(50)]
    client._client.get_attachments_from_content.return_value = {
        "results": looping_page,
        "_links": {"next": "/rest/api/content/123/child/attachment?start=0&limit=50"},
    }

    result = client.get_attachments("123")

    assert len(result) == 50
    client._client.get_attachments_from_content.assert_called_once_with("123", start=0, limit=50)


def test_confluence_client_sets_cloud_flag_for_var_kwargs_constructor(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyCloudClient:
        last_kwargs: dict[str, object] | None = None

        def __init__(self, url: str, *args: object, **kwargs: object) -> None:
            DummyCloudClient.last_kwargs = {"url": url, **kwargs}

        def create_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

        def update_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

    monkeypatch.setattr("confluence_orchestrator.http.AtlassianConfluenceCloud", DummyCloudClient)

    settings = ConfluenceSettings.model_validate(
        {
            "CONFLUENCE_INTERNAL_URL": "https://example.atlassian.net/wiki",
            "INTERNAL_CONFLUENCE_TOKEN": "cloud-token",
            "EXTERNAL_CONFLUENCE_TOKEN": "external-token",
        }
    )

    client = ConfluenceClient(settings, server="internal")

    assert client._is_cloud is True  # type: ignore[attr-defined]
    assert DummyCloudClient.last_kwargs is not None
    assert DummyCloudClient.last_kwargs.get("cloud") is True
    assert DummyCloudClient.last_kwargs.get("token") == "cloud-token"


def test_confluence_client_sets_cloud_false_for_server_var_kwargs_constructor(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyServerClient:
        last_kwargs: dict[str, object] | None = None

        def __init__(self, url: str, *args: object, **kwargs: object) -> None:
            DummyServerClient.last_kwargs = {"url": url, **kwargs}

        def create_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

        def update_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

    monkeypatch.setattr("confluence_orchestrator.http.AtlassianConfluenceServer", DummyServerClient)

    settings = ConfluenceSettings.model_validate(
        {
            "CONFLUENCE_INTERNAL_URL": "https://confluence.digital.vn",
            "VDS_USERNAME": "user",
            "VDS_PASSWORD": "pass",
            "INTERNAL_CONFLUENCE_TOKEN": "server-token",
            "EXTERNAL_CONFLUENCE_TOKEN": "external-token",
        }
    )

    client = ConfluenceClient(settings, server="internal")

    assert client._is_cloud is False  # type: ignore[attr-defined]
    assert DummyServerClient.last_kwargs is not None
    assert DummyServerClient.last_kwargs.get("cloud") is False
    assert DummyServerClient.last_kwargs.get("username") == "user"
    assert DummyServerClient.last_kwargs.get("password") == "pass"


def test_confluence_client_cloud_falls_back_to_basic_auth_when_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyCloudClient:
        last_kwargs: dict[str, object] | None = None

        def __init__(self, url: str, *args: object, **kwargs: object) -> None:
            DummyCloudClient.last_kwargs = {"url": url, **kwargs}

        def create_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

        def update_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

    monkeypatch.setattr("confluence_orchestrator.http.AtlassianConfluenceCloud", DummyCloudClient)

    settings = ConfluenceSettings.model_validate(
        {
            "CONFLUENCE_INTERNAL_URL": "https://example.atlassian.net/wiki",
            "VDS_USERNAME": "user",
            "VDS_PASSWORD": "pass",
        }
    )

    client = ConfluenceClient(settings, server="internal")

    assert client._is_cloud is True  # type: ignore[attr-defined]
    assert DummyCloudClient.last_kwargs is not None
    assert DummyCloudClient.last_kwargs.get("cloud") is True
    assert DummyCloudClient.last_kwargs.get("username") == "user"
    assert DummyCloudClient.last_kwargs.get("password") == "pass"
    assert DummyCloudClient.last_kwargs.get("token") is None


def test_confluence_client_cloud_prefers_basic_auth_over_token(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyCloudClient:
        last_kwargs: dict[str, object] | None = None

        def __init__(self, url: str, *args: object, **kwargs: object) -> None:
            DummyCloudClient.last_kwargs = {"url": url, **kwargs}

        def create_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

        def update_page(self, *args: object, **kwargs: object) -> dict[str, object]:
            return {}

    monkeypatch.setattr("confluence_orchestrator.http.AtlassianConfluenceCloud", DummyCloudClient)

    settings = ConfluenceSettings.model_validate(
        {
            "CONFLUENCE_INTERNAL_URL": "https://example.atlassian.net/wiki",
            "VDS_USERNAME": "user",
            "VDS_PASSWORD": "pass",
            "INTERNAL_CONFLUENCE_TOKEN": "cloud-token",
        }
    )

    client = ConfluenceClient(settings, server="internal")

    assert client._is_cloud is True  # type: ignore[attr-defined]
    assert DummyCloudClient.last_kwargs is not None
    assert DummyCloudClient.last_kwargs.get("cloud") is True
    assert DummyCloudClient.last_kwargs.get("username") == "user"
    assert DummyCloudClient.last_kwargs.get("password") == "pass"
    assert DummyCloudClient.last_kwargs.get("token") is None
