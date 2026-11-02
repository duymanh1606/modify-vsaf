#!/usr/bin/env bash
# install-agy-skills.sh — make the Antigravity (agy) host usable from this repo.
#
# agy 1.0.14 discovers USER skills from the GLOBAL dir ~/.gemini/config/skills/
# (project-scope .agents/skills is NOT auto-discovered in this version). So we:
#   1. symlink the `vsaf-agy` launcher onto PATH (~/.local/bin, where agy lives)
#   2. symlink each repo-shipped agy glue skill into ~/.gemini/config/skills/
#
# Machine-local + idempotent + reversible (symlinks only). Re-run any time.
# This is what `bootstrap.sh --antigravity` will call.
set -eo pipefail

HERE="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
SKILLS_DIR="$HOME/.gemini/config/skills"

mkdir -p "$BIN_DIR" "$SKILLS_DIR"

# 1) vsaf-agy launcher onto PATH
ln -sf "$HERE/vsaf-agy" "$BIN_DIR/vsaf-agy"
echo "✓ vsaf-agy -> $BIN_DIR/vsaf-agy"

# 2) glue skills -> global skills dir (one symlink per skill folder)
for skill in "$HERE/agy-skills/"*/; do
  [ -d "$skill" ] || continue
  name="$(basename "$skill")"
  ln -sfn "$skill" "$SKILLS_DIR/$name"
  echo "✓ skill $name -> $SKILLS_DIR/$name"
done

# 2b) vendored third-party skills từ .agent/skills (dùng chung mọi host) -> agy global dir.
#     agy không đọc .agent/skills project-scope → cần symlink như glue skills.
REPO_ROOT="$(cd -P "$HERE/../.." && pwd)"
for name in lavish; do
  src="$REPO_ROOT/.agent/skills/$name"
  if [ -d "$src" ]; then
    ln -sfn "$src" "$SKILLS_DIR/$name"
    echo "✓ skill $name -> $SKILLS_DIR/$name (vendored)"
  fi
done

# 3) Hook 9 agy-native PostToolUse (optional realtime layer). Driver-level hooks need
#    no install — the driver invokes hooks/*.sh directly. This only sets up the per-edit shim.
if [ -f "$HERE/hooks/install-agy-hooks.sh" ]; then
  echo
  bash "$HERE/hooks/install-agy-hooks.sh" | sed 's/^/  /'
fi

echo
echo "Done. In agy you can now use slash commands, e.g.:"
echo "  /NTAPP-agy-vsaf-slice-loop SLICE-01"
echo "  /NTAPP-agy-vsaf-ad-hoc-per-unit \"Thêm endpoint health-check\""
echo "Workflow gate hooks (3,4,5,5b,6,7,8,10) fire automatically at node boundaries."
echo
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "NOTE: add to PATH -> export PATH=\"\$HOME/.local/bin:\$PATH\"";; esac
