"""VDS platform error hierarchy.

Provides a structured exception tree rooted at VDSError(RuntimeError) so that
all platform exceptions are distinguishable from stdlib exceptions and from each
other, while remaining catchable via a single VDSError guard.

Hierarchy::

    RuntimeError
    └── VDSError                     (base; carries optional context dict)
        ├── VDSClientError           (remote / SDK operation errors)
        │   ├── AuthError
        │   ├── ClientPermissionError (NOT PermissionError)
        │   ├── TransportError
        │   │   └── ClientTimeoutError (NOT TimeoutError)
        │   ├── RetryError
        │   ├── ResponseError
        │   ├── NotFoundError
        │   ├── RateLimitError
        │   └── ConflictError
        └── SettingsError            (local config / env errors)
"""

from __future__ import annotations

from typing import Any


class VDSError(RuntimeError):
    """Root of the VDS exception hierarchy.

    Args:
        message: Human-readable error description.
        context: Optional structured diagnostic payload (repo name, attempt
            count, HTTP status, etc.).  Stored as ``self.context``.
        **kwargs: Forwarded to ``RuntimeError.__init__`` for cooperative MRO
            compatibility (required when VDSError participates in diamond
            inheritance).
    """

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.context: dict[str, Any] = context or {}


# ---------------------------------------------------------------------------
# Client errors — remote / SDK operation failures
# ---------------------------------------------------------------------------


class VDSClientError(VDSError):
    """Base for all errors originating from remote calls or SDK operations."""


class AuthError(VDSClientError):
    """Authentication failure (invalid credentials, expired token, etc.)."""


class ClientPermissionError(VDSClientError):
    """Authorisation failure — caller lacks permission for the operation.

    Named ``ClientPermissionError`` rather than ``PermissionError`` to avoid
    shadowing the stdlib built-in.
    """


class TransportError(VDSClientError):
    """Network / transport-layer failure (connection refused, DNS error, etc.)."""


class ClientTimeoutError(TransportError):
    """Request exceeded its deadline.

    Named ``ClientTimeoutError`` rather than ``TimeoutError`` to avoid
    shadowing the stdlib built-in.
    """


class RetryError(VDSClientError):
    """All retry attempts exhausted without a successful response."""


class ResponseError(VDSClientError):
    """Server returned an unexpected or malformed response."""


class NotFoundError(VDSClientError):
    """Requested resource does not exist on the remote."""


class RateLimitError(VDSClientError):
    """Rate limit / quota exceeded on the remote API."""


class ConflictError(VDSClientError):
    """Operation conflicts with the current state of the remote resource."""


# ---------------------------------------------------------------------------
# Settings errors — local configuration / environment failures
# ---------------------------------------------------------------------------


class SettingsError(VDSError):
    """Configuration or environment setup error (missing env var, bad config file, etc.)."""


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
]
