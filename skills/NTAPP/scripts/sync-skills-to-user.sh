#!/usr/bin/env bash
# Setup máy cho user mới theo project này:
#   1. Đẩy toàn bộ skill trong <repo>/.agent/skills vào skill dir của từng
#      công cụ (phẳng 1 cấp) để dùng được cho mọi project:
#        - Claude Code : ~/.claude/skills
#        - Gemini      : ~/.gemini/config/skills
#        - Antigravity : ~/.codeium/skills
#      Gemini/Antigravity (agy 1.0.14) CHỈ đọc skill user ở global dir
#      ~/.gemini/config/skills/ — KHÔNG phải ~/.gemini/skills, và cũng không
#      auto-discover skill project-scope. Đường này phải khớp với
#      scripts/antigravity/install-agy-skills.sh (cùng SKILLS_DIR), nếu không
#      thì skill copy một nơi, agy đọc một nơi khác và im lặng không thấy gì.
#   2. Copy các rule file theo stack (<repo>/rules/*.md) vào ~/.claude/rules/:
#      rule FE/BE (Sonar giờ nằm trong rule BE) KHÔNG chèn vào CLAUDE.md global
#      (tránh loãng context + áp sai ngữ cảnh) — từng code repo import qua dòng
#      `@~/.claude/rules/<file>` do scripts/bootstrap.sh chèn (tùy repo là FE hay BE).
#   3. Dọn các block legacy đã từng nhúng thẳng vào ~/.claude/CLAUDE.md global
#      (baseline Sonar cũ + FE cũ) — giờ mọi rule đều sống ở ~/.claude/rules/ và
#      import per-repo, KHÔNG còn rule mặc định cho all trong CLAUDE.md global.
#
# Skill copy phẳng vào ~/.claude/skills/<tên-skill>/ đúng chuẩn Claude quét (1 cấp).
# Manifest ~/.claude/skills/.vds-skills-manifest ghi lại skill do chính script này
# tạo, để bước dọn stale chỉ đụng đúng những skill đó, không xoá skill cá nhân.
#
# Dọn skill stale LUÔN chạy, không cần cờ. Lý do: manifest bị ghi đè ở cuối mỗi
# lần chạy bất kể cờ nào, nên nếu để dọn stale sau một cờ opt-in thì chỉ cần một
# lần chạy thường là mất dấu vết skill đã bỏ khỏi nguồn, và lần chạy có cờ sau đó
# không còn gì để đối chiếu — skill đã khai tử nằm lại vĩnh viễn trong máy user.
#
# Usage:
#   ./scripts/sync-skills-to-user.sh            # copy skill + dọn stale + copy rule files
#   ./scripts/sync-skills-to-user.sh --dry-run  # xem trước, không ghi
#   ./scripts/sync-skills-to-user.sh --clean    # deprecated, giữ cho tương thích lệnh cũ
#   ./scripts/sync-skills-to-user.sh --skills-only   # chỉ copy skill, bỏ qua rule
#   ./scripts/sync-skills-to-user.sh --rules-only    # chỉ xử lý rule, bỏ qua skill
set -euo pipefail

DRY_RUN=0
CLEAN=0
DO_SKILLS=1
DO_RULES=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=1 ;;
    --clean)      CLEAN=1 ;;
    --skills-only) DO_RULES=0 ;;
    --rules-only)  DO_SKILLS=0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
if [[ $CLEAN -eq 1 ]]; then
  echo "(--clean đã là mặc định — cờ này chỉ còn giữ cho tương thích, không cần truyền)"
fi

# Repo root = thư mục cha của scripts/ (portable, không hardcode path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$REPO_ROOT/.agent/skills"
# Danh sách skill dir đích theo từng công cụ. Mỗi dòng: "<tên> <path>".
SKILL_DESTS=(
  "Claude:$HOME/.claude/skills"
  "Gemini:$HOME/.gemini/config/skills"
  "Antigravity:$HOME/.codeium/skills"
)
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
RULES_SRC="$REPO_ROOT/rules"
RULES_DEST="$HOME/.claude/rules"

# Marker các block legacy từng nhúng thẳng vào ~/.claude/CLAUDE.md global — chỉ
# giữ để gỡ block cũ. Mọi rule (kể cả Sonar) giờ sống ở ~/.claude/rules/ +
# import per-repo, KHÔNG còn rule mặc định cho all trong CLAUDE.md global.
BEGIN_MARKER="<!-- >>> VDS baseline rules (managed by sync-skills-to-user.sh) — do not edit inside >>> -->"
END_MARKER="<!-- <<< VDS baseline rules <<< -->"
FE_BEGIN_MARKER="<!-- >>> VDS FE rules (managed by sync-skills-to-user.sh) — do not edit inside >>> -->"
FE_END_MARKER="<!-- <<< VDS FE rules <<< -->"


