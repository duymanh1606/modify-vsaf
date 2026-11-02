#!/usr/bin/env bash
# run-project-audit.sh — High-level project audit launcher
#
# Resolves project metadata (checklist page ID) from audit state, builds the
# correct vds-cli audit workflow-project invocation, and delegates to
# run-audit-in-tmux.sh for persistent tmux session management.
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Usage:
#   ./scripts/run-project-audit.sh <project-storage-key> [options]
#   ./scripts/run-project-audit.sh --list
#   ./scripts/run-project-audit.sh --kill <session>
#   ./scripts/run-project-audit.sh --status <session>
#   ./scripts/run-project-audit.sh --attach <session>
#
# Options:
#   --checklist-page-id ID    Override checklist (default: resolved from state)
#   --repos FILTER            Restrict repos (default: all)
#   --profiles LIST           Restrict LLM profiles (default: all)
#   --max-concurrent N        Concurrency (default: 16)
#   --scope-id ID             Narrow to single repo
#   --new-run                 Start a fresh run (default)
#   --resume                  Resume an existing run
#   --upload-to-confluence    Enable Confluence upload
#   --incremental-upload      Enable incremental upload
#   --session-name NAME       Override tmux session name
#   --log-dir DIR             Log directory (default: /tmp)
#   --dry-run                 Print command without executing
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Examples:
#
#   # Full project audit with defaults (resolves checklist from state)
#   ./scripts/run-project-audit.sh 88727304
#
#   # Override checklist, limit concurrency
#   ./scripts/run-project-audit.sh 88727304 \
#     --checklist-page-id 88722450 --max-concurrent 4
#
#   # Single repo within a project
#   ./scripts/run-project-audit.sh 88727304 \
#     --scope-id abc123 --upload-to-confluence
#
#   # Resume a previous run
#   ./scripts/run-project-audit.sh 88727304 --resume
#
#   # Dry run to inspect the generated command
#   ./scripts/run-project-audit.sh 88727304 --dry-run
#
#   # List / status / attach / kill (delegated to run-audit-in-tmux.sh)
#   ./scripts/run-project-audit.sh --list
#   ./scripts/run-project-audit.sh --status proj-88727304
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./vds_sh_helpers.sh
source "$SCRIPT_DIR/vds_sh_helpers.sh"

TMUX_RUNNER="$SCRIPT_DIR/run-audit-in-tmux.sh"

# ── Management subcommands (delegate directly) ──────────────────────

if [[ "${1:-}" == "--list" ]]; then
    exec "$TMUX_RUNNER" --list
fi
if [[ "${1:-}" == "--kill" ]]; then
    exec "$TMUX_RUNNER" --kill "${2:?--kill requires session name}"
fi
if [[ "${1:-}" == "--status" ]]; then
    exec "$TMUX_RUNNER" --status "${2:?--status requires session name}"
fi
if [[ "${1:-}" == "--attach" ]]; then
    exec "$TMUX_RUNNER" --attach "${2:?--attach requires session name}"
fi

# ── Positional: project storage key ─────────────────────────────────

PROJECT_KEY="${1:-}"
if [[ -z "$PROJECT_KEY" || "$PROJECT_KEY" == -* ]]; then
    echo "Usage: $0 <project-storage-key> [options]" >&2
    echo "       $0 --list | --kill NAME | --status NAME | --attach NAME" >&2
    exit 1
fi
shift

# ── Defaults ─────────────────────────────────────────────────────────

CHECKLIST_PAGE_ID=""
REPOS=""
PROFILES=""
MAX_CONCURRENT="16"
SCOPE_ID=""
RUN_MODE="--new-run"
UPLOAD_TO_CONFLUENCE=false
INCREMENTAL_UPLOAD=false
SESSION_NAME=""
LOG_DIR="/tmp"
DRY_RUN=false

# ── Option parsing ───────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --checklist-page-id)
            CHECKLIST_PAGE_ID="$2"
            shift 2
            ;;
        --repos)
            REPOS="$2"
            shift 2
            ;;
        --profiles)
            PROFILES="$2"
            shift 2
            ;;
        --max-concurrent)
            MAX_CONCURRENT="$2"
            shift 2
            ;;
        --scope-id)
            SCOPE_ID="$2"
            shift 2
            ;;
        --new-run)
            RUN_MODE="--new-run"
            shift
            ;;
        --resume)
            RUN_MODE="--resume"
            shift
            ;;
        --upload-to-confluence)
            UPLOAD_TO_CONFLUENCE=true
            shift
            ;;
        --incremental-upload)
            INCREMENTAL_UPLOAD=true
            shift
            ;;
        --session-name)
            SESSION_NAME="$2"
            shift 2
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# ── Checklist resolution (TSK-165.6) ────────────────────────────────

