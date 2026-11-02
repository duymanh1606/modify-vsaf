<!-- diátaxis: reference -->

# MCP Orchestrator

> MCP (Model Context Protocol) stdio server exposing VDS platform tools to AI agents.

## Scope

- **Does:** Run a FastMCP stdio server that registers Jira, Confluence, Bitbucket, and Git tools callable by MCP clients.
- **Does NOT:** Replace direct `vds-cli` usage, manage LLM provider authentication, or expose arbitrary shell execution.
- **Primary users:** AI agents (tool dispatch via MCP), IDE integrations (Claude Desktop, Cursor), developers (MCP plumbing).

## CLI Entry

```bash
# Via unified router
vds-cli mcp --help

# Direct entry
vds-cli mcp-server --help
```

## Server Behavior

The server starts over stdio transport by default. It loads shared VDS environment configuration on startup and exposes the following tool categories:

| Tool Category | Tools |
|---------------|-------|
| Jira | `jira_search`, `jira_get_issue` |
| Confluence | `confluence_search` |
| Bitbucket | `bitbucket_list_projects`, `bitbucket_list_repositories` |
| Git | `git_clone`, `git_status` |

Each tool delegates to `vds-cli` via subprocess and returns stdout/stderr/returncode.

## Tool Examples

```json
// jira_search
{"query": "project = NTTC AND status = Open", "limit": 20}

// confluence_search
{"query": "space = TDOV", "server": "internal", "limit": 10}

// bitbucket_list_repositories
{"project_key": "LEP"}

// git_clone
{"project": "lep"}
```

## Configuration

Requires shared VDS environment (`~/.vds/.env`) with:
- `VDS_JIRA_*` credentials for Jira tools
- `VDS_CONFLUENCE_*` credentials for Confluence tools
- `VDS_BITBUCKET_*` credentials for Bitbucket tools

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Server started successfully |
| 1 | Configuration or runtime error |

## Workflow Examples

```bash
# Start the MCP server (stdio transport)
vds-cli mcp-server

# Start via unified router
vds-cli mcp

# Configure in Claude Desktop (example)
# {
#   "mcpServers": {
#     "vds": {
#       "command": "vds-cli mcp-server"
#     }
#   }
# }
```

## Related

- **Orchestrators:** [jira](jira-orchestrator.md), [confluence](confluence-orchestrator.md), [bitbucket](bitbucket-orchestrator.md)
- **Skills:** [research-skill](../../../../vds-skills/skills/research-skill/SKILL.md)
