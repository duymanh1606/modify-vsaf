# Confluence Sync Scripts

This directory contains standalone sync scripts for synchronizing local files with Confluence attachments.

## Standard Practice: Use VDS CLI

**✅ RECOMMENDED**: Use the unified VDS CLI to run sync commands:

```bash
# Sync PDFs to Confluence
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence sync pdfs \
  <page_id> \
  --dir /path/to/pdf/directory \
  --server external

# Sync PNGs to Confluence
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence sync pngs \
  <page_id> \
  --dir /path/to/png/directory \
  --server external

# Regenerate PDFs from markdown (via PDF orchestrator)
./scripts/worktree_uv.sh run --project vds_cli vds-cli pdf -- md2pdf file.md -o file.pdf
```

## Standalone Script Execution

If you need to run scripts directly (e.g., for automation or debugging), use:

```bash
cd /path/to/vds-scripts/confluence_orchestrator

# Sync PDFs
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_pdfs_to_confluence.py \
  sync <page_id> --dir /path/to/pdfs --server external

# Sync PNGs
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_png_attachments.py \
  sync <page_id> --dir /path/to/pngs --server external

# Regenerate PDFs from markdown
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_pdfs_from_markdown.py \
  /path/to/target-state
```

## Scripts

### `sync_pdfs_to_confluence.py`

Syncs local PDF files with Confluence page attachments.

**Commands**:
- `list <page_id>` - List PDF attachments on a page
- `sync <page_id> --dir <directory>` - Sync PDFs from directory to page

**Options**:
- `--server` - Confluence server (internal|external)
- `--pattern` - Filter PDF files by pattern
- `--dry-run` - Show what would be done without making changes
- `--comment` - Comment for attachment updates
- `--yes` - Auto-confirm without prompting

### `sync_png_attachments.py`

Syncs local PNG files with Confluence page attachments.

**Commands**:
- `list <page_id>` - List PNG attachments on a page
- `sync <page_id> --dir <directory>` - Sync PNGs from directory to page

**Options**: Same as `sync_pdfs_to_confluence.py`

### `sync_pdfs_from_markdown.py`

Regenerates PDF files from markdown sources using `vds-cli pdf md2pdf`.

**Usage**:
```bash
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_pdfs_from_markdown.py \
  /path/to/directory \
  [--pattern "*.md"] \
  [--dry-run]
```

**Options**:
- `--pattern` - Filter markdown files by pattern (e.g., `"*-schema.md"`)
- `--dry-run` - Show what would be regenerated without actually regenerating

## Environment Requirements

All scripts require:
- `confluence_orchestrator` package installed (via `uv sync`)
- Confluence credentials in the shared VDS env file:
  - `INTERNAL_CONFLUENCE_TOKEN` or `EXTERNAL_CONFLUENCE_TOKEN`
- For PDF generation: `vds_cli` package with PDF orchestrator

## Integration with VDS CLI

The sync commands are integrated into the unified VDS CLI:

```bash
# List PDF attachments
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content attachments \
  --page <page_id> --server external

# Sync PDFs (via sync command)
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence sync pdfs \
  <page_id> --dir /path/to/pdfs --server external
```

## Troubleshooting

**ModuleNotFoundError: No module named 'confluence_orchestrator'**:
- Ensure you're running from `vds-scripts/confluence_orchestrator` directory
- Or use `./scripts/worktree_uv.sh run --project confluence_orchestrator python <script>`
- Or use the unified CLI: `./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence sync ...`

**PDF generation fails**:
- Ensure `vds_cli` package is installed: `uv sync --project vds_cli`
- Check that `vds-cli pdf md2pdf` works independently

**Confluence authentication fails**:
- Run `./scripts/worktree_uv.sh run --project vds_cli vds-cli env load` to load credentials
- Verify the shared VDS env file contains the required tokens

ns

