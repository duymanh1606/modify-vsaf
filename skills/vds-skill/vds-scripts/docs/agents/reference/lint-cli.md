<!-- diátaxis: reference -->

# Lint CLI Reference

> Compliance diagnostics and governance checks for the VDS CLI platform.

## Summary Box

| Property | Value |
|---|---|
| Command family | `vds-cli lint` |
| Source file | `vds_cli/src/vds_cli/commands/lint_cli.py` |
| Report scope | CLI surface, orchestrator mappings, doc drift, tool configs, test coverage gates |
| Target agents | CI pipelines, repository maintainers |

## Table of Contents

- [Quick Reference](#quick-reference)
- [cli](#cli)
- [Report Checks](#report-checks)
- [Exit Codes](#exit-codes)
- [See Also](#see-also)

## Quick Reference

| Subcommand | Purpose | Key Flags | Example |
|---|---|---|---|
| `cli` | Run compliance diagnostics for the vds-cli surface | `--json` | `vds-cli lint cli --json` |

## cli

Run governance checks against the CLI surface and generate a compliance report.

```bash
vds-cli lint cli [OPTIONS]
```

#### Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--json` | bool | `False` | Emit machine-readable JSON output |

#### Report Checks

The report validates these dimensions:

| Check | Pass Criteria |
|---|---|
| orchestrator count | Matches `len(ORCHESTRATORS)` in router |
| legacy alias count | Zero removed aliases in workspace `pyproject.toml` `[project.scripts]` |
| doc drift | No removed aliases or direct executables referenced in `cli-help-matrix.md` |
| tool configs | `[tool.ruff]` and `[tool.mypy]` present in workspace `pyproject.toml` |
| coverage gate | Any scanned `pyproject.toml` has `fail_under` > 0 |
| anti-patterns | No `sys.exit()`, no `argparse`, no `click`, no bare `RuntimeError()` in `*/cli.py` |

#### Example (human readable)

```bash
vds-cli lint cli
```

#### Example (JSON)

```bash
vds-cli lint cli --json
```

**Sample JSON output (partial):**

```json
{
  "compliant": true,
  "checks": {
    "orchestrator_count": { "status": "pass", "value": 33 },
    "legacy_alias_count": { "status": "pass", "value": 0 },
    "doc_drift": { "status": "pass", "issues": [] },
    "tool_configs": { "status": "pass", "ruff": true, "mypy": true },
    "coverage_gate": { "status": "pass", "threshold": 70 },
    "anti_patterns": { "status": "pass", "issues": [] }
  }
}
```

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | All checks pass |
| `1` | One or more checks failed |

## See Also

- [CLI Development Standards](cli-development-standards.md) — governance rules and authoring checklist
- [CLI Help Matrix](cli-help-matrix.md) — verified routed command inventory
- `vds_cli/src/vds_cli/commands/lint_cli.py` — source implementation

---
*Generated from `lint_cli.py` (Phase 179).*
