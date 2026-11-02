#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"
FLAGS="${UV_SYNC_FLAGS:-}"

# Sync a narrow subset of workspace packages for diagram/markdown workflows.
# This is a targeted helper, not the canonical full-workspace bootstrap path.
if [[ -n "$FLAGS" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS=( $FLAGS )
else
  EXTRA_ARGS=()
fi

vds_uv_sync_package vds_cli "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
vds_uv_sync_package markdown_orchestrator "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
