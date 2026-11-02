#!/usr/bin/env bash
# Hook 13 — triage-decision-validate (NEW)
# Event: SubagentStop after /ntapp-feature-triage.
# Check: decision file front-matter has lane + next_slash_command + reasoning
#        + refused_paths + honest_limits, none empty.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable
stop_reentry_guard "triage-decision-validate"

SPEC="$(get_spec_repo_root)"
TRIAGE_DIR="$SPEC/NTAPP-output/Stage_1_Discovery/triage"

[[ -d "$TRIAGE_DIR" ]] || ok

# Newest decision file (last 5 min)
DECISION=$(find "$TRIAGE_DIR" -maxdepth 1 -name '*.md' -mmin -5 2>/dev/null \
  | grep -vE 'README|index' | head -1)
[[ -n "$DECISION" ]] || ok

missing=()
required_fields=( lane next_slash_command reasoning refused_paths honest_limits )

for field in "${required_fields[@]}"; do
  val=$(awk -v f="$field" '
    /^---$/{n++; next}
    n==1 && $0 ~ "^"f":" {
      sub("^"f":[[:space:]]*", "")
      print; exit
    }
  ' "$DECISION" | tr -d '"' | xargs)
  if [[ -z "$val" || "$val" == "TODO" || "$val" == "n/a" ]]; then
    missing+=( "$field" )
  fi
done

# Lane value must be in allowed set
lane_val=$(awk '/^---$/{n++; next} n==1 && /^lane:/' "$DECISION" \
  | sed -E 's/^lane:[[:space:]]*//' | tr -d '"' | xargs)
case "$lane_val" in
  lane-1-express|lane-2-quick-dev|lane-3-full-slice|lane-4-ad-hoc|refused) : ;;
  "") : ;;  # already in missing
  *) missing+=( "lane='$lane_val' not in allowed set (lane-1-express|2-quick-dev|3-full-slice|4-ad-hoc|refused)" ) ;;
esac

if [[ ${#missing[@]} -gt 0 ]]; then
  log_event "triage-decision-validate" "WARN" "$(basename "$DECISION"): ${missing[*]}"
  "$HOOK_DIR/notify.sh" warn false \
    "Triage decision file incomplete" \
    "File: ${DECISION#$SPEC/}
Missing/invalid fields:
$(printf '  - %s\n' "${missing[@]}")

Re-run /ntapp-feature-triage hoặc edit file để complete front-matter:
---
lane: lane-N-...
next_slash_command: /...
reasoning: <why this lane>
refused_paths: <which lanes refused + why>
honest_limits: <what triage can't detect>
---" \
    --mention "@dev"

  block "Triage decision file incomplete — workflow can't dispatch.
$(basename "$DECISION") missing: ${missing[*]}"
fi

log_event "triage-decision-validate" "PASS" "$(basename "$DECISION")"
ok
