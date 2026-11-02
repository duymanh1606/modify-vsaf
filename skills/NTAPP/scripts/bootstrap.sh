#!/usr/bin/env bash
# Bootstrap script — NTAPP Phase 1 project setup (V4)
#
# Features:
#   - Auto-detect repos trong parent folder (V1)
#   - Idempotent re-run + backup file user-edited (V1)
#   - Multi-repo support: spec + multiple code + optional meta (V2)
#   - Per-code-repo stack auto-detect (V2)
#   - Symlink skill library cross-repo (V2)
#   - Relative symlink path (V3) — portable qua git clone
#   - Auto-managed .gitignore block (V3) — chặn commit symlink/IDE cache
#   - --upgrade mode (V3) — single→multi hoặc add code repo mới
#   - Code repo .bmm-config.yaml machine-local (V4 / Phase 1.6)
#   - Refresh mode generate full machine-local artifacts (V4 / Phase 1.6)
#
# Usage:
#   ./scripts/bootstrap.sh             # full setup (lần đầu)
#   ./scripts/bootstrap.sh --upgrade   # single→multi, hoặc add code repo mới
#   ./scripts/bootstrap.sh --refresh   # dev join, repo đã có config commit
#   ./scripts/bootstrap.sh --dry-run   # show plan, không apply
#   ./scripts/bootstrap.sh --help      # help
#
# Environment vars (non-interactive mode):
#   PROJECT_NAME       Tên project (skip prompt)
#   AUTO_CONFIRM=1     Skip all confirmation prompts

set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT_DIR="$(cd "$SPEC_REPO_ROOT/.." && pwd)"
HOOK_TEMPLATE="$SCRIPT_DIR/templates/pre-commit.template.sh"
HOOK_SETTINGS_TEMPLATE="$SCRIPT_DIR/templates/claude-hooks.settings.json"
WORKSPACE_TEMPLATE="$SCRIPT_DIR/templates/workspace.template.json"
BMM_CONFIG_TEMPLATE="$SCRIPT_DIR/templates/bmm-config-coderepo.template.yaml"
SPEC_BMM_CONFIG_TEMPLATE="$SCRIPT_DIR/templates/bmm-config-specrepo.template.yaml"
GITATTRIBUTES_TEMPLATE="$SCRIPT_DIR/templates/.gitattributes"
AGENTS_MD_TEMPLATE="$SCRIPT_DIR/templates/AGENTS.md"
GEMINI_MD_TEMPLATE="$SCRIPT_DIR/templates/GEMINI.md"
ENGINE_PATCH_SCRIPT="$SCRIPT_DIR/engine-patches/vsaf-4.2.7/apply.sh"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

# Python interpreter — Windows (Git Bash) thường chỉ có 'python' hoặc launcher 'py',
# KHÔNG có 'python3'. Resolve 1 lần, dùng lại ở mọi bước cần Python.
PYTHON_BIN=""
for _py in python3 python; do
  if command -v "$_py" &> /dev/null; then PYTHON_BIN="$_py"; break; fi
done
if [[ -z "$PYTHON_BIN" ]] && command -v py &> /dev/null; then PYTHON_BIN="py -3"; fi

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Mode flags
MODE="full"
DRY_RUN=0
AUTO_CONFIRM="${AUTO_CONFIRM:-0}"

# Detected repos (populated by detect_repos)
DETECTED_SPEC_REPO=""
DETECTED_META_REPO=""
DETECTED_CODE_REPOS=()    # bash 3.x compat array

# Repo scope (populated by setup_repo_scopes — V5 / Phase 1.7)
# Parallel array to DETECTED_CODE_REPOS: scope[i] applies to code_repo[i].
# Values: service-only | fullstack | unknown
DETECTED_REPO_SCOPES=()
DETECTED_REPO_SCOPE_SIGNALS=()

# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════
info()    { printf "${BLUE}ℹ${NC}  %s\n" "$*"; }
success() { printf "${GREEN}✓${NC}  %s\n" "$*"; }
warn()    { printf "${YELLOW}⚠${NC}  %s\n" "$*"; }
error()   { printf "${RED}✗${NC}  %s\n" "$*" >&2; }
heading() { printf "\n${BOLD}── %s ──${NC}\n" "$*"; }

ask() {
  local prompt="$1"
  local default="${2:-}"
  local answer

  if [[ "$AUTO_CONFIRM" == "1" ]]; then
    echo "$default"
    return
  fi

  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " answer
    answer="${answer:-$default}"
  else
    read -r -p "$prompt: " answer
  fi
  echo "$answer"
}

ask_yn() {
  local prompt="$1"
  local default="${2:-y}"

  if [[ "$AUTO_CONFIRM" == "1" ]]; then
    [[ "$default" == "y" ]] && return 0 || return 1
  fi

  local answer
  read -r -p "$prompt (y/n) [$default]: " answer
  answer="${answer:-$default}"
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

# Backup file before overwrite
backup_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    local backup="${file}.bak.${TIMESTAMP}"
    if [[ "$DRY_RUN" == "0" ]]; then
      cp "$file" "$backup"
    fi
    warn "Backup: $file → $backup"
  fi
}

# Run command in dry-run aware way
run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Would run: $*"
  else
    eval "$@"
  fi
}

# Cross-platform sed in-place edit
sed_inplace() {
  local pattern="$1"
  local file="$2"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "$pattern" "$file"
  else
    sed -i "$pattern" "$file"
  fi
}

# Relative path từ $2 (from) tới $1 (to), luôn dùng forward slash.
# $3 = fallback khi không có Python. Path truyền qua argv (an toàn cho path có space).
# Windows Python trả backslash ('..\code') → normalize về '/' để hợp lệ trong JSON
# workspace, YAML config và symlink target.
relpath() {
  local to="$1" from="$2" fallback="$3" result=""
  if [[ -n "$PYTHON_BIN" ]]; then
    result=$($PYTHON_BIN -c "import os.path,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$to" "$from" 2>/dev/null || true)
  fi
  [[ -z "$result" ]] && result="$fallback"
  # backslash → forward slash qua tr '\134' (octal). Param-expansion ${x//\\//}
  # không đáng tin trên MSYS/Git-Bash; tr octal thì portable.
  printf '%s' "$result" | tr '\134' '/'
  printf '\n'
}

# ═══════════════════════════════════════════════════════════════════
# HELP
# ═══════════════════════════════════════════════════════════════════
show_help() {
  cat << 'EOF'
Bootstrap script — NTAPP Phase 1 project setup (V3)

USAGE:
  ./scripts/bootstrap.sh             Full setup (lần đầu)
  ./scripts/bootstrap.sh --upgrade   Single→multi, hoặc add code repo mới
  ./scripts/bootstrap.sh --refresh   Dev join (config đã commit) — hook (pre-commit + event) + IDE cache
  ./scripts/bootstrap.sh --dry-run   Show plan, không apply
  ./scripts/bootstrap.sh --help      Show this help

MODE COMPARISON:
                                full  upgrade  refresh   PIC
  Project name prompt            ✓       ✗        ✗      Project Lead (full only)
  Workspace file (committed)     ✓       ✓        ✗      Project Lead
  Code repo .bmm-config.yaml     ✓       ✓        ✓      All roles (machine-local)
  Skill symlinks                 ✓       ✓        ✓      All roles (machine-local)
  .gitignore block (committed)   ✓       ✓        ✗      Project Lead
  .gitattributes (committed)     ✓       ✓        ✗      Project Lead (spec repo, eol=lf)
  AGENTS.md / GEMINI.md pointer  ✓       ✓        ✗      Project Lead (committed)
  Repo scope block (committed)   ✓       ✓        ✗      Project Lead (full/upgrade only)
  Pre-commit hook                ✓       ✓        ✓      All roles (machine-local)
  Event hook symlink             ✓       ✓        ✓      All roles (.claude/hooks, machine-local)
  Event hook settings block      ✓       ✓        ✓      committed (merge idempotent, no-diff)
  IDE skill cache                ✓       ✓        ✓      All roles (machine-local)

WHAT IT DOES (full mode):
  1. Auto-detect repos trong folder cha (cùng cấp với spec repo)
     - Spec repo: folder hiện tại (có NTAPP-output/)
     - Code repos: folder có package.json / pom.xml / go.mod / etc, hoặc
       marker hệ Apple (Package.swift / Podfile / project Xcode)
     - Meta repo: folder có .agent/skills/ ở root, không có NTAPP-output/
  2. Hỏi xác nhận scope (code repo nào in/out)
  3. Set project name vào heading '# Project: ' của CLAUDE.md + project_name
     của _bmad/bmm/config.yaml. Default = tiêu đề spec repo (tên thư mục, bỏ
     hậu tố -doc/-spec); tên base template bị coi như placeholder nên bản copy
     KHÔNG kế thừa tên template. Tên này cũng là tên file .code-workspace
  4. Sinh workspace file ở spec repo root (.code-workspace)
  5. Sinh .bmm-config.yaml ở mỗi code repo với:
     - Relative path tới spec/meta repo
     - Stack auto-detected (lang, framework, ui_library)
  6. Symlink .agent/skills/ từ skill source — RELATIVE path (V3)
  7. Append .gitignore block chặn commit symlink/IDE cache (V3)
  8. Detect repo scope per code repo (service-only / fullstack), batch
     confirm + write marker block vào <code-repo>/CLAUDE.md (V5)
  9. Chèn import coding rules (@~/.claude/rules/<file>) vào <code-repo>/CLAUDE.md
     theo detect FE/BE — spec repo KHÔNG chèn; rule files do
     scripts/sync-skills-to-user.sh (chạy từ repo template) cài vào ~/.claude/rules/ (V6)
 10. Cài pre-commit hook ở mọi repo
 11. Wire event hook (Claude Code): symlink .claude/hooks/ + merge block
     `hooks` vào .claude/settings.json từ manifest claude-hooks.settings.json
 12. Sinh .gitattributes ở spec repo (`* text=auto eol=lf`) — giữ SHA của
     bundle OKF ổn định giữa macOS/Linux/Windows (không có nó, clone Windows
     với core.autocrlf=true làm mọi node báo stale ở cả hai chiều)
 13. Sinh con trỏ AGENTS.md + GEMINI.md ở spec repo và mọi code repo, kèm
     chèn `@AGENTS.md` vào CLAUDE.md — nội dung THẬT chỉ nằm ở
     <output_folder>/.okf/index.md, ba file kia là con trỏ ngắn
 14. Self-test: workspace JSON valid, pre-commit chặn dummy commit,
     event hook registered + approval_gate fire đúng

ENVIRONMENT VARIABLES:
  PROJECT_NAME       Skip project name prompt
  AUTO_CONFIRM=1     Skip all y/n prompts (use defaults)

IDEMPOTENCY:
  Re-run script an toàn — file user-edited sẽ backup .bak.<timestamp>
  trước khi overwrite. Hook re-install OK (machine-local). Event hook
  merge vào settings.json idempotent (giữ enabledPlugins/permissions,
  byte y hệt nếu block không đổi).
  Symlink relative path (V3) → survive git clone, không cần re-run khi
  clone về máy mới với cùng folder structure (chỉ cần --refresh).
EOF
}

# ═══════════════════════════════════════════════════════════════════
# ENGINE PATCH — fanout + ledger support (machine-local; dist-only engine)
# ═══════════════════════════════════════════════════════════════════
# Engine @ngocsangairvds/vsaf ships dist-only; two node keys used by
# docs/Process/slice-loop.yaml — `fanout` (glob fan-out) + `ledger: <path>` (engine reads
# file → prepends to prompt as cross-iteration context, cap 16KB, also for fanout sub-tasks)
# — are delivered by re-applying the diff onto the installed engine via a 3-way merge
# (version-agnostic — patches ANY version whose anchor lines still exist, preserving that
# version's own code). `npm i -g` overwrites the engine → re-apply on every bootstrap run
# (all modes). apply.sh is idempotent (skips files already carrying the patch); a true
# divergence surfaces as a merge conflict and warns instead of clobbering.
apply_engine_patches() {
  [[ -x "$ENGINE_PATCH_SCRIPT" ]] || return 0
  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Would apply VSAF engine patch (fanout + ledger): $ENGINE_PATCH_SCRIPT"
    "$ENGINE_PATCH_SCRIPT" --status 2>/dev/null || true
    return 0
  fi
  if "$ENGINE_PATCH_SCRIPT" >/dev/null 2>&1; then
    success "VSAF engine patch applied (3-way merge; engine supports fanout: over/as/max_concurrency + ledger: <path>)"
  else
    warn "VSAF engine patch NOT applied — 3-way merge conflict (engine diverged quá xa baseline)."
    info "  Workflow dùng 'fanout:' / 'ledger:' (vd docs/Process/slice-loop.yaml) sẽ fail validate."
    info "  Kiểm tra: $ENGINE_PATCH_SCRIPT --status   |   re-gen orig/+patched/ theo build engine mới."
  fi
}

# ═══════════════════════════════════════════════════════════════════
# VSAF ENGINE — auto-install nếu chưa có (global, 1 lần)
# ═══════════════════════════════════════════════════════════════════
# Trả 0 nếu 'vsaf' có mặt sau khi hàm chạy xong, 1 nếu vẫn thiếu.
ensure_vsaf_installed() {
  command -v vsaf &> /dev/null && return 0
  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Would install VSAF engine: npm install -g @ngocsangairvds/vsaf"
    return 1
  fi
  if ! command -v npm &> /dev/null; then
    warn "VSAF engine CHƯA cài và 'npm' cũng không có trên PATH → không thể auto-install."
    info "  Cài Node.js (kèm npm) trước, rồi chạy lại: ./scripts/bootstrap.sh --refresh"
    return 1
  fi
  info "VSAF engine chưa có — đang cài (global): npm install -g @ngocsangairvds/vsaf ..."
  if npm install -g @ngocsangairvds/vsaf >/dev/null 2>&1; then
    hash -r 2>/dev/null || true
    command -v vsaf &> /dev/null && return 0
    warn "npm install xong nhưng 'vsaf' chưa có trên PATH — kiểm tra global bin của npm có trong PATH."
    return 1
  fi
  warn "Auto-install VSAF engine thất bại — chạy tay: npm install -g @ngocsangairvds/vsaf"
  return 1
}

# ═══════════════════════════════════════════════════════════════════
# LAVISH SKILL — visual review loop (KHÔNG install từ bootstrap)
# ═══════════════════════════════════════════════════════════════════
# Skill đến từ 2 nguồn, không nguồn nào cần bootstrap gọi npm:
#   - Base template: .agent/skills/lavish (MIT, committed) → reload_ide_skills
#     rsync sang .claude/skills/ + .cursor/skills/; sync-skills-to-user.sh đẩy
#     lên ~/.claude/skills/ nên spec repo copy ra vẫn thấy /lavish (global).
#   - Antigravity: scripts/antigravity/install-agy-skills.sh symlink vào
#     ~/.gemini/config/skills/ (agy chỉ đọc global dir, không đọc project-scope).
# Bootstrap TỪNG có fallback `npx skills add` khi .agent/skills/lavish thiếu —
# đã bỏ: spec repo được tạo bằng copy base TRỪ .agent/skills (README §Bước 2)
# nên fallback đó fire ở MỌI project, và CLI materialize .agents/skills/ trong
# spec repo — thư mục không stack nào ở đây đọc. Các integration point
# (ux-sketch step-05 default ON; ui-generation / feature-design opt-in) gọi
# `npx -y lavish-axi` trực tiếp → thiếu skill vẫn chạy được.
warn_stray_agents_dir() {
  [[ -d "$SPEC_REPO_ROOT/.agents" ]] || return 0
  warn "Thư mục rác '.agents/' trong spec repo (bootstrap cũ chạy 'npx skills add') — không stack nào đọc."
  info "  → Xoá được: rm -rf \"$SPEC_REPO_ROOT/.agents\"   (skill lavish nạp từ global ~/.claude/skills/)"
}

