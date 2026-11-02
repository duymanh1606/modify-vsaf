#!/usr/bin/env bash
# audit-dashboard.sh — Live dashboard for all running/completed audit sessions
#
# Discovers tmux sessions with audit log files and renders a progress table.
# Reads ONLY from tmux state and log files — no Postgres, no CLI calls.
# Designed for fast, side-effect-free monitoring in watch mode.
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Usage:
#   ./scripts/audit-dashboard.sh                  # Single snapshot
#   ./scripts/audit-dashboard.sh --watch           # Refresh every 10s
#   ./scripts/audit-dashboard.sh --watch 5         # Refresh every 5s
#   ./scripts/audit-dashboard.sh --department PAR  # Filter dept-PAR* sessions
#   ./scripts/audit-dashboard.sh --json            # Machine-readable JSON output
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Examples:
#
#   # Quick check on all audit sessions
#   ./scripts/audit-dashboard.sh
#
#   # Watch payment department audits
#   ./scripts/audit-dashboard.sh --department payment --watch 15
#
#   # Pipe JSON to jq for scripting
#   ./scripts/audit-dashboard.sh --json | jq '.[] | select(.status=="error")'
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────

LOG_DIR="/tmp"
CACHE_DIR="${HOME}/.vds/cache/audit_runs"
WATCH_INTERVAL=""
DEPT_FILTER=""
JSON_OUTPUT=false
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Option parsing ───────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --watch)
            WATCH_INTERVAL="${2:-10}"
            if [[ "$WATCH_INTERVAL" =~ ^[0-9]+$ ]]; then
                shift 2
            else
                WATCH_INTERVAL=10
                shift
            fi
            ;;
        --department)
            DEPT_FILTER="${2:?--department requires a name}"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --log-dir)
            LOG_DIR="${2:?--log-dir requires a path}"
            shift 2
            ;;
        -h|--help)
            sed -n '2,/^set -/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# ── Session discovery ─────────────────────────────────────────────────
# Finds all tmux sessions matching dept-* or proj-* prefixes, plus any
# other sessions that have a matching audit log file.

_discover_sessions() {
    local tmpfile
    tmpfile=$(mktemp /tmp/audit-dash-discover.XXXXXX)
    trap "rm -f '$tmpfile'" RETURN

    # Pass 1: tmux sessions with audit-relevant prefixes
    while IFS=' ' read -r name created; do
        [[ -z "$name" ]] && continue
        if [[ "$name" == dept-* ]] || [[ "$name" == proj-* ]]; then
            echo "$name $created" >> "$tmpfile"
        else
            # Check if a log file exists for this session
            for candidate in "${LOG_DIR}/audit-${name}.log" "/tmp/audit-${name}.log"; do
                if [[ -f "$candidate" ]]; then
                    echo "$name $created" >> "$tmpfile"
                    break
                fi
            done
        fi
    done < <(tmux list-sessions -F '#{session_name} #{session_created}' 2>/dev/null || true)

    # Pass 2: orphan log files (session ended, log remains)
    for logfile in "${LOG_DIR}"/audit-*.log /tmp/audit-*.log; do
        [[ -f "$logfile" ]] || continue
        local base
        base=$(basename "$logfile")
        # Extract session name: audit-<name>.log
        local sname="${base#audit-}"
        sname="${sname%.log}"
        [[ -z "$sname" ]] && continue
        # Skip if already discovered in pass 1
        if ! grep -q "^${sname} " "$tmpfile" 2>/dev/null; then
            if [[ "$sname" == dept-* ]] || [[ "$sname" == proj-* ]]; then
                echo "$sname 0" >> "$tmpfile"
            fi
        fi
    done

    # Emit deduplicated, sorted: name created_epoch
    sort -u -k1,1 "$tmpfile" 2>/dev/null || true
}

# ── Log file resolution ───────────────────────────────────────────────

