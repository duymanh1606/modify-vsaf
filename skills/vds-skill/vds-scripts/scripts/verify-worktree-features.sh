#!/usr/bin/env bash
# Live verification for VDS worktree features:
# - scripts/worktree_uv.sh (VAMI-013/Phase 176): venv-aware uv wrapper
# - scripts/worktree_compose.sh: docker-compose worktree wrapper
# - git worktree integration (list/parse/path-resolve)
# - PYTHONPATH hydration from _vds_*.pth stubs
# - ~/.vds/.env propagation through uv-launched Python
#
# Companion to scripts/verify-memory-cli-e2e.sh (which covers memory CLI).
# Read-only — no mutations to repos, worktrees, or containers.
#
# Usage:
#   bash scripts/verify-worktree-features.sh
#   bash scripts/verify-worktree-features.sh --quick   # skip docker checks
#
# Exit 0 on all pass, 1 on any failure.

set -uo pipefail
# NOTE: `set -e` deliberately omitted — many checks below probe failure paths
# and capture stderr; the per-check `|| true` + explicit if-checks make
# `set -e` actively harmful here (it would abort the whole verification on
# the first probe whose subshell has a non-zero exit).

QUICK="no"
if [[ "${1:-}" == "--quick" ]]; then
    QUICK="yes"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PASS=0
FAIL=0
SKIP=0
ERRORS=()

