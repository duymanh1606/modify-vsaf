#!/usr/bin/env bash
# DEPRECATED: The launch subcommand now delegates to run-project-audit.sh
# rather than containing its own parallel session-launching implementation.
# The scope-ids and print subcommands remain useful standalone utilities.
# See: ./scripts/run-project-audit.sh --help
#      ./scripts/run-department-audit.sh --help
set -euo pipefail

# repair_autopay_reports.sh — helper for repairing Auto Payment canonical repo reports
#
# Generates scope_ids for the 3 Auto Payment repos and prints or launches
# single-repo workflow-project reruns that will republish canonical repo pages.
#
# Usage:
#   ./scripts/repair_autopay_reports.sh scope-ids
#   ./scripts/repair_autopay_reports.sh print [all|management|schedule|transaction]
#   ./scripts/repair_autopay_reports.sh launch [all|management|schedule|transaction]
#
# Examples:
#   ./scripts/repair_autopay_reports.sh scope-ids
#   ./scripts/repair_autopay_reports.sh print all
#   ./scripts/repair_autopay_reports.sh launch management

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./vds_sh_helpers.sh
source "$SCRIPT_DIR/vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"
PROJECT_KEY="88718977"
CHECKLIST_PAGE_ID="88722450"
MAX_CONCURRENT="6"
SESSION_PREFIX="autopay-repair"

REPO_KEYS=(
  "pay-auto-payment-management"
  "pay-auto-payment-schedule"
  "pay-auto-payment-transaction"
)

repo_slug_for_key() {
  case "$1" in
    pay-auto-payment-management) printf '%s\n' 'auto-payment-management' ;;
    pay-auto-payment-schedule) printf '%s\n' 'auto-payment-schedule' ;;
    pay-auto-payment-transaction) printf '%s\n' 'auto-payment-transaction' ;;
    *)
      echo "Unknown repo key: $1" >&2
      return 1
      ;;
  esac
}

session_name_for_key() {
  case "$1" in
    pay-auto-payment-management) printf '%s\n' "${SESSION_PREFIX}-management" ;;
    pay-auto-payment-schedule) printf '%s\n' "${SESSION_PREFIX}-schedule" ;;
    pay-auto-payment-transaction) printf '%s\n' "${SESSION_PREFIX}-transaction" ;;
    *)
      echo "Unknown repo key: $1" >&2
      return 1
      ;;
  esac
}

selected_repo_keys() {
  local selector="${1:-all}"
  case "$selector" in
    all)
      printf '%s\n' "${REPO_KEYS[@]}"
      ;;
    management)
      printf '%s\n' 'pay-auto-payment-management'
      ;;
    schedule)
      printf '%s\n' 'pay-auto-payment-schedule'
      ;;
    transaction)
      printf '%s\n' 'pay-auto-payment-transaction'
      ;;
    *)
      echo "Unknown selector: $selector (expected all|management|schedule|transaction)" >&2
      return 1
      ;;
  esac
}

get_scope_id() {
  local repo_key="$1"
  local repo_slug
  repo_slug="$(repo_slug_for_key "$repo_key")"

  local output
  output="$(vds_uv_run_package audit_orchestrator vds-cli audit --json-only parse-repo \
    --project "$PROJECT_KEY" \
    --repo "$repo_slug")"

  python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["scope_id"])' <<< "$output"
}

print_scope_ids() {
  local repo_key scope_id
  while IFS= read -r repo_key; do
    [[ -z "$repo_key" ]] && continue
    scope_id="$(get_scope_id "$repo_key")"
    printf '%s %s\n' "$repo_key" "$scope_id"
  done < <(selected_repo_keys all)
}

print_command() {
  local repo_key="$1"
  local scope_id="$2"
  local session_name
  session_name="$(session_name_for_key "$repo_key")"
  cat <<EOF
./scripts/run-project-audit.sh $PROJECT_KEY \
  --scope-id $scope_id \
  --checklist-page-id $CHECKLIST_PAGE_ID \
  --max-concurrent $MAX_CONCURRENT \
  --upload-to-confluence \
  --session-name $session_name \
  --new-run
EOF
}

launch_repo() {
  local repo_key="$1"
  local scope_id="$2"
  local session_name
  session_name="$(session_name_for_key "$repo_key")"

  "$SCRIPT_DIR/run-project-audit.sh" "$PROJECT_KEY" \
    --scope-id "$scope_id" \
    --checklist-page-id "$CHECKLIST_PAGE_ID" \
    --max-concurrent "$MAX_CONCURRENT" \
    --upload-to-confluence \
    --session-name "$session_name" \
    --new-run
}

main() {
  local action="${1:-}"
  local selector="${2:-all}"
  local repo_key scope_id

  case "$action" in
    scope-ids)
      print_scope_ids
      ;;
    print)
      while IFS= read -r repo_key; do
        [[ -z "$repo_key" ]] && continue
        scope_id="$(get_scope_id "$repo_key")"
        print_command "$repo_key" "$scope_id"
        printf '\n'
      done < <(selected_repo_keys "$selector")
      ;;
    launch)
      echo "WARNING: 'launch' is deprecated. Use run-project-audit.sh instead:" >&2
      echo "  ./scripts/run-project-audit.sh $PROJECT_KEY --scope-id <scope-id> --checklist-page-id $CHECKLIST_PAGE_ID" >&2
      while IFS= read -r repo_key; do
        [[ -z "$repo_key" ]] && continue
        scope_id="$(get_scope_id "$repo_key")"
        echo "Launching $repo_key with scope_id=$scope_id"
        launch_repo "$repo_key" "$scope_id"
      done < <(selected_repo_keys "$selector")
      ;;
    *)
      echo "Usage: $0 {scope-ids|print|launch} [all|management|schedule|transaction]" >&2
      exit 1
      ;;
  esac
}

main "$@"
