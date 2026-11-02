"""HTTP-status → VDSClientError mapper — TSK-7.4."""

from __future__ import annotations

from typing import Any

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    TransportError,
    VDSClientError,
)

_DEFAULT_MAP: dict[int, type[VDSClientError]] = {
    401: AuthError,
    403: ClientPermissionError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}
_SERVICE_MAP: dict[str, dict[int, type[VDSClientError]]] = {}


def register_http_error_mapping(service: str, status: int, error_cls: type[VDSClientError]) -> None:
    """Register a service-specific HTTP status → exception mapping (overrides defaults)."""
    _SERVICE_MAP.setdefault(service, {})[status] = error_cls


def map_http_error(status: int, body: Any, *, service: str | None = None) -> VDSClientError:
    """Convert HTTP *status* + *body* into a VDSClientError.

    Lookup order: service override → default map → 5xx → generic.
    """
    message = str(body)
    if service and (cls := _SERVICE_MAP.get(service, {}).get(status)):
        return cls(message)
    if cls := _DEFAULT_MAP.get(status):
        return cls(message)
    if 500 <= status < 600:
        return TransportError(message)
    return VDSClientError(message)


__all__ = ["map_http_error", "register_http_error_mapping"]
