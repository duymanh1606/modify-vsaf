#!/usr/bin/env bash
# Hook 16 — hotfix-classifier (NEW)
# Event: UserPromptSubmit before express-hotfix workflow trigger.
# Check: prompt declares 1 of 5 preset Lane 1 types (typo / config / log-level /
#        lint / test-fix). If not → redirect to /ntapp-feature-triage.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable

INPUT="$(read_stdin_json)"
PROMPT="$(json_get "$INPUT" '.prompt')"

# Trigger only when user explicitly claims express/hotfix lane
echo "$PROMPT" | grep -qiE '\bexpress[- ]?(lane|hotfix)|hotfix|fast[- ]?lane|SKIP_PRECOMMIT=1' \
  || ok

# Match 1 of 5 preset
preset=""
echo "$PROMPT" | grep -qiE '\btypo\b|spelling|misspell'                      && preset="typo"
echo "$PROMPT" | grep -qiE '\bconfig\b.*(change|update|fix)|configuration'   && preset="${preset:-config}"
echo "$PROMPT" | grep -qiE '\blog[- ]?level|logging level'                   && preset="${preset:-log-level}"
echo "$PROMPT" | grep -qiE '\blint(er)?\b.*(fix|error|warning)'              && preset="${preset:-lint}"
echo "$PROMPT" | grep -qiE '\btest[- ]?fix|fix.*test|flak(y|iness)'          && preset="${preset:-test-fix}"

if [[ -z "$preset" ]]; then
  log_event "hotfix-classifier" "BLOCK" "no preset matched"
  block "Hotfix không match preset Express Lane (typo / config / log-level / lint / test-fix).
Express Lane bypass full Detailed Design — không dùng cho feature mới hoặc bug logic phức tạp.

Để route đúng lane, chạy:
  /ntapp-feature-triage \"<mô tả thay đổi>\"

Hoặc nếu thực sự là hotfix 1 trong 5 loại trên, prompt phải nêu rõ loại
(vd: \"hotfix typo trong message error login\")."
fi

log_event "hotfix-classifier" "PASS" "preset=$preset"
echo "[hotfix-classifier] Preset: $preset. Compensate full DD + WBS entry + ripple audit trong 48h." >&2
ok
