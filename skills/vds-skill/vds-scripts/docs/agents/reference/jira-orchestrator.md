<!-- diátaxis: reference -->

# Jira Orchestrator

> Manage Jira issues: create, update, query, transition, and comment on tickets within the WHO project.

## Scope

**What this orchestrator does:**
- Query Jira issues by key, project, Epic, assignee, or JQL.
- Create or update issues with structured fields.
- Transition issues through workflow states (e.g., To Do → In Progress → Done).
- Add worklog entries and comments.
- Generate Confluence pages from Epic scope data.

**What it does NOT do:**
- Does not create or modify Jira workflow schemas.
- Does not send arbitrary REST calls outside the Jira plugin surface.

**Primary users:** AI agents during audit triage; human project leads for progress tracking.

## CLI Entry

```bash
vds-cli jira --help
vds-cli jira-cli --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `get-issue` | Fetch a single issue by key | `--issue` |
| `search-issues` | JQL search with pagination | `--jql` |
| `create-issue` | Create a new ticket | `--project`, `--summary`, `--type` |
| `update-issue` | Update fields and labels | `--issue` |
| `transition-issue` | Move issue to a new status | `--issue`, `--transition-id` |
| `add-comment` | Append comment to an issue | `--issue`, `--text` |
| `add-worklog` | Log time on an issue | `--issue`, `--duration` |
| `from-epic-to-confluence` | Export Epic children to Confluence | `--epic-key` |

## Common Workflows

### Workflow 1: Audit Triage
1. Run `vds-cli audit` to identify findings.
2. Use `vds-cli jira create-issue --project=PAR --type=Bug` to create tickets.
3. Use `vds-cli jira transition-issue` to send tickets to In Review.
4. Link evidence files from Confluence pages.

### Workflow 2: Sprint Planning
1. Query open tasks: `vds-cli jira search-issues --jql='PROJECT="TTCN24" AND status="Open"'`.
2. Create sub-tasks under each Epic.
3. Assign and set start/end dates via `update-issue`.

## Related

- **Orchestrators:** [confluence](../confluence-workflow.md), [bitbucket](bitbucket-orchestrator.md), [spec](spec-orchestrator.md)
- **Skills:** [jira-skill](../../../../vds-skills/skills/)
- **Confluence:** TTCN24 project pages
- **Bitbucket:** vds-scripts repository
