"""Tests for async_client.py — platform_core-composed Confluence HTTP client."""

from __future__ import annotations

import pytest
from confluence_orchestrator.async_client import SERVICE_NAME, build_confluence_client
from vds_platform_core.errors import AuthError, ClientPermissionError, ConflictError, NotFoundError, RateLimitError
from vds_platform_core.http.errors import map_http_error
from vds_platform_core.protocols import HTTPClient


def _make_settings(**overrides):
    """Return a minimal ConfluenceSettings suitable for unit tests."""
    from confluence_orchestrator.config import ConfluenceSettings

    return ConfluenceSettings(
        **{
            "VDS_USERNAME": "test",
            "VDS_PASSWORD": "test_pass",
            "INTERNAL_CONFLUENCE_TOKEN": "internal_tok",
            "EXTERNAL_CONFLUENCE_TOKEN": "external_tok",
            **overrides,
        }
    )


# ---------------------------------------------------------------------------
# Error-mapping registration (side effect of module import)
# ---------------------------------------------------------------------------


def test_confluence_error_map_401_returns_auth_error() -> None:
    err = map_http_error(401, "Unauthorized", service=SERVICE_NAME)
    assert isinstance(err, AuthError)


def test_confluence_error_map_403_returns_permission_error() -> None:
    err = map_http_error(403, "Forbidden", service=SERVICE_NAME)
    assert isinstance(err, ClientPermissionError)


def test_confluence_error_map_404_returns_not_found() -> None:
    err = map_http_error(404, "Not found", service=SERVICE_NAME)
    assert isinstance(err, NotFoundError)


def test_confluence_error_map_409_returns_conflict_error() -> None:
    err = map_http_error(409, "Conflict", service=SERVICE_NAME)
    assert isinstance(err, ConflictError)


def test_confluence_error_map_429_returns_rate_limit_error() -> None:
    err = map_http_error(429, "Rate limited", service=SERVICE_NAME)
    assert isinstance(err, RateLimitError)


# ---------------------------------------------------------------------------
# build_confluence_client factory
# ---------------------------------------------------------------------------


def test_build_confluence_client_returns_http_client_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_CONFLUENCE_TOKEN", "tok")
    settings = _make_settings()
    client = build_confluence_client(settings, server="internal")
    assert isinstance(client, HTTPClient)


def test_build_confluence_client_external_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXTERNAL_CONFLUENCE_TOKEN", "ext_tok")
    settings = _make_settings()
    client = build_confluence_client(settings, server="external")
    assert isinstance(client, HTTPClient)


def test_build_confluence_client_defaults_to_settings_default_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_CONFLUENCE_TOKEN", "tok")
    settings = _make_settings()
    # default_server is "internal"
    assert settings.default_server == "internal"
    client = build_confluence_client(settings)
    assert isinstance(client, HTTPClient)


def test_build_confluence_client_unknown_server_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _make_settings()
    with pytest.raises(ValueError, match="Unknown Confluence server alias 'bogus'"):
        build_confluence_client(settings, server="bogus")


@pytest.mark.parametrize("alias", ["int", "main"])
def test_build_confluence_client_accepts_internal_aliases(alias: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_CONFLUENCE_TOKEN", "tok")
    settings = _make_settings()
    client = build_confluence_client(settings, server=alias)
    assert isinstance(client, HTTPClient)


@pytest.mark.parametrize("alias", ["ext", "outsource"])
def test_build_confluence_client_accepts_external_aliases(alias: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXTERNAL_CONFLUENCE_TOKEN", "ext_tok")
    settings = _make_settings()
    client = build_confluence_client(settings, server=alias)
    assert isinstance(client, HTTPClient)
