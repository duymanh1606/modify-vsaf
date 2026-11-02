"""Elastic error types — re-exports from vds_platform_core with service tag."""

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

SERVICE_NAME = "elastic"

__all__ = [
    "AuthError",
    "ClientPermissionError",
    "ClientTimeoutError",
    "ConflictError",
    "NotFoundError",
    "RateLimitError",
    "ResponseError",
    "RetryError",
    "SettingsError",
    "TransportError",
    "VDSClientError",
    "VDSError",
    "SERVICE_NAME",
]
