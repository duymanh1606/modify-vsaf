"""Canonical branch probing and resolution for VDS git operations.

Provides ``git ls-remote``-based branch discovery with auth injection,
a canonical branch candidate order, and typed result dataclasses.

Extracted from ``audit_orchestrator/sync/repo_sync.py`` lines 36-206.
Both ``audit_orchestrator`` and ``git_orchestrator/orchestrator.py`` import
from here instead of maintaining independent implementations.

Phase 4 — FR-P2, FR-P3 (TSK-P2.1).
"""

from __future__ import annotations

import asyncio
import os
from base64 import b64encode
from dataclasses import dataclass, field
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Canonical branch candidate order (FR-P3)
# ---------------------------------------------------------------------------

#: Modern convention: ``main`` first, matching GitHub/Bitbucket Cloud defaults.
#: Replaces the 3-way inconsistency across git/sync/audit orchestrators.
#: When ``VDS_SYNC_BRANCH_ORDER=legacy`` is set, consumers should fall back to
#: their pre-Phase-4 per-package ordering (see ``get_branch_candidates()``).
BRANCH_CANDIDATES: tuple[str, ...] = ("main", "release", "master", "staging")

#: Pre-Phase-4 ordering used by ``git_orchestrator/orchestrator.py``.
_LEGACY_GIT_ORCHESTRATOR_ORDER: tuple[str, ...] = ("release", "master", "main", "staging")


def get_branch_candidates() -> tuple[str, ...]:
    """Return the active branch candidate order.

    Respects ``VDS_SYNC_BRANCH_ORDER=legacy`` for rollback during the
    transition period (FR-P3).  When ``legacy`` is set, returns the
    pre-Phase-4 git_orchestrator ordering.
    """
    if os.environ.get("VDS_SYNC_BRANCH_ORDER", "").strip().lower() == "legacy":
        return _LEGACY_GIT_ORCHESTRATOR_ORDER
    return BRANCH_CANDIDATES


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchProbeResult:
    """Result of probing a remote for known branch candidates."""

    deterministic: bool
    available_branches: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class BranchHintResult:
    """Result of broad branch discovery via ``git ls-remote --symref``."""

    deterministic: bool
    default_branch: str | None = None
    discovered_branches: list[str] = field(default_factory=list)
    discovered_branch_count: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Supported remote schemes
# ---------------------------------------------------------------------------

_ALLOWED_SCHEMES = frozenset({"http", "https", "ssh", "git"})

# ---------------------------------------------------------------------------
# Auth injection
# ---------------------------------------------------------------------------


def _build_ls_remote_command(
    *,
    remote_url: str,
    branch_candidates: tuple[str, ...] | None = None,
    include_symref: bool = False,
) -> list[str]:
    """Build a ``git ls-remote`` command with optional basic-auth injection.

    Auth is injected when **both** ``VDS_USERNAME`` and ``VDS_PASSWORD``
    environment variables are present.  If only one is set, auth is skipped
    (partial credentials are never sent).
    """
    command: list[str] = ["git"]

    username = os.environ.get("VDS_USERNAME")
    password = os.environ.get("VDS_PASSWORD")
    if username and password:
        token = b64encode(f"{username}:{password}".encode()).decode()
        command.extend(["-c", f"http.extraHeader=Authorization: Basic {token}"])

    command.append("ls-remote")
    if include_symref:
        command.append("--symref")
    command.extend(["--heads", remote_url])

    if branch_candidates:
        refs = [f"refs/heads/{branch}" for branch in branch_candidates]
        command.extend(refs)

    return command


# ---------------------------------------------------------------------------
# Probing functions
# ---------------------------------------------------------------------------


async def probe_branch_candidates(
    remote_url: str,
    candidates: tuple[str, ...] = BRANCH_CANDIDATES,
    *,
    timeout: float = 20.0,
) -> BranchProbeResult:
    """Probe a remote for known branch candidates via ``git ls-remote``.

    Returns a :class:`BranchProbeResult` whose ``available_branches`` lists
    which of *candidates* actually exist on the remote, preserving candidate
    order.
    """
    normalized_remote = str(remote_url or "").strip()
    if not normalized_remote:
        return BranchProbeResult(
            deterministic=False,
            error="missing_remote_url",
        )

    parsed_remote = urlparse(normalized_remote)
    if parsed_remote.scheme not in _ALLOWED_SCHEMES:
        return BranchProbeResult(
            deterministic=False,
            error=f"unsupported_remote_scheme:{parsed_remote.scheme or 'none'}",
        )

    command = _build_ls_remote_command(
        remote_url=normalized_remote,
        branch_candidates=candidates,
    )
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.communicate()
        return BranchProbeResult(
            deterministic=False,
            error="ls_remote_timeout",
        )

    returncode = process.returncode or 0
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    if returncode != 0:
        return BranchProbeResult(
            deterministic=False,
            error=(stderr.strip() or stdout.strip() or f"ls_remote_failed:{returncode}"),
        )

    available_branches: list[str] = []
    branch_set = set(candidates)
    for line in stdout.splitlines():
        ref = str(line).strip().split()[-1] if line.strip() else ""
        if not ref.startswith("refs/heads/"):
            continue
        branch_name = ref.removeprefix("refs/heads/").strip()
        if branch_name in branch_set and branch_name not in available_branches:
            available_branches.append(branch_name)

    return BranchProbeResult(
        deterministic=True,
        available_branches=available_branches,
    )


async def probe_branch_hints(
    remote_url: str,
    *,
    sample_limit: int = 5,
    timeout: float = 20.0,
) -> BranchHintResult:
    """Discover all remote branches and the HEAD default via ``--symref``.

    Returns a :class:`BranchHintResult` with the server's default branch
    (if ``HEAD`` is a symbolic ref) and a sample of discovered branch names.
    """
    normalized_remote = str(remote_url or "").strip()
    if not normalized_remote:
        return BranchHintResult(
            deterministic=False,
            error="missing_remote_url",
        )

    parsed_remote = urlparse(normalized_remote)
    if parsed_remote.scheme not in _ALLOWED_SCHEMES:
        return BranchHintResult(
            deterministic=False,
            error=f"unsupported_remote_scheme:{parsed_remote.scheme or 'none'}",
        )

    command = _build_ls_remote_command(
        remote_url=normalized_remote,
        branch_candidates=None,
        include_symref=True,
    )
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.communicate()
        return BranchHintResult(
            deterministic=False,
            error="ls_remote_timeout",
        )

    returncode = process.returncode or 0
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    if returncode != 0:
        return BranchHintResult(
            deterministic=False,
            error=(stderr.strip() or stdout.strip() or f"ls_remote_failed:{returncode}"),
        )

    discovered_branches: list[str] = []
    default_branch: str | None = None
    for line in stdout.splitlines():
        stripped = str(line).strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) >= 3 and parts[0] == "ref:" and parts[-1] == "HEAD":
            ref = str(parts[1] or "").strip()
            if ref.startswith("refs/heads/"):
                parsed_default = ref.removeprefix("refs/heads/").strip()
                if parsed_default:
                    default_branch = parsed_default
            continue
        ref = parts[-1] if parts else ""
        if not str(ref).startswith("refs/heads/"):
            continue
        branch_name = str(ref).removeprefix("refs/heads/").strip()
        if branch_name and branch_name not in discovered_branches:
            discovered_branches.append(branch_name)

    safe_sample_limit = max(int(sample_limit), 1)
    return BranchHintResult(
        deterministic=True,
        default_branch=default_branch,
        discovered_branches=discovered_branches[:safe_sample_limit],
        discovered_branch_count=len(discovered_branches),
    )
