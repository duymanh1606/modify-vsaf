#!/usr/bin/env python3
"""Pre-commit guard: block invalid symlinks, committed worktrees, and macOS artifacts.

Rejects staged changes that match any of these antipatterns:

1. Staged path under `worktrees/` (committed worktree directories)
2. Staged path under `audit_orchestrator/temp_bitbucket_clones/` (clone cache)
3. Basename matching `<name> <digits>` — macOS Finder rename-conflict artifacts
   (e.g. `.venv 3`, `file 2.txt`)
4. Symlink (mode 120000) with absolute target (starts with `/`)
5. Symlink with target containing `.nosync` (macOS iCloud marker)
6. Symlink whose relative target escapes the repo root
7. Staged path containing any ASCII control byte (0x00-0x1F or 0x7F) — crashes Bitbucket Server /browse

stdlib-only; exits 0 on pass, 1 on violation.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import PurePosixPath

# Rule constants
WORKTREES_PREFIX = "worktrees/"
CLONE_CACHE_PREFIX = "audit_orchestrator/temp_bitbucket_clones/"
NOSYNC_MARKER = ".nosync"
SYMLINK_MODE = "120000"

# Match a trailing " <digits>" before an optional extension, e.g.:
#   ".venv 3", "file 2", "file 2.txt", "foo 12.md"
RENAME_CONFLICT_RE = re.compile(r" \d+(\.[^/]*)?$")


def _run(cmd: list[str]) -> bytes:
    """Run a git command and return stdout bytes. Raises on non-zero exit."""
    result = subprocess.run(cmd, capture_output=True, check=True)
    return result.stdout


def _staged_paths_bytes() -> list[bytes]:
    """Return staged added/modified paths as raw bytes. Raw bytes are required
    for Rule 7; decoding would mask ASCII control bytes as UTF-8 replacements."""
    out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM", "-z"])
    return [p for p in out.split(b"\x00") if p]


def _check_control_chars(path_bytes: bytes) -> str | None:
    """Rule-7: reject any ASCII control byte (0x00-0x1F or 0x7F) in a path."""
    for b in path_bytes:
        if b < 0x20 or b == 0x7F:
            decoded = path_bytes.decode("utf-8", errors="replace")
            return (
                f"{decoded!r}: path contains ASCII control character (byte 0x{b:02x})"
                " — crashes Bitbucket /browse renderer (KB 'A non-blank path is required')"
            )
    return None


def _index_entry(path: str) -> tuple[str, str] | None:
    """Return (mode, sha) for a path in the index, or None if not staged."""
    try:
        out = _run(["git", "ls-files", "-s", "--", path])
    except subprocess.CalledProcessError:
        return None
    if not out:
        return None
    # Format: "<mode> <sha> <stage>\t<path>"
    first_line = out.split(b"\n", 1)[0].decode("utf-8", errors="replace")
    head = first_line.split("\t", 1)[0]
    fields = head.split()
    if len(fields) < 2:
        return None
    return fields[0], fields[1]


def _symlink_target(sha: str) -> str:
    """Read the blob content of a symlink object (its target path)."""
    out = _run(["git", "cat-file", "blob", sha])
    return out.decode("utf-8", errors="replace")


def _escapes_repo_root(link_path: str, target: str) -> bool:
    """Return True if a relative target escapes above the repo root.

    link_path is the repo-relative path of the symlink itself; target is its
    literal target string. We resolve logically (no filesystem access) using
    PurePosixPath so parent-count reasoning is deterministic.
    """
    if target.startswith("/"):
        # Absolute targets are handled by a dedicated rule; skip here.
        return False
    link_dir = PurePosixPath(link_path).parent
    parts = list(link_dir.parts) + target.split("/")
    depth = 0
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            depth -= 1
            if depth < 0:
                return True
        else:
            depth += 1
    return False


def _check_path(path: str) -> list[str]:
    """Return a list of violation messages for one staged path."""
    violations: list[str] = []

    if path.startswith(WORKTREES_PREFIX):
        violations.append(f"{path}: path under 'worktrees/' — committed worktree directories are a git antipattern")

    if path.startswith(CLONE_CACHE_PREFIX):
        violations.append(f"{path}: path under '{CLONE_CACHE_PREFIX}' — external clone cache must not be tracked")

    basename = os.path.basename(path)
    if RENAME_CONFLICT_RE.search(basename):
        violations.append(
            f"{path}: basename '{basename}' looks like a macOS Finder rename-conflict artifact (' <digits>' suffix)"
        )

    entry = _index_entry(path)
    if entry is None:
        return violations
    mode, sha = entry
    if mode != SYMLINK_MODE:
        return violations

    try:
        target = _symlink_target(sha)
    except subprocess.CalledProcessError:
        violations.append(f"{path}: unable to read symlink target from index")
        return violations

    if target.startswith("/"):
        violations.append(f"{path}: symlink has ABSOLUTE target '{target}' — won't resolve on other machines")
    if NOSYNC_MARKER in target:
        violations.append(
            f"{path}: symlink target contains '.nosync' (target={target!r}) — macOS iCloud marker must not be committed"
        )
    if _escapes_repo_root(path, target):
        violations.append(f"{path}: relative symlink target '{target}' escapes repo root")

    return violations


def main() -> int:
    try:
        paths_bytes = _staged_paths_bytes()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"check-invalid-symlinks: git call failed: {exc}\n")
        return 1

    all_violations: list[str] = []
    for path_bytes in paths_bytes:
        # Rule 7 on raw bytes; on hit we skip later rules (they need a str).
        ctrl_msg = _check_control_chars(path_bytes)
        if ctrl_msg is not None:
            all_violations.append(ctrl_msg)
            continue
        path = path_bytes.decode("utf-8", errors="replace")
        all_violations.extend(_check_path(path))

    if not all_violations:
        return 0

    sys.stderr.write("check-invalid-symlinks: BLOCKED — staged changes contain disallowed patterns:\n")
    for msg in all_violations:
        sys.stderr.write(f"  - {msg}\n")
    sys.stderr.write(
        "\nRefuse rationale: these patterns break Bitbucket Server's /browse "
        "renderer and fail on Linux CI. Unstage with `git reset HEAD -- <path>` "
        "and add to .gitignore if needed.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
