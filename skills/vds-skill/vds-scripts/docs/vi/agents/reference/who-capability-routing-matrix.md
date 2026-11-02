<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# WHO Capability Routing Matrix

| Intent | Human Doc Surface | Command Family / CLI | Skill Owner |
|-------|--------------------|----------------------|-------------|
| Bootstrap workspace | `reference/vds-cli-reference.md` | `vds-cli env/status/doctor` | `vds-scripts-skill` |
| Use Jira/Confluence/Bitbucket/Git | `reference/cli-commands.md` | `vds-cli jira/confluence/bitbucket/git` | `vds-scripts-skill` |
| Validate docs or platform artifacts | `reference/cli-commands.md` | `vds-cli openapi/links/structure/schema/pdf/diagrams/excel/google-sheets` | `vds-scripts-skill` |
| Run audit workflow | `reference/cli-commands.md` + audit docs | `vds-cli audit` | `audit-orchestrator-skill` |
| Create or validate spec | scripts/spec docs | `vds-cli spec` | `spec-creation-skill` |
| Configure LSP | specialist docs | `vds-cli lsp` | `lsp-skill` |
| Analyze dependency cycles | specialist docs | `vds-cli circular-dependency` | `circular-dependency-skill` |
| Research a problem | skills references | mixed tools | `research-skill` |
