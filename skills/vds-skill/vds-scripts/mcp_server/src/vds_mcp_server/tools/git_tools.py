"""Git tools for MCP server.

Based on MCP Python SDK v1.0.0+
Context7: /modelcontextprotocol/python-sdk
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_git_tools(mcp: FastMCP, execute_cli: Callable[..., Any]) -> None:
    """Register Git tools with MCP server.

    Args:
        mcp: FastMCP server instance
        execute_cli: Function to execute VDS CLI commands
    """

    @mcp.tool()
    async def git_clone(project: str) -> str:
        """Clone a VDS project repository.

        Args:
            project: Project name (e.g., "lep", "insurance")

        Returns:
            str: Clone operation result
        """
        result = await execute_cli("git", "clone", project)
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]

    @mcp.tool()
    async def git_status(match: str | None = None) -> str:
        """Get Git repository status.

        Args:
            match: Pattern to match repositories (e.g., "*service*")

        Returns:
            str: Status information for matching repositories
        """
        args = ["git", "status"]
        if match:
            args.extend(["--match", match])
        result = await execute_cli(*args)
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]

    @mcp.tool()
    async def git_pull(project: str | None = None) -> str:
        """Pull latest changes from Git repositories.

        Args:
            project: Project name to pull (optional, pulls all if not specified)

        Returns:
            str: Pull operation result
        """
        args = ["git", "pull"]
        if project:
            args.extend(["--project", project])
        result = await execute_cli(*args)
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]
