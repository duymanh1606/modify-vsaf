#!/usr/bin/env bash
# vds_sh_helpers.sh — General-purpose helpers for VDS shell scripts.
#
# Provides workspace root resolution plus a canonical uv invocation contract for
# maintained shell scripts under WHO-project/vds-scripts.
#
# Canonical contract:
#   - resolve the vds-scripts workspace root
#   - invoke scripts/worktree_uv.sh
#   - bind the workspace explicitly with --directory <root> for non-root callers
#   - target uv packages by their [project].name value when using --package
#
# Callers may continue to pass workspace member directory names (e.g. vds_cli,
# markdown_orchestrator); this helper resolves those to uv project names.

set -euo pipefail

# ---------------------------------------------------------------------------
# vds_resolve_scripts_root
#
# Walk upward from this helper location until a pyproject.toml containing the
# vds-scripts workspace marker is found.
#
# Outputs the absolute path to the vds-scripts workspace root (no trailing /).
# ---------------------------------------------------------------------------
vds_resolve_scripts_root() {
  local dir candidate depth
  dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  candidate="$dir"
  depth=0

  while [[ "$candidate" != "/" && $depth -lt 20 ]]; do
    if [[ -f "$candidate/pyproject.toml" ]] && grep -q "vds-scripts-workspace" "$candidate/pyproject.toml" 2>/dev/null; then
      printf '%s\n' "$candidate"
      return 0
    fi
    candidate="$(dirname "$candidate")"
    (( depth++ )) || true
  done

  local fallback
  fallback="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  if [[ -f "$fallback/scripts/worktree_uv.sh" ]]; then
    printf '%s\n' "$fallback"
    return 0
  fi

  echo "vds_sh_helpers: cannot locate vds-scripts workspace root" >&2
  return 1
}

# ---------------------------------------------------------------------------
# resolve_insurance_docs_root [base]
#
# Locate the insurance-document directory, optionally relative to [base].
# Preserved for backward compatibility with scripts that already call it.
# ---------------------------------------------------------------------------
resolve_insurance_docs_root() {
  local base="${1:-$(vds_resolve_scripts_root)}"

  if [[ -n "${VDS_INSURANCE_DOCS_ROOT:-}" ]]; then
    printf '%s\n' "${VDS_INSURANCE_DOCS_ROOT}"
    return 0
  fi

  if [[ -d "$base/WHO-project/insurance-document" ]]; then
    printf '%s\n' "$base/WHO-project/insurance-document"
    return 0
  fi

  local match=""
  match="$(find "$base" -maxdepth 2 -type d -path "$base/*-project/insurance-document" 2>/dev/null | sort | head -n 1)"
  if [[ -n "$match" ]]; then
    printf '%s\n' "$match"
    return 0
  fi

  printf '%s\n' "$base/WHO-project/insurance-document"
}

# ---------------------------------------------------------------------------
# vds_uv_project_name <member-or-package>
#
# Resolve a workspace member directory name (e.g. vds_cli) to the uv package
# name declared in that member's pyproject.toml (e.g. vds-cli). If the input is
# already not a member directory, return it unchanged to allow explicit package
# names from callers.
#
# Intentionally avoids a host-Python/tomllib dependency so scripts remain
# portable across shells where `python3` may be older than 3.11.
# ---------------------------------------------------------------------------
vds_uv_project_name() {
  local member_or_package="${1:?vds_uv_project_name: member or package is required}"
  local root member_pyproject line
  root="$(vds_resolve_scripts_root)"
  member_pyproject="$root/$member_or_package/pyproject.toml"

  if [[ ! -f "$member_pyproject" ]]; then
    printf '%s\n' "$member_or_package"
    return 0
  fi

  line="$(awk '
    BEGIN { in_project = 0 }
    /^\[project\]/ { in_project = 1; next }
    /^\[/ && in_project { exit }
    in_project && $0 ~ /^[[:space:]]*name[[:space:]]*=/ { print; exit }
  ' "$member_pyproject")"

  if [[ -z "$line" ]]; then
    echo "vds_sh_helpers: missing [project].name in $member_pyproject" >&2
    return 1
  fi

  line="${line#*=}"
  line="$(printf '%s' "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  line="${line#\"}"
  line="${line%\"}"
  printf '%s\n' "$line"
}

# ---------------------------------------------------------------------------
# vds_worktree_uv <uv args...>
#
# Invoke scripts/worktree_uv.sh from the resolved workspace root.
# ---------------------------------------------------------------------------
vds_worktree_uv() {
  local root wrapper
  root="$(vds_resolve_scripts_root)"
  wrapper="$root/scripts/worktree_uv.sh"

  if [[ ! -x "$wrapper" ]]; then
    echo "vds_sh_helpers: worktree_uv.sh not found or not executable at $wrapper" >&2
    return 1
  fi

  "$wrapper" "$@"
}

# ---------------------------------------------------------------------------
# vds_uv_run_package <member-or-package> [command args...]
#
# Run a command from a workspace package through the worktree wrapper, binding
# the workspace explicitly with --directory for callers outside the root.
# ---------------------------------------------------------------------------
vds_uv_run_package() {
  local member_or_package="${1:?vds_uv_run_package: member or package is required}"
  shift
  local root package_name
  root="$(vds_resolve_scripts_root)"
  package_name="$(vds_uv_project_name "$member_or_package")"

  vds_worktree_uv run --directory "$root" --package "$package_name" "$@"
}

# ---------------------------------------------------------------------------
# vds_uv_sync_package <member-or-package> [extra uv sync args...]
#
# Sync a single workspace package.
# ---------------------------------------------------------------------------
vds_uv_sync_package() {
  local member_or_package="${1:?vds_uv_sync_package: member or package is required}"
  shift
  local root package_name
  root="$(vds_resolve_scripts_root)"
  package_name="$(vds_uv_project_name "$member_or_package")"

  vds_worktree_uv sync --directory "$root" --package "$package_name" "$@"
}

# ---------------------------------------------------------------------------
# vds_uv_sync_all [extra uv sync args...]
#
# Full workspace sync — syncs all members defined in the root pyproject.toml.
# ---------------------------------------------------------------------------
vds_uv_sync_all() {
  local root
  root="$(vds_resolve_scripts_root)"
  vds_worktree_uv sync --directory "$root" --all-packages "$@"
}
