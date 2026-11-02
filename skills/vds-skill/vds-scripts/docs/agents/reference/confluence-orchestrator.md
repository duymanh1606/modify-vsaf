<!-- diátaxis: reference -->

# Confluence Orchestrator

> Manage Confluence content: create, update, copy pages, upload attachments, and sync doc inventories programmatically.

## Scope

**What this orchestrator does:**
- Create or update pages under a specific parent (e.g., WHO Documentation Hub).
- Copy page trees with optional label filtering.
- Upload local files as page attachments.
- Generate table-of-contents and navigation pages automatically.
- Sync markdown docs to Confluence as formatted content.

**What it does NOT do:**
- Does not manage Confluence space settings or user permissions.
- Does not provide full HTML rendering (XHTML subset only).

**Primary users:** AI agents syncing doc states; human leads publishing reports.

## CLI Entry

```bash
vds-cli confluence --help
vds-cli confluence-cli --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `create-page` | Create a page under a parent | `--space`, `--parent-id`, `--title` |
| `update-page` | Edit an existing page body | `--page-id`, `--file` |
| `copy-tree` | Copy a page and its children | `--src-page-id`, `--dst-parent-id` |
| `upload-attachment` | Attach a file to a page | `--page-id`, `--file-path` |
| `get-page` | Retrieve page metadata and body | `--page-id` |
| `search` | Search pages by text | `--query`, `--space` |

## Common Workflows

### Workflow 1: Doc Inventory Sync
1. Run `vds-cli docs ecosystem-index --generate`.
2. Push the result to Confluence: `vds-cli confluence create-page --parent-id=57250660 --file=ECOSYSTEM-DOCS.md`.
3. Verify with `vds-cli confluence search --query="WHO Ecosystem"`.

### Workflow 2: Audit Evidence Attachment
1. After `vds-cli audit`, locate the `evidence/` directory.
2. Upload all `.html` files: `vds-cli confluence upload-attachment --page-id=88716821 --file-path=evidence/`.
3. Update the audit page with evidence links.

## Related

- **Orchestrators:** [jira](jira-orchestrator.md), [bitbucket](bitbucket-orchestrator.md), [progress](progress-orchestrator.md)
- **Skills:** [confluence-skill](../../../../vds-skills/skills/)
- **Confluence:** TTCN24/WHO-Project (pageId 57250660)
