# VDS MCP Server

Model Context Protocol (MCP) server for VDS Platform operations, enabling AI agents to interact with JIRA, Confluence,
Bitbucket, and Git through a standardized interface.

## Installation

```bash
cd vds-scripts
# Optional: sync every package once
./scripts/bootstrap_uv.sh

# Package-specific sync (only when you need dev extras)
uv sync --project mcp_server
```

## Usage

### Start MCP Server

```bash
# Using stdio transport (default)
uv run vds-cli mcp

# Or directly
uv run --project mcp_server python -m vds_mcp_server.server
```

### Available Tools

The MCP server exposes the following tools:

#### JIRA Tools

- `jira_search` - Search JIRA issues using JQL query
- `jira_get_issue` - Get JIRA issue details
- `jira_list_projects` - List all JIRA projects

#### Confluence Tools

- `confluence_search` - Search Confluence content using CQL query
- `confluence_get_page` - Get Confluence page content

#### Bitbucket Tools

- `bitbucket_list_projects` - List all Bitbucket projects
- `bitbucket_list_repositories` - List repositories in a project

#### Git Tools

- `git_clone` - Clone a VDS project repository
- `git_status` - Get Git repository status
- `git_pull` - Pull latest changes from Git repositories

## Client Integration

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vds-orchestrator": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/path/to/vds-scripts/mcp_server",
        "vds-cli mcp"
      ],
      "env": {
        "VDS_USERNAME": "${VDS_USERNAME}",
        "VDS_PASSWORD": "${VDS_PASSWORD}",
        "BITBUCKET_ACCESS_TOKEN": "${BITBUCKET_ACCESS_TOKEN}",
        "INTERNAL_CONFLUENCE_TOKEN": "${INTERNAL_CONFLUENCE_TOKEN}",
        "EXTERNAL_CONFLUENCE_TOKEN": "${EXTERNAL_CONFLUENCE_TOKEN}"
      }
    }
  }
}
```

### Using with Docker

```bash
cd vds-scripts/docker
docker-compose up -d mcp-server
```

## Development

### Running Tests

```bash
# Unit tests
uv run --project mcp_server pytest tests/unit/ -v

# Verification tests (requires credentials)
uv run --project mcp_server pytest tests/verification/ -v

# With coverage
uv run --project mcp_server pytest tests/ -v --cov=vds_mcp_server --cov-report=term-missing
```

### Code Quality

```bash
# Lint check
uv run --project mcp_server ruff check src/

# Format code
uv run --project mcp_server ruff format src/
```

## Architecture

The MCP server uses:

- **FastMCP**: High-level MCP server interface from official Python SDK
- **VDS CLI**: Executes commands via `vds-cli` subprocess
- **Tool Registration**: All tools registered at server startup

## Requirements

- Python >= 3.11
- uv (for package management)
- vds-cli (must be installed and available in PATH)
- Shared VDS env file with the required credentials

## Dependencies

- **mcp** >= 1.0.0 - Official MCP Python SDK (Context7: `/modelcontextprotocol/python-sdk`)
- **typer** >= 0.20.0 - CLI framework
- **pydantic** >= 2.12.3 - Data validation
- **pydantic-settings** >= 2.12.0 - Settings management

______________________________________________________________________

*Last updated: 2025-11-12*
