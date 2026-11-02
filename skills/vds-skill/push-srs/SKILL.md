---
name: vds-skill-push-srs
description: Push SRS markdown to Viettel Confluence via vds-cli. Same flow as push-prd plus link to the corresponding PRD page. Use after /sdlc-srs has produced 05-srs.md. Viettel-only (requires vds-cli).
---

# /vds-skill-push-srs

Publish the current SRS to Viettel Confluence via `vds-cli` — create or update the page, and link to the corresponding PRD page if it exists.

## Input

- `[file]` — optional path to a specific markdown file. Default: scan `.vsaf/docs/features/*/05-srs.md`
- `[comment]` — optional version note

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
[[ -z "${VDS_CONFLUENCE_SPACE_DEFAULT:-}" ]] && MISSING="$MISSING VDS_CONFLUENCE_SPACE_DEFAULT"
if [[ -n "$MISSING" ]]; then
  echo "BLOCKED — missing:$MISSING"
  echo "Fix: edit ~/.vds/sdlc-config.env (or run: vsaf install vds-skill)"
else
  echo "OK"
fi
```

If BLOCKED: tell the user exactly what's missing and how to fix, then STOP. Do NOT fabricate output.

## Prerequisites

- `vds-cli` installed
- An SRS markdown file must exist
- `VDS_CONFLUENCE_TOKEN` + `VDS_CONFLUENCE_SPACE_DEFAULT` in `~/.vds/sdlc-config.env`
- Confluence parent page in config or lazy-prompted

## Steps

### Step 1 — Find SRS file

- If `[file]` given: use directly
- Otherwise: list `.vsaf/docs/features/*/05-srs.md` (exclude `*-results.md`)
- Multiple: ask user
- None: STOP — tell user to run `/sdlc-srs` first
- Read full content

### Step 2 — Load Confluence config

Same as `/vds-skill-push-prd` Step 2.

### Step 3 — Determine page title

- For `05-srs.md` under `features/{feature-name}/`: title = `[SRS] {Feature Name}` (derived from folder name)
- Otherwise: first `# Heading` or filename stem

### Step 4 — Convert markdown → Confluence storage format (XHTML)

Same conversion rules as `/vds-skill-push-prd` Step 4 (see that skill for full reference). Save converted body to `$BODY_FILE`.

### Step 5 — Search for existing page

Same as `/vds-skill-push-prd` Step 5 — search for `[SRS] {Feature Name}` page in the space, store `EXISTING_PAGE_ID` and `SEARCH_RESULT`.

### Step 6 — Update existing page (via vds-cli)

Same as `/vds-skill-push-prd` Step 6 (with auto-retry on conflict). Use `Updated via vds-skill-push-srs` as default version comment.

### Step 7 — Create new page (via vds-cli)

Same as `/vds-skill-push-prd` Step 7. Use `Initial SRS push via vds-skill-push-srs` as default version comment.

### Step 8 — Link SRS page to PRD page (if PRD exists)

```bash
source .claude/skills/_shared/vds-skill/credentials.sh
ensure_env VDS_CONFLUENCE_TOKEN "Enter VDS Confluence personal access token"

# Derive PRD page title from feature name
FEATURE_NAME="<from folder>"
PRD_TITLE="[PRD] $FEATURE_NAME"

PRD_PAGE=$(vds-cli confluence search \
    --cql "space=$SPACE_KEY AND title = \"$PRD_TITLE\"" \
    --limit 1 --json-only)

PRD_URL=$(echo "$PRD_PAGE" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); r=d.get("results"); print(r[0].get("url","") if r else "")')

if [[ -n "$PRD_URL" ]]; then
    # Prepend "Related Documents" macro to SRS body BEFORE push (modify $BODY_FILE)
    RELATED_BLOCK='<ac:structured-macro ac:name="info"><ac:parameter ac:name="title">Related Documents</ac:parameter><ac:rich-text-body><p><a href="'"$PRD_URL"'">'"$PRD_TITLE"'</a></p></ac:rich-text-body></ac:structured-macro>'

    NEW_BODY=$(mktemp --suffix=.html)
    { echo "$RELATED_BLOCK"; cat "$BODY_FILE"; } > "$NEW_BODY"
    mv "$NEW_BODY" "$BODY_FILE"
fi
```

This block runs BEFORE Step 6/7 actually executes the create/update — i.e., the Related Documents banner is part of the body content pushed to Confluence.

### Step 9 — Output to user

```
## SRS pushed to Confluence

- Page:     {page_title}
- Action:   [Created / Updated]
- Space:    {space_key}
- Comment:  {comment}
- URL:      {confluence_page_url}
- PRD link: [linked / not found]

## Next step
Continue to Phase 5: /sdlc-test-design
```

## Notes

- If `vds-cli` is not installed, tell user to install vds-scripts first
- Do not modify the local file during this step
- SRS result files (`*-results.md`) are test outputs — push those separately if needed
- Conflict handling: version mismatch → auto-retry once with fresh version number
- PRD link is best-effort — if PRD page doesn't exist in Confluence yet, SRS pushes without the link
