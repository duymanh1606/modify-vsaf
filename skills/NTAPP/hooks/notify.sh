#!/usr/bin/env bash
# Notification sink — multi-channel router (hooks_design.md §4)
#
# Usage:
#   notify <severity> <decision_required:bool> <title> <body> [--mention @role]
#
# Severity routing:
#   info             → log file only
#   warn             → IDE chat inbox
#   decision_required=true → Telegram + IDE chat inbox
#   error            → IDE chat inbox (LLM reads system-reminder)

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
. "$HOOK_DIR/lib/telegram.sh"

severity="${1:-info}"
decision="${2:-false}"
title="${3:-}"
body="${4:-}"
mention=""

shift 4 2>/dev/null || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mention) mention="$2"; shift 2 ;;
    *)         shift ;;
  esac
done

[[ -z "$title" ]] && { echo "notify: title required" >&2; exit 1; }

INBOX_DIR="$(get_spec_repo_root)/NTAPP-output/_notifications"
mkdir -p "$INBOX_DIR"
INBOX="$INBOX_DIR/inbox.md"
LOG="$INBOX_DIR/notify.log"

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ─── Always log ─────────────────────────────────────────────────────
echo "$ts | $severity | decision=$decision | $title | mention=$mention" >> "$LOG"

# ─── info → log only ────────────────────────────────────────────────
if [[ "$severity" == "info" && "$decision" != "true" ]]; then
  exit 0
fi

# ─── IDE inbox (warn / error / decision_required) ───────────────────
{
  echo ""
  echo "## [$ts] $severity${decision:+ (decision required)}"
  [[ -n "$mention" ]] && echo "**Mention:** $mention"
  echo "**Title:** $title"
  echo ""
  echo "$body"
  echo ""
  echo "---"
} >> "$INBOX"

# ─── Telegram (decision_required only) ──────────────────────────────
if [[ "$decision" == "true" ]]; then
  role="$(echo "$mention" | sed 's/@//; s/,.*//')"
  chat_id="$(tg_chat_for_role "$role")"
  tg_body="$body"
  [[ -n "$mention" ]] && tg_body="Mention: $mention\n\n$body"
  tg_send "$title" "$tg_body" "$chat_id"
fi

exit 0
