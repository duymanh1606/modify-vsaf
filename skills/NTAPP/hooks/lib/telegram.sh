#!/usr/bin/env bash
# Telegram sender — env-driven, fail-silent if env not set
# Usage: . lib/telegram.sh; tg_send "<title>" "<body>" [chat_id_override]

set -uo pipefail

tg_send() {
  local title="$1" body="$2" chat_id="${3:-${TELEGRAM_CHAT_ID:-}}"
  local token="${TELEGRAM_BOT_TOKEN:-}"

  [[ -z "$token" || -z "$chat_id" ]] && return 0  # silent skip

  local payload
  payload=$(printf '{"chat_id":"%s","parse_mode":"Markdown","text":"*%s*\n\n%s"}' \
    "$chat_id" "$title" "$body")

  curl -fsS --max-time 5 \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "https://api.telegram.org/bot${token}/sendMessage" \
    >/dev/null 2>&1 || return 0  # never fail the hook on Telegram error
}

# Resolve role → chat_id via env (set per project)
# Env: TG_CHAT_SA, TG_CHAT_DSO, TG_CHAT_QA, TG_CHAT_PM, TG_CHAT_TECHLEAD
tg_chat_for_role() {
  local role="$1"
  local varname="TG_CHAT_${role^^}"
  echo "${!varname:-${TELEGRAM_CHAT_ID:-}}"
}