# ═══════════════════════════════════════════════════════════════════
# SDLC INIT — tái tạo /sdlc-init bằng bash (merge/skip, KHÔNG overwrite)
# ═══════════════════════════════════════════════════════════════════
# Tương đương skill sdlc-init: scaffold .vsaf/docs/ + CONTEXT.md + .gitignore.
# Idempotent: file đã có → giữ nguyên; chỉ tạo file thiếu, chỉ ADD entry gitignore.
init_sdlc_structure() {
  local docs="$SPEC_REPO_ROOT/.vsaf/docs"
  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Would scaffold SDLC structure (.vsaf/docs/, CONTEXT.md, .gitignore) — tương đương /sdlc-init"
    return 0
  fi

  local created=() skipped=()

  mkdir -p "$docs/features" "$docs/hotfixes" "$docs/onboarding"

  if [[ ! -f "$docs/STATUS.md" ]]; then
    cat > "$docs/STATUS.md" <<'MD'
# SDLC Status Tracker

## Active Features

| Feature | Phase | Status | Last Updated |
|---------|-------|--------|-------------|

## Active Hotfixes

| Bug ID | Phase | Status | Last Updated |
|--------|-------|--------|-------------|

## Completed Features

## Completed Hotfixes
MD
    created+=("STATUS.md")
  else
    skipped+=("STATUS.md")
  fi

  if [[ ! -f "$docs/KNOWLEDGE.md" ]]; then
    cat > "$docs/KNOWLEDGE.md" <<'MD'
# Domain Knowledge

Accumulated knowledge from all phases.
MD
    created+=("KNOWLEDGE.md")
  else
    skipped+=("KNOWLEDGE.md")
  fi

  if [[ ! -f "$SPEC_REPO_ROOT/CONTEXT.md" ]]; then
    cat > "$SPEC_REPO_ROOT/CONTEXT.md" <<'MD'
# Project Context

## Project Overview
{Brief project description — fill after onboarding}

## Tech Stack
{Will be updated by onboard-code}

## Shared Language

| Term | Definition | Example |
|------|-----------|---------|
| {term} | {1-line definition} | {concrete example} |

## Architecture Decisions
{Will be updated by sdlc-architecture}
MD
    created+=("CONTEXT.md")
  else
    skipped+=("CONTEXT.md")
  fi

  # .gitignore — chỉ ADD entry thiếu, KHÔNG xoá entry sẵn có.
  local gi="$SPEC_REPO_ROOT/.gitignore"
  local gi_added=()
  local entry
  for entry in "graphify-out/" ".gitnexus/"; do
    if [[ ! -f "$gi" ]] || ! grep -qxF "$entry" "$gi" 2>/dev/null; then
      printf '%s\n' "$entry" >> "$gi"
      gi_added+=("$entry")
    fi
  done

  if [[ ${#created[@]} -gt 0 ]]; then
    success "SDLC scaffold (/sdlc-init): tạo mới ${created[*]}"
  fi
  if [[ ${#gi_added[@]} -gt 0 ]]; then
    success "SDLC scaffold: thêm .gitignore entry ${gi_added[*]}"
  fi
  if [[ ${#created[@]} -eq 0 && ${#gi_added[@]} -eq 0 ]]; then
    info "SDLC scaffold (/sdlc-init): đã tồn tại đầy đủ — giữ nguyên (${skipped[*]})."
  fi
}

# ═══════════════════════════════════════════════════════════════════
# PRE-FLIGHT
# ═══════════════════════════════════════════════════════════════════
check_prerequisites() {
  heading "Pre-flight checks"

  if ! command -v git &> /dev/null; then
    error "git chưa cài. Install git ≥ 2.30."
    exit 1
  fi

  if [[ ! -d "$SPEC_REPO_ROOT/.git" ]]; then
    error "Folder $SPEC_REPO_ROOT chưa là git repo. Chạy 'git init' trước."
    exit 1
  fi

  for f in "$HOOK_TEMPLATE" "$WORKSPACE_TEMPLATE" "$BMM_CONFIG_TEMPLATE"; do
    if [[ ! -f "$f" ]]; then
      error "Template file thiếu: $f"
      exit 1
    fi
  done

  if [[ ! -f "$SPEC_REPO_ROOT/CLAUDE.md" ]]; then
    error "CLAUDE.md không tìm thấy. Đang chạy script trong folder template clone về?"
    exit 1
  fi

  success "git: $(git --version | awk '{print $3}')"

  # Toolchain Node — engine chính 'vsaf'. Chain tự động: (1) auto-install nếu thiếu →
  # (2) scaffold SDLC structure (tương đương /sdlc-init) → (3) apply engine patch (fanout + ledger).
  # vsaf cài qua 'npm install -g @ngocsangairvds/vsaf'. KHÔNG bước nào của bootstrap
  # phụ thuộc vsaf để hoàn tất → install fail vẫn setup xong phần còn lại.
  ensure_vsaf_installed || true
  if command -v vsaf &> /dev/null; then
    success "vsaf: $(vsaf --version 2>/dev/null || echo '?')"
    init_sdlc_structure
    apply_engine_patches
  else
    warn "VSAF engine (CLI 'vsaf') CHƯA cài — toàn bộ workflow tự động sẽ KHÔNG hoạt động."
    info "  Repo vẫn setup xong (skills + hooks + config), nhưng thiếu engine điều phối DAG:"
    info "  'vsaf run NTAPP/slice-loop', create_prd_epics, feature-triage, staging-deploy... đều không chạy được."
    info "  → Cài tay (global, 1 lần): npm install -g @ngocsangairvds/vsaf"
    info "  → Xác nhận sau khi cài: vsaf --version   (xong là 'vsaf run ...' dùng được ngay)"
  fi

  # Lavish skill: KHÔNG install ở đây (xem §LAVISH SKILL) — chỉ dọn dấu vết cũ.
  warn_stray_agents_dir

  success "Spec repo: $SPEC_REPO_ROOT"
  success "Parent dir: $PARENT_DIR"
}

# ═══════════════════════════════════════════════════════════════════
# V1: AUTO-DETECT REPOS
# ═══════════════════════════════════════════════════════════════════
# Manifest "chung" — tên file cố định, match được bằng vòng lặp.
MANIFEST_NAMES=(package.json pom.xml go.mod build.gradle build.gradle.kts Cargo.toml pyproject.toml requirements.txt)

# Thư mục có ít nhất 1 manifest chung?
has_generic_manifest() {
  local dir="$1" m
  for m in "${MANIFEST_NAMES[@]}"; do
    [[ -f "$dir/$m" ]] && return 0
  done
  return 1
}

# Thư mục KHÔNG bao giờ là manifest dir của repo — build output hoặc dependency
# đã vendor (Pods / Carthage / .build chứa project Apple của thư viện ngoài).
scan_skip_dir() {
  case "$1" in
    node_modules|target|build|dist|out|vendor|.git|.idea|.vscode|.gradle) return 0 ;;
    Pods|Carthage|DerivedData|.build|.swiftpm) return 0 ;;
  esac
  return 1
}

# ─── Marker hệ Apple (iOS / macOS) ─────────────────────────────────
# Hệ Apple không có manifest nào trong MANIFEST_NAMES, và hai đặc điểm sau làm
# vòng lặp tên-file-cố-định trượt hoàn toàn:
#   1. Project của Xcode là DIRECTORY, không phải file, nên phép thử -f sai kiểu.
#   2. Tên project mang tên app (ví dụ một repo tên VDOMiniApp) nên phải dò bằng
#      glob theo phần mở rộng, không liệt kê được trước.
# Echo marker mạnh nhất tìm thấy, hoặc rỗng nếu không phải repo Apple. Thứ tự ưu
# tiên đi từ khai báo dependency (biết chắc build tool) xuống project file.
detect_apple_marker() {
  local dir="$1" p
  [[ -f "$dir/Package.swift" ]] && { printf 'spm'; return 0; }
  [[ -f "$dir/Podfile" ]] && { printf 'cocoapods'; return 0; }
  for p in "$dir"/*.podspec; do
    [[ -f "$p" ]] && { printf 'cocoapods'; return 0; }
  done
  [[ -f "$dir/Project.swift" ]] && { printf 'tuist'; return 0; }
  [[ -f "$dir/Cartfile" ]] && { printf 'carthage'; return 0; }
  for p in "$dir"/*.xcworkspace; do
    [[ -d "$p" ]] && { printf 'xcworkspace'; return 0; }
  done
  for p in "$dir"/*.xcodeproj; do
    [[ -d "$p" ]] && { printf 'xcodeproj'; return 0; }
  done
  return 0
}

# Thư mục chứa manifest của repo — thử root trước, rồi quét sâu 1 cấp.
# Repo Maven multi-module hay đặt aggregator trong subfolder (vd
# mobile-money-be/mobilemoney-2.0/pom.xml) → root trống manifest, nếu chỉ soi
# root thì repo bị xếp loại "other" và bootstrap skip mất. Echo path tìm được;
# không thấy gì thì echo lại chính repo root (caller xử lý như cũ).
#
# Ở depth 1, marker Apple được quét SAU khi quét hết manifest chung (pass 2) —
# repo cross-platform kiểu React Native có cả một thư mục web và một thư mục ios
# thì stack chính vẫn thắng, không tụt xuống thành repo iOS thuần. Repo Flutter
# (có pubspec) chỉ giữ project Apple ở subfolder platform nên không dive vào.
find_manifest_dir() {
  local repo="$1" d name pass
  has_generic_manifest "$repo" && { printf '%s' "$repo"; return 0; }
  [[ -n "$(detect_apple_marker "$repo")" ]] && { printf '%s' "$repo"; return 0; }
  [[ -f "$repo/pubspec.yaml" ]] && { printf '%s' "$repo"; return 0; }

  for pass in generic apple; do
    for d in "$repo"/*/; do
      [[ -d "$d" ]] || continue
      d="${d%/}"
      name="$(basename "$d")"
      scan_skip_dir "$name" && continue
      if [[ "$pass" == "generic" ]]; then
        has_generic_manifest "$d" && { printf '%s' "$d"; return 0; }
      else
        [[ -n "$(detect_apple_marker "$d")" ]] && { printf '%s' "$d"; return 0; }
      fi
    done
  done
  printf '%s' "$repo"
}

classify_repo() {
  local path="$1"

  # Spec repo: là current spec repo
  if [[ "$path" == "$SPEC_REPO_ROOT" ]]; then
    echo "spec"
    return
  fi

  # Code repo: có manifest file (check TRƯỚC meta để tránh mis-classify
  # khi code repo đã có .agent/skills symlink từ bootstrap trước).
  # Manifest có thể nằm sâu 1 cấp → resolve qua find_manifest_dir.
  # Repo hệ Apple nhận diện bằng marker riêng (xem detect_apple_marker).
  local manifest_dir
  manifest_dir="$(find_manifest_dir "$path")"
  if has_generic_manifest "$manifest_dir" || [[ -n "$(detect_apple_marker "$manifest_dir")" ]]; then
    echo "code"
    return
  fi

  # Meta repo: có .agent/skills/ nhưng KHÔNG có code manifest VÀ KHÔNG có NTAPP-output/
  if [[ -d "$path/.agent/skills" ]] && [[ ! -d "$path/NTAPP-output" ]]; then
    echo "meta"
    return
  fi

  echo "other"
}

detect_repos() {
  heading "Auto-detect repos trong $PARENT_DIR"

  local found_count=0

  for entry in "$PARENT_DIR"/*; do
    if [[ ! -d "$entry" ]] || [[ ! -d "$entry/.git" ]]; then
      continue
    fi

    local name
    name="$(basename "$entry")"
    local type
    type="$(classify_repo "$entry")"
    found_count=$((found_count + 1))

    case "$type" in
      spec)
        DETECTED_SPEC_REPO="$entry"
        success "Spec repo:  $name"
        ;;
      meta)
        DETECTED_META_REPO="$entry"
        success "Meta repo:  $name"
        ;;
      code)
        DETECTED_CODE_REPOS+=("$entry")
        success "Code repo:  $name"
        ;;
      other)
        info "Other:      $name (skip)"
        ;;
    esac
  done

  if [[ "$found_count" -eq 0 ]]; then
    warn "Không detect được repo nào ngoài spec repo hiện tại."
    info "Single-repo mode sẽ được áp dụng."
  fi
}

confirm_scope() {
  heading "Confirm scope"

  if [[ ${#DETECTED_CODE_REPOS[@]} -eq 0 ]]; then
    info "Không có code repo detected. Single-repo mode."
    return 0
  fi

  echo ""
  info "Code repos sẽ được setup:"
  local i=1
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    echo "  [$i] $(basename "$repo")"
    i=$((i + 1))
  done

  if [[ -n "$DETECTED_META_REPO" ]]; then
    echo ""
    info "Meta repo detected: $(basename "$DETECTED_META_REPO")"
    info "  → Skills sẽ symlink từ meta repo (single source of truth)"
  else
    echo ""
    info "Không có meta repo → skills lấy từ spec repo"
  fi

  echo ""
  if ! ask_yn "Tiếp tục với scope này?" "y"; then
    echo ""
    info "Skip toàn bộ code repos. Spec repo vẫn được setup (IDE skill cache + pre-commit hook + .gitignore)."
    if ! ask_yn "Continue với spec-repo-only setup?" "y"; then
      info "Aborted by user."
      exit 0
    fi
    DETECTED_CODE_REPOS=()
    DETECTED_META_REPO=""
    info "→ Spec-repo-only mode. Để add code repos sau, chạy './scripts/bootstrap.sh --upgrade'."
  fi
}

# ═══════════════════════════════════════════════════════════════════
# V2: STACK AUTO-DETECT
# ═══════════════════════════════════════════════════════════════════
# Repo có bundler đóng gói cho trình duyệt?
has_browser_bundler() {
  grep -qE '"(rollup|vite|webpack|esbuild|tsup|parcel)"' "$1/package.json" 2>/dev/null
}

# Source có dùng API chỉ tồn tại trong trình duyệt? Bỏ output đã build và trang
# demo để tín hiệu đến từ code thật của repo, không phải trang mẫu.
uses_browser_globals() {
  grep -rqE '\b(window|document|navigator|localStorage)\.' "$1" \
    --include='*.ts' --include='*.tsx' --include='*.js' --include='*.mjs' \
    --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build \
    --exclude-dir=out --exclude-dir=.git --exclude-dir=demo \
    --exclude-dir=docs-site --exclude-dir=coverage 2>/dev/null
}

# Repo có dependency của server framework?
has_node_server_framework() {
  grep -qE '"(express|fastify|@nestjs/core|koa|hapi|hono|@hapi/hapi|restify)"' \
    "$1/package.json" 2>/dev/null
}

# Đếm số file source khai báo dùng một UI framework của Apple. Bỏ thư mục
# dependency đã vendor để không đếm code thư viện ngoài thành code của repo.
apple_import_count() {
  local dir="$1" pattern="$2"
  grep -rlE --include='*.swift' --include='*.m' --include='*.mm' --include='*.h' \
    --exclude-dir=Pods --exclude-dir=Carthage --exclude-dir=DerivedData \
    --exclude-dir=.build --exclude-dir=.swiftpm --exclude-dir=.git \
    "$pattern" "$dir" 2>/dev/null | wc -l | tr -d ' '
}

# UI framework của repo Apple — SwiftUI, UIKit (iOS) hay AppKit (macOS). Repo
# thực tế thường trộn, nên echo cái chiếm đa số trước rồi mới tới cái thiểu số.
detect_apple_ui_framework() {
  local dir="$1" n_swiftui n_uikit n_appkit
  n_swiftui="$(apple_import_count "$dir" 'import[[:space:]]+SwiftUI|<SwiftUI/')"
  n_uikit="$(apple_import_count "$dir" 'import[[:space:]]+UIKit|<UIKit/')"
  n_appkit="$(apple_import_count "$dir" 'import[[:space:]]+AppKit|<AppKit/')"

  if (( n_swiftui == 0 && n_uikit == 0 && n_appkit == 0 )); then
    printf '<TODO>'
  elif (( n_appkit > n_uikit && n_appkit > n_swiftui )); then
    printf 'appkit'
    (( n_swiftui > 0 )) && printf '+swiftui'
  elif (( n_swiftui >= n_uikit )); then
    printf 'swiftui'
    (( n_uikit > 0 )) && printf '+uikit'
  else
    printf 'uikit'
    (( n_swiftui > 0 )) && printf '+swiftui'
  fi
  return 0
}

# Ngôn ngữ chính của repo Apple — Swift, Objective-C, hay trộn. Ngôn ngữ thứ hai
# chỉ được ghi kèm khi chiếm từ khoảng một phần năm số file trở lên: repo Swift
# gần như luôn có vài file bridging Objective-C, ghi kèm thì sai bức tranh.
detect_apple_language() {
  local dir="$1" n_swift n_objc
  n_swift="$(find "$dir" -name '*.swift' -not -path '*/Pods/*' -not -path '*/.build/*' \
    -not -path '*/Carthage/*' -not -path '*/.git/*' 2>/dev/null | head -2000 | wc -l | tr -d ' ')"
  n_objc="$(find "$dir" \( -name '*.m' -o -name '*.mm' \) -not -path '*/Pods/*' \
    -not -path '*/.build/*' -not -path '*/Carthage/*' -not -path '*/.git/*' 2>/dev/null \
    | head -2000 | wc -l | tr -d ' ')"

  if (( n_objc > n_swift )); then
    printf 'objective-c'
    (( n_swift * 5 >= n_objc )) && printf '+swift'
  elif (( n_objc > 0 )); then
    printf 'swift'
    (( n_objc * 5 >= n_swift )) && printf '+objc'
  else
    printf 'swift'
  fi
  return 0
}

# Build tool suy từ marker Apple. Dependency manager đi kèm được ghi luôn vì
# lệnh build khác nhau (workspace của CocoaPods vs project trần).
apple_build_tool_for_marker() {
  case "$1" in
    spm)         printf 'swiftpm' ;;
    tuist)       printf 'tuist' ;;
    cocoapods)   printf 'xcodebuild+cocoapods' ;;
    carthage)    printf 'xcodebuild+carthage' ;;
    *)           printf 'xcodebuild' ;;
  esac
}

detect_stack_for_repo() {
  local repo="$1"
  # Manifest có thể nằm sâu 1 cấp — đọc stack từ thư mục chứa manifest thật.
  repo="$(find_manifest_dir "$repo")"

  # Defaults
  local lang="<TODO>"
  local framework="<TODO>"
  local ui_lib="<TODO>"
  local build_tool="<TODO>"

  if [[ -f "$repo/package.json" ]]; then
    lang="typescript"
    build_tool="npm"
    # Detect framework
    if grep -q '"@angular/core"' "$repo/package.json" 2>/dev/null; then
      framework="angular"
      ui_lib="angular-material"
    elif grep -q '"react"' "$repo/package.json" 2>/dev/null; then
      framework="react"
      ui_lib="<react-component-lib>"
    elif grep -q '"vue"' "$repo/package.json" 2>/dev/null; then
      framework="vue"
      ui_lib="<vue-component-lib>"
    elif has_browser_bundler "$repo" && uses_browser_globals "$repo"; then
      # Thư viện đóng gói cho trình duyệt (SDK nhúng vào webview, widget). Trước
      # đây rơi vào nhánh cuối và bị ghi là "node" — một khẳng định SAI chứ
      # không phải chỗ trống, đọc vào dễ viết code hệ thống tệp vào code chạy
      # trong trình duyệt.
      framework="browser-lib"
      ui_lib="n/a"
    elif has_node_server_framework "$repo"; then
      framework="node"
      ui_lib="n/a"
    else
      # Không nhận ra gì thì để trống cho người điền, KHÔNG đoán "node".
      framework="<TODO>"
    fi
  elif [[ -f "$repo/pom.xml" ]]; then
    lang="java"
    build_tool="maven"
    if grep -q "spring-boot" "$repo/pom.xml" 2>/dev/null; then
      framework="spring-boot"
    else
      framework="java"
    fi
    ui_lib="n/a"
  elif [[ -f "$repo/build.gradle" ]] || [[ -f "$repo/build.gradle.kts" ]]; then
    lang="java"
    build_tool="gradle"
    framework="<TODO>"
    ui_lib="n/a"
  elif [[ -f "$repo/go.mod" ]]; then
    lang="go"
    build_tool="go"
    framework="<TODO>"
    ui_lib="n/a"
  elif [[ -f "$repo/Cargo.toml" ]]; then
    lang="rust"
    build_tool="cargo"
    framework="<TODO>"
    ui_lib="n/a"
  elif [[ -f "$repo/pyproject.toml" ]] || [[ -f "$repo/requirements.txt" ]]; then
    lang="python"
    build_tool="pip"
    framework="<TODO>"
    ui_lib="n/a"
  else
    # Hệ Apple xét CUỐI: repo cross-platform (React Native) có package.json ở
    # root phải nhận stack chính, không tụt xuống thành repo iOS thuần.
    local apple_marker
    apple_marker="$(detect_apple_marker "$repo")"
    if [[ -n "$apple_marker" ]]; then
      lang="$(detect_apple_language "$repo")"
      build_tool="$(apple_build_tool_for_marker "$apple_marker")"
      framework="$(detect_apple_ui_framework "$repo")"
      if [[ "$framework" == "<TODO>" ]]; then
        # Không tìm thấy UI framework nào → thư viện thuần dữ liệu, không có
        # component nào để nói tới.
        ui_lib="n/a"
      else
        # Repo Apple thường tự dựng component nội bộ, không có component lib
        # ngoài như bên web → để placeholder cho người điền.
        ui_lib="<apple-component-lib>"
      fi
    fi
  fi

  echo "$lang|$framework|$ui_lib|$build_tool"
}

# ═══════════════════════════════════════════════════════════════════
# V5 (Phase 1.7): REPO SCOPE auto-detect + batch confirm
# ═══════════════════════════════════════════════════════════════════
# Vấn đề giải quyết: agents (Claude / Cursor) khi chạy Stage 5 hay tự
# sinh Dockerfile / CI / helm / terraform / UI test config vào code repo
# kể cả khi team BE chỉ own service code. Khai báo repo_type ở code repo
# cho agent + pre-commit hook biết boundary, chặn drift.
#
# Heuristic:
#   - Node package.json có FE deps → fullstack
#   - Node package.json có BE deps only → service-only
#   - Java/Go/Rust/Python BE manifest → service-only
#   - Cả 2 signal → fullstack
#   - Không signal nào rõ → unknown (hỏi explicit)
#
# Output: marker block trong <code-repo>/CLAUDE.md (idempotent như gitignore block).
# Pre-commit Rule 8 đọc block này để enforce forbidden paths khi service-only.

REPO_SCOPE_MARKER_BEGIN="<!-- >>> NTAPP repo scope (auto-managed, do not edit) >>>"
REPO_SCOPE_MARKER_END="<!-- <<< NTAPP repo scope <<< -->"

detect_repo_scope_for_repo() {
  local repo="$1"
  # Manifest có thể nằm sâu 1 cấp — soi thư mục chứa manifest thật.
  repo="$(find_manifest_dir "$repo")"
  local has_frontend=0
  local has_backend=0
  local signal=""

  # Node manifest — check FE deps trước (chính xác hơn BE check)
  if [[ -f "$repo/package.json" ]]; then
    if grep -qE '"(react|next|vue|svelte|@angular/core|nuxt|remix|astro|solid-js|preact|qwik)"' "$repo/package.json" 2>/dev/null; then
      has_frontend=1
      signal="package.json + FE framework deps"
    fi
    if grep -qE '"(express|fastify|@nestjs/core|koa|hapi|hono|@hapi/hapi|restify)"' "$repo/package.json" 2>/dev/null; then
      has_backend=1
      [[ -z "$signal" ]] && signal="package.json + BE framework deps only"
    fi
  fi

  # Hệ Apple: repo client, cùng nhóm với FE web nên KHÔNG chặn infra path —
  # repo mobile cần giữ pipeline build và ký app trong repo của chính nó.
  if [[ "$has_frontend" == "0" ]]; then
    local apple_marker
    apple_marker="$(detect_apple_marker "$repo")"
    if [[ -n "$apple_marker" ]]; then
      has_frontend=1
      [[ -z "$signal" ]] && signal="marker Apple $apple_marker (repo client iOS/macOS)"
    fi
  fi

  # Non-Node BE manifest
  for manifest in pom.xml build.gradle build.gradle.kts go.mod Cargo.toml pyproject.toml requirements.txt; do
    if [[ -f "$repo/$manifest" ]]; then
      has_backend=1
      [[ -z "$signal" ]] && signal="$manifest (BE manifest, no UI deps)"
      break
    fi
  done

  # Decide
  local scope
  if [[ "$has_frontend" == "1" ]] && [[ "$has_backend" == "1" ]]; then
    scope="fullstack"
    signal="FE + BE deps cùng repo (monorepo signal)"
  elif [[ "$has_frontend" == "1" ]]; then
    scope="fullstack"
  elif [[ "$has_backend" == "1" ]]; then
    scope="service-only"
  else
    scope="unknown"
    signal="manifest không cho biết FE hay BE"
  fi

  echo "$scope|$signal"
}

# Check if code repo's CLAUDE.md already has a scope block (sticky behavior)
repo_has_scope_block() {
  local repo="$1"
  local claude_md="$repo/CLAUDE.md"
  [[ -f "$claude_md" ]] && grep -qF "$REPO_SCOPE_MARKER_BEGIN" "$claude_md"
}

# Extract existing repo_type from code repo CLAUDE.md (returns empty if none)
extract_existing_scope() {
  local repo="$1"
  local claude_md="$repo/CLAUDE.md"
  [[ -f "$claude_md" ]] || return
  awk -v begin="$REPO_SCOPE_MARKER_BEGIN" -v end="$REPO_SCOPE_MARKER_END" '
    index($0, begin)==1 {inblock=1; next}
    index($0, end)==1 {inblock=0; next}
    inblock' "$claude_md" \
    | grep -oE '`repo_type`:[[:space:]]*[a-z-]+' \
    | sed -E 's/`repo_type`:[[:space:]]*//' \
    | head -1
}

# Setup repo scopes: detect → batch confirm → write CLAUDE.md scope blocks
setup_repo_scopes() {
  heading "Repo scope (service-only vs fullstack)"

  if [[ ${#DETECTED_CODE_REPOS[@]} -eq 0 ]]; then
    info "Không có code repo → skip"
    return 0
  fi

  # ─── Phase 1: per-repo detection ───────────────────────────────────
  DETECTED_REPO_SCOPES=()
  DETECTED_REPO_SCOPE_SIGNALS=()
  local sticky_count=0

  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    # Sticky: nếu đã có scope block thì KHÔNG override (user đã decide)
    if repo_has_scope_block "$repo"; then
      local existing
      existing="$(extract_existing_scope "$repo")"
      DETECTED_REPO_SCOPES+=("${existing:-unknown}")
      DETECTED_REPO_SCOPE_SIGNALS+=("(existing scope block — giữ nguyên)")
      sticky_count=$((sticky_count + 1))
      continue
    fi

    # Detect mới
    local info_pair scope signal
    info_pair=$(detect_repo_scope_for_repo "$repo")
    scope="${info_pair%%|*}"
    signal="${info_pair#*|}"
    DETECTED_REPO_SCOPES+=("$scope")
    DETECTED_REPO_SCOPE_SIGNALS+=("$signal")
  done

  # ─── Phase 2: batch confirm UI ─────────────────────────────────────
  echo ""
  info "Heuristic kết quả cho ${#DETECTED_CODE_REPOS[@]} code repo(s):"
  echo ""
  printf "  %-3s %-25s %-15s %s\n" "#" "Repo" "Scope" "Signal"
  printf "  %-3s %-25s %-15s %s\n" "---" "-------------------------" "---------------" "-------------------------"
  local i=0
  while [[ $i -lt ${#DETECTED_CODE_REPOS[@]} ]]; do
    local repo_name
    repo_name="$(basename "${DETECTED_CODE_REPOS[$i]}")"
    printf "  %-3s %-25s %-15s %s\n" "[$((i+1))]" "$repo_name" "${DETECTED_REPO_SCOPES[$i]}" "${DETECTED_REPO_SCOPE_SIGNALS[$i]}"
    i=$((i + 1))
  done
  echo ""
  info "Scope quyết định pre-commit Rule 8 có chặn infra paths (Dockerfile, CI, helm, ...) hay không."
  if [[ "$sticky_count" -gt 0 ]]; then
    info "($sticky_count repo đã có scope block trong CLAUDE.md → giữ nguyên, không hỏi lại)"
  fi
  echo ""

  if [[ "$AUTO_CONFIRM" == "1" ]]; then
    info "AUTO_CONFIRM=1 → accept heuristic, không hỏi"
  else
    echo "  [Y] Accept all (mặc định)"
    echo "  [n] Abort"
    echo "  [edit] Sửa scope của repo cụ thể"
    echo ""
    local answer
    read -r -p "Choice [Y/n/edit]: " answer
    answer="${answer:-Y}"
    case "$answer" in
      n|N|no|NO)
        info "Aborted by user."
        exit 0
        ;;
      edit|EDIT|e|E)
        edit_repo_scopes_loop
        ;;
      *)
        # Accept
        ;;
    esac
  fi

  # ─── Phase 3: warn unknown ─────────────────────────────────────────
  local has_unknown=0
  local j=0
  while [[ $j -lt ${#DETECTED_CODE_REPOS[@]} ]]; do
    if [[ "${DETECTED_REPO_SCOPES[$j]}" == "unknown" ]]; then
      warn "$(basename "${DETECTED_CODE_REPOS[$j]}"): scope=unknown → Rule 8 sẽ KHÔNG enforce. Sửa CLAUDE.md sau khi xác định."
      has_unknown=1
    fi
    j=$((j + 1))
  done
  [[ "$has_unknown" == "1" ]] && echo ""

  # ─── Phase 4: write CLAUDE.md scope blocks ─────────────────────────
  write_repo_scope_blocks
}

# Interactive edit loop: cho user override scope per repo
edit_repo_scopes_loop() {
  echo ""
  info "Edit mode — gõ số repo + scope mới (vd: '1 fullstack'), hoặc 'done' để xong."
  info "Scope hợp lệ: service-only | fullstack | unknown"
  echo ""

  while true; do
    local line
    read -r -p "edit> " line
    line="$(echo "$line" | xargs)"   # trim whitespace
    [[ -z "$line" ]] && continue
    if [[ "$line" == "done" ]] || [[ "$line" == "exit" ]] || [[ "$line" == "q" ]]; then
      break
    fi

    local idx new_scope
    idx="$(echo "$line" | awk '{print $1}')"
    new_scope="$(echo "$line" | awk '{print $2}')"

    if ! [[ "$idx" =~ ^[0-9]+$ ]] || [[ "$idx" -lt 1 ]] || [[ "$idx" -gt ${#DETECTED_CODE_REPOS[@]} ]]; then
      warn "Số repo không hợp lệ. Hiện có ${#DETECTED_CODE_REPOS[@]} repo, chọn 1-${#DETECTED_CODE_REPOS[@]}."
      continue
    fi

    case "$new_scope" in
      service-only|fullstack|unknown)
        local arr_idx=$((idx - 1))
        DETECTED_REPO_SCOPES[$arr_idx]="$new_scope"
        DETECTED_REPO_SCOPE_SIGNALS[$arr_idx]="(user override)"
        success "$(basename "${DETECTED_CODE_REPOS[$arr_idx]}") → $new_scope"
        ;;
      *)
        warn "Scope không hợp lệ: '$new_scope'. Dùng: service-only | fullstack | unknown"
        ;;
    esac
  done
}

# Render scope block content based on repo_type
render_scope_block() {
  local repo_type="$1"
  local body

  case "$repo_type" in
    service-only)
      body=$(cat << 'BLOCK_EOF'
## Repo scope

`repo_type`: service-only

Repo này chỉ chứa **service code**. Infrastructure (Docker, CI/CD, Kubernetes, Terraform, Ansible) thuộc team khác và ở repo riêng. **Agents KHÔNG được sinh file thuộc các path forbidden dưới đây vào repo này.**

**Forbidden paths (pre-commit Rule 8 sẽ chặn):**

- `Dockerfile`, `docker-compose*.y[a]ml`
- `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`
- `helm/`, `chart/`, `k8s/`, `kubernetes/`, `manifests/`
- `terraform/`, `*.tf`, `*.tfvars`, `ansible/`
- `.devcontainer/`

Test framework configs (`playwright.config.*`, `cypress.config.*`, `cypress/`, `vitest.config.*`, `jest.config.*`, `pytest.ini`, ...) **KHÔNG** thuộc forbidden — đó là test code, không phải infra. `/bmad-testarch-framework` tự detect stack để chọn framework đúng (Playwright / Cypress cho UI repo, Pytest / Vitest / Jest / Junit cho service-only).

**Khi feature thực sự cần đụng các path infra:** escalate tới team owner của infra repo, không tự sinh ở đây. Bypass khẩn cấp (hotfix only, phải compensate trong 48h): `SKIP_PRECOMMIT=1 git commit ...`
BLOCK_EOF
)
      ;;
    fullstack)
      body=$(cat << 'BLOCK_EOF'
## Repo scope

`repo_type`: fullstack

Repo này chứa cả service + UI code (hoặc monorepo có infra). Pre-commit Rule 8 KHÔNG enforce forbidden paths — agents được tự do sinh Dockerfile, CI config theo nhu cầu feature.
BLOCK_EOF
)
      ;;
    *)
      body=$(cat << 'BLOCK_EOF'
## Repo scope

`repo_type`: unknown

Bootstrap không suy ra được scope từ manifest. Sửa `repo_type` thành `service-only` hoặc `fullstack`, hoặc chạy lại `./scripts/bootstrap.sh --upgrade` để re-detect. Pre-commit Rule 8 KHÔNG enforce khi scope=unknown.
BLOCK_EOF
)
      ;;
  esac

  echo "$body"
}

# Write scope block into each code repo's CLAUDE.md (idempotent, marker-based)
write_repo_scope_blocks() {
  local i=0
  while [[ $i -lt ${#DETECTED_CODE_REPOS[@]} ]]; do
    local repo="${DETECTED_CODE_REPOS[$i]}"
    local scope="${DETECTED_REPO_SCOPES[$i]}"
    local repo_name
    repo_name="$(basename "$repo")"
    local claude_md="$repo/CLAUDE.md"

    # Sticky: nếu đã có block VÀ scope chưa đổi → skip write
    if repo_has_scope_block "$repo"; then
      local existing
      existing="$(extract_existing_scope "$repo")"
      if [[ "$existing" == "$scope" ]]; then
        info "$repo_name: scope block đã đúng ($scope) → skip"
        i=$((i + 1))
        continue
      fi
    fi

    if [[ "$DRY_RUN" == "1" ]]; then
      info "[DRY-RUN] $repo_name: write scope block (repo_type=$scope) vào CLAUDE.md"
      i=$((i + 1))
      continue
    fi

    local body
    body="$(render_scope_block "$scope")"

    if [[ -f "$claude_md" ]] && grep -qF "$REPO_SCOPE_MARKER_BEGIN" "$claude_md"; then
      # Block exists — replace
      backup_file "$claude_md"
      local tmp="${claude_md}.tmp.$$"
      awk -v begin="$REPO_SCOPE_MARKER_BEGIN" -v end="$REPO_SCOPE_MARKER_END" '
        index($0, begin)==1 {skip=1; next}
        index($0, end)==1 {skip=0; next}
        !skip
      ' "$claude_md" > "$tmp"
      sed_inplace '/./,$!d' "$tmp" 2>/dev/null || true
      {
        cat "$tmp"
        echo ""
        echo "$REPO_SCOPE_MARKER_BEGIN"
        echo ""
        echo "$body"
        echo ""
        echo "$REPO_SCOPE_MARKER_END"
      } > "$claude_md"
      rm -f "$tmp"
      success "$repo_name: scope block refreshed ($scope)"
    elif [[ -f "$claude_md" ]]; then
      # CLAUDE.md exists but no block — append
      backup_file "$claude_md"
      {
        cat "$claude_md"
        if [[ -n "$(tail -c1 "$claude_md" 2>/dev/null)" ]]; then echo ""; fi
        echo ""
        echo "$REPO_SCOPE_MARKER_BEGIN"
        echo ""
        echo "$body"
        echo ""
        echo "$REPO_SCOPE_MARKER_END"
      } > "${claude_md}.new"
      mv "${claude_md}.new" "$claude_md"
      success "$repo_name: scope block appended vào CLAUDE.md có sẵn ($scope)"
    else
      # No CLAUDE.md — create minimal one with scope block
      {
        echo "# $repo_name"
        echo ""
        echo "Code repo của project **${RESOLVED_PROJECT_NAME:-project}**. Spec + design sống ở spec repo (xem multi-root workspace)."
        echo ""
        echo "$REPO_SCOPE_MARKER_BEGIN"
        echo ""
        echo "$body"
        echo ""
        echo "$REPO_SCOPE_MARKER_END"
      } > "$claude_md"
      success "$repo_name: CLAUDE.md created + scope block written ($scope)"
    fi

    i=$((i + 1))
  done
}

# ═══════════════════════════════════════════════════════════════════
# V6: CODING RULES import per code repo (FE / BE)
# ═══════════════════════════════════════════════════════════════════
# Rule chi tiết theo stack (Angular FE / BE tài chính) sống ở ~/.claude/rules/
# (machine-local, cài bởi scripts/sync-skills-to-user.sh chạy từ repo template).
# Bootstrap chỉ chèn dòng import `@~/.claude/rules/<file>` vào CLAUDE.md của
# từng CODE repo theo stack detect được — spec repo KHÔNG chèn (session làm
# tài liệu không cần rule code, tránh loãng context).
#   - Repo có FE framework deps  → import fe-angular-rules.md
#   - Repo có BE manifest/deps   → import be-finance-rules.md
#   - Monorepo có cả 2 signal    → import cả 2
#   - Repo Apple CÓ giao diện    → tính là FE (cho Design System) nhưng KHÔNG
#     import rule web, vì bộ rule FE hiện có là rule Angular
#   - Repo Apple KHÔNG giao diện → thư viện client, không FE không BE: không
#     Design System, không rule import
#   - Không signal (unknown)     → không chèn

RULES_IMPORT_MARKER_BEGIN="<!-- >>> NTAPP coding rules import (auto-managed, do not edit) >>>"
RULES_IMPORT_MARKER_END="<!-- <<< NTAPP coding rules import <<< -->"
FE_RULES_FILE="fe-angular-rules.md"
BE_RULES_FILE="be-finance-rules.md"

# kinds là list token cách nhau bởi space. So khớp NGUYÊN token để "fe-apple"
# không lọt qua phép so khớp lỏng của rule FE web.
kinds_has() {
  local token="$1" kinds="$2"
  [[ " $kinds " == *" $token "* ]]
}

# Detect bộ rule cho repo — echo "fe", "be", "fe-apple", "fe be", hoặc "" (none).
# Cùng heuristic manifest với detect_repo_scope_for_repo nhưng trả lời câu hỏi
# khác: repo chứa code FE hay BE (scope trả lời service-only vs fullstack).
# Lưu ý: mọi token bắt đầu bằng "fe" đều được các chỗ đếm FE repo (Design System
# multi-DS) tính là FE — riêng "fe-apple" thì không map sang file rule nào.
detect_repo_rules_for_repo() {
  local repo="$1"
  # Manifest có thể nằm sâu 1 cấp — soi thư mục chứa manifest thật.
  repo="$(find_manifest_dir "$repo")"
  local kinds=""

  if [[ -f "$repo/package.json" ]]; then
    if grep -qE '"(react|next|vue|svelte|@angular/core|nuxt|remix|astro|solid-js|preact|qwik)"' "$repo/package.json" 2>/dev/null; then
      kinds="fe"
    fi
    if grep -qE '"(express|fastify|@nestjs/core|koa|hapi|hono|@hapi/hapi|restify)"' "$repo/package.json" 2>/dev/null; then
      kinds="${kinds:+$kinds }be"
    fi
  fi

  # Marker Apple chỉ nói repo dùng toolchain Apple, CHƯA nói là repo có giao
  # diện. SDK Swift thuần dữ liệu (networking, mã hoá) không có màn hình nào →
  # cấp Design System cho nó chỉ tạo ra thư mục rỗng và một dòng rác trong
  # registry. Xét thêm UI framework thật để đường Apple có cùng độ phân giải
  # với đường web (đường web xét dependency, không xét sự tồn tại manifest).
  if [[ "$kinds" != *fe* ]] && [[ -n "$(detect_apple_marker "$repo")" ]]; then
    if [[ "$(detect_apple_ui_framework "$repo")" == "<TODO>" ]]; then
      kinds="${kinds:+$kinds }apple-lib"
    else
      kinds="${kinds:+$kinds }fe-apple"
    fi
  fi

  if [[ "$kinds" != *be* ]]; then
    for manifest in pom.xml build.gradle build.gradle.kts go.mod Cargo.toml pyproject.toml requirements.txt; do
      if [[ -f "$repo/$manifest" ]]; then
        kinds="${kinds:+$kinds }be"
        break
      fi
    done
  fi

  echo "$kinds"
}

# Repo có rule file nào để import không (fe-apple hiện chưa có bộ rule riêng)
rules_kinds_importable() {
  local kinds="$1"
  kinds_has fe "$kinds" || kinds_has be "$kinds"
}

# Render nội dung block import theo danh sách rule kind ("fe", "be", "fe be")
render_rules_import_block() {
  local kinds="$1"
  echo "## Coding rules"
  echo ""
  echo "Rule code chi tiết theo stack — import từ \`~/.claude/rules/\` (machine-local; mỗi dev cài bằng \`./scripts/sync-skills-to-user.sh\` chạy từ repo template NTAPP). Nếu file chưa tồn tại, import bị bỏ qua — chạy script sync để kích hoạt."
  echo ""
  if kinds_has fe "$kinds"; then
    echo "@~/.claude/rules/$FE_RULES_FILE"
  fi
  if kinds_has be "$kinds"; then
    echo "@~/.claude/rules/$BE_RULES_FILE"
  fi
}

# Chèn/refresh block import vào CLAUDE.md của mọi code repo (idempotent, marker-based)
setup_rule_imports() {
  heading "Coding rules import (FE / BE)"

  if [[ ${#DETECTED_CODE_REPOS[@]} -eq 0 ]]; then
    info "Không có code repo → skip"
    return 0
  fi

  if [[ ! -f "$HOME/.claude/rules/$FE_RULES_FILE" ]] && [[ ! -f "$HOME/.claude/rules/$BE_RULES_FILE" ]]; then
    warn "~/.claude/rules/ chưa có rule file — import sẽ chưa có tác dụng."
    warn "  → Chạy ./scripts/sync-skills-to-user.sh từ repo template NTAPP để cài."
  fi

  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    local repo_name kinds claude_md
    repo_name="$(basename "$repo")"
    claude_md="$repo/CLAUDE.md"
    kinds="$(detect_repo_rules_for_repo "$repo")"

    if [[ -z "$kinds" ]]; then
      info "$repo_name: không detect được FE/BE → không chèn rule import"
      continue
    fi

    if ! rules_kinds_importable "$kinds"; then
      info "$repo_name: stack '$kinds' — chưa có bộ rule tương ứng trong ~/.claude/rules/ → không chèn rule import"
      continue
    fi

    if [[ "$DRY_RUN" == "1" ]]; then
      info "[DRY-RUN] $repo_name: chèn rule import ($kinds) vào CLAUDE.md"
      continue
    fi

    local body
    body="$(render_rules_import_block "$kinds")"

    if [[ -f "$claude_md" ]] && grep -qF "$RULES_IMPORT_MARKER_BEGIN" "$claude_md"; then
      # Block đã có — so nội dung, giống hệt thì skip, khác thì replace
      local existing_body
      existing_body="$(awk -v begin="$RULES_IMPORT_MARKER_BEGIN" -v end="$RULES_IMPORT_MARKER_END" '
        index($0, begin)==1 {inblock=1; next}
        index($0, end)==1 {inblock=0; next}
        inblock' "$claude_md")"
      if [[ "$(echo "$existing_body" | grep -v '^[[:space:]]*$' || true)" == "$(echo "$body" | grep -v '^[[:space:]]*$' || true)" ]]; then
        info "$repo_name: rule import đã đúng ($kinds) → skip"
        continue
      fi
      backup_file "$claude_md"
      local tmp="${claude_md}.tmp.$$"
      awk -v begin="$RULES_IMPORT_MARKER_BEGIN" -v end="$RULES_IMPORT_MARKER_END" '
        index($0, begin)==1 {skip=1; next}
        index($0, end)==1 {skip=0; next}
        !skip
      ' "$claude_md" > "$tmp"
      {
        cat "$tmp"
        echo ""
        echo "$RULES_IMPORT_MARKER_BEGIN"
        echo ""
        echo "$body"
        echo ""
        echo "$RULES_IMPORT_MARKER_END"
      } > "$claude_md"
      rm -f "$tmp"
      success "$repo_name: rule import refreshed ($kinds)"
    elif [[ -f "$claude_md" ]]; then
      backup_file "$claude_md"
      {
        cat "$claude_md"
        if [[ -n "$(tail -c1 "$claude_md" 2>/dev/null)" ]]; then echo ""; fi
        echo ""
        echo "$RULES_IMPORT_MARKER_BEGIN"
        echo ""
        echo "$body"
        echo ""
        echo "$RULES_IMPORT_MARKER_END"
      } > "${claude_md}.new"
      mv "${claude_md}.new" "$claude_md"
      success "$repo_name: rule import appended vào CLAUDE.md có sẵn ($kinds)"
    else
      {
        echo "# $repo_name"
        echo ""
        echo "Code repo của project **${RESOLVED_PROJECT_NAME:-project}**. Spec + design sống ở spec repo (xem multi-root workspace)."
        echo ""
        echo "$RULES_IMPORT_MARKER_BEGIN"
        echo ""
        echo "$body"
        echo ""
        echo "$RULES_IMPORT_MARKER_END"
      } > "$claude_md"
      success "$repo_name: CLAUDE.md created + rule import written ($kinds)"
    fi
  done
}

# ═══════════════════════════════════════════════════════════════════
# PROJECT NAME — SSoT là heading '# Project: ' ở CLAUDE.md
# ═══════════════════════════════════════════════════════════════════
# Spec repo sinh ra bằng cách COPY base template (README §Bước 2) → CLAUDE.md
# mang sẵn heading của template. Nếu coi heading đó là "đã cấu hình" thì MỌI
# project copy ra đều tên 'NTAPP (VSAF Blended)' và workspace file cũng vậy —
# nên tên template phải bị xử như placeholder, tên thật suy từ tiêu đề spec repo.
TEMPLATE_PROJECT_NAMES=(
  "<PROJECT_NAME>"
  "NTAPP (VSAF Blended)"
  "NTAPP VSAF Blended"
  "NTAPP-VSAF-Blended"
  "NTAPP VSAF"
  "ntapp-vsaf-blended-template"
)

read_project_name() {
  grep -E '^# Project: ' "$SPEC_REPO_ROOT/CLAUDE.md" 2>/dev/null | head -1 | sed -E 's/^# Project: *//'
}

is_template_project_name() {
  local name="$1" t
  [[ -z "$name" ]] && return 0
  for t in "${TEMPLATE_PROJECT_NAMES[@]}"; do
    [[ "$name" == "$t" ]] && return 0
  done
  return 1
}

# Base template repo tự bootstrap (dev/maintain template) — nhận diện qua
# README.spec-template.md: spec repo copy ra đã `mv` file này thành README.md.
# Ở base template thì KHÔNG rename identity của nó thành tên thư mục.
is_base_template_repo() {
  [[ -f "$SPEC_REPO_ROOT/README.spec-template.md" ]]
}

# Tiêu đề spec repo = tên thư mục, bỏ hậu tố -doc / -spec (README: '<project>-spec')
default_project_name() {
  basename "$SPEC_REPO_ROOT" | sed -E 's/-(doc|spec)$//'
}

# Ghi tên vào heading TRỰC TIẾP (không phụ thuộc placeholder còn tồn tại — bản
# copy từ template đã mất <PROJECT_NAME> từ lâu) + key project_name của BMM.
write_project_name() {
  local name="$1" esc claude_md="$SPEC_REPO_ROOT/CLAUDE.md" tmp
  esc=$(printf '%s' "$name" | sed -e 's/[\\&|]/\\&/g')  # escape cho replacement của sed

  backup_file "$claude_md"
  if grep -qE '^# Project: ' "$claude_md"; then
    # Giới hạn 20 dòng đầu: heading identity ở dòng 1, không đụng prose bên dưới
    sed_inplace "1,20s|^# Project: .*|# Project: $esc|" "$claude_md"
  else
    tmp="$claude_md.tmp.$$"
    { printf '# Project: %s\n\n' "$name"; cat "$claude_md"; } > "$tmp" && mv "$tmp" "$claude_md"
  fi
  sed_inplace "s|<PROJECT_NAME>|$esc|g" "$claude_md"

  if [[ -f "$SPEC_REPO_ROOT/_bmad/bmm/config.yaml" ]]; then
    backup_file "$SPEC_REPO_ROOT/_bmad/bmm/config.yaml"
    sed_inplace "s|^project_name:.*|project_name: $esc|" "$SPEC_REPO_ROOT/_bmad/bmm/config.yaml"
    sed_inplace "s|<PROJECT_NAME>|$esc|g" "$SPEC_REPO_ROOT/_bmad/bmm/config.yaml"
  fi
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Project name
# ═══════════════════════════════════════════════════════════════════
setup_project_name() {
  heading "Project name"

  local current_name
  current_name=$(read_project_name)

  if is_template_project_name "$current_name"; then
    # Tên template/placeholder → phải đặt tên thật, KHÔNG hỏi "Override?" (default
    # 'n' + AUTO_CONFIRM biến nó thành cái bẫy: mọi project giữ tên template).
    if [[ -z "${PROJECT_NAME:-}" ]] && is_base_template_repo; then
      info "Base template repo (README.spec-template.md còn đó) — giữ nguyên tên '$current_name'"
      export RESOLVED_PROJECT_NAME="$current_name"
      return 0
    fi
    [[ -n "$current_name" ]] && info "CLAUDE.md đang là placeholder / tên base template ('$current_name') → đặt tên project thật"
  else
    info "CLAUDE.md đã có project name: '$current_name'"
    if [[ -z "${PROJECT_NAME:-}" ]] || [[ "$PROJECT_NAME" == "$current_name" ]]; then
      if ! ask_yn "Override?" "n"; then
        export RESOLVED_PROJECT_NAME="$current_name"
        return 0
      fi
    else
      info "PROJECT_NAME='$PROJECT_NAME' (env) → override tên cũ"
    fi
  fi

  local project_name="${PROJECT_NAME:-}"
  if [[ -z "$project_name" ]]; then
    project_name=$(ask "Tên project" "$(default_project_name)")
  fi

  if [[ -z "$project_name" ]]; then
    error "Project name không được rỗng"
    exit 1
  fi

  if is_template_project_name "$project_name" && ! is_base_template_repo; then
    warn "'$project_name' là tên base template — workspace file sẽ mang tên đó. Đặt tên riêng cho project thì chạy lại với PROJECT_NAME=\"<tên>\"."
  fi

  if [[ "$DRY_RUN" == "0" ]]; then
    write_project_name "$project_name"
  else
    info "[DRY-RUN] Would set '# Project: $project_name' trong CLAUDE.md + project_name trong _bmad/bmm/config.yaml"
  fi

  export RESOLVED_PROJECT_NAME="$project_name"
  success "Project name: $project_name  (workspace: $project_name.code-workspace)"
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Generate workspace file
# ═══════════════════════════════════════════════════════════════════
generate_workspace() {
  heading "Workspace file"

  if [[ ${#DETECTED_CODE_REPOS[@]} -eq 0 ]] && [[ -z "$DETECTED_META_REPO" ]]; then
    info "Single-repo mode → skip workspace generation"
    return 0
  fi

  # Workspace ở meta repo nếu có, else ở spec repo
  local workspace_host
  if [[ -n "$DETECTED_META_REPO" ]]; then
    workspace_host="$DETECTED_META_REPO/workspaces"
    run "mkdir -p \"$workspace_host\""
  else
    workspace_host="$SPEC_REPO_ROOT"
  fi

  local workspace_file="$workspace_host/${RESOLVED_PROJECT_NAME:-project}.code-workspace"
  backup_file "$workspace_file"

  # Build folders: mảng "name|path" (path đã forward-slash từ relpath)
  local ws_folders=()

  # Spec repo entry
  local spec_path
  if [[ "$workspace_host" == "$SPEC_REPO_ROOT" ]]; then
    spec_path="."
  else
    spec_path=$(relpath "$SPEC_REPO_ROOT" "$workspace_host" "../../$(basename "$SPEC_REPO_ROOT")")
  fi
  ws_folders+=("spec-repo|$spec_path")

  # Code repos
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    local repo_name repo_path
    repo_name=$(basename "$repo")
    repo_path=$(relpath "$repo" "$workspace_host" "../../$repo_name")
    ws_folders+=("$repo_name|$repo_path")
  done

  # Meta repo (if exists and workspace not hosted there)
  if [[ -n "$DETECTED_META_REPO" ]] && [[ "$workspace_host" != "$DETECTED_META_REPO/workspaces" ]]; then
    local meta_path
    meta_path=$(relpath "$DETECTED_META_REPO" "$workspace_host" "../../$(basename "$DETECTED_META_REPO")")
    ws_folders+=("meta-repo|$meta_path")
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    success "Workspace: $workspace_file"
    return 0
  fi

  # Render qua Python — robust cross-platform. (perl one-liner escaping không đáng tin
  # trên Windows/Git-Bash: không escape slash, không join newline → sinh JSON hỏng.)
  # Python giữ nguyên block settings trong template + validate JSON trước khi ghi.
  if [[ -n "$PYTHON_BIN" ]]; then
    $PYTHON_BIN -c '
import json, sys
tmpl_path, out_path = sys.argv[1], sys.argv[2]
folders = []
for pair in sys.argv[3:]:
    name, _, path = pair.partition("|")
    folders.append({"name": name, "path": path})
block = ",\n    ".join(json.dumps(f, indent=2).replace("\n", "\n    ") for f in folders)
with open(tmpl_path, encoding="utf-8") as f:
    content = f.read()
content = content.replace("{{FOLDERS}}", block)
json.loads(content)  # validate trước khi ghi
with open(out_path, "w", encoding="utf-8") as f:
    f.write(content)
' "$WORKSPACE_TEMPLATE" "$workspace_file" "${ws_folders[@]}"
  else
    # Fallback không có Python: build tay (settings tối giản)
    {
      echo "{"
      echo "  \"folders\": ["
      local n=${#ws_folders[@]} idx=0 pair name path
      for pair in "${ws_folders[@]}"; do
        name="${pair%%|*}"; path="${pair#*|}"
        idx=$((idx + 1))
        printf '    { "name": "%s", "path": "%s" }' "$name" "$path"
        [[ $idx -lt $n ]] && printf ','
        printf '\n'
      done
      echo "  ],"
      echo "  \"settings\": {"
      echo "    \"files.exclude\": { \"**/node_modules\": true, \"**/NTAPP-output/archive\": true }"
      echo "  }"
      echo "}"
    } > "$workspace_file"
  fi

  success "Workspace: $workspace_file"
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Generate per-code-repo .bmm-config.yaml
# ═══════════════════════════════════════════════════════════════════

# ─── Multi-DS helpers (per-repo design_system_root) ─────────────────
# Nhiều FE repo → mỗi repo 1 DS root riêng trong design-system/ (namespaced theo
# registry.yaml). Schema: spec repo NTAPP-output/design-system/_shared/ds-registry-schema.md.

# ds_id từ tên repo: lowercase, non-alnum → '-'.
ds_id_for_repo_name() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

# Đếm repo FE-capable (heuristic manifest — cùng nguồn detect_repo_rules_for_repo).
count_fe_repos() {
  local n=0 repo
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    case "$(detect_repo_rules_for_repo "$repo")" in *fe*) n=$((n+1)) ;; esac
  done
  echo "$n"
}

# Tra root của repo trong registry.yaml theo code_repo. Echo root ("." | "{ds}/") hoặc rỗng.
registry_root_for_repo() {
  local reg="$1" want="$2"
  [[ -f "$reg" ]] || { echo ""; return; }
  awk -v want="$want" '
    # exit trong awk vẫn chạy END → guard done chống flush in đôi
    function flush() { if (!done && found && root != "") { print root; done=1; exit } }
    /^  [A-Za-z0-9_-]+:[[:space:]]*$/ { flush(); root=""; found=0 }
    /^[[:space:]]+root:/ {
      r=$0; sub(/^[[:space:]]+root:[[:space:]]*/, "", r); gsub(/["\047]/, "", r); root=r
    }
    /^[[:space:]]+code_repo:/ {
      c=$0; sub(/^[[:space:]]+code_repo:[[:space:]]*/, "", c); gsub(/["\047\[\]]/, "", c)
      n=split(c, arr, /,[[:space:]]*/)
      for (i=1; i<=n; i++) if (arr[i] == want) found=1
    }
    END { flush() }
  ' "$reg"
}

# Scaffold registry.yaml — chỉ khi ≥2 FE repo + chưa có registry + chưa có DS legacy.
scaffold_ds_registry() {
  local family_root="$SPEC_REPO_ROOT/NTAPP-output/design-system"
  local registry_file="$family_root/registry.yaml"

  info "Multi-DS: ≥2 FE repo, chưa có DS nào → scaffold registry.yaml (1 DS namespaced / FE repo)"
  if [[ "$DRY_RUN" == "1" ]]; then
    info "  [dry-run] sẽ tạo $registry_file"
    return 0
  fi

  mkdir -p "$family_root"
  {
    echo "# DS Registry — sinh bởi bootstrap.sh (multi-FE-repo)."
    echo "# Schema + semantics: _shared/ds-registry-schema.md. Resolve: _shared/ds-resolution.md."
    echo "# DSO bổ sung id_prefixes/modules để skill resolve unit→DS không cần hỏi."
    echo "version: 1"
    echo ""
    echo "systems:"
    local repo repo_name ds_id stack_info lang framework ui_lib build_tool
    for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
      case "$(detect_repo_rules_for_repo "$repo")" in *fe*) ;; *) continue ;; esac
      repo_name=$(basename "$repo")
      ds_id=$(ds_id_for_repo_name "$repo_name")
      stack_info=$(detect_stack_for_repo "$repo")
      IFS='|' read -r lang framework ui_lib build_tool <<< "$stack_info"
      echo "  $ds_id:"
      echo "    root: \"$ds_id/\""
      echo "    code_repo: $repo_name"
      echo "    framework: ${framework:-unknown}"
      echo "    # id_prefixes: [SCR-XXX-, WGT-XXX-]   # hint resolve unit→DS (khuyến nghị điền)"
    done
  } > "$registry_file"
  success "  → $registry_file (commit vào spec repo — SSoT danh sách DS)"
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Spec repo .bmm-config.yaml (Layer 2)
# ═══════════════════════════════════════════════════════════════════
# Trước đây bước này không tồn tại: file được coi là "người viết tay rồi commit"
# nên script không đụng tới. Giả định đó vỡ khi project mới được scaffold từ một
# pack — repo mới nhận nguyên si file của project cũ, trỏ spec_repo_root sang
# một thư mục không tồn tại. Đã xảy ra ít nhất hai lần và phải sửa tay.
#
# Nên bước này KHÔNG ghi vô điều kiện. Nó chỉ ghi khi file chưa có, hoặc khi file
# hiện tại lộ dấu hiệu là bản chép nhầm; file đã tinh chỉnh tay thì để nguyên và
# chỉ cảnh báo. Đây là nơi duy nhất `okf.families` được rót vào project mới —
# engine chỉ đọc families từ Layer 2, khai ở Layer 1 sẽ bị bỏ qua âm thầm.

# Dấu hiệu file là bản hand-tuned thật → tuyệt đối không ghi đè.
spec_config_is_handtuned() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  grep -qE "^  families:" "$file" && return 0
  grep -qE "^ntapp-[a-z-]+:" "$file" && return 0
  return 1
}

# Dấu hiệu file là bản chép nhầm từ project khác.
# In ra từng lý do để người đọc log biết vì sao file bị thay, không phải đoán.
spec_config_staleness() {
  local file="$1"
  local reasons=()
  if grep -qE "^# .*CODE REPO config" "$file"; then
    reasons+=("header khai là CODE REPO config")
  fi
  local pname
  pname=$(grep -E "^project_name:" "$file" | head -1 | sed -E 's/^project_name:[[:space:]]*//; s/^"(.*)"$/\1/')
  if [[ -z "$pname" ]] || [[ "$pname" == "project" ]] || [[ "$pname" == "<PROJECT_NAME>" ]]; then
    reasons+=("project_name còn là placeholder ('${pname}')")
  fi
  local sroot
  sroot=$(grep -E "^  spec_repo_root:" "$file" | head -1 | sed -E 's/^  spec_repo_root:[[:space:]]*//; s/^"(.*)"$/\1/')
  if [[ -n "$sroot" ]] && [[ "$sroot" != "." ]]; then
    reasons+=("spec_repo_root trỏ ra ngoài repo này ('${sroot}')")
  fi
  printf '%s\n' ${reasons[@]+"${reasons[@]}"}
}

# Danh sách code_repos cho block OKF. Để dạng comment: engine chỉ nên biết repo
# đã thực sự gắn thẻ `// id:` ở đầu file code, mà lúc bootstrap thì chưa repo nào
# gắn. Khai sớm một repo 0 thẻ sẽ kéo số độ phủ xuống theo hướng sai.
render_okf_code_repos() {
  if [[ ${#DETECTED_CODE_REPOS[@]} -eq 0 ]]; then
    echo "    # Chưa phát hiện code repo nào. Thêm khi có, dạng:"
    echo "    #   - {name: <ten-repo>, path: ../<ten-repo>}"
    return 0
  fi
  echo "    # Bỏ comment từng dòng KHI repo đó đã gắn thẻ \`// id:\` ở đầu file code."
  local repo repo_name
  for repo in "${DETECTED_CODE_REPOS[@]}"; do
    repo_name=$(basename "$repo")
    echo "    # - {name: $repo_name, path: ../$repo_name}"
  done
}

generate_spec_repo_config() {
  heading "Spec repo config (.bmm-config.yaml + lớp OKF)"

  local config_path="$SPEC_REPO_ROOT/.bmm-config.yaml"
  local spec_repo_name
  spec_repo_name=$(basename "$SPEC_REPO_ROOT")

  if [[ ! -f "$SPEC_BMM_CONFIG_TEMPLATE" ]]; then
    warn "Thiếu template $SPEC_BMM_CONFIG_TEMPLATE → skip"
    return 0
  fi

  if spec_config_is_handtuned "$config_path"; then
    info "$spec_repo_name: .bmm-config.yaml đã tinh chỉnh tay (có families / override ntapp-*) → giữ nguyên"
    return 0
  fi

  local reasons=()
  if [[ -f "$config_path" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] && reasons+=("$line")
    done < <(spec_config_staleness "$config_path")

    if [[ ${#reasons[@]} -eq 0 ]]; then
      info "$spec_repo_name: .bmm-config.yaml hợp lệ → giữ nguyên"
      return 0
    fi

    warn "$spec_repo_name: .bmm-config.yaml có dấu hiệu là bản chép từ project khác:"
    local reason
    for reason in "${reasons[@]}"; do
      warn "    · $reason"
    done
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Would write $config_path (15 OKF family + per-skill overrides)"
    return 0
  fi

  backup_file "$config_path"

  # code_repos là block NHIỀU DÒNG. Cả hai cách hiển nhiên đều không portable:
  # chuỗi thay thế có newline thì sed BSD và GNU xử lý khác nhau, còn `awk -v`
  # thì BSD awk từ chối thẳng ("newline in string"). Nên block được ghi ra file
  # tạm và awk đọc bằng getline — biến truyền vào chỉ là một đường dẫn một dòng.
  local repos_file awk_rc=0
  repos_file=$(mktemp "${TMPDIR:-/tmp}/ntapp-okf-repos.XXXXXX")
  render_okf_code_repos > "$repos_file"

  # `lit()` thay chuỗi NGUYÊN VĂN. Không dùng gsub() vì awk đọc `&` trong chuỗi
  # thay thế là "phần vừa khớp" — một project name chứa `&` sẽ bị bóp méo lặng
  # lẽ. Cùng cái bẫy đó cũng có ở sed, chỉ là chưa ai đặt tên project như vậy.
  awk -v pname="${RESOLVED_PROJECT_NAME:-project}" \
      -v sname="$spec_repo_name" \
      -v ts="$TIMESTAMP" \
      -v reposfile="$repos_file" '
    function lit(s, needle, repl,   out, at) {
      out = ""
      while ((at = index(s, needle)) > 0) {
        out = out substr(s, 1, at - 1) repl
        s = substr(s, at + length(needle))
      }
      return out s
    }
    {
      $0 = lit($0, "{{PROJECT_NAME}}", pname)
      $0 = lit($0, "{{SPEC_REPO_NAME}}", sname)
      $0 = lit($0, "{{TIMESTAMP}}", ts)
      if (index($0, "{{OKF_CODE_REPOS}}") > 0) {
        while ((getline line < reposfile) > 0) print line
        close(reposfile)
        next
      }
      print
    }
  ' "$SPEC_BMM_CONFIG_TEMPLATE" > "$config_path" || awk_rc=$?

  # Dọn tường minh thay vì `trap ... RETURN`: RETURN là signal riêng của bash,
  # zsh từ chối thẳng. Đặt sau `|| awk_rc=$?` nên `set -e` không cắt ngang trước
  # khi tới đây, và lỗi vẫn được báo chứ không nuốt.
  rm -f "$repos_file"
  if [[ "$awk_rc" -ne 0 ]]; then
    error "$spec_repo_name: sinh .bmm-config.yaml thất bại (awk exit $awk_rc)"
    return 1
  fi

  success "  → $config_path (15 OKF family, min_nodes chờ điền sau lần chiếu đầu)"
  info "  Chạy /NTAPP-okf-refresh khi có artifact; family chưa tới stage sẽ tự bỏ qua."
}

generate_code_repo_configs() {
  heading "Code repo configs"

  if [[ ${#DETECTED_CODE_REPOS[@]} -eq 0 ]]; then
    info "Không có code repo → skip"
    return 0
  fi

  # Multi-DS pre-pass: ≥2 FE repo → mỗi FE repo 1 DS root riêng (registry-driven).
  local family_root="$SPEC_REPO_ROOT/NTAPP-output/design-system"
  local registry_file="$family_root/registry.yaml"
  local fe_count multi_ds=0
  fe_count=$(count_fe_repos)
  if [[ "$fe_count" -ge 2 ]]; then
    multi_ds=1
    if [[ ! -f "$registry_file" ]]; then
      if [[ -f "$family_root/master_token.json" ]]; then
        # DS legacy flat đã tồn tại — không biết thuộc FE repo nào → KHÔNG tự chia.
        warn "Multi-DS: $fe_count FE repo nhưng design-system/ đang là DS legacy (flat, chưa có registry.yaml)."
        warn "  → Configs tạm trỏ family root. Chạy /ntapp-ds-bootstrap từ FE repo MỚI — step-01 HITL sẽ"
        warn "    sinh registry (DS cũ root: \".\", DS mới namespaced) + sửa lại design_system_root repo đó."
        multi_ds=0
      else
        scaffold_ds_registry
      fi
    fi
  fi

  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    local repo_name
    repo_name=$(basename "$repo")
    local config_path="$repo/.bmm-config.yaml"

    # Calculate relative paths from code repo → spec/meta
    local spec_rel
    spec_rel=$(relpath "$SPEC_REPO_ROOT" "$repo" "../$(basename "$SPEC_REPO_ROOT")")

    local meta_rel="n/a"
    if [[ -n "$DETECTED_META_REPO" ]]; then
      meta_rel=$(relpath "$DETECTED_META_REPO" "$repo" "../$(basename "$DETECTED_META_REPO")")
    fi

    # Detect stack
    local stack_info
    stack_info=$(detect_stack_for_repo "$repo")
    local lang framework ui_lib build_tool
    IFS='|' read -r lang framework ui_lib build_tool <<< "$stack_info"

    # DS root per repo: default = family root (single-DS / repo BE). Multi-DS + FE repo
    # → {family}/{root} theo registry ("." = family root in-place).
    local ds_root_value="$spec_rel/NTAPP-output/design-system"
    if [[ "$multi_ds" == "1" ]]; then
      case "$(detect_repo_rules_for_repo "$repo")" in
        *fe*)
          local reg_root
          reg_root="$(registry_root_for_repo "$registry_file" "$repo_name")"
          if [[ -z "$reg_root" ]]; then
            reg_root="$(ds_id_for_repo_name "$repo_name")/"
            warn "  $repo_name chưa có trong registry.yaml — dùng DS root suy đoán '$reg_root'. Bổ sung entry registry cho khớp."
          fi
          if [[ "$reg_root" != "." ]]; then
            ds_root_value="$spec_rel/NTAPP-output/design-system/${reg_root%/}"
          fi
          ;;
      esac
    fi

    info "$repo_name: $lang/$framework (build: $build_tool) — DS root: ${ds_root_value#$spec_rel/}"

    backup_file "$config_path"

    if [[ "$DRY_RUN" == "0" ]]; then
      sed -e "s|{{PROJECT_NAME}}|${RESOLVED_PROJECT_NAME:-project}|g" \
          -e "s|{{CODE_REPO_NAME}}|$repo_name|g" \
          -e "s|{{TIMESTAMP}}|$TIMESTAMP|g" \
          -e "s|{{SPEC_REPO_RELATIVE}}|$spec_rel|g" \
          -e "s|{{META_REPO_RELATIVE}}|$meta_rel|g" \
          -e "s|{{DS_ROOT}}|$ds_root_value|g" \
          -e "s|{{LANG}}|$lang|g" \
          -e "s|{{FRAMEWORK}}|$framework|g" \
          -e "s|{{UI_LIB}}|$ui_lib|g" \
          -e "s|{{BUILD_TOOL}}|$build_tool|g" \
          "$BMM_CONFIG_TEMPLATE" > "$config_path"
    fi

    success "  → $config_path"
  done
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Symlink skill library cross-repo
# ═══════════════════════════════════════════════════════════════════
link_skills() {
  heading "Symlink skill library"

  if [[ ${#DETECTED_CODE_REPOS[@]} -eq 0 ]]; then
    info "Không có code repo → skip"
    return 0
  fi

  # Source of skills: meta repo nếu có, else spec repo
  local skill_source
  if [[ -n "$DETECTED_META_REPO" ]] && [[ -d "$DETECTED_META_REPO/.agent/skills" ]]; then
    skill_source="$DETECTED_META_REPO/.agent/skills"
    info "Skill source: meta repo"
  else
    skill_source="$SPEC_REPO_ROOT/.agent/skills"
    info "Skill source: spec repo"
  fi

  # Skill source có thể đã bị gỡ khỏi spec repo (skills nạp từ môi trường Claude
  # global thay vì symlink repo). Không có source thì bỏ qua cả bước — tạo symlink
  # trỏ vào đích không tồn tại sẽ fail trên Windows (ln nativestrict) và abort script.
  if [[ ! -d "$skill_source" ]]; then
    warn "Skill source không tồn tại: $skill_source — skip symlink skill (skills nạp từ Claude global)."
    return 0
  fi

  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    local repo_name
    repo_name=$(basename "$repo")
    local target="$repo/.agent/skills"
    local target_parent="$repo/.agent"

    # Compute RELATIVE path from target's parent dir → skill_source
    # → symlink survives git clone vì không hardcode absolute path máy lead
    local rel_source
    rel_source=$(relpath "$skill_source" "$target_parent" "$skill_source")

    if [[ -L "$target" ]]; then
      # Already symlinked — verify and refresh if needed
      local current_target
      current_target=$(readlink "$target")
      # Accept either the new relative path OR legacy absolute path pointing to same place
      if [[ "$current_target" == "$rel_source" ]] || [[ "$current_target" == "$skill_source" ]]; then
        # Migrate legacy absolute → relative
        if [[ "$current_target" == "$skill_source" ]] && [[ "$current_target" != "$rel_source" ]]; then
          info "$repo_name: migrate symlink absolute → relative"
          run "rm \"$target\""
          run "ln -sf \"$rel_source\" \"$target\""
        else
          info "$repo_name: skill symlink OK (relative)"
        fi
        continue
      fi
      warn "$repo_name: skill symlink trỏ sai đích, fix lại"
      run "rm \"$target\""
    elif [[ -d "$target" ]]; then
      warn "$repo_name: .agent/skills/ là folder thật (không phải symlink) — skip để tránh data loss"
      info "  → Manual: backup $target rồi xóa, chạy lại script"
      continue
    fi

    run "mkdir -p \"$target_parent\""
    run "ln -sf \"$rel_source\" \"$target\""
    success "$repo_name: skill symlinked → $rel_source (relative)"
  done
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Setup .gitignore (machine-local artifacts)
# ═══════════════════════════════════════════════════════════════════
# Tránh accident commit symlink absolute hoặc IDE cache giữa các máy.
# Idempotent: dùng marker block để re-apply sạch, không duplicate entry.
setup_gitignore() {
  heading "Setup .gitignore (machine-local artifacts)"

  local marker_begin="# >>> NTAPP bootstrap (auto-managed, do not edit) >>>"
  local marker_end="# <<< NTAPP bootstrap <<<"

  # Spec repo: KHÔNG ignore .agent/skills (đây là canonical source).
  # Spec repo .bmm-config.yaml là hand-edited project config → commit.
  local spec_entries=".claude/skills/
.cursor/skills/
.claude/hooks
*.bak.*"

  # Code repo: ignore tất cả machine-local artifacts do bootstrap sinh ra.
  # .bmm-config.yaml ở code repo có TIMESTAMP comment + stack auto-detect
  # → vary per machine → gitignore, mỗi máy bootstrap tự sinh lại.
  local code_entries=".agent/skills
.claude/skills/
.cursor/skills/
.claude/hooks
.claude/settings.json
.bmm-config.yaml
*.bak.*"

  local repos=("$SPEC_REPO_ROOT")
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do repos+=("$repo"); done

  for repo in "${repos[@]}"; do
    local repo_name
    repo_name=$(basename "$repo")
    local gitignore="$repo/.gitignore"
    local entries
    if [[ "$repo" == "$SPEC_REPO_ROOT" ]]; then
      entries="$spec_entries"
    else
      entries="$code_entries"
    fi

    if [[ "$DRY_RUN" == "1" ]]; then
      if [[ -f "$gitignore" ]] && grep -qF "$marker_begin" "$gitignore"; then
        info "[DRY-RUN] $repo_name: refresh NTAPP block in .gitignore"
      else
        info "[DRY-RUN] $repo_name: add NTAPP block to .gitignore"
      fi
      continue
    fi

    if [[ -f "$gitignore" ]] && grep -qF "$marker_begin" "$gitignore"; then
      # Block exists — strip + re-append
      backup_file "$gitignore"
      local tmp="${gitignore}.tmp.$$"
      awk -v begin="$marker_begin" -v end="$marker_end" '
        index($0, begin) == 1 {skip=1; next}
        index($0, end) == 1 {skip=0; next}
        !skip
      ' "$gitignore" > "$tmp"
      # Strip trailing blank lines
      sed_inplace '/./,$!d' "$tmp" 2>/dev/null || true
      {
        cat "$tmp"
        echo ""
        echo "$marker_begin"
        echo "$entries"
        echo "$marker_end"
      } > "$gitignore"
      rm -f "$tmp"
      success "$repo_name: .gitignore NTAPP block refreshed"
    else
      # No block — append (create file if needed)
      {
        if [[ -f "$gitignore" ]]; then
          cat "$gitignore"
          # Ensure trailing newline before our block
          if [[ -n "$(tail -c1 "$gitignore" 2>/dev/null)" ]]; then echo ""; fi
        fi
        echo ""
        echo "$marker_begin"
        echo "$entries"
        echo "$marker_end"
      } > "${gitignore}.new"
      mv "${gitignore}.new" "$gitignore"
      success "$repo_name: .gitignore NTAPP block added"
    fi
  done
}

# ═══════════════════════════════════════════════════════════════════
# HELPER: upsert 1 block giữa 2 marker (idempotent)
# ═══════════════════════════════════════════════════════════════════
# Cùng khuôn với setup_gitignore / setup_rule_imports, gom lại vì dùng ở nhiều
# file. Block đã đúng → KHÔNG đụng vào file (return 1); khác → backup rồi
# replace; file có sẵn nhưng chưa có block → append; file chưa tồn tại → tạo.
# Nội dung ngoài block (kể cả phần user đã sửa) luôn được giữ nguyên.
#
# upsert_marker_block <file> <begin> <end> <body> [header_khi_tao_moi]
# Return: 0 = đã ghi, 1 = không đổi. LUÔN gọi trong ngữ cảnh `if` (set -e).
upsert_marker_block() {
  local file="$1" begin="$2" end="$3" body="$4" header="${5:-}"

  if [[ -f "$file" ]] && grep -qF "$begin" "$file"; then
    local existing
    existing="$(awk -v b="$begin" -v e="$end" '
      index($0, b) == 1 {inblock=1; next}
      index($0, e) == 1 {inblock=0; next}
      inblock
    ' "$file")"
    [[ "$existing" == "$body" ]] && return 1

    backup_file "$file"
    local tmp="${file}.tmp.$$"
    awk -v b="$begin" -v e="$end" '
      index($0, b) == 1 {skip=1; next}
      index($0, e) == 1 {skip=0; next}
      !skip
    ' "$file" > "$tmp"
    # Bỏ dòng trắng thừa ở cuối phần giữ lại, rồi tự chèn 1 dòng ngăn cách.
    sed_inplace '/./,$!d' "$tmp" 2>/dev/null || true
    {
      cat "$tmp"
      echo ""
      echo "$begin"
      echo "$body"
      echo "$end"
    } > "$file"
    rm -f "$tmp"
    return 0
  fi

  if [[ -f "$file" ]]; then
    backup_file "$file"
    {
      cat "$file"
      if [[ -n "$(tail -c1 "$file" 2>/dev/null)" ]]; then echo ""; fi
      echo ""
      echo "$begin"
      echo "$body"
      echo "$end"
    } > "${file}.new"
    mv "${file}.new" "$file"
    return 0
  fi

  {
    if [[ -n "$header" ]]; then
      echo "$header"
      echo ""
    fi
    echo "$begin"
    echo "$body"
    echo "$end"
  } > "$file"
  return 0
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Setup .gitattributes ở spec repo (eol=lf — nền của OKF content_sha)
# ═══════════════════════════════════════════════════════════════════
# Không có file này, máy Windows clone với mặc định core.autocrlf=true sẽ
# checkout mọi .md thành CRLF → byte đổi → SHA đổi → toàn bộ node OKF báo
# stale trên máy đó; refresh xong thì tới lượt macOS/CI thấy y như vậy. Hai
# bên ping-pong commit 2.340 file vô tận. Lớp phòng thứ hai (lớp một là băm
# trên văn bản đã chuẩn hoá trong okf_project.py) — cần cả hai.
GITATTRIBUTES_MARKER_BEGIN="# >>> NTAPP bootstrap (auto-managed, do not edit) >>>"
GITATTRIBUTES_MARKER_END="# <<< NTAPP bootstrap <<<"

setup_gitattributes() {
  heading "Setup .gitattributes (eol=lf)"

  if [[ ! -f "$GITATTRIBUTES_TEMPLATE" ]]; then
    warn "Template không tồn tại: $GITATTRIBUTES_TEMPLATE → skip"
    return 0
  fi

  local target="$SPEC_REPO_ROOT/.gitattributes"
  local body
  body="$(cat "$GITATTRIBUTES_TEMPLATE")"

  if [[ "$DRY_RUN" == "1" ]]; then
    if [[ -f "$target" ]] && grep -qF "$GITATTRIBUTES_MARKER_BEGIN" "$target"; then
      info "[DRY-RUN] spec repo: refresh NTAPP block trong .gitattributes"
    else
      info "[DRY-RUN] spec repo: add NTAPP block vào .gitattributes"
    fi
    return 0
  fi

  if upsert_marker_block "$target" \
       "$GITATTRIBUTES_MARKER_BEGIN" "$GITATTRIBUTES_MARKER_END" "$body"; then
    success "spec repo: .gitattributes NTAPP block written"
    info "  → Cây làm việc đã có CRLF từ trước? Chạy: git add --renormalize ."
  else
    info "spec repo: .gitattributes đã đúng → skip"
  fi
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Con trỏ tri thức liên-tool (AGENTS.md / GEMINI.md + import CLAUDE.md)
# ═══════════════════════════════════════════════════════════════════
# Claude Code đọc CLAUDE.md, Codex đọc AGENTS.md, Antigravity/Gemini đọc
# GEMINI.md — gần như không chia sẻ bề mặt chỉ dẫn nào. Nguyên tắc: nội dung
# THẬT nằm đúng MỘT chỗ (<output_folder>/.okf/index.md), ba file kia chỉ là
# con trỏ ngắn. Chép hướng dẫn vào bốn file là đúng cách repo này đã phân kỳ
# một lần rồi, và CLAUDE.md vốn đã ~8k token nạp vào MỌI phiên.
# Cùng tiền lệ với setup_rule_imports: chèn dòng import vào CLAUDE.md.
OKF_POINTER_MARKER_BEGIN="<!-- >>> NTAPP OKF pointer (auto-managed, do not edit) >>>"
OKF_POINTER_MARKER_END="<!-- <<< NTAPP OKF pointer <<< -->"
OKF_IMPORT_MARKER_BEGIN="<!-- >>> NTAPP OKF index import (auto-managed, do not edit) >>>"
OKF_IMPORT_MARKER_END="<!-- <<< NTAPP OKF index import <<< -->"

# Con trỏ KHÔNG hardcode tên project hay đường dẫn tuyệt đối: <PROJECT_NAME>
# thay bằng tên đã resolve, còn vị trí bundle thì file tự dặn cách suy ra
# (spec repo: output_folder; code repo: qua spec_repo_root trong .bmm-config.yaml).
render_okf_pointer() {
  sed -e "s|<PROJECT_NAME>|${RESOLVED_PROJECT_NAME:-project}|g" "$1"
}

render_okf_import_block() {
  echo "## Tri thức dự án (OKF)"
  echo ""
  echo "Con trỏ điều hướng tri thức nằm ở \`AGENTS.md\` cạnh file này (import bên dưới); nó trỏ tiếp tới \`<output_folder>/.okf/index.md\` — chỉ dẫn THẬT chỉ nằm ở đó. Node card là **chỉ mục truy hồi, KHÔNG BAO GIỜ là nguồn để viết** (Iron Rules R1/R2). Bundle cũ / chưa có → chạy \`/NTAPP-okf-refresh\`."
  echo ""
  echo "@AGENTS.md"
}

setup_okf_pointers() {
  heading "OKF pointer (AGENTS.md / GEMINI.md)"

  if [[ ! -f "$AGENTS_MD_TEMPLATE" ]] || [[ ! -f "$GEMINI_MD_TEMPLATE" ]]; then
    warn "Thiếu template AGENTS.md / GEMINI.md trong $SCRIPT_DIR/templates → skip"
    return 0
  fi

  local repos=("$SPEC_REPO_ROOT")
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do repos+=("$repo"); done

  for repo in "${repos[@]}"; do
    local repo_name
    repo_name=$(basename "$repo")

    if [[ "$DRY_RUN" == "1" ]]; then
      info "[DRY-RUN] $repo_name: AGENTS.md + GEMINI.md pointer, @AGENTS.md import vào CLAUDE.md"
      continue
    fi

    local agents_body gemini_body import_body
    agents_body="$(render_okf_pointer "$AGENTS_MD_TEMPLATE")"
    gemini_body="$(render_okf_pointer "$GEMINI_MD_TEMPLATE")"
    import_body="$(render_okf_import_block)"

    if upsert_marker_block "$repo/AGENTS.md" \
         "$OKF_POINTER_MARKER_BEGIN" "$OKF_POINTER_MARKER_END" "$agents_body"; then
      success "$repo_name: AGENTS.md pointer written"
    else
      info "$repo_name: AGENTS.md đã đúng → skip"
    fi

    if upsert_marker_block "$repo/GEMINI.md" \
         "$OKF_POINTER_MARKER_BEGIN" "$OKF_POINTER_MARKER_END" "$gemini_body"; then
      success "$repo_name: GEMINI.md pointer written"
    else
      info "$repo_name: GEMINI.md đã đúng → skip"
    fi

    if [[ ! -f "$repo/CLAUDE.md" ]]; then
      info "$repo_name: chưa có CLAUDE.md → bỏ qua import (AGENTS.md/GEMINI.md vẫn đọc trực tiếp được)"
      continue
    fi
    if upsert_marker_block "$repo/CLAUDE.md" \
         "$OKF_IMPORT_MARKER_BEGIN" "$OKF_IMPORT_MARKER_END" "$import_body"; then
      success "$repo_name: @AGENTS.md import chèn vào CLAUDE.md"
    else
      info "$repo_name: CLAUDE.md OKF import đã đúng → skip"
    fi
  done
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Install pre-commit hook trong mọi repos
# ═══════════════════════════════════════════════════════════════════
install_hooks() {
  heading "Install pre-commit hooks"

  local hook_targets=("$SPEC_REPO_ROOT")
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    hook_targets+=("$repo")
  done

  for target in "${hook_targets[@]}"; do
    local repo_name
    repo_name=$(basename "$target")
    local hook_dir="$target/.git/hooks"
    local hook_path="$hook_dir/pre-commit"

    if [[ ! -d "$hook_dir" ]]; then
      warn "$repo_name: chưa init git, skip hook"
      continue
    fi

    if [[ -f "$hook_path" ]]; then
      backup_file "$hook_path"
    fi

    run "cp \"$HOOK_TEMPLATE\" \"$hook_path\""
    run "chmod +x \"$hook_path\""
    success "$repo_name: pre-commit installed"
  done
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Wire Claude Code EVENT hooks (UserPromptSubmit / PostToolUse / SubagentStop)
# ═══════════════════════════════════════════════════════════════════
# Khác install_hooks() (git pre-commit). Đây là event hook của Claude Code:
#   1. Symlink hooks/ → .claude/hooks/ (relative, machine-local, gitignored)
#   2. Merge block `hooks` từ manifest vào .claude/settings.json (committed)
# Hook KHÔNG merge giữa settings.json ↔ settings.local.json → block `hooks`
# PHẢI ở settings.json (committed). Re-run ghi đè trọn block → tự nhặt hook mới.
link_event_hooks() {
  heading "Wire Claude Code event hooks"

  if [[ ! -f "$HOOK_SETTINGS_TEMPLATE" ]]; then
    warn "Manifest $HOOK_SETTINGS_TEMPLATE không tồn tại → skip event hook wiring"
    return 0
  fi

  # Hooks source repo: meta repo nếu có hooks/, else spec repo (cùng nguồn với skill)
  local hooks_source
  if [[ -n "$DETECTED_META_REPO" ]] && [[ -d "$DETECTED_META_REPO/hooks" ]]; then
    hooks_source="$DETECTED_META_REPO/hooks"
  else
    hooks_source="$SPEC_REPO_ROOT/hooks"
  fi
  if [[ ! -d "$hooks_source" ]]; then
    warn "Hooks source $hooks_source không tồn tại → skip"
    return 0
  fi
  info "Hooks source: $hooks_source"

  local targets=("$SPEC_REPO_ROOT")
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do targets+=("$repo"); done

  for target in "${targets[@]}"; do
    local repo_name
    repo_name=$(basename "$target")
    local claude_dir="$target/.claude"
    local link="$claude_dir/hooks"
    local settings="$claude_dir/settings.json"

    run "mkdir -p \"$claude_dir\""

    # 1) Symlink hooks/ → .claude/hooks (relative path → portable qua git clone)
    local rel_source
    rel_source=$(relpath "$hooks_source" "$claude_dir" "$hooks_source")

    if [[ -L "$link" ]]; then
      local cur; cur=$(readlink "$link")
      if [[ "$cur" != "$rel_source" ]] && [[ "$cur" != "$hooks_source" ]]; then
        warn "$repo_name: .claude/hooks trỏ sai đích, fix lại"
        run "rm \"$link\""
        run "ln -sf \"$rel_source\" \"$link\""
      else
        info "$repo_name: .claude/hooks symlink OK"
      fi
    elif [[ -d "$link" ]]; then
      warn "$repo_name: .claude/hooks là folder thật (không phải symlink) — skip để tránh data loss"
    else
      run "ln -sf \"$rel_source\" \"$link\""
      success "$repo_name: .claude/hooks → $rel_source"
    fi

    # exec bit cho hook script (follows symlink)
    run "chmod +x \"$hooks_source\"/*.sh \"$hooks_source\"/*.py 2>/dev/null || true"

    # 2) Merge block `hooks` vào .claude/settings.json (giữ enabledPlugins/permissions)
    if [[ "$DRY_RUN" == "1" ]]; then
      info "[DRY-RUN] $repo_name: merge hooks block vào .claude/settings.json"
      continue
    fi
    [[ -f "$settings" ]] && backup_file "$settings"
    if [[ -z "$PYTHON_BIN" ]]; then
      error "$repo_name: không có Python (python3/python/py) trên PATH → không merge được settings.json, event hook sẽ không fire. Cài Python rồi chạy lại '--refresh'."
      continue
    fi
    if $PYTHON_BIN - "$settings" "$HOOK_SETTINGS_TEMPLATE" <<'PY'
import json, os, sys
settings_path, manifest_path = sys.argv[1], sys.argv[2]
with open(manifest_path, encoding="utf-8") as f:
    manifest = json.load(f)
data = {}
if os.path.exists(settings_path):
    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
data["hooks"] = manifest["hooks"]
with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
    then
      success "$repo_name: hooks block merged vào settings.json"
    else
      error "$repo_name: merge settings.json THẤT BẠI (python3?) — hook sẽ không fire"
    fi
  done

  warn "Nhắc: ĐỪNG đặt block 'hooks' vào .claude/settings.local.json — local thay thế hoàn toàn project, sẽ xoá sạch hook."
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Self-test
# ═══════════════════════════════════════════════════════════════════
self_test() {
  heading "Self-test"

  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Skip self-test"
    return 0
  fi

  local errors=0

  # Test 1: CLAUDE.md không còn placeholder VÀ không còn mang tên base template
  local st_name
  st_name=$(read_project_name)
  if grep -q "<PROJECT_NAME>" "$SPEC_REPO_ROOT/CLAUDE.md"; then
    warn "CLAUDE.md vẫn còn <PROJECT_NAME>"
    errors=$((errors + 1))
  elif is_template_project_name "$st_name" && ! is_base_template_repo; then
    warn "CLAUDE.md project name vẫn là tên base template: '${st_name:-<rỗng>}' — chạy lại full mode với PROJECT_NAME=\"<tên>\""
    errors=$((errors + 1))
  else
    success "CLAUDE.md: project name set ('$st_name')"
  fi

  # Test 2: Workspace JSON valid (nếu có)
  local workspace_file=""
  if [[ -n "$DETECTED_META_REPO" ]]; then
    workspace_file="$DETECTED_META_REPO/workspaces/${RESOLVED_PROJECT_NAME:-project}.code-workspace"
  elif [[ ${#DETECTED_CODE_REPOS[@]} -gt 0 ]]; then
    workspace_file="$SPEC_REPO_ROOT/${RESOLVED_PROJECT_NAME:-project}.code-workspace"
  fi

  if [[ -n "$workspace_file" ]] && [[ -f "$workspace_file" ]]; then
    if [[ -n "$PYTHON_BIN" ]]; then
      if $PYTHON_BIN -c "import json,sys; json.load(open(sys.argv[1]))" "$workspace_file" 2>/dev/null; then
        success "Workspace JSON: valid"
      else
        error "Workspace JSON: invalid syntax"
        errors=$((errors + 1))
      fi
    else
      info "Workspace JSON: skip validation (không có Python)"
    fi
  fi

  # Test 3: Pre-commit hook executable trong mọi repo
  local hook_targets=("$SPEC_REPO_ROOT")
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    hook_targets+=("$repo")
  done

  for target in "${hook_targets[@]}"; do
    local hook="$target/.git/hooks/pre-commit"
    if [[ -x "$hook" ]]; then
      success "$(basename "$target"): hook executable"
    elif [[ -d "$target/.git" ]]; then
      error "$(basename "$target"): hook không executable"
      errors=$((errors + 1))
    fi
  done

  # Test 4: Skill symlinks
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    local target="$repo/.agent/skills"
    if [[ -L "$target" ]] && [[ -d "$target" ]]; then
      success "$(basename "$repo"): skill symlink resolved"
    elif [[ ${#DETECTED_CODE_REPOS[@]} -gt 0 ]]; then
      warn "$(basename "$repo"): skill symlink missing/broken"
    fi
  done

  # Test 5: Code repo configs
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    local config="$repo/.bmm-config.yaml"
    if [[ -f "$config" ]]; then
      success "$(basename "$repo"): .bmm-config.yaml OK"
    fi
  done

  echo ""
  if [[ "$errors" -gt 0 ]]; then
    error "Self-test FAIL: $errors issues"
    return 1
  fi
  success "Self-test PASS"
}

# ═══════════════════════════════════════════════════════════════════
# V3: Skill auto-reload — pre-populate IDE skill caches
# ═══════════════════════════════════════════════════════════════════
# Claude Code reads từ .claude/skills/, Cursor từ .cursor/skills/.
# Bootstrap pre-populates các cache này từ .agent/skills/ để dev không
# phải gõ "duplicate skill X" trong chat.
reload_ide_skills() {
  heading "Reload IDE skill caches"

  # Skill source: meta repo nếu có, else spec repo
  local skill_source
  if [[ -n "$DETECTED_META_REPO" ]] && [[ -d "$DETECTED_META_REPO/.agent/skills" ]]; then
    skill_source="$DETECTED_META_REPO/.agent/skills"
  else
    skill_source="$SPEC_REPO_ROOT/.agent/skills"
  fi

  if [[ ! -d "$skill_source" ]]; then
    warn "Skill source không tồn tại: $skill_source — skip"
    return 0
  fi

  # Target repos: spec + tất cả code
  local targets=("$SPEC_REPO_ROOT")
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    targets+=("$repo")
  done

  for target in "${targets[@]}"; do
    local repo_name
    repo_name="$(basename "$target")"

    # Pre-populate .claude/skills/
    local claude_dir="$target/.claude/skills"
    if [[ "$DRY_RUN" == "0" ]]; then
      mkdir -p "$claude_dir"
      # rsync để keep state minimal, exclude .DS_Store
      rsync -a --delete --exclude='.DS_Store' "$skill_source/" "$claude_dir/" 2>/dev/null || cp -R "$skill_source/." "$claude_dir/"
    else
      info "[DRY-RUN] Would rsync skills → $claude_dir"
    fi

    # Pre-populate .cursor/skills/
    local cursor_dir="$target/.cursor/skills"
    if [[ "$DRY_RUN" == "0" ]]; then
      mkdir -p "$cursor_dir"
      rsync -a --delete --exclude='.DS_Store' "$skill_source/" "$cursor_dir/" 2>/dev/null || cp -R "$skill_source/." "$cursor_dir/"
    else
      info "[DRY-RUN] Would rsync skills → $cursor_dir"
    fi

    local skill_count
    skill_count=$(find "$skill_source" -maxdepth 1 -type d | wc -l | tr -d ' ')
    skill_count=$((skill_count - 1))  # subtract root dir itself
    success "$repo_name: $skill_count skills → .claude/ + .cursor/"
  done
}

# ═══════════════════════════════════════════════════════════════════
# V3: Self-test hook end-to-end — run hook với dummy bad file
# ═══════════════════════════════════════════════════════════════════
self_test_hook_e2e() {
  heading "Self-test hook (end-to-end)"

  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Skip e2e test"
    return 0
  fi

  local errors=0
  local targets=("$SPEC_REPO_ROOT")
  for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
    targets+=("$repo")
  done

  for target in "${targets[@]}"; do
    local repo_name
    repo_name="$(basename "$target")"
    local hook="$target/.git/hooks/pre-commit"

    if [[ ! -x "$hook" ]]; then
      continue
    fi

    # Tạo dummy file thiếu header trong subfolder tmp
    local test_file="$target/__bootstrap_test_$$.ts"
    echo 'console.log("hook test");' > "$test_file"

    # Stage file
    (cd "$target" && git add "$test_file" 2>/dev/null) || {
      rm -f "$test_file"
      continue
    }

    # Run hook trực tiếp (không trigger commit thực sự)
    local hook_output
    local hook_exit
    hook_output=$(cd "$target" && bash "$hook" 2>&1) || hook_exit=$?
    hook_exit=${hook_exit:-0}

    # Unstage + xóa test file
    (cd "$target" && git reset HEAD "$test_file" > /dev/null 2>&1) || true
    rm -f "$test_file"

    # Verify hook chặn (exit code != 0)
    if [[ "$hook_exit" -ne 0 ]] && echo "$hook_output" | grep -q "Rule 1"; then
      success "$repo_name: hook chặn dummy file thiếu header (PASS)"
    else
      error "$repo_name: hook KHÔNG chặn dummy file (exit=$hook_exit)"
      errors=$((errors + 1))
    fi
  done

  if [[ "$errors" -gt 0 ]]; then
    warn "Self-test hook e2e: $errors repo(s) hook không hoạt động đúng"
    return 1
  fi
}

# ═══════════════════════════════════════════════════════════════════
# STEP: Final report
# ═══════════════════════════════════════════════════════════════════
self_test_event_hooks() {
  heading "Self-test event hooks (registration)"

  if [[ "$DRY_RUN" == "1" ]]; then
    info "[DRY-RUN] Skip event-hook self-test"
    return 0
  fi

  local errors=0
  local target="$SPEC_REPO_ROOT"
  local repo_name; repo_name="$(basename "$target")"
  local settings="$target/.claude/settings.json"
  local gate="$target/.claude/hooks/approval_gate.sh"

  # 1) settings.json có block hooks
  if [[ -n "$PYTHON_BIN" ]] && $PYTHON_BIN -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('hooks') else 1)" "$settings" 2>/dev/null; then
    success "$repo_name: settings.json có block 'hooks'"
  else
    error "$repo_name: settings.json THIẾU block 'hooks' → event hook không fire"
    errors=$((errors + 1))
  fi

  # 2) symlink .claude/hooks resolve + hook executable
  if [[ -x "$gate" ]]; then
    success "$repo_name: .claude/hooks/approval_gate.sh resolve + executable"
  else
    error "$repo_name: .claude/hooks/approval_gate.sh không resolve/exec (symlink hỏng?)"
    errors=$((errors + 1))
  fi

  # 3) Hook chạy được + block đúng (trigger Stage 2 khi gate file chưa approved → exit 2)
  if [[ -x "$gate" ]]; then
    local out exit_code=0
    out=$(echo '{"prompt":"/ntapp-architecture-design"}' | (cd "$target" && bash "$gate") 2>&1) || exit_code=$?
    if [[ "$exit_code" == "2" ]]; then
      success "$repo_name: approval_gate chặn Stage 2 khi PRD/Epics chưa approved (exit 2)"
    elif [[ "$exit_code" == "0" ]]; then
      info "$repo_name: approval_gate pass (PRD/Epics đã approved hoặc chưa có trigger) — runnable OK"
    else
      error "$repo_name: approval_gate exit bất thường ($exit_code) — không phải 0/2"
      errors=$((errors + 1))
    fi
  fi

  if [[ "$errors" -gt 0 ]]; then
    warn "Self-test event hooks: $errors lỗi — kiểm tra link_event_hooks output ở trên"
    return 1
  fi
  success "Event hooks wired đúng. (Lưu ý: SubagentStop chỉ fire cho Task-subagent;"
  warn "  nếu skill /ntapp-* chạy ở main loop, smoke-test thật để xác nhận — fallback: đổi event sang 'Stop'.)"
}

final_report() {
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  printf "  ${GREEN}${BOLD}Setup DONE${NC}\n"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""

  info "Project: ${RESOLVED_PROJECT_NAME:-<unchanged>}"
  info "Spec repo: $SPEC_REPO_ROOT"
  if [[ -n "$DETECTED_META_REPO" ]]; then
    info "Meta repo: $DETECTED_META_REPO"
  fi
  if [[ ${#DETECTED_CODE_REPOS[@]} -gt 0 ]]; then
    info "Code repos:"
    for repo in ${DETECTED_CODE_REPOS[@]+"${DETECTED_CODE_REPOS[@]}"}; do
      echo "         - $(basename "$repo")"
    done
  fi

  echo ""
  info "Bước tiếp theo:"
  if [[ ${#DETECTED_CODE_REPOS[@]} -gt 0 ]] || [[ -n "$DETECTED_META_REPO" ]]; then
    local workspace_file
    if [[ -n "$DETECTED_META_REPO" ]]; then
      workspace_file="$DETECTED_META_REPO/workspaces/${RESOLVED_PROJECT_NAME:-project}.code-workspace"
    else
      workspace_file="$SPEC_REPO_ROOT/${RESOLVED_PROJECT_NAME:-project}.code-workspace"
    fi
    echo "  1. Mở workspace:"
    echo "       code \"$workspace_file\""
  else
    echo "  1. Mở IDE ở folder spec repo: code \"$SPEC_REPO_ROOT\""
  fi
  echo "  2. Gõ '/' trong chat IDE — verify command '/ntapp-', '/bmad-', '/superpowers:'"
  echo "  3. Đọc docs/Process/Manual_phase_1.md mục 1-7"
  echo "  4. Bắt đầu Stage 1: gõ '/bmad-create-prd'"
  echo ""

  if [[ ${#DETECTED_CODE_REPOS[@]} -gt 0 ]]; then
    info "Code repos đã setup:"
    local k=0
    while [[ $k -lt ${#DETECTED_CODE_REPOS[@]} ]]; do
      local repo="${DETECTED_CODE_REPOS[$k]}"
      local scope_str=""
      if [[ ${#DETECTED_REPO_SCOPES[@]} -gt $k ]]; then
        scope_str=" (scope: ${DETECTED_REPO_SCOPES[$k]})"
      fi
      echo "  - $(basename "$repo")$scope_str"
      echo "      .bmm-config.yaml: ✓"
      echo "      .agent/skills/  : symlinked"
      echo "      .git/hooks/     : pre-commit installed"
      if [[ -n "$scope_str" ]]; then
        echo "      CLAUDE.md       : scope block"
      fi
      k=$((k + 1))
    done
    echo ""
  fi
}

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --refresh) MODE="refresh"; shift ;;
      --upgrade) MODE="upgrade"; shift ;;
      --dry-run) DRY_RUN=1; shift ;;
      --help|-h) show_help; exit 0 ;;
      *) error "Unknown flag: $1"; show_help; exit 1 ;;
    esac
  done

  echo "═══════════════════════════════════════════════════════════════"
  printf "  ${BOLD}NTAPP Phase 1 — Project Bootstrap (V3)${NC}\n"
  printf "  Mode: ${MODE}"
  if [[ "$DRY_RUN" == "1" ]]; then printf " ${YELLOW}[DRY-RUN]${NC}"; fi
  if [[ "$AUTO_CONFIRM" == "1" ]]; then printf " ${YELLOW}[AUTO-CONFIRM]${NC}"; fi
  echo ""
  echo "═══════════════════════════════════════════════════════════════"

  check_prerequisites
  detect_repos
  confirm_scope

  case "$MODE" in
    full)
      setup_project_name
      generate_workspace
      generate_spec_repo_config
      generate_code_repo_configs
      link_skills
      setup_gitignore
      setup_gitattributes
      setup_repo_scopes
      setup_rule_imports
      setup_okf_pointers
      ;;
    upgrade)
      # Like full but skip project name prompt (đã set rồi).
      # Read project name from CLAUDE.md để downstream steps (generate_workspace) có RESOLVED_PROJECT_NAME.
      local existing_name
      existing_name=$(read_project_name)
      if is_template_project_name "$existing_name" && ! is_base_template_repo; then
        error "Upgrade mode yêu cầu CLAUDE.md đã có project name THẬT (hiện: '${existing_name:-<rỗng>}' — placeholder hoặc tên base template)."
        error "Chạy full mode ('./scripts/bootstrap.sh') để set project name lần đầu."
        exit 1
      fi
      export RESOLVED_PROJECT_NAME="$existing_name"
      info "Upgrade mode — project name: '$existing_name' (giữ nguyên). Re-run workspace + configs + symlinks + gitignore + gitattributes + repo scope + rule imports + OKF pointer"
      generate_workspace
      generate_spec_repo_config
      generate_code_repo_configs
      link_skills
      setup_gitignore
      setup_gitattributes
      setup_repo_scopes
      setup_rule_imports
      setup_okf_pointers
      ;;
    refresh)
      # Machine-local artifacts: code repo .bmm-config.yaml (gitignored — Phase 1.6),
      # skill symlinks (gitignored — Phase 1.5), hooks (.git/hooks), IDE skill cache.
      # KHÔNG đụng workspace / .gitignore / spec repo configs (đã commit từ project lead).
      # KHÔNG đụng repo scope (committed trong code repo CLAUDE.md — sticky).
      local existing_name_refresh
      existing_name_refresh=$(read_project_name)
      if [[ -n "$existing_name_refresh" ]] && [[ "$existing_name_refresh" != "<PROJECT_NAME>" ]]; then
        export RESOLVED_PROJECT_NAME="$existing_name_refresh"
      fi
      if is_template_project_name "$existing_name_refresh" && ! is_base_template_repo; then
        warn "Project name chưa set (đang là '${existing_name_refresh:-<rỗng>}' — tên base template). Refresh KHÔNG đặt tên; chạy full mode để set."
      fi
      info "Refresh mode — re-create machine-local artifacts (code repo configs + symlinks + hook + IDE cache)"
      generate_code_repo_configs
      link_skills
      ;;
  esac

  install_hooks
  link_event_hooks
  reload_ide_skills
  self_test
  self_test_hook_e2e
  self_test_event_hooks
  final_report
}

main "$@"
