#!/usr/bin/env bash
# Shared helpers for NTAPP hooks
# Source: . "$(dirname "$0")/lib/common.sh"

set -uo pipefail

# ─── Color ──────────────────────────────────────────────────────────
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

# ─── stdin JSON helpers (Claude Code hook payload) ──────────────────
# Hook payload schema:
#   UserPromptSubmit: {prompt, session_id, cwd, ...}
#   PostToolUse:      {tool_name, tool_input, tool_response, ...}
#   SubagentStop:     {transcript_path, ...}
#   Stop:             {transcript_path, ...}

read_stdin_json() {
  cat
}

json_get() {
  # Usage: json_get "$JSON" ".prompt"   (path = dotted key path, vd .tool_input.file_path)
  #
  # jq la duong chinh; thieu jq thi PHAI co fallback, khong duoc tra rong im lang: moi hook doc
  # payload de branch (.prompt / .hook_event_name / .tool_input.file_path) — path rong nghia la
  # khong nhan ra prompt/file nao ca -> hook thoat 0 va CA HANG RAO bien thanh no-op ma khong ai
  # biet (may khong cai jq van thay "hook chay binh thuong"). Fallback python3 giu nguyen semantics
  # cua `jq -r '<path> // empty'`: key thieu / null / rong -> in ra rong; bool -> true|false.
  local json="$1" path="$2"

  if command -v jq >/dev/null 2>&1; then
    printf '%s\n' "$json" | jq -r "$path // empty" 2>/dev/null
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "$json" | JSON_GET_PATH="$path" python3 -c '
import json, os, sys

filt = os.environ.get("JSON_GET_PATH", "")
filt = filt.split("//")[0].strip()          # bo phan "// empty" neu caller da tu them
raw = sys.stdin.read()
if not raw.strip():
    sys.exit(0)
try:
    cur = json.loads(raw)
except Exception:
    sys.exit(0)                              # payload khong phai JSON -> nhu jq: rong

for key in [k for k in filt.lstrip(".").split(".") if k]:
    if not isinstance(cur, dict):
        sys.exit(0)
    cur = cur.get(key)
    if cur is None:
        sys.exit(0)

if cur is None or cur == "":
    sys.exit(0)
if isinstance(cur, bool):
    out = "true" if cur else "false"
elif isinstance(cur, (int, float)):
    out = str(cur)
elif isinstance(cur, str):
    out = cur
else:
    out = json.dumps(cur, ensure_ascii=False)
sys.stdout.write(out + "\n")
' 2>/dev/null
    return
  fi

  # Khong co ca jq lan python3: khong the doc payload -> canh bao THAT TO ra stderr thay vi
  # de hook am tham pass. Caller nhan chuoi rong nen se thoat 0 (fail-open, khong brick session).
  echo "${YELLOW}[HOOK DEGRADED]${NC} thieu ca jq va python3 — khong doc duoc hook payload, gate dang chay nhu no-op. Cai jq: brew install jq" >&2
}

# ─── Repo path resolution ──────────────────────────────────────────
get_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

get_spec_repo_root() {
  local repo_root="$(get_repo_root)"
  local config="$repo_root/.bmm-config.yaml"

  if [[ ! -f "$config" ]]; then
    echo "$repo_root"; return
  fi

  local rel
  rel=$(grep -E "^\s*spec_repo_root:" "$config" 2>/dev/null \
    | head -1 \
    | sed -E 's/^[[:space:]]*spec_repo_root:[[:space:]]*//' \
    | tr -d '"' | tr -d "'" | xargs)

  if [[ -z "$rel" || "$rel" == "." || "$rel" == "n/a" ]]; then
    echo "$repo_root"
  elif [[ -d "$repo_root/$rel" ]]; then
    (cd "$repo_root/$rel" && pwd)
  else
    echo "$repo_root"
  fi
}

get_code_repo_root() {
  local repo_root="$(get_repo_root)"
  local config="$repo_root/.bmm-config.yaml"

  if [[ ! -f "$config" ]]; then echo "$repo_root"; return; fi

  local rel
  rel=$(grep -E "^\s*code_repo_root:" "$config" 2>/dev/null \
    | head -1 \
    | sed -E 's/^[[:space:]]*code_repo_root:[[:space:]]*//' \
    | tr -d '"' | tr -d "'" | xargs)

  if [[ -z "$rel" || "$rel" == "." ]]; then
    echo "$repo_root"
  elif [[ -d "$repo_root/$rel" ]]; then
    (cd "$repo_root/$rel" && pwd)
  else
    echo "$repo_root"
  fi
}

