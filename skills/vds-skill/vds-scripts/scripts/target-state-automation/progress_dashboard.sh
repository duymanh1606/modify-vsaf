#!/usr/bin/env bash
# UV-PATTERN: NO-UV — Delegates entirely to coordination.sh (curl/HTTP calls).
# No uv invocation needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"
COORD="$ROOT/scripts/target-state-automation/coordination.sh"

echo "== Agents =="
"$COORD" list-agents

echo "== Tasks =="
"$COORD" list-tasks
