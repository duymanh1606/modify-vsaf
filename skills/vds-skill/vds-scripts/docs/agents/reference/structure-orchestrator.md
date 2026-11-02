<!-- diátaxis: reference -->

# Structure Orchestrator

> Structure validation for VDS documentation and project folder consistency.

## Scope

- **Does:** Validate target-state documentation structure, check folder consistency across projects, and generate structure compliance reports.
- **Does NOT:** Create missing folders automatically or validate file content.
- **Primary users:** AI agents (docs readiness checks), project maintainers.

## CLI Entry

```bash
# Via unified router
vds-cli structure --help

# Direct entry
vds-structure --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `validate` | Validate structure (target-state or folder consistency) | `--mode`, `--root`, `--report` |

## Validation Modes

- `target-state` — validate target-state documentation tree structure
- `folder-consistency` — compare folder structures across projects and score consistency

## Workflow Examples

```bash
# Validate target-state structure
vds-structure validate --mode target-state

# Validate with custom root
vds-structure validate --mode target-state --root ./docs

# Folder consistency check across projects
vds-structure validate --mode folder-consistency --root ./projects

# Write JSON report
vds-structure validate --mode target-state --report structure-report.json

# JSON-only output
vds-structure --json-only validate --mode target-state
```

## Report Output

Folder consistency reports include:
- Total and analyzed project counts
- Consistency score (percentage)
- Missing projects list
- Common folders and files
- Per-project mismatch details

## Environment

- `VDS_INSURANCE_DOCS_ROOT` — override default documentation root discovery

## Related

- **Orchestrators:** [links](links-orchestrator.md), [brd](brd-orchestrator.md)
- **Confluence:** [WHO Structure](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
