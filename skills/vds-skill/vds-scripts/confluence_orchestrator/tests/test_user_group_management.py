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
    client._with_retry = lambda operation, _: operation()  # type: ignore[assignment]
    return client, inner


# ---------------------------------------------------------------------------
# Client method coverage
# ---------------------------------------------------------------------------


def test_client_get_all_groups_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_all_groups.return_value = [{"name": "group1"}, {"name": "group2"}]

    result = client.get_all_groups(start=0, limit=100)

    assert len(result) == 2
    assert result[0]["name"] == "group1"
    inner.get_all_groups.assert_called_once_with(start=0, limit=100)


def test_client_get_all_groups_with_pagination() -> None:
    client, inner = _build_fake_client()
    inner.get_all_groups.return_value = [{"name": "group3"}]

    result = client.get_all_groups(start=10, limit=20)

    assert len(result) == 1
    inner.get_all_groups.assert_called_once_with(start=10, limit=20)


def test_client_get_group_members_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_group_members.return_value = [{"username": "user1"}, {"username": "user2"}]

    result = client.get_group_members("admins", start=0, limit=100)

    assert len(result) == 2
    assert result[0]["username"] == "user1"
    inner.get_group_members.assert_called_once_with("admins", start=0, limit=100)


def test_client_get_user_details_by_username_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_user_details_by_username.return_value = {"username": "testuser", "displayName": "Test User"}

    result = client.get_user_details_by_username("testuser", expand="status")

    assert result["username"] == "testuser"
    inner.get_user_details_by_username.assert_called_once_with("testuser", expand="status")


def test_client_get_user_details_by_userkey_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.get_user_details_by_userkey.return_value = {"userKey": "key123", "displayName": "Test User"}

    result = client.get_user_details_by_userkey("key123")

    assert result["userKey"] == "key123"
    inner.get_user_details_by_userkey.assert_called_once_with("key123", expand=None)


def test_client_change_user_password_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.change_user_password.return_value = None

    result = client.change_user_password("testuser", "newpass123")

    assert result is None
    inner.change_user_password.assert_called_once_with("testuser", "newpass123")


def test_client_add_user_to_group_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.add_user_to_group.return_value = None

    result = client.add_user_to_group("testuser", "admins")

    assert result is None
    inner.add_user_to_group.assert_called_once_with("testuser", "admins")


def test_client_remove_user_from_group_invokes_sdk() -> None:
    client, inner = _build_fake_client()
    inner.remove_user_from_group.return_value = None

    result = client.remove_user_from_group("testuser", "admins")

    assert result is None
    inner.remove_user_from_group.assert_called_once_with("testuser", "admins")


# ---------------------------------------------------------------------------
# CLI command coverage
# ---------------------------------------------------------------------------


class DummyGroupClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def get_all_groups(self, start: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        self.calls.append(("get_all_groups", (start, limit), {}))
        return [{"name": "group1"}, {"name": "group2"}]

    def get_group_members(self, group_name: str, start: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        self.calls.append(("get_group_members", (group_name, start, limit), {}))
        return [{"username": "user1"}]


class DummyUserClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def get_user_details_by_username(self, username: str, expand: str | None = None) -> dict[str, Any]:
        self.calls.append(("get_user_details_by_username", (username,), {"expand": expand}))
        return {"username": username, "displayName": "Test User"}

    def get_user_details_by_userkey(self, userkey: str, expand: str | None = None) -> dict[str, Any]:
        self.calls.append(("get_user_details_by_userkey", (userkey,), {"expand": expand}))
        return {"userKey": userkey, "displayName": "Test User"}

    def change_user_password(self, username: str, password: str) -> None:
        self.calls.append(("change_user_password", (username, password), {}))

    def add_user_to_group(self, username: str, group_name: str) -> None:
        self.calls.append(("add_user_to_group", (username, group_name), {}))

    def remove_user_from_group(self, username: str, group_name: str) -> None:
        self.calls.append(("remove_user_from_group", (username, group_name), {}))


def test_cli_group_list_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyGroupClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["group", "list", "--start", "0", "--limit", "100"])

    assert result.exit_code == 0
    assert "group1" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_all_groups"


def test_cli_group_list_with_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyGroupClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["group", "list", "--start", "10", "--limit", "50"])

    assert result.exit_code == 0
    assert client.calls[0][1] == (10, 50)


