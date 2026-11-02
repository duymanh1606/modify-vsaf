<!-- diátaxis: reference -->

# Public Interface Orchestrator

> Public interface boundary evidence extraction for audit compliance.

## Scope

- **Does:** Scan repositories for import statements that may indicate boundary violations (internal, impl, adapter, infrastructure imports), producing heuristic evidence for audit checklist items.
- **Does NOT:** Prove violations conclusively — output requires manual confirmation and syntax-aware interpretation.
- **Primary users:** AI agents (audit evidence collection), compliance reviewers.

## CLI Entry

```bash
# Via unified router
vds-cli public-interface --help

# Direct entry
vds-cli public-interface --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `scan-repo` | Scan a single repo for boundary candidate imports | `--json/--no-json`, `--output` |
| `scan-project` | Scan a project directory containing multiple repos | `--json/--no-json`, `--output` |

## Detection Heuristics

Scans `.py`, `.java`, `.kt`, `.ts`, `.tsx`, `.js`, `.jsx` files (excluding tests) for:

- `internal` imports
- `impl` / `adapter` imports
- `infrastructure` imports
- `*Impl` / `*Implementation` symbol imports

## Workflow Examples

```bash
# Scan a single repository
vds-cli public-interface scan-repo /path/to/repo

# Scan with JSON output persisted
vds-cli public-interface scan-repo /path/to/repo --output boundary-evidence.json

# Scan a project directory containing multiple repos
vds-cli public-interface scan-project /path/to/project --output project-boundary.json

# Non-JSON human-readable output
vds-cli public-interface scan-repo /path/to/repo --no-json
```

## Output Format

```json
{
  "command": "scan-repo",
  "scope": "repo",
  "shared_companion_only": true,
  "files_scanned": 150,
  "candidate_file_count": 3,
  "result_type": "evidence_gap",
  "reasoning": "...",
  "candidates": [...]
}
```

## Related

- **Orchestrators:** [hexagonal](hexagonal-orchestrator.md), [structure](structure-orchestrator.md)
- **Confluence:** [WHO Public Interface](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
