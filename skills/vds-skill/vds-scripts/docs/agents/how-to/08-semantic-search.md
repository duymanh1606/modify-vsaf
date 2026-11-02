<!-- diátaxis: how-to -->

# Semantic Search

> Use semantic search to find code and documentation by meaning, not exact string.

## Scope

- **Does:** Search by concept, intent, and semantic meaning across code and docs.
- **Does NOT:** Replace exact-string search (`rg`) when you know the symbol name.

## CLI Entry

```bash
# Via unified router
vds-cli research --help

# Direct entry
vds-cli research --help
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `search` | Semantic search |
| `score` | Score evidence quality |

## Workflow

### Search by Meaning

1. Run: `vds-cli research search "credential resolution pattern"`
2. Review ranked results by relevance
3. Filter by source: `--tool tavily`, `--tool grepai`

```bash
# Example: find how VDS handles retry
grepai search "retry pattern with exponential backoff"
```

## Related

- [Search Tools Reference](../reference/search-tools.md)
- [Research Orchestrator](../reference/research-orchestrator.md)
- [Memory Orchestrator](../reference/memory-orchestrator.md)
