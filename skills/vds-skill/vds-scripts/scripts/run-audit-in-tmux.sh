#!/usr/bin/env bash
# run-audit-in-tmux.sh — Persistent runner for vds-cli audit commands
#
# Wraps any vds-cli audit invocation in a named tmux session so it survives
# Claude Code session timeouts, terminal closures, and SSH disconnects.
# The parent process stays alive for the full duration, child subprocesses
# are never orphaned, and all output is tee'd to a log file.
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Usage:
#   ./scripts/run-audit-in-tmux.sh [options] <session-name> <vds-cli audit args...>
#
# Options:
#   --log-dir DIR    Log directory (default: /tmp)
#   --dry-run        Print command without executing
#   --list           List active audit tmux sessions
#   --kill NAME      Kill a named session
#   --status NAME    Show progress from session artifacts
#   --attach NAME    Attach to a running session
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Examples:
#
#   # Single repo evaluation
#   ./scripts/run-audit-in-tmux.sh billing-eval \
#     workflow ~/.vds/cache/repos/PAR-project/merchant-billing \
#     --project-storage-key 88727304 --checklist-page-id 88722450 \
#     --skip-readiness-check --skip-evidence-check --offline
#
#   # Full project (all repos, parallel profiles)
#   ./scripts/run-audit-in-tmux.sh par-full \
#     workflow-project --project-storage-key 88727304 \
#     --checklist-page-id 88722450 --offline --max-concurrent 4 --new-run
#
#   # One prepared repo under project semantics, all available profiles
#   ./scripts/run-audit-in-tmux.sh core-transfer-swit-all-profiles \
#     workflow-project --project-storage-key 88718975 \
#     --seed-payload /tmp/core-transfer-switching-timeout-seed.json \
#     --checklist-page-id 88722450 --max-concurrent 6 \
#     --upload-to-confluence --incremental-upload --new-run
#
#   # Multi-project (department-wide)
#   ./scripts/run-audit-in-tmux.sh payment-dept \
#     workflow-projects --project-storage-keys 88718943,88718977,91335346 \
#     --checklist-page-id 88722450 --prepare-materials \
#     --max-projects-concurrent 2 --max-concurrent 4
#
#   # Preparation only
#   ./scripts/run-audit-in-tmux.sh par-prepare \
#     prepare --project 88727304
#
#   # Any vds-cli audit command (doctor, state, parse-registry, etc.)
#   ./scripts/run-audit-in-tmux.sh registry-parse \
#     parse-registry --registry-page 88716694 --state-dsn env
#
#   # List active sessions
#   ./scripts/run-audit-in-tmux.sh --list
#
#   # Check session progress
#   ./scripts/run-audit-in-tmux.sh --status par-full
#
#   # Attach to watch live
#   ./scripts/run-audit-in-tmux.sh --attach par-full
#
#   # Kill a stuck session
#   ./scripts/run-audit-in-tmux.sh --kill par-full
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -uo pipefail

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPTS_DIR")"
LOG_DIR="/tmp"
DRY_RUN=false

# ── Subcommands ──────────────────────────────────────────────────────

_list_sessions() {
    echo "Active audit tmux sessions:"
    local found=false
    while read -r name; do
        # Check both /tmp and LOG_DIR for audit logs
        local log=""
        for candidate in "/tmp/audit-${name}.log" "${LOG_DIR}/audit-${name}.log"; do
            [ -f "$candidate" ] && log="$candidate" && break
        done
        if [ -n "$log" ]; then
            local lines
            lines=$(wc -l < "$log" 2>/dev/null)
            local last
            last=$(tail -1 "$log" 2>/dev/null | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}T[0-9:]*' | head -1)
            echo "  $name  (log: ${lines} lines, last: ${last:-unknown})"
            found=true
        fi
    done < <(tmux list-sessions -F '#{session_name}' 2>/dev/null)
    if [ "$found" = false ]; then
        echo "  (no audit sessions found)"
    fi
}

_kill_session() {
    local name="$1"
    if tmux has-session -t "$name" 2>/dev/null; then
        tmux kill-session -t "$name"
        echo "Killed session: $name"
    else
        echo "No session named: $name"
    fi
}