# ─── Output stages dir ──────────────────────────────────────────────
stage_dir() {
  # Usage: stage_dir 2 → <spec>/NTAPP-output/Stage_2_Architecture
  local n="$1"
  local spec_root="$(get_spec_repo_root)"
  case "$n" in
    0)   echo "$spec_root/NTAPP-output/design-system" ;;
    0.5) echo "$spec_root/NTAPP-output/Stage_1_Discovery/triage" ;;
    1)   echo "$spec_root/NTAPP-output/Stage_1_Discovery" ;;
    2)   echo "$spec_root/NTAPP-output/Stage_2_Architecture" ;;
    3)   echo "$spec_root/NTAPP-output/Stage_3_Specs" ;;
    4)   echo "$spec_root/NTAPP-output/Stage_4_Design" ;;
    5)   echo "$spec_root/NTAPP-output/Stage_5_Build_Verify" ;;
    *)   echo "$spec_root/NTAPP-output" ;;
  esac
}

# ─── Design-system root resolution (multi-DS aware) ────────────────
# Thủ tục chuẩn: NTAPP-output/design-system/_shared/ds-resolution.md (nhánh D).
# get_design_system_root: giá trị `design_system_root:` từ .bmm-config.yaml của repo
# hiện tại; thiếu key/file → default <spec>/NTAPP-output/design-system. Giá trị có thể
# là FAMILY root (spec repo — chứa registry.yaml khi multi-DS) hoặc DS root đơn
# (code repo / legacy). Hook KHÔNG hardcode path này nữa.
get_design_system_root() {
  local repo_root="$(get_repo_root)"
  local config="$repo_root/.bmm-config.yaml"
  local rel=""

  if [[ -f "$config" ]]; then
    rel=$(grep -E "^\s*design_system_root:" "$config" 2>/dev/null \
      | head -1 \
      | sed -E 's/^[[:space:]]*design_system_root:[[:space:]]*//' \
      | tr -d '"' | tr -d "'" | xargs)
  fi

  if [[ -z "$rel" ]]; then
    echo "$(get_spec_repo_root)/NTAPP-output/design-system"
  elif [[ "$rel" = /* ]]; then
    echo "$rel"
  elif [[ -d "$repo_root/$rel" ]]; then
    (cd "$repo_root/$rel" && pwd)
  else
    echo "$repo_root/$rel"
  fi
}

# ds_roots: in mọi DS root hiện hữu, 1 dòng/root.
# Không có registry.yaml → chính root config (legacy single-DS / per-repo DS root).
# Có registry.yaml → mỗi `root:` trong systems ("." = family root in-place).
ds_roots() {
  local base="$(get_design_system_root)"
  local reg="$base/registry.yaml"
  if [[ ! -f "$reg" ]]; then
    echo "$base"; return
  fi
  local r found=0
  while IFS= read -r r; do
    r="$(echo "$r" | sed -E 's/^[[:space:]]*root:[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)"
    [[ -z "$r" ]] && continue
    found=1
    if [[ "$r" == "." ]]; then echo "$base"; else echo "$base/${r%/}"; fi
  done < <(grep -E '^[[:space:]]+root:' "$reg" 2>/dev/null)
  [[ "$found" == 1 ]] || echo "$base"  # registry rỗng/hỏng → fallback legacy
}

# find_unit_delta_dir <ID> → path {ds_root}/feature_deltas/<ID> đầu tiên tồn tại
# (WBS ID global-unique → tối đa 1 hit). Return 1 nếu không có.
find_unit_delta_dir() {
  local id="$1" root
  while IFS= read -r root; do
    if [[ -d "$root/feature_deltas/$id" ]]; then
      echo "$root/feature_deltas/$id"; return 0
    fi
  done < <(ds_roots)
  return 1
}

# ds_root_of_delta_path <path-trong-feature_deltas> → DS root chứa nó
# (.../{ds_root}/feature_deltas/{id}/file → {ds_root}).
ds_root_of_delta_path() {
  local p="$1"
  while [[ "$p" != "/" && -n "$p" ]]; do
    if [[ "$(basename "$p")" == "feature_deltas" ]]; then
      dirname "$p"; return 0
    fi
    p="$(dirname "$p")"
  done
  return 1
}

# ─── Block decision (Claude Code exit codes) ────────────────────────
# Exit 0 = pass; exit 2 = block (stderr → LLM) per Claude Code convention
block() {
  local message="$1"
  echo -e "${RED}[HOOK BLOCK]${NC} $message" >&2
  exit 2
}

warn_pass() {
  local message="$1"
  echo -e "${YELLOW}[HOOK WARN]${NC} $message" >&2
  exit 0
}

ok() {
  exit 0
}

# ─── Disable switch ─────────────────────────────────────────────────
# DISABLE_HOOKS_ALL=1 → tắt mọi hook. DISABLE_HOOK_<NAME>=1 → tắt 1 hook,
# NAME = tên file viết HOA, ký tự ngoài [A-Z0-9] thành '_' (vd build_loop.sh
# → DISABLE_HOOK_BUILD_LOOP). Gọi `maybe_disable` ngay sau khi source common.sh.
maybe_disable() {
  local src="${1:-${BASH_SOURCE[1]:-$0}}"
  local base name var
  base="$(basename "$src")"; base="${base%.sh}"; base="${base%.py}"
  name="$(printf '%s' "$base" | tr '[:lower:]' '[:upper:]' | tr -c 'A-Z0-9' '_')"
  name="${name%_}"
  if is_true "${DISABLE_HOOKS_ALL:-}"; then
    echo "[hook disabled] DISABLE_HOOKS_ALL — skip $base" >&2; exit 0
  fi
  var="DISABLE_HOOK_${name}"
  if is_true "${!var:-}"; then
    echo "[hook disabled] $var — skip $base" >&2; exit 0
  fi
}

# ─── Truthy check ───────────────────────────────────────────────────
# is_true "$x" → return 0 nếu x ∈ {true,1,yes,on} (case-insensitive).
is_true() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    true|1|yes|on) return 0 ;;
    *)             return 1 ;;
  esac
}

# ─── Đọc flag phẳng từ .bmm-config.yaml ─────────────────────────────
# bmm_config_value <key> → echo value của dòng `<key>: <value>` đầu tiên (mọi cấp
# thụt lề), hoặc rỗng. Dùng cho flag tên-duy-nhất như ds_delta_auto_approve.
bmm_config_value() {
  local key="$1"
  local cfg="$(get_repo_root)/.bmm-config.yaml"
  [[ -f "$cfg" ]] || { echo ""; return; }
  grep -E "^[[:space:]]*${key}:" "$cfg" 2>/dev/null | head -1 \
    | sed -E "s/^[[:space:]]*${key}:[[:space:]]*//" | tr -d '"' | tr -d "'" | xargs
}

# ─── Stop/SubagentStop re-entry guard ───────────────────────────────
# Claude Code đặt stop_hook_active=true khi hook đã block ≥1 lần và agent
# đang chạy tiếp vì bị chặn dừng. Nếu không thoát ở đây, một gate mà agent
# KHÔNG tự thỏa mãn được (vd decision-cho-người) sẽ block → continue → block
# vô hạn (livelock). Gọi NGAY sau khi source common.sh trong mọi hook
# SubagentStop/Stop có block. Đọc stdin 1 lần và "tee" lại cho hook qua $STOP_GUARD_INPUT.
STOP_GUARD_INPUT=""
stop_reentry_guard() {
  STOP_GUARD_INPUT="$(cat)"
  if [[ "$(json_get "$STOP_GUARD_INPUT" '.stop_hook_active')" == "true" ]]; then
    log_event "stop-reentry-guard" "RELEASE" "${1:-$(basename "${BASH_SOURCE[1]:-hook}")}"
    ok
  fi
}

# ─── Logger ─────────────────────────────────────────────────────────
log_event() {
  local hook="$1" verdict="$2" detail="${3:-}"
  local log_dir="$(get_spec_repo_root)/NTAPP-output/_notifications"
  mkdir -p "$log_dir"
  printf '%s\t%s\t%s\t%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$hook" "$verdict" "$detail" \
    >> "$log_dir/hook_events.log"
}
