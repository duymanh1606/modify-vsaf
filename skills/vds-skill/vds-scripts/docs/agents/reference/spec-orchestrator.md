<!-- diátaxis: reference -->

# Spec Orchestrator

> Create, validate, and maintain canonical VDS specification triplets.

## Scope

- **Does:** Scaffold spec directories, validate triplet consistency, check alignment between requirements/design/tasks, enforce AGENTS.md sync lines.
- **Does NOT:** Write spec content for you, auto-generate designs from thin air, replace human review.
- **Primary users:** AI agents (spec creation), human leads (review and approval).

## CLI Entry

```bash
# Via unified router
vds-cli spec --help

# Direct entry
vds-cli spec --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `validate <path>` | Validate a spec triplet | — |
| `check-alignment <path>` | Cross-reference FRs and tasks | — |
| `validate-sync <name>` | Sync-check with AGENTS.md | `--agents-label` |
| `create <name>` | Scaffold new spec directory | — |

## Common Workflows

### Workflow: Create New Phase Spec

1. Define scope and acceptance criteria
2. Run `vds-cli spec create <name>` to scaffold triplet
3. Fill in `requirements.md`, `design.md`, `tasks.md`
4. Run `vds-cli spec validate <path>` to verify structure
5. Run `vds-cli spec check-alignment <path>` to cross-reference
6. Update AGENTS.md sync line
7. Run `vds-cli spec validate-sync <name> --agents-label "..."`

### Workflow: Validate Existing Spec

1. Run `vds-cli spec validate <path>` — checks version alignment, FR presence, task packages
2. Run `vds-cli spec check-alignment <path>` — verifies FR/task cross-references
3. Fix any reported gaps
4. Re-run until all checks pass

## Related

- **Orchestrators:** [tasks](tasks-orchestrator.md), [audit](audit-triage-playbook.md), [research](research-orchestrator.md)
- **Skills:** [spec-creation-skill](../../../../vds-skills/skills/spec-creation-skill/SKILL.md)
- **Confluence:** [WHO Specs](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
- **Bitbucket:** [vds-scripts source](https://bitbucket.digital.vn/projects/WHO/repos/vds-scripts/browse)
