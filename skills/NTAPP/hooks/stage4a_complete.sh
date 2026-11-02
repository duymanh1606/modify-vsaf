#!/usr/bin/env bash
# Hook 4 — stage4a-completeness
# Event: SubagentStop after /ntapp-feature-design.
# Check: required sections in {id}_detailed_design.md.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable

INPUT="$(read_stdin_json)"
TRANSCRIPT="$(json_get "$INPUT" '.transcript_path')"

# Identify which DD was just written. Strategy:
#   1. Inspect git working tree for unstaged DD files modified in last N seconds.
#   2. Fallback — find newest *_detailed_design.md in stage 4 dir.

SPEC="$(get_spec_repo_root)"
DD_DIR="$SPEC/NTAPP-output/Stage_4_Design/detailed_design"

[[ -d "$DD_DIR" ]] || ok  # no DD ever written → not our concern

# Driver (Antigravity host) may pin the exact unit via HOOK_TARGET_ID — deterministic in
# parallel fanout. Else fall back to the newest DD (last 5 min) — Claude SubagentStop path.
if [[ -n "${HOOK_TARGET_ID:-}" && -f "$DD_DIR/${HOOK_TARGET_ID}_detailed_design.md" ]]; then
  DD_FILE="$DD_DIR/${HOOK_TARGET_ID}_detailed_design.md"
else
  DD_FILE=$(find "$DD_DIR" -maxdepth 1 -name '*_detailed_design.md' -mmin -5 2>/dev/null \
    | head -1)
fi

[[ -n "$DD_FILE" ]] || ok  # nothing new → not our SubagentStop

ID=$(basename "$DD_FILE" | sed -E 's/_detailed_design\.md$//')
is_fe_unit="false"
[[ "$ID" =~ ^(SCR|WGT)- ]] && is_fe_unit="true"

missing=()

grep -qE '^## *1\.|§ *1\.|^# *1 ' "$DD_FILE" \
  || grep -qiE 'tổng quan|overview' "$DD_FILE" \
  || missing+=( "§1 Tổng quan & Ranh giới" )

grep -qiE 'logic[[:space:]]*matrix' "$DD_FILE" \
  || missing+=( "§3.2 Logic Matrix" )

grep -qE 'P0' "$DD_FILE" \
  || missing+=( "§5.2 KBKT (no P0 case)" )

if [[ "$is_fe_unit" == "true" ]]; then
  grep -qiE 'wireframe' "$DD_FILE" \
    || missing+=( "§2.2 Wireframe" )
  grep -qiE 'icon[[:space:]]*legend' "$DD_FILE" \
    || missing+=( "Icon Legend table (FE unit)" )
  grep -qiE 'ui[[:space:]]+control' "$DD_FILE" \
    || missing+=( "§2.3 UI Controls table" )

  # Layout Groups required if wireframe has ≥2 sibling controls
  if grep -qiE '\[(input|button|select|text|chip|tab)_' "$DD_FILE"; then
    grep -qiE 'layout[[:space:]]*group' "$DD_FILE" \
      || missing+=( "Layout Groups table (wireframe has multi-control)" )
  fi
fi

# ── TRANSCRIBE vision gate ────────────────────────────────────────────────
# Figma mapped cho unit này → DD BẮT BUỘC có bảng [FRAMES VIEWED] trong §2.5
# (step-02 §0b nghĩa vụ 6). Ảnh là kênh duy nhất chở radius/viền/canh lề/tỉ lệ và
# nó RỜI pipeline sau 4a — 4b đọc DD, Stage 5 đọc ui_schema + DD, không ai mở lại
# PNG. Bỏ xem ảnh ở đây thì không tầng nào phía sau phát hiện được: DD vẫn đủ
# section, code vẫn chạy, chỉ giao diện là sai. Vì thế đây là check duy nhất
# trong hook này được BLOCK (phần còn lại warn-only — xem cuối file).
# Read-only, 0 network. Kill switch: DISABLE_FIGMA_TRANSCRIBE_GATE=1
figma_transcribe_gate() {
  [[ "${DISABLE_FIGMA_TRANSCRIBE_GATE:-0}" == "1" ]] && return 0
  [[ "$is_fe_unit" == "true" ]] || return 0

  local mf="" r
  while IFS= read -r r; do
    [[ -f "$r/_reference/figma/figma-manifest.yaml" ]] || continue
    if awk -v w="$ID" \
         '$1=="-" && $2=="unit_id:" {inblk=($3==w || $3=="\""w"\"")} inblk{print}' \
         "$r/_reference/figma/figma-manifest.yaml" | grep -q 'figma_status:'; then
      mf="$r/_reference/figma/figma-manifest.yaml"; break
    fi
  done < <(ds_roots)

  [[ -n "$mf" ]] || return 0   # không có manifest / unit không có entry → AUTHOR mode

  local blk status
  blk="$(awk -v w="$ID" \
    '$1=="-" && $2=="unit_id:" {inblk=($3==w || $3=="\""w"\"")} inblk{print}' "$mf")"
  status="$(printf '%s\n' "$blk" | grep -m1 'figma_status:' \
    | sed -E 's/.*figma_status:[[:space:]]*//' | tr -d '\042\047' | xargs)"

  # Chỉ mapped mới vào TRANSCRIBE mode. missing/stale/not_in_scope/ignored → author.
  [[ "$status" == "mapped" ]] || return 0

  # Số state đã export PNG — mỗi state cần 1 dòng trong bảng.
  local want
  want="$(printf '%s\n' "$blk" | grep -c 'frame_exported:[[:space:]]*true' || true)"
  [[ "$want" -gt 0 ]] || want=1

  if ! grep -qE '\[FRAMES VIEWED\]' "$DD_FILE"; then
    log_event "stage4a-completeness" "BLOCK" "$ID: missing [FRAMES VIEWED]"
    block "Stage 4a TRANSCRIBE — $ID thiếu bảng [FRAMES VIEWED] trong §2.5

