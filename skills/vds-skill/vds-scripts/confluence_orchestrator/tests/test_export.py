from __future__ import annotations

from pathlib import Path
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
    client._is_cloud = True  # type: ignore[attr-defined]
    client._with_retry = lambda operation, _: operation()  # type: ignore[assignment]
    return client, inner


# ---------------------------------------------------------------------------
# Client method coverage
# ---------------------------------------------------------------------------


def test_client_export_page_cloud_mode_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.export_page.return_value = b"%PDF-1.4 fake pdf content"

    result = client.export_page("12345")

    assert result == b"%PDF-1.4 fake pdf content"
    # SDK auto-detects Cloud/Server mode, so api_version is not passed
    inner.export_page.assert_called_once_with("12345")


def test_client_export_page_server_mode_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    client._is_cloud = False  # type: ignore[attr-defined]
    inner.export_page.return_value = b"%PDF-1.4 fake pdf content"

    result = client.export_page("12345")

    assert result == b"%PDF-1.4 fake pdf content"
    # SDK auto-detects Cloud/Server mode, so api_version is not passed
    inner.export_page.assert_called_once_with("12345")


def test_client_export_page_with_explicit_api_version() -> None:
    client, inner = _build_fake_client()
    inner.export_page.return_value = b"%PDF-1.4 fake pdf content"

    result = client.export_page("12345", api_version="server")

    assert result == b"%PDF-1.4 fake pdf content"
    # SDK auto-detects Cloud/Server mode, so api_version parameter is accepted but not passed to SDK
    inner.export_page.assert_called_once_with("12345")


def test_client_export_page_handles_file_path() -> None:
    client, inner = _build_fake_client()
    # Mock file path return
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"%PDF-1.4 fake pdf content")
        tmp_path = tmp.name

    inner.export_page.return_value = tmp_path

    result = client.export_page("12345")

    assert result == b"%PDF-1.4 fake pdf content"
    # Cleanup
    Path(tmp_path).unlink()


def test_client_get_space_export_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_space_export.return_value = "https://example.com/export/space.pdf"

    result = client.get_space_export("ABC", "pdf")

    assert result == "https://example.com/export/space.pdf"
    inner.get_space_export.assert_called_once_with("ABC", "pdf")


def test_client_get_space_export_with_different_types() -> None:
    client, inner = _build_fake_client()
    inner.get_space_export.return_value = "https://example.com/export/space.html"

    result = client.get_space_export("ABC", "html")

    assert result == "https://example.com/export/space.html"
    inner.get_space_export.assert_called_once_with("ABC", "html")


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummyExportClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def export_page(self, page_id: str, api_version: str | None = None) -> bytes:
        self.calls.append(("export_page", (page_id,), {"api_version": api_version}))
        return b"%PDF-1.4 fake pdf content"

    def get_space_export(self, space_key: str, export_type: str) -> str:
        self.calls.append(("get_space_export", (space_key, export_type), {}))
        return f"https://example.com/export/{space_key}.{export_type}"


def test_cli_export_page_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    output_file = tmp_path / "test.pdf"
    result = runner.invoke(app, ["export", "page", "--page-id", "12345", "--output", str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()
    assert output_file.read_bytes() == b"%PDF-1.4 fake pdf content"
    assert len(client.calls) == 1
    assert client.calls[0][0] == "export_page"


def test_cli_export_page_requires_page_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["export", "page"])

    assert result.exit_code != 0
    assert "--page-id required" in result.stdout or "--page-id required" in result.stderr


def test_cli_export_page_with_api_version(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    output_file = tmp_path / "test.pdf"
    result = runner.invoke(
        app, ["export", "page", "--page-id", "12345", "--api-version", "server", "--output", str(output_file)]
    )

    assert result.exit_code == 0
    assert client.calls[0][2]["api_version"] == "server"


def test_cli_export_space_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["export", "space", "--space-key", "ABC", "--export-type", "pdf"])

    assert result.exit_code == 0
    assert "ABC" in result.stdout or "download_url" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_space_export"


def test_cli_export_space_requires_space_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["export", "space", "--export-type", "pdf"])

    assert result.exit_code != 0
    assert "--space-key required" in result.stdout or "--space-key required" in result.stderr


def test_cli_export_space_requires_export_type(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["export", "space", "--space-key", "ABC"])

    assert result.exit_code != 0
    assert "--export-type required" in result.stdout or "--export-type required" in result.stderr


def test_cli_export_space_validates_export_type(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["export", "space", "--space-key", "ABC", "--export-type", "invalid"])

    assert result.exit_code != 0
    assert "must be one of" in result.stdout or "must be one of" in result.stderr


def test_cli_export_space_with_different_types(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    for export_type in ("pdf", "html", "xml"):
        result = runner.invoke(app, ["export", "space", "--space-key", "ABC", "--export-type", export_type])
        assert result.exit_code == 0


def test_cli_export_invalid_action(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyExportClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["export", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
