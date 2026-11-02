#!/usr/bin/env bash
# Hook 9 — build-loop
# Event: PostToolUse (Edit/Write) + git pre-commit.
# Behavior: realtime feedback on 9 pre-commit rules per file (Manual §7).
#           Output LLM-friendly errors; LLM self-corrects in same turn.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable
. "$HOOK_DIR/lib/entry_mode.sh"

mode="$(entry_mode)"

# ─── Identify target file ───────────────────────────────────────────
INPUT="$(read_stdin_json)"
EVENT="$(json_get "$INPUT" '.hook_event_name')"
TOOL_NAME="$(json_get "$INPUT" '.tool_name')"
FILE="$(json_get "$INPUT" '.tool_input.file_path')"

# Skip non-relevant tools
if [[ "$EVENT" == "PostToolUse" ]]; then
  case "$TOOL_NAME" in
    Edit|Write|MultiEdit) : ;;
    *) ok ;;
  esac
fi

[[ -z "$FILE" || ! -f "$FILE" ]] && ok

# ─── Skip excluded paths (skill libs + BMM core) ────────────────────
case "$FILE" in
  */.agent/skills/*|*/.claude/skills/*|*/.cursor/skills/*|*/_bmad/*)
    ok ;;
  *NTAPP-output/*) ok ;;  # generated artifacts, not project code
  *.md|*.json|*.yaml|*.yml) ok ;;  # docs not code
esac

# ─── Determine file class ───────────────────────────────────────────
UI_EXTENSIONS='\.(tsx|jsx|vue|html|css|scss|sass|less)$'
CODE_EXTENSIONS='\.(ts|tsx|js|jsx|go|java|kt|py|rs|cs|swift|vue|html|css|scss|sass|less)$'

is_code=false
is_ui=false
[[ "$FILE" =~ $CODE_EXTENSIONS ]] && is_code=true
[[ "$FILE" =~ $UI_EXTENSIONS ]] && is_ui=true

$is_code || ok

errors=()
notices=()

# ─── Path roots + dual-repo detection (tính 1 lần) ──────────────────
# Dual-repo: spec repo tách khỏi repo đang edit (agent đang ở CODE repo) → artifact
# spec-side (WBS / DD / ui_schema) KHÔNG phải thứ agent ở đây tạo được. Rule 2/3/6
# vì thế hạ xuống cảnh báo (notice), KHÔNG block — tránh livelock đòi file ngoài tầm với.
# Khi single-repo (SPEC == repo hiện tại) thì vẫn enforce cứng như cũ.
SPEC="$(get_spec_repo_root)"
REPO_ROOT="$(get_repo_root)"
enforce_spec_artifacts=true
[[ "$SPEC" != "$REPO_ROOT" ]] && enforce_spec_artifacts=false

# ─── Rule 1: header id: + dd_version: ───────────────────────────────
HEAD=$(head -10 "$FILE")
ID_LINE=$(echo "$HEAD" | grep -E '(^|[^a-zA-Z_])id:[[:space:]]+[A-Za-z0-9_-]+' | head -1)

if [[ -z "$ID_LINE" ]]; then
  errors+=( "Rule 1: Header missing. Add to line 1:
    // id: <ID> | dd_version: v1   (TS/JS/Go/Java/...)
    # id: <ID> | dd_version: v1    (Python/Shell)
    <!-- id: <ID> | dd_version: v1 -->  (HTML)" )
else
  echo "$ID_LINE" | grep -qE 'dd_version:[[:space:]]*v[0-9]+' \
    || errors+=( "Rule 1: Header has id: but missing dd_version: vN" )

  ID=$(echo "$ID_LINE" | grep -oE '(^|[^a-zA-Z_])id:[[:space:]]+[A-Za-z0-9_-]+' \
    | sed -E 's/.*id:[[:space:]]+//')
  UI_PATTERN="${UI_ID_PREFIX_PATTERN:-^(SCR|WGT)-}"

  if $is_ui && ! [[ "$ID" =~ $UI_PATTERN ]]; then
    errors+=( "Rule 1: UI file uses non-UI prefix '$ID'. Must match $UI_PATTERN" )
  elif ! $is_ui && [[ "$ID" =~ $UI_PATTERN ]]; then
    errors+=( "Rule 1: Non-UI file uses UI prefix '$ID'. Use BE prefix (HUB-, MPF-, ...)" )
  fi
fi

# ─── Rule 2: WBS lookup (skip in stage_4/5_standalone if synthetic) ─
WBS="$SPEC/NTAPP-output/Stage_2_Architecture/project_wbs.md"

if [[ -n "${ID:-}" ]]; then
  if [[ "$mode" == "full" || ( -f "$WBS" && "$mode" != "stage_5_standalone" ) ]]; then
    if [[ -f "$WBS" ]]; then
      if ! python3 "$HOOK_DIR/lib/wbs_parser.py" "$WBS" | cut -f1 | grep -qxF "$ID"; then
        if $enforce_spec_artifacts; then
          errors+=( "Rule 2: ID '$ID' not in project_wbs.md. Add row to WBS first." )
        else
          notices+=( "Rule 2 (dual-repo, non-blocking): ID '$ID' chưa có trong project_wbs.md (spec repo). Nhờ spec-side thêm row." )
        fi
      fi
    fi
  fi
fi

# ─── Rule 3: DD file exists (skip in stage_5_standalone) ────────────
if [[ "$mode" != "stage_5_standalone" && -n "${ID:-}" ]]; then
  DD="$SPEC/NTAPP-output/Stage_4_Design/detailed_design/${ID}_detailed_design.md"
  if [[ ! -f "$DD" ]]; then
    if $enforce_spec_artifacts; then
      errors+=( "Rule 3: ${ID}_detailed_design.md missing. Run /ntapp-feature-design $ID." )
    else
      notices+=( "Rule 3 (dual-repo, non-blocking): ${ID}_detailed_design.md chưa có ở spec repo. Đảm bảo DD đã được tạo spec-side." )
    fi
  fi
fi

# ─── Rule 4: UI no hardcoded color/px/font ──────────────────────────
# Bắt vào biến shell (không ghi /tmp file tên cố định → an toàn khi fan-out song song).
if $is_ui; then
  h4_hex=$(grep -nE '#[0-9a-fA-F]{3,8}\b' "$FILE" | grep -v '// allow-token\|/\* allow-token \*/' | head -3)
  if [[ -n "$h4_hex" ]]; then
    errors+=( "Rule 4: Hardcoded color hex in UI file. Use design token from master_token.json:
$h4_hex" )
  fi
  h4_px=$(grep -nE '[0-9]+px\b' "$FILE" | grep -v '// allow-px' | head -3)
  if [[ -n "$h4_px" ]]; then
    errors+=( "Rule 4: Hardcoded px value. Use spacing/sizing token:
$h4_px" )
  fi
  h4_font=$(grep -nE 'font-family:\s*["'"'"']?[A-Za-z]' "$FILE" | head -2)
  if [[ -n "$h4_font" ]]; then
    errors+=( "Rule 4: Hardcoded font-family. Use typography token:
$h4_font" )
  fi
fi

# ─── Rule 6: UI schema exists ───────────────────────────────────────
if $is_ui && [[ -n "${ID:-}" && "$mode" != "stage_5_standalone" ]]; then
  UI_SCHEMA="$SPEC/NTAPP-output/Stage_4_Design/ui_schema/ui_schema_${ID}.json"
  if [[ ! -f "$UI_SCHEMA" ]]; then
    if $enforce_spec_artifacts; then
      errors+=( "Rule 6: ui_schema_${ID}.json missing. Run /ntapp-ui-generation $ID." )
    else
      notices+=( "Rule 6 (dual-repo, non-blocking): ui_schema_${ID}.json chưa có ở spec repo. Đảm bảo đã sinh spec-side." )
    fi
  fi
fi

# ─── Rule 8: infra-path guard (read repo_type from CLAUDE.md) ───────
CLAUDE_MD="$REPO_ROOT/CLAUDE.md"
if [[ -f "$CLAUDE_MD" ]] && grep -qE 'repo_type[`:]\s*\S*service-only' "$CLAUDE_MD"; then
  case "$FILE" in
    */Dockerfile|*/docker-compose*.yml|*/docker-compose*.yaml \
      |*/.github/workflows/*|*/.gitlab-ci.yml|*/Jenkinsfile|*/azure-pipelines.yml \
      |*/helm/*|*/chart/*|*/charts/*|*/k8s/*|*/kubernetes/*|*/manifests/* \
      |*/terraform/*|*.tf|*.tfvars|*/ansible/*|*/.devcontainer/*)
      errors+=( "Rule 8: service-only repo cannot commit infra path: $FILE
Infra owned by Platform team in separate repo. Move file or change repo_type=fullstack." ) ;;
  esac
fi

# ─── Rule 9: UI emoji guard ─────────────────────────────────────────
if $is_ui; then
  if ! echo "$HEAD" | grep -qE 'allow-emoji'; then
    if python3 -c "
import sys
text = open('$FILE', encoding='utf-8', errors='ignore').read()
ranges = [(0x2600,0x27BF),(0x1F300,0x1FAFF)]
for ch in text:
    o = ord(ch)
    if any(lo<=o<=hi for lo,hi in ranges):
        print(ch); sys.exit(1)
" 2>/dev/null; then
      :
    else
      errors+=( "Rule 9: UI file contains emoji glyph. Use icon component from stack-profile.icon_library, or add pragma '// allow-emoji' in first 10 lines if legit (chat/picker)." )
    fi
  fi
fi

# ─── Report ─────────────────────────────────────────────────────────
# Notice (dual-repo) — in cảnh báo nhưng KHÔNG block.
if [[ ${#notices[@]} -gt 0 ]]; then
  for n in "${notices[@]}"; do echo -e "${YELLOW}[build-loop notice]${NC} $n" >&2; done
fi

if [[ ${#errors[@]} -gt 0 ]]; then
  log_event "build-loop" "BLOCK" "$FILE: ${#errors[@]} violation(s)"
  out="Build-loop violations in $FILE:
"
  for e in "${errors[@]}"; do out+="
- $e
"; done
  out+="
Fix and retry."
  block "$out"
fi

log_event "build-loop" "PASS" "$FILE"
ok