figma_status: mapped → F3 phải MỞ từng frame PNG (vision) và ghi bằng chứng, 1 dòng/state:
  | State | Frame | Quan sát thị giác (KHÔNG suy được từ JSON) |

Cột 3 phải là thứ chỉ thấy bằng mắt (canh lề thật, vai trò bo góc, có/không viền,
tỉ lệ, phần tử nào cùng hàng). Cấm chép lại JSON, cấm câu rỗng 'đã xem, khớp specs'.

Vì sao chặn: ảnh rời pipeline sau bước này — 4b đọc DD, Stage 5 đọc ui_schema + DD,
không ai mở lại PNG. Thiếu bước xem ảnh thì không gate nào phía sau bắt được.
Chi tiết: .agent/skills/NTAPP-feature-design/steps/step-02-ui-interaction-design.md §0b nghĩa vụ 6
Bỏ qua (không khuyến nghị): DISABLE_FIGMA_TRANSCRIBE_GATE=1"
  fi

  # Đếm dòng bảng: dòng markdown có 3 dấu | và trỏ tới frames/*.png (hoặc export fail).
  local rows
  rows="$(grep -cE '^[[:space:]]*\|.*\|.*(frames/[^|]*\.png|export fail).*\|' "$DD_FILE" || true)"
  if [[ "$rows" -lt "$want" ]]; then
    log_event "stage4a-completeness" "BLOCK" "$ID: [FRAMES VIEWED] $rows/$want rows"
    block "Stage 4a TRANSCRIBE — $ID: bảng [FRAMES VIEWED] chỉ có $rows dòng, manifest có $want state đã export PNG

Xem TẤT CẢ state, không chỉ default — mandatory-states audit (L2) dựa vào đây.
State nào PNG lỗi: vẫn 1 dòng, cột Frame ghi '— (export fail)'.
Bỏ qua: DISABLE_FIGMA_TRANSCRIBE_GATE=1"
  fi

  # Câu rỗng — bắt đúng các mẫu đã thấy trong thực tế.
  if grep -qiE '\|[^|]*(đã xem[,.]? *khớp|bố cục như mô tả|khớp (với )?specs?|no observation|nothing notable)[^|]*\|' "$DD_FILE"; then
    log_event "stage4a-completeness" "BLOCK" "$ID: [FRAMES VIEWED] filler text"
    block "Stage 4a TRANSCRIBE — $ID: cột quan sát của [FRAMES VIEWED] có câu rỗng

'đã xem, khớp specs' / 'bố cục như mô tả' không phải quan sát — nó không chứa thông
tin nào mà specs JSON chưa có. Ghi thứ CHỈ thấy bằng mắt, hoặc thú nhận thẳng
'không quan sát thêm được gì ngoài specs' cho state đó.
Bỏ qua: DISABLE_FIGMA_TRANSCRIBE_GATE=1"
  fi

  log_event "stage4a-completeness" "PASS" "$ID: [FRAMES VIEWED] $rows/$want"
  return 0
}

figma_transcribe_gate

if [[ ${#missing[@]} -gt 0 ]]; then
  log_event "stage4a-completeness" "WARN" "$ID: ${missing[*]}"
  "$HOOK_DIR/notify.sh" warn false \
    "Stage 4a DD incomplete — $ID" \
    "Sections missing: $(printf '%s; ' "${missing[@]}")
Re-run /ntapp-feature-design to fill, or edit by hand if minor." \
    --mention "@SeniorDev"
  # Don't block — DD quality is partial inferential; notify only
  ok
fi

log_event "stage4a-completeness" "PASS" "$ID"
ok
