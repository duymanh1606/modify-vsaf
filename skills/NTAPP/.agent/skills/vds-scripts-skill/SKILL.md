---
name: vds-scripts-skill
description: Use the WHO VDS scripts ecosystem as the platform entrypoint for routed CLI commands, workspace capabilities, and skill delegation. Use when you need to choose the right vds-cli command family, understand the current WHO scripts surface, or route to the correct specialist skill.
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: "VDS Platform Team"
  category: "infrastructure"
  tags:
    - cli
    - routing
    - orchestrators
    - platform
    - who
---

# VDS Scripts Skill

Use this skill as the **platform-routing entrypoint** for the WHO scripts ecosystem.

The VDS scripts ecosystem lives at `~/.claude/vds-scripts/` (installed via `vsaf global`).

This skill helps you:
- find the right `vds-cli` command family
- understand the current WHO scripts workspace surface
- identify whether a task belongs to a platform command or a specialist skill
- route humans and AI agents to the correct authoritative source

## When to Use

Use this skill when you need:
- a quick map of the WHO scripts ecosystem
- the right command family for a task
- the right specialist skill for deeper guidance
- bootstrap guidance for `vds-cli`, environment checks, and command discovery
- a capability index for current WHO automation surfaces

Do **not** use this skill as the authoritative deep runbook for:
- audit workflow execution → use `audit-orchestrator-skill`
- LLM-backed content evaluation → use `llm-analysis-skill`
- spec authoring/consolidation → use `spec-creation-skill`
- LSP setup and type-checking workflows → use `lsp-skill`
- circular dependency analysis → use `circular-dependency-skill`

## Canonical Sources

- Scripts workspace: `~/.claude/vds-scripts/`
- Installed by: `vsaf install vds-skill`

## Primary Command Entry Points

```bash
# Via uv run (cross-platform — recommended)
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli --help
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli confluence --help
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli jira --help
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli bitbucket --help
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli git --help

# Audit orchestrator
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit --help

# Spec orchestrator
uv run --directory ~/.claude/vds-scripts --package spec_orchestrator vds-spec --help
```

## Platform Command Families

### Bootstrap and discovery
- `vds-cli env ...`
- `vds-cli status`
- `vds-cli doctor`
- `vds-cli docs ...`

### Integrations
- `vds-cli jira ...`
- `vds-cli confluence ...`
- `vds-cli bitbucket ...`
- `vds-cli git ...`
- `vds-cli elastic ...`
- `vds-cli grafana ...`
- `vds-cli sonarqube ...`
- `vds-cli vidp ...` — VIDP third-party gateway (trigger workflows, poll job status)

### Documentation and validation
- `vds-cli openapi ...`
- `vds-cli links ...`
- `vds-cli structure ...`
- `vds-cli schema ...`
- `vds-cli pdf ...`
- `vds-cli diagrams ...`
- `vds-cli excel ...`
- `vds-cli google-sheets ...`
- `vds-markdown ...` via `markdown_orchestrator`

### Development and workflow
- `vds-cli intellij ...`
- `vds-cli tasks ...`
- `vds-cli lsp ...`
- `vds-cli spec ...`
- `vds-cli audit ...`
- `vds-cli circular-dependency ...`

## Specialist Routing Map

- Audit workflow execution and readiness gates → `audit-orchestrator-skill`
- LLM-assisted doc/content scoring → `llm-analysis-skill`
- Spec creation and consolidation → `spec-creation-skill`
- CLI/orchestrator development standards → `cli-development-skill`
- LSP configuration and usage → `lsp-skill`
- Circular dependency analysis → `circular-dependency-skill`
- Research-backed investigation → `research-skill`
- Structural graph review → `code-review-graph-skill`

## Mandatory Rules

### Confluence Content Export

When fetching or exporting Confluence page content (especially BRD, KBNV, SRS pages with tables and images), you **MUST** read and follow `references/confluence-content-export.md` before proceeding. Key rules:

0. **Output to `.vsaf/docs/confluence/<page-title>/`** — never to `docs/` at project root
1. **Use `body.storage`** (not `body.view`) as source of truth for image references
2. **Only download attachments referenced in `body.storage`** — never bulk-download all attachments
3. **Preserve image position** in output — replace `ac:image` with `![](images/...)` in-place, never collect at end
4. **Keep HTML tables** in markdown output — do not flatten to pipe tables
5. **Verify image count** matches between `body.storage` and output before reporting done

Failure to follow these rules causes silent data loss (wrong images downloaded, table structure destroyed, image↔text mapping broken).

## Progressive Disclosure

Use these bundled references for depth:
- `references/platform-bootstrap.md`
- `references/capability-index.md`
- `references/integration-commands.md`
- `references/validation-commands.md`
- `references/development-commands.md`
- `references/specialist-routing.md`
- `references/confluence-content-export.md`

## Notes

- Keep this file concise and routing-oriented; push deeper command catalogs into `references/`.
- For integrated `~/.claude/vds-scripts` workspace usage, Python 3.10+ is the preferred baseline.
- After updates, re-run `vsaf global` to sync skills to all agent surfaces.
