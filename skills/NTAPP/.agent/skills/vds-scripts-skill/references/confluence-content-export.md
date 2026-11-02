# Confluence Content Export — Mandatory Rules

When extracting content from a Confluence page (BRD, KBNV, SRS, or any page with tables/images), follow these rules strictly. Violations cause data loss that is invisible to the user.

## Rule 0 — Output Directory

All Confluence export artifacts **MUST** be placed under `.vsaf/docs/` in the project root, **not** in `docs/` at root.

```
<project-root>/
├── .vsaf/
│   └── docs/
│       └── confluence/
│           ├── <page-title>/
│           │   ├── content.md
│           │   └── images/
│           │       ├── screen-login.png
│           │       └── flow-diagram.png
│           └── <another-page>/
│               ├── content.md
│               └── images/
└── docs/          ← project docs, NOT for Confluence exports
```

- Use `.vsaf/docs/confluence/<page-title>/` as the output directory for each page.
- This keeps Confluence artifacts separate from project documentation and co-located with other VSAF working files.
- Pass `--out .vsaf/docs/confluence/<page-title>/` when using CLI commands that accept output path.

## Rule 1 — Use `body.storage` as the Single Source of Truth for Image Refs

- **Never** rely on `body.view` for image references — it is post-render HTML that may add or drop images via macros.
- `body.storage` is raw XHTML containing `<ac:image><ri:attachment ri:filename="..."/></ac:image>` — this is the definitive set of inline images.
- **Only download attachments whose filename appears in `body.storage`**. Do not bulk-download from `attachments --list`.

```bash
# Step 1: fetch storage body
uv run --directory ~/.claude/vds-scripts --package vds-cli \
  vds-cli confluence content page <PAGE_ID> --expand body.storage
```

```python
# Step 2: extract referenced filenames from storage XHTML
import re
storage_xml: str = ...  # body.storage content
referenced = set(re.findall(r'ri:filename="([^"]+)"', storage_xml))
# referenced = {'screen-login.png', 'flow-diagram.png', 'table-header.png'}
```

## Rule 2 — Preserve Image-to-Text Positional Mapping

When converting to markdown/local file:

- Replace each `<ac:image>...<ri:attachment ri:filename="X"/>...</ac:image>` with `![X](images/X)` **at its original position** in the document. Never collect images into a list at the end.
- If the content contains `<table>`, **keep HTML table markup** in the markdown output. Markdown viewers (GitHub, Obsidian, VS Code) all render HTML tables. Do not flatten tables with nested bullets or merged cells into pure-markdown `|` tables — this destroys row/column relationships.
- Place the `images/` folder at the same level as `content.md`.

```python
# Step 3: convert storage XHTML → markdown with inline image refs
import re

def storage_to_markdown(storage_xml: str) -> str:
    """Convert Confluence storage XHTML to markdown, preserving image positions and tables."""
    result = storage_xml

    # Replace ac:image with markdown image refs (in-place)
    def replace_ac_image(match: re.Match) -> str:
        filename = re.search(r'ri:filename="([^"]+)"', match.group(0))
        if filename:
            name = filename.group(1)
            return f'![{name}](images/{name})'
        return match.group(0)

    result = re.sub(
        r'<ac:image[^>]*>.*?</ac:image>',
        replace_ac_image,
        result,
        flags=re.DOTALL,
    )

    # Keep <table>...</table> blocks as-is (HTML in markdown)
    # Convert other XHTML elements to markdown as usual:
    # <p> → newline, <h1> → #, <li> → -, <strong> → **, etc.
    # ...

    return result
```

## Rule 3 — Classify Downloaded Attachments

If the user requests "all attachments" (audit/backup scenario):

- Split into two directories:
  - `images/` — files referenced inline in `body.storage`
  - `images_unused/` — attached to the page but **not** referenced inline
- Report summary: `Used: N inline / Total: M attached`

```bash
# Download only referenced attachments into .vsaf/docs/confluence/<page>/images/
OUT_DIR=".vsaf/docs/confluence/<page-title>"
mkdir -p "$OUT_DIR/images"
for filename in $REFERENCED_FILES; do
  att_id=$(vds-cli confluence content list-attachments <PAGE_ID> --json-only \
    | jq -r ".[] | select(.title == \"$filename\") | .id")
  uv run --directory ~/.claude/vds-scripts --package vds-cli \
    vds-cli confluence content download-attachment "$att_id" --out "$OUT_DIR/images/$filename"
done
```

## Rule 4 — Verify Before Reporting "Done"

After generating `content.md`:

1. Count inline image refs in output: `grep -c '!\[.*\](images/.*)' content.md`
2. Count `ri:filename` occurrences in `body.storage`
3. **Both counts must match.** If they differ, log a warning with the diff:

```
WARNING: Image ref mismatch — storage has 3 ri:filename refs, content.md has 2 inline images.
Missing: screen-step3.png
```

Do not report success if counts diverge.

## Rule 5 — Correct Invocation Sequence (Step by Step)

```bash
# B0: Set output directory
OUT_DIR=".vsaf/docs/confluence/<page-title>"
mkdir -p "$OUT_DIR/images"

# B1: Fetch storage body (source of truth for image refs)
uv run --directory ~/.claude/vds-scripts --package vds-cli \
  vds-cli confluence content page <PAGE_ID> --expand body.storage

# B2: Extract ri:filename values from storage XML (see Rule 1 Python snippet)

# B3: Download only referenced attachments
uv run --directory ~/.claude/vds-scripts --package vds-cli \
  vds-cli confluence content download-attachment <ATT_ID> --out "$OUT_DIR/images/<filename>"

# B4: Convert storage XHTML → markdown (see Rule 2 Python snippet)
#     - ac:image → ![](images/...) in-place
#     - tables stay as HTML
#     - output: $OUT_DIR/content.md + $OUT_DIR/images/

# B5: Verify (see Rule 4)
```

## Anti-Patterns (What NOT to Do)

| Anti-pattern | Why it fails |
|---|---|
| Fetch `body.view` then strip HTML | Loses image positions, macro-injected images leak in |
| `attachments --list` then download all | Downloads orphaned/versioned files (59 vs 3 actually used) |
| Flatten `<table>` to markdown `\|` pipe tables | Destroys merged cells, nested bullets, colspan/rowspan |
| Collect images at end of document | Breaks image↔context mapping (which screen? which step?) |
| Skip verification | Silent data loss — user trusts output without knowing images are missing |
| Export to `docs/` at project root | Pollutes project docs; use `.vsaf/docs/confluence/` instead |
