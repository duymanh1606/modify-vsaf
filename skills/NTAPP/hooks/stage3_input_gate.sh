#!/usr/bin/env bash
# Hook 3 — stage3-input-gate
# Event: UserPromptSubmit before /ntapp-technical-design, /ntapp-ux-design,
#        /ntapp-feature-design.
# Check: WBS lock + SLICE-N.md exists + HLD + Master DS.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable
. "$HOOK_DIR/lib/entry_mode.sh"

if mode_skips hook3; then ok; fi

INPUT="$(read_stdin_json)"
PROMPT="$(json_get "$INPUT" '.prompt')"

# Only run for triggers below
echo "$PROMPT" | grep -qE '/(ntapp-technical-design|ntapp-ux-design|ntapp-feature-design)' \
  || ok

SPEC="$(get_spec_repo_root)"
WBS="$SPEC/NTAPP-output/Stage_2_Architecture/project_wbs.md"
HLD="$SPEC/NTAPP-output/Stage_2_Architecture/architecture_design.md"
SLICES_DIR="$SPEC/NTAPP-output/Stage_2_Architecture/slices"

missing=()
[[ -f "$WBS" ]]      || missing+=( "project_wbs.md (Stage 2 not done)" )
[[ -f "$HLD" ]]      || missing+=( "architecture_design.md (Stage 2 not done)" )

# Master DS — multi-DS aware (_shared/ds-resolution.md nhánh D): quét mọi DS root
# qua registry (nếu có) thay vì 1 path cứng. Block CHỈ khi KHÔNG system nào bootstrap
# xong (DS B chưa bootstrap không được chặn unit thuộc DS A — warn thôi).
ds_ok=0
ds_not_ready=()
while IFS= read -r dsr; do
  if [[ -f "$dsr/master_token.json" && -f "$dsr/components_metadata.json" ]]; then
    ds_ok=$((ds_ok+1))
  else
    ds_not_ready+=( "${dsr#$SPEC/}" )
  fi
done < <(ds_roots)
if [[ $ds_ok -eq 0 ]]; then
  missing+=( "master_token.json + components_metadata.json — không DS root nào sẵn sàng (Stage 0 not done; checked: ${ds_not_ready[*]:-$(get_design_system_root)})" )
fi

