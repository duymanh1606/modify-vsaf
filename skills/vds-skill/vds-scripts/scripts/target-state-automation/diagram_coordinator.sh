#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"
DOCS_ROOT="$(resolve_insurance_docs_root "$ROOT")"
TARGET_STATE_ARCH_ROOT="$DOCS_ROOT/projects/INSURANCE/analysis/target-state/architecture"
COORD="$ROOT/scripts/target-state-automation/coordination.sh"
AGENT_ID="${AGENT_ID:-diagram-agent-01}"

if [[ -z "${SERVICES:-}" ]]; then
  SERVICES=$(vds_uv_run_package vds_cli vds-cli diagrams -- --project INSURANCE --list | sed -n 's/^  - //p')
fi

for svc in $SERVICES; do
  echo "== $svc =="
  lock_file="$TARGET_STATE_ARCH_ROOT/$svc/${svc}-component.puml"
  "$COORD" lock "$AGENT_ID" "$lock_file" "generate-diagrams" >/dev/null || true
  vds_uv_run_package vds_cli vds-cli diagrams -- --project INSURANCE --service "$svc" --use-case
  "$COORD" unlock "$AGENT_ID" "$lock_file" >/dev/null || true
  echo "-- done $svc --"
done
