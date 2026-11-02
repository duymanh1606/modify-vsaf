#!/usr/bin/env bash
# Hook 7 — story-bridge-gate
# Event: SubagentStop after /bmad-create-story.
# Check: story has AC + Tasks + Dev Notes + Testing + slice_id referencing
#        existing SLICE-N manifest.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable
. "$HOOK_DIR/lib/entry_mode.sh"
stop_reentry_guard "story-bridge-gate"

SPEC="$(get_spec_repo_root)"
STORY_DIR="$SPEC/NTAPP-output/Stage_5_Build_Verify"
SLICES_DIR="$SPEC/NTAPP-output/Stage_2_Architecture/slices"

[[ -d "$STORY_DIR" ]] || ok

# Driver (Antigravity host) may pin the exact story via HOOK_TARGET_ID — deterministic in
# parallel fanout (this gate BLOCKS, so picking the right story matters). Else newest (Claude).
if [[ -n "${HOOK_TARGET_ID:-}" && -f "$STORY_DIR/${HOOK_TARGET_ID}.md" ]]; then
  STORY="$STORY_DIR/${HOOK_TARGET_ID}.md"
else
  STORY=$(find "$STORY_DIR" -maxdepth 1 -name '*.md' -mmin -5 \
    ! -name '_*' ! -name 'sprint-status.yaml' 2>/dev/null | head -1)
fi
[[ -n "$STORY" ]] || ok

problems=()

grep -qiE '^## *Acceptance Criteria|^### *Acceptance Criteria' "$STORY" \
  || problems+=( "Acceptance Criteria section missing" )
grep -qiE '^## *Tasks|^### *Tasks|^## *Tasks ?/ ?Subtasks' "$STORY" \
  || problems+=( "Tasks/Subtasks section missing" )
grep -qiE '^## *Dev Notes|^### *Dev Notes' "$STORY" \
  || problems+=( "Dev Notes section missing" )
grep -qiE '^## *Testing|^### *Testing|^## *Testing Requirements' "$STORY" \
  || problems+=( "Testing Requirements section missing" )

# slice_id check — skip in stage_4_standalone (no slice plan)
mode="$(entry_mode)"
if [[ "$mode" == "full" ]]; then
  slice_id=$(grep -E '^slice_id:' "$STORY" | head -1 \
    | sed -E 's/^slice_id:[[:space:]]*//' | tr -d '"' | xargs)
  if [[ -z "$slice_id" ]]; then
    problems+=( "slice_id front-matter missing" )
  # `${slice_id}-*` va KHONG phai `${slice_id}*`: dau gach la thu duy nhat chan
  # SLICE-1 khop nham SLICE-10..19 (do duoc: SLICE-1* = 11 file, SLICE-2* = 7 file
  # tren tap 25 slice hien tai). Nhan ca hai bo cuc: phang (feature dau tien) va
  # long trong thu muc feature (feature ke tiep, xem §3.6).
  elif ! ls "$SLICES_DIR/${slice_id}"-*.md "$SLICES_DIR"/*/"${slice_id}"-*.md \
       >/dev/null 2>&1; then
    problems+=( "slice_id=$slice_id but manifest not in $SLICES_DIR/" )
  fi
fi

if [[ ${#problems[@]} -gt 0 ]]; then
  log_event "story-bridge-gate" "BLOCK" "$(basename "$STORY"): ${problems[*]}"
  block "Story bridge incomplete: $(basename "$STORY")
$(printf '  - %s\n' "${problems[@]}")
Re-run /bmad-create-story or edit story file."
fi

log_event "story-bridge-gate" "PASS" "$(basename "$STORY")"
ok
