<!-- diátaxis: explanation -->


## Doc Structure

This directory follows the Diátaxis framework:

| Quadrant | Purpose | Examples |
|----------|---------|----------|
| [Tutorials](tutorials/) | Step-by-step learning | zero-to-productive-developer |
| [How-To](how-to/) | Task-focused guides | install, decision-tree, workflow |
| [Reference](reference/) | Command/API reference | 28 orchestrator docs |
| [Explanation](explanation/) | Conceptual depth | ecosystem model, verification |

## CLI Entry

```bash
# Validate all docs
vds-cli docs validate --repo-root . --check-diataxis --check-orchestrators --check-vi

# Score quality
vds-cli docs quality-score --repo-root .

# Show freshness
vds-cli docs freshness --repo-root .
```

## Related

- [VDS Scripts AGENTS.md](../../../AGENTS.md)
- [Orchestrator Index](reference/orchestrator-index.md)
- [WHO Ecosystem Model](explanation/who-ecosystem-model.md)
- [Confluence Hub](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
