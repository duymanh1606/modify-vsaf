<!-- diátaxis: reference -->
# `vds-cli docs confluence-sync` — Confluence Documentation Sync

> One-way sync from local Markdown to Confluence pages.

```bash
vds-cli docs confluence-sync [--repo-root PATH] [--space-key SPACE]
```

## Synopsis

Pushes selected Markdown docs (e.g., `docs/agents/**/*.md`) to a Confluence space.
Requires a `confluence_access_token` in the shared env (`~/.vds/shared.env`).

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--repo-root` | `Path` | `CWD` | Repository root carrying docs to sync |
| `--space-key` | `str` | `WHO` | Confluence space key |
| `--dry-run` | `bool` | `False` | Preview changes without writing |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All pages updated or no changes |
| `1` | Auth missing, network failure, or page conflict |

## Prerequisites

1. `confluence_access_token` exported in `~/.vds/shared.env`
2. Space read/write permission for the bot account
3. Page IDs cached in `docs/.confluence_ids.json` (auto-created on first run)

## Caveats

- **Rate limits**: 1 req/s enforced internally; burst may trigger 429
- **Images**: Relative image paths are resolved against `repo_root`; unsupported formats are skipped with a warning
- **Parent page**: The first H1 becomes the page title; H2/H3 become Confluence headings
- **Tables**: Standard Markdown tables work; merged cells are flattened

## See Also

- [CLI Commands Reference](./cli-commands.md)
- [Confluence Orchestrator Reference](./confluence-orchestrator.md)
