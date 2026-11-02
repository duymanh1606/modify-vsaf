---
name: vds-skill-search-confluence
description: Search Viettel Confluence + Jira for historical context related to a feature, write index to .vsaf/docs/features/{name}/01-discovery-historical.{md,json}. Run BEFORE /sdlc-discovery to enrich grill session context. Viettel-only (requires vds-cli).
---

# /vds-skill-search-confluence

Search Viettel Confluence + Jira for pages/tickets related to a feature, then write a Markdown + JSON index into the feature folder. Output is consumed by `/sdlc-discovery` (Phase 1) to enrich the grill session.

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
[[ -z "${VDS_CONFLUENCE_TOKEN:-}" ]] && MISSING="$MISSING VDS_CONFLUENCE_TOKEN"
[[ -z "${VDS_JIRA_TOKEN:-}" ]] && MISSING="$MISSING VDS_JIRA_TOKEN"
[[ -z "${VDS_CONFLUENCE_SPACE_DEFAULT:-}" ]] && MISSING="$MISSING VDS_CONFLUENCE_SPACE_DEFAULT"
[[ -z "${VDS_JIRA_PROJECT_DEFAULT:-}" ]] && MISSING="$MISSING VDS_JIRA_PROJECT_DEFAULT"
if [[ -n "$MISSING" ]]; then
  echo "BLOCKED — missing:$MISSING"
  echo "Fix: edit ~/.vds/sdlc-config.env (or run: vsaf install vds-skill)"
else
  echo "OK"
fi
```

If BLOCKED: tell the user exactly what's missing and how to fix, then STOP. Do NOT fabricate output. `--dry-run` mode skips vds-cli check.

## Prerequisites

- `vds-cli` installed
- `python3` installed
- Inside a project root with `.vsaf/docs/features/`
- `VDS_CONFLUENCE_TOKEN`, `VDS_JIRA_TOKEN`, `VDS_CONFLUENCE_SPACE_DEFAULT`, `VDS_JIRA_PROJECT_DEFAULT` in `~/.vds/sdlc-config.env`

## Usage

```bash
/vds-skill-search-confluence --feature user-management --query "auth jwt"
/vds-skill-search-confluence --feature payment --query "payment flow" --days 90 --limit 50
/vds-skill-search-confluence --feature billing --query "billing" --dry-run
```

## Behavior

1. Build CQL: `space=<DEFAULT> AND text ~ "<QUERY>" AND lastmodified > now("-Nd")`
2. Build JQL: `project = <DEFAULT> AND text ~ "<QUERY>" AND created > -Nd ORDER BY created DESC`
3. Execute `vds-cli confluence search` + `vds-cli jira search` (sequential)
4. Combine into JSON at `<feature-dir>/01-discovery-historical.json`
5. Generate Markdown summary at `<feature-dir>/01-discovery-historical.md` (top 10 Confluence + top 15 Jira)

## Implementation

```bash
bash .claude/skills/vds-skill-search-confluence/scripts/search.sh "$@"
```

## Notes

- Run BEFORE `/sdlc-discovery` to enrich grill session.
- Default `--days 180`, `--limit 30`.
- Empty results are OK — Markdown still generated, sdlc-discovery proceeds normally.
- Dry-run skips `vds-cli` invocation — preview mode works without `vds-cli` installed.
