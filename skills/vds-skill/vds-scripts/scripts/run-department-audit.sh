#!/usr/bin/env bash
# run-department-audit.sh — Department-wide audit launcher
#
# Discovers all projects in a department via vds-cli audit state, resolves
# checklist page IDs, and delegates to run-audit-in-tmux.sh with a single
# parent tmux session running workflow-projects.
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Usage:
#   ./scripts/run-department-audit.sh [options] <department-selector>
#
#   The department selector can be a name, Confluence page ID, or storage key.
#
# Options:
#   --checklist-page-id ID        Override checklist for all projects
#   --repos FILTER                Restrict repos within each project
#   --profiles LIST               Restrict LLM profiles
#   --max-concurrent N            Child-level concurrency (default: 16)
#   --max-projects-concurrent N   Parent-level project concurrency (default: 3)
#   --project-filter KEYS         Comma-separated project keys to include
#   --project-exclude KEYS        Comma-separated project keys to exclude
#   --stagger-seconds N           Delay between project launches (default: 5)
#   --log-dir DIR                 Log directory (default: /tmp)
#   --dry-run                     Print command without executing
#   --prepare-materials           Enable material preparation (default)
#   --skip-materials              Skip material preparation
#   --upload-to-confluence        Enable Confluence upload
#   --incremental-upload          Enable incremental upload
#
# Management:
#   --list                        List active department audit sessions
#   --kill DEPT                   Kill session matching dept-<DEPT>
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Examples:
#
#   # Launch audit for a department by name
#   ./scripts/run-department-audit.sh "3.2.4 Nền tảng thanh toán"
#
#   # Launch by page ID, override checklist, limit concurrency
#   ./scripts/run-department-audit.sh 88716700 \
#     --checklist-page-id 88722450 --max-projects-concurrent 2
#
#   # Dry run with project filter
#   ./scripts/run-department-audit.sh 88716700 \
#     --project-filter 88718943,88718977 --dry-run
#
#   # List active department sessions
#   ./scripts/run-department-audit.sh --list
#
#   # Kill a department session
#   ./scripts/run-department-audit.sh --kill 88716700
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./vds_sh_helpers.sh
source "$SCRIPT_DIR/vds_sh_helpers.sh"

ROOT="$(vds_resolve_scripts_root)"

# ── Defaults ─────────────────────────────────────────────────────────

LOG_DIR="/tmp"
DRY_RUN=false
CHECKLIST_PAGE_ID=""
REPOS_FILTER=""
PROFILES=""
MAX_CONCURRENT=16
MAX_PROJECTS_CONCURRENT=3
PROJECT_FILTER=""
PROJECT_EXCLUDE=""
STAGGER_SECONDS=5
PREPARE_MATERIALS=true
UPLOAD_TO_CONFLUENCE=false
INCREMENTAL_UPLOAD=false
DEPARTMENT_SELECTOR=""

# ── Slugify ──────────────────────────────────────────────────────────
# slugify — Convert a department name to a tmux-safe session slug.
#
# Lowercase, replace non-alphanumeric with hyphens, collapse multiples,
# strip leading/trailing hyphens.
#   "3.2.4 Nền tảng thanh toán" → "3-2-4-n-n-t-ng-thanh-to-n"
#   "88716700"                   → "88716700"
slugify() {
  local input="$1"
  printf '%s' "$input" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9]/-/g' \
    | sed 's/--*/-/g' \
    | sed 's/^-//; s/-$//'
}

# ── Management subcommands ───────────────────────────────────────────

_list_dept_sessions() {
  echo "Active department audit sessions:"
  local found=false
  while IFS= read -r name; do
    case "$name" in dept-*)
      local log=""
      for candidate in "${LOG_DIR}/audit-${name}.log" "/tmp/audit-${name}.log"; do
        [ -f "$candidate" ] && log="$candidate" && break
      done
      local info=""
      if [ -n "$log" ]; then
        local lines
        lines=$(wc -l < "$log" 2>/dev/null)
        info="  (log: ${lines} lines)"
      fi
      echo "  $name$info"
      found=true
      ;;
    esac
  done < <(tmux list-sessions -F '#{session_name}' 2>/dev/null || true)
  if [ "$found" = false ]; then
    echo "  (no department audit sessions found)"
  fi
}

_kill_dept_session() {
  local dept="$1"
  local session="dept-${dept}"
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux kill-session -t "$session"
    echo "Killed session: $session"
  else
    echo "No session named: $session"
  fi
}

