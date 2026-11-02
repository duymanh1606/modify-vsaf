"""Tests for confluence_orchestrator error re-exports from vds_platform_core."""

from __future__ import annotations

from confluence_orchestrator.errors import (
    SERVICE_NAME,
    AuthError,
    ClientPermissionError,
    ClientTimeoutError,
    ConfluenceDegradedWriteError,
    RateLimitError,
    RetryError,
    TransportError,
    VDSClientError,
)
from vds_platform_core.errors import (
    AuthError as PlatformAuthError,
)
from vds_platform_core.errors import (
    ClientPermissionError as PlatformPermissionError,
)
from vds_platform_core.errors import (
    ClientTimeoutError as PlatformTimeoutError,
)
from vds_platform_core.errors import (
    RateLimitError as PlatformRateLimitError,
)
from vds_platform_core.errors import (
    RetryError as PlatformRetryError,
)
from vds_platform_core.errors import (
    TransportError as PlatformTransportError,
)
from vds_platform_core.errors import (
    VDSClientError as PlatformVDSClientError,
)


def test_service_name() -> None:
    assert SERVICE_NAME == "confluence"


def test_re_exports_are_platform_core_classes() -> None:
    assert AuthError is PlatformAuthError
    assert VDSClientError is PlatformVDSClientError
    assert RateLimitError is PlatformRateLimitError
    assert RetryError is PlatformRetryError
    assert TransportError is PlatformTransportError
    assert ClientPermissionError is PlatformPermissionError
    assert ClientTimeoutError is PlatformTimeoutError


def test_errors_are_catchable_as_vds_client_error() -> None:
    errors = [AuthError("auth"), RateLimitError("rate"), RetryError("retry")]
    for error in errors:
        assert isinstance(error, VDSClientError)
        assert isinstance(error, RuntimeError)


def test_degraded_write_error_is_vds_client_error() -> None:
    error = ConfluenceDegradedWriteError("create_page My Title")
    assert isinstance(error, VDSClientError)
    assert isinstance(error, RuntimeError)
    assert "create_page" in str(error)


def test_timeout_inherits_transport() -> None:
    assert issubclass(ClientTimeoutError, TransportError)
    assert issubclass(TransportError, VDSClientError)


def test_error_instantiation_with_context() -> None:
    error = VDSClientError("test", context={"service": "confluence"})
    assert error.context == {"service": "confluence"}
    assert "test" in str(error)
