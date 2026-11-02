#!/usr/bin/env bash
# Run uv in the current worktree without inheriting a mismatched active virtualenv.
# Usage: scripts/worktree_uv.sh <uv args...>

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKTREE_VENV="${ROOT}/.venv"
site_packages="$(echo "$WORKTREE_VENV"/lib/python*/site-packages)"

# uv project commands manage their own environment by default.
# If a parent checkout exported VIRTUAL_ENV from a different repo/worktree,
# uv will warn and ignore it. Clear inherited active-environment state so
# worktree commands are quiet and deterministic.
if [[ -n "${VIRTUAL_ENV:-}" && "${VIRTUAL_ENV}" != "${WORKTREE_VENV}" ]]; then
  unset VIRTUAL_ENV
fi

# Prevent a parent shell from forcing a different project environment.
unset UV_PROJECT_ENVIRONMENT
unset CONDA_PREFIX

# Worktree venvs in this repo rely on editable _vds_*.pth files. Rebuild
# PYTHONPATH from those stubs so uv-launched entrypoints resolve workspace
# packages consistently even when Python skips underscore-prefixed .pth files.
if [[ -d "$site_packages" ]]; then
  pythonpath_entries=()
  while IFS= read -r -d '' pth_file; do
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" ]] && continue
      pythonpath_entries+=("$line")
    done < "$pth_file"
  done < <(find "$site_packages" -maxdepth 1 -type f -name '_vds_*.pth' -print0 | sort -z)

  if [[ ${#pythonpath_entries[@]} -gt 0 ]]; then
    joined_pythonpath=""
    for entry in "${pythonpath_entries[@]}"; do
      if [[ -z "$joined_pythonpath" ]]; then
        joined_pythonpath="$entry"
      else
        joined_pythonpath="$joined_pythonpath:$entry"
      fi
    done
    export PYTHONPATH="$joined_pythonpath${PYTHONPATH:+:$PYTHONPATH}"
  fi
fi

# Hydrate missing runtime env from ~/.vds/.env so uv-launched Python and child
# shells see the same baseline config as CLI entrypoints. Preserve explicit shell
# overrides by only exporting keys that are currently unset.
bootstrap_python="${WORKTREE_VENV}/bin/python"
if [[ ! -x "$bootstrap_python" ]]; then
  bootstrap_python="$(command -v python3 || true)"
fi
if [[ -n "${bootstrap_python}" ]]; then
  if shared_env_exports="$(VDS_WORKTREE_UV_ROOT="$ROOT" "$bootstrap_python" - <<'PY' 2>/dev/null
import os
import sys
from pathlib import Path

root = Path(os.environ["VDS_WORKTREE_UV_ROOT"])
sys.path.insert(0, str(root / "vds_cli_common" / "src"))

from vds_cli_common.env import render_shared_env_exports

print(render_shared_env_exports(ensure_defaults=False))
PY
  )"; then
    if [[ -n "$shared_env_exports" ]]; then
      eval "$shared_env_exports"
    fi
  fi
fi

cd "$ROOT"

exec uv "$@"