# ── Option parsing ───────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --checklist-page-id)
      CHECKLIST_PAGE_ID="$2"; shift 2 ;;
    --repos)
      REPOS_FILTER="$2"; shift 2 ;;
    --profiles)
      PROFILES="$2"; shift 2 ;;
    --max-concurrent)
      MAX_CONCURRENT="$2"; shift 2 ;;
    --max-projects-concurrent)
      MAX_PROJECTS_CONCURRENT="$2"; shift 2 ;;
    --project-filter)
      PROJECT_FILTER="$2"; shift 2 ;;
    --project-exclude)
      PROJECT_EXCLUDE="$2"; shift 2 ;;
    --stagger-seconds)
      STAGGER_SECONDS="$2"; shift 2 ;;
    --log-dir)
      LOG_DIR="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    --prepare-materials)
      PREPARE_MATERIALS=true; shift ;;
    --skip-materials)
      PREPARE_MATERIALS=false; shift ;;
    --upload-to-confluence)
      UPLOAD_TO_CONFLUENCE=true; shift ;;
    --incremental-upload)
      INCREMENTAL_UPLOAD=true; shift ;;
    --list)
      _list_dept_sessions; exit 0 ;;
    --kill)
      _kill_dept_session "${2:?--kill requires department slug or ID}"
      exit 0 ;;
    -*)
      echo "Unknown option: $1" >&2; exit 1 ;;
    *)
      if [ -z "$DEPARTMENT_SELECTOR" ]; then
        DEPARTMENT_SELECTOR="$1"; shift
      else
        echo "Error: unexpected argument: $1" >&2; exit 1
      fi
      ;;
  esac
done

if [ -z "$DEPARTMENT_SELECTOR" ]; then
  echo "Error: department selector is required" >&2
  echo "Usage: $0 [options] <department-name|page-id|storage-key>" >&2
  exit 1
fi

# ── Project discovery (TSK-165.9) ────────────────────────────────────

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Discovering projects for department: $DEPARTMENT_SELECTOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Query ALL projects (no --department filter) because the SQL filter only
# matches the full Vietnamese department name.  We filter client-side below
# against department, department_page_id, and department_storage_key.
QUERY_OUTPUT="$(vds_uv_run_package audit_orchestrator \
  vds-cli audit --json-only state query-projects)"

# Parse project list and metadata from JSON output.
# The API returns {"result": [...], "status": "ok", ...}.
# Client-side filter: match DEPARTMENT_SELECTOR against department,
# department_page_id, or department_storage_key (case-insensitive, partial
# match for the department name field).
# Checklist resolution order:
#   1. metadata.checklist_page_id (if non-null)
#   2. metadata.checklist_profiles[0].page_ids[0] (if available)
PARSED="$(python3 -c "
import json, sys

selector = sys.argv[1]
sel_lower = selector.lower()

data = json.loads(sys.stdin.read())
projects = data.get('result', [])
if not isinstance(projects, list):
    projects = []

dept_name = ''
dept_storage_key = ''

for p in projects:
    # Match against three fields
    p_dept = str(p.get('department', ''))
    p_dept_page_id = str(p.get('department_page_id', ''))
    p_dept_skey = str(p.get('department_storage_key', ''))

    matched = False
    if sel_lower == p_dept_page_id.lower():
        matched = True
    elif sel_lower == p_dept_skey.lower():
        matched = True
    elif sel_lower in p_dept.lower():
        matched = True

    if not matched:
        continue

    # Capture department name / storage key from first match
    if not dept_name:
        dept_name = p_dept
    if not dept_storage_key:
        dept_storage_key = p_dept_skey

    key = str(p.get('project_storage_key', p.get('storage_key', p.get('key', ''))))
    name = p.get('project_name', p.get('name', ''))
    meta = p.get('metadata') or {}

    # Resolve checklist page ID
    cl_id = ''
    raw = meta.get('checklist_page_id')
    if raw:
        cl_id = str(raw)
    else:
        profiles = meta.get('checklist_profiles') or []
        if profiles:
            page_ids = profiles[0].get('page_ids') or []
            if page_ids:
                cl_id = str(page_ids[0])

    print(f'PROJECT={key}|{name}|{cl_id}')

# Emit department metadata for slug / display
print('DEPT_NAME=' + dept_name)
print('DEPT_STORAGE_KEY=' + dept_storage_key)
" "$DEPARTMENT_SELECTOR" <<< "$QUERY_OUTPUT")"

