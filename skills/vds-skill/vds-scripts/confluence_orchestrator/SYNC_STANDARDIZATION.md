# Sync Scripts Standardization

**Date**: 2025-12-15  
**Status**: ✅ Complete

## Summary

Standardized PDF and PNG sync scripts to follow VDS CLI best practices. Sync scripts are now integrated into the unified VDS CLI and located in the `confluence_orchestrator` directory for consistency.

## Changes Made

### 1. Script Relocation

- **Moved** `sync_pdfs_from_markdown.py` from `docs-nttc/projects/INSURANCE/analysis/target-state/architecture/scripts/` to `vds-scripts/confluence_orchestrator/`
- **Moved** `sync_pdfs_to_confluence.py` from `docs-nttc/projects/INSURANCE/analysis/target-state/architecture/scripts/` to `vds-scripts/confluence_orchestrator/`
- **Reason**: Consistency with existing `sync_png_attachments.py` location and VDS orchestrator structure

### 2. CLI Integration

- **Added** `sync` subcommand group to `confluence_orchestrator.cli`
- **Added** `sync pdfs` command that delegates to `sync_pdfs_to_confluence.py`
- **Added** `sync pngs` command that delegates to `sync_png_attachments.py`
- **Accessible via**: `./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence sync pdfs/pngs`

### 3. Path Fixes

- **Fixed** hardcoded absolute path in `sync_pdfs_from_markdown.py` to use relative path based on script location
- **Updated** `VDS_SCRIPTS` path calculation to be relative: `Path(__file__).resolve().parent.parent`

### 4. Documentation Updates

- **Created** `SYNC_SCRIPTS.md` in `confluence_orchestrator/` with complete usage guide
- **Updated** `confluence_orchestrator/README.md` with sync command examples
- **Updated** `architecture/scripts/README.md` to note script relocation and point to new location
- **Updated** `PDF_SYNC_WORKFLOW.md` to reflect standard practice (VDS CLI usage)

## Standard Practice

### ✅ Recommended: Use VDS CLI

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
```

### Alternative: Direct Script Execution

```bash
cd vds-scripts/confluence_orchestrator

# Sync PDFs
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_pdfs_to_confluence.py \
  sync <page_id> --dir <directory> --server external

# Sync PNGs
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_png_attachments.py \
  sync <page_id> --dir <directory> --server external

# Regenerate PDFs from markdown
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_pdfs_from_markdown.py \
  /path/to/target-state --dry-run
```

## Testing

✅ **Validated**:
- `sync_pdfs_from_markdown.py` runs successfully from `confluence_orchestrator/` directory
- Script correctly finds markdown files and generates sync plan
- Path resolution works correctly with relative paths

⚠️ **Note**: Full end-to-end testing requires:
- Confluence credentials in the shared VDS env file
- Access to Confluence server
- PDF generation via `vds-cli pdf md2pdf`

## Files Modified

1. `vds-scripts/confluence_orchestrator/src/confluence_orchestrator/cli.py` - Added sync commands
2. `vds-scripts/confluence_orchestrator/sync_pdfs_from_markdown.py` - Fixed path resolution
3. `vds-scripts/confluence_orchestrator/sync_pdfs_to_confluence.py` - Copied from original location
4. `vds-scripts/confluence_orchestrator/SYNC_SCRIPTS.md` - New documentation
5. `vds-scripts/confluence_orchestrator/README.md` - Updated with sync examples
6. `docs-nttc/projects/INSURANCE/analysis/target-state/architecture/scripts/README.md` - Updated to note relocation

## Benefits

1. **Consistency**: All sync scripts in one location (`confluence_orchestrator/`)
2. **Unified CLI**: Access via `vds-cli confluence sync` commands
3. **Standard Practice**: Follows VDS orchestrator patterns
4. **Maintainability**: Single source of truth for sync functionality
5. **Documentation**: Complete usage guide in `SYNC_SCRIPTS.md`

## Next Steps

- [ ] Test full end-to-end sync workflow (markdown → PDF → Confluence)
- [ ] Add sync commands to main VDS CLI help documentation
- [ ] Consider adding sync commands to other orchestrators if needed
- [ ] Monitor usage and gather feedback for improvements

