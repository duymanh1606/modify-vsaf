#!/usr/bin/env bash
# Hook 14 — stage2-completeness (NEW)
# Event: SubagentStop after /ntapp-architecture-design.
# Check: 3 artifacts exist + non-empty + WBS has ≥1 unit row.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable
. "$HOOK_DIR/lib/entry_mode.sh"

if mode_skips hook14; then ok; fi

SPEC="$(get_spec_repo_root)"
HLD="$SPEC/NTAPP-output/Stage_2_Architecture/architecture_design.md"
M0="$SPEC/NTAPP-output/Stage_2_Architecture/00_system_connectivity_integration.md"
WBS="$SPEC/NTAPP-output/Stage_2_Architecture/project_wbs.md"

# Trigger only if at least one of these was just written
recently_modified=false
for f in "$HLD" "$M0" "$WBS"; do
  if [[ -f "$f" ]] && [[ $(find "$f" -mmin -5 2>/dev/null) ]]; then
    recently_modified=true; break
  fi
done
$recently_modified || ok

problems=()

for f in "$HLD" "$M0" "$WBS"; do
  if [[ ! -f "$f" ]]; then
    problems+=( "$(basename "$f") missing" )
  elif [[ ! -s "$f" ]]; then
    problems+=( "$(basename "$f") empty" )
  fi
done

# WBS: ≥1 unit row
if [[ -f "$WBS" ]]; then
  units=$(python3 "$HOOK_DIR/lib/wbs_parser.py" "$WBS" 2>/dev/null | wc -l | xargs)
  if [[ "$units" -lt 1 ]]; then
    problems+=( "project_wbs.md has 0 units (table parse fail or empty)" )
  fi
fi

# HLD: must have at least one mermaid block (system diagram)
if [[ -f "$HLD" ]]; then
  grep -q '```mermaid' "$HLD" || problems+=( "architecture_design.md has no mermaid diagram" )
fi

# Module 0: must have §Contracts section
if [[ -f "$M0" ]]; then
  grep -qiE '^#+\s*(Contracts?|API Contracts?|State Enum)' "$M0" \
    || problems+=( "00_system_connectivity_integration.md missing Contracts section" )
fi

if [[ ${#problems[@]} -gt 0 ]]; then
  log_event "stage2-completeness" "WARN" "${problems[*]}"
  "$HOOK_DIR/notify.sh" warn false \
    "Stage 2 output incomplete" \
    "Problems:
$(printf '  - %s\n' "${problems[@]}")

Possibly 1 sub-agent in /ntapp-architecture-design failed silently.
Re-run, or fill missing sections by hand." \
    --mention "@SeniorDev,@SA"
  # Notify but don't block — Hook 1 approval-gate will block downstream anyway
  ok
fi

log_event "stage2-completeness" "PASS"
ok
