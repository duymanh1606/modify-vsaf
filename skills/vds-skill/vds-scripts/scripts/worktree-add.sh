#!/usr/bin/env bash
# Phase 220.V (FR-220.V.1, ADR-93) — canonical worktree-creation wrapper.
#
# Replaces bare `git worktree add` for vds-scripts. Adds idempotent setup
# steps so the new worktree is immediately ready for tests:
#   1. Create worktree via git (or skip if path already a worktree)
#   2. Auto-lock iCloud-backed paths (cloud sync can corrupt git index)
#   3. Sync workspace deps via `worktree_uv.sh sync --all-packages --all-extras`
#      (closes the Phase 206/219 rediscovery loop where new worktrees
#      collected with missing extras and pytest failed on jose/passlib/etc.)
#   4. Stamp `.uv-sync-stamp` for the doctor lint (FR-220.V.4)
#
# Usage:
#   scripts/worktree-add.sh <worktree-path> <branch-name> [--from <base-ref>] \
#                            [--no-sync] [--no-lock]
#
# Exit codes:
#   0 — success (or idempotent re-run no-op)
#   2 — usage error
#   3 — git worktree add failed
#   4 — uv sync failed
#
# Idempotence: re-running on an existing worktree skips create/lock and
# re-runs only the sync (which `uv sync` is itself idempotent on).

set -euo pipefail

# JSON-safe key-value emitter (Phase 220 code-review A2).
# Bash inline `echo '{"key": "'"$VAR"'"}'` is unsafe when VAR contains
# double-quote, backslash, or newline. python3 json.dumps handles all
# escaping correctly. Output a single JSON object on stdout.
#
# Usage: emit_json step=create result=ok path="$ABS_WT_PATH" branch="$BRANCH"
emit_json() {
    python3 -c '
import json, sys
out = {}
for arg in sys.argv[1:]:
    k, _, v = arg.partition("=")
    out[k] = v
print(json.dumps(out))
' "$@"
}

# ---- arg parsing ----
if [[ $# -lt 2 ]]; then
    echo "usage: $0 <worktree-path> <branch-name> [--from <ref>] [--no-sync] [--no-lock]" >&2
    exit 2
fi

WT_PATH="$1"
BRANCH="$2"
shift 2

FROM_REF="master"
DO_SYNC=1
DO_LOCK="auto"  # auto, force, never

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from) FROM_REF="$2"; shift 2 ;;
        --no-sync) DO_SYNC=0; shift ;;
        --no-lock) DO_LOCK="never"; shift ;;
        --force-lock) DO_LOCK="force"; shift ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

# ---- resolve repo root ----
REPO_ROOT="$(git rev-parse --show-toplevel)"
# Canonicalize path (macOS /tmp → /private/tmp; iCloud spaces; symlinks)
ABS_WT_PATH="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$WT_PATH")"

# ---- step 1: create-or-skip ----
if git -C "$REPO_ROOT" worktree list --porcelain | grep -qxF "worktree ${ABS_WT_PATH}"; then
    echo '{"step": "create", "result": "[idempotent] worktree exists"}'
else
    emit_json step=create result=creating path="$ABS_WT_PATH" branch="$BRANCH"
    if ! git -C "$REPO_ROOT" worktree add -b "$BRANCH" "$WT_PATH" "$FROM_REF" 2>&1; then
        echo '{"step": "create", "result": "fail", "reason": "git worktree add returned non-zero"}' >&2
        exit 3
    fi
    echo '{"step": "create", "result": "ok"}'
fi

# ---- step 2: auto-lock iCloud-backed paths ----
if [[ "$DO_LOCK" != "never" ]]; then
    NEEDS_LOCK=0
    if [[ "$DO_LOCK" == "force" ]]; then
        NEEDS_LOCK=1
    elif realpath "$WT_PATH" 2>/dev/null | grep -q "Mobile Documents"; then
        NEEDS_LOCK=1
    fi
    if [[ $NEEDS_LOCK -eq 1 ]]; then
        if git -C "$REPO_ROOT" worktree lock --reason "iCloud-backed; auto-locked by worktree-add.sh" "$WT_PATH" 2>/dev/null; then
            echo '{"step": "lock", "result": "ok", "reason": "iCloud-backed path"}'
        else
            echo '{"step": "lock", "result": "[idempotent] already locked"}'
        fi
    fi
fi

# ---- step 3: uv sync --all-packages --all-extras ----
if [[ $DO_SYNC -eq 1 ]]; then
    cd "$WT_PATH"
    if [[ -x ./scripts/worktree_uv.sh ]]; then
        echo '{"step": "sync", "result": "running", "command": "worktree_uv.sh sync --all-packages --all-extras"}'
        if ! ./scripts/worktree_uv.sh sync --all-packages --all-extras 2>&1; then
            echo '{"step": "sync", "result": "fail", "reason": "worktree_uv.sh sync returned non-zero"}' >&2
            exit 4
        fi
    else
        # Fallback to direct uv sync if worktree_uv.sh missing (older worktrees)
        echo '{"step": "sync", "result": "running", "command": "uv sync --all-packages --all-extras"}'
        if ! uv sync --all-packages --all-extras 2>&1; then
            echo '{"step": "sync", "result": "fail", "reason": "uv sync returned non-zero"}' >&2
            exit 4
        fi
    fi
    # Stamp the marker file (FR-220.V.4) — idempotent (overwrite is no-op semantically)
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "$WT_PATH/.uv-sync-stamp"
    echo '{"step": "sync", "result": "ok"}'
else
    echo '{"step": "sync", "result": "[skipped] --no-sync"}'
fi

emit_json step=done result=ok worktree="$ABS_WT_PATH" branch="$BRANCH"
exit 0
