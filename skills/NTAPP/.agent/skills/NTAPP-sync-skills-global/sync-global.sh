#!/usr/bin/env bash
# Đồng bộ skill NTAPP + rule coding mới nhất (nhánh main, Bitbucket) ra global
# (~/.claude/skills, ~/.gemini/config/skills, ~/.codeium/skills, ~/.claude/rules)
# mà KHÔNG cần giữ một bản clone thường trực của repo template trên máy.
#
# Cơ chế: clone tạm (--depth 1) vào thư mục temp, chạy nguyên
# scripts/sync-skills-to-user.sh của repo template ngay trong đó, rồi xóa temp.
# Script gốc tự tính REPO_ROOT từ vị trí chính nó nên chạy từ temp dir vẫn đúng.
#
# Usage: sync-global.sh [--dry-run] [--clean] [--skills-only] [--rules-only]
#   (args được forward nguyên cho scripts/sync-skills-to-user.sh)
set -euo pipefail

REPO_URL="http://bitbucket.digital.vn/scm/platform/ntapp-vsaf-blended-template.git"
BRANCH="main"

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "== Clone tạm nhánh $BRANCH từ $REPO_URL =="
git clone --depth 1 --branch "$BRANCH" --single-branch "$REPO_URL" "$TMP_DIR"

SYNC_SCRIPT="$TMP_DIR/scripts/sync-skills-to-user.sh"
if [[ ! -f "$SYNC_SCRIPT" ]]; then
  echo "Không tìm thấy $SYNC_SCRIPT trong repo template (có thể đã đổi tên/đường dẫn)." >&2
  exit 1
fi

echo "== Chạy sync-skills-to-user.sh =="
bash "$SYNC_SCRIPT" "$@"
