---
name: vds-skill-create-jira-epic
description: Create a Jira Epic via `vds-cli jira create --issuetype Epic` from a PRD file. Use after /sdlc-prd has produced 02-prd.md. Auto-detects PRD location, lazy-prompts credentials. Viettel-only (requires vds-cli).
---

# /vds-skill-create-jira-epic

Create a Jira Epic on Viettel Jira based on a PRD markdown file.

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
[[ -z "${VDS_JIRA_TOKEN:-}" ]] && MISSING="$MISSING VDS_JIRA_TOKEN"
[[ -z "${VDS_JIRA_PROJECT_DEFAULT:-}" ]] && MISSING="$MISSING VDS_JIRA_PROJECT_DEFAULT"
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
- `python3` installed
- A PRD file exists at `.vsaf/docs/features/{feature}/02-prd.md`
- `VDS_JIRA_TOKEN` + `VDS_JIRA_PROJECT_DEFAULT` in `~/.vds/sdlc-config.env`

## Usage

```bash
/vds-skill-create-jira-epic                                  # auto-detect latest PRD
/vds-skill-create-jira-epic --feature user-management        # specific feature folder
/vds-skill-create-jira-epic --project NTTC                   # override project key
/vds-skill-create-jira-epic --dry-run                        # preview
/vds-skill-create-jira-epic --description-file path/to.md    # custom description source
```

## Behavior

1. Locate PRD file (or use `--description-file`)
2. Extract summary from PRD's first H1 heading
3. Lazy-prompt `VDS_JIRA_TOKEN` + `VDS_JIRA_PROJECT_DEFAULT` if missing
4. Confirm with user
5. Run `vds-cli jira create --project KEY --issuetype Epic --summary ... --description-file ... --yes --json-only`
6. Save returned epic key to `<feature-dir>/jira-epic-key.txt`

## Implementation

```bash
bash .claude/skills/vds-skill-create-jira-epic/scripts/create-epic.sh "$@"
```

## Notes

- Dry-run prints constructed `vds-cli` command without executing
- Dry-run skips `vds-cli` availability check — works on machines without vds-cli installed
- Epic key written to `<feature-dir>/jira-epic-key.txt` for later cross-reference
