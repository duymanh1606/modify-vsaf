"""Unit tests for Git tools.

Based on pytest v8.3.3+ API
Context7: /pytest-dev/pytest
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

pytestmark = pytest.mark.anyio


async def test_git_clone_tool(client_session: ClientSession) -> None:
    """Test git_clone tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "git_clone" in tool_names


async def test_git_status_tool(client_session: ClientSession) -> None:
    """Test git_status tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "git_status" in tool_names


async def test_git_pull_tool(client_session: ClientSession) -> None:
    """Test git_pull tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "git_pull" in tool_names
