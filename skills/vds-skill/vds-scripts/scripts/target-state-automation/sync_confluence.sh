#!/usr/bin/env bash
set -euo pipefail

# Sync docs and diagrams to Confluence.
# Requires: uv, vds_cli project synced, proper tokens in the shared VDS env file

PAGE_ID=${1:-166465076}  # override with first arg

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"
DOCS_ROOT="$(resolve_insurance_docs_root "$ROOT")"
DOC_DIR="$DOCS_ROOT/projects/INSURANCE/analysis/target-state"
ARCH_DIR="$DOC_DIR/architecture"

echo "Syncing PDFs (docs) to Confluence page $PAGE_ID..."
vds_uv_run_package vds_cli vds-cli confluence sync pdfs \
  "$PAGE_ID" \
  --dir "$DOC_DIR" \
  --server external

echo "Syncing PNG/SVG (diagrams) to Confluence page $PAGE_ID..."
vds_uv_run_package vds_cli vds-cli confluence sync pngs \
  "$PAGE_ID" \
  --dir "$ARCH_DIR" \
  --server external

echo "Done."
