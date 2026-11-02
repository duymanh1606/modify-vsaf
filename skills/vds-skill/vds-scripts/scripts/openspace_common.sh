#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -n "${VDS_ENV_FILE:-}" ]]; then
  SHARED_ENV_PATH="$VDS_ENV_FILE"
else
  SHARED_ENV_PATH="$HOME/.vds/.env"
fi

load_shared_env() {
  if [[ -f "$SHARED_ENV_PATH" ]]; then
    set -a
    source "$SHARED_ENV_PATH"
    set +a
  fi
}

openspace_root() {
  printf '%s\n' "${OPENSPACE_WORKSPACE:-$PROJECT_ROOT}/.openspace"
}

openspace_db_path() {
  printf '%s/openspace.db\n' "$(openspace_root)"
}

openspace_shadow_skills_path() {
  printf '%s/shadow/skills\n' "$(openspace_root)"
}

canonical_skills_path() {
  if [[ -n "${VDS_SKILLS_PATH:-}" ]]; then
    printf '%s\n' "$VDS_SKILLS_PATH"
    return 0
  fi

  local repo_local="$PROJECT_ROOT/WHO-project/vds-skills/skills"
  local sibling_repo="$PROJECT_ROOT/../vds-skills/skills"
  local monorepo_sibling="$(cd "$PROJECT_ROOT/../../.." && pwd)/WHO-project/vds-skills/skills"

  for candidate in "$repo_local" "$sibling_repo" "$monorepo_sibling"; do
    if [[ -d "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  printf '%s\n' "$repo_local"
}

evolution_log_root() {
  printf '%s/.evolution-log\n' "$(openspace_root)"
}

openspace_mcp_cmd() {
  if command -v openspace-mcp >/dev/null 2>&1; then
    command -v openspace-mcp
    return 0
  fi
  if [[ -x "$PROJECT_ROOT/.venv/bin/openspace-mcp" ]]; then
    printf '%s\n' "$PROJECT_ROOT/.venv/bin/openspace-mcp"
    return 0
  fi
  return 1
}

official_openspace_repo_path() {
  printf '%s\n' "$PROJECT_ROOT/code/OpenSpace"
}

official_openspace_store_root() {
  printf '%s/.openspace\n' "$(official_openspace_repo_path)"
}
