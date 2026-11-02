#!/usr/bin/env bash
# Bootstrap uv-managed project environments in the vds-scripts workspace.
#
# Canonical full-workspace bootstrap assumes Python 3.14+ as the preferred
# integrated baseline for operators and AI agents.
#
# Usage:
#   scripts/bootstrap_uv.sh                      # canonical full sync — all workspace members
#   scripts/bootstrap_uv.sh --package <member>   # targeted sync — one member/package
#   scripts/bootstrap_uv.sh --package <m> [uv sync flags...]
#   scripts/bootstrap_uv.sh [uv sync flags...]   # full sync, extra flags forwarded
#
# Examples:
#   scripts/bootstrap_uv.sh                        # sync all 30 members
#   scripts/bootstrap_uv.sh --package audit_orchestrator
#   scripts/bootstrap_uv.sh --package vds_cli --frozen
#   scripts/bootstrap_uv.sh --frozen               # full sync, frozen lockfile

set -euo pipefail

_BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./vds_sh_helpers.sh
source "$_BOOTSTRAP_DIR/vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
TARGETED_PACKAGE=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package)
      if [[ -z "${2:-}" ]]; then
        echo "bootstrap_uv: --package requires a member name" >&2
        exit 1
      fi
      TARGETED_PACKAGE="$2"
      shift 2
      ;;
    --package=*)
      TARGETED_PACKAGE="${1#--package=}"
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Targeted mode
# ---------------------------------------------------------------------------
if [[ -n "$TARGETED_PACKAGE" ]]; then
  echo "Syncing workspace package/member: $TARGETED_PACKAGE"
  vds_uv_sync_package "$TARGETED_PACKAGE" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
  echo "Done."
  exit 0
fi

# ---------------------------------------------------------------------------
# Full mode — sync the entire workspace
# ---------------------------------------------------------------------------
echo "Syncing full vds-scripts workspace (preferred baseline: Python 3.14+)..."
vds_uv_sync_all "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
echo "All workspace members synced."
