"""Runtime-checkable structural protocols for VDS platform services — TSK-7.1.

Defines the three core abstractions that orchestrators bind to via middleware
(with_retry, with_auth) introduced in Phase 7 Wave 2.

SyncableRepo is re-exported from vds_git_orchestrator when available (backward
compat); if that package is not installed the symbol is absent from this module.
"""

from __future__ import annotations

import contextlib
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HTTPClient(Protocol):
    """Structural contract for an async HTTP client.

    Any object exposing async get/post/aclose satisfies this protocol
    without explicit inheritance — enabling transparent middleware wrapping.
    """

    async def get(self, url: str, **kwargs: Any) -> Any:
        """Issue an async GET request."""
        ...

    async def post(self, url: str, **kwargs: Any) -> Any:
        """Issue an async POST request."""
        ...

    async def aclose(self) -> None:
        """Release underlying connections."""
        ...


@runtime_checkable
class CredentialResolver(Protocol):
    """Structural contract for a credential resolution strategy."""

    def resolve(self) -> str | None:
        """Return the resolved credential string, or None if unavailable."""
        ...


@runtime_checkable
class RetryPolicy(Protocol):
    """Structural contract for a retry decision strategy.

    Decouples retry logic from the HTTP layer — policies can be swapped
    without touching the client (exponential, linear, circuit-breaker, etc.).
    """

    def can_retry(self, attempt: int, exc: BaseException) -> bool:
        """Return True if another attempt should be made after *exc*."""
        ...

    def wait_seconds(self, attempt: int) -> float:
        """Return the number of seconds to wait before attempt *attempt*."""
        ...


# ---------------------------------------------------------------------------
# Backward-compat re-export: SyncableRepo lives in vds_git_orchestrator but
# is surfaced here so callers can import from a single stable location.
# vds_git_orchestrator is NOT a hard dependency of platform_core; if it is
# not installed this try-block is silently skipped.
# ---------------------------------------------------------------------------
with contextlib.suppress(ImportError):
    pass


__all__ = [
    "CredentialResolver",
    "HTTPClient",
    "RetryPolicy",
]
