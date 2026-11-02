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

STATUS=0

check() {
  local label="$1"
  local ok="$2"
  local detail="${3:-}"
  if [[ "$ok" == "1" ]]; then
    printf '[OK]   %s %s\n' "$label" "$detail"
  else
    printf '[FAIL] %s %s\n' "$label" "$detail"
    STATUS=1
  fi
}

check "shared env path" "$( [[ -f "$SHARED_ENV_PATH" ]] && echo 1 || echo 0 )" "$SHARED_ENV_PATH"
check "openspace root" "$( [[ -d "$OPENSPACE_ROOT" ]] && echo 1 || echo 0 )" "$OPENSPACE_ROOT"
check "openspace db" "$( [[ -f "$OPENSPACE_DB" ]] && echo 1 || echo 0 )" "$OPENSPACE_DB"
check "shadow skills dir" "$( [[ -d "$SHADOW_SKILLS" ]] && echo 1 || echo 0 )" "$SHADOW_SKILLS"
check "canonical skills dir" "$( [[ -d "$CANONICAL_SKILLS" ]] && echo 1 || echo 0 )" "$CANONICAL_SKILLS"
if OPENSPACE_MCP_BIN="$(openspace_mcp_cmd 2>/dev/null)"; then
  check "openspace-mcp available" "1" "$OPENSPACE_MCP_BIN"
else
  check "openspace-mcp available" "0" "not found on PATH or project .venv"
fi
check "autonomy disabled by default" "$( [[ "${OPENSPACE_AUTONOMOUS_ENABLED:-false}" == "false" ]] && echo 1 || echo 0 )" "value=${OPENSPACE_AUTONOMOUS_ENABLED:-unset}"

python3 - <<PY
from pathlib import Path
import sqlite3
p = Path(r'''$OPENSPACE_DB''')
if p.exists():
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print("db_tables:", ", ".join(tables) if tables else "<empty>")
    conn.close()
else:
    print("db_tables: <missing>")
shadow = Path(r'''$SHADOW_SKILLS''')
if shadow.exists():
    skills = [p.name for p in shadow.iterdir() if p.is_dir()]
    print("shadow_skill_count:", len(skills))
else:
    print("shadow_skill_count: <missing>")
PY

exit "$STATUS"
