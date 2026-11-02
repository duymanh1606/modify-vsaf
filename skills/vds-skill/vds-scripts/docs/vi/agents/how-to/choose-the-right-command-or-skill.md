<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# Choose The Right WHO Command Or Skill

Use this guide when you know the task you want to perform but are not sure whether to start with a CLI command family or a specialist skill.

## Step 1: Is this a platform-routing question?

Use `vds-scripts-skill` when you need to:
- find the right WHO command family
- bootstrap the scripts workspace
- understand which workspace capability owns a task
- route to the correct specialist skill

## Step 2: Route by task intent

| Intent | Start Here |
|-------|------------|
| Run audit workflow, readiness, rerun, upload | `audit-orchestrator-skill` + `vds-cli audit` |
| Evaluate README/API docs/security docs with LLM support | `llm-analysis-skill` |
| Create or update specs | `spec-creation-skill` + `vds-cli spec` |
| Develop a CLI/orchestrator | `cli-development-skill` |
| Use Jira/Confluence/Bitbucket/Git | `vds-scripts-skill` + `vds-cli` integration family |
| Validate docs, links, schemas, OpenAPI, diagrams, sheets | `vds-scripts-skill` + validation family |
| Configure LSP | `lsp-skill` |
| Analyze dependency cycles | `circular-dependency-skill` |
| Research across local + external sources | `research-skill` |

## Step 3: Follow canonical sources

- Scripts: `WHO-project/vds-scripts/`
- Skills: `WHO-project/vds-skills/skills/`
- Do not edit `.agent/skills/` directly
- For shared env/config/cache path behavior, use `../reference/portable-paths-and-config.md`
