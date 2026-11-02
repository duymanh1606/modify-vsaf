#!/usr/bin/env bash
# Hook 8 — atdd-classifier (decision point ⛔)
# Event: UserPromptSubmit before /bmad-dev-story.
# Logic: risk/structure triggers → Mandatory; else Fallback soft-signal → QA
#        judgment (advisory, non-blocking); else Optional.
#
# Canonical criteria (single source of truth):
#   docs/Process/Manual_phase_1.md §5.1 "Phân loại Mandatory ATDD".
#   Nhóm A (test-level necessity): A1 cross-system · A2 multi-actor/stateful · A3 async/resilience.
#   Nhóm B (blast-radius):         B1 critical-domain (money|auth|RBAC|PII/audit) · B2 destructive.
#   match ≥1 (A* hoặc B*) → Mandatory. Bugfix-regression KHÔNG ở gate này (pipeline bugfix riêng).

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable

INPUT="$(read_stdin_json)"
PROMPT="$(json_get "$INPUT" '.prompt')"

# Chỉ gate formal story path. /bmad-quick-dev (Lane 2 / Path B) cố ý skip ATDD —
# KHÔNG classify nó (tránh cross-lane contamination).
echo "$PROMPT" | grep -qE '/bmad-dev-story' || ok

SPEC="$(get_spec_repo_root)"
STORY_DIR="$SPEC/NTAPP-output/Stage_5_Build_Verify"

# Tìm story file referenced trong prompt; fallback — story mới nhất (≤120 phút,
# rộng hơn để sống sót qua HITL gate trước đó).
STORY_REF=$(echo "$PROMPT" | grep -oE '[^[:space:]]+\.md' | head -1)
if [[ -n "$STORY_REF" && -f "$STORY_REF" ]]; then
  STORY="$STORY_REF"
elif [[ -n "$STORY_REF" && -f "$STORY_DIR/$STORY_REF" ]]; then
  STORY="$STORY_DIR/$STORY_REF"
else
  STORY=$(find "$STORY_DIR" -maxdepth 1 -name '*.md' -mmin -120 \
    ! -name '_*' 2>/dev/null | head -1)
fi

[[ -n "$STORY" && -f "$STORY" ]] || ok

# ─── Front-matter override: quyết định Fallback đã ghi của QA Lead luôn thắng ──
fm=$(grep -iE '^atdd:[[:space:]]*(mandatory|optional)' "$STORY" | head -1)
if echo "$fm" | grep -qiE 'optional'; then
  log_event "atdd-classifier" "OPTIONAL-OVERRIDE" "$(basename "$STORY")"
  echo "[ATDD: Optional] $(basename "$STORY") — QA override (front-matter atdd: optional)." >&2
  ok
fi
if echo "$fm" | grep -qiE 'mandatory'; then
  log_event "atdd-classifier" "MANDATORY-OVERRIDE" "$(basename "$STORY")"
  echo "[ATDD: Mandatory] $(basename "$STORY") — QA override. Đảm bảo /bmad-testarch-atdd đã chạy." >&2
  ok
fi

# ─── Trigger sets (word-boundary để tránh false-positive substring) ──────────
matches=()

# A1 — Cross-system: ≥2 distinct service/module prefix (proxy cho "≥2 service").
PREFIX_PAT="${ATDD_MODULE_PREFIX_PATTERN:-HUB|MPF|PCM|PMT|POL|INT}"
prefixes=$(grep -oE "\b(${PREFIX_PAT})-[A-Z0-9_]+" "$STORY" 2>/dev/null \
  | sed -E 's/-.*//' | sort -u | wc -l | xargs)
[[ "${prefixes:-0}" -ge 2 ]] && matches+=( "A1 cross-system (${prefixes} services)" )

# A2 — Multi-actor stateful workflow (tổng quát hoá "approval" → mọi flow đa-actor/đa-trạng-thái).
if grep -qiE '\b(approval|approve|multi-actor|multi-step|hand-?off|escalat[a-z]*|sign-?off|state[- ]machine)\b' "$STORY" \
   || grep -qiE 'phê duyệt|đa bước|nhiều actor|chuyển trạng thái|đồng ký|nhiều bên' "$STORY"; then
  matches+=( "A2 multi-actor/stateful" )
fi