# Extract department name and storage key for slug
DEPT_NAME="$(echo "$PARSED" | grep '^DEPT_NAME=' | head -1 | sed 's/^DEPT_NAME=//')"
DEPT_STORAGE_KEY="$(echo "$PARSED" | grep '^DEPT_STORAGE_KEY=' | head -1 | sed 's/^DEPT_STORAGE_KEY=//')"
if [ -z "$DEPT_NAME" ]; then
  DEPT_NAME="$DEPARTMENT_SELECTOR"
fi

# Prefer the storage key for the slug (already ASCII-safe)
if [ -n "$DEPT_STORAGE_KEY" ]; then
  DEPT_SLUG="$DEPT_STORAGE_KEY"
else
  DEPT_SLUG="$(slugify "$DEPT_NAME")"
fi
SESSION_NAME="dept-${DEPT_SLUG}"

# Build arrays of discovered projects
declare -a PROJECT_KEYS=()
declare -a PROJECT_NAMES=()
declare -a PROJECT_CHECKLISTS=()

while IFS= read -r line; do
  [[ "$line" != PROJECT=* ]] && continue
  line="${line#PROJECT=}"
  IFS='|' read -r key name cl_id <<< "$line"
  PROJECT_KEYS+=("$key")
  PROJECT_NAMES+=("$name")
  PROJECT_CHECKLISTS+=("$cl_id")
done <<< "$PARSED"

