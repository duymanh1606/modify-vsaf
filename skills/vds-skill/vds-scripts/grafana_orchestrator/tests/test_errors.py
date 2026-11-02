"""Tests for vds_grafana_orchestrator error re-exports from vds_platform_core."""

from __future__ import annotations

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
    NotFoundError as PlatformNotFoundError,
)
from vds_platform_core.errors import (
    RateLimitError as PlatformRateLimitError,
)
from vds_platform_core.errors import (
    ResponseError as PlatformResponseError,
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

from vds_grafana_orchestrator.errors import (
    SERVICE_NAME,
    AuthError,
    ClientPermissionError,
    ClientTimeoutError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    RetryError,
    TransportError,
    VDSClientError,
)


def test_service_name() -> None:
    assert SERVICE_NAME == "grafana"


def test_re_exports_are_platform_core_classes() -> None:
    assert AuthError is PlatformAuthError
    assert VDSClientError is PlatformVDSClientError
    assert RateLimitError is PlatformRateLimitError
    assert NotFoundError is PlatformNotFoundError
    assert ResponseError is PlatformResponseError
    assert RetryError is PlatformRetryError
    assert TransportError is PlatformTransportError
    assert ClientPermissionError is PlatformPermissionError
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
    error = VDSClientError("test", context={"service": "grafana"})
    assert error.context == {"service": "grafana"}
    assert "test" in str(error)
