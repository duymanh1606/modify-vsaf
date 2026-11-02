<!-- diátaxis: reference -->

# Orchestrator Comparison Matrix

Quick reference for selecting the right orchestrator for your task.

## By Use Case

### I want to audit code quality

| Orchestrator | Scope | Prerequisites | Output |
|-------------|-------|--------------|--------|
| `audit` | Multi-repo, department-level | Confluence access, checklist config | Scorecard, evidence |
| `sonarqube` | Single repo | SonarQube server | Issues, metrics, coverage |
| `hexagonal` | Single repo | Python source | Boundary violations |
| `public_interface` | Single repo | Python source | Import violations |

### I want to generate or update documentation

| Orchestrator | Scope | Prerequisites | Output |
|-------------|-------|--------------|--------|
| `confluence` | Pages, spaces | Confluence credentials | Uploaded pages |
| `markdown` | Files | — | Formatted markdown |
| `brd` | Business requirements | PRD input | BRD document |
| `spec` | VDS specs | Skill manifest | Validated spec |
| `diagrams` | Architecture | Code or config | Mermaid, PNG, PDF |

### I want to work with data

| Orchestrator | Scope | Prerequisites | Output |
|-------------|-------|--------------|--------|
| `db_query` | Ad-hoc SQL | DB connection | Query results |
| `elastic` | Logs, metrics | ES cluster | Search results |
| `schema` | Data formats | Source schema | Converted schema |
| `excel` | Spreadsheets | — | Processed Excel |
| `google_sheets` | Sheets | Google API | Synced data |
| `metabase` | Dashboards | Metabase instance | Embedded charts |

### I want to manage infrastructure

| Orchestrator | Scope | Prerequisites | Output |
|-------------|-------|--------------|--------|
| `git` | Repositories | Git access | Worktrees, operations |
| `scheduler` | Cron jobs | Redis | Scheduled tasks |
| `evolution` | Ecosystem health | Postgres | Evolution report |
| `links` | Internal links | — | Link health report |
| `structure` | Repo structure | — | Structure analysis |

### I want AI-assisted development

| Orchestrator | Scope | Prerequisites | Output |
|-------------|-------|--------------|--------|
| `memory` | Cross-session | Memory service | Persistent knowledge |
| `research` | Evidence | MCP router | Research report |
| `multi_agent` | Parallel agents | Workflow def | Aggregated results |
| `telegram` | Notifications | Bot token | Messages, alerts |
| `claude` | Claude API | Anthropic key | Generated content |
| `mcp` | MCP servers | Server config | Integrated tools |
| `lsp` | Code intelligence | LSP server | Diagnostics, refs |

## By Complexity

| Complexity | Orchestrators | Start With |
|-----------|---------------|-----------|
| Basic | audit, confluence, db_query, diagrams, progress, scheduler | `vds-cli <name> --help` |
| Intermediate | circular_dependency, elastic, git, hexagonal, links, memory, public_interface, schema, sonarqube, spec, structure | Read the how-to guide first |
| Advanced | brd, claude, evolution, excel, google_sheets, intellij, jira, lsp, markdown, mcp, metabase, multi_agent, openapi, pdf, research, telegram | Check prerequisites carefully |

## Quick Recommendations

| Task | Recommended | Why |
|------|------------|-----|
| First audit ever | `audit` | Built-in defaults, no extra config |
| Upload evidence | `confluence` | Automatic formatting |
| Check architecture | `hexagonal` + `public_interface` | Two views of same problem |
| Generate diagrams | `diagrams` | Mermaid output, version-controlled |
| Parallel work | `git worktree-create` | Isolated branches |
| Research topic | `research` | Combines local + web sources |
| Schedule reports | `scheduler` | Cron-like, Redis-backed |
