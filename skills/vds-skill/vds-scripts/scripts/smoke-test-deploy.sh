#!/usr/bin/env bash
# pytest-skip-default: requires Docker
#
# smoke-test-deploy.sh — v2.12.3 §Post-Merge Live Deploy runbook (P6 WP-6.3)
#
# Automates the 8-step runbook and writes a JSON evidence artifact to
# docs/p4-closure-evidence/smoke-<timestamp>-<git-sha>.json
#
# Usage:
#   bash scripts/smoke-test-deploy.sh [--target {live|ephemeral}]
#
# Environment:
#   VDS_SMOKE_ARTIFACT_DIR   Override artifact directory
#                            (default: <repo-root>/docs/p4-closure-evidence)
#   SKIP_DOWNGRADE_TESTS     Set to 1 to skip step 8 (alembic downgrade
#                            regression suite); useful if Docker is unavailable.
#
# Exit codes:
#   0  All 8 runbook steps passed + verify succeeded
#   1  One or more steps failed (partial artifact still written)
#   2  Pre-flight check failed (Python / make not found)
#
# Steps:
#   1. make build-cli
#   2. make run-audit-migrate
#   3. make run-progress-migrate
#   4. make up-memory
#   5. make up-multi-agent
#   6. make up-scheduler
#   7. make verify
#   8. pytest -m docker (alembic downgrade regression — ADR-INF-11)
#      Skip with: SKIP_DOWNGRADE_TESTS=1 bash scripts/smoke-test-deploy.sh
#
# DO NOT run this script directly in CI unless Docker compose is available.
# The unit-test contract (scripts/tests/test_smoke_deploy.py) covers the
# Python logic; this Bash wrapper is the operator-facing entrypoint.

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
TARGET="live"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"
      shift 2
      ;;
    --target=*)
      TARGET="${1#*=}"
      shift
      ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$TARGET" != "live" && "$TARGET" != "ephemeral" ]]; then
  echo "ERROR: --target must be 'live' or 'ephemeral', got: $TARGET" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ARTIFACT_DIR="${VDS_SMOKE_ARTIFACT_DIR:-"$REPO_ROOT/docs/p4-closure-evidence"}"

# ---------------------------------------------------------------------------
# Pre-flight: require Python 3 and make
# ---------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found in PATH" >&2
  exit 2
fi
if ! command -v make &>/dev/null; then
  echo "ERROR: make not found in PATH" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Locate smoke_deploy_lib.py (sibling of this script)
# ---------------------------------------------------------------------------
SMOKE_LIB="$SCRIPT_DIR/smoke_deploy_lib.py"
if [[ ! -f "$SMOKE_LIB" ]]; then
  echo "ERROR: $SMOKE_LIB not found — cannot proceed" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Resolve git SHA for artifact filename
# ---------------------------------------------------------------------------
GIT_SHA="unknown"
if command -v git &>/dev/null; then
  GIT_SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
fi

# ---------------------------------------------------------------------------
# Delegate to Python helper (handles step execution + artifact writing + trap)
# ---------------------------------------------------------------------------
echo "=== VDS P6 WP-6.3 Smoke Deploy (8 steps) ==="
echo "  target:              $TARGET"
echo "  repo root:           $REPO_ROOT"
echo "  artifact dir:        $ARTIFACT_DIR"
echo "  git SHA:             $GIT_SHA"
echo "  skip downgrade tests: ${SKIP_DOWNGRADE_TESTS:-0}"
echo ""

ARTIFACT_PATH="$(SKIP_DOWNGRADE_TESTS="${SKIP_DOWNGRADE_TESTS:-0}" python3 "$SMOKE_LIB" \
  --artifact-dir "$ARTIFACT_DIR" \
  --repo-root    "$REPO_ROOT" \
  --git-sha      "$GIT_SHA" \
  --target       "$TARGET")"

EXIT_CODE=$?

if [[ -n "$ARTIFACT_PATH" ]]; then
  echo ""
  echo "Artifact: $ARTIFACT_PATH"
fi

if [[ $EXIT_CODE -eq 0 ]]; then
  echo "Result:   PASS"
else
  echo "Result:   FAIL (exit $EXIT_CODE)" >&2
fi

exit $EXIT_CODE
