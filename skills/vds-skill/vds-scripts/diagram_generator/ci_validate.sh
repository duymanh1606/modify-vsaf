#!/usr/bin/env bash
set -euo pipefail

PROJECT="${1:-INSURANCE}"
SERVICE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ -n "${SERVICE}" ]; then
  uv run python generate_all_diagrams.py --project "${PROJECT}" --service "${SERVICE}" --validate-existing
else
  uv run python generate_all_diagrams.py --project "${PROJECT}" --validate-existing
fi


