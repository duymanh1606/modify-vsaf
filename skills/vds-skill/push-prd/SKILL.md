---
name: vds-skill-push-prd
description: Push PRD markdown to Viettel Confluence via vds-cli. Converts markdown → Confluence Storage Format (XHTML), searches for existing page, creates or updates. Use after /sdlc-prd has produced 02-prd.md. Viettel-only (requires vds-cli).
---

# /vds-skill-push-prd

Publish the current PRD to Viettel Confluence via `vds-cli` — create a new page if it doesn't exist, or update the existing one. The optional `[comment]` becomes the Confluence version note.

## Input

- `[file]` — optional path to a specific markdown file. Default: scan `.vsaf/docs/features/*/02-prd.md`
- `[comment]` — optional version note (e.g., "Initial draft", "Updated after stakeholder review")

## Config Check (run FIRST)

Before doing anything, run this check via Bash tool:

```bash
source .claude/skills/_shared/vds-skill/credentials.sh 2>/dev/null
MISSING=""
[[ -x .claude/bin/vds-cli ]] && export PATH=".claude/bin:$PATH"
if ! vds-cli --version >/dev/null 2>&1; then
  MISSING="$MISSING vds-cli"
  # Show why: broken shim vs truly missing
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

- `vds-cli` installed (`command -v vds-cli`)
- A PRD markdown file must exist
- `VDS_CONFLUENCE_TOKEN` + `VDS_CONFLUENCE_SPACE_DEFAULT` in `~/.vds/sdlc-config.env`
- Confluence parent page configured in `.vsaf/config.yaml` (or lazy-prompted)

## Steps

### Step 1 — Find PRD file

- If `[file]` given: use directly
- Otherwise: list `.vsaf/docs/features/*/02-prd.md`
  - Multiple: ask user which one
  - None: STOP — tell user to run `/sdlc-prd` first
- Read full file content

### Step 2 — Load Confluence config

Read `.vsaf/config.yaml` (or `.vsaf/_bmad/bmm/config.yaml`) and extract:
- `confluence_space_key`
- `confluence_parent_page`

If missing: lazy-prompt + persist via `_shared/credentials.sh ensure_env`.

### Step 3 — Determine page title

- For `02-prd.md` under `features/{feature-name}/`: title = `[PRD] {Feature Name}` (derived from folder name)
- Otherwise: use first `# Heading` in file, or filename stem

### Step 4 — Convert markdown → Confluence storage format (XHTML)

**CRITICAL RULES:**

1. **Never send raw markdown.** All content must be converted to Confluence Storage Format (XHTML).
2. **Never wrap entire body in `<![CDATA[...]]>`.** CDATA is ONLY valid inside `<ac:plain-text-body>` within code macros.
3. **All Confluence macro attributes MUST use `ac:` namespace prefix.** The tag is `<ac:parameter ac:name="...">`, never `<parameter name="...">`.
4. **Escape HTML entities in regular text:** `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`.
5. **Every opened tag must be closed.** Confluence XML parser is strict.

**Block elements:**

```
# Heading      → <h1>Heading</h1>
## Heading     → <h2>Heading</h2>
### Heading    → <h3>Heading</h3>
#### Heading   → <h4>Heading</h4>
paragraph      → <p>paragraph</p>
---            → <hr/>
```

**Inline elements:**

```
**bold**       → <strong>bold</strong>
*italic*       → <em>italic</em>
`code`         → <code>code</code>
[text](url)    → <a href="url">text</a>
```

**Lists:**

```
- item         → <ul><li>item</li></ul>
1. item        → <ol><li>item</li></ol>
```

**Tables:**

```
| H1 | H2 |   →  <table><tbody>
|----|----|         <tr><th>H1</th><th>H2</th></tr>
| a  | b  |          <tr><td>a</td><td>b</td></tr>
                </tbody></table>
```

**Code blocks (ONLY place for CDATA):**

```
```lang        →  <ac:structured-macro ac:name="code">
code here           <ac:parameter ac:name="language">lang</ac:parameter>
```                 <ac:plain-text-body><![CDATA[code here]]></ac:plain-text-body>
                  </ac:structured-macro>
```

**Info/warning/tip boxes:**

```
> [!NOTE]      →  <ac:structured-macro ac:name="info">
> body              <ac:parameter ac:name="title">title</ac:parameter>
                    <ac:rich-text-body><p>body</p></ac:rich-text-body>
                  </ac:structured-macro>

> [!WARNING]   →  ac:name="warning"
> [!TIP]       →  ac:name="tip"
```

**Blockquote:**

```
> text         → <blockquote><p>text</p></blockquote>
```

Save converted XHTML to a temp file: `BODY_FILE=$(mktemp --suffix=.html)`.

### Step 5 — Search for existing page

Use Bash tool to run:

```bash
source .claude/skills/_shared/vds-skill/credentials.sh
ensure_env VDS_CONFLUENCE_TOKEN "Enter VDS Confluence personal access token"

SPACE_KEY="<from config>"
PAGE_TITLE="<title from Step 3>"

SEARCH_RESULT=$(vds-cli confluence search \
    --cql "space=$SPACE_KEY AND title = \"$PAGE_TITLE\"" \
    --limit 1 --json-only)

EXISTING_PAGE_ID=$(echo "$SEARCH_RESULT" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); print(d["results"][0]["id"] if d.get("results") else "")')
```

If `$EXISTING_PAGE_ID` non-empty → Step 6 (update). Otherwise → Step 7 (create).

### Step 6 — Update existing page (via vds-cli)

```bash
EXISTING_VERSION=$(echo "$SEARCH_RESULT" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); print(d["results"][0].get("version",{}).get("number",1))')

VERSION_COMMENT="${COMMENT:-Updated via vds-skill-push-prd}"

vds-cli confluence content update \
    --page-id "$EXISTING_PAGE_ID" \
    --body-file "$BODY_FILE" \
    --version $((EXISTING_VERSION + 1)) \
    --version-comment "$VERSION_COMMENT" \
    --json-only

rm -f "$BODY_FILE"
```

**Conflict handling:** if `vds-cli` returns version mismatch error, retry once with fresh version:

```bash
LATEST_VERSION=$(vds-cli confluence content page "$EXISTING_PAGE_ID" --json-only \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"]["number"])')

vds-cli confluence content update \
    --page-id "$EXISTING_PAGE_ID" \
    --body-file "$BODY_FILE" \
    --version $((LATEST_VERSION + 1)) \
    --version-comment "$VERSION_COMMENT" \
    --json-only
```

### Step 7 — Create new page (via vds-cli)

```bash
# Resolve parent page ID via search
PARENT_ID=""
if [[ -n "$CONFLUENCE_PARENT_PAGE" ]]; then
    PARENT_ID=$(vds-cli confluence search \
        --cql "space=$SPACE_KEY AND title = \"$CONFLUENCE_PARENT_PAGE\"" \
        --limit 1 --json-only \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["results"][0]["id"] if d.get("results") else "")')
fi

CREATE_ARGS=(vds-cli confluence content create-page
    --space "$SPACE_KEY"
    --title "$PAGE_TITLE"
    --body-file "$BODY_FILE"
    --version-comment "${COMMENT:-Initial PRD push via vds-skill-push-prd}"
    --json-only)
[[ -n "$PARENT_ID" ]] && CREATE_ARGS+=(--parent-id "$PARENT_ID")

"${CREATE_ARGS[@]}"
rm -f "$BODY_FILE"
```

### Step 8 — Output to user

```
## PRD pushed to Confluence

- Page:    {page_title}
- Action:  [Created / Updated]
- Space:   {space_key}
- Comment: {comment}
- URL:     {confluence_page_url}

## Next step
Optionally run /vds-skill-create-jira-epic to create a Jira epic from this PRD,
or continue with /sdlc-architecture (Phase 3).
```

## Notes

- Never push a PRD that has failed validation
- If `vds-cli` is not installed, tell user to install vds-scripts first
- Do not modify the local file during this step
- Conflict handling: version mismatch → auto-retry once with fresh version number
