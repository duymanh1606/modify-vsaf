"""Unit tests for Bitbucket tools.

Based on pytest v8.3.3+ API
Context7: /pytest-dev/pytest
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

pytestmark = pytest.mark.anyio


async def test_bitbucket_list_projects_tool(client_session: ClientSession) -> None:
    """Test bitbucket_list_projects tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "bitbucket_list_projects" in tool_names


async def test_bitbucket_list_repositories_tool(client_session: ClientSession) -> None:
    """Test bitbucket_list_repositories tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "bitbucket_list_repositories" in tool_names
