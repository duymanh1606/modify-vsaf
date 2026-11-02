"""Tests for OutputManager."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from vds_cli_common import CLIContext, OutputManager
from vds_cli_common.output import NullProgress


class TestNullProgress:
    """Tests for NullProgress class."""

    def test_add_task_returns_zero(self) -> None:
        """Test add_task returns 0."""
        progress = NullProgress()
        task_id = progress.add_task("Test", total=100)
        assert task_id == 0

    def test_update_is_noop(self) -> None:
        """Test update does nothing."""
        progress = NullProgress()
        # Should not raise
        progress.update(0, advance=1)

    def test_context_manager(self) -> None:
        """Test NullProgress works as context manager."""
        with NullProgress() as progress:
            assert isinstance(progress, NullProgress)


class TestOutputManager:
    """Tests for OutputManager class."""

    def test_output_json_compact_in_json_only_mode(self) -> None:
        """Test JSON output is compact in json_only mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=True)
            out = OutputManager(ctx)

            with patch("builtins.print") as mock_print:
                out.output_json({"key": "value"})
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                # Should be compact (no indentation)
                assert call_args == '{"key": "value"}'

    def test_output_json_pretty_in_normal_mode(self) -> None:
        """Test JSON output is pretty-printed in normal mode."""
        with patch("sys.stdout.isatty", return_value=False):
            ctx = CLIContext.from_options(json_only=False)
            out = OutputManager(ctx)

            with patch("builtins.print") as mock_print:
                out.output_json({"key": "value"}, pretty=True)
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                # Should be pretty-printed
                assert "  " in call_args or "\n" in call_args

    def test_output_error_json_format_in_json_only_mode(self) -> None:
        """Test error output is JSON in json_only mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=True)
            out = OutputManager(ctx)

            with patch("builtins.print") as mock_print:
                out.output_error("Test error", hint="Test hint")
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                error_obj = json.loads(call_args)
                assert error_obj["error"] is True
                assert error_obj["message"] == "Test error"
                assert error_obj["hint"] == "Test hint"

    def test_output_error_with_details(self) -> None:
        """Test error output includes details."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=True)
            out = OutputManager(ctx)

            with patch("builtins.print") as mock_print:
                out.output_error("Error", details={"key": "value"})
                call_args = mock_print.call_args[0][0]
                error_obj = json.loads(call_args)
                assert error_obj["details"] == {"key": "value"}

    def test_output_success_shown_when_hints_enabled(self) -> None:
        """Test success message is shown when hints enabled."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=False, quiet=False)
            out = OutputManager(ctx)

            # Mock the console print
            out._console = MagicMock()
            out.output_success("Success!")
            out._console.print.assert_called_once()

    def test_output_success_hidden_in_quiet_mode(self) -> None:
        """Test success message is hidden in quiet mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(quiet=True)
            out = OutputManager(ctx)

            out._console = MagicMock()
            out.output_success("Success!")
            out._console.print.assert_not_called()

    def test_output_warning_shown_when_hints_enabled(self) -> None:
        """Test warning message is shown when hints enabled."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=False, quiet=False)
            out = OutputManager(ctx)

            out._console = MagicMock()
            out.output_warning("Warning!")
            out._console.print.assert_called_once()

    def test_output_info_shown_when_hints_enabled(self) -> None:
        """Test info message is shown when hints enabled."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=False, quiet=False)
            out = OutputManager(ctx)

            out._console = MagicMock()
            out.output_info("Info!")
            out._console.print.assert_called_once()

    def test_suggest_next_shown_when_hints_enabled(self) -> None:
        """Test suggestions are shown when hints enabled."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options(json_only=False, quiet=False)
            out = OutputManager(ctx)

            out._console = MagicMock()
            out.suggest_next(["search", "count"])
            out._console.print.assert_called_once()

    def test_suggest_next_hidden_in_json_only_mode(self) -> None:
        """Test suggestions are hidden in json_only mode."""
        ctx = CLIContext.from_options(json_only=True)
        out = OutputManager(ctx)

        out._console = MagicMock()
        out.suggest_next(["search", "count"])
        out._console.print.assert_not_called()

    def test_suggest_next_empty_list(self) -> None:
        """Test suggest_next with empty list does nothing."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options()
            out = OutputManager(ctx)

            out._console = MagicMock()
            out.suggest_next([])
            out._console.print.assert_not_called()

    def test_spinner_shown_in_tty(self) -> None:
        """Test spinner is shown in TTY mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options()
            out = OutputManager(ctx)

            out._err_console = MagicMock()
            out._err_console.status = MagicMock()

            with out.spinner("Testing..."):
                pass

            out._err_console.status.assert_called_once()

    def test_spinner_hidden_in_pipe(self) -> None:
        """Test spinner is hidden when piped."""
        with patch("sys.stdout.isatty", return_value=False):
            ctx = CLIContext.from_options()
            out = OutputManager(ctx)

            out._err_console = MagicMock()

            # Should not call status
            with out.spinner("Testing..."):
                pass

            out._err_console.status.assert_not_called()

    def test_progress_returns_null_in_pipe(self) -> None:
        """Test progress returns NullProgress when piped."""
        with patch("sys.stdout.isatty", return_value=False):
            ctx = CLIContext.from_options()
            out = OutputManager(ctx)

            with out.progress("Test", total=100) as progress:
                assert isinstance(progress, NullProgress)

    def test_table_returns_none_in_json_only_mode(self) -> None:
        """Test table returns None in json_only mode."""
        ctx = CLIContext.from_options(json_only=True)
        out = OutputManager(ctx)

        table = out.table("Test", columns=["A", "B"])
        assert table is None

    def test_table_returns_table_in_tty(self) -> None:
        """Test table returns Rich Table in TTY mode."""
        with patch("sys.stdout.isatty", return_value=True):
            ctx = CLIContext.from_options()
            out = OutputManager(ctx)

            table = out.table("Test", columns=["A", "B"], rows=[["1", "2"]])
            assert table is not None

    def test_print_delegates_to_console(self) -> None:
        """Test print delegates to console."""
        ctx = CLIContext()
        out = OutputManager(ctx)

        out._console = MagicMock()
        out.print("Hello")
        out._console.print.assert_called_once_with("Hello")

    def test_print_err_delegates_to_err_console(self) -> None:
        """Test print_err delegates to err_console."""
        ctx = CLIContext()
        out = OutputManager(ctx)

        out._err_console = MagicMock()
        out.print_err("Error")
        out._err_console.print.assert_called_once_with("Error")
