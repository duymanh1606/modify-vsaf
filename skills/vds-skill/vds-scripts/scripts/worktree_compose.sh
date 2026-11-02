#!/usr/bin/env bash
# VDS AI Memory — worktree-safe Docker-Compose wrapper (VAMI-013 / Phase 176).
#
# Analogue of scripts/worktree_uv.sh for Docker Compose. Detects mainline vs
# worktree, auto-copies memory_orchestrator/.env from mainline when missing,
# pins compose --project-directory to the worktree's memory_orchestrator/, and
# forces compose project identity "vds-ai-memory" so named volumes reattach
# across worktree switches.
#
# Usage:
#   scripts/worktree_compose.sh up [--force]
#   scripts/worktree_compose.sh down
#   scripts/worktree_compose.sh restart
#   scripts/worktree_compose.sh logs [service...]
#   scripts/worktree_compose.sh ps
#   scripts/worktree_compose.sh <anything-else>    # pass-through
#
# Env:
#   VDS_MAIN_WORKTREE  Explicit mainline path override (ADR-6).
#   COMPOSE_PROFILES   Comma-list of profiles (dev|prod|mem0|full).
#
# Exit codes:
#   0   success
#   1   usage error
#   2   safety refusal (missing .env, bind-mount mismatch)
#   >2  docker compose exit code

set -euo pipefail

PROJECT_NAME="vds-ai-memory"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MEMORY_DIR="${REPO_ROOT}/memory_orchestrator"

# ──────────────────────────────────────────────────────────────
# Detection
# ──────────────────────────────────────────────────────────────

detect_mode() {
  # Compare git-dir (per-worktree) vs git-common-dir (shared). They differ
  # inside a worktree, match inside the primary checkout.
  local git_dir git_common
  git_dir="$(git -C "${REPO_ROOT}" rev-parse --absolute-git-dir 2>/dev/null || echo "")"
  git_common="$(git -C "${REPO_ROOT}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo "")"
  if [[ -z "${git_dir}" || -z "${git_common}" ]]; then
    echo "mainline"  # not a git checkout; treat as mainline
    return
  fi
  if [[ "${git_dir}" == "${git_common}" ]]; then
    echo "mainline"
  else
    echo "worktree"
  fi
}

resolve_mainline() {
  # Return the filesystem path of the primary (non-bare, non-locked) worktree.
  # Priority: VDS_MAIN_WORKTREE env override > first entry in `git worktree
  # list --porcelain` whose `bare` flag is absent and which is not listed as
  # locked with a path different from REPO_ROOT.
  if [[ -n "${VDS_MAIN_WORKTREE:-}" ]]; then
    echo "${VDS_MAIN_WORKTREE}"
    return
  fi
  local line path_line bare_line
  path_line=""
  while IFS= read -r line; do
    if [[ "${line}" == worktree\ * ]]; then
      path_line="${line#worktree }"
      bare_line=""
    elif [[ "${line}" == "bare" ]]; then
      bare_line="yes"
    elif [[ -z "${line}" ]]; then
      # record terminator — emit if this is the first non-bare one
      if [[ -n "${path_line}" && -z "${bare_line}" ]]; then
        # The primary worktree is the one whose git-dir has no `gitdir` file
        # (i.e., its .git is a real directory, not a pointer).
        if [[ -d "${path_line}/.git" ]]; then
          echo "${path_line}"
          return
        fi
      fi
      path_line=""
      bare_line=""
    fi
  done < <(git -C "${REPO_ROOT}" worktree list --porcelain 2>/dev/null; echo "")
  # Fallback: guess by convention (WHO-project/vds-scripts sibling of
  # worktrees/<branch>). Not authoritative — user should set VDS_MAIN_WORKTREE.
  local guess="${REPO_ROOT%/worktrees/*}"
  if [[ "${guess}" != "${REPO_ROOT}" && -d "${guess}/.git" ]]; then
    # guess is e.g. .../WHO-project (parent of worktrees/). Walk one level
    # down to vds-scripts.
    if [[ -d "${guess}/vds-scripts/.git" ]]; then
      echo "${guess}/vds-scripts"
      return
    fi
  fi
  echo ""  # unresolved — caller must handle
}

resolve_memory_dir() {
  echo "${MEMORY_DIR}"
}

# ──────────────────────────────────────────────────────────────
# .env handling (T-A3)
# ──────────────────────────────────────────────────────────────

