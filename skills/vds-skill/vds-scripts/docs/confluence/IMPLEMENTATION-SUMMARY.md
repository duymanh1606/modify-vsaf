# WHO-Project Confluence Documentation Hub — Implementation Summary

**Date:** 2026-04-21
**Branch:** `feat/who-confluence-hub-scripts`
**Status:** COMPLETE

---

## Page Hierarchy

```
57250660 "II. Hoạt động sản xuất nội bộ" (TTCN24)
└── WHO-Project Ecosystem Documentation (98997962) [navigation_hub]
    ├── Ecosystem Installation Guide (98997963)
    ├── vds-scripts Quick Reference (98997964)
    ├── vds-skills Quick Reference (98997965)
    ├── vds-skills Quick Reference (98997966)
    └── Documentation Health Dashboard (98997968)
```

## Commands

### Sync all pages
```bash
vds-cli docs confluence-sync
```

### Dry run
```bash
vds-cli docs confluence-sync --dry-run
```

### Create missing pages
```bash
vds-cli docs confluence-sync --create-missing
```

### Standalone Confluence operations (via vds-cli)
```bash
# Create page
vds-cli confluence content create-page --space-key TTCN24 --title "..." --body "..." --parent-id 98997962

# Update page
vds-cli confluence content update-page PAGE_ID --title "..." --body "..."

# Move page
vds-cli confluence content move PAGE_ID --target-title "WHO-Project Ecosystem Documentation"

# List child pages
vds-cli confluence content child-pages PAGE_ID
```

## Architecture

- **Config:** `docs/.confluence.yaml` — source of truth for page definitions
- **Sync engine:** `vds_cli/src/vds_cli/confluence_sync.py` (~420 lines)
- **Confluence client:** `confluence_orchestrator.ConfluenceClient` + `ContentClient` (imported)
- **Bitbucket links:** Deterministic URL generation from config (no Bitbucket API calls)
- **Cross-worktree:** Content loaded from sibling worktrees (skills, plugins)

## Auth

- `INTERNAL_CONFLUENCE_TOKEN` — loaded from `~/.vds/.env` via `ConfluenceSettings`
- `INTERNAL_BITBUCKET_TOKEN` — for Bitbucket link resolution

## Spec Alignment

- `requirements.md`: Updated with correct space_key (TTCN24), page IDs, hierarchy
- `tasks.md`: DOC-021..DOC-027 marked COMPLETE
- `design.md`: Updated space_key reference

## Branches

| Repo | Branch | Status |
|------|--------|--------|
| vds-scripts | feat/who-confluence-hub-scripts | 5 commits, pushed |
| vds-skills | feat/who-confluence-hub-skills | 1 commit, pushed |
| vds-skills | feat/who-confluence-hub-plugins | 1 commit, pushed |
