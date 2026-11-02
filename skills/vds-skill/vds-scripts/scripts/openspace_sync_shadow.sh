#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/openspace_common.sh
source "$SCRIPT_DIR/openspace_common.sh"

load_shared_env

SHADOW_SKILLS="$(openspace_shadow_skills_path)"
CANONICAL_SKILLS="$(canonical_skills_path)"

mkdir -p "$SHADOW_SKILLS"

if [[ ! -d "$CANONICAL_SKILLS" ]]; then
  echo "canonical skills dir missing: $CANONICAL_SKILLS" >&2
  exit 1
fi

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "$CANONICAL_SKILLS/" "$SHADOW_SKILLS/"
else
  rm -rf "$SHADOW_SKILLS"
  mkdir -p "$SHADOW_SKILLS"
  cp -R "$CANONICAL_SKILLS/." "$SHADOW_SKILLS/"
fi

echo "shadow skills synced"
echo "  canonical: $CANONICAL_SKILLS"
echo "  shadow:    $SHADOW_SKILLS"

# Sync skills to OpenSpace database (optional, skip if openspace not available)
OPENSSPACE_REPO="${OPENSPACE_REPO:-$(official_openspace_repo_path)}"
if [[ -x "$PROJECT_ROOT/.venv/bin/python" && -d "$OPENSSPACE_REPO" ]]; then
  set -a
  source "$SHARED_ENV_PATH" 2>/dev/null || true
  set +a

  # Use openspace-mcp wrapper which has proper PYTHONPATH
  : "${PYTHONPATH:-}"
  PYTHONPATH="$OPENSSPACE_REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$PROJECT_ROOT/.venv/bin/python" - <<'PY'
import sys
import asyncio
import os

# Ensure OpenSpace is importable - use env var or detect
openspace_repo = os.environ.get("OPENSPACE_REPO", "")
if openspace_repo and openspace_repo not in sys.path:
    sys.path.insert(0, openspace_repo)

try:
    from openspace.mcp_server import _get_local_skill_registry, _get_store

    registry = _get_local_skill_registry()
    store = _get_store()
    all_skills = registry.list_skills()
    created = asyncio.run(store.sync_from_registry(all_skills)) if all_skills else 0
    print(f"db skill sync complete: registry={len(all_skills)} created={created}")
except ImportError as e:
    print(f"db skill sync skipped: {e}")
except Exception as e:
    print(f"db skill sync warning: {e}")
PY
fi