_find_log() {
    local name="$1"
    for candidate in "${LOG_DIR}/audit-${name}.log" "/tmp/audit-${name}.log"; do
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# ── Elapsed time formatting ──────────────────────────────────────────

_format_elapsed() {
    local seconds="$1"
    if (( seconds < 0 )); then
        echo "—"
        return
    fi
    local h m s
    h=$(( seconds / 3600 ))
    m=$(( (seconds % 3600) / 60 ))
    s=$(( seconds % 60 ))
    if (( h > 0 )); then
        printf '%dh %02dm %02ds' "$h" "$m" "$s"
    else
        printf '%dm %02ds' "$m" "$s"
    fi
}

# ── Elapsed from log timestamps or tmux creation ─────────────────────

_calc_elapsed() {
    local log="$1"
    local created_epoch="$2"
    local now_epoch
    now_epoch=$(date +%s)

    # Try log file: first line timestamp vs last line timestamp (or now if still running)
    if [[ -n "$log" ]] && [[ -f "$log" ]]; then
        local first_ts last_ts
        first_ts=$(head -1 "$log" 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
        last_ts=$(tail -1 "$log" 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
        if [[ -n "$first_ts" ]]; then
            local start_epoch end_epoch
            # macOS date -j vs GNU date
            if date -j -f '%Y-%m-%dT%H:%M:%S' "$first_ts" '+%s' &>/dev/null; then
                start_epoch=$(date -j -f '%Y-%m-%dT%H:%M:%S' "$first_ts" '+%s' 2>/dev/null)
                if [[ -n "$last_ts" ]]; then
                    end_epoch=$(date -j -f '%Y-%m-%dT%H:%M:%S' "$last_ts" '+%s' 2>/dev/null)
                fi
            else
                start_epoch=$(date -d "$first_ts" '+%s' 2>/dev/null)
                if [[ -n "$last_ts" ]]; then
                    end_epoch=$(date -d "$last_ts" '+%s' 2>/dev/null)
                fi
            fi
            if [[ -n "${start_epoch:-}" ]]; then
                end_epoch="${end_epoch:-$now_epoch}"
                echo $(( end_epoch - start_epoch ))
                return
            fi
        fi
    fi

    # Fallback: tmux session creation time
    if [[ "$created_epoch" -gt 0 ]] 2>/dev/null; then
        echo $(( now_epoch - created_epoch ))
        return
    fi

    echo "-1"
}

# ── Scope detection ───────────────────────────────────────────────────
# Attempt to determine scope (e.g. "3 projs", "AutoPay") from log content
# or workflow-summary.json artifacts.

_detect_scope() {
    local name="$1"
    local log="$2"

    # For dept-* sessions, count project keys from log
    if [[ "$name" == dept-* ]]; then
        if [[ -n "$log" ]] && [[ -f "$log" ]]; then
            local proj_count
            proj_count=$(grep -oE 'project_storage_key=[0-9]+' "$log" 2>/dev/null | sort -u | wc -l | tr -d ' ')
            if [[ "$proj_count" -gt 0 ]]; then
                echo "${proj_count} projs"
                return
            fi
        fi
        echo "dept"
        return
    fi

    # For proj-* sessions, try to find project/repo name from log
    if [[ "$name" == proj-* ]]; then
        local key="${name#proj-}"
        if [[ -n "$log" ]] && [[ -f "$log" ]]; then
            # Look for project_name or repo slug in early log lines
            local pname
            pname=$(head -50 "$log" 2>/dev/null | grep -oE 'project_name=[^ ]+' | head -1 | cut -d= -f2)
            if [[ -n "$pname" ]]; then
                echo "$pname"
                return
            fi
        fi
        echo "$key"
        return
    fi

    echo "—"
}

# ── Progress extraction from log + artifacts ─────────────────────────
# Returns: completion_pct error_count exit_code status

_extract_progress() {
    local name="$1"
    local log="$2"
    local alive="$3"

    local completion_pct="-"
    local error_count="0"
    local exit_code="-"
    local status="unknown"

    if [[ -n "$log" ]] && [[ -f "$log" ]]; then
        # Latest completion_pct (handles both = and : separators)
        local pct_line
        pct_line=$(grep -oE 'completion_pct[=:] *[0-9]+(\.[0-9]+)?' "$log" 2>/dev/null | tail -1)
        if [[ -n "$pct_line" ]]; then
            completion_pct=$(echo "$pct_line" | grep -oE '[0-9]+(\.[0-9]+)?' | tail -1)
        fi

        # Error count — last reported value
        local err_line
        err_line=$(grep -oE 'error_count[=:] *[0-9]+' "$log" 2>/dev/null | tail -1)
        if [[ -n "$err_line" ]]; then
            error_count=$(echo "$err_line" | grep -oE '[0-9]+' | tail -1)
        fi

        # Exit code from the trailer block
        local ec_line
        ec_line=$(grep -oE 'EXIT CODE: [0-9]+' "$log" 2>/dev/null | tail -1)
        if [[ -n "$ec_line" ]]; then
            exit_code=$(echo "$ec_line" | grep -oE '[0-9]+')
        fi
    fi

    # Try workflow-summary.json from cache
    if [[ -d "$CACHE_DIR" ]] && [[ -n "$log" ]] && [[ -f "$log" ]]; then
        for summary in "$CACHE_DIR"/*/runs/*/workflow-summary.json; do
            [[ -f "$summary" ]] || continue
            local run_dir run_name
            run_dir=$(dirname "$summary")
            run_name=$(basename "$run_dir")
            if grep -q "$run_name" "$log" 2>/dev/null; then
                # Extract from JSON with python (fast, single read)
                eval "$(python3 -c "
import json, sys
try:
    d = json.load(open('$summary'))
    ps = d.get('progress_snapshot', {})
    pct = ps.get('completion_pct')
    errs = ps.get('error_jobs', 0)
    if pct is not None:
        print(f'completion_pct={pct}')
    if errs:
        print(f'error_count={errs}')
except Exception:
    pass
" 2>/dev/null)" || true
                break
            fi
        done
    fi

    # Determine status
    if [[ "$exit_code" != "-" ]]; then
        if [[ "$exit_code" == "0" ]]; then
            status="completed"
            completion_pct="100.0"
        else
            status="error(${exit_code})"
        fi
    elif [[ "$alive" == "true" ]]; then
        status="running"
    else
        status="ended"
    fi

    echo "${completion_pct} ${error_count} ${exit_code} ${status}"
}

# ── Render: table output ──────────────────────────────────────────────

_render_table() {
    local -a rows=()
    local -a error_sessions=()
    local total=0 running=0 completed=0 errored=0 ended=0

    while IFS=' ' read -r name created_epoch; do
        [[ -z "$name" ]] && continue

        # Apply department filter
        if [[ -n "$DEPT_FILTER" ]]; then
            local lower_name lower_filter
            lower_name=$(echo "$name" | tr '[:upper:]' '[:lower:]')
            lower_filter=$(echo "dept-${DEPT_FILTER}" | tr '[:upper:]' '[:lower:]')
            [[ "$lower_name" == ${lower_filter}* ]] || continue
        fi

        # Liveness check
        local alive="false"
        if tmux has-session -t "$name" 2>/dev/null; then
            alive="true"
        fi

        # Log file
        local log=""
        log=$(_find_log "$name") || true

        # Scope
        local scope
        scope=$(_detect_scope "$name" "$log")

        # Progress
        local progress_data
        progress_data=$(_extract_progress "$name" "$log" "$alive")
        local completion_pct error_count exit_code status
        read -r completion_pct error_count exit_code status <<< "$progress_data"

        # Elapsed
        local elapsed_secs elapsed_str
        elapsed_secs=$(_calc_elapsed "$log" "$created_epoch")
        elapsed_str=$(_format_elapsed "$elapsed_secs")

        # Format progress display
        local progress_str
        if [[ "$completion_pct" == "-" ]]; then
            progress_str="—"
        else
            progress_str="${completion_pct}%"
        fi

        # Counters
        (( total++ )) || true
        case "$status" in
            running)    (( running++ ))   || true ;;
            completed)  (( completed++ )) || true ;;
            error*)     (( errored++ ))   || true
                        error_sessions+=("$name|$exit_code") ;;
            ended)      (( ended++ ))     || true ;;
        esac

        rows+=("$(printf '%-20s %-9s %-11s %-9s %-7s %s' \
            "$name" "$scope" "$status" "$progress_str" "$error_count" "$elapsed_str")")

    done < <(_discover_sessions)

    # Print header
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf '%-20s %-9s %-11s %-9s %-7s %s\n' \
        "SESSION" "SCOPE" "STATUS" "PROGRESS" "ERRORS" "ELAPSED"
    echo "───────────────────────────────────────────────────────────────────────────────"

    if [[ ${#rows[@]} -eq 0 ]]; then
        echo "  (no audit sessions found)"
    else
        for row in "${rows[@]}"; do
            echo "$row"
        done
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Summary line
    local parts="Total: ${total} sessions"
    [[ $running -gt 0 ]]   && parts+=" | ${running} running"
    [[ $completed -gt 0 ]] && parts+=" | ${completed} completed"
    [[ $errored -gt 0 ]]   && parts+=" | ${errored} errored"
    [[ $ended -gt 0 ]]     && parts+=" | ${ended} ended"
    echo "$parts"

    # TSK-165.21: Hints for errored sessions
    if [[ ${#error_sessions[@]} -gt 0 ]]; then
        echo ""
        for entry in "${error_sessions[@]}"; do
            local sess_name="${entry%%|*}"
            local sess_ec="${entry##*|}"
            # Derive storage key from proj-<key> pattern
            if [[ "$sess_name" == proj-* ]]; then
                local key="${sess_name#proj-}"
                echo "Hint: ${sess_name} ended with errors (exit ${sess_ec}). Resume: ./scripts/run-project-audit.sh ${key} --resume"
            else
                echo "Hint: ${sess_name} ended with errors (exit ${sess_ec}). Check: ./scripts/run-audit-in-tmux.sh --status ${sess_name}"
            fi
        done
    fi
}

# ── Render: JSON output ───────────────────────────────────────────────

_render_json() {
    local first=true
    echo "["

    while IFS=' ' read -r name created_epoch; do
        [[ -z "$name" ]] && continue

        # Apply department filter
        if [[ -n "$DEPT_FILTER" ]]; then
            local lower_name lower_filter
            lower_name=$(echo "$name" | tr '[:upper:]' '[:lower:]')
            lower_filter=$(echo "dept-${DEPT_FILTER}" | tr '[:upper:]' '[:lower:]')
            [[ "$lower_name" == ${lower_filter}* ]] || continue
        fi

        local alive="false"
        if tmux has-session -t "$name" 2>/dev/null; then
            alive="true"
        fi

        local log=""
        log=$(_find_log "$name") || true

        local scope
        scope=$(_detect_scope "$name" "$log")

        local progress_data
        progress_data=$(_extract_progress "$name" "$log" "$alive")
        local completion_pct error_count exit_code status
        read -r completion_pct error_count exit_code status <<< "$progress_data"

        local elapsed_secs
        elapsed_secs=$(_calc_elapsed "$log" "$created_epoch")
        local elapsed_str
        elapsed_str=$(_format_elapsed "$elapsed_secs")

        # JSON-safe null handling
        local pct_json="null"
        [[ "$completion_pct" != "-" ]] && pct_json="$completion_pct"
        local ec_json="null"
        [[ "$exit_code" != "-" ]] && ec_json="$exit_code"
        local log_json="null"
        [[ -n "$log" ]] && log_json="\"${log}\""

        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi

        cat <<ENTRY
  {
    "session": "$name",
    "scope": "$scope",
    "status": "$status",
    "alive": $alive,
    "completion_pct": $pct_json,
    "error_count": $error_count,
    "exit_code": $ec_json,
    "elapsed_seconds": $elapsed_secs,
    "elapsed": "$elapsed_str",
    "log_file": $log_json
  }
ENTRY
        # no newline after ENTRY — the comma/bracket logic handles it

    done < <(_discover_sessions)

    echo ""
    echo "]"
}

# ── Main ──────────────────────────────────────────────────────────────

_render() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        _render_json
    else
        _render_table
    fi
}

if [[ -n "$WATCH_INTERVAL" ]]; then
    # Watch mode: clear and redraw on interval
    while true; do
        clear
        echo "Audit Dashboard  (refreshing every ${WATCH_INTERVAL}s — Ctrl-C to stop)"
        echo ""
        _render
        echo ""
        echo "Last refresh: $(date '+%Y-%m-%d %H:%M:%S')"
        sleep "$WATCH_INTERVAL"
    done
else
    _render
fi
