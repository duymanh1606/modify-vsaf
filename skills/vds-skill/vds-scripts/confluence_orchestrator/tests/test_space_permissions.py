from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, call

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
    client._with_retry = lambda operation, _: operation()  # type: ignore[assignment]
    return client, inner


# ---------------------------------------------------------------------------
# Client method coverage
# ---------------------------------------------------------------------------


def test_client_get_space_permissions_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_space_permissions.return_value = [{"id": 1}]

    result = client.get_space_permissions("ABC")

    assert result == {"value": [{"id": 1}]}
    inner.get_space_permissions.assert_called_once_with("ABC")


def test_client_set_permissions_to_user_for_space_passes_operations() -> None:
    client, inner = _build_fake_client()
    client.set_permissions_to_user_for_space("ABC", "user-key", operations=["read", "write"])

    inner.set_permissions_to_user_for_space.assert_called_once_with("ABC", "user-key", operations=["read", "write"])


def test_client_remove_permissions_from_group_for_space() -> None:
    client, inner = _build_fake_client()
    client.remove_permissions_from_group_for_space("ABC", "admins")

    inner.remove_permissions_from_group_for_space.assert_called_once_with("ABC", "admins")


def test_client_set_permissions_to_multiple_items_for_space_native_items_contract() -> None:
    client, inner = _build_fake_client()
    client._safe_signature_params = (  # type: ignore[assignment]
        lambda method: ["space_key", "items"] if method is inner.set_permissions_to_multiple_items_for_space else []
    )
    items = [{"target": {"type": "group", "value": "admins"}, "operations": ["read"]}]
    inner.set_permissions_to_multiple_items_for_space.return_value = {"status": "ok"}

    result = client.set_permissions_to_multiple_items_for_space("ABC", items)

    assert result == {"status": "ok"}
    inner.set_permissions_to_multiple_items_for_space.assert_called_once_with("ABC", items=items)


def test_client_set_permissions_to_multiple_items_for_space_legacy_single_target_contract() -> None:
    client, inner = _build_fake_client()
    client._safe_signature_params = (  # type: ignore[assignment]
        lambda method: (
            ["space_key", "user_key", "group_name", "operations"]
            if method is inner.set_permissions_to_multiple_items_for_space
            else []
        )
    )
    items = [
        {"target": {"type": "user", "value": "user-1"}, "operations": ["read"]},
        {"target": {"type": "group", "value": "admins"}, "operations": ["read", "write"]},
        {"target": {"type": "anonymous"}, "operations": ["read"]},
    ]
    inner.set_permissions_to_multiple_items_for_space.side_effect = [
        {"status": "user-ok"},
        {"status": "group-ok"},
        {"status": "anonymous-ok"},
    ]

    result = client.set_permissions_to_multiple_items_for_space("ABC", items)

    assert result["mode"] == "legacy-bulk"
    assert result["items_processed"] == 3
    assert inner.set_permissions_to_multiple_items_for_space.call_args_list == [
        call("ABC", user_key="user-1", operations=["read"]),
        call("ABC", group_name="admins", operations=["read", "write"]),
        call("ABC", operations=["read"]),
    ]


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummySpacePermissionsClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def get_space_permissions(self, space_key: str) -> list[dict[str, Any]]:
        self.calls.append(("get", (space_key,), {}))
        return [{"type": "user"}]

    def set_permissions_to_user_for_space(
        self, space_key: str, user_key: str, *, operations: list[str] | None = None
    ) -> dict[str, Any]:
        self.calls.append(("set_user", (space_key, user_key), {"operations": operations}))
        return {"status": "ok"}

    def set_permissions_to_group_for_space(
        self, space_key: str, group_name: str, *, operations: list[str] | None = None
    ) -> dict[str, Any]:
        self.calls.append(("set_group", (space_key, group_name), {"operations": operations}))
        return {"status": "ok"}

    def set_permissions_to_anonymous_for_space(
        self, space_key: str, *, operations: list[str] | None = None
    ) -> dict[str, Any]:
        self.calls.append(("set_anonymous", (space_key,), {"operations": operations}))
        return {"status": "ok"}

    def set_permissions_to_multiple_items_for_space(
        self, space_key: str, items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.calls.append(("bulk_set", (space_key,), {"items": items}))
        return {"status": "ok"}

    def remove_permissions_from_user_for_space(self, space_key: str, user_key: str) -> dict[str, Any]:
        self.calls.append(("remove_user", (space_key, user_key), {}))
        return {"status": "ok"}

    def remove_permissions_from_group_for_space(self, space_key: str, group_name: str) -> dict[str, Any]:
        self.calls.append(("remove_group", (space_key, group_name), {}))
        return {"status": "ok"}

    def remove_permissions_from_anonymous_for_space(self, space_key: str) -> dict[str, Any]:
        self.calls.append(("remove_anonymous", (space_key,), {}))
        return {"status": "ok"}


@pytest.fixture
def dummy_client(monkeypatch: pytest.MonkeyPatch) -> DummySpacePermissionsClient:
    client = DummySpacePermissionsClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args, **kwargs: client)
    return client


