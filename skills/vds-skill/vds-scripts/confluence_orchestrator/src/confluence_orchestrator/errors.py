"""Confluence error types — re-exports from vds_platform_core with service tag."""

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ClientTimeoutError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    RetryError,
    SettingsError,
    TransportError,
    VDSClientError,
    VDSError,
)

SERVICE_NAME = "confluence"


class ConfluenceDegradedWriteError(VDSClientError):
    """Raised when a write operation is blocked in degraded (read-only) mode."""

    def __init__(self, operation: str) -> None:
        super().__init__(f"Write blocked in degraded mode: {operation}")
        self.operation = operation


__all__ = [
    "SERVICE_NAME",
    "AuthError",
    "ClientPermissionError",
    "ClientTimeoutError",
    "ConflictError",
    "ConfluenceDegradedWriteError",
    "NotFoundError",
    "RateLimitError",
    "ResponseError",
    "RetryError",
    "SettingsError",
    "TransportError",
    "VDSClientError",
    "VDSError",
]
