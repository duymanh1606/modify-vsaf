"""Shared protocols for cross-orchestrator interoperability (Phase 4, FR-P4).

Defines ``SyncableRepo`` — a structural protocol that both ``RepoSpec``
(sync_orchestrator) and ``RepoInfo`` (audit_orchestrator) satisfy, allowing
the execution layer to accept repositories from either source without
coupling to their concrete types.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SyncableRepo(Protocol):
    """Structural contract for a repository that can be synced.

    Any object exposing these five read-only properties satisfies the
    protocol — no explicit inheritance required.
    """

    @property
    def name(self) -> str: ...

    @property
    def project(self) -> str: ...

    @property
    def branch(self) -> str: ...

    @property
    def url(self) -> str | None: ...

    @property
    def sync_metadata(self) -> dict[str, Any]: ...