def test_cli_group_members_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyGroupClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["group", "members", "--group", "admins"])

    assert result.exit_code == 0
    assert "user1" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_group_members"


def test_cli_group_members_requires_group(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyGroupClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["group", "members"])

    assert result.exit_code != 0
    assert "--group required" in result.stdout or "--group required" in result.stderr


def test_cli_group_invalid_action(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyGroupClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["group", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr


def test_cli_user_get_by_username_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "get", "--username", "testuser"])

    assert result.exit_code == 0
    assert "testuser" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_user_details_by_username"


def test_cli_user_get_by_userkey_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "get", "--userkey", "key123"])

    assert result.exit_code == 0
    assert "key123" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "get_user_details_by_userkey"


def test_cli_user_get_with_expand(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "get", "--username", "testuser", "--expand", "status,details"])

    assert result.exit_code == 0
    assert client.calls[0][2]["expand"] == "status,details"


def test_cli_user_get_requires_username_or_userkey(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "get"])

    assert result.exit_code != 0
    assert "--username" in result.stdout or "--username" in result.stderr or "--userkey" in result.stdout


def test_cli_user_get_rejects_both_username_and_userkey(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "get", "--username", "testuser", "--userkey", "key123"])

    assert result.exit_code != 0
    assert "not both" in result.stdout or "not both" in result.stderr


def test_cli_user_password_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "password", "--username", "testuser", "--new-password", "newpass123", "--yes"])

    assert result.exit_code == 0
    assert "password_changed" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "change_user_password"


def test_cli_user_password_requires_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "password", "--username", "testuser", "--new-password", "newpass123"])

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr


def test_cli_user_password_requires_username(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "password", "--new-password", "newpass123", "--yes"])

    assert result.exit_code != 0
    assert "--username required" in result.stdout or "--username required" in result.stderr


def test_cli_user_password_requires_new_password(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "password", "--username", "testuser", "--yes"])

    assert result.exit_code != 0
    assert "--new-password required" in result.stdout or "--new-password required" in result.stderr


def test_cli_user_group_add_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "group-add", "--username", "testuser", "--group", "admins", "--yes"])

    assert result.exit_code == 0
    assert "added" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "add_user_to_group"


def test_cli_user_group_add_requires_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "group-add", "--username", "testuser", "--group", "admins"])

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr


def test_cli_user_group_add_requires_username(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "group-add", "--group", "admins", "--yes"])

    assert result.exit_code != 0
    assert "--username required" in result.stdout or "--username required" in result.stderr


def test_cli_user_group_add_requires_group(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "group-add", "--username", "testuser", "--yes"])

    assert result.exit_code != 0
    assert "--group required" in result.stdout or "--group required" in result.stderr


def test_cli_user_group_remove_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "group-remove", "--username", "testuser", "--group", "admins", "--yes"])

    assert result.exit_code == 0
    assert "removed" in result.stdout
    assert len(client.calls) == 1
    assert client.calls[0][0] == "remove_user_from_group"


def test_cli_user_group_remove_requires_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "group-remove", "--username", "testuser", "--group", "admins"])

    assert result.exit_code != 0
    assert "--yes required" in result.stdout or "--yes required" in result.stderr


def test_cli_user_invalid_action(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyUserClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda *args: client)

    result = runner.invoke(app, ["user", "invalid"])

    assert result.exit_code != 0
    assert "Unknown action" in result.stdout or "Unknown action" in result.stderr
