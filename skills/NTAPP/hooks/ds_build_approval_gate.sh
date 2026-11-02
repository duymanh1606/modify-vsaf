#!/usr/bin/env bash
# Hook 5b — ds-build-approval-gate
# Event: UserPromptSubmit trước /ntapp-ds-build-component.
# Check: decision record cho ID có status ∈ {approved, auto_approved}.
#        Nếu pending → block (1 lần, an toàn — do người resubmit, không livelock).
# Cặp với ds_delta_router.sh (Hook 5): Hook 5 chỉ GHI record + notify (không block-on-Stop);
# enforcement thật nằm ở ĐÂY. Đây là hiện thân của nguyên tắc
# "cổng chờ-người luôn đặt ở UserPromptSubmit, không bao giờ ở Stop".

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable

INPUT="$(read_stdin_json)"
PROMPT="$(json_get "$INPUT" '.prompt')"

echo "$PROMPT" | grep -qE '/ntapp-ds-build-component' || ok

SPEC="$(get_spec_repo_root)"

# Multi-DS aware (_shared/ds-resolution.md nhánh D): decision record nằm trong
# {ds_root}/feature_deltas/{id}/ của DS bất kỳ — tra qua ds_roots/find_unit_delta_dir.
HAS_DELTAS=0
while IFS= read -r dsr; do
  [[ -d "$dsr/feature_deltas" ]] && { HAS_DELTAS=1; break; }
done < <(ds_roots)
[[ "$HAS_DELTAS" == 1 ]] || ok

# status: của decision record
status_of() {
  awk '/^---$/{n++; next} n==1 && /^status:/{sub(/^status:[[:space:]]*/,""); print; exit}' "$1" \
    | tr -d '"' | xargs
}

# Parse ID từ prompt: token sau /ntapp-ds-build-component
ID=$(echo "$PROMPT" | grep -oE '/ntapp-ds-build-component[[:space:]]+[A-Za-z0-9_-]+' \
  | head -1 | awk '{print $2}')

declare -a pending=()

if [[ -n "$ID" ]]; then
  tdir="$(find_unit_delta_dir "$ID")" || tdir=""
  DEC="${tdir:+$tdir/ds_delta_decision.md}"
  if [[ -n "$DEC" && -f "$DEC" ]]; then
    st=$(status_of "$DEC")
    [[ "$st" == "approved" || "$st" == "auto_approved" ]] || pending+=( "$ID (status: ${st:-none})" )
  fi
  # delta dir / file missing → không có NEW delta nào được flag cho ID → cho qua
else
  # Không parse được ID → quét mọi record còn pending trên mọi DS root
  while IFS= read -r dsr; do
    [[ -d "$dsr/feature_deltas" ]] || continue
    while IFS= read -r f; do
      st=$(status_of "$f")
      [[ "$st" == "approved" || "$st" == "auto_approved" ]] \
        || pending+=( "$(basename "$(dirname "$f")") (status: ${st:-none})" )
    done < <(find "$dsr/feature_deltas" -maxdepth 3 -name 'ds_delta_decision.md' 2>/dev/null)
  done < <(ds_roots)
fi

if [[ ${#pending[@]} -gt 0 ]]; then
  log_event "ds-build-approval-gate" "BLOCK" "${pending[*]}"
  block "DS delta chưa được duyệt — không thể chạy /ntapp-ds-build-component:
  - $(printf '%s\n  - ' "${pending[@]}")
Duyệt tay: đổi 'status: approved' + approved_by/at trong ds_delta_decision.md tương ứng.
Hoặc bật auto-approve: .bmm-config.yaml → ntapp-ds-build-component.ds_delta_auto_approve: true,
rồi re-run /ntapp-ui-generation để ghi lại record (hoặc sửa status thủ công)."
fi

log_event "ds-build-approval-gate" "PASS" "${ID:-all}"
ok
