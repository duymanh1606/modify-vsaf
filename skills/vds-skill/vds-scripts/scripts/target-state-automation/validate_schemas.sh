#!/usr/bin/env bash
set -euo pipefail

# Validate/generate PlantUML ERD diagrams for all INSURANCE services.
# Requires: uv, vds_cli project synced.
#
# FOLLOW-UP DRIFT NOTE:
# This script now routes through the canonical helper contract correctly, but
# the underlying schema command surface appears to have drifted: the current
# `vds-cli schema` / `vds-schema-convert` compatibility layer no longer accepts
# the historical `convert --all --format plantuml --validate-all` shape.
# Keep this script classified as follow-up schema-command alignment work rather
# than treating any remaining failure here as a helper-layer regression.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=WHO-project/vds-scripts/scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"

echo "Validating PlantUML ERDs for all services..."
echo "ERROR: schema validation automation is currently unavailable in this worktree." >&2
echo "The shell helper migration is complete, but the underlying schema command surface is still a follow-up item." >&2
echo "Use help-first discovery to inspect the current schema compatibility layer:" >&2
echo "  ./scripts/worktree_uv.sh run --project vds_cli vds-cli schema --help" >&2
echo "  ./scripts/worktree_uv.sh run --project schema_converter vds-cli schema convert --help" >&2
exit 2

