"""Confluence tools for MCP server.

Based on MCP Python SDK v1.0.0+
Context7: /modelcontextprotocol/python-sdk
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_confluence_tools(mcp: FastMCP, execute_cli: Callable[..., Any]) -> None:
    """Register Confluence tools with MCP server.

    Args:
        mcp: FastMCP server instance
        execute_cli: Function to execute VDS CLI commands
    """

    @mcp.tool()
    async def confluence_search(query: str, server: str = "internal", limit: int = 10) -> str:
        """Search Confluence content using CQL query.

        Args:
            query: CQL query string (e.g., "space = TDOV")
            server: Server to query ("internal" or "external", default: "internal")
            limit: Maximum number of results (default: 10)

        Returns:
            str: JSON-formatted search results
        """
        result = await execute_cli("confluence", "content", "search", query, f"--server={server}", f"--limit={limit}")
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]

    @mcp.tool()
    async def confluence_get_page(page_id: str, server: str = "internal") -> str:
        """Get Confluence page content.

        Args:
            page_id: Page ID (e.g., "99647801")
            server: Server to query ("internal" or "external", default: "internal")

        Returns:
            str: JSON-formatted page content
        """
        result = await execute_cli("confluence", "content", "page", page_id, f"--server={server}")
        if result["returncode"] != 0:
            return f"Error: {result['stderr']}"
        return result["stdout"]