def test_cli_space_permissions_get_success(dummy_client: DummySpacePermissionsClient, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--report-dir", str(tmp_path), "space-permissions", "get", "--space-key", "ABC", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["space"] == "ABC"
    assert payload["permissions"] == [{"type": "user"}]
    assert dummy_client.calls[0][0] == "get"


def test_cli_space_permissions_set_requires_yes(dummy_client: DummySpacePermissionsClient, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "set",
            "--space-key",
            "ABC",
            "--user",
            "user-1",
            "--operation",
            "read",
            "--json",
        ],
    )

    assert result.exit_code != 0
    assert "--yes required" in result.stderr or "--yes required" in result.output
    assert not dummy_client.calls


def test_cli_space_permissions_set_user_success(dummy_client: DummySpacePermissionsClient, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "set",
            "--space-key",
            "ABC",
            "--user",
            "user-1",
            "--operation",
            "read",
            "--operation",
            "write",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["operations"] == ["read", "write"]
    assert dummy_client.calls[0][0] == "set_user"
    assert dummy_client.calls[0][2]["operations"] == ["read", "write"]


def test_cli_space_permissions_set_anonymous_success(dummy_client: DummySpacePermissionsClient, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "set",
            "--space-key",
            "ABC",
            "--anonymous",
            "--operation",
            "read",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["target"]["type"] == "anonymous"
    assert dummy_client.calls[0][0] == "set_anonymous"


def test_cli_space_permissions_set_bulk_from_file(dummy_client: DummySpacePermissionsClient, tmp_path: Path) -> None:
    data = [{"target": {"type": "group", "value": "admins"}, "operations": ["read"]}]
    permissions_file = tmp_path / "permissions.json"
    permissions_file.write_text(json.dumps(data))

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "set",
            "--space-key",
            "ABC",
            "--permissions-file",
            str(permissions_file),
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["bulk"] is True
    assert payload["items_processed"] == 1
    assert dummy_client.calls[0][0] == "bulk_set"


def test_cli_space_permissions_remove_group_success(dummy_client: DummySpacePermissionsClient, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "remove",
            "--space-key",
            "ABC",
            "--group",
            "admins",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["target"]["type"] == "group"
    assert dummy_client.calls[0][0] == "remove_group"


def test_cli_space_permissions_remove_anonymous_success(
    dummy_client: DummySpacePermissionsClient, tmp_path: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "remove",
            "--space-key",
            "ABC",
            "--anonymous",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["target"]["type"] == "anonymous"
    assert dummy_client.calls[0][0] == "remove_anonymous"


def test_cli_space_permissions_set_multiple_targets_error(
    dummy_client: DummySpacePermissionsClient, tmp_path: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "set",
            "--space-key",
            "ABC",
            "--user",
            "user-1",
            "--group",
            "admins",
            "--operation",
            "read",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code != 0
    assert "exactly one" in result.stderr or "exactly one" in result.output
    assert not dummy_client.calls


def test_cli_space_permissions_set_requires_operations_when_user(
    dummy_client: DummySpacePermissionsClient, tmp_path: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "space-permissions",
            "set",
            "--space-key",
            "ABC",
            "--user",
            "user-1",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code != 0
    assert "At least one --operation required" in result.stderr or "At least one --operation required" in result.output
    assert not dummy_client.calls
