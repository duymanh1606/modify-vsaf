#!/usr/bin/env bash
# Hook 1 — approval-gate
# Event: UserPromptSubmit
# Trigger: skill thuộc stage cao hơn → check stage thấp đã approved chưa.
# Check: front-matter `approved_by:` + `approved_at:` trong file gate.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable
. "$HOOK_DIR/lib/entry_mode.sh"

if mode_skips hook1; then ok; fi

INPUT="$(read_stdin_json)"
PROMPT="$(json_get "$INPUT" '.prompt')"
SPEC="$(get_spec_repo_root)"

declare -a GATE_FILES=()
S1="$SPEC/NTAPP-output/Stage_1_Discovery"

if echo "$PROMPT" | grep -qE '/(ntapp-architecture-design|ntapp-system-overview)'; then
  GATE_FILES=( "$S1/prd.md" "$S1/epics.md" )

  # Brownfield reproduce (Stage 2 as-is dung lai tu code — workflow NTAPP/reproduce_architecture): PRD/Epics
  # KHONG phai tien dieu kien, vi tai lieu dang mo ta he thong DANG CHAY chu khong phai intent tuong lai.
  # Relax TU DONG chi khi ca 2 file VANG MAT (khong co gi de ky) VA co bang chung brownfield: marker
  # NTAPP-output/.reproduce-mode (node input-gate cua workflow ghi) hoac baseline system_overview da sinh.
  # File ton tai nhung chua ky -> van BLOCK: Stage 1 da chay thi phai ky (giu ky luat greenfield).
  # BROWNFIELD_REPRODUCE=1 = escape tay, override ca truong hop file ton tai chua ky.
  brownfield_evidence=false
  [[ -f "$SPEC/NTAPP-output/.reproduce-mode" ]] && brownfield_evidence=true
  if [[ -n "$(find "$S1/system_overview" -maxdepth 1 -name '*.md' -print -quit 2>/dev/null)" ]]; then
    brownfield_evidence=true
  fi

  if is_true "${BROWNFIELD_REPRODUCE:-}"; then
    log_event "approval-gate" "RELAX" "BROWNFIELD_REPRODUCE=1 (escape tay)"
    warn_pass "BROWNFIELD_REPRODUCE=1 — bo qua Stage 1 gate (PRD/Epics) cho lan chay nay."
  fi
  if [[ ! -f "$S1/prd.md" && ! -f "$S1/epics.md" ]] && $brownfield_evidence; then
    log_event "approval-gate" "RELAX" "brownfield reproduce — khong co PRD/Epics de gate"
    warn_pass "Brownfield reproduce: khong co prd.md/epics.md -> bo qua Stage 1 gate.
Stage 2 as-is doc evidence tu code (system_overview baseline), khong doc yeu cau.
Muon enforce lai: tao prd.md + epics.md co approved_by/approved_at roi chay lai."
  fi
elif echo "$PROMPT" | grep -qE '/(ntapp-slice-planning|ntapp-technical-design|ntapp-ux-design)'; then
  GATE_FILES=( "$SPEC/NTAPP-output/Stage_2_Architecture/architecture_design.md"
               "$SPEC/NTAPP-output/Stage_2_Architecture/00_system_connectivity_integration.md"
               "$SPEC/NTAPP-output/Stage_2_Architecture/project_wbs.md" )
else
  ok
fi

missing=()
for f in "${GATE_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    missing+=( "$f (file missing)" )
    continue
  fi
  approved_by=$(awk '/^---$/{n++; next} n==1 && /^approved_by:/' "$f" | head -1 \
    | sed -E 's/^approved_by:[[:space:]]*//' | tr -d '"' | xargs)
  approved_at=$(awk '/^---$/{n++; next} n==1 && /^approved_at:/' "$f" | head -1 \
    | sed -E 's/^approved_at:[[:space:]]*//' | tr -d '"' | xargs)
  if [[ -z "$approved_by" || -z "$approved_at" ]]; then
    missing+=( "$(basename "$f") (no approved_by/at)" )
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  log_event "approval-gate" "BLOCK" "${missing[*]}"
  block "Stage gate not approved. Files thiếu approval signature:
  - $(printf '%s\n  - ' "${missing[@]}")
Approve bằng cách thêm front-matter:
    ---
    approved_by: <user>
    approved_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
    ---
into each file above, then re-run."
fi

log_event "approval-gate" "PASS"
ok
