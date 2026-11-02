<!-- diátaxis: explanation -->

# WHO Ecosystem Explanation Index

> Overview and navigation for WHO documentation explanation pages.

## Available Explanations

| Document | Purpose | Audience |
|----------|---------|----------|
| [Runtime Verification and Gap Reporting](runtime-verification-and-gap-reporting.md) | How VDS verifies results and reports gaps | All developers |
| [WHO Ecosystem Model](who-ecosystem-model.md) | Architecture and component relationships | New team members |

## Common Questions

### How does the WHO ecosystem work?

The WHO ecosystem is a multi-repo monorepo centered around `WHO-project/`:
- `vds-scripts`: Core platform and orchestrator router
- `vds-skills`: 27+ skills catalog
- `vds-skills`: Unified skills catalog, hooks, and plugin marketplace
- `vds-ai-memory`: Cross-session memory

### How do I find the right doc?

Use [Orchestrator Index](../reference/orchestrator-index.md) or search with:
```bash
rg "topic" docs/agents/
```

## Related

- [WHO Ecosystem Model](who-ecosystem-model.md)
- [Runtime Verification](runtime-verification-and-gap-reporting.md)
- [Orchestrator Index](../reference/orchestrator-index.md)
- [Skills Reference](../reference/skills-reference.md)
