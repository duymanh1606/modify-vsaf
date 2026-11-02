from __future__ import annotations

import json
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
    def fake_load(strict: bool = False) -> ConfluenceSettings:
        return ConfluenceSettings.model_validate(
            {
                "VDS_USERNAME": "user",
                "VDS_PASSWORD": "pass",
                "INTERNAL_CONFLUENCE_TOKEN": "token-int",
                "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
            }
        )

    monkeypatch.setattr("confluence_orchestrator.cli.load_settings", fake_load)


def _build_fake_client() -> tuple[ConfluenceClient, Mock]:
    inner = Mock()
    client = ConfluenceClient.__new__(ConfluenceClient)  # type: ignore[call-arg]
    client._client = inner  # type: ignore[attr-defined]
    client._log = Mock()
    client._with_retry = lambda operation, _: operation()  # type: ignore[assignment]
    return client, inner


# ---------------------------------------------------------------------------
# Client method coverage
# ---------------------------------------------------------------------------


def test_client_archive_space_calls_sdk() -> None:
    client, inner = _build_fake_client()
    inner.archive_space.return_value = {"status": "archived"}

    result = client.archive_space("ABC")

    assert result == {"status": "archived"}
    inner.archive_space.assert_called_once_with("ABC")


def test_client_get_trashed_contents_passes_arguments() -> None:
    client, inner = _build_fake_client()
    inner.get_trashed_contents_by_space.return_value = {"results": []}

    result = client.get_trashed_contents_by_space("ABC", cursor="cur", expand="children", limit=25)

    assert result == {"results": []}
    inner.get_trashed_contents_by_space.assert_called_once_with("ABC", cursor="cur", expand="children", limit=25)


def test_client_remove_trashed_contents_calls_sdk() -> None:
    client, inner = _build_fake_client()
    inner.remove_trashed_contents_by_space.return_value = {"status": "removed"}

    result = client.remove_trashed_contents_by_space("ABC")

    assert result == {"status": "removed"}
    inner.remove_trashed_contents_by_space.assert_called_once_with("ABC")


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummySpaceManagementClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def archive_space(self, space_key: str) -> dict[str, Any]:
        self.calls.append(("archive", (space_key,), {}))
        return {"status": "archived"}

    def get_trashed_contents_by_space(
        self,
        space_key: str,
        *,
        cursor: str | None = None,
        expand: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        self.calls.append(("trash_list", (space_key,), {"cursor": cursor, "expand": expand, "limit": limit}))
        return {"results": [{"title": "Page"}], "size": 1}

    def remove_trashed_contents_by_space(self, space_key: str) -> dict[str, Any]:
        self.calls.append(("trash_remove", (space_key,), {}))
        return {"status": "removed"}


@pytest.fixture
def dummy_client(monkeypatch: pytest.MonkeyPatch) -> DummySpaceManagementClient:
    client = DummySpaceManagementClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args, **kwargs: client)
    return client


def test_cli_space_management_archive_requires_yes(dummy_client: DummySpaceManagementClient, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-management",
            "archive",
            "--space-key",
            "ABC",
            "--json",
        ],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stderr or "--yes required" in result.output
    assert not dummy_client.calls


def test_cli_space_management_archive_success(dummy_client: DummySpaceManagementClient, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-management",
            "archive",
            "--space-key",
            "ABC",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["action"] == "archive"
    assert dummy_client.calls[0][0] == "archive"


def test_cli_space_management_trash_list_success(dummy_client: DummySpaceManagementClient, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-management",
            "trash-list",
            "--space-key",
            "ABC",
            "--cursor",
            "cur",
            "--limit",
            "25",
            "--expand",
            "children",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["action"] == "trash-list"
    assert dummy_client.calls[0][2]["limit"] == 25
    assert dummy_client.calls[0][2]["cursor"] == "cur"


def test_cli_space_management_trash_remove_success(dummy_client: DummySpaceManagementClient, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-management",
            "trash-remove",
            "--space-key",
            "ABC",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["action"] == "trash-remove"
    assert dummy_client.calls[0][0] == "trash_remove"


def test_cli_space_management_limit_validation(dummy_client: DummySpaceManagementClient, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-management",
            "trash-list",
            "--space-key",
            "ABC",
            "--limit",
            "500",
            "--json",
        ],
    )

    assert result.exit_code != 0
    assert "must be between 1 and 100" in result.stderr or "must be between 1 and 100" in result.output
    assert not dummy_client.calls


def test_cli_space_management_unknown_action(dummy_client: DummySpaceManagementClient, tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-management",
            "unknown",
            "--space-key",
            "ABC",
            "--json",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown action" in result.stderr or "Unknown action" in result.output
    assert not dummy_client.calls