# Slice manifests required only if NOT stage_4_standalone (Hook 3 in standalone
# already short-circuits via mode_skips above for stage_5_standalone; for
# stage_4_standalone we keep DS check, skip slice check).
mode="$(entry_mode)"
if [[ "$mode" == "full" ]]; then
  shopt -s nullglob
  slices=( "$SLICES_DIR"/SLICE-*.md )
  shopt -u nullglob
  [[ ${#slices[@]} -gt 0 ]] || missing+=( "slices/SLICE-*.md (Stage 2b not done)" )
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  log_event "stage3-input-gate" "BLOCK" "${missing[*]}"
  block "Stage 3 prerequisites missing:
  - $(printf '%s\n  - ' "${missing[@]}")
Run upstream stages first, or declare .bmm-entry-mode if intentional."
fi

# Multi-DS: có system chưa bootstrap → warn advisory (không block — unit thuộc DS đó
# sẽ tự STOP ở pre-flight skill khi resolve DS root thiếu artifact).
if [[ $ds_ok -gt 0 && ${#ds_not_ready[@]} -gt 0 ]]; then
  log_event "stage3-input-gate" "PASS-PARTIAL-DS" "${ds_not_ready[*]}"
  echo "[HOOK WARN] DS chưa bootstrap: ${ds_not_ready[*]} — unit thuộc DS này cần /ntapp-ds-bootstrap trước." >&2
fi

# ─── Figma drift gate (read-only, 0 network) ─────────────────────────
# Đây là TOÀN BỘ phần Figma nằm trong slice-loop: so checksum trong DD (figma_ref)
# với figma-manifest.yaml hiện tại. Ingest chạy NGOÀI loop (/ntapp-figma-ingest) —
# hook không bao giờ gọi Figma, không cần PAT.
# Tắt riêng: DISABLE_FIGMA_DRIFT_GATE=1.
# Multi-DS: nhánh D của _shared/ds-resolution.md — quét ds_roots bằng glob, KHÔNG parse WBS.
figma_drift_gate() {
  is_true "${DISABLE_FIGMA_DRIFT_GATE:-}" && return 0

  # Chỉ áp cho feature-design (Stage 4a là nơi DD ghi figma_ref).
  echo "$PROMPT" | grep -qE '/ntapp-feature-design' || return 0

  local unit_id
  unit_id="$(echo "$PROMPT" | grep -oE '\b(SCR|WGT)-[A-Z0-9][A-Z0-9-]*' | head -1)"
  [[ -n "$unit_id" ]] || return 0   # không nêu unit FE trong prompt → không có gì so

  local dd="$SPEC/NTAPP-output/Stage_4_Design/detailed_design/${unit_id}_detailed_design.md"
  [[ -f "$dd" ]] || return 0        # DD chưa có (lần đầu) → không có baseline

  # Tìm manifest chứa unit này (ID global-unique → tối đa 1 hit)
  local mf="" dsr
  while IFS= read -r dsr; do
    local cand="$dsr/_reference/figma/figma-manifest.yaml"
    if [[ -f "$cand" ]] && awk -v w="$unit_id" \
         '$1=="-" && $2=="unit_id:" && ($3==w || $3=="\""w"\""){f=1} END{exit !f}' "$cand"; then
      mf="$cand"; break
    fi
  done < <(ds_roots)

  local dd_sum mf_sum mf_status blk
  dd_sum="$(grep -m1 -i 'figma_ref' "$dd" 2>/dev/null | grep -oE 'sha256:[0-9a-f]+' || true)"

  if [[ -z "$mf" ]]; then
    # DD nói mình transcribe từ Figma nhưng không còn manifest nào khai unit này.
    if [[ -n "$dd_sum" ]]; then
      log_event "stage3-input-gate" "WARN-FIGMA-MANIFEST-MISSING" "$unit_id"
      echo "[HOOK WARN] DD $unit_id có figma_ref nhưng không tìm thấy figma-manifest.yaml khai unit này. Manifest bị xoá hay chưa commit? Chạy lại /ntapp-figma-ingest nếu design vẫn là nguồn." >&2
    fi
    return 0
  fi

  blk="$(awk -v w="$unit_id" \
    '$1=="-" && $2=="unit_id:" {inblk=($3==w || $3=="\""w"\"")} inblk{print}' "$mf")"
  mf_sum="$(printf '%s\n' "$blk" | grep -m1 -oE 'sha256:[0-9a-f]+' || true)"
  mf_status="$(printf '%s\n' "$blk" | grep -m1 -E '^[[:space:]]*figma_status:' \
                | sed -E 's/^[[:space:]]*figma_status:[[:space:]]*//' \
                | tr -d '\042\047' | xargs || true)"

  # not_in_scope = lần ingest gần nhất KHÔNG xét unit này (scope hẹp) → không có
  # checksum hiện hành để so. DD đã transcribe từ Figma → chưa verify được drift.
  # WARN chứ không block: entry cũ vẫn hợp lệ, chỉ là chưa được xác nhận lại.
  if [[ "$mf_status" == "not_in_scope" ]]; then
    if [[ -n "$dd_sum" ]]; then
      log_event "stage3-input-gate" "WARN-FIGMA-NOT-IN-SCOPE" "$unit_id"
      echo "[HOOK WARN] Unit $unit_id: manifest ghi figma_status=not_in_scope (lần ingest gần nhất không phủ unit này) nhưng DD có figma_ref → chưa verify được drift. Muốn chắc: chạy /ntapp-figma-ingest với scope phủ unit này (vd --feature <tên> hoặc scope_pages tương ứng)." >&2
    fi
    return 0
  fi

  # Unit không được map (missing/stale) → 4a chạy author mode, không có gì để drift.
  [[ "$mf_status" == "mapped" ]] || return 0

  if [[ -z "$dd_sum" ]]; then
    # DD author trước khi ingest — advisory, KHÔNG block (author mode vẫn là output hợp lệ).
    log_event "stage3-input-gate" "WARN-FIGMA-NOT-TRANSCRIBED" "$unit_id"
    echo "[HOOK WARN] Unit $unit_id đã có frame Figma (manifest: mapped) nhưng DD hiện tại KHÔNG có figma_ref → DD được author trước khi ingest. Cân nhắc refresh DD ở TRANSCRIBE mode để khớp design." >&2
    return 0
  fi

  if [[ -n "$mf_sum" && "$dd_sum" != "$mf_sum" ]]; then
    log_event "stage3-input-gate" "BLOCK-FIGMA-DRIFT" "$unit_id dd=$dd_sum mf=$mf_sum"
    block "Figma drift — unit $unit_id:
  - DD ($(basename "$dd")) transcribe từ:  $dd_sum
  - figma-manifest.yaml hiện tại:          $mf_sum
Design đã đổi sau khi DD được ký. Chạy /ntapp-figma-ingest (NGOÀI slice-loop) để re-ingest,
rồi refresh DD (bump dd_version) trước khi tiếp tục. Bỏ qua có chủ ý: DISABLE_FIGMA_DRIFT_GATE=1."
  fi
}
figma_drift_gate

log_event "stage3-input-gate" "PASS"
ok