if [ ${#PROJECT_KEYS[@]} -eq 0 ]; then
  echo "Error: no projects found for department: $DEPARTMENT_SELECTOR" >&2
  exit 1
fi

echo "  Found ${#PROJECT_KEYS[@]} project(s)"

# ── Apply project filters ────────────────────────────────────────────

declare -a FILTERED_KEYS=()
declare -a FILTERED_NAMES=()
declare -a FILTERED_CHECKLISTS=()

for i in "${!PROJECT_KEYS[@]}"; do
  key="${PROJECT_KEYS[$i]}"

  # --project-filter: include only matching keys
  if [ -n "$PROJECT_FILTER" ]; then
    if ! echo ",$PROJECT_FILTER," | grep -q ",$key,"; then
      continue
    fi
  fi

  # --project-exclude: skip matching keys
  if [ -n "$PROJECT_EXCLUDE" ]; then
    if echo ",$PROJECT_EXCLUDE," | grep -q ",$key,"; then
      continue
    fi
  fi

  FILTERED_KEYS+=("$key")
  FILTERED_NAMES+=("${PROJECT_NAMES[$i]}")
  FILTERED_CHECKLISTS+=("${PROJECT_CHECKLISTS[$i]}")
done

if [ ${#FILTERED_KEYS[@]} -eq 0 ]; then
  echo "Error: all projects excluded by filters" >&2
  echo "  --project-filter: ${PROJECT_FILTER:-<none>}" >&2
  echo "  --project-exclude: ${PROJECT_EXCLUDE:-<none>}" >&2
  exit 1
fi

echo "  After filters: ${#FILTERED_KEYS[@]} project(s)"

# ── Resolve checklist page IDs ───────────────────────────────────────

declare -a RESOLVED_CHECKLISTS=()
declare -a MISSING_CHECKLIST_PROJECTS=()

for i in "${!FILTERED_KEYS[@]}"; do
  if [ -n "$CHECKLIST_PAGE_ID" ]; then
    # Global override applies to all projects
    RESOLVED_CHECKLISTS+=("$CHECKLIST_PAGE_ID")
  elif [ -n "${FILTERED_CHECKLISTS[$i]}" ]; then
    # Per-project checklist from state metadata
    RESOLVED_CHECKLISTS+=("${FILTERED_CHECKLISTS[$i]}")
  else
    RESOLVED_CHECKLISTS+=("")
    MISSING_CHECKLIST_PROJECTS+=("${FILTERED_KEYS[$i]} (${FILTERED_NAMES[$i]})")
  fi
done

if [ ${#MISSING_CHECKLIST_PROJECTS[@]} -gt 0 ]; then
  echo "" >&2
  echo "Error: the following projects have no resolvable checklist page ID:" >&2
  for entry in "${MISSING_CHECKLIST_PROJECTS[@]}"; do
    echo "  - $entry" >&2
  done
  echo "" >&2
  echo "Provide --checklist-page-id to override, or ensure state metadata" >&2
  echo "contains either checklist_page_id or checklist_profiles[0].page_ids[0] for each project." >&2
  exit 1
fi

# ── Build CSV of project storage keys ────────────────────────────────

PROJECT_KEYS_CSV=""
for i in "${!FILTERED_KEYS[@]}"; do
  if [ -n "$PROJECT_KEYS_CSV" ]; then
    PROJECT_KEYS_CSV="${PROJECT_KEYS_CSV},${FILTERED_KEYS[$i]}"
  else
    PROJECT_KEYS_CSV="${FILTERED_KEYS[$i]}"
  fi
done

# Resolve a single checklist ID if all projects share the same one
COMMON_CHECKLIST=""
if [ -n "$CHECKLIST_PAGE_ID" ]; then
  COMMON_CHECKLIST="$CHECKLIST_PAGE_ID"
else
  # Check if all resolved checklists are the same
  all_same=true
  first="${RESOLVED_CHECKLISTS[0]}"
  for cl in "${RESOLVED_CHECKLISTS[@]}"; do
    if [ "$cl" != "$first" ]; then
      all_same=false
      break
    fi
  done
  if [ "$all_same" = true ] && [ -n "$first" ]; then
    COMMON_CHECKLIST="$first"
  fi
fi

# ── Parent launch (TSK-165.10) ───────────────────────────────────────

LOG_FILE="${LOG_DIR}/audit-${SESSION_NAME}.log"

# Build argument list for run-audit-in-tmux.sh
declare -a TMUX_ARGS=()
TMUX_ARGS+=("--log-dir" "$LOG_DIR")
if [ "$DRY_RUN" = true ]; then
  TMUX_ARGS+=("--dry-run")
fi
TMUX_ARGS+=("$SESSION_NAME")
TMUX_ARGS+=("workflow-projects")
TMUX_ARGS+=("--project-storage-keys" "$PROJECT_KEYS_CSV")

if [ -n "$COMMON_CHECKLIST" ]; then
  TMUX_ARGS+=("--checklist-page-id" "$COMMON_CHECKLIST")
fi

TMUX_ARGS+=("--max-projects-concurrent" "$MAX_PROJECTS_CONCURRENT")
TMUX_ARGS+=("--max-concurrent" "$MAX_CONCURRENT")

if [ -n "$PROFILES" ]; then
  TMUX_ARGS+=("--profiles" "$PROFILES")
fi

if [ -n "$REPOS_FILTER" ]; then
  TMUX_ARGS+=("--repos" "$REPOS_FILTER")
fi

if [ -n "$PROJECT_FILTER" ]; then
  TMUX_ARGS+=("--project-filter" "$PROJECT_FILTER")
fi

if [ -n "$PROJECT_EXCLUDE" ]; then
  TMUX_ARGS+=("--project-exclude" "$PROJECT_EXCLUDE")
fi

if [ "$PREPARE_MATERIALS" = true ]; then
  TMUX_ARGS+=("--prepare-materials")
else
  TMUX_ARGS+=("--skip-materials")
fi

if [ "$UPLOAD_TO_CONFLUENCE" = true ]; then
  TMUX_ARGS+=("--upload-to-confluence")
fi

if [ "$INCREMENTAL_UPLOAD" = true ]; then
  TMUX_ARGS+=("--incremental-upload")
fi

# ── Delegate to run-audit-in-tmux.sh ─────────────────────────────────

"$SCRIPT_DIR/run-audit-in-tmux.sh" "${TMUX_ARGS[@]}"

# ── Post-launch summary (TSK-165.20 partial) ─────────────────────────

if [ "$DRY_RUN" = true ]; then
  exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Department audit: $DEPT_NAME"
echo "  Session:          $SESSION_NAME"
echo "  Log:              $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Selected projects (${#FILTERED_KEYS[@]}):"
  for i in "${!FILTERED_KEYS[@]}"; do
    cl_info=""
    if [ -n "${RESOLVED_CHECKLISTS[$i]}" ]; then
      cl_info="  checklist=${RESOLVED_CHECKLISTS[$i]}"
    fi
    echo "    ${FILTERED_KEYS[$i]}  ${FILTERED_NAMES[$i]}${cl_info}"
  done
echo ""
echo "  Monitor:"
echo "    $0 --list"
echo "    $SCRIPT_DIR/run-audit-in-tmux.sh --status $SESSION_NAME"
echo "    tail -f $LOG_FILE"
echo "    tmux attach -t $SESSION_NAME"
echo ""
echo "  Control:"
echo "    $0 --kill $DEPT_SLUG"
echo "    $SCRIPT_DIR/run-audit-in-tmux.sh --kill $SESSION_NAME"
echo ""
echo "  # Resume interrupted run:"
echo "  #   ./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow-projects --resume --report-dir ~/.vds/cache/audit_runs/workflow-projects/<thread_id>"
echo ""
echo "  # Publish-only (if parent run completed but upload was skipped):"
echo "  #   vds-cli audit publish-project-run --resume-run <thread_id> --upload-to-confluence"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
