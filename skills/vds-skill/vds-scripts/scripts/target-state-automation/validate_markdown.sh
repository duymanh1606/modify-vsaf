#!/usr/bin/env bash
set -euo pipefail

# Validate markdown in target-state docs.
# Requires: uv, markdown_orchestrator project synced.
#
# UV-PATTERN EXCEPTION: This script intentionally uses `uv pip install -e .`
# rather than the standard helper-driven workspace pattern (for example
# `vds_uv_run_package markdown_orchestrator ...`). Reason: the script is a
# local-dev helper that installs the package
# in editable mode so authors can iterate on the markdown_orchestrator source
# without re-syncing the full workspace.  This is a deliberate trade-off for
# development convenience, not an oversight.  Do NOT migrate to the worktree
# wrapper pattern without first evaluating whether the editable-install
# semantics are still needed.
#
# See scripts/vds_sh_helpers.sh for the canonical UV invocation helpers.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=WHO-project/vds-scripts/scripts/target-state-automation/docs_root.sh
source "$SCRIPT_DIR/docs_root.sh"

ROOT="$(resolve_repo_root)"
VDS_SCRIPTS="$ROOT/WHO-project/vds-scripts"
DOCS_ROOT="$(resolve_insurance_docs_root "$ROOT")"
TARGET_STATE="$DOCS_ROOT/projects/INSURANCE/analysis/target-state"

echo "Validating markdown in target-state..."
echo "========================================"

# Run markdown validation — editable install intentional (see header comment).
cd "$VDS_SCRIPTS/markdown_orchestrator"
uv pip install -e . --quiet
uv run -- vds-cli markdown check \
  "$TARGET_STATE"/architecture/*.md \
  "$TARGET_STATE"/architecture/**/*.md \
  "$TARGET_STATE"/service-specifications/**/*.md \
  "$TARGET_STATE"/*.md

VALIDATION_EXIT_CODE=$?

echo ""
echo "========================================"
echo "Markdown validation completed with exit code: $VALIDATION_EXIT_CODE"

if [ $VALIDATION_EXIT_CODE -eq 0 ]; then
  echo "Markdown validation PASSED"
else
  echo "Markdown validation FAILED with exit code: $VALIDATION_EXIT_CODE"
fi

echo ""