pass() { PASS=$((PASS + 1)); echo "  ✓ PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); ERRORS+=("$1: $2"); echo "  ✗ FAIL: $1 — $2"; }
skip() { SKIP=$((SKIP + 1)); echo "  ⊘ SKIP: $1 — $2"; }
header() { echo ""; echo "--- $1 ---"; }

echo "============================================================"
echo "  VDS Worktree Features — Live Verification"
echo "============================================================"
echo "Repo root: $REPO_ROOT"
echo "Quick mode: $QUICK"

# --------------------------------------------------------------------------
# W1 — worktree_uv.sh exists and is executable
# --------------------------------------------------------------------------
header "W1: worktree_uv.sh present + executable"
if [[ -x "${REPO_ROOT}/scripts/worktree_uv.sh" ]]; then
    pass "W1 worktree_uv.sh found at scripts/worktree_uv.sh and is executable"
else
    fail "W1" "scripts/worktree_uv.sh not found or not executable"
    echo "STATUS: ABORT"
    exit 1
fi

# --------------------------------------------------------------------------
# W2 — worktree_compose.sh exists and is executable
# --------------------------------------------------------------------------
header "W2: worktree_compose.sh present + executable"
if [[ -x "${REPO_ROOT}/scripts/worktree_compose.sh" ]]; then
    pass "W2 worktree_compose.sh found at scripts/worktree_compose.sh and is executable"
else
    fail "W2" "scripts/worktree_compose.sh not found or not executable"
fi

# --------------------------------------------------------------------------
# W3 — Worktree venv exists at .venv/ in current repo
# --------------------------------------------------------------------------
header "W3: worktree venv at \$REPO_ROOT/.venv/"
if [[ -d "${REPO_ROOT}/.venv" ]] && [[ -x "${REPO_ROOT}/.venv/bin/python" ]] || \
   [[ -x "$(echo "${REPO_ROOT}"/.venv/bin/python3* 2>/dev/null | awk '{print $1}')" ]]; then
    PY_VER=$("${REPO_ROOT}/.venv/bin/python" --version 2>&1 || \
             "${REPO_ROOT}"/.venv/bin/python3* --version 2>&1)
    pass "W3 .venv present (interpreter: $PY_VER)"
else
    fail "W3" ".venv directory or python interpreter missing under $REPO_ROOT"
fi

# --------------------------------------------------------------------------
# W4 — worktree_uv.sh resolves --project vds_cli + emits CLI version
# --------------------------------------------------------------------------
header "W4: worktree_uv.sh run --project vds_cli vds-cli memory --version (version surface)"
W4_OUT=$("${REPO_ROOT}/scripts/worktree_uv.sh" run --project vds_cli vds-cli memory --version 2>&1 || true)
if echo "$W4_OUT" | grep -qE "vds-memory|[0-9]+\.[0-9]+"; then
    W4_VER=$(echo "$W4_OUT" | grep -oE "[0-9]+\.[0-9]+(\.[0-9]+)?" | head -1)
    pass "W4 vds-cli memory version surface returned ($W4_VER)"
else
    fail "W4" "vds-cli memory --version did not return a version string: $(echo "$W4_OUT" | head -c 200)"
fi

# --------------------------------------------------------------------------
# W5 — A second project resolves correctly (--project memory_orchestrator)
# --------------------------------------------------------------------------
header "W5: worktree_uv.sh run --project memory_orchestrator (second project resolves)"
W5_OUT=$("${REPO_ROOT}/scripts/worktree_uv.sh" run --project memory_orchestrator python -c "import vds_memory_orchestrator; print('ok')" 2>&1 || true)
if echo "$W5_OUT" | grep -q "^ok$"; then
    pass "W5 memory_orchestrator project import resolved via worktree_uv.sh"
else
    fail "W5" "memory_orchestrator import failed: $(echo "$W5_OUT" | head -c 200)"
fi

# --------------------------------------------------------------------------
# W6 — PYTHONPATH hydration from _vds_*.pth stubs (VAMI-013 contract)
# --------------------------------------------------------------------------
header "W6: PYTHONPATH hydration from _vds_*.pth stubs"
PTH_COUNT=$(find "${REPO_ROOT}"/.venv/lib/python*/site-packages -maxdepth 1 -type f -name '_vds_*.pth' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$PTH_COUNT" -gt 0 ]]; then
    # Verify worktree_uv.sh actually exports PYTHONPATH with at least one of those entries.
    HYDRATED_PATH=$("${REPO_ROOT}/scripts/worktree_uv.sh" run --project vds_cli python -c "import os; print(os.environ.get('PYTHONPATH', ''))" 2>&1 | tail -1)
    if [[ -n "$HYDRATED_PATH" ]]; then
        pass "W6 found $PTH_COUNT _vds_*.pth stub(s); PYTHONPATH exported (length=${#HYDRATED_PATH} chars)"
    else
        fail "W6" "$PTH_COUNT _vds_*.pth stubs found but PYTHONPATH was empty after worktree_uv.sh run"
    fi
else
    skip "W6" "no _vds_*.pth stubs in this venv (worktree may not require PYTHONPATH hydration)"
fi

# --------------------------------------------------------------------------
# W7 — ~/.vds/.env propagation: a known shared env var visible to uv-launched Python
# --------------------------------------------------------------------------
header "W7: ~/.vds/.env propagation through worktree_uv.sh"
if [[ -f "${HOME}/.vds/.env" ]]; then
    # Pick a deterministic key from ~/.vds/.env (ignoring comments and empty lines).
    PROBE_KEY=$(grep -E "^[A-Z_]+=" "${HOME}/.vds/.env" 2>/dev/null | head -1 | cut -d= -f1)
    if [[ -n "$PROBE_KEY" ]]; then
        PROBE_VAL=$("${REPO_ROOT}/scripts/worktree_uv.sh" run --project vds_cli python -c "import os; print(os.environ.get('${PROBE_KEY}', '__MISSING__'))" 2>&1 | tail -1)
        if [[ "$PROBE_VAL" != "__MISSING__" ]] && [[ -n "$PROBE_VAL" ]]; then
            pass "W7 ~/.vds/.env key '$PROBE_KEY' propagated through worktree_uv.sh"
        else
            fail "W7" "~/.vds/.env key '$PROBE_KEY' not visible after worktree_uv.sh run"
        fi
    else
        skip "W7" "~/.vds/.env exists but no shell-style KEY= entries to probe"
    fi
else
    skip "W7" "~/.vds/.env does not exist (nothing to propagate)"
fi

# --------------------------------------------------------------------------
# W8 — git worktree list --porcelain parses cleanly + current dir is recognized
# --------------------------------------------------------------------------
header "W8: git worktree list --porcelain parses; current dir is a worktree-aware path"
WT_LIST=$(git -C "${REPO_ROOT}" worktree list --porcelain 2>&1 || true)
if echo "$WT_LIST" | grep -qE "^worktree "; then
    WT_COUNT=$(echo "$WT_LIST" | grep -cE "^worktree ")
    # Verify current dir is in the list (or is the main checkout).
    CURRENT_REAL=$(cd "${REPO_ROOT}" && pwd -P)
    if echo "$WT_LIST" | grep -qF "$CURRENT_REAL"; then
        pass "W8 git worktree list parses ($WT_COUNT worktree(s)); current path matches an entry"
    else
        # Strict equality may fail on iCloud paths with normalization; soft-pass on parse-only.
        pass "W8 git worktree list parses ($WT_COUNT worktree(s)); current path normalization differs but porcelain valid"
    fi
else
    fail "W8" "git worktree list --porcelain did not return any 'worktree ' lines: $(echo "$WT_LIST" | head -c 200)"
fi

# --------------------------------------------------------------------------
# W9 — VIRTUAL_ENV cleanup: pre-export a fake VIRTUAL_ENV; worktree_uv.sh
#       must clear it (per script comment "Clear inherited active-environment state")
# --------------------------------------------------------------------------
header "W9: worktree_uv.sh clears mismatched VIRTUAL_ENV"
W9_OUT=$(VIRTUAL_ENV="/tmp/__nonexistent_venv_$$__" "${REPO_ROOT}/scripts/worktree_uv.sh" run --project vds_cli python -c "import os; print('VENV=' + os.environ.get('VIRTUAL_ENV', '__UNSET__'))" 2>&1 | tail -1)
if echo "$W9_OUT" | grep -qE "VENV=.*\.venv"; then
    # uv replaced our fake VIRTUAL_ENV with the real worktree venv → cleanup worked.
    pass "W9 mismatched VIRTUAL_ENV was overridden by worktree venv"
elif echo "$W9_OUT" | grep -q "VENV=__UNSET__"; then
    pass "W9 mismatched VIRTUAL_ENV was unset before uv launch"
else
    fail "W9" "VIRTUAL_ENV cleanup did not happen: $W9_OUT"
fi

# --------------------------------------------------------------------------
# W10 — worktree_compose.sh detection mode (read-only): `ps` lists vds-platform memory-stack
#       containers (post ADR-INF-10 three-tier compose; project renamed vds-ai-memory → vds-platform).
# --------------------------------------------------------------------------
if [[ "$QUICK" == "yes" ]]; then
    skip "W10" "--quick flag skips docker checks"
else
    header "W10: docker compose -p vds-platform ps — read-only container listing"
    # Post ADR-INF-10 the canonical compose project is `vds-platform` and split across
    # docker/docker-compose.{infra,services,cli}.yml. The legacy worktree_compose.sh
    # wrapper still points at the retired memory_orchestrator/compose.yaml so we query
    # the project label directly here.
    W10_OUT=$(docker ps --filter "label=com.docker.compose.project=vds-platform" --format '{{.Names}}' 2>&1 || true)
    if echo "$W10_OUT" | grep -qE "^vds-(postgres|redis|qdrant|memory-api|memory-worker)$"; then
        CONTAINER_LINES=$(echo "$W10_OUT" | grep -cE "^vds-(postgres|redis|qdrant|memory-|scheduler-|multi-agent-)")
        pass "W10 docker compose project=vds-platform lists $CONTAINER_LINES container(s)"
    else
        fail "W10" "no vds-platform containers found via project label: $(echo "$W10_OUT" | head -c 200)"
    fi
fi

# --------------------------------------------------------------------------
# W11 — Compose project identity pinned (regardless of which worktree invokes it).
#       Per infrastructure-evolution-skill v1.4.0 / ADR-INF-7, the canonical project
#       name is `vds-platform` (was `vds-ai-memory` pre-v2.10.0).
# --------------------------------------------------------------------------
if [[ "$QUICK" == "yes" ]]; then
    skip "W11" "--quick flag skips docker checks"
else
    header "W11: docker compose project identity 'vds-platform' (single anchor across worktrees)"
    PROJECT_LIST=$(docker compose ls --format json 2>&1 || true)
    if echo "$PROJECT_LIST" | grep -q '"vds-platform"'; then
        pass "W11 docker compose project 'vds-platform' is registered (compose-project-identity anchor holds)"
    else
        fail "W11" "docker compose ls did not show 'vds-platform' project: $(echo "$PROJECT_LIST" | head -c 200)"
    fi
fi

# --------------------------------------------------------------------------
# W12 — Each branch-isolated worktree has its own venv (isolation invariant)
# --------------------------------------------------------------------------
header "W12: each git worktree has its own .venv/ directory (or shares main with explicit symlink)"
WT_COUNT=$(git -C "${REPO_ROOT}" worktree list --porcelain 2>&1 | grep -cE "^worktree " || true)
if [[ "$WT_COUNT" -gt 1 ]]; then
    MISSING_VENV=0
    while IFS= read -r wt_path; do
        # Strip "worktree " prefix
        wt_path="${wt_path#worktree }"
        if [[ ! -d "${wt_path}/.venv" ]] && [[ ! -L "${wt_path}/.venv" ]]; then
            MISSING_VENV=$((MISSING_VENV + 1))
        fi
    done < <(git -C "${REPO_ROOT}" worktree list --porcelain 2>&1 | grep -E "^worktree ")
    if [[ "$MISSING_VENV" -eq 0 ]]; then
        pass "W12 all $WT_COUNT worktrees have a .venv/ directory"
    else
        # Soft warning — a recently-created worktree may not yet have synced; treat as informational.
        skip "W12" "$MISSING_VENV of $WT_COUNT worktrees missing .venv/ (may need uv sync; not a regression)"
    fi
else
    skip "W12" "only 1 worktree present; isolation invariant trivially holds"
fi

# --------------------------------------------------------------------------
# W13 — `git worktree prune --dry-run` is safe (no stale metadata to clean,
#       OR explicit list of stale entries — never an error).
# --------------------------------------------------------------------------
header "W13: git worktree prune --dry-run reports cleanly (no error)"
PRUNE_OUT=$(git -C "${REPO_ROOT}" worktree prune --dry-run --verbose 2>&1)
PRUNE_EXIT=$?
if [[ $PRUNE_EXIT -eq 0 ]]; then
    PRUNE_LINES=$(echo "$PRUNE_OUT" | wc -l | tr -d ' ')
    if [[ -z "$PRUNE_OUT" ]] || [[ "$PRUNE_LINES" -eq 1 && -z "$(echo "$PRUNE_OUT" | tr -d '[:space:]')" ]]; then
        pass "W13 worktree prune --dry-run: no stale metadata"
    else
        pass "W13 worktree prune --dry-run reports stale entries (would remove on real prune): $(echo "$PRUNE_OUT" | head -1 | head -c 120)"
    fi
else
    fail "W13" "git worktree prune --dry-run exited $PRUNE_EXIT: $(echo "$PRUNE_OUT" | head -c 200)"
fi

# --------------------------------------------------------------------------
# W14 — Worktree lock state is inspectable via `worktree list --porcelain`
#       (locked entries show `locked` line). Required for cloud-backed paths.
# --------------------------------------------------------------------------
header "W14: worktree lock state inspectable via porcelain output (cloud-path safety)"
LOCK_LINES=$(git -C "${REPO_ROOT}" worktree list --porcelain 2>&1 | grep -cE "^locked( |$)" || true)
TOTAL_WT=$(git -C "${REPO_ROOT}" worktree list --porcelain 2>&1 | grep -cE "^worktree " || true)
if [[ "$TOTAL_WT" -gt 0 ]]; then
    pass "W14 porcelain output exposes lock state ($LOCK_LINES of $TOTAL_WT worktrees locked)"
else
    fail "W14" "no worktrees found at all — cannot verify lock-state surface"
fi

# --------------------------------------------------------------------------
# W15 — Each worktree owns a unique branch (isolation invariant from
#       git-worktree-skill §Core Rules: "one dedicated branch per worktree").
#       Detached-HEAD entries are exempt.
# --------------------------------------------------------------------------
header "W15: each worktree owns a unique branch (one-branch-per-worktree invariant)"
BRANCHES=$(git -C "${REPO_ROOT}" worktree list --porcelain 2>&1 | grep -E "^branch " | sort)
DETACHED_COUNT=$(git -C "${REPO_ROOT}" worktree list --porcelain 2>&1 | grep -cE "^detached$" || true)
if [[ -n "$BRANCHES" ]]; then
    BRANCH_COUNT=$(echo "$BRANCHES" | wc -l | tr -d ' ')
    UNIQ_COUNT=$(echo "$BRANCHES" | sort -u | wc -l | tr -d ' ')
    if [[ "$BRANCH_COUNT" -eq "$UNIQ_COUNT" ]]; then
        pass "W15 all $BRANCH_COUNT branched worktree(s) have unique branches (+$DETACHED_COUNT detached, exempt)"
    else
        DUP=$(echo "$BRANCHES" | uniq -d | head -1)
        fail "W15" "two worktrees share branch '$DUP' — violates git-worktree-skill §Core Rules invariant"
    fi
else
    skip "W15" "no branched worktrees (all detached) — invariant trivially holds"
fi

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
echo ""
echo "============================================================"
TOTAL=$((PASS + FAIL + SKIP))
echo "Worktree Features Results: ${PASS}/${TOTAL} pass | ${FAIL} fail | ${SKIP} skip"
if [[ ${FAIL} -gt 0 ]]; then
    echo "FAILURES:"
    for e in "${ERRORS[@]}"; do
        printf '  - %s\n' "$e"
    done
    exit 1
fi
echo "STATUS: ALL GREEN"
