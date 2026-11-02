#!/usr/bin/env bash
# docs_root.sh — Backward-compatibility shim.
#
# Delegates to scripts/vds_sh_helpers.sh which provides the authoritative
# implementations.  Existing callers that source this file and call
# resolve_repo_root() or resolve_insurance_docs_root() continue to work
# without modification.

set -euo pipefail

_DOCS_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../vds_sh_helpers.sh
source "$_DOCS_ROOT_DIR/../vds_sh_helpers.sh"

# resolve_repo_root — kept for backward compatibility.
# Returns the vds-scripts workspace root (same as vds_resolve_scripts_root).
resolve_repo_root() {
  vds_resolve_scripts_root
}

# resolve_insurance_docs_root is already provided by vds_sh_helpers.sh.
# No re-declaration needed.
