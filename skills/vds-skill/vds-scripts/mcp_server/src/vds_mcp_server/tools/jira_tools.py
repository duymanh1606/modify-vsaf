"""JIRA tools for MCP server.

Based on MCP Python SDK v1.0.0+
Context7: /modelcontextprotocol/python-sdk
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_jira_tools(mcp: FastMCP, execute_cli: Callable[..., Any]) -> None:
    """Register JIRA tools with MCP server.

    Args:
        mcp: FastMCP server instance
        execute_cli: Function to execute VDS CLI commands
    """

    @mcp.tool()
    async def jira_search(query: str, limit: int = 20) -> str:
        """Search JIRA issues using JQL query.

        Args:
            query: JQL query string (e.g., "project = NTTC")
            limit: Maximum number of results (default: 20)

        Returns:
            str: JSON-formatted search results
        """
        result = await execute_cli("jira", "search", query, f"--limit={limit}")
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]

    @mcp.tool()
    async def jira_get_issue(issue_key: str) -> str:
        """Get JIRA issue details.

        Args:
            issue_key: Issue key (e.g., "NTTC-123")

        Returns:
            str: JSON-formatted issue details
        """
        result = await execute_cli("jira", "issue", issue_key)
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]

    @mcp.tool()
    async def jira_list_projects() -> str:
        """List all JIRA projects.

        Returns:
            str: JSON-formatted list of projects
        """
        result = await execute_cli("jira", "projects")
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]
