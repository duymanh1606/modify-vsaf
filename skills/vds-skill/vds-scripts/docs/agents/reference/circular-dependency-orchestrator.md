<!-- diátaxis: reference -->

# Circular Dependency Orchestrator

> Detect and visualize circular dependencies in Python and JavaScript codebases.

## Scope

- **Does:** Analyze import graphs, detect cycles, generate visualizations, suggest break points, and export cycle reports.
- **Does NOT:** Auto-fix cycles, analyze non-code dependencies, or replace architectural review.
- **Primary users:** AI agents (code health), developers (refactoring planning), tech leads.

## CLI Entry

```bash
# Via unified router
vds-cli circular-dependency --help

# Direct entry
vds-circular-dependency --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `analyze` | Analyze repo for cycles | `--path`, `--language` |
| `visualize` | Generate cycle graph | `--format`, `--output` |
| `report` | Generate cycle report | `--output`, `--detail` |
| `suggest` | Suggest break points | `--cycle-id` |

## Common Workflows

### Workflow: Detect and Fix Cycles

1. Run `vds-cli circular-dependency analyze --path . --language python`
2. Review detected cycles
3. Visualize: `vds-cli circular-dependency visualize --format svg --output cycles.svg`
4. Get suggestions: `vds-circular-dependency suggest --cycle-id 1`
5. Refactor based on suggestions
6. Re-run analysis to verify fix

## Related

- **Orchestrators:** [structure](structure-orchestrator.md), [hexagonal](hexagonal-orchestrator.md), [code-review](code-review-graph-skill.md)
- **Skills:** [circular-dependency-skill](../../../../vds-skills/skills/circular-dependency-skill/SKILL.md)
- **Confluence:** [WHO Circular Dependency](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
