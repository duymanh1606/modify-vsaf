<!-- diátaxis: reference -->

# Diagrams Orchestrator

> Generate C4, sequence, component, use case, and mermaid diagrams from code or DSL.

## Scope

- **Does:** Generate C4 context/container/component/code diagrams, sequence diagrams, use case diagrams, and render mermaid from markdown or DSL.
- **Does NOT:** Create artistic diagrams, replace dedicated diagramming tools like draw.io.
- **Primary users:** AI agents (architecture documentation), developers (design docs).

## CLI Entry

```bash
# Via unified router
vds-cli diagrams --help

# Direct entry
vds-cli diagrams --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `c4` | Generate C4 diagram | `--level`, `--output` |
| `sequence` | Generate sequence diagram | `--participants`, `--output` |
| `component` | Generate component diagram | `--scope`, `--output` |
| `usecase` | Generate use case diagram | `--actors`, `--output` |
| `mermaid` | Render mermaid from file | `--input`, `--output` |

## Common Workflows

### Workflow: Generate C4 Architecture Diagram

1. Define components in a DSL or markdown file
2. Run `vds-cli diagrams c4 --level container --input architecture.md --output c4-container.png`
3. Review generated diagram
4. Include in Confluence or documentation

### Workflow: Render Mermaid from Markdown

1. Write mermaid syntax in a markdown file: ````mermaid graph TD; A-->B;````
2. Run `vds-cli diagrams mermaid --input doc.md --output diagram.svg`
3. Embed SVG in documentation

## Related

- **Orchestrators:** [schema](schema-orchestrator.md), [structure](structure-orchestrator.md), [pdf](pdf-orchestrator.md)
- **Skills:** [cli-development-skill](../../../../vds-skills/skills/cli-development-skill/SKILL.md)
- **Confluence:** [WHO Diagrams](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
