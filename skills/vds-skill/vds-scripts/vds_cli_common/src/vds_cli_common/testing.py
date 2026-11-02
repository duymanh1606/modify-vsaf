"""Test fixtures and helpers for VDS CLI testing.

This module provides pytest fixtures and helper functions for testing
CLI components with TTY mocking, output capture, and environment control.

Usage:
    from vds_cli_common.testing import mock_tty, mock_pipe, create_test_context

    def test_tty_detection(mock_tty):
        ctx = CLIContext()
        assert ctx.is_tty is True

    def test_pipe_mode(mock_pipe):
        ctx = CLIContext()
        assert ctx.is_tty is False
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from .context import CLIContext
    from .output import OutputManager


@contextmanager
def mock_tty() -> Iterator[None]:
    """Context manager to mock stdout as a TTY.

    Usage:
        with mock_tty():
            ctx = CLIContext()
            assert ctx.is_tty is True

    Yields:
        None
    """
    with patch.object(sys.stdout, "isatty", return_value=True):
        yield


@contextmanager
def mock_pipe() -> Iterator[None]:
    """Context manager to mock stdout as a pipe (non-TTY).

    Usage:
        with mock_pipe():
            ctx = CLIContext()
            assert ctx.is_tty is False

    Yields:
        None
    """
    with patch.object(sys.stdout, "isatty", return_value=False):
        yield


@contextmanager
def mock_no_color_env() -> Iterator[None]:
    """Context manager to mock NO_COLOR environment variable.

    Usage:
        with mock_no_color_env():
            ctx = CLIContext()
            assert ctx.use_color is False

    Yields:
        None
    """
    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        yield


@contextmanager
def mock_force_color_env() -> Iterator[None]:
    """Context manager to mock FORCE_COLOR environment variable.

    Usage:
        with mock_force_color_env():
            ctx = CLIContext()
            assert ctx.use_color is True

    Yields:
        None
    """
    with patch.dict(os.environ, {"FORCE_COLOR": "1"}):
        yield


@contextmanager
def capture_output() -> Iterator[dict[str, list[str]]]:
    """Context manager to capture stdout and stderr for testing.

    Usage:
        with capture_output() as captured:
            print("Hello")
        assert "Hello" in captured["stdout"][0]

    Yields:
        Dictionary with "stdout" and "stderr" lists
    """
    captured: dict[str, list[str]] = {"stdout": [], "stderr": []}


    def mock_stdout_write(text: str) -> int:
        if text.strip():  # Skip empty/whitespace-only
            captured["stdout"].append(text)
        return len(text)

    def mock_stderr_write(text: str) -> int:
        if text.strip():  # Skip empty/whitespace-only
            captured["stderr"].append(text)
        return len(text)

    with patch.object(sys.stdout, "write", mock_stdout_write), patch.object(sys.stderr, "write", mock_stderr_write):
        yield captured


def create_test_context(
    *,
    json_only: bool = False,
    quiet: bool = False,
    no_color: bool = False,
    force_color: bool = False,
    is_tty: bool = True,
) -> CLIContext:
    """Create a CLIContext for testing with specified settings.

    Args:
        json_only: Enable JSON-only mode
        quiet: Enable quiet mode
        no_color: Disable colors
        force_color: Force colors
        is_tty: Mock TTY detection result

    Returns:
        Configured CLIContext instance
    """
    from .context import CLIContext

    with patch.object(sys.stdout, "isatty", return_value=is_tty):
        return CLIContext.from_options(
            json_only=json_only,
            quiet=quiet,
            no_color=no_color,
            force_color=force_color,
        )


def create_test_output(ctx: CLIContext | None = None) -> OutputManager:
    """Create an OutputManager for testing.

    Args:
        ctx: Optional CLIContext (creates default if not provided)

    Returns:
        Configured OutputManager instance
    """
    from .output import OutputManager

    if ctx is None:
        ctx = create_test_context()
    return OutputManager(ctx)


# Pytest fixtures (can be used directly or as reference)
def pytest_fixtures() -> str:
    """Return pytest fixture definitions for copy-paste into conftest.py.

    Returns:
        String containing pytest fixture code
    """
    return '''
import pytest
from vds_cli_common.testing import (
    mock_tty as _mock_tty,
    mock_pipe as _mock_pipe,
    mock_no_color_env as _mock_no_color_env,
    mock_force_color_env as _mock_force_color_env,
)

@pytest.fixture
def mock_tty():
    """Mock stdout as a TTY."""
    with _mock_tty():
        yield

@pytest.fixture
def mock_pipe():
    """Mock stdout as a pipe (non-TTY)."""
    with _mock_pipe():
        yield

@pytest.fixture
def mock_no_color_env():
    """Mock NO_COLOR environment variable."""
    with _mock_no_color_env():
        yield

@pytest.fixture
def mock_force_color_env():
    """Mock FORCE_COLOR environment variable."""
    with _mock_force_color_env():
        yield
'''
