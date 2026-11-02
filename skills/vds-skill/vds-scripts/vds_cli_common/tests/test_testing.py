"""Tests for testing utilities."""

from __future__ import annotations

import os
import sys

from vds_cli_common import CLIContext
from vds_cli_common.testing import (
    capture_output,
    create_test_context,
    create_test_output,
    mock_force_color_env,
    mock_no_color_env,
    mock_pipe,
    mock_tty,
)


class TestMockTty:
    """Tests for mock_tty context manager."""

    def test_mocks_isatty_true(self) -> None:
        """Test mock_tty makes isatty return True."""
        with mock_tty():
            assert sys.stdout.isatty() is True

    def test_restores_after_context(self) -> None:
        """Test mock_tty restores original after context."""
        original = sys.stdout.isatty()
        with mock_tty():
            pass
        # Should be restored (may still be True if actually TTY)
        assert sys.stdout.isatty() == original


class TestMockPipe:
    """Tests for mock_pipe context manager."""

    def test_mocks_isatty_false(self) -> None:
        """Test mock_pipe makes isatty return False."""
        with mock_pipe():
            assert sys.stdout.isatty() is False


class TestMockNoColorEnv:
    """Tests for mock_no_color_env context manager."""

    def test_sets_no_color_env(self) -> None:
        """Test mock_no_color_env sets NO_COLOR."""
        with mock_no_color_env():
            assert os.environ.get("NO_COLOR") == "1"

    def test_restores_after_context(self) -> None:
        """Test mock_no_color_env restores env after context."""
        original = os.environ.get("NO_COLOR")
        with mock_no_color_env():
            pass
        assert os.environ.get("NO_COLOR") == original


class TestMockForceColorEnv:
    """Tests for mock_force_color_env context manager."""

    def test_sets_force_color_env(self) -> None:
        """Test mock_force_color_env sets FORCE_COLOR."""
        with mock_force_color_env():
            assert os.environ.get("FORCE_COLOR") == "1"


class TestCaptureOutput:
    """Tests for capture_output context manager."""

    def test_captures_stdout(self) -> None:
        """Test capture_output captures stdout."""
        with capture_output() as captured:
            print("Hello")
        assert any("Hello" in s for s in captured["stdout"])

    def test_captures_stderr(self) -> None:
        """Test capture_output captures stderr."""
        with capture_output() as captured:
            print("Error", file=sys.stderr)
        assert any("Error" in s for s in captured["stderr"])

    def test_empty_by_default(self) -> None:
        """Test captured is empty by default."""
        with capture_output() as captured:
            pass
        assert captured["stdout"] == []
        assert captured["stderr"] == []


class TestCreateTestContext:
    """Tests for create_test_context helper."""

    def test_creates_context_with_defaults(self) -> None:
        """Test creates context with default settings."""
        ctx = create_test_context()
        assert isinstance(ctx, CLIContext)
        assert ctx.json_only is False
        assert ctx.quiet is False

    def test_creates_context_with_json_only(self) -> None:
        """Test creates context with json_only."""
        ctx = create_test_context(json_only=True)
        assert ctx.json_only is True

    def test_creates_context_with_quiet(self) -> None:
        """Test creates context with quiet mode."""
        ctx = create_test_context(quiet=True)
        assert ctx.quiet is True

    def test_creates_context_with_tty_mock(self) -> None:
        """Test creates context with TTY mocked."""
        ctx = create_test_context(is_tty=True)
        assert ctx.is_tty is True

        ctx = create_test_context(is_tty=False)
        assert ctx.is_tty is False


class TestCreateTestOutput:
    """Tests for create_test_output helper."""

    def test_creates_output_manager(self) -> None:
        """Test creates OutputManager."""
        from vds_cli_common import OutputManager

        output = create_test_output()
        assert isinstance(output, OutputManager)

    def test_uses_provided_context(self) -> None:
        """Test uses provided CLIContext."""
        ctx = create_test_context(json_only=True)
        output = create_test_output(ctx)
        assert output.ctx is ctx
        assert output.ctx.json_only is True
