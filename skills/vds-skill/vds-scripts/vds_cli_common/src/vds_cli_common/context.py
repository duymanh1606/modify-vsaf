"""CLI Context for unified state management across VDS CLIs.

This module provides CLIContext, a dataclass that handles:
- TTY detection for adaptive output
- Color control (flags, env vars, TTY detection)
- Quiet mode for suppressing non-essential output
- JSON-only mode for machine-readable output

Usage:
    @app.callback()
    def callback(
        ctx: typer.Context,
        json_only: bool = typer.Option(False, "--json-only", "-j"),
        quiet: bool = typer.Option(False, "--quiet", "-q"),
        no_color: bool = typer.Option(False, "--no-color"),
        color: bool = typer.Option(False, "--color"),
    ):
        cli_ctx = CLIContext.from_options(
            json_only=json_only,
            quiet=quiet,
            no_color=no_color,
            force_color=color,
        )
        ctx.obj = {"cli_ctx": cli_ctx}
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typer
    from rich.console import Console


@dataclass
class CLIContext:
    """Unified CLI context for all VDS orchestrator CLIs.

    Handles TTY detection, color preferences, output mode, and quiet mode
    consistently across all CLIs.

    Attributes:
        json_only: Output clean JSON only (existing behavior)
        structured_logs: Emit JSON logs to stderr
        is_tty: Whether stdout is an interactive terminal
        no_color: Disable colors explicitly
        force_color: Force colors even in non-TTY
        quiet: Suppress progress and non-essential output
        no_input: Disable interactive prompts
    """

    # Core flags
    json_only: bool = False
    quiet: bool = False
    structured_logs: bool = False
    no_input: bool = False

    # Color control
    no_color: bool = False
    force_color: bool = False

    # Computed properties (set during initialization)
    _is_tty: bool = field(default=False, init=False)
    _console: Console | None = field(default=None, init=False, repr=False)
    _err_console: Console | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Detect TTY after initialization."""
        self._is_tty = sys.stdout.isatty()

    @classmethod
    def from_options(
        cls,
        *,
        json_only: bool = False,
        quiet: bool = False,
        structured_logs: bool = False,
        no_input: bool = False,
        no_color: bool = False,
        force_color: bool = False,
    ) -> CLIContext:
        """Factory method to create CLIContext from CLI options."""
        return cls(
            json_only=json_only,
            quiet=quiet,
            structured_logs=structured_logs,
            no_input=no_input,
            no_color=no_color,
            force_color=force_color,
        )

    @classmethod
    def from_typer_context(cls, ctx: typer.Context) -> CLIContext:  # type: ignore[name-defined]
        """Get CLIContext from Typer context, or create default.

        Args:
            ctx: Typer context object

        Returns:
            CLIContext from ctx.obj if available, else default CLIContext
        """
        if ctx.obj is not None:
            if isinstance(ctx.obj, CLIContext):
                return ctx.obj
            if isinstance(ctx.obj, dict) and "cli_ctx" in ctx.obj:
                cli_ctx = ctx.obj["cli_ctx"]
                if isinstance(cli_ctx, CLIContext):
                    return cli_ctx
        return cls()

    @property
    def is_tty(self) -> bool:
        """Whether stdout is an interactive terminal."""
        return self._is_tty

    @property
    def use_color(self) -> bool:
        """Determine if colors should be used.

        Precedence (highest to lowest):
        1. --no-color flag (disables)
        2. --color flag (enables)
        3. FORCE_COLOR env var (enables)
        4. NO_COLOR env var (disables)
        5. TTY detection (enables if TTY)
        6. json_only mode (disables)
        """
        # json_only always disables color
        if self.json_only:
            return False

        # CLI flags have highest precedence
        if self.no_color:
            return False
        if self.force_color:
            return True

        # Environment variables
        if os.environ.get("FORCE_COLOR"):
            return True
        if os.environ.get("NO_COLOR"):
            return False

        # Default to TTY detection
        return self._is_tty

    @property
    def use_rich_output(self) -> bool:
        """Whether to use Rich formatting (tables, panels, etc).

        Disabled when:
        - json_only mode is active
        - stdout is not a TTY (piped output)
        """
        if self.json_only:
            return False
        return self._is_tty

    @property
    def use_spinner(self) -> bool:
        """Whether to show spinners for long operations."""
        return self.use_rich_output and not self.quiet

    @property
    def use_progress(self) -> bool:
        """Whether to show progress bars for batch operations."""
        return self.use_rich_output and not self.quiet

    @property
    def show_hints(self) -> bool:
        """Whether to show hints and suggestions."""
        return not self.json_only and not self.quiet

    @property
    def console(self) -> Console:
        """Get the stdout console with appropriate settings."""
        if self._console is None:
            from rich.console import Console

            self._console = Console(
                force_terminal=self.force_color if self.force_color else None,
                no_color=not self.use_color,
            )
        return self._console

    @property
    def err_console(self) -> Console:
        """Get the stderr console with appropriate settings."""
        if self._err_console is None:
            from rich.console import Console

            self._err_console = Console(
                stderr=True,
                force_terminal=self.force_color if self.force_color else None,
                no_color=not self.use_color,
            )
        return self._err_console
