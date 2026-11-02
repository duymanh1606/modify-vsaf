#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"
DOCS_ROOT="$(resolve_insurance_docs_root "$ROOT")"
TARGET_STATE_ROOT="$DOCS_ROOT/projects/INSURANCE/analysis/target-state"
COORD="$ROOT/scripts/target-state-automation/coordination.sh"
AGENT_ID="${AGENT_ID:-confluence-agent-01}"
PAGE_ID="${PAGE_ID:?Set PAGE_ID for Confluence sync}"
SERVER="${SERVER:-external}"

lock_file="$TARGET_STATE_ROOT/README.md"
"$COORD" lock "$AGENT_ID" "$lock_file" "confluence-sync" >/dev/null || true

vds_uv_run_package vds_cli vds-cli confluence sync pngs "$PAGE_ID" \
  --dir "$TARGET_STATE_ROOT/architecture" \
  --server "$SERVER"

vds_uv_run_package vds_cli vds-cli confluence sync pdfs "$PAGE_ID" \
  --dir "$TARGET_STATE_ROOT" \
  --server "$SERVER"

"$COORD" unlock "$AGENT_ID" "$lock_file" >/dev/null || true