if [[ -z "$CHECKLIST_PAGE_ID" ]]; then
    echo "Resolving checklist page ID for project $PROJECT_KEY from audit state..."
    STATE_JSON="$(vds_uv_run_package audit_orchestrator vds-cli audit --json-only state query-projects --project "$PROJECT_KEY" 2>/dev/null)" || true

    if [[ -n "$STATE_JSON" ]]; then
        CHECKLIST_PAGE_ID="$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
# API returns {\"result\": [...], \"status\": \"ok\", ...}
projects = data.get('result', []) if isinstance(data, dict) else data
if not isinstance(projects, list):
    projects = [projects]
for p in projects:
    meta = p.get('metadata') or {}
    # 1. Try metadata.checklist_page_id (may be null)
    cid = meta.get('checklist_page_id')
    if cid:
        print(cid)
        sys.exit(0)
    # 2. Fallback: metadata.checklist_profiles[0].page_ids[0]
    profiles = meta.get('checklist_profiles') or []
    if profiles:
        page_ids = profiles[0].get('page_ids') or []
        if page_ids:
            print(page_ids[0])
            sys.exit(0)
sys.exit(1)
" <<< "$STATE_JSON" 2>/dev/null)" || CHECKLIST_PAGE_ID=""
    fi

    if [[ -z "$CHECKLIST_PAGE_ID" ]]; then
        echo "Error: cannot resolve checklist page ID for project $PROJECT_KEY. Provide --checklist-page-id explicitly." >&2
        exit 1
    fi
    echo "  Resolved checklist page ID: $CHECKLIST_PAGE_ID"
fi

# ── Session name ─────────────────────────────────────────────────────

if [[ -z "$SESSION_NAME" ]]; then
    SESSION_NAME="proj-${PROJECT_KEY}"
fi

# ── Build vds-cli audit args ─────────────────────────────────────────────

AUDIT_ARGS=(
    workflow-project
    --project-storage-key "$PROJECT_KEY"
    --checklist-page-id "$CHECKLIST_PAGE_ID"
    --max-concurrent "$MAX_CONCURRENT"
    "$RUN_MODE"
)

if [[ -n "$REPOS" ]]; then
    AUDIT_ARGS+=(--repos "$REPOS")
fi
if [[ -n "$PROFILES" ]]; then
    AUDIT_ARGS+=(--profiles "$PROFILES")
fi
if [[ -n "$SCOPE_ID" ]]; then
    AUDIT_ARGS+=(--scope-id "$SCOPE_ID")
fi
if [[ "$UPLOAD_TO_CONFLUENCE" == true ]]; then
    AUDIT_ARGS+=(--upload-to-confluence)
fi
if [[ "$INCREMENTAL_UPLOAD" == true ]]; then
    AUDIT_ARGS+=(--incremental-upload)
fi

# ── Build runner args ────────────────────────────────────────────────

RUNNER_ARGS=()
if [[ "$LOG_DIR" != "/tmp" ]]; then
    RUNNER_ARGS+=(--log-dir "$LOG_DIR")
fi
if [[ "$DRY_RUN" == true ]]; then
    RUNNER_ARGS+=(--dry-run)
fi
RUNNER_ARGS+=("$SESSION_NAME")
RUNNER_ARGS+=("${AUDIT_ARGS[@]}")

LOG_FILE="${LOG_DIR}/audit-${SESSION_NAME}.log"

# ── Launch or dry-run ────────────────────────────────────────────────

"$TMUX_RUNNER" "${RUNNER_ARGS[@]}"

# ── Post-launch follow-up commands (TSK-165.19) ─────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Follow-up commands:"
echo ""
echo "  ./scripts/run-audit-in-tmux.sh --status $SESSION_NAME"
echo "  ./scripts/run-audit-in-tmux.sh --attach $SESSION_NAME"
echo "  ./scripts/run-audit-in-tmux.sh --kill $SESSION_NAME"
echo "  tail -f $LOG_FILE"
echo ""
echo "  # Resume interrupted run:"
echo "  #   ./scripts/run-project-audit.sh $PROJECT_KEY --resume --checklist-page-id $CHECKLIST_PAGE_ID"
echo ""
echo "  # Publish-only (if run completed but upload was skipped):"
echo "  #   vds-cli audit publish-project-run --resume-run <thread_id> --upload-to-confluence"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
