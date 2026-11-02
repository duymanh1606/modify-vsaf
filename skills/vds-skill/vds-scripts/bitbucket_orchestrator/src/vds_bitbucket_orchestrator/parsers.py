"""Shared Bitbucket REST API JSON parsers.

Pure-function extractors for clone URLs and default branch metadata from
Bitbucket Server REST API response dicts.  Both ``vds_sync_orchestrator``
and ``audit_orchestrator`` import from here instead of maintaining inline
extraction logic.

Phase 4 — FR-P1 (TSK-P1.1).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BitbucketBranchInfo:
    """Default branch metadata extracted from a Bitbucket repo dict.

    Attributes:
        display_id: Human-readable branch name (e.g. ``"release"``, ``"main"``).
                     When the server has no default branch this equals
                     *missing_sentinel*.
        ref: Full git ref (e.g. ``"refs/heads/release"``), or ``None`` when
             the server omits it.
        missing: ``True`` when the server did not report a default branch and
                 *display_id* was filled from the sentinel.
    """

    display_id: str
    ref: str | None
    missing: bool


def parse_clone_url(repo_dict: dict) -> str | None:
    """Extract the HTTP(S) clone URL from a Bitbucket repo dict.

    Iterates the ``links.clone`` array looking for the entry named ``"http"``.
    Falls back to the ``"ssh"`` entry when HTTP is absent.  Returns ``None``
    when neither is available.
    """
    links = repo_dict.get("links") or {}
    clone_entries = links.get("clone") or []

    http_url: str | None = None
    ssh_url: str | None = None

    for entry in clone_entries:
        name = (entry.get("name") or "").lower()
        href = entry.get("href")
        if not href:
            continue
        if name == "http":
            http_url = str(href)
        elif name == "ssh":
            ssh_url = str(href)

    return http_url or ssh_url


def parse_default_branch(
    repo_dict: dict,
    *,
    missing_sentinel: str = "main",
) -> BitbucketBranchInfo:
    """Extract default-branch metadata from a Bitbucket repo dict.

    The Bitbucket Server REST API may represent ``defaultBranch`` as:

    * A **dict** with ``displayId``, ``id`` (full ref), and optional
      ``latestCommit``.
    * A **plain string** (the branch name directly).
    * **Absent** — the server has no default branch configured.

    When absent, *missing_sentinel* is used as the ``display_id`` value and
    ``missing`` is set to ``True``.  This replaces the inconsistent hardcoded
    sentinels (``"release"`` in sync, ``"main"`` in audit) with a single
    parameterised entry point.
    """
    payload = repo_dict.get("defaultBranch")

    if isinstance(payload, dict):
        display_id = str(payload.get("displayId") or "").strip()
        ref_raw = str(payload.get("id") or payload.get("latestCommit") or "").strip()
        ref = ref_raw or None

        if not display_id:
            return BitbucketBranchInfo(
                display_id=missing_sentinel,
                ref=ref,
                missing=True,
            )
        return BitbucketBranchInfo(
            display_id=display_id,
            ref=ref,
            missing=False,
        )

    if isinstance(payload, str):
        stripped = payload.strip()
        if stripped:
            return BitbucketBranchInfo(
                display_id=stripped,
                ref=None,
                missing=False,
            )

    # No defaultBranch at all (None, empty string, or unexpected type)
    return BitbucketBranchInfo(
        display_id=missing_sentinel,
        ref=None,
        missing=True,
    )
