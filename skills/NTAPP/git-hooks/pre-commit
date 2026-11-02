#!/usr/bin/env bash
# Pre-commit hook — NTAPP Phase 1 workflow guardrails
#
# Reference: docs/Process/Manual_phase_1.md §7
#
# Rules:
#   1. File code phải có header `id: <ID>` + `dd_version: vN`. ID prefix phải
#      khớp loại file: UI file dùng `SCR-*` hoặc `WGT-*`; non-UI file dùng
#      prefix khác (vd `MPF-*`, `HUB-*`, `INT-*`).
#   2. `<id>` phải tồn tại trong project_wbs.md (markdown table cột đầu)
#   3. File `{id}_detailed_design.md` phải tồn tại trong spec repo
#   4. UI code không hardcode color hex / px / font name
#   5. (SKIP — semantic check, không automate được)
#   6. UI code: file `ui_schema_{id}.json` phải tồn tại
#   7. Build-component: nếu proposed_ds_updates.md có [NEW], phải có build_report.md
#   8. Repo scope: nếu CLAUDE.md khai báo repo_type=service-only thì commit
#      KHÔNG được đụng infra paths (Dockerfile / CI / helm / terraform / IaC)
#   9. UI files KHÔNG được chứa unicode emoji (block range U+2600-U+27BF +
#      U+1F300-U+1FAFF) trừ khi file có pragma `// allow-emoji` hoặc
#      `<!-- allow-emoji -->` trong 10 dòng đầu. Wireframe emoji là visual hint
#      chỉ tồn tại trong detailed_design.md — Stage 4b đã translate sang
#      icon_bindings trong ui_schema_{id}.json. Code phải đọc icon từ ui_schema.
#
#   Rule 4/6/7 chỉ enforce khi Master DS đã tồn tại (master_token.json trong spec
#   repo). Greenfield build toàn bộ slice trước rồi chuẩn hoá DS sau → skip 4/6/7
#   cho tới pass chuẩn hoá. Brownfield bootstrap DS ở Phase A nên enforce sớm.
#
# Hook skip third-party skill library paths + BMM core
#   (.agent/skills/, .claude/skills/, .cursor/skills/, _bmad/) — đây là skill
#   canonical / IDE cache / BMM bundled core của third-party (BMAD, Superpowers).
#   Không follow NTAPP id header convention → trip Rule 1 là false positive.
#
# Rule 8 đọc marker block trong CLAUDE.md (khai báo bởi bootstrap script).
# Áp dụng cho code repo declare repo_type=service-only. Spec repo / fullstack
# repo / không có scope block → không enforce.
#
# ─── Header schema: unified `id:` ──────────────────────────────────
# Mỗi file code 10 dòng đầu phải có header:
#   // id: <ID> | dd_version: v<N>           (TS/JS/Go/Java/...)
#   # id: <ID> | dd_version: v<N>            (Python/Ruby/Shell)
#   <!-- id: <ID> | dd_version: v<N> -->     (HTML/Vue template)
#
# Loại unit encoded qua ID prefix (không tách key riêng):
#   - SCR-*  = FE screen     → bắt buộc trên UI extension (.tsx/.jsx/.vue/.html/.css/.scss/...)
#   - WGT-*  = FE widget     → bắt buộc trên UI extension
#   - Khác   = BE feature / integration contract / job / etc → bắt buộc trên non-UI extension
#
# UI_ID_PREFIX_PATTERN có thể override per-project nếu convention prefix khác.
#
# Bypass tạm thời: SKIP_PRECOMMIT=1 git commit ...
#   → chỉ dùng cho hotfix khẩn cấp, phải compensate trong 48h

set -uo pipefail

# ─── Config ─────────────────────────────────────────────────────────
CODE_EXTENSIONS='\.(ts|tsx|js|jsx|go|java|kt|py|rs|cs|swift)$'
UI_EXTENSIONS='\.(tsx|jsx|vue|html|css|scss|sass|less)$'

# Paths to EXCLUDE from hook checks (third-party skill libs + BMM core).
# Match by prefix relative to repo root (git diff --name-only output).
EXCLUDED_PATHS='^\.agent/skills/|^\.claude/skills/|^\.cursor/skills/|^_bmad/'

# Header pattern — accept unified `id:` key PLUS legacy prefix-id keys
# (`screen_id:` / `widget_id:` / `feature_id:`). Loại unit vẫn mã hóa qua
# PREFIX của value (SCR-*/WGT-* = UI), không qua tên key. Boundary
# `(^|[^a-zA-Z0-9_])` + whitelist prefix tránh match nhầm `user_id:` /
# `merchant_id:` ... trong code. extract_id dùng `.*id:` nên tự strip cả prefix.
ID_HEADER_PATTERN='(^|[^a-zA-Z0-9_])(screen_|widget_|feature_)?id:[[:space:]]+[A-Za-z0-9_-]+'