ensure_env_file() {
  local mode="$1"
  local env_file="${MEMORY_DIR}/.env"
  if [[ -f "${env_file}" ]]; then
    ENV_SOURCE="${env_file} (already present)"
    return
  fi
  if [[ "${mode}" == "mainline" ]]; then
    echo "error: ${env_file} is missing on mainline; cannot bootstrap" >&2
    exit 2
  fi
  local mainline
  mainline="$(resolve_mainline)"
  if [[ -z "${mainline}" ]]; then
    echo "error: cannot locate mainline worktree. Set VDS_MAIN_WORKTREE." >&2
    exit 2
  fi
  local src="${mainline}/memory_orchestrator/.env"
  if [[ ! -f "${src}" ]]; then
    echo "error: mainline .env not found at ${src}" >&2
    exit 2
  fi
  # FR-6: never write to mainline. We only READ src and copy INTO worktree.
  cp "${src}" "${env_file}"
  ENV_SOURCE="copied from ${src}"
}

# ──────────────────────────────────────────────────────────────
# Bind-mount mismatch guard (T-A2, FR-5)
# ──────────────────────────────────────────────────────────────

check_bind_mount_mismatch() {
  local force="$1"
  # Inspect the currently-running `vds-ai-memory` compose project (if any).
  # If its ConfigFiles points to a different memory_orchestrator/compose.yaml
  # than ours, refuse to `up`.
  local json
  if ! json="$(docker compose ls --all --format json 2>/dev/null)"; then
    return 0  # docker unavailable — let the subsequent command fail naturally
  fi
  # Cheap parsing: look for a project named vds-ai-memory
  local match
  match="$(printf '%s\n' "${json}" \
    | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '[]')
except json.JSONDecodeError:
    sys.exit(0)
for entry in data if isinstance(data, list) else []:
    name = entry.get('Name') or entry.get('name')
    if name == 'vds-ai-memory':
        print(entry.get('ConfigFiles') or entry.get('configFiles') or '')
        break
" 2>/dev/null || echo "")"
  if [[ -z "${match}" ]]; then
    return 0  # no running project to conflict with
  fi
  local our="${MEMORY_DIR}/compose.yaml"
  if [[ "${match}" != *"${our}"* ]]; then
    if [[ "${force}" == "yes" ]]; then
      echo "warning: vds-ai-memory already running from '${match}'; --force overrides the guard" >&2
      return 0
    fi
    echo "error: compose project 'vds-ai-memory' is already running from a different tree:" >&2
    echo "       ${match}" >&2
    echo "       run 'scripts/worktree_compose.sh down' in that tree first, or pass --force." >&2
    exit 2
  fi
}

# ──────────────────────────────────────────────────────────────
# Pre-flight (T-A1 / FR-3)
# ──────────────────────────────────────────────────────────────

print_preflight() {
  local mode="$1"
  local subcommand="$2"
  echo "=== worktree_compose.sh pre-flight ==="
  echo "  mode             : ${mode}"
  echo "  repo_root        : ${REPO_ROOT}"
  echo "  memory_dir       : ${MEMORY_DIR}"
  echo "  compose_project  : ${PROJECT_NAME}"
  echo "  env_source       : ${ENV_SOURCE:-<not resolved>}"
  echo "  compose_profiles : ${COMPOSE_PROFILES:-<none>}"
  echo "  subcommand       : ${subcommand}"
  if [[ "${mode}" == "worktree" ]]; then
    echo "  mainline         : $(resolve_mainline || echo '<unresolved>')"
  fi
  echo "======================================="
}

# ──────────────────────────────────────────────────────────────
# Dispatch (T-A4)
# ──────────────────────────────────────────────────────────────

compose() {
  # All subcommands go through this single entry so --project-directory and -p
  # are applied consistently.
  docker compose \
    --project-directory "${MEMORY_DIR}" \
    -p "${PROJECT_NAME}" \
    "$@"
}

usage() {
  sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

main() {
  local subcommand="${1:-}"
  if [[ -z "${subcommand}" || "${subcommand}" == "-h" || "${subcommand}" == "--help" ]]; then
    usage
    exit 0
  fi
  shift

  local mode
  mode="$(detect_mode)"

  # --force is only meaningful for `up`.
  local force="no"
  local -a rest=()
  for arg in "$@"; do
    case "${arg}" in
      --force) force="yes" ;;
      *)       rest+=("${arg}") ;;
    esac
  done

  ensure_env_file "${mode}"

  case "${subcommand}" in
    up)
      check_bind_mount_mismatch "${force}"
      print_preflight "${mode}" "up"
      compose up -d "${rest[@]+"${rest[@]}"}"
      ;;
    down)
      print_preflight "${mode}" "down"
      compose down "${rest[@]+"${rest[@]}"}"
      ;;
    restart)
      print_preflight "${mode}" "restart"
      compose restart "${rest[@]+"${rest[@]}"}"
      ;;
    logs)
      compose logs "${rest[@]+"${rest[@]}"}"
      ;;
    ps)
      compose ps "${rest[@]+"${rest[@]}"}"
      ;;
    *)
      # Pass-through: unknown subcommand is forwarded verbatim.
      print_preflight "${mode}" "${subcommand} (pass-through)"
      compose "${subcommand}" "${rest[@]+"${rest[@]}"}"
      ;;
  esac
}

main "$@"
