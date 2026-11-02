# Confluence Sync Guide

## Prerequisites

```bash
# Ensure tokens are configured in ~/.vds/.env
export INTERNAL_CONFLUENCE_TOKEN="your-confluence-token"
export INTERNAL_BITBUCKET_TOKEN="your-bitbucket-token"
```

## Quick Start

### 1. Dry Run
```bash
vds-cli docs confluence-sync --dry-run
```

### 2. Create Parent Page (DOC-021)
```bash
vds-cli docs confluence-sync --create-missing --page "WHO-Project Ecosystem Documentation"
```

Capture the returned `page_id` and update `docs/.confluence.yaml`.

### 3. Create Child Pages
```bash
vds-cli docs confluence-sync --create-missing
```

### 4. Update Specific Page
```bash
vds-cli docs confluence-sync --page "vds-scripts Quick Reference"
```

### 5. Full Sync
```bash
vds-cli docs confluence-sync
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Auth error | Check `INTERNAL_CONFLUENCE_TOKEN` |
| Page not found | Use `--create-missing` |
| Wrong parent | Verify `parent_page_id` |
| Link 404 | Check repo slug matches Bitbucket |