_status_session() {
    local name="$1"
    # Search both /tmp and LOG_DIR
    local log=""
    for candidate in "${LOG_DIR}/audit-${name}.log" "/tmp/audit-${name}.log"; do
        [ -f "$candidate" ] && log="$candidate" && break
    done

    echo "Session: $name"
    if tmux has-session -t "$name" 2>/dev/null; then
        echo "  tmux: alive"
    else
        echo "  tmux: ended"
    fi

    if [ -n "$log" ]; then
        echo "  log: $log ($(wc -l < "$log") lines)"
        echo ""
        echo "  Latest events:"
        grep -E "completion_pct|dispatch_completed|dispatch_started|workflow_completed|error_count|row_outcome|dispatch_slot_utilization|row_concurrency_active" "$log" 2>/dev/null | tail -8 | sed 's/^/    /'
        if [ "$(grep -c "completion_pct" "$log" 2>/dev/null)" -eq 0 ]; then
            echo "    (no completion events yet)"
            tail -3 "$log" 2>/dev/null | sed 's/^/    /'
        fi
    else
        echo "  log: not found"
    fi

    # Try to read workflow-summary from run artifacts
    echo ""
    echo "  Run artifacts:"
    local found=false
    for summary in ~/.vds/cache/audit_runs/*/runs/*/workflow-summary.json; do
        if [ -f "$summary" ]; then
            local run_dir
            run_dir=$(dirname "$summary")
            local run_name
            run_name=$(basename "$run_dir")
            # Check if the log references this run
            if [ -n "$log" ] && grep -q "$run_name" "$log" 2>/dev/null; then
                python3 -c "
import json
d = json.load(open('$summary'))
ps = d.get('progress_snapshot', {})
st = d.get('status', '?')
fin = ps.get('finished_jobs', '?')
plan = ps.get('planned_jobs', '?')
err = ps.get('error_jobs', 0)
print(f'    {st}: {fin}/{plan} jobs, {err} errors')
print(f'    dir: $run_dir')
" 2>/dev/null && found=true && break
            fi
        fi
    done
    if [ "$found" = false ]; then
        echo "    (no matching run artifacts found)"
    fi
}

_attach_session() {
    local name="$1"
    if tmux has-session -t "$name" 2>/dev/null; then
        tmux attach -t "$name"
    else
        echo "No session named: $name"
        echo "Active sessions:"
        tmux list-sessions 2>/dev/null | sed 's/^/  /'
    fi
}

# ── Option parsing ───────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --list)
            _list_sessions
            exit 0
            ;;
        --kill)
            _kill_session "${2:?--kill requires session name}"
            exit 0
            ;;
        --status)
            _status_session "${2:?--status requires session name}"
            exit 0
            ;;
        --attach)
            _attach_session "${2:?--attach requires session name}"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# ── Main: launch audit in tmux ───────────────────────────────────────

SESSION_NAME="${1:?Usage: $0 [options] <session-name> <vds-cli audit args...>}"
shift

if [ $# -eq 0 ]; then
    echo "Error: no vds-cli audit command provided" >&2
    echo "Usage: $0 <session-name> <vds-cli audit subcommand> [args...]" >&2
    exit 1
fi

# Validate session name (tmux disallows colons and periods at start)
if [[ "$SESSION_NAME" =~ [:] ]]; then
    echo "Error: session name cannot contain ':' (reserved by tmux)" >&2
    exit 1
fi

# Ensure log directory exists
mkdir -p "$LOG_DIR" || { echo "Error: cannot create log directory: $LOG_DIR" >&2; exit 1; }

LOG_FILE="${LOG_DIR}/audit-${SESSION_NAME}.log"

# Build the command — use printf %q for safe shell quoting
AUDIT_CMD="set -o pipefail; cd '${PROJECT_DIR}' && ./scripts/worktree_uv.sh run --project vds_cli vds-cli audit"
for arg in "$@"; do
    AUDIT_CMD+=" $(printf '%q' "$arg")"
done
AUDIT_CMD+=" 2>&1 | tee '${LOG_FILE}'"
# Capture vds-cli audit exit code through the pipe (pipefail is set above)
AUDIT_CMD+="; _ec=\${PIPESTATUS[0]:-\$?}"
AUDIT_CMD+="; echo ''"
AUDIT_CMD+="; echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'"
AUDIT_CMD+="; echo \"EXIT CODE: \${_ec}\""
AUDIT_CMD+="; echo \"Completed at: \$(date)\""
AUDIT_CMD+="; echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'"
AUDIT_CMD+="; echo 'Session will close in 30s (Ctrl-C to keep open)...'"
AUDIT_CMD+="; sleep 30"

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN — would execute in tmux session '$SESSION_NAME':"
    echo ""
    echo "  $AUDIT_CMD"
    echo ""
    echo "Log: $LOG_FILE"
    exit 0
fi

# Kill existing session with same name
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# Create detached tmux session
tmux new-session -d -s "$SESSION_NAME" "bash -c $(printf '%q' "$AUDIT_CMD")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Audit run: $SESSION_NAME"
echo "  Command:   vds-cli audit $*"
echo "  Log:       $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Monitor:"
echo "    $0 --status $SESSION_NAME"
echo "    tail -f $LOG_FILE"
echo "    tmux attach -t $SESSION_NAME"
echo ""
echo "  Control:"
echo "    $0 --kill $SESSION_NAME"
echo "    $0 --list"