# A3 — Async / eventual-consistency / resilience.
if grep -qiE '\b(async|asynchronous|queue|retry|retries|eventual|webhook|idempoten[ct][a-z]*|circuit[- ]breaker|saga|outbox)\b' "$STORY" \
   || grep -qiE 'bất đồng bộ|hàng đợi|cơ chế thử lại|nhất quán cuối|phục hồi lỗi' "$STORY"; then
  matches+=( "A3 async/resilience" )
fi

# B1 — Critical domain (danh sách hợp nhất: money | auth | RBAC | PII/audit-compliance).
grep -qiE '\b(money|billing|currency|payment|invoice|refund|ledger|settlement)\b' "$STORY" \
  || grep -qiE 'tiền|thanh toán|tài chính|hóa đơn|hoá đơn' "$STORY" \
  && matches+=( "B1 money/billing" )
grep -qiE '\b(auth|authentication|authorization|login|logout|session|oauth|sso)\b' "$STORY" \
  || grep -qiE 'xác thực|đăng nhập|phiên đăng nhập' "$STORY" \
  && matches+=( "B1 auth" )
grep -qiE '\b(rbac|permission|role-based|privilege|access[- ]control)\b' "$STORY" \
  || grep -qiE 'phân quyền|quyền truy cập' "$STORY" \
  && matches+=( "B1 RBAC/permission" )
grep -qiE '\b(pii|audit[- ]log|audit[- ]trail|compliance|gdpr|sensitive[- ]data)\b' "$STORY" \
  || grep -qiE 'nhật ký kiểm toán|dữ liệu nhạy cảm|tuân thủ' "$STORY" \
  && matches+=( "B1 PII/audit/compliance" )

# B2 — Destructive / irreversible.
if grep -qiE '\b(delete|drop|truncate|purge|bulk[- ](update|delete)|migration|migrate|irreversible|hard[- ]delete|cascade)\b' "$STORY" \
   || grep -qiE 'xóa hàng loạt|xoá hàng loạt|không hồi phục|di trú dữ liệu|ghi đè dữ liệu' "$STORY"; then
  matches+=( "B2 destructive/irreversible" )
fi

# Dedup matches (B1 có thể match nhiều domain — gộp để log gọn).
if [[ ${#matches[@]} -ge 1 ]]; then
  uniq_matches=$(printf '%s\n' "${matches[@]}" | awk '!seen[$0]++' | paste -sd '; ' -)
  log_event "atdd-classifier" "MANDATORY" "$(basename "$STORY"): $uniq_matches"
  echo "[ATDD: Mandatory] $(basename "$STORY") matched: $uniq_matches. Chạy /bmad-testarch-atdd TRƯỚC /bmad-dev-story." >&2
  ok
fi

# ─── Fallback: không khớp trigger cứng, nhưng soft-signal gợi ý thiệt hại đo được.
# Hook không tự phán "thiệt hại đo được" → surface QA Lead (advisory, non-blocking).
if grep -qiE 'wallet|balance|debit|credit|quota|external|third-party' "$STORY" \
   || grep -qiE 'số dư|hạn mức|báo cáo tài chính|bên thứ ba|nhà cung cấp' "$STORY"; then
  log_event "atdd-classifier" "FALLBACK-REVIEW" "$(basename "$STORY")"
  "$HOOK_DIR/notify.sh" decision_required false \
    "ATDD fallback review — $(basename "$STORY")" \
    "Story: ${STORY#$SPEC/}
Không khớp trigger cứng A/B, nhưng có soft-signal gợi ý rủi ro thiệt hại đo được.
QA Lead áp Fallback rule: fail gây thiệt hại tiền/dữ liệu/uy tín ĐO ĐƯỢC, hoặc có audit requirement?
  Có    → ghi 'atdd: mandatory' vào front-matter story → chạy /bmad-testarch-atdd trước.
  Không → ghi 'atdd: optional' → tiếp tục /bmad-dev-story." \
    --mention "@QA"
  echo "[ATDD: Fallback review] $(basename "$STORY") — soft-signal, QA Lead judgment (non-blocking). Default Optional nếu không phản hồi." >&2
  ok
fi

log_event "atdd-classifier" "OPTIONAL" "$(basename "$STORY")"
echo "[ATDD: Optional] $(basename "$STORY") — không khớp trigger A/B." >&2
ok
