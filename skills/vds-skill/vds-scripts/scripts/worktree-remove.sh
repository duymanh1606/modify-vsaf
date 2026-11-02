#!/usr/bin/env bash
# Phase 220.V (FR-220.V.2, ADR-93) — canonical worktree-removal wrapper.
#
# Replaces bare `git worktree remove` for vds-scripts. Adds husk cleanup
# (the .claude/, .gitnexus/, graphify-out/ directories that hooks create
# OUTSIDE git's tracked content and which `git worktree remove` therefore
# leaves behind — Phase 219 cleanup audit found 198MB of orphaned husks).
#
# Usage:
#   scripts/worktree-remove.sh <worktree-path> [--force] [--keep-cache]
#
# Steps (each idempotent):
#   1. Unlock if locked (catch-and-ignore "not locked" errors)
#   2. Inventory husk dirs (logged, not yet deleted)
#   3. git worktree remove [--force]
#   4. rm -rf orphan caches (.claude/, .gitnexus/, graphify-out/) — unless --keep-cache
#   5. git worktree prune (cleans .git/worktrees/<name>/ orphans)
#   6. Verify path absence in `git worktree list`

set -euo pipefail

# JSON-safe key-value emitter (Phase 220 code-review A2).
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

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <worktree-path> [--force] [--keep-cache]" >&2
    exit 2
fi

WT_PATH="$1"
shift

FORCE_FLAG=""
KEEP_CACHE=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE_FLAG="--force"; shift ;;
        --keep-cache) KEEP_CACHE=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

REPO_ROOT="$(git rev-parse --show-toplevel)"
# Canonicalize path (macOS /tmp → /private/tmp; iCloud spaces; symlinks)
ABS_WT_PATH="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$WT_PATH")"

# step 1: unlock if locked
if git -C "$REPO_ROOT" worktree unlock "$WT_PATH" 2>/dev/null; then
    echo '{"step": "unlock", "result": "ok"}'
else
    echo '{"step": "unlock", "result": "[idempotent] not locked or not registered"}'
fi

# step 2: inventory husk dirs
HUSK_DIRS=()
for d in .claude .gitnexus graphify-out __pycache__; do
    if [[ -d "$WT_PATH/$d" ]]; then
        HUSK_DIRS+=("$d")
    fi
done
if [[ ${#HUSK_DIRS[@]} -gt 0 ]]; then
    SIZE_KB=$(du -sk "${HUSK_DIRS[@]/#/$WT_PATH/}" 2>/dev/null | tail -1 | awk '{print $1}')
    HUSK_CSV="$(IFS=','; echo "${HUSK_DIRS[*]}")"
    emit_json step=inventory husk_dirs="$HUSK_CSV" size_kb="${SIZE_KB:-0}"
fi

# step 3: git worktree remove
if git -C "$REPO_ROOT" worktree list --porcelain | grep -qxF "worktree ${ABS_WT_PATH}"; then
    if git -C "$REPO_ROOT" worktree remove ${FORCE_FLAG:+"$FORCE_FLAG"} "$WT_PATH" 2>&1; then
        echo '{"step": "remove", "result": "ok"}'
    else
        echo '{"step": "remove", "result": "fail", "reason": "git worktree remove returned non-zero (try --force?)"}' >&2
        exit 3
    fi
else
    echo '{"step": "remove", "result": "[idempotent] not registered"}'
fi

# step 4: husk cleanup
if [[ $KEEP_CACHE -eq 0 ]]; then
    for d in .claude .gitnexus graphify-out __pycache__; do
        if [[ -d "$WT_PATH/$d" ]]; then
            rm -rf "$WT_PATH/$d"
            emit_json step=husk_cleanup result=removed dir="$d"
        fi
    done
    if [[ -d "$WT_PATH" ]] && [[ -z "$(ls -A "$WT_PATH" 2>/dev/null)" ]]; then
        rmdir "$WT_PATH" 2>/dev/null && echo '{"step": "rmdir", "result": "ok"}'
    fi
fi

# step 5: prune metadata
git -C "$REPO_ROOT" worktree prune
echo '{"step": "prune", "result": "ok"}'

# step 6: verify
if git -C "$REPO_ROOT" worktree list --porcelain | grep -qxF "worktree ${ABS_WT_PATH}"; then
    echo '{"step": "verify", "result": "fail", "reason": "worktree still listed after removal"}' >&2
    exit 4
fi

echo '{"step": "done", "result": "ok"}'
exit 0
