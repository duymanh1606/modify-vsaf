"""One rejected login, one fallback, and never a third attempt.

Why this file exists: on Bitbucket Server, ``Bitbucket(url, token=<PAT>)`` answers
401 Authentication failed while ``Bitbucket(url, username=..., password=<PAT>)`` lists
every repo of the project. ``get_auth_kwargs`` always handed over the first shape, so
every ``vds-cli bitbucket`` command spent a failed login and returned nothing — and a
handful of those locks the account. So the order is pinned here, and so is the ceiling:
the client must never try a third time, because retrying is what locks accounts.

Everything here is mocked. Nothing in this file may reach a Bitbucket server.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import AuthError

from .conftest import clear_runtime_env

TOKEN = "pat-not-a-real-token"
USER = "someone"
UNAUTHORIZED = "401 Unauthorized: Authentication failed"


def server_settings(monkeypatch: pytest.MonkeyPatch, *, user: str | None = USER) -> BitbucketSettings:
    """Server-mode settings, with the ambient environment kept out of the way."""
    clear_runtime_env(monkeypatch)
    return BitbucketSettings(
        VDS_USERNAME=user,
        VDS_PASSWORD=None,
        BITBUCKET_TOKEN=TOKEN,
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


def refusing(**methods: Any) -> Mock:
    """A stand-in atlassian client whose named methods answer 401."""
    client = Mock()
    for name in methods:
        getattr(client, name).side_effect = Exception(UNAUTHORIZED)
    return client


class TestAuthAttempts:
    """The order, and the fact that there are only ever two of them."""

    def test_server_tries_the_shape_the_server_accepts_first(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Server nhận basic-auth với token, nên nó đứng đầu — 0 lần đăng nhập hỏng.

        Trước đây Bearer đứng đầu cho mọi chế độ, nên mỗi lệnh chạm Server tốn đúng một
        lần hỏng, và một lần đã đủ khoá tài khoản thật.
        """
        attempts = server_settings(monkeypatch).auth_attempts()

        assert attempts == [
            {"username": USER, "password": TOKEN},
            {"token": TOKEN},
        ]

    def test_stops_at_two_so_a_wrong_credential_costs_two_logins_at_most(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clear_runtime_env(monkeypatch)
        # A password configured beside a token is deliberately not a third attempt.
        settings = BitbucketSettings(VDS_USERNAME=USER, VDS_PASSWORD="pw", BITBUCKET_TOKEN=TOKEN)

        assert len(settings.auth_attempts()) == 2

    def test_a_token_with_nobody_to_be_has_no_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Basic auth needs a username. Inventing one would be a login attempt spent on a guess.
        settings = server_settings(monkeypatch, user=None)

        assert settings.auth_attempts() == [{"token": TOKEN}]

    def test_basic_auth_alone_stays_one_attempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clear_runtime_env(monkeypatch)
        settings = BitbucketSettings(VDS_USERNAME=USER, VDS_PASSWORD="pw", BITBUCKET_TOKEN=None)

        assert settings.auth_attempts() == [{"username": USER, "password": "pw"}]

    def test_no_credentials_at_all_still_refuses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clear_runtime_env(monkeypatch)
        settings = BitbucketSettings(VDS_USERNAME=None, VDS_PASSWORD=None, BITBUCKET_TOKEN=None)

        with pytest.raises(ValueError, match="No valid authentication credentials"):
            settings.auth_attempts()

    def test_get_auth_kwargs_is_the_first_attempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = server_settings(monkeypatch)

        assert settings.get_auth_kwargs() == settings.auth_attempts()[0]


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
class TestClientFallsBackOnce:
    """What the client does with the two attempts."""

    def test_a_401_is_retried_with_basic_auth_and_succeeds(
        self, atlassian: Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Ở chế độ Server, lần đầu là basic; đường lùi là Bearer. Test này kiểm cơ chế
        # lùi vẫn chạy khi lần đầu bị từ chối — bất kể lần đầu là dạng nào.
        first = refusing(repo_list=True)
        second = Mock()
        second.repo_list.return_value = [{"slug": "map-core"}]
        atlassian.side_effect = [first, second]

        client = BitbucketClient(server_settings(monkeypatch))

        assert client.list_repositories("MAP") == [{"slug": "map-core"}]
        assert atlassian.call_count == 2
        # Lần đầu: basic với token làm password — dạng máy chủ Server nhận.
        assert atlassian.call_args_list[0].kwargs["username"] == USER
        assert atlassian.call_args_list[0].kwargs["password"] == TOKEN
        assert "token" not in atlassian.call_args_list[0].kwargs
        # Lần lùi: Bearer.
        assert atlassian.call_args_list[1].kwargs["token"] == TOKEN

    def test_a_401_from_a_generator_is_caught_too(self, atlassian: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
        """The paginated calls only send their request once someone iterates them."""

        def refused() -> Any:
            raise Exception(UNAUTHORIZED)
            yield  # pragma: no cover - unreachable, present to make this a generator

        bearer = Mock()
        bearer.project_list.return_value = refused()
        basic = Mock()
        basic.project_list.return_value = [{"key": "MAP"}]
        atlassian.side_effect = [bearer, basic]

        client = BitbucketClient(server_settings(monkeypatch))

        assert client.list_projects() == [{"key": "MAP"}]
        assert atlassian.call_count == 2

    def test_two_refusals_stop_there_and_never_become_a_loop(
        self, atlassian: Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        atlassian.side_effect = [refusing(repo_list=True), refusing(repo_list=True)]

        client = BitbucketClient(server_settings(monkeypatch))

        with pytest.raises(AuthError):
            client.list_repositories("MAP")
        assert atlassian.call_count == 2

        # And the next command does not start the walk over again: two logins is the
        # ceiling for the whole process, not per call. This is the assertion that keeps
        # the account unlocked.
        with pytest.raises(AuthError):
            client.list_repositories("MAP")
        assert atlassian.call_count == 2

    def test_a_403_does_not_spend_the_fallback(self, atlassian: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
        # A 403 comes from a server that accepted the login and is talking about
        # permissions. A second login attempt there buys nothing and costs one.
        forbidden = Mock()
        forbidden.repo_list.side_effect = Exception("403 Forbidden")
        atlassian.side_effect = [forbidden, Mock()]

        client = BitbucketClient(server_settings(monkeypatch))

        with pytest.raises(AuthError):
            client.list_repositories("MAP")
        assert atlassian.call_count == 1

    def test_a_working_token_is_left_alone(self, atlassian: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
        # Bitbucket Cloud accepts the Bearer token, and nothing here may push it off it.
        bearer = Mock()
        bearer.repo_list.return_value = [{"slug": "map-core"}]
        atlassian.side_effect = [bearer, Mock()]

        client = BitbucketClient(server_settings(monkeypatch))

        assert client.list_repositories("MAP") == [{"slug": "map-core"}]
        assert atlassian.call_count == 1

    def test_a_missing_method_is_still_missing(self, atlassian: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
        # client.py asks `hasattr(self._client, "merge_pull_request")`, so the wrapper has
        # to keep answering that question about the real client rather than about itself.
        inner = Mock(spec=["repo_list"])
        atlassian.side_effect = [inner]

        client = BitbucketClient(server_settings(monkeypatch))

        assert hasattr(client._client, "repo_list")
        assert not hasattr(client._client, "khong_co_ham_nay")


# ── Thứ tự thử theo chế độ ──────────────────────────────────────────────────────
#
# Đây là phần đắt nhất của cả tính năng này: mỗi lần thử bị từ chối là một lần đăng
# nhập hỏng, và máy chủ Server khoá tài khoản sau rất ít lần — một lần đã đủ, hai
# lượt riêng biệt trên tài khoản thật. Đặt Bearer trước cho mọi chế độ nghĩa là mọi
# lệnh chạm Server đều tốn đúng một lần hỏng, kể cả khi đã có đường lùi.


def _settings(mode: str) -> BitbucketSettings:
    return BitbucketSettings(
        BITBUCKET_TOKEN="tok",
        VDS_USERNAME="user",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE=mode,
    )


def test_server_mode_tries_basic_first_so_nothing_is_rejected() -> None:
    """Server chấp nhận basic-auth với token; thử nó trước là 0 lần đăng nhập hỏng."""
    attempts = _settings("server").auth_attempts()
    assert attempts[0] == {"username": "user", "password": "tok"}
    assert attempts[1] == {"token": "tok"}


def test_cloud_mode_tries_bearer_first() -> None:
    """Cloud nhận Bearer — dạng có tài liệu — nên nó đứng trước ở chế độ này."""
    attempts = _settings("cloud").auth_attempts()
    assert attempts[0] == {"token": "tok"}
    assert attempts[1] == {"username": "user", "password": "tok"}


def test_get_auth_kwargs_follows_the_mode() -> None:
    """Đường gọi một-lần cũng phải nhận dạng đúng, không chỉ auth_attempts."""
    assert _settings("server").get_auth_kwargs() == {"username": "user", "password": "tok"}
    assert _settings("cloud").get_auth_kwargs() == {"token": "tok"}


def test_never_more_than_two_attempts() -> None:
    """Trần hai lần là chốt an toàn, không phải chi tiết cài đặt."""
    for mode in ("server", "cloud"):
        assert len(_settings(mode).auth_attempts()) == 2


def test_no_username_means_bearer_only() -> None:
    """Không có username thì không có dạng basic nào để thử — kể cả ở Server."""
    only = BitbucketSettings(
        BITBUCKET_TOKEN="tok", VDS_USERNAME=None,
        BITBUCKET_BASE_URL="https://bitbucket.test.com", BITBUCKET_MODE="server",
    ).auth_attempts()
    assert only == [{"token": "tok"}]
