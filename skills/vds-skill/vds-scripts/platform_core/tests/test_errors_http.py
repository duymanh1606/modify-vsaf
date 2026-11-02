"""Tests for vds_platform_core.http.errors — TSK-7.4."""

from __future__ import annotations

import pytest
import vds_platform_core.http.errors as _err_mod
from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    TransportError,
    VDSClientError,
)
from vds_platform_core.http.errors import map_http_error, register_http_error_mapping


@pytest.fixture(autouse=True)
def _reset_service_map() -> None:
    """Isolate _SERVICE_MAP between tests."""
    _err_mod._SERVICE_MAP.clear()


def test_map_401_returns_auth_error() -> None:
    assert isinstance(map_http_error(401, "Unauthorized"), AuthError)


def test_map_403_returns_permission_error() -> None:
    assert isinstance(map_http_error(403, "Forbidden"), ClientPermissionError)


def test_map_404_returns_not_found_error() -> None:
    assert isinstance(map_http_error(404, "Not Found"), NotFoundError)


def test_map_409_returns_conflict_error() -> None:
    assert isinstance(map_http_error(409, "Conflict"), ConflictError)


def test_map_429_returns_rate_limit_error() -> None:
    assert isinstance(map_http_error(429, "Too Many Requests"), RateLimitError)


def test_map_500_returns_transport_error() -> None:
    assert isinstance(map_http_error(500, "Internal Server Error"), TransportError)


def test_map_503_returns_transport_error() -> None:
    """All 5xx statuses map to TransportError."""
    assert isinstance(map_http_error(503, "Service Unavailable"), TransportError)


def test_map_unknown_status_returns_vds_client_error() -> None:
    """Unmapped statuses fall back to generic VDSClientError."""
    err = map_http_error(418, "I'm a teapot")
    assert type(err) is VDSClientError


def test_service_override_beats_default() -> None:
    """A registered service override takes precedence over the default map."""
    register_http_error_mapping("my-service", 404, TransportError)
    assert isinstance(map_http_error(404, "not found", service="my-service"), TransportError)


def test_service_override_does_not_affect_other_services() -> None:
    """A service-specific override does not leak to other services."""
    register_http_error_mapping("svc-a", 404, ConflictError)
    assert isinstance(map_http_error(404, "not found", service="svc-b"), NotFoundError)


def test_error_body_stored_in_message() -> None:
    """The response body is surfaced in the exception message."""
    assert "token expired" in str(map_http_error(401, "token expired"))
