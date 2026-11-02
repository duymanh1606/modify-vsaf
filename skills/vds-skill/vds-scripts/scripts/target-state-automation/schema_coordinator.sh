#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"
DOCS_ROOT="$(resolve_insurance_docs_root "$ROOT")"
TARGET_STATE_ARCH_ROOT="$DOCS_ROOT/projects/INSURANCE/analysis/target-state/architecture"
COORD="$ROOT/scripts/target-state-automation/coordination.sh"
AGENT_ID="${AGENT_ID:-schema-agent-01}"

if [[ -z "${SERVICES:-}" ]]; then
  SERVICES=$(ls -d "$TARGET_STATE_ARCH_ROOT"/insurance-* 2>/dev/null | xargs -n1 basename)
fi

for svc in $SERVICES; do
  echo "== $svc =="
  schema_file="$TARGET_STATE_ARCH_ROOT/$svc/${svc}-database-target-schema.md"
  "$COORD" lock "$AGENT_ID" "$schema_file" "validate-schema" >/dev/null || true
  vds_uv_run_package vds_cli vds-cli schema convert --service "$svc" --format plantuml --validate
  "$COORD" unlock "$AGENT_ID" "$schema_file" >/dev/null || true
  echo "-- done $svc --"
done
