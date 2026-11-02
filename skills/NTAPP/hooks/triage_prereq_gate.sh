#!/usr/bin/env bash
# Hook 12 — triage-prereq-gate (NEW)
# Event: UserPromptSubmit before /ntapp-feature-triage.
# Check: project_wbs.md exists + has ≥1 module + slice plan exists.
# Fail: redirect to workflow 3 (Stage 1-2-2b) first.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable

INPUT="$(read_stdin_json)"
PROMPT="$(json_get "$INPUT" '.prompt')"

echo "$PROMPT" | grep -qE '/ntapp-feature-triage' || ok

SPEC="$(get_spec_repo_root)"
WBS="$SPEC/NTAPP-output/Stage_2_Architecture/project_wbs.md"
SLICES_DIR="$SPEC/NTAPP-output/Stage_2_Architecture/slices"
MODULE0="$SPEC/NTAPP-output/Stage_2_Architecture/00_system_connectivity_integration.md"

missing=()

[[ -f "$WBS" ]] || missing+=( "project_wbs.md — Stage 2 not done" )
[[ -f "$MODULE0" ]] || missing+=( "00_system_connectivity_integration.md — Stage 2 not done" )

if [[ -f "$WBS" ]]; then
  unit_count=$(python3 "$HOOK_DIR/lib/wbs_parser.py" "$WBS" | wc -l | xargs)
  [[ "$unit_count" -ge 1 ]] || missing+=( "project_wbs.md has 0 units" )
fi

shopt -s nullglob
slice_files=( "$SLICES_DIR"/SLICE-*.md )
shopt -u nullglob
[[ ${#slice_files[@]} -gt 0 ]] || missing+=( "slices/SLICE-*.md — Stage 2b not done" )

if [[ ${#missing[@]} -gt 0 ]]; then
  log_event "triage-prereq-gate" "BLOCK" "${missing[*]}"
  block "Project chưa setup batch phase — không thể triage feature mới.
Missing:
$(printf '  - %s\n' "${missing[@]}")

Chạy workflow 3 (Stage 1-2-2b) trước:
  1. /bmad-create-prd → /bmad-create-epics-and-stories
  2. /ntapp-architecture-design
  3. /ntapp-slice-planning"
fi

log_event "triage-prereq-gate" "PASS"
ok
