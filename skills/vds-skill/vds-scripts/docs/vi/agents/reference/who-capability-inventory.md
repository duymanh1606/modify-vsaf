<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# WHO Capability Inventory

This document records the current WHO ecosystem capability surface for routing, documentation, and validation.

## 1. Routed command surfaces

These are the primary user-facing command families exposed through `vds-cli`.

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

### Documentation and validation
- `vds-cli openapi ...`
- `vds-cli links ...`
- `vds-cli structure ...`
- `vds-cli schema ...`
- `vds-cli pdf ...`
- `vds-cli diagrams ...`
- `vds-cli excel ...`
- `vds-cli google-sheets ...`

### Development and workflow
- `vds-cli intellij ...`
- `vds-cli tasks ...`
- `vds-cli lsp ...`
- `vds-cli spec ...`
- `vds-cli audit ...`
- `vds-cli circular-dependency ...`

## 2. Standalone workspace capabilities

These WHO packages matter operationally even if they are not all presented as primary routed command families inside one platform skill.

- `markdown_orchestrator`
- `hexagonal_orchestrator`
- `mcp_server`
- `multi_agent_orchestrator`

## 3. Shared and internal support layers

These shape the ecosystem but are not primary user task entrypoints.

- `vds_cli_common`

## 4. Skills ecosystem linkage

The WHO skills catalog provides specialist workflow ownership alongside the scripts workspace.

### Platform-routing skill
- `vds-scripts-skill`

### Specialist skills
- `audit-orchestrator-skill`
- `llm-analysis-skill`
- `spec-creation-skill`
- `cli-development-skill`
- `lsp-skill`
- `circular-dependency-skill`
- `research-skill`
- `code-review-graph-skill`
- `app-config-discovery-skill`
- `repomix-skill`
- `grepai-skill`
- `hexagonal-compliance-skill`
- `vds-ai-memory-skill`

## 5. Derived and generated surfaces

These are important for agents and operators but are not canonical authoring roots.

- `WHO-project/vds-skills/registry.yaml`
- `WHO-project/vds-skills/AGENTS.md`
- root generated `AGENTS.md`
- `.agent/skills/`

## 6. Validation use

Use this inventory with:
- `vds-scripts-skill` references
- `docs/agents/reference/who-capability-routing-matrix.md`
- `WHO-project/vds-skills/registry.yaml`
- alignment/sync checks before closure