# UI file ID prefix whitelist. Override via env if project uses other prefixes.
UI_ID_PREFIX_PATTERN="${UI_ID_PREFIX_PATTERN:-^(SCR|WGT)-}"

# Extra UI-file filename pattern (default empty). Some frameworks put UI
# components in plain `.ts` not covered by UI_EXTENSIONS — e.g. Angular's
# `*.component.ts`. Such files legitimately carry SCR-*/WGT- IDs, but the
# extension-only check would mis-classify them as non-UI. Set this to a regex
# matched against the file path so they are treated as UI for ALL rules
# (1 prefix, 4 token, 6 ui_schema, 9 emoji). Source order:
#   1. env UI_FILE_PATTERN (highest)
#   2. `ui_file_pattern:` in the code repo .bmm-config.yaml (persistent)
#   3. built-in default UI_FILE_PATTERN_DEFAULT (Angular *.component.ts / *.page.ts)
# Chỉ *.component.ts / *.page.ts mới coi là UI — *.service.ts / *.model.ts /
# main.ts ... vẫn là non-UI (prefix ngoài SCR-/WGT-). Override: set env rỗng
# (UI_FILE_PATTERN= ) hoặc ui_file_pattern trong .bmm-config.yaml để đổi phạm vi.
UI_FILE_PATTERN_DEFAULT='\.(component|page)\.ts$'
UI_FILE_PATTERN="${UI_FILE_PATTERN:-}"

# ─── Color codes ────────────────────────────────────────────────────
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
NC=$'\033[0m'

# ─── Bypass check ───────────────────────────────────────────────────
if [[ "${SKIP_PRECOMMIT:-0}" == "1" ]]; then
  echo "${YELLOW}⚠️  SKIP_PRECOMMIT=1 — bỏ qua pre-commit hook (phải compensate trong 48h)${NC}"
  exit 0
fi

