#!/usr/bin/env bash
# Đẩy bản NTAPP đang sửa trong modify-vsaf sang một spec repo để thử, và ghi lại
# đúng phiên bản nào đã được đẩy — để số đo sau này biết nó đo bản skill nào.
#
#   scripts/dev-deploy.sh <spec-repo>            cập nhật spec repo đã có (mặc định)
#   scripts/dev-deploy.sh <spec-repo> --new      dựng spec repo mới (apply-pack + bootstrap)
#
# Tuỳ chọn:
#   --new            dựng lần đầu. Cần PROJECT_NAME (mặc định: tên thư mục bỏ -spec)
#   --skip-skills    không sync skill ra ~/.claude/skills (và Gemini/Antigravity)
#   --rewire         sau khi cập nhật, chạy lại scripts/bootstrap.sh --refresh trong spec repo
#   --dry-run        in ra sẽ làm gì, không ghi gì
#
# Vì sao không dùng `vsaf apply-pack` cho cả cập nhật: không --force thì nó chỉ copy
# file CHƯA có (sửa trong pack không tới project), có --force thì đè cả CLAUDE.md đã
# điền tên project và README.md của project. Chế độ cập nhật ở đây chỉ đồng bộ phần
# thuộc về pack, và giữ nguyên phần thuộc về project:
#   đồng bộ : .vsaf/workflows/<pack-flow>/ (xoá file pack đã bỏ), .vsaf/commands/,
#             hooks/, scripts/, rules/, docs/Process/, _bmad/ (trừ config.yaml),
#             CLAUDE.md (giữ dòng tiêu đề + khối OKF auto-managed của project)
#   giữ     : NTAPP-output/, README.md, .bmm-config.yaml, _bmad/**/config.yaml,
#             .vsaf/config.yaml, workflow/command riêng của project
#
# Skill KHÔNG nằm trong project: nó sống ở ~/.claude/skills, dùng chung mọi project.
# Nên lịch sử deploy được ghi ở hai nơi:
#   <spec-repo>/.vsaf/dev-deploy.json           bản đang có trong project này
#   ~/.local/state/vsaf-dev/deploys.jsonl       mọi lần deploy — skill global đổi theo nó
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACK="$ROOT/skills/NTAPP"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/vsaf-dev"

MODE=update SKIP_SKILLS=0 REWIRE=0 DRY=0 SPEC=""
for arg in "$@"; do
  case "$arg" in
    --new) MODE=new ;;
    --skip-skills) SKIP_SKILLS=1 ;;
    --rewire) REWIRE=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "Không hiểu tuỳ chọn: $arg" >&2; exit 2 ;;
    *) [[ -z "$SPEC" ]] || { echo "Chỉ nhận một spec repo" >&2; exit 2; }; SPEC="$arg" ;;
  esac
done
[[ -n "$SPEC" ]] || { echo "Thiếu đường dẫn spec repo. Xem --help." >&2; exit 2; }

