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


def test_client_history_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.history.return_value = {"latest": True, "results": [{"number": 1, "when": "2025-01-01"}]}

    result = client.history("123")

    assert "latest" in result
    inner.history.assert_called_once_with("123")


def test_client_get_content_history_by_version_number_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_content_history_by_version_number.return_value = {"id": "123", "version": 2, "title": "Version 2"}

    result = client.get_content_history_by_version_number("123", 2)

    assert result["version"] == 2
    inner.get_content_history_by_version_number.assert_called_once_with("123", 2)


def test_client_remove_content_history_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.remove_content_history.return_value = None

    result = client.remove_content_history("123", 2)

    assert result is None
    inner.remove_content_history.assert_called_once_with("123", 2)


def test_client_get_page_history_uses_history_fallback() -> None:
    class LegacyHistorySdk:
        def history(self, page_id: str) -> dict[str, Any]:
            return {"id": page_id, "results": [{"number": 1}]}

    client = ConfluenceClient.__new__(ConfluenceClient)  # type: ignore[call-arg]
    client._client = LegacyHistorySdk()  # type: ignore[attr-defined]
    client._log = Mock()

    result = client.get_page_history("123")

    assert result["id"] == "123"


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummyHistoryClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def history(self, page_id: str) -> dict[str, Any]:
        self.calls.append(("history", (page_id,), {}))
        return {"latest": True, "results": [{"number": 1}]}

    def get_content_history_by_version_number(self, page_id: str, version: int) -> dict[str, Any]:
        self.calls.append(("get_content_history_by_version_number", (page_id, version), {}))
        return {"id": page_id, "version": version}

    def remove_content_history(self, page_id: str, version: int) -> None:
        self.calls.append(("remove_content_history", (page_id, version), {}))


def test_cli_history_get_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "get", "--page-id", "123"])

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "history"


def test_cli_history_get_requires_page_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "get"])

    assert result.exit_code != 0
    assert "--page-id required" in result.stdout or "--page-id required" in result.stderr


def test_cli_history_version_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "version", "--page-id", "123", "--version", "2"])

    assert result.exit_code == 0
    assert "123" in result.stdout
    assert "2" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_content_history_by_version_number"
    assert client.calls[0][1][1] == 2


def test_cli_history_version_requires_page_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "version", "--version", "2"])

    assert result.exit_code != 0
    assert "--page-id required" in result.stdout or "--page-id required" in result.stderr


def test_cli_history_version_requires_version(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "version", "--page-id", "123"])

    assert result.exit_code != 0
    assert "--version required" in result.stdout or "--version required" in result.stderr


def test_cli_history_remove_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "remove", "--page-id", "123", "--version", "2", "--yes"])

    assert result.exit_code == 0
    assert "removed" in result.stdout
    assert "experimental" in result.stderr
    assert len(client.calls) == 1
    assert client.calls[0][0] == "remove_content_history"


def test_cli_history_remove_requires_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "remove", "--page-id", "123", "--version", "2"])

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr
    assert "experimental" in result.stdout or "experimental" in result.stderr


def test_cli_history_remove_requires_page_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "remove", "--version", "2", "--yes"])

    assert result.exit_code != 0
    assert "--page-id required" in result.stdout or "--page-id required" in result.stderr


def test_cli_history_remove_requires_version(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "remove", "--page-id", "123", "--yes"])

    assert result.exit_code != 0
    assert "--version required" in result.stdout or "--version required" in result.stderr


def test_cli_history_invalid_action(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyHistoryClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["history", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
