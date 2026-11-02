"""Output Manager for unified CLI output across VDS CLIs.

This module provides OutputManager, a class that handles:
- JSON output (compact/pretty based on mode)
- Rich tables, panels, and formatted output
- Spinners for long-running operations
- Progress bars for batch operations
- Error messages with hints

Usage:
    ctx = CLIContext.from_options(json_only=False)
    out = OutputManager(ctx)

    with out.spinner("Connecting..."):
        result = client.ping()

    out.output_json({"status": "ok"})
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.progress import Progress
    from rich.table import Table

    from .context import CLIContext


class NullProgress:
    """No-op progress bar for non-TTY environments."""

    def add_task(self, description: str, total: float = 100.0, **kwargs: Any) -> int:
        """Add a task (no-op)."""
        return 0

    def update(self, task_id: int, advance: float = 1.0, **kwargs: Any) -> None:
        """Update task progress (no-op)."""

    def __enter__(self) -> NullProgress:
        """Enter context."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context."""


class OutputManager:
    """Unified output manager for VDS CLIs.

    Handles all output operations with context-aware formatting:
    - JSON output (always clean, parseable)
    - Rich tables (TTY only)
    - Spinners (TTY only, respects quiet mode)
    - Progress bars (TTY only, respects quiet mode)
    - Error messages (always shown, styled for TTY)
    - Success/info/warning messages (respects quiet mode)

    Args:
        ctx: CLIContext instance for output settings
    """

    def __init__(self, ctx: CLIContext) -> None:
        """Initialize OutputManager with CLI context."""

        self.ctx: CLIContext = ctx
        self._console = ctx.console
        self._err_console = ctx.err_console

    def output_json(self, data: dict[str, Any] | list[Any], pretty: bool = True) -> None:
        """Output data as JSON to stdout.

        In json_only mode, always outputs compact JSON.
        Otherwise, outputs pretty-printed JSON or uses Rich JSON highlighting.

        Args:
            data: Data to output as JSON
            pretty: Whether to pretty-print (ignored in json_only mode)
        """
        if self.ctx.json_only:
            # Compact JSON for piping/parsing
            print(json.dumps(data, default=str, ensure_ascii=False))
        elif pretty and self.ctx.use_rich_output:
            # Pretty JSON with syntax highlighting
            from rich.json import JSON

            self._console.print(JSON.from_data(data))
        elif pretty:
            print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        else:
            print(json.dumps(data, default=str, ensure_ascii=False))

    def output_error(
        self,
        message: str,
        *,
        hint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Output error message to stderr.

        In json_only mode, outputs JSON error object.
        Otherwise, outputs styled error with optional hint.

        Args:
            message: Error message
            hint: Optional hint for resolution
            details: Optional additional details
        """
        if self.ctx.json_only:
            error_obj: dict[str, Any] = {"error": True, "message": message}
            if hint:
                error_obj["hint"] = hint
            if details:
                error_obj["details"] = details
            print(json.dumps(error_obj), file=sys.stderr)
        else:
            self._err_console.print(f"[bold red]✗ Error:[/bold red] {message}")
            if hint:
                self._err_console.print(f"[yellow]  💡 Hint:[/yellow] {hint}")
            if details:
                for key, value in details.items():
                    self._err_console.print(f"[dim]  {key}:[/dim] {value}")

    def output_success(self, message: str) -> None:
        """Output success message (suppressed in quiet/json mode).

        Args:
            message: Success message to display
        """
        if self.ctx.show_hints:
            self._console.print(f"[bold green]✓[/bold green] {message}")

    def output_warning(self, message: str) -> None:
        """Output warning message (suppressed in quiet/json mode).

        Args:
            message: Warning message to display
        """
        if self.ctx.show_hints:
            self._console.print(f"[bold yellow]⚠[/bold yellow] {message}")

    def output_info(self, message: str) -> None:
        """Output info message (suppressed in quiet/json mode).

        Args:
            message: Info message to display
        """
        if self.ctx.show_hints:
            self._console.print(f"[blue]ℹ[/blue] {message}")

    def suggest_next(self, commands: list[str]) -> None:
        """Suggest next commands to run (suppressed in quiet/json mode).

        Args:
            commands: List of suggested commands
        """
        if self.ctx.show_hints and commands:
            suggestions = ", ".join(f"[cyan]{cmd}[/cyan]" for cmd in commands)
            self._console.print(f"\n[dim]Try next:[/dim] {suggestions}")

    @contextmanager
    def spinner(self, message: str) -> Iterator[None]:
        """Show a spinner while executing a block.

        The spinner is only shown when:
        - stdout is a TTY
        - not in json_only mode
        - not in quiet mode

        Args:
            message: Message to display with spinner

        Yields:
            None
        """
        if not self.ctx.use_spinner:
            yield
            return

        with self._err_console.status(f"[bold green]{message}", spinner="dots"):
            yield

    @contextmanager
    def progress(
        self,
        description: str,
        total: float = 100.0,
    ) -> Iterator[Progress | NullProgress]:
        """Create a progress bar context.

        Returns NullProgress if progress should be hidden.

        Args:
            description: Description of the progress
            total: Total number of steps

        Yields:
            Progress bar instance (or NullProgress if hidden)
        """
        if not self.ctx.use_progress:
            yield NullProgress()
            return

        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
            TimeRemainingColumn,
        )

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self._err_console,
            transient=True,
        )

        with progress:
            yield progress

    def table(
        self,
        title: str | None = None,
        columns: list[str] | None = None,
        rows: list[list[Any]] | None = None,
    ) -> Table | None:
        """Create and optionally populate a Rich table for output.

        Returns None if tables should not be used (json_only or not TTY).

        Args:
            title: Optional table title
            columns: Optional list of column names
            rows: Optional list of row data

        Returns:
            Rich Table instance or None if tables shouldn't be used
        """
        if not self.ctx.use_rich_output:
            return None

        from rich.table import Table

        table = Table(title=title)
        if columns:
            for col in columns:
                table.add_column(col)
        if rows:
            for row in rows:
                table.add_row(*[str(cell) for cell in row])
        return table

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to console (respects color settings).

        Args:
            *args: Arguments to print
            **kwargs: Keyword arguments for console.print
        """
        self._console.print(*args, **kwargs)

    def print_err(self, *args: Any, **kwargs: Any) -> None:
        """Print to stderr (respects color settings).

        Args:
            *args: Arguments to print
            **kwargs: Keyword arguments for console.print
        """
        self._err_console.print(*args, **kwargs)