say()  { printf '\033[1m▸ %s\033[0m\n' "$*"; }
warn() { printf '\033[0;33m⚠ %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[0;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
run()  { if (( DRY )); then echo "  [dry-run] $*"; else "$@"; fi; }

# ── Preflight ──────────────────────────────────────────────────────────────────
[[ -f "$PACK/pack.yaml" ]] || die "Không thấy $PACK/pack.yaml"

linked="$(readlink -f "$(command -v vsaf 2>/dev/null)" 2>/dev/null || true)"
if [[ "$linked" != "$ROOT/"* ]]; then
  warn "Lệnh vsaf đang trỏ tới '${linked:-không có}', không phải repo này — engine chạy KHÔNG phải bản đang sửa."
  warn "Chạy: (cd $ROOT && npm link)"
fi

SHA="$(git -C "$ROOT" rev-parse HEAD)"
SHORT="$(git -C "$ROOT" rev-parse --short HEAD)"
# package-lock.json là sản phẩm phụ của npm install, không phải nội dung pack.
DIRTY_FILES="$(git -C "$ROOT" status --porcelain -- . ':!package-lock.json')"
DIRTY=false
if [[ -n "$DIRTY_FILES" ]]; then
  DIRTY=true
  warn "modify-vsaf có thay đổi chưa commit — số đo sẽ không gắn được với một commit cụ thể:"
  printf '%s\n' "$DIRTY_FILES" | sed 's/^/    /' >&2
fi
# Băm nội dung skill: khi DIRTY, đây là thứ duy nhất phân biệt hai lần deploy cùng SHA.
SKILLS_HASH="$(cd "$PACK/.agent/skills" && find . -type f ! -path '*/__pycache__/*' -print0 \
  | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16)"

if [[ "$MODE" == new ]]; then
  [[ ! -e "$SPEC" || -z "$(ls -A "$SPEC" 2>/dev/null)" ]] || die "$SPEC đã có nội dung — bỏ --new để cập nhật."
else
  [[ -d "$SPEC/.git" && -d "$SPEC/NTAPP-output" ]] \
    || die "$SPEC không phải spec repo NTAPP (cần .git và NTAPP-output/). Dựng mới thì thêm --new."
fi
mkdir -p "$SPEC" 2>/dev/null || true
SPEC="$(cd "$SPEC" && pwd)"

say "modify-vsaf $SHORT$([[ $DIRTY == true ]] && echo ' (dirty)') · skills $SKILLS_HASH → $SPEC ($MODE)"

# ── 1. Project files ───────────────────────────────────────────────────────────
if [[ "$MODE" == new ]]; then
  say "Dựng project bằng vsaf apply-pack"
  name="${PROJECT_NAME:-$(basename "$SPEC" | sed -E 's/-(spec|doc)$//')}"
  if (( DRY )); then
    (cd "$SPEC" && vsaf apply-pack "$PACK" --dry-run)
  else
    (cd "$SPEC" && PROJECT_NAME="$name" AUTO_CONFIRM=1 vsaf apply-pack "$PACK")
  fi
else
  say "Đồng bộ phần thuộc pack"
  # So bằng checksum, không chép mtime: chỉ file khác NỘI DUNG mới được ghi và được in,
  # nên danh sách in ra chính là diff thật giữa pack và project.
  RS=(rsync -rlpc --itemize-changes --exclude '__pycache__/' --exclude '*.bak.*')
  (( DRY )) && RS+=(-n)
  sync_dir() {  # <path trong pack> [tuỳ chọn rsync thêm...]
    local rel="$1"; shift
    [[ -d "$PACK/$rel" ]] || return 0
    (( DRY )) || mkdir -p "$SPEC/$rel"
    "${RS[@]}" "$@" "$PACK/$rel/" "$SPEC/$rel/" | { grep -v '^\.d' || true; } | sed "s|^|  $rel/ |"
  }
  # Mỗi flow của pack là của pack trọn vẹn → --delete để file pack đã bỏ cũng đi theo.
  # Flow riêng của project nằm ở thư mục khác nên không bị đụng.
  for flow in "$PACK"/.vsaf/workflows/*/; do
    sync_dir ".vsaf/workflows/$(basename "$flow")" --delete
  done
  sync_dir .vsaf/commands
  sync_dir hooks   --exclude 'settings.json'   # packOnly
  sync_dir scripts
  sync_dir rules   --exclude 'rules.json'      # packOnly
  sync_dir docs/Process
  sync_dir _bmad   --exclude 'config.yaml'     # bootstrap ghi đường dẫn của project vào đây

  # CLAUDE.md: thân lấy từ pack; dòng tiêu đề và khối OKF là của project.
  python3 - "$PACK/CLAUDE.md" "$SPEC/CLAUDE.md" "$DRY" <<'PY'
import re, sys
pack_path, proj_path, dry = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
pack = open(pack_path, encoding="utf-8").read()
try:
    proj = open(proj_path, encoding="utf-8").read()
except FileNotFoundError:
    proj = ""
lines = pack.split("\n")
if proj.startswith("# Project:"):
    lines[0] = proj.split("\n", 1)[0]
out = "\n".join(lines)
okf = re.search(r"\n*<!-- >>> NTAPP OKF index import.*?<!-- <<< NTAPP OKF index import <<< -->\n?", proj, re.S)
if okf:
    out = out.rstrip("\n") + "\n\n" + okf.group(0).lstrip("\n")
if out == proj:
    print("  CLAUDE.md   không đổi")
elif dry:
    print("  CLAUDE.md   sẽ cập nhật")
else:
    open(proj_path, "w", encoding="utf-8").write(out)
    print("  CLAUDE.md   đã cập nhật")
PY

  if (( REWIRE )); then
    say "Nối dây lại (bootstrap --refresh)"
    run bash -c "cd '$SPEC' && AUTO_CONFIRM=1 ./scripts/bootstrap.sh --refresh"
  fi
fi

# ── 2. Skills (global) ─────────────────────────────────────────────────────────
if (( SKIP_SKILLS )); then
  say "Bỏ qua sync skill (--skip-skills)"
else
  say "Sync skill ra máy (~/.claude/skills, Gemini, Antigravity)"
  args=(--skills-only); (( DRY )) && args+=(--dry-run)
  (cd "$PACK" && bash scripts/sync-skills-to-user.sh "${args[@]}") | grep -E '^(==|  →)' || true
fi

# ── 3. Ghi lại phiên bản ───────────────────────────────────────────────────────
if (( DRY )); then
  say "Dry-run — không ghi gì."
  exit 0
fi
record="$(python3 - "$SPEC" "$MODE" "$SHA" "$DIRTY" "$SKILLS_HASH" "$SKIP_SKILLS" "$PACK/pack.yaml" <<'PY'
import datetime, json, re, sys
spec, mode, sha, dirty, skills_hash, skip_skills, pack_yaml = sys.argv[1:]
version = re.search(r"^version:\s*(\S+)", open(pack_yaml).read(), re.M)
print(json.dumps({
    "deployed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "project": spec,
    "mode": mode,
    "vsaf_sha": sha,
    "dirty": dirty == "true",
    "skills_hash": skills_hash,
    "skills_synced": skip_skills != "1",
    "pack": "NTAPP",
    "pack_version": version.group(1) if version else None,
}, ensure_ascii=False))
PY
)"
mkdir -p "$SPEC/.vsaf" "$LOG_DIR"
python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1]), indent=2, ensure_ascii=False))' "$record" > "$SPEC/.vsaf/dev-deploy.json"
printf '%s\n' "$record" >> "$LOG_DIR/deploys.jsonl"

say "Xong. Đã ghi $SPEC/.vsaf/dev-deploy.json và $LOG_DIR/deploys.jsonl"
[[ "$MODE" == update ]] && echo "  Xem thay đổi trong spec repo: git -C '$SPEC' status"
exit 0
