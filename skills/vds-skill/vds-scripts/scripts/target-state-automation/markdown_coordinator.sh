#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=WHO-project/vds-scripts/scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

SCRIPTS_ROOT="$(vds_resolve_scripts_root)"
MONO_ROOT="$(dirname "$(dirname "$SCRIPTS_ROOT")")"
DOCS_ROOT="$(resolve_insurance_docs_root "$MONO_ROOT")"
DOC_ROOT="$DOCS_ROOT/projects/INSURANCE/analysis/target-state"
COORD="$SCRIPTS_ROOT/scripts/target-state-automation/coordination.sh"
AGENT_ID="${AGENT_ID:-markdown-agent-01}"

lock_file="$DOC_ROOT/README.md"
"$COORD" lock "$AGENT_ID" "$lock_file" "markdown-check" >/dev/null || true

cd "$DOC_ROOT"
vds_uv_run_package markdown_orchestrator -- vds-cli markdown check \
  architecture/*.md \
  architecture/**/*.md \
  service-specifications/**/*.md \
  *.md

"$COORD" unlock "$AGENT_ID" "$lock_file" >/dev/null || true
