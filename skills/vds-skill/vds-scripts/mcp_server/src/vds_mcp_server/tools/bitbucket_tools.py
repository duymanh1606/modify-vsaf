"""Bitbucket tools for MCP server.

Based on MCP Python SDK v1.0.0+
Context7: /modelcontextprotocol/python-sdk
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_bitbucket_tools(mcp: FastMCP, execute_cli: Callable[..., Any]) -> None:
    """Register Bitbucket tools with MCP server.

    Args:
        mcp: FastMCP server instance
        execute_cli: Function to execute VDS CLI commands
    """

    @mcp.tool()
    async def bitbucket_list_projects() -> str:
        """List all Bitbucket projects.

        Returns:
            str: JSON-formatted list of projects
        """
        result = await execute_cli("bitbucket", "projects")
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]

    @mcp.tool()
    async def bitbucket_list_repositories(project_key: str) -> str:
        """List repositories in a Bitbucket project.

        Args:
            project_key: Project key (e.g., "LEP")

        Returns:
            str: JSON-formatted list of repositories
        """
        result = await execute_cli("bitbucket", "repositories", project_key)
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]
