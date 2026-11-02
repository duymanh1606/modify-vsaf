"""Unit tests for Confluence tools.

Based on pytest v8.3.3+ API
Context7: /pytest-dev/pytest
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

pytestmark = pytest.mark.anyio


async def test_confluence_search_tool(client_session: ClientSession) -> None:
    """Test confluence_search tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "confluence_search" in tool_names


async def test_confluence_get_page_tool(client_session: ClientSession) -> None:
    """Test confluence_get_page tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "confluence_get_page" in tool_names
