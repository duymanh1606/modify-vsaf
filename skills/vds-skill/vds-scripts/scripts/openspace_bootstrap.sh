#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/openspace_common.sh
source "$SCRIPT_DIR/openspace_common.sh"

load_shared_env

OPENSPACE_ROOT="$(openspace_root)"
OPENSPACE_DB="$(openspace_db_path)"
SHADOW_SKILLS="$(openspace_shadow_skills_path)"
CANONICAL_SKILLS="$(canonical_skills_path)"
OFFICIAL_REPO="$(official_openspace_repo_path)"
OFFICIAL_STORE_ROOT="$(official_openspace_store_root)"

mkdir -p "$OPENSPACE_ROOT" "$SHADOW_SKILLS"

if [[ -d "$OFFICIAL_REPO" ]]; then
  if [[ -L "$OFFICIAL_STORE_ROOT" ]]; then
    :
  elif [[ -d "$OFFICIAL_STORE_ROOT" ]]; then
    rm -rf "$OFFICIAL_STORE_ROOT"
    ln -s "$OPENSPACE_ROOT" "$OFFICIAL_STORE_ROOT"
  elif [[ ! -e "$OFFICIAL_STORE_ROOT" ]]; then
    ln -s "$OPENSPACE_ROOT" "$OFFICIAL_STORE_ROOT"
  fi
fi

if [[ ! -f "$OPENSPACE_DB" ]]; then
  python3 - <<PY
import sqlite3
path = r'''$OPENSPACE_DB'''
conn = sqlite3.connect(path)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
conn.close()
print(f"initialized sqlite db: {path}")
PY
fi

echo "OpenSpace bootstrap complete"
echo "  shared env:      $SHARED_ENV_PATH"
echo "  workspace root:  ${OPENSPACE_WORKSPACE:-$PROJECT_ROOT}"
echo "  openspace root:  $OPENSPACE_ROOT"
echo "  sqlite db:       $OPENSPACE_DB"
echo "  shadow skills:   $SHADOW_SKILLS"
echo "  canonical skills:$CANONICAL_SKILLS"
echo "  autonomy:        ${OPENSPACE_AUTONOMOUS_ENABLED:-false}"

echo
echo "Recommended shared env entries:"
echo "OPENSPACE_WORKSPACE=${OPENSPACE_WORKSPACE:-$PROJECT_ROOT}"
echo "OPENSPACE_HOST_SKILL_DIRS=${OPENSPACE_HOST_SKILL_DIRS:-$SHADOW_SKILLS}"
echo "OPENSPACE_TRANSPORT=${OPENSPACE_TRANSPORT:-stdio}"
echo "OPENSPACE_AUTONOMOUS_ENABLED=${OPENSPACE_AUTONOMOUS_ENABLED:-false}"