# sync_skills <label> <dest>
# Copy toàn bộ skill vào <dest> (phẳng 1 cấp), manifest riêng theo từng đích.
sync_skills() {
  local label="$1" DEST="$2"
  local MANIFEST="$DEST/.vds-skills-manifest"
  [[ -d "$SRC" ]] || { echo "Không tìm thấy skill source: $SRC" >&2; exit 1; }
  echo "== Skills ($label) =="
  echo "Nguồn : $SRC"
  echo "Đích  : $DEST"
  [[ $DRY_RUN -eq 0 ]] && mkdir -p "$DEST"

  local new_manifest="" count=0 skipped=0
  for dir in "$SRC"/*/; do
    local name; name="$(basename "$dir")"
    if [[ ! -f "$dir/SKILL.md" ]]; then
      echo "  skip (không có SKILL.md): $name"
      skipped=$((skipped + 1))
      continue
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "  would copy: $name"
    else
      rm -rf "$DEST/$name"
      cp -R "$dir" "$DEST/$name"
    fi
    new_manifest+="$name"$'\n'
    count=$((count + 1))
  done

  # Dọn skill đã bị bỏ khỏi nguồn — chạy vô điều kiện, TRƯỚC khi ghi manifest mới.
  # Đối chiếu manifest cũ nên chỉ đụng skill do chính script này tạo; skill cá nhân
  # user tự bỏ vào thư mục đích không nằm trong manifest nên không bị xoá.
  local removed=0
  if [[ -f "$MANIFEST" ]]; then
    while IFS= read -r name; do
      [[ -z "$name" ]] && continue
      if [[ ! -d "$SRC/$name" && -d "$DEST/$name" ]]; then
        if [[ $DRY_RUN -eq 1 ]]; then
          echo "  would remove (stale): $name"
        else
          rm -rf "$DEST/$name"
          echo "  removed (stale): $name"
        fi
        removed=$((removed + 1))
      fi
    done < "$MANIFEST"
  fi

  [[ $DRY_RUN -eq 0 ]] && printf '%s' "$new_manifest" > "$MANIFEST"
  echo "  → $count skill${skipped:+, $skipped skipped}${removed:+, $removed stale removed}."
}

# remove_block <begin_marker> <end_marker> <label>
# Gỡ block giữa 2 marker khỏi CLAUDE.md global (dọn block legacy), không chèn lại.
remove_block() {
  local begin="$1" end="$2" label="$3"
  [[ -f "$CLAUDE_MD" ]] || return 0
  grep -qF "$begin" "$CLAUDE_MD" || return 0

  local tmp; tmp="$(mktemp)"
  awk -v b="$begin" -v e="$end" '
    $0==b {if (n>0 && a[n] ~ /^[[:space:]]*$/) n--; skip=1; next}
    $0==e {skip=0; next}
    skip==0 {a[++n]=$0}
    END {last=0; for(i=1;i<=n;i++) if(a[i] ~ /[^[:space:]]/) last=i; for(i=1;i<=last;i++) print a[i]}
  ' "$CLAUDE_MD" > "$tmp"
  mv "$tmp" "$CLAUDE_MD"
  echo "  → removed legacy block: $label"
}

# Dọn các block rule legacy khỏi CLAUDE.md global — Sonar giờ nằm trong rule BE
# (~/.claude/rules/be-finance-rules.md), FE nằm ở rule FE; cả hai import per-repo,
# KHÔNG còn rule mặc định cho all trong CLAUDE.md global.
cleanup_legacy_global_rules() {
  echo "== Dọn rule legacy trong CLAUDE.md global =="
  echo "Đích  : $CLAUDE_MD"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  would remove legacy block (nếu có): baseline (Sonar) — đã chuyển sang rule BE"
    echo "  would remove legacy block (nếu có): FE (Angular) — đã chuyển sang rule FE"
    return
  fi

  remove_block "$BEGIN_MARKER" "$END_MARKER" "baseline (Sonar) — đã chuyển sang ~/.claude/rules/be-finance-rules.md"
  remove_block "$FE_BEGIN_MARKER" "$FE_END_MARKER" "FE (Angular) — đã chuyển sang ~/.claude/rules/ + import per-repo"
}

# Copy rule files theo stack vào ~/.claude/rules/ — code repo import qua
# dòng `@~/.claude/rules/<file>` trong CLAUDE.md (do bootstrap.sh chèn).
sync_rule_files() {
  echo "== Rule files vào ~/.claude/rules =="
  if [[ ! -d "$RULES_SRC" ]]; then
    echo "  skip: không tìm thấy rule source $RULES_SRC"
    return
  fi
  echo "Nguồn : $RULES_SRC"
  echo "Đích  : $RULES_DEST"

  local count=0
  for f in "$RULES_SRC"/*.md; do
    [[ -e "$f" ]] || continue
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "  would copy: $(basename "$f")"
    else
      mkdir -p "$RULES_DEST"
      cp -f "$f" "$RULES_DEST/"
      echo "  copied: $(basename "$f")"
    fi
    count=$((count + 1))
  done
  echo "  → $count rule file(s)."
}

[[ $DRY_RUN -eq 1 ]] && echo "(DRY-RUN — không ghi gì)"
if [[ $DO_SKILLS -eq 1 ]]; then
  for entry in "${SKILL_DESTS[@]}"; do
    sync_skills "${entry%%:*}" "${entry#*:}"
  done
fi
if [[ $DO_RULES -eq 1 ]]; then
  cleanup_legacy_global_rules
  sync_rule_files
fi
echo "Xong."
