#!/usr/bin/env bash
# Hook 5 — ds-delta-router (decision RECORDER — KHÔNG block-on-Stop)
# Event: SubagentStop after /ntapp-ui-generation.
# Behavior: parse proposed_ds_updates.md → nếu [NEW] non-empty thì GHI decision record
#           (pending | auto_approved tùy config) + notify DSO, rồi để agent dừng bình thường.
# Enforcement THẬT (chặn /ntapp-ds-build-component khi pending) nằm ở ds_build_approval_gate.sh
# (Hook 5b, UserPromptSubmit) — nơi "chặn = từ chối 1 prompt", đúng bản chất chờ-người,
# KHÔNG gây livelock như block-on-Stop trước đây.
#
# Auto-approve: env DS_DELTA_AUTO_APPROVE=1 hoặc .bmm-config.yaml
#   ntapp-ds-build-component.ds_delta_auto_approve: true  → NEW delta tự duyệt (audit vẫn ghi).

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable

SPEC="$(get_spec_repo_root)"

# Multi-DS aware (_shared/ds-resolution.md nhánh D): quét mọi DS root (registry-aware)
# thay vì 1 path cứng. Driver (Antigravity host) may pin the exact unit via
# HOOK_TARGET_ID — deterministic in parallel fanout (avoids "newest of 4 concurrent
# proposals" race). Else newest (Claude path).
PROPOSAL=""
if [[ -n "${HOOK_TARGET_ID:-}" ]]; then
  tdir="$(find_unit_delta_dir "$HOOK_TARGET_ID")" \
    && [[ -f "$tdir/proposed_ds_updates.md" ]] \
    && PROPOSAL="$tdir/proposed_ds_updates.md"
fi
if [[ -z "$PROPOSAL" ]]; then
  while IFS= read -r dsr; do
    [[ -d "$dsr/feature_deltas" ]] || continue
    PROPOSAL=$(find "$dsr/feature_deltas" -maxdepth 3 -name 'proposed_ds_updates.md' -mmin -5 2>/dev/null \
      | head -1)
    [[ -n "$PROPOSAL" ]] && break
  done < <(ds_roots)
fi

[[ -n "$PROPOSAL" ]] || ok

# Extract [NEW] block content
NEW_BLOCK=$(awk '
  /^\[NEW\]/      { capture=1; next }
  /^\[(MODIFIED|WARNINGS|SUMMARY)\]/ { capture=0 }
  capture && NF   { print }
' "$PROPOSAL")

ID=$(dirname "$PROPOSAL" | xargs basename)
DECISION="$(dirname "$PROPOSAL")/ds_delta_decision.md"

if [[ -z "$NEW_BLOCK" ]]; then
  log_event "ds-delta-router" "PASS-EMPTY" "$ID"
  echo "[DS delta empty] $ID dùng đủ token + component có sẵn. Skip /ntapp-ds-build-component, đi thẳng Stage 4c." >&2
  ok
fi

# ─── Auto-approve? ──────────────────────────────────────────────────
auto_approve=false
if is_true "${DS_DELTA_AUTO_APPROVE:-}" || is_true "$(bmm_config_value ds_delta_auto_approve)"; then
  auto_approve=true
fi

# ─── KHÔNG clobber một approval đã có (DSO duyệt tay rồi) ────────────
existing_status=""
[[ -f "$DECISION" ]] && existing_status=$(awk '
  /^---$/{n++; next} n==1 && /^status:/{sub(/^status:[[:space:]]*/,""); print; exit}
' "$DECISION" | tr -d '"' | xargs)

if [[ "$existing_status" == "approved" || "$existing_status" == "auto_approved" ]] && ! $auto_approve; then
  log_event "ds-delta-router" "ALREADY-${existing_status}" "$ID"
  echo "[DS delta] $ID đã '$existing_status' trước đó — giữ nguyên record, cho qua." >&2
  ok
fi

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if $auto_approve; then
  status="auto_approved"; by="auto"; at="$NOW"
else
  status="pending"; by=""; at=""
fi

# ─── Ghi decision record ────────────────────────────────────────────
mkdir -p "$(dirname "$DECISION")"
{
  echo "---"
  echo "id: $ID"
  echo "status: $status"
  echo "approved_by: $by"
  echo "approved_at: $at"
  echo "recorded_at: $NOW"
  echo "---"
  echo
  echo "# DS Delta Decision — $ID"
  echo
  echo "NEW entries cần duyệt trước khi chạy \`/ntapp-ds-build-component $ID\`:"
  echo
  echo '```'
  echo "$NEW_BLOCK"
  echo '```'
  echo
  echo "**DSO duyệt tay:** đổi \`status: approved\` + điền \`approved_by\`/\`approved_at\` trong file này, rồi chạy \`/ntapp-ds-build-component $ID\`."
  echo "**Bật auto:** \`.bmm-config.yaml\` → \`ntapp-ds-build-component.ds_delta_auto_approve: true\` (audit trail vẫn ghi)."
} > "$DECISION"

# ─── Auto-approved → notify info + pass ─────────────────────────────
if $auto_approve; then
  log_event "ds-delta-router" "AUTO-APPROVED" "$ID"
  "$HOOK_DIR/notify.sh" info false \
    "DS delta AUTO-APPROVED — $ID" \
    "Auto-approve đang BẬT. NEW entries (audit):
$NEW_BLOCK

Record: ${DECISION#$SPEC/}" \
    --mention "@DSO" || true
  echo "[DS delta] $ID — auto-approved. /ntapp-ds-build-component $ID được phép chạy." >&2
  ok
fi

# ─── Pending → notify decision + pass (gate thật ở Hook 5b) ─────────
log_event "ds-delta-router" "PENDING" "$ID"
"$HOOK_DIR/notify.sh" decision_required true \
  "DS delta NEW — $ID (chờ DSO)" \
  "Proposal: ${PROPOSAL#$SPEC/}
NEW entries:
$NEW_BLOCK

Duyệt: đổi 'status: approved' trong ${DECISION#$SPEC/} rồi chạy /ntapp-ds-build-component $ID.
Hoặc revise: edit DD + re-run /ntapp-ui-generation." \
  --mention "@DSO" || true

warn_pass "DS delta $ID có [NEW] — đã ghi decision PENDING + báo DSO. Agent dừng bình thường;
/ntapp-ds-build-component $ID sẽ bị Hook 5b chặn tới khi status=approved (hoặc bật auto-approve)."
