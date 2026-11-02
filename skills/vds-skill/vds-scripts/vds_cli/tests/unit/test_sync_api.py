"""Unit tests for SyncApiClient HTTP adapter."""

from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest
from vds_cli.sync_api import (
    ConfluencePropertySyncApiClient,
    SyncApiClient,
    SyncApiRevisionConflict,
    SyncApiTransientError,
    VdsAiMemorySyncApiClient,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object] | None, *, headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.headers = headers or {}

    def read(self) -> bytes:
        if self._payload is None:
            return b""
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_pull_document_returns_none_on_404(monkeypatch) -> None:
    client = SyncApiClient(endpoint="https://example.invalid/instructions")

    def _raise_404(_request, timeout: int):
        raise HTTPError(
            client.endpoint,
            404,
            "Not Found",
            hdrs={},
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _raise_404)
    assert client.pull_document() is None


def test_pull_document_prefers_etag_revision(monkeypatch) -> None:
    client = SyncApiClient(endpoint="https://example.invalid/instructions")

    def _ok(_request, timeout: int):
        return _FakeResponse(
            {
                "content": "hello",
                "source_file": "AGENTS.md",
                "updated_at": "2026-02-28T00:00:00Z",
            },
            headers={"ETag": '"42"'},
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _ok)
    document = client.pull_document()

    assert document is not None
    assert document.revision == "42"
    assert document.content == "hello"
    assert document.source_file == "AGENTS.md"


def test_push_if_match_sets_conditional_header(monkeypatch) -> None:
    client = SyncApiClient(endpoint="https://example.invalid/instructions")
    captured_headers: dict[str, str] = {}

    def _ok(request, timeout: int):
        captured_headers.update(request.headers)
        return _FakeResponse(
            {
                "content": "merged",
                "source_file": "CLAUDE.md",
                "updated_at": "2026-02-28T00:00:01Z",
                "revision": "9",
            }
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _ok)
    document = client.push_document_if_match(
        content="merged",
        source_file="CLAUDE.md",
        expected_revision="8",
    )

    assert captured_headers.get("If-match") == '"8"'
    assert document.revision == "9"
    assert document.content == "merged"


def test_push_if_match_conflict_raises(monkeypatch) -> None:
    client = SyncApiClient(endpoint="https://example.invalid/instructions")

    def _conflict(request, timeout: int):
        raise HTTPError(
            request.full_url,
            412,
            "Precondition Failed",
            hdrs={},
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _conflict)

    with pytest.raises(SyncApiRevisionConflict):
        client.push_document_if_match(
            content="latest",
            source_file="AGENTS.md",
            expected_revision="7",
        )


def test_pull_document_transient_http_503_raises_transient(monkeypatch) -> None:
    client = SyncApiClient(endpoint="https://example.invalid/instructions")

    def _raise_503(request, timeout: int):
        raise HTTPError(
            request.full_url,
            503,
            "Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _raise_503)
    with pytest.raises(SyncApiTransientError):
        client.pull_document()


def test_pull_document_transient_network_error_raises_transient(monkeypatch) -> None:
    client = SyncApiClient(endpoint="https://example.invalid/instructions")

    def _raise_urlerror(_request, timeout: int):
        raise URLError("connection reset")

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _raise_urlerror)
    with pytest.raises(SyncApiTransientError):
        client.pull_document()


def test_vds_ai_memory_pull_document(monkeypatch) -> None:
    client = VdsAiMemorySyncApiClient(
        base_url="https://memory.example",
        memory_id="mem-1",
        user_id="sync-user",
        session_id="sync-session",
    )

    def _ok(request, timeout: int):
        assert request.full_url.endswith("/api/v1/memories/mem-1")
        return _FakeResponse(
            {
                "content": "shared body",
                "current_version_number": 7,
                "updated_at": "2026-02-28T00:00:00Z",
                "metadata": {
                    "sync_source_file": "CLAUDE.md",
                    "sync_content_hash": "deadbeef",
                },
            }
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _ok)
    document = client.pull_document()

    assert document is not None
    assert document.revision == "7"
    assert document.source_file == "CLAUDE.md"
    assert document.content_hash == "deadbeef"
    assert document.content == "shared body"


