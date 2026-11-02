---
name: vds-skill-create-bitbucket-pr
description: Create a Bitbucket PR via `vds-cli bitbucket pr create`. Auto-extracts PROJECT/REPO from `git remote get-url origin`. Viettel-only — for GitHub use `gh pr create`. Run after /sdlc-ship when remote is bitbucket.digital.vn.
---

# /vds-skill-create-bitbucket-pr

Create a Bitbucket PR on Viettel internal Bitbucket via `vds-cli`.

## Config Check (run FIRST)

Before doing anything, run this check via Bash tool:

```bash
source .claude/skills/_shared/vds-skill/credentials.sh 2>/dev/null
MISSING=""
[[ -x .claude/bin/vds-cli ]] && export PATH=".claude/bin:$PATH"
if ! vds-cli --version >/dev/null 2>&1; then
  MISSING="$MISSING vds-cli"
  VDS_PATH=$(command -v vds-cli 2>/dev/null)
  if [[ -n "$VDS_PATH" ]]; then
    echo "NOTE: $VDS_PATH exists but fails to run (broken shim or missing venv)"
  fi
fi
[[ -z "${VDS_BITBUCKET_TOKEN:-}" ]] && MISSING="$MISSING VDS_BITBUCKET_TOKEN"
if [[ -n "$MISSING" ]]; then
  echo "BLOCKED — missing:$MISSING"
  echo "Fix: edit ~/.vds/sdlc-config.env (or run: vsaf install vds-skill)"
else
  echo "OK"
fi
```

If BLOCKED: tell the user exactly what's missing and how to fix, then STOP. Do NOT fabricate output. `--dry-run` mode skips credential + vds-cli checks.

## Prerequisites

- `vds-cli` installed (for non-dry-run)
- Inside a git repo with remote pointing to `bitbucket.digital.vn`
- On a named branch (not detached HEAD)
- `VDS_BITBUCKET_TOKEN` in `~/.vds/sdlc-config.env`

## Usage

```bash
/vds-skill-create-bitbucket-pr                          # interactive, target=master
/vds-skill-create-bitbucket-pr --target develop          # different target
/vds-skill-create-bitbucket-pr --dry-run                 # preview without executing
/vds-skill-create-bitbucket-pr --description-file FILE   # custom description
/vds-skill-create-bitbucket-pr --title "Custom title"
```

## Behavior

1. Verify remote URL matches `bitbucket.digital.vn` — abort if not
2. Extract PROJECT/REPO from remote URL
3. Determine source branch (current) + target (default `master`)
4. Auto-detect description from `.vsaf/docs/features/*/09-ship.md` or `.vsaf/docs/hotfixes/*/03-ship.md`
5. Lazy-prompt `VDS_BITBUCKET_TOKEN` if not set
6. Confirm with user before executing
7. Run `vds-cli bitbucket pr create $PROJECT/$REPO --source ... --target ... --title ... --description-file ... --yes --json-only`

## Implementation

```bash
bash .claude/skills/vds-skill-create-bitbucket-pr/scripts/create-pr.sh "$@"
```

## Notes

- For GitHub repos: use `gh pr create` instead (already standard in `/sdlc-ship`).
- PR description defaults to the latest ship report from `.vsaf/docs/`.
- Dry-run works without `vds-cli` installed (preview mode).
