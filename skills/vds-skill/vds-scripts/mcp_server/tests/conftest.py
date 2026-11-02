"""Pytest configuration and fixtures for MCP server tests."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from vds_mcp_server.server import mcp

if TYPE_CHECKING:
    from mcp.client.session import ClientSession


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio backend for tests."""
    return "asyncio"


@pytest.fixture
async def client_session() -> AsyncGenerator[ClientSession]:
    """Create in-memory MCP client session for testing."""
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as session:
        yield session


@pytest.fixture
def mock_execute_cli() -> Mock:
    """Mock CLI execution function."""
    return Mock(return_value={"stdout": "test output", "stderr": "", "returncode": 0})