def test_vds_ai_memory_push_revision_mismatch_raises(monkeypatch) -> None:
    client = VdsAiMemorySyncApiClient(
        base_url="https://memory.example",
        memory_id="mem-1",
        user_id="sync-user",
        session_id="sync-session",
    )

    def _ok(_request, timeout: int):
        return _FakeResponse(
            {
                "content": "remote",
                "current_version_number": 9,
                "updated_at": "2026-02-28T00:00:00Z",
            }
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _ok)
    with pytest.raises(SyncApiRevisionConflict):
        client.push_document_if_match(
            content="local",
            source_file="AGENTS.md",
            expected_revision="8",
        )


def test_vds_ai_memory_push_updates_with_metadata(monkeypatch) -> None:
    client = VdsAiMemorySyncApiClient(
        base_url="https://memory.example",
        memory_id="mem-1",
        user_id="sync-user",
        session_id="sync-session",
    )
    seen_patch_payload: dict[str, object] = {}
    call_count = {"count": 0}

    def _mock(request, timeout: int):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return _FakeResponse(
                {
                    "content": "remote",
                    "current_version_number": 3,
                    "updated_at": "2026-02-28T00:00:00Z",
                }
            )
        assert request.get_method() == "PATCH"
        assert request.headers.get("If-match") == '"3"'
        seen_patch_payload.update(json.loads(request.data.decode("utf-8")))
        return _FakeResponse(
            {
                "content": "local-updated",
                "current_version_number": 4,
                "updated_at": "2026-02-28T00:00:01Z",
                "metadata": {"sync_source_file": "AGENTS.md"},
            }
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _mock)
    document = client.push_document_if_match(
        content="local-updated",
        source_file="AGENTS.md",
        expected_revision="3",
    )

    assert document.revision == "4"
    metadata = seen_patch_payload.get("metadata")
    assert isinstance(metadata, dict)
    assert metadata.get("sync_source_file") == "AGENTS.md"
    assert seen_patch_payload.get("expected_current_version_number") == 3


def test_confluence_property_pull_document(monkeypatch) -> None:
    client = ConfluencePropertySyncApiClient(
        base_url="https://confluence.example",
        page_id="12345",
        property_key="vds_sync_instructions",
        auth_token="token",
    )

    def _ok(request, timeout: int):
        assert request.full_url.endswith("/rest/api/content/12345/property/vds_sync_instructions")
        return _FakeResponse(
            {
                "value": {
                    "content": "canonical",
                    "source_file": "AGENTS.md",
                    "content_hash": "cafebabe",
                    "updated_at": "2026-02-28T00:00:00Z",
                },
                "version": {"number": 12, "when": "2026-02-28T00:00:00Z"},
            }
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _ok)
    document = client.pull_document()
    assert document is not None
    assert document.revision == "12"
    assert document.source_file == "AGENTS.md"
    assert document.content_hash == "cafebabe"


def test_confluence_property_push_increments_version(monkeypatch) -> None:
    client = ConfluencePropertySyncApiClient(
        base_url="https://confluence.example",
        page_id="12345",
        property_key="vds_sync_instructions",
        auth_token="token",
    )
    seen_payload: dict[str, object] = {}
    call_count = {"count": 0}

    def _mock(request, timeout: int):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return _FakeResponse(
                {
                    "value": {"content": "old"},
                    "version": {"number": 4, "when": "2026-02-28T00:00:00Z"},
                }
            )
        seen_payload.update(json.loads(request.data.decode("utf-8")))
        return _FakeResponse(
            {
                "value": {"content": "new", "source_file": "CLAUDE.md"},
                "version": {"number": 5, "when": "2026-02-28T00:00:01Z"},
            }
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _mock)
    document = client.push_document_if_match(
        content="new",
        source_file="CLAUDE.md",
        expected_revision="4",
    )

    assert document.revision == "5"
    version = seen_payload.get("version")
    assert isinstance(version, dict)
    assert version.get("number") == 5


def test_confluence_property_conflict_raises(monkeypatch) -> None:
    client = ConfluencePropertySyncApiClient(
        base_url="https://confluence.example",
        page_id="12345",
        property_key="vds_sync_instructions",
        auth_token="token",
    )
    call_count = {"count": 0}

    def _mock(request, timeout: int):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return _FakeResponse(
                {
                    "value": {"content": "old"},
                    "version": {"number": 7, "when": "2026-02-28T00:00:00Z"},
                }
            )
        raise HTTPError(
            request.full_url,
            409,
            "Conflict",
            hdrs={},
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr("vds_cli.sync_api.urlopen", _mock)
    with pytest.raises(SyncApiRevisionConflict):
        client.push_document_if_match(
            content="new",
            source_file="AGENTS.md",
            expected_revision="7",
        )
