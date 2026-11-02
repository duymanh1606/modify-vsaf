#!/usr/bin/env bash
set -euo pipefail

# Generate component + sequence + use-case diagrams for all INSURANCE services.
# Requires: uv, vds_cli project synced.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

services=$(vds_uv_run_package vds_cli vds-cli diagrams -- --project INSURANCE --list | grep "insurance-")

for svc in $services; do
  echo "Generating diagrams for: $svc"
  vds_uv_run_package vds_cli vds-cli diagrams -- --project INSURANCE --service "$svc" --component --sequence --use-case
done

echo "Validating diagrams..."
vds_uv_run_package vds_cli vds-cli diagrams -- --project INSURANCE --validate-existing

echo "Done."

