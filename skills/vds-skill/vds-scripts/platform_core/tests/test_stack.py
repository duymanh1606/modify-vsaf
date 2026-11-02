"""Tests for platform_core.http.stack — TSK-7.18."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
from vds_platform_core.config import HTTPClientSettings
from vds_platform_core.http.stack import build_client, vds_default_stack
from vds_platform_core.protocols import HTTPClient


def _settings(**kw: Any) -> HTTPClientSettings:
    return HTTPClientSettings(**kw)


def _stub_httpx_client() -> MagicMock:
    """Plain MagicMock with get/post/aclose — satisfies HTTPClient Protocol.

    Intentionally no spec= so this works both inside and outside @patch contexts
    (patching httpx.AsyncClient replaces the class globally, making spec= fail).
    """
    stub = MagicMock()
    stub.get = MagicMock(return_value=None)
    stub.post = MagicMock(return_value=None)
    stub.aclose = MagicMock(return_value=None)
    return stub


class TestBuildClientProtocol:
    @patch("vds_platform_core.http.stack.httpx.AsyncClient")
    def test_returns_http_client_protocol(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _stub_httpx_client()
        result = build_client(settings=_settings(), service="svc", base_url="http://api", token_field="TOKEN")
        assert isinstance(result, HTTPClient)

    @patch("vds_platform_core.http.stack.httpx.AsyncClient")
    def test_service_param_accepted_without_error(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _stub_httpx_client()
        # service is reserved for future error-map registry — must not raise
        build_client(settings=_settings(), service="my-service", base_url="http://x", token_field="TOK")


class TestBuildClientTimeouts:
    def test_timeouts_flow_to_httpx(self) -> None:
        captured: dict[str, Any] = {}
        original_init = httpx.AsyncClient.__init__

        def tracking_init(self: Any, **kwargs: Any) -> None:
            captured.update(kwargs)
            original_init(self, **kwargs)

        s = _settings(connect_timeout=1.0, read_timeout=2.0, write_timeout=3.0, pool_timeout=4.0)
        with patch.object(httpx.AsyncClient, "__init__", tracking_init):
            build_client(settings=s, service="svc", base_url="http://api", token_field="TOK")

        t: httpx.Timeout = captured["timeout"]
        assert t.connect == 1.0
        assert t.read == 2.0
        assert t.write == 3.0
        assert t.pool == 4.0


class TestBuildClientHeaderName:
    @patch("vds_platform_core.http.stack.httpx.AsyncClient")
    def test_default_header_name_is_authorization(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _stub_httpx_client()
        client = build_client(settings=_settings(), service="svc", base_url="http://api", token_field="TOKEN")
        # unwrap auth wrapper → _header_name attribute set by with_auth
        assert client._header_name == "Authorization"  # type: ignore[attr-defined]

    @patch("vds_platform_core.http.stack.httpx.AsyncClient")
    def test_custom_header_name_propagates(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _stub_httpx_client()
        client = build_client(
            settings=_settings(),
            service="svc",
            base_url="http://api",
            token_field="TOKEN",
            header_name="X-Api-Key",
        )
        assert client._header_name == "X-Api-Key"  # type: ignore[attr-defined]


class TestExtraMiddleware:
    @patch("vds_platform_core.http.stack.httpx.AsyncClient")
    def test_extra_middleware_fifo_order(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _stub_httpx_client()
        applied: list[int] = []

        def mw1(c: HTTPClient) -> HTTPClient:
            applied.append(1)
            return c

        def mw2(c: HTTPClient) -> HTTPClient:
            applied.append(2)
            return c

        build_client(
            settings=_settings(),
            service="svc",
            base_url="http://api",
            token_field="TOKEN",
            extra_middleware=(mw1, mw2),
        )
        assert applied == [1, 2]

    @patch("vds_platform_core.http.stack.httpx.AsyncClient")
    def test_no_extra_middleware_works(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _stub_httpx_client()
        result = build_client(settings=_settings(), service="svc", base_url="http://api", token_field="TOKEN")
        assert isinstance(result, HTTPClient)


class TestVdsDefaultStack:
    def test_wraps_client_satisfying_protocol(self) -> None:
        from vds_platform_core.credentials import HeaderAuthResolver
        from vds_platform_core.http.retry import exponential_backoff

        stub = _stub_httpx_client()
        resolver = HeaderAuthResolver(token_field="TOK", header_name="Authorization")
        policy = exponential_backoff()
        result = vds_default_stack(
            stub,  # type: ignore[arg-type]
            resolver=resolver,
            retry_policy=policy,
            service="test",
        )
        assert isinstance(result, HTTPClient)
