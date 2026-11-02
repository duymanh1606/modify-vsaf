from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from confluence_orchestrator.cli import app
from confluence_orchestrator.config import ConfluenceSettings
from confluence_orchestrator.errors import VDSClientError
from confluence_orchestrator.http import ConfluenceClient
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load_settings(strict: bool = False) -> ConfluenceSettings:
        return ConfluenceSettings.model_validate(
            {
                "VDS_USERNAME": "user",
                "VDS_PASSWORD": "pass",
                "INTERNAL_CONFLUENCE_TOKEN": "token-int",
                "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
            }
        )

    monkeypatch.setattr("confluence_orchestrator.cli.load_settings", fake_load_settings)


def _build_fake_client(cloud: bool = False) -> tuple[ConfluenceClient, Mock]:
    inner = Mock()
    client = ConfluenceClient.__new__(ConfluenceClient)  # type: ignore[call-arg]
    client._client = inner  # type: ignore[attr-defined]
    client._log = Mock()
    client._is_cloud = cloud  # type: ignore[attr-defined]
    client._with_retry = lambda operation, _: operation()  # type: ignore[assignment]
    return client, inner


# ---------------------------------------------------------------------------
# Client method coverage
# ---------------------------------------------------------------------------


def test_client_get_draft_page_by_id_server_mode_invokes_sdk() -> None:
    client, inner = _build_fake_client(cloud=False)
    inner.get_draft_page_by_id.return_value = {"id": "123", "title": "Draft Page"}

    result = client.get_draft_page_by_id("123")

    assert result["id"] == "123"
    inner.get_draft_page_by_id.assert_called_once_with("123")


def test_client_get_draft_page_by_id_cloud_mode_raises_error() -> None:
    client, inner = _build_fake_client(cloud=True)

    with pytest.raises(VDSClientError, match="only available in Confluence Server"):
        client.get_draft_page_by_id("123")
    inner.get_draft_page_by_id.assert_not_called()


def test_client_get_all_draft_pages_from_space_server_mode_invokes_sdk() -> None:
    client, inner = _build_fake_client(cloud=False)
    inner.get_all_draft_pages_from_space.return_value = [
        {"id": "1", "title": "Draft 1"},
        {"id": "2", "title": "Draft 2"},
    ]

    result = client.get_all_draft_pages_from_space("ABC", limit=50)

    assert len(result) == 2
    inner.get_all_draft_pages_from_space.assert_called_once_with("ABC", limit=50)


def test_client_get_all_draft_pages_from_space_cloud_mode_raises_error() -> None:
    client, inner = _build_fake_client(cloud=True)

    with pytest.raises(VDSClientError, match="only available in Confluence Server"):
        client.get_all_draft_pages_from_space("ABC")
    inner.get_all_draft_pages_from_space.assert_not_called()


def test_client_remove_page_as_draft_server_mode_invokes_sdk() -> None:
    client, inner = _build_fake_client(cloud=False)
    inner.remove_page_as_draft.return_value = None

    result = client.remove_page_as_draft("123")

    assert result is None
    inner.remove_page_as_draft.assert_called_once_with("123")


def test_client_remove_page_as_draft_cloud_mode_raises_error() -> None:
    client, inner = _build_fake_client(cloud=True)

    with pytest.raises(VDSClientError, match="only available in Confluence Server"):
        client.remove_page_as_draft("123")
    inner.remove_page_as_draft.assert_not_called()


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummyDraftClient:
    def __init__(self, cloud: bool = False) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._is_cloud = cloud  # type: ignore[attr-defined]

    def get_draft_page_by_id(self, page_id: str) -> dict[str, Any]:
        if self._is_cloud:
            raise VDSClientError("Server-only feature")
        self.calls.append(("get_draft_page_by_id", (page_id,), {}))
        return {"id": page_id, "title": "Draft Page"}

    def get_all_draft_pages_from_space(self, space_key: str, limit: int = 25) -> list[dict[str, Any]]:
        if self._is_cloud:
            raise VDSClientError("Server-only feature")
        self.calls.append(("get_all_draft_pages_from_space", (space_key,), {"limit": limit}))
        return [{"id": "1", "title": "Draft 1"}]

    def remove_page_as_draft(self, page_id: str) -> None:
        if self._is_cloud:
            raise VDSClientError("Server-only feature")
        self.calls.append(("remove_page_as_draft", (page_id,), {}))


def test_cli_draft_get_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "get", "--page-id", "123"])

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_draft_page_by_id"


def test_cli_draft_get_requires_page_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "get"])

    assert result.exit_code != 0
    assert "--page-id required" in result.stdout or "--page-id required" in result.stderr


def test_cli_draft_list_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "list", "--space-key", "ABC", "--limit", "50"])

    assert result.exit_code == 0
    assert "ABC" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_all_draft_pages_from_space"
    assert client.calls[0][2]["limit"] == 50


def test_cli_draft_list_requires_space_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "list"])

    assert result.exit_code != 0
    assert "--space-key required" in result.stdout or "--space-key required" in result.stderr


def test_cli_draft_remove_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "remove", "--page-id", "123", "--yes"])

    assert result.exit_code == 0
    assert "removed" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "remove_page_as_draft"


def test_cli_draft_remove_requires_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "remove", "--page-id", "123"])

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr


def test_cli_draft_remove_requires_page_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "remove", "--yes"])

    assert result.exit_code != 0
    assert "--page-id required" in result.stdout or "--page-id required" in result.stderr


def test_cli_draft_cloud_mode_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=True)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "get", "--page-id", "123"])

    assert result.exit_code != 0
    assert "Server-only" in result.stderr or "Server-only" in result.stdout


def test_cli_draft_invalid_action(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyDraftClient(cloud=False)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["draft", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
