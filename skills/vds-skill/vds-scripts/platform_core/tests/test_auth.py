"""Tests for vds_platform_core.http.auth — TSK-7.3b."""

from __future__ import annotations

import asyncio
from typing import Any

from vds_platform_core.http.auth import with_auth
from vds_platform_core.protocols import HTTPClient


class _StubClient:
    def __init__(self) -> None:
        self.last_get_kw: dict[str, Any] = {}
        self.last_post_kw: dict[str, Any] = {}
        self.closed = False

    async def get(self, url: str, **kw: Any) -> dict[str, Any]:
        self.last_get_kw = kw
        return {}

    async def post(self, url: str, **kw: Any) -> dict[str, Any]:
        self.last_post_kw = kw
        return {}

    async def aclose(self) -> None:
        self.closed = True


class _TokenResolver:
    def __init__(self, token: str | None) -> None:
        self._token = token

    def resolve(self) -> str | None:
        return self._token


def test_with_auth_returns_http_client() -> None:
    """with_auth result satisfies the HTTPClient protocol."""
    assert isinstance(with_auth(_StubClient(), _TokenResolver("tok")), HTTPClient)


def test_with_auth_injects_default_authorization_header() -> None:
    """Token injected into Authorization header on GET by default."""
    stub = _StubClient()
    asyncio.run(with_auth(stub, _TokenResolver("Bearer abc")).get("https://x.com"))
    assert stub.last_get_kw["headers"]["Authorization"] == "Bearer abc"


def test_with_auth_uses_custom_header_name() -> None:
    """custom header_name is used instead of Authorization."""
    stub = _StubClient()
    asyncio.run(with_auth(stub, _TokenResolver("tok"), header_name="X-API-Key").get("https://x.com"))
    assert stub.last_get_kw["headers"]["X-API-Key"] == "tok"


def test_with_auth_none_resolver_skips_injection() -> None:
    """When resolver returns None, no header is injected."""
    stub = _StubClient()
    asyncio.run(with_auth(stub, _TokenResolver(None)).get("https://x.com"))
    assert "Authorization" not in stub.last_get_kw.get("headers", {})


def test_with_auth_does_not_overwrite_existing_header() -> None:
    """User-supplied Authorization header is preserved (setdefault semantics)."""
    stub = _StubClient()
    asyncio.run(
        with_auth(stub, _TokenResolver("server-token")).get("https://x.com", headers={"Authorization": "user-token"})
    )
    assert stub.last_get_kw["headers"]["Authorization"] == "user-token"


def test_with_auth_delegates_aclose() -> None:
    """aclose() is forwarded to the underlying client."""
    stub = _StubClient()
    asyncio.run(with_auth(stub, _TokenResolver("tok")).aclose())
    assert stub.closed is True


def test_with_auth_injects_on_post() -> None:
    """Header is also injected on POST requests."""
    stub = _StubClient()
    asyncio.run(with_auth(stub, _TokenResolver("tok")).post("https://x.com", json={"a": 1}))
    assert stub.last_post_kw["headers"]["Authorization"] == "tok"