# ─── Resolve spec repo root ─────────────────────────────────────────
# Single-repo: spec_root = current repo
# Multi-repo: đọc .bmm-config.yaml để tìm spec_repo_root
get_spec_repo_root() {
  local repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
  local config="$repo_root/.bmm-config.yaml"

  if [[ ! -f "$config" ]]; then
    # Không có config → assume single-repo (this IS the spec repo)
    echo "$repo_root"
    return
  fi

  local rel
  rel=$(grep -E "^\s*spec_repo_root:" "$config" | head -1 | sed -E 's/^[[:space:]]*spec_repo_root:[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)

  if [[ -z "$rel" ]] || [[ "$rel" == "." ]] || [[ "$rel" == "n/a" ]]; then
    echo "$repo_root"
  else
    # Resolve relative path
    if [[ -d "$repo_root/$rel" ]]; then
      (cd "$repo_root/$rel" && pwd)
    else
      echo "$repo_root"  # fallback if path invalid
    fi
  fi
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
SPEC_ROOT="$(get_spec_repo_root)"

# Fallback UI_FILE_PATTERN from code repo .bmm-config.yaml if env didn't set it.
if [[ -z "$UI_FILE_PATTERN" ]] && [[ -f "$REPO_ROOT/.bmm-config.yaml" ]]; then
  UI_FILE_PATTERN=$(grep -E "^\s*ui_file_pattern:" "$REPO_ROOT/.bmm-config.yaml" \
    | head -1 | sed -E 's/^[[:space:]]*ui_file_pattern:[[:space:]]*//' \
    | tr -d '"' | tr -d "'" | xargs || true)
fi
# Built-in default (precedence thấp nhất): áp dụng khi env + .bmm-config.yaml đều
# không set. Angular để UI component trong .ts thuần (*.component.ts / *.page.ts).
[[ -z "$UI_FILE_PATTERN" ]] && UI_FILE_PATTERN="$UI_FILE_PATTERN_DEFAULT"
WBS_FILE="$SPEC_ROOT/NTAPP-output/Stage_2_Architecture/project_wbs.md"
DD_DIR="$SPEC_ROOT/NTAPP-output/Stage_4_Design/detailed_design"
UI_SCHEMA_DIR="$SPEC_ROOT/NTAPP-output/Stage_4_Design/ui_schema"

# ─── Design-system root (per-repo, multi-DS aware) ──────────────────
# design_system_root đọc từ .bmm-config.yaml của CHÍNH repo đang commit:
#   code repo → DS root của repo đó (per-repo gate — repo chưa bootstrap DS thì
#   Rule 4/6/7 skip cho RIÊNG repo đó, không ăn theo repo khác);
#   spec repo → family root (chứa registry.yaml khi multi-DS).
# Thiếu key → default legacy <spec>/NTAPP-output/design-system.
# Thủ tục chuẩn: NTAPP-output/design-system/_shared/ds-resolution.md (nhánh D).
get_design_system_root() {
  local config="$REPO_ROOT/.bmm-config.yaml"
  local rel=""
  if [[ -f "$config" ]]; then
    rel=$(grep -E "^\s*design_system_root:" "$config" | head -1 \
      | sed -E 's/^[[:space:]]*design_system_root:[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)
  fi
  if [[ -z "$rel" ]]; then
    echo "$SPEC_ROOT/NTAPP-output/design-system"
  elif [[ "$rel" = /* ]]; then
    echo "$rel"
  elif [[ -d "$REPO_ROOT/$rel" ]]; then
    (cd "$REPO_ROOT/$rel" && pwd)
  else
    echo "$REPO_ROOT/$rel"
  fi
}
DS_ROOT="$(get_design_system_root)"

# ds_roots: mọi DS root hiện hữu. Không có registry.yaml → chính DS_ROOT (legacy /
# per-repo). Có registry.yaml (family root) → mỗi systems.*.root ("." = in-place).
ds_roots() {
  local reg="$DS_ROOT/registry.yaml"
  if [[ ! -f "$reg" ]]; then echo "$DS_ROOT"; return; fi
  local r found=0
  while IFS= read -r r; do
    r="$(echo "$r" | sed -E 's/^[[:space:]]*root:[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)"
    [[ -z "$r" ]] && continue
    found=1
    if [[ "$r" == "." ]]; then echo "$DS_ROOT"; else echo "$DS_ROOT/${r%/}"; fi
  done < <(grep -E '^[[:space:]]+root:' "$reg" 2>/dev/null)
  [[ "$found" == 1 ]] || echo "$DS_ROOT"
}

# find_unit_delta_dir <ID> → {ds_root}/feature_deltas/<ID> đầu tiên tồn tại
# (WBS ID global-unique → tối đa 1 hit).
find_unit_delta_dir() {
  local id="$1" root
  while IFS= read -r root; do
    [[ -d "$root/feature_deltas/$id" ]] && { echo "$root/feature_deltas/$id"; return 0; }
  done < <(ds_roots)
  return 1
}

# DS standardization gate: Rule 4/6/7 (token discipline + ui_schema + build_report)
# chỉ enforce khi Master DS đã tồn tại (≥1 DS root có master_token.json — code repo
# chỉ nhìn thấy DS root của chính nó nên gate là per-repo). Greenfield build toàn bộ
# slice TRƯỚC, chuẩn hoá DS sau (master_token.json chưa có) → skip 4/6/7 tới pass
# chuẩn hoá. Brownfield bootstrap DS ở Phase A nên master_token.json có sớm → enforce.
DS_BOOTSTRAPPED=0
while IFS= read -r _dsr; do
  [[ -f "$_dsr/master_token.json" ]] && { DS_BOOTSTRAPPED=1; break; }
done < <(ds_roots)

# ─── Helpers ────────────────────────────────────────────────────────
fail()   { echo "${RED}❌ $*${NC}" >&2; }
warn()   { echo "${YELLOW}⚠️  $*${NC}"; }
pass()   { echo "${GREEN}✓${NC} $*"; }

# Extract ID value from file header (first 10 lines).
# grep -oE returns the matched substring (may include 1 leading non-identifier
# char from the boundary group); sed strips everything up to `id:` and the
# whitespace after.
extract_id() {
  head -10 "$1" 2>/dev/null \
    | grep -oE "$ID_HEADER_PATTERN" \
    | sed -E 's/.*id:[[:space:]]+//' \
    | head -1
}

# Check if file is UI: matches a UI extension OR the extra UI_FILE_PATTERN
# (e.g. Angular `*.component.ts`). UI_FILE_PATTERN is opt-in (empty by default).
is_ui_file() {
  [[ "$1" =~ $UI_EXTENSIONS ]] && return 0
  [[ -n "$UI_FILE_PATTERN" ]] && [[ "$1" =~ $UI_FILE_PATTERN ]]
}

# Check if an ID value has a UI prefix (SCR-* / WGT-*).
is_ui_id() {
  [[ "$1" =~ $UI_ID_PREFIX_PATTERN ]]
}

# ─── Get staged files ───────────────────────────────────────────────
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || echo "")

# Filter: code files NOT in third-party skill libs / BMM core
STAGED_CODE_FILES=$(echo "$STAGED_FILES" \
  | grep -E "$CODE_EXTENSIONS" \
  | grep -vE "$EXCLUDED_PATHS" \
  || true)

if [[ -z "$STAGED_CODE_FILES" ]]; then
  exit 0  # không có project code file → skip
fi

# Track errors across rules
TOTAL_ERRORS=0

# ═══════════════════════════════════════════════════════════════════
# RULE 1: Header `id: <ID> | dd_version: vN` + prefix khớp loại file
# ═══════════════════════════════════════════════════════════════════
MISSING_HEADER=()
MISSING_DD_VERSION=()
PREFIX_MISMATCH=()

while IFS= read -r file; do
  if [[ ! -f "$file" ]]; then continue; fi
  HEADER=$(head -10 "$file")

  if ! echo "$HEADER" | grep -qE "$ID_HEADER_PATTERN"; then
    MISSING_HEADER+=("$file")
    continue
  fi

  if ! echo "$HEADER" | grep -qE "dd_version:[[:space:]]*v[0-9]+"; then
    MISSING_DD_VERSION+=("$file")
  fi

  # Prefix-vs-file-type check: UI extension phải dùng UI prefix (SCR-/WGT-);
  # non-UI extension không được dùng UI prefix.
  fid=$(extract_id "$file")
  if [[ -n "$fid" ]]; then
    if is_ui_file "$file"; then
      if ! is_ui_id "$fid"; then
        PREFIX_MISMATCH+=("$file (UI file dùng id=$fid — prefix phải khớp $UI_ID_PREFIX_PATTERN, vd SCR- / WGT-)")
      fi
    else
      if is_ui_id "$fid"; then
        PREFIX_MISMATCH+=("$file (non-UI file dùng id=$fid — prefix UI ($UI_ID_PREFIX_PATTERN) chỉ dùng cho UI extension)")
      fi
    fi
  fi
done <<< "$STAGED_CODE_FILES"

if [[ ${#MISSING_HEADER[@]} -gt 0 ]]; then
  fail "Rule 1: File code thiếu header id"
  echo ""
  echo "Format bắt buộc trong 10 dòng đầu:"
  echo "  // id: <ID> | dd_version: v<N>           (TS/JS/Go/Java/…)"
  echo "  # id: <ID> | dd_version: v<N>            (Python/Shell)"
  echo "  <!-- id: <ID> | dd_version: v<N> -->     (HTML/Vue template)"
  echo ""
  echo "Loại unit encoded qua ID prefix:"
  echo "  - UI file (.tsx/.jsx/.vue/.html/.css/.scss/...) → id phải bắt đầu SCR- / WGT-"
  echo "  - File code khác → id KHÔNG được bắt đầu SCR- / WGT-"
  echo ""
  echo "File vi phạm:"
  for f in "${MISSING_HEADER[@]}"; do echo "  - $f"; done
  TOTAL_ERRORS=$((TOTAL_ERRORS + ${#MISSING_HEADER[@]}))
fi

if [[ ${#MISSING_DD_VERSION[@]} -gt 0 ]]; then
  fail "Rule 1: File code thiếu dd_version (format vN)"
  for f in "${MISSING_DD_VERSION[@]}"; do echo "  - $f"; done
  TOTAL_ERRORS=$((TOTAL_ERRORS + ${#MISSING_DD_VERSION[@]}))
fi

if [[ ${#PREFIX_MISMATCH[@]} -gt 0 ]]; then
  fail "Rule 1: ID prefix không khớp loại file"
  echo "  Quy ước: UI extension (.tsx/.jsx/.vue/.html/.css/.scss/...) → ID phải SCR-* hoặc WGT-*;"
  echo "  non-UI extension → ID không được bắt đầu SCR-/WGT-."
  echo ""
  echo "Vi phạm:"
  for v in "${PREFIX_MISMATCH[@]}"; do echo "  - $v"; done
  TOTAL_ERRORS=$((TOTAL_ERRORS + ${#PREFIX_MISMATCH[@]}))
fi

# Nếu Rule 1 fail header toàn bộ — exit ngay, các rule sau cần <id> đã extract
if [[ ${#MISSING_HEADER[@]} -gt 0 ]]; then
  exit 1
fi

# ═══════════════════════════════════════════════════════════════════
# Collect unique <id> from staged files
# ═══════════════════════════════════════════════════════════════════
SEEN_IDS=":"
ID_FILES=":"   # "ID:file1,file2,..." pairs

while IFS= read -r file; do
  if [[ ! -f "$file" ]]; then continue; fi
  fid=$(extract_id "$file")
  if [[ -z "$fid" ]]; then continue; fi

  if [[ "$SEEN_IDS" != *":$fid:"* ]]; then
    SEEN_IDS="$SEEN_IDS$fid:"
  fi
  ID_FILES="$ID_FILES$fid:$file:"
done <<< "$STAGED_CODE_FILES"

# Convert SEEN_IDS to array (bash 3.x compat)
UNIQUE_IDS=()
IFS=':' read -ra _tmp <<< "$SEEN_IDS"
for id in "${_tmp[@]}"; do
  if [[ -n "$id" ]]; then UNIQUE_IDS+=("$id"); fi
done

# ═══════════════════════════════════════════════════════════════════
# RULE 2: <id> tồn tại trong WBS
# ═══════════════════════════════════════════════════════════════════
if [[ -f "$WBS_FILE" ]]; then
  UNKNOWN_IDS=()
  for fid in "${UNIQUE_IDS[@]}"; do
    if ! grep -qE "^\|[[:space:]]*${fid}[[:space:]]*\|" "$WBS_FILE"; then
      UNKNOWN_IDS+=("$fid")
    fi
  done

  if [[ ${#UNKNOWN_IDS[@]} -gt 0 ]]; then
    fail "Rule 2: <id> không có trong WBS ($WBS_FILE)"
    for id in "${UNKNOWN_IDS[@]}"; do echo "  - $id"; done
    echo "  → Cập nhật WBS qua /ntapp-architecture-design (Stage 2)"
    TOTAL_ERRORS=$((TOTAL_ERRORS + ${#UNKNOWN_IDS[@]}))
  fi
else
  warn "Rule 2 skipped: WBS chưa tồn tại ($WBS_FILE)"
fi

# ═══════════════════════════════════════════════════════════════════
# RULE 3: DD file phải tồn tại
# ═══════════════════════════════════════════════════════════════════
if [[ -d "$DD_DIR" ]]; then
  MISSING_DD=()
  for fid in "${UNIQUE_IDS[@]}"; do
    if [[ ! -f "$DD_DIR/${fid}_detailed_design.md" ]]; then
      MISSING_DD+=("$fid")
    fi
  done

  if [[ ${#MISSING_DD[@]} -gt 0 ]]; then
    fail "Rule 3: DD file chưa tồn tại trong $DD_DIR"
    for id in "${MISSING_DD[@]}"; do
      echo "  - ${id}_detailed_design.md"
    done
    echo "  → Chạy /ntapp-feature-design $id (Stage 4a) trước khi commit code"
    TOTAL_ERRORS=$((TOTAL_ERRORS + ${#MISSING_DD[@]}))
  fi
else
  warn "Rule 3 skipped: $DD_DIR chưa tồn tại (Stage 4 chưa chạy lần nào)"
fi

# ═══════════════════════════════════════════════════════════════════
# RULE 4: UI code không hardcode color hex / px / font name
# ═══════════════════════════════════════════════════════════════════
HARDCODE_VIOLATIONS=()

if [[ "$DS_BOOTSTRAPPED" != 1 ]]; then
  warn "Rule 4 skipped: master_token.json chưa tồn tại (DS chưa chuẩn hoá — greenfield pre-standardization)"
else
while IFS= read -r file; do
  if [[ ! -f "$file" ]] || ! is_ui_file "$file"; then continue; fi

  # Color hex: #RGB, #RRGGBB, #RRGGBBAA
  if grep -nE '#[0-9a-fA-F]{3,8}\b' "$file" | grep -qvE '^[0-9]+:[[:space:]]*//|^[0-9]+:[[:space:]]*\*|^[0-9]+:[[:space:]]*<!--'; then
    LINE=$(grep -nE '#[0-9a-fA-F]{3,8}\b' "$file" | grep -vE '^[0-9]+:[[:space:]]*//|^[0-9]+:[[:space:]]*\*|^[0-9]+:[[:space:]]*<!--' | head -1)
    HARDCODE_VIOLATIONS+=("$file:$LINE [color hex]")
  fi

  # px values trong CSS/SCSS (số + px)
  if [[ "$file" =~ \.(css|scss|sass|less)$ ]]; then
    if grep -nE '\b[0-9]+px\b' "$file" | grep -qvE '^[0-9]+:[[:space:]]*//|^[0-9]+:[[:space:]]*\*'; then
      LINE=$(grep -nE '\b[0-9]+px\b' "$file" | grep -vE '^[0-9]+:[[:space:]]*//|^[0-9]+:[[:space:]]*\*' | head -1)
      HARDCODE_VIOLATIONS+=("$file:$LINE [px hardcode]")
    fi
  fi

  # Font name trong font-family
  if grep -nE 'font-family:[[:space:]]*["'\''][^"'\'']+["'\'']' "$file" > /dev/null 2>&1; then
    if ! grep -qE 'font-family:[[:space:]]*var\(' "$file"; then
      LINE=$(grep -nE 'font-family:[[:space:]]*["'\''][^"'\'']+["'\'']' "$file" | head -1)
      HARDCODE_VIOLATIONS+=("$file:$LINE [font-family hardcode]")
    fi
  fi
done <<< "$STAGED_CODE_FILES"

if [[ ${#HARDCODE_VIOLATIONS[@]} -gt 0 ]]; then
  fail "Rule 4: UI code hardcode design token (color/px/font)"
  echo "  → Reference token từ Master DS thay vì hardcode."
  echo "  → Ví dụ: var(--color-primary), var(--spacing-md), var(--font-family-base)"
  echo ""
  echo "Vi phạm:"
  for v in "${HARDCODE_VIOLATIONS[@]}"; do echo "  - $v"; done
  TOTAL_ERRORS=$((TOTAL_ERRORS + ${#HARDCODE_VIOLATIONS[@]}))
fi
fi

# ═══════════════════════════════════════════════════════════════════
# RULE 6: ui_schema file phải tồn tại (chỉ check khi commit UI file)
# ═══════════════════════════════════════════════════════════════════
# Filter via is_ui_file so UI_FILE_PATTERN matches (Angular *.component.ts) count too.
STAGED_UI_FILES=""
while IFS= read -r file; do
  [[ -n "$file" ]] && is_ui_file "$file" && STAGED_UI_FILES+="$file"$'\n'
done <<< "$STAGED_CODE_FILES"
STAGED_UI_FILES="${STAGED_UI_FILES%$'\n'}"

if [[ -n "$STAGED_UI_FILES" ]] && [[ -d "$UI_SCHEMA_DIR" ]] && [[ "$DS_BOOTSTRAPPED" == 1 ]]; then
  # Lấy <id> từ UI files (SCR-* / WGT-* sau Rule 1 prefix check)
  UI_IDS=":"
  while IFS= read -r file; do
    if [[ ! -f "$file" ]]; then continue; fi
    fid=$(extract_id "$file")
    if [[ -n "$fid" ]] && [[ "$UI_IDS" != *":$fid:"* ]]; then
      UI_IDS="$UI_IDS$fid:"
    fi
  done <<< "$STAGED_UI_FILES"

  MISSING_SCHEMA=()
  IFS=':' read -ra _ui_ids <<< "$UI_IDS"
  for fid in "${_ui_ids[@]}"; do
    if [[ -z "$fid" ]]; then continue; fi
    if [[ ! -f "$UI_SCHEMA_DIR/ui_schema_${fid}.json" ]]; then
      MISSING_SCHEMA+=("$fid")
    fi
  done

  if [[ ${#MISSING_SCHEMA[@]} -gt 0 ]]; then
    fail "Rule 6: ui_schema file chưa tồn tại"
    for id in "${MISSING_SCHEMA[@]}"; do
      echo "  - $UI_SCHEMA_DIR/ui_schema_${id}.json"
    done
    echo "  → Chạy /ntapp-ui-generation $id (Stage 4b) trước khi commit UI code"
    TOTAL_ERRORS=$((TOTAL_ERRORS + ${#MISSING_SCHEMA[@]}))
  fi
fi

# ═══════════════════════════════════════════════════════════════════
# RULE 7: Build-component khi delta có [NEW]
# ═══════════════════════════════════════════════════════════════════
# Multi-DS: delta dir tra per-unit qua find_unit_delta_dir (quét mọi DS root).
HAS_DELTAS=0
while IFS= read -r _dsr; do
  [[ -d "$_dsr/feature_deltas" ]] && { HAS_DELTAS=1; break; }
done < <(ds_roots)

if [[ "$HAS_DELTAS" == 1 ]] && [[ "$DS_BOOTSTRAPPED" == 1 ]]; then
  BUILD_MISSING=()
  BUILD_STALE=()

  for fid in "${UNIQUE_IDS[@]}"; do
    delta_dir="$(find_unit_delta_dir "$fid")" || continue
    local_proposal="$delta_dir/proposed_ds_updates.md"
    local_report="$delta_dir/build_report.md"

    if [[ ! -f "$local_proposal" ]]; then continue; fi

    # Check if proposal has [NEW] section non-empty
    if grep -qE '^\[NEW\]|^## \[NEW\]|^### \[NEW\]' "$local_proposal"; then
      # Extract [NEW] section, check if has content
      NEW_CONTENT=$(awk '/^(\[NEW\]|## \[NEW\]|### \[NEW\])/{flag=1; next} /^(\[MODIFIED\]|## \[MODIFIED\]|### \[MODIFIED\]|\[WARNINGS\]|## \[WARNINGS\]|### \[WARNINGS\])/{flag=0} flag' "$local_proposal" | grep -vE '^[[:space:]]*$|^[[:space:]]*-[[:space:]]*$' | head -3)

      if [[ -n "$NEW_CONTENT" ]] && [[ ! -f "$local_report" ]]; then
        BUILD_MISSING+=("$fid")
      fi
    fi

    # Checksum: build_report ghi proposal checksum (ds-build step-05, format canonical
    # `**Proposal checksum:** sha256:{hash}`; nhận thêm `proposal_sha256: {hash}`) → phải
    # khớp proposal hiện tại, chống report stale pass gate. Report không có checksum → skip.
    if [[ -f "$local_report" ]]; then
      declared_sha=$(grep -iE 'proposal[ _]?checksum|proposal_sha256' "$local_report" 2>/dev/null | head -1 \
        | grep -oE '[0-9a-fA-F]{64}' | head -1 | tr '[:upper:]' '[:lower:]')
      if [[ -n "$declared_sha" ]]; then
        actual_sha=$( (shasum -a 256 "$local_proposal" 2>/dev/null || sha256sum "$local_proposal" 2>/dev/null) \
          | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
        if [[ -n "$actual_sha" && "$declared_sha" != "$actual_sha" ]]; then
          BUILD_STALE+=("$fid")
        fi
      fi
    fi
  done

  if [[ ${#BUILD_MISSING[@]} -gt 0 ]]; then
    fail "Rule 7: đơn vị có [NEW] component/token nhưng chưa build"
    for id in "${BUILD_MISSING[@]}"; do
      echo "  - $id: proposed_ds_updates.md có [NEW] nhưng thiếu build_report.md"
    done
    echo "  → Chạy /ntapp-ds-build-component (Stage 4b gate) trước khi commit"
    TOTAL_ERRORS=$((TOTAL_ERRORS + ${#BUILD_MISSING[@]}))
  fi

  if [[ ${#BUILD_STALE[@]} -gt 0 ]]; then
    fail "Rule 7: build_report.md stale (proposal đã sửa sau khi build)"
    for id in "${BUILD_STALE[@]}"; do
      echo "  - $id: proposal_sha256 trong build_report.md ≠ checksum proposed_ds_updates.md hiện tại"
    done
    echo "  → Re-run /ntapp-ds-build-component để build theo proposal mới nhất"
    TOTAL_ERRORS=$((TOTAL_ERRORS + ${#BUILD_STALE[@]}))
  fi
fi

# ═══════════════════════════════════════════════════════════════════
# RULE 8: Repo scope (service-only repos không được commit infra paths)
# ═══════════════════════════════════════════════════════════════════
# Read repo_type từ marker block trong CLAUDE.md (do bootstrap script ghi).
# Marker format:
#   <!-- >>> NTAPP repo scope (auto-managed, do not edit) >>>
#   ...
#   `repo_type`: service-only | fullstack | unknown
#   ...
#   <!-- <<< NTAPP repo scope <<< -->
get_repo_type() {
  local claude_md="$REPO_ROOT/CLAUDE.md"
  [[ -f "$claude_md" ]] || { echo "unknown"; return; }

  local repo_type
  repo_type=$(awk '
    /<!-- >>> NTAPP repo scope/ {inblock=1; next}
    /<!-- <<< NTAPP repo scope/ {inblock=0; next}
    inblock
  ' "$claude_md" \
    | grep -oE '`repo_type`:[[:space:]]*[a-z-]+' \
    | sed -E 's/`repo_type`:[[:space:]]*//' \
    | head -1)

  echo "${repo_type:-unknown}"
}

REPO_TYPE="$(get_repo_type)"

if [[ "$REPO_TYPE" == "service-only" ]]; then
  # Forbidden paths cho service-only repo. Pattern khớp đầu chuỗi (relative
  # path từ repo root như git diff --name-only output) hoặc cuối cho *.tf.
  # Scope: chỉ true infra (Docker / CI / orchestration / IaC / dev env).
  # Test framework configs (playwright/cypress) KHÔNG block — đó là test code,
  # không phải infra; testarch-framework skill tự detect stack để chọn đúng framework.
  FORBIDDEN_PATTERN='^(Dockerfile$|Dockerfile\..+|docker-compose.*\.ya?ml$|\.github/workflows/|\.gitlab-ci\.yml$|Jenkinsfile$|azure-pipelines\.yml$|helm/|chart/|charts/|k8s/|kubernetes/|manifests/|terraform/|ansible/|\.devcontainer/)|\.tf$|\.tfvars$'

  FORBIDDEN_STAGED=$(echo "$STAGED_FILES" | grep -E "$FORBIDDEN_PATTERN" || true)

  if [[ -n "$FORBIDDEN_STAGED" ]]; then
    fail "Rule 8: Repo này declare repo_type=service-only nhưng commit đụng infra path"
    echo ""
    echo "Vi phạm:"
    while IFS= read -r f; do echo "  - $f"; done <<< "$FORBIDDEN_STAGED"
    echo ""
    echo "Forbidden paths cho service-only repo:"
    echo "  - Dockerfile, docker-compose*.yml"
    echo "  - .github/workflows/, .gitlab-ci.yml, Jenkinsfile, azure-pipelines.yml"
    echo "  - helm/, chart/, charts/, k8s/, kubernetes/, manifests/"
    echo "  - terraform/, *.tf, *.tfvars, ansible/"
    echo "  - .devcontainer/"
    echo ""
    echo "  → Nếu agent tự sinh: prompt agent KHÔNG sinh infra files cho service-only repo."
    echo "  → Nếu cố ý: sửa repo_type trong CLAUDE.md sang fullstack (chạy ./scripts/bootstrap.sh --upgrade)."
    VIOLATION_COUNT=$(echo "$FORBIDDEN_STAGED" | wc -l | tr -d ' ')
    TOTAL_ERRORS=$((TOTAL_ERRORS + VIOLATION_COUNT))
  fi
fi

# ═══════════════════════════════════════════════════════════════════
# RULE 9: UI files không chứa unicode emoji (wireframe emoji là visual hint
# only — Stage 4b đã translate sang icon_bindings trong ui_schema)
# ═══════════════════════════════════════════════════════════════════
# Bypass per-file: file có dòng `// allow-emoji` HOẶC `<!-- allow-emoji -->`
# HOẶC `# allow-emoji` trong 10 dòng đầu (legit case: chat content, emoji
# picker, emoji reaction component).
#
# Detect ranges (đầy đủ unicode emoji blocks):
#   U+2600-U+27BF    (Misc Symbols + Dingbats — ✖ ⬇ ⚠ ☑)
#   U+1F300-U+1FAFF  (Emoji & pictograph blocks — 🔍 🎉 📊 ✅)
#   U+FE0F           (Variation Selector-16 — emoji presentation)
#
# Dùng python cho regex unicode (grep -P không portable trên macOS/BSD).
# Windows (Git Bash) thường chỉ có 'python' / 'py', không có 'python3'.
EMOJI_VIOLATIONS=()

PYBIN=""
for _py in python3 python; do
  if command -v "$_py" > /dev/null 2>&1; then PYBIN="$_py"; break; fi
done
if [[ -z "$PYBIN" ]] && command -v py > /dev/null 2>&1; then PYBIN="py -3"; fi

if [[ -n "$PYBIN" ]]; then
  while IFS= read -r file; do
    if [[ ! -f "$file" ]] || ! is_ui_file "$file"; then continue; fi

    # Check allow-emoji pragma in first 10 lines
    if head -n 10 "$file" 2>/dev/null | grep -qE '(//|#|<!--|/\*)[[:space:]]*allow-emoji'; then
      continue
    fi

    # Detect emoji using python3.
    # Pattern explanation (non-raw string so \u / \U escapes interpret):
    #   [☀-➿]   = Misc Symbols + Dingbats (✖ ⬇ ⚠ ☑ ➜)
    #   [\U0001F300-\U0001FAFF] = Emoji & pictograph blocks (🔍 🎉 📊 ✅)
    #   ️            = Variation Selector-16 (emoji presentation)
    EMOJI_HIT=$($PYBIN -c "
import re, sys
# Windows: stdout mặc định cp1252 → in glyph emoji sẽ UnicodeEncodeError,
# bị 'except' nuốt → Rule 9 mất tác dụng. Ép stdout UTF-8 trước khi in.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
pattern = re.compile(
    '[☀-➿]|[\U0001F300-\U0001FAFF]|️'
)
try:
    with open(sys.argv[1], 'r', encoding='utf-8', errors='replace') as f:
        for lineno, line in enumerate(f, 1):
            m = pattern.search(line)
            if m:
                print(f'{lineno}:{m.group(0)}:{line.rstrip()[:80]}')
                sys.exit(0)
except Exception as e:
    pass
" "$file" 2>/dev/null)

    if [[ -n "$EMOJI_HIT" ]]; then
      EMOJI_VIOLATIONS+=("$file:$EMOJI_HIT")
    fi
  done <<< "$STAGED_CODE_FILES"

  if [[ ${#EMOJI_VIOLATIONS[@]} -gt 0 ]]; then
    fail "Rule 9: UI file chứa unicode emoji (wireframe emoji KHÔNG được copy sang code)"
    echo "  → Wireframe emoji là visual hint cho người đọc detailed_design.md."
    echo "  → Stage 4b đã translate sang icon_bindings trong ui_schema_{id}.json."
    echo "  → Code phải import icon component từ icon library (theo stack-profile.icon_library)."
    echo "  → Edge case legit (chat content, emoji picker): thêm pragma // allow-emoji ở đầu file."
    echo ""
    echo "Vi phạm:"
    for v in "${EMOJI_VIOLATIONS[@]}"; do echo "  - $v"; done
    TOTAL_ERRORS=$((TOTAL_ERRORS + ${#EMOJI_VIOLATIONS[@]}))
  fi
else
  warn "Rule 9 skipped: không có Python (python3/python/py) — cần cho unicode regex"
fi

# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════
if [[ "$TOTAL_ERRORS" -gt 0 ]]; then
  echo ""
  fail "Pre-commit FAILED ($TOTAL_ERRORS issues across rules 1-9)"
  echo ""
  echo "Bypass khẩn cấp (hotfix only — phải compensate trong 48h):"
  echo "  SKIP_PRECOMMIT=1 git commit ..."
  exit 1
fi

ID_COUNT=${#UNIQUE_IDS[@]}
SCOPE_NOTE=""
[[ "$REPO_TYPE" == "service-only" ]] && SCOPE_NOTE=" | scope=service-only"
pass "Pre-commit OK ($ID_COUNT <id> verified across rules 1-9$SCOPE_NOTE)"
exit 0
