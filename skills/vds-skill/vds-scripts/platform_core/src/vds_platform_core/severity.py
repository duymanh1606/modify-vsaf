"""VDS error severity and recoverability registry.

Provides:
- ``ErrorSeverity`` — StrEnum with CRITICAL / HIGH / MEDIUM / LOW levels.
- ``ErrorRecoverability`` — StrEnum with 5-value recovery strategy taxonomy,
  derived from production patterns across audit, sync, and provider failure
  classification subsystems.
- ``ErrorCodeMeta`` — frozen generic dataclass associating a code string with
  severity, recoverability, and a human description.
- ``ErrorCodeRegistry`` — prefix-scoped store for ``ErrorCodeMeta`` instances,
  supporting register / lookup / enumerate operations.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ErrorSeverity(StrEnum):
    """Operational severity levels for VDS errors."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ErrorRecoverability(StrEnum):
    """Categorizes error recovery strategy.

    Derived from production patterns across audit (3-value), sync (boolean),
    and provider failure classification (6-value). See research RQ-severity-2026-04-16.

    Mapping to existing taxonomies:

    * audit ``RETRYABLE``                     → ``TRANSIENT``
    * audit ``MANUAL``                        → ``MANUAL``
    * audit ``NON_RECOVERABLE``               → ``PERMANENT``
    * sync ``recoverable=True``               → ``TRANSIENT`` or ``RATE_LIMITED``
    * sync ``recoverable=False``              → ``PERMANENT``
    * provider ``RETRYABLE_TRANSIENT``        → ``TRANSIENT``
    * provider ``QUOTA_OR_CAPACITY``          → ``RATE_LIMITED``
    * provider ``PROVIDER_DEGRADED``          → ``DEGRADED``
    * provider ``ROUTE_PROVIDER_UNAVAILABLE`` → ``DEGRADED``
    * provider ``TERMINAL_AUTH``              → ``PERMANENT``
    * provider ``NON_PROVIDER_BUG``           → ``PERMANENT``
    """

    TRANSIENT = "transient"
    """Immediate retry likely to succeed (network timeout, 503)."""

    RATE_LIMITED = "rate_limited"
    """Wait then retry (429, quota exhaustion, Retry-After header)."""

    DEGRADED = "degraded"
    """Continue with reduced functionality or failover to alternate provider."""

    MANUAL = "manual"
    """Human intervention required (config error, missing resource, permission)."""

    PERMANENT = "permanent"
    """Cannot recover regardless of retry or intervention (401, validation failure)."""


# ---------------------------------------------------------------------------
# Generic type variables
# ---------------------------------------------------------------------------

S = TypeVar("S", bound=StrEnum)
R = TypeVar("R", bound=StrEnum)


# ---------------------------------------------------------------------------
# ErrorCodeMeta
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorCodeMeta[S: StrEnum, R: StrEnum]:
    """Immutable metadata for a single error code.

    Args:
        code: Unique error code string (e.g. ``"CLI-001"``).
        description: Human-readable description of the error condition.
        severity: Operational impact level.
        recoverability: Whether the condition is expected to self-resolve.
    """

    code: str
    description: str
    severity: S  # type: ignore[misc]
    recoverability: R  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ErrorCodeRegistry
# ---------------------------------------------------------------------------


class ErrorCodeRegistry[S: StrEnum, R: StrEnum]:
    """Prefix-scoped registry for :class:`ErrorCodeMeta` instances.

    Error codes are grouped by *prefix* (e.g. ``"CLI"``, ``"SONAR"``).
    Within a prefix, code strings must be unique.

    Example::

        registry = ErrorCodeRegistry()
        registry.register(
            "CLI",
            ErrorCodeMeta("CLI-001", "Config missing", ErrorSeverity.HIGH, ErrorRecoverability.PERMANENT),
        )
        meta = registry.lookup("CLI-001")
    """

    def __init__(self) -> None:
        # Map: prefix → {code → ErrorCodeMeta}
        self._store: dict[str, dict[str, ErrorCodeMeta[S, R]]] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, prefix: str, meta: ErrorCodeMeta[S, R]) -> None:
        """Register *meta* under *prefix*.

        Raises:
            ValueError: If a ``meta`` with the same ``code`` already exists
                under *prefix*.
        """
        bucket = self._store.setdefault(prefix, {})
        if meta.code in bucket:
            raise ValueError(
                f"Error code {meta.code!r} is already registered under prefix {prefix!r}. "
                "Use a unique code or remove the existing registration first."
            )
        bucket[meta.code] = meta

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def lookup(self, code: str) -> ErrorCodeMeta[S, R] | None:
        """Return the ``ErrorCodeMeta`` for *code*, or ``None`` if not found."""
        for bucket in self._store.values():
            if code in bucket:
                return bucket[code]
        return None

    def all_codes(self, *, prefix: str | None = None) -> Iterator[ErrorCodeMeta[S, R]]:
        """Yield all registered ``ErrorCodeMeta`` instances.

        Args:
            prefix: When supplied, restrict results to that prefix only.
        """
        if prefix is not None:
            yield from self._store.get(prefix, {}).values()
        else:
            for bucket in self._store.values():
                yield from bucket.values()


__all__ = [
    "ErrorCodeMeta",
    "ErrorCodeRegistry",
    "ErrorRecoverability",
    "ErrorSeverity",
]
