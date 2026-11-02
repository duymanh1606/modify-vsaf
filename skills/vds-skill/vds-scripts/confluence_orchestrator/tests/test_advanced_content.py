from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from confluence_orchestrator.cli import app
from confluence_orchestrator.config import ConfluenceSettings
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


def _build_fake_client() -> tuple[ConfluenceClient, Mock]:
    inner = Mock()
    client = ConfluenceClient.__new__(ConfluenceClient)  # type: ignore[call-arg]
    client._client = inner  # type: ignore[attr-defined]
    client._log = Mock()
    client._is_cloud = False  # type: ignore[attr-defined]
    client._with_retry = lambda operation, _: operation()  # type: ignore[assignment]
    return client, inner


# ---------------------------------------------------------------------------
# Client method coverage
# ---------------------------------------------------------------------------


def test_client_get_page_ancestors_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_page_ancestors.return_value = [{"id": "1", "title": "Parent 1"}, {"id": "2", "title": "Parent 2"}]

    result = client.get_page_ancestors("123")

    assert len(result) == 2
    assert result[0]["title"] == "Parent 1"
    inner.get_page_ancestors.assert_called_once_with("123")


def test_client_move_page_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    client._safe_signature_params = (  # type: ignore[assignment]
        lambda method: (
            ["space_key", "page_id", "target_id", "target_title", "position"] if method is inner.move_page else []
        )
    )
    inner.get_page_space.return_value = "TTTC"
    inner.move_page.return_value = {"id": "123", "title": "Moved Page"}

    result = client.move_page("123", "Target Page", position="append")

    assert result["id"] == "123"
    inner.move_page.assert_called_once_with("TTTC", "123", target_title="Target Page", position="append")


def test_client_move_page_with_position() -> None:
    client, inner = _build_fake_client()
    client._safe_signature_params = (  # type: ignore[assignment]
        lambda method: (
            ["space_key", "page_id", "target_id", "target_title", "position"] if method is inner.move_page else []
        )
    )
    inner.get_page_space.return_value = "TTTC"
    inner.move_page.return_value = {"id": "123"}

    client.move_page("123", "Target Page", position="before")

    inner.move_page.assert_called_once_with("TTTC", "123", target_title="Target Page", position="above")


def test_client_move_page_modern_sdk_contract() -> None:
    client, inner = _build_fake_client()
    client._safe_signature_params = (  # type: ignore[assignment]
        lambda method: ["page_id", "target_title", "position"] if method is inner.move_page else []
    )
    inner.move_page.return_value = {"id": "123", "title": "Moved Page"}

    result = client.move_page("123", "Target Page", position="after")

    assert result["id"] == "123"
    inner.move_page.assert_called_once_with("123", "Target Page", position="after")


def test_client_get_tables_from_page_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_tables_from_page.return_value = [{"rows": 2, "cols": 3}, {"rows": 1, "cols": 2}]

    result = client.get_tables_from_page("123")

    assert len(result) == 2
    inner.get_tables_from_page.assert_called_once_with("123")


def test_client_scrap_regex_from_page_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.scrap_regex_from_page.return_value = [{"match": "test1"}, {"match": "test2"}]

    result = client.scrap_regex_from_page("123", r"\d+")

    assert len(result) == 2
    inner.scrap_regex_from_page.assert_called_once_with("123", r"\d+")


def test_client_get_all_restrictions_for_content_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_all_restrictions_for_content.return_value = {"read": ["user1"], "write": ["user2"]}

    result = client.get_all_restrictions_for_content("123")

    assert "read" in result
    inner.get_all_restrictions_for_content.assert_called_once_with("123")


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummyAdvancedContentClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def get_page_ancestors(self, page_id: str) -> list[dict[str, Any]]:
        self.calls.append(("get_page_ancestors", (page_id,), {}))
        return [{"id": "1", "title": "Parent"}]

    def move_page(self, page_id: str, target_title: str, position: str = "append") -> dict[str, Any]:
        self.calls.append(("move_page", (page_id, target_title), {"position": position}))
        return {"id": page_id, "moved": True}

    def get_tables_from_page(self, page_id: str) -> list[dict[str, Any]]:
        self.calls.append(("get_tables_from_page", (page_id,), {}))
        return [{"rows": 2, "cols": 3}]

    def scrap_regex_from_page(self, page_id: str, regex: str) -> list[dict[str, Any]]:
        self.calls.append(("scrap_regex_from_page", (page_id, regex), {}))
        return [{"match": "test"}]

    def get_all_restrictions_for_content(self, content_id: str) -> dict[str, Any]:
        self.calls.append(("get_all_restrictions_for_content", (content_id,), {}))
        return {"read": ["user1"]}


def test_cli_content_ancestors_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["content", "ancestors", "123"])

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_page_ancestors"


def test_cli_content_move_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(
        app, ["content", "move", "123", "--target-title", "Target Page", "--position", "append", "--yes"]
    )

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "move_page"
    assert client.calls[0][2]["position"] == "append"


def test_cli_content_move_requires_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["content", "move", "123", "--target-title", "Target Page"])

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr


def test_cli_content_move_validates_position(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(
        app, ["content", "move", "123", "--target-title", "Target", "--position", "invalid", "--yes"]
    )

    assert result.exit_code != 0
    assert "must be one of" in result.stdout or "must be one of" in result.stderr


def test_cli_content_tables_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["content", "tables", "123"])

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_tables_from_page"


def test_cli_content_regex_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["content", "regex", "123", "--pattern", r"\d+"])

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "scrap_regex_from_page"


def test_cli_content_regex_requires_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["content", "regex", "123"])

    assert result.exit_code != 0
    # Typer will show error about missing required option


def test_cli_content_restrictions_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyAdvancedContentClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["content", "restrictions", "123"])

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_all_restrictions_for_content"
