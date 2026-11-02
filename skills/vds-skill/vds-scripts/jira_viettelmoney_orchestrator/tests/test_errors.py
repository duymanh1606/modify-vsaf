"""Tests for vds_jira_orchestrator error re-exports from vds_platform_core."""

from __future__ import annotations

import pytest

from vds_platform_core.errors import (
    AuthError as PlatformAuthError,
    ClientTimeoutError as PlatformTimeoutError,
    ConflictError as PlatformConflictError,
    NotFoundError as PlatformNotFoundError,
    RateLimitError as PlatformRateLimitError,
    RetryError as PlatformRetryError,
    TransportError as PlatformTransportError,
    VDSClientError as PlatformVDSClientError,
)

from vds_jira_orchestrator.errors import (
    SERVICE_NAME,
    AuthError,
    ClientTimeoutError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    RetryError,
    TransportError,
    VDSClientError,
)


def test_service_name() -> None:
    assert SERVICE_NAME == "jira"


def test_re_exports_are_platform_core_classes() -> None:
    assert AuthError is PlatformAuthError
    assert VDSClientError is PlatformVDSClientError
    assert RateLimitError is PlatformRateLimitError
    assert NotFoundError is PlatformNotFoundError
    assert ConflictError is PlatformConflictError
    assert RetryError is PlatformRetryError
    assert TransportError is PlatformTransportError
    assert ClientTimeoutError is PlatformTimeoutError


def test_errors_are_catchable_as_vds_client_error() -> None:
    errors = [AuthError("auth"), RateLimitError("rate"), NotFoundError("nf")]
    for error in errors:
        assert isinstance(error, VDSClientError)
        assert isinstance(error, RuntimeError)


def test_timeout_inherits_transport() -> None:
    assert issubclass(ClientTimeoutError, TransportError)
    assert issubclass(TransportError, VDSClientError)


def test_error_instantiation_with_context() -> None:
    error = VDSClientError("test", context={"service": "jira"})
    assert error.context == {"service": "jira"}
    assert "test" in str(error)
