# Scripts UV Workspace Alignment Verification Note

Date: 2026-03-25
Branch: `feat/scripts-uv-workspace-alignment`
Scope: helper/bootstrap/script-shell alignment for `WHO-project/vds-scripts/scripts/`

## Summary

This note records the bounded verification run for the current implementation lane.
The purpose is to prove that the updated shell contract works across the main
contexts called out by the spec:

- clean shell execution
- polluted parent environment execution
- non-standard nested caller path execution

It also records one helper portability fix discovered during verification.

## Verified contract

The current intended contract is:

- maintained scripts use `scripts/worktree_uv.sh` through `scripts/vds_sh_helpers.sh`
- helper-driven invocations bind the workspace explicitly with `--directory <vds-scripts-root>`
- helper-driven package targeting resolves workspace member directories to uv project names for `--package`
- canonical integrated bootstrap assumes Python 3.14+

## Three-context regression matrix

### Context 1 — clean shell

Command class verified:
- helper-driven spec package help surface

Observed result:
- passed

Notes:
- `vds_uv_run_package spec_orchestrator vds-spec --help` succeeded from the implementation worktree with no inherited environment state.

### Context 2 — polluted parent environment

Command class verified:
- helper-driven routed CLI command with fake parent environment values

Injected environment:
- `VIRTUAL_ENV=/tmp/fake-venv`
- `UV_PROJECT_ENVIRONMENT=/tmp/fake-project-env`
- `CONDA_PREFIX=/tmp/fake-conda`

Observed result:
- passed

Notes:
- `vds_uv_run_package vds_cli vds-cli doctor` succeeded.
- The wrapper/helper path remained functional despite the polluted parent environment.

### Context 3 — non-standard nested caller path

Command class verified:
- targeted sync helper script launched from `scripts/target-state-automation/`

Observed result:
- passed

Notes:
- `UV_SYNC_FLAGS=--dry-run ./update_dependencies.sh` succeeded when launched from the nested target-state-automation directory.
- This confirms root resolution and wrapper binding do not depend on the older hardcoded 4-level traversal pattern.

## Additional bounded verification already passed in this lane

Previously verified in this worktree:

- helper-driven `vds-spec --help`
- helper-driven `vds-cli status`
- helper-driven `vds-cli doctor`
- helper-driven `vds-markdown --help`
- targeted bootstrap dry-run
- full bootstrap dry-run
- updated shell scripts syntax-check cleanly

## Helper portability fix discovered during verification

### Issue

The initial helper implementation used host `python3` plus `tomllib` to resolve
workspace member directory names to uv package names.

That failed in a shell path where `python3` did not provide `tomllib`.

### Fix

The helper was updated to parse `[project].name` from member `pyproject.toml`
using shell/awk logic instead of host Python.

### Outcome

Package-name resolution no longer depends on a host Python 3.11+ runtime just to
run the shell helper layer.

## Known follow-up outside helper-layer closure

### `scripts/target-state-automation/validate_schemas.sh`

The script now routes through the helper correctly, but the underlying schema
command shape appears stale relative to the current `vds-cli schema` /
`vds-schema-convert` compatibility surface.

The script has therefore been updated to fail explicitly and truthfully with a
clear follow-up message instead of forwarding operators into a stale command and
producing a confusing CLI option error.

This remains classified as:
- schema-command drift follow-up
- not a helper-layer regression

## Closure assessment for this lane

For the shell/uv alignment scope covered by this branch:
- helper consolidation: complete
- bootstrap alignment: complete
- maintained script migration in scope: complete
- docs alignment in scope: complete
- three-context regression matrix: complete

This branch is ready for review/merge for the intended helper/bootstrap/docs
alignment scope, with `validate_schemas.sh` command-surface drift explicitly
left as separate follow-up work.
