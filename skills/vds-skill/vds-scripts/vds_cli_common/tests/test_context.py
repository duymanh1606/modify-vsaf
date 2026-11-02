"""Tests for CLIContext."""

from __future__ import annotations

import os
from unittest.mock import patch

from vds_cli_common import CLIContext


class TestCLIContext:
    """Tests for CLIContext class."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        ctx = CLIContext()
        assert ctx.json_only is False
        assert ctx.quiet is False
        assert ctx.structured_logs is False
        assert ctx.no_input is False
        assert ctx.no_color is False
        assert ctx.force_color is False

    def test_from_options_factory(self) -> None:
        """Test from_options factory method."""
        ctx = CLIContext.from_options(
            json_only=True,
            quiet=True,
            no_color=True,
        )
        assert ctx.json_only is True
        assert ctx.quiet is True
        assert ctx.no_color is True

    def test_is_tty_detected_in_tty(self) -> None:
        """Test TTY is detected when stdout is a terminal."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext()
            assert ctx.is_tty is True

    def test_is_tty_detected_in_pipe(self) -> None:
        """Test TTY is not detected when stdout is piped."""
        with patch("sys.stdout.isatty", return_value=False):
            ctx = CLIContext()
            assert ctx.is_tty is False

    def test_use_color_disabled_by_json_only(self) -> None:
        """Test json_only mode disables colors."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=True)
            assert ctx.use_color is False

    def test_use_color_disabled_by_no_color_flag(self) -> None:
        """Test --no-color flag disables colors."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(no_color=True)
            assert ctx.use_color is False

    def test_use_color_enabled_by_force_color_flag(self) -> None:
        """Test --color flag enables colors."""
        with patch("sys.stdout.isatty", return_value=False):
            ctx = CLIContext.from_options(force_color=True)
            assert ctx.use_color is True

    def test_no_color_flag_overrides_force_color(self) -> None:
        """Test --no-color flag takes precedence over --color."""
        ctx = CLIContext.from_options(no_color=True, force_color=True)
        assert ctx.use_color is False

    def test_no_color_env_var_respected(self) -> None:
        """Test NO_COLOR environment variable disables colors."""
        with patch("sys.stdout.isatty", return_value=True), patch.dict(os.environ, {"NO_COLOR": "1"}):
            ctx = CLIContext()
            assert ctx.use_color is False

    def test_force_color_env_var_respected(self) -> None:
        """Test FORCE_COLOR environment variable enables colors."""
        with patch("sys.stdout.isatty", return_value=False):
            with patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
                # Clear NO_COLOR if present
                env = os.environ.copy()
                env.pop("NO_COLOR", None)
                env["FORCE_COLOR"] = "1"
                with patch.dict(os.environ, env, clear=True):
                    ctx = CLIContext()
                    assert ctx.use_color is True

    def test_use_rich_output_in_tty(self) -> None:
        """Test Rich output is enabled in TTY."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext()
            assert ctx.use_rich_output is True

    def test_use_rich_output_disabled_in_pipe(self) -> None:
        """Test Rich output is disabled when piped."""
        with patch("sys.stdout.isatty", return_value=False):
            ctx = CLIContext()
            assert ctx.use_rich_output is False

    def test_use_rich_output_disabled_by_json_only(self) -> None:
        """Test Rich output is disabled in json_only mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=True)
            assert ctx.use_rich_output is False

    def test_use_spinner_in_tty(self) -> None:
        """Test spinner is enabled in TTY."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext()
            assert ctx.use_spinner is True

    def test_use_spinner_disabled_by_quiet(self) -> None:
        """Test spinner is disabled in quiet mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(quiet=True)
            assert ctx.use_spinner is False

    def test_use_progress_in_tty(self) -> None:
        """Test progress is enabled in TTY."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext()
            assert ctx.use_progress is True

    def test_use_progress_disabled_by_quiet(self) -> None:
        """Test progress is disabled in quiet mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(quiet=True)
            assert ctx.use_progress is False

    def test_show_hints_enabled_by_default(self) -> None:
        """Test hints are shown by default."""
        ctx = CLIContext()
        assert ctx.show_hints is True

    def test_show_hints_disabled_by_json_only(self) -> None:
        """Test hints are hidden in json_only mode."""
        ctx = CLIContext.from_options(json_only=True)
        assert ctx.show_hints is False

    def test_show_hints_disabled_by_quiet(self) -> None:
        """Test hints are hidden in quiet mode."""
        ctx = CLIContext.from_options(quiet=True)
        assert ctx.show_hints is False

    def test_console_property_returns_console(self) -> None:
        """Test console property returns Rich Console."""
        ctx = CLIContext()
        console = ctx.console
        assert console is not None
        # Should return same instance on second call
        assert ctx.console is console

    def test_err_console_property_returns_stderr_console(self) -> None:
        """Test err_console property returns Rich Console for stderr."""
        ctx = CLIContext()
        err_console = ctx.err_console
        assert err_console is not None
        # Should return same instance on second call
        assert ctx.err_console is err_console

    def test_from_typer_context_with_cli_context(self) -> None:
        """Test from_typer_context extracts CLIContext."""
        from unittest.mock import MagicMock

        original_ctx = CLIContext.from_options(json_only=True)
        typer_ctx = MagicMock()
        typer_ctx.obj = original_ctx

        result = CLIContext.from_typer_context(typer_ctx)
        assert result is original_ctx

    def test_from_typer_context_with_dict(self) -> None:
        """Test from_typer_context extracts CLIContext from dict."""
        from unittest.mock import MagicMock

        original_ctx = CLIContext.from_options(quiet=True)
        typer_ctx = MagicMock()
        typer_ctx.obj = {"cli_ctx": original_ctx}

        result = CLIContext.from_typer_context(typer_ctx)
        assert result is original_ctx

    def test_from_typer_context_returns_default(self) -> None:
        """Test from_typer_context returns default when not found."""
        from unittest.mock import MagicMock

        typer_ctx = MagicMock()
        typer_ctx.obj = None

        result = CLIContext.from_typer_context(typer_ctx)
        assert isinstance(result, CLIContext)
        assert result.json_only is False
