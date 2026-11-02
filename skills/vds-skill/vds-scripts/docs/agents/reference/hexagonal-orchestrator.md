<!-- diátaxis: reference -->

# Hexagonal Orchestrator

> Validate hexagonal architecture compliance in Python and Java repositories.

## Scope

- **Does:** Analyze repositories for dependency direction, port/adapter boundaries, domain isolation, and layer violations using AST-based analyzers.
- **Does NOT:** Auto-refactor code or validate performance.
- **Primary users:** AI agents (architecture review), tech leads (CI compliance gates).

## CLI Entry

```bash
# Via unified router
vds-cli hexagonal --help

# Direct entry
vds-cli hexagonal --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `analyze` | Run hexagonal compliance analysis | `--config`, `--verbose`, `--timing`, `--cache-dir`, `--no-cache` |

## Analysis Pipeline

1. **Profile repository** — discover source files (`.py`, `.java`, `.kt`)
2. **Classify layers** — map files to domain, application, infrastructure layers
3. **Route to analyzers** — Python AST, Java AST, or fallback analyzer
4. **Generate report** — violations with file paths, line numbers, and severity

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Analysis completed successfully |
| 1 | Runtime error (file not found, parse error) |
| 2 | Configuration error |
| 3 | Violations found (CI gate) |

## Workflow Examples

```bash
# Basic analysis
vds-cli hexagonal analyze /path/to/repo

# With custom config and verbose output
vds-cli hexagonal analyze /path/to/repo --config hexagonal.yaml --verbose --timing

# JSON-only output for CI
vds-cli hexagonal analyze /path/to/repo --json-only --quiet

# Disable cache
vds-cli hexagonal analyze /path/to/repo --no-cache
```

## Related

- **Orchestrators:** [structure](structure-orchestrator.md), [circular-dependency](circular-dependency-orchestrator.md)
- **Skills:** [code-review-graph-skill](../../../../vds-skills/skills/code-review-graph-skill/SKILL.md)
