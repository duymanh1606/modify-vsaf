#!/usr/bin/env bash
# Parse .bmm-entry-mode marker — relax upstream gates per hooks_design.md §3
# Usage: . "$(dirname "$0")/lib/entry_mode.sh"; entry_mode  # prints: full|stage_4_standalone|stage_5_standalone

set -uo pipefail

entry_mode() {
  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  local marker="$repo_root/.bmm-entry-mode"

  if [[ -f "$marker" ]]; then
    grep -E '^mode:' "$marker" 2>/dev/null \
      | head -1 \
      | sed -E 's/^mode:[[:space:]]*//' \
      | tr -d '"' | tr -d "'" | xargs
    return
  fi

  # Fallback — CLAUDE.md inline declaration
  local claude_md="$repo_root/CLAUDE.md"
  if [[ -f "$claude_md" ]]; then
    grep -oE '<!--[[:space:]]*entry-mode:[[:space:]]*(full|stage_4_standalone|stage_5_standalone)[[:space:]]*-->' "$claude_md" \
      | head -1 \
      | sed -E 's/.*entry-mode:[[:space:]]*([a-z_4-5]+).*/\1/'
    return
  fi

  echo "full"
}

# Helper: returns 0 if mode skips this hook
mode_skips() {
  # Usage: mode_skips "hook1"  → exits 0 if current mode says skip
  local hook_key="$1"
  local mode="$(entry_mode)"

  case "$mode:$hook_key" in
    stage_4_standalone:hook1) return 0 ;;
    stage_4_standalone:hook2) return 0 ;;
    stage_4_standalone:hook3-techspec) return 0 ;;
    stage_4_standalone:hook14) return 0 ;;
    stage_4_standalone:hook15) return 0 ;;
    stage_5_standalone:hook1) return 0 ;;
    stage_5_standalone:hook2) return 0 ;;
    stage_5_standalone:hook3) return 0 ;;
    stage_5_standalone:hook4) return 0 ;;
    stage_5_standalone:hook7) return 0 ;;
    stage_5_standalone:hook14) return 0 ;;
    stage_5_standalone:hook15) return 0 ;;
    *) return 1 ;;
  esac
}
