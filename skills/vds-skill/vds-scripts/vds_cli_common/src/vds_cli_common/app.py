"""VDS CLI application factory — vds_cli_common.app (TSK-7.16)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings

from vds_cli_common.context import CLIContext


def make_vds_app(
    *,
    name: str,
    help: str,
    settings_factory: Callable[[], BaseSettings],
) -> typer.Typer:
    """Return a Typer app wired with VDS standard global options.

    This factory is recommended for new CLIs only. Existing CLIs should
    keep the direct `typer.Typer()` + dedicated `_version_callback()`
    pattern used by `bitbucket_orchestrator/cli.py`, which preserves the
    established test-compatible callback and output behavior.

    Settings construction is deferred to the callback so each invocation
    gets a fresh instance — safe for pytest-xdist parallel test runs.
    """
    app = typer.Typer(name=name, help=help)

    @app.callback()
    def _callback(
        ctx: typer.Context,
        json: bool = typer.Option(False, "--json-only", "--json", help="Emit JSON to stdout only"),
        quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Structured logs"),
        no_color: bool = typer.Option(False, "--no-color", help="Disable colour"),
    ) -> None:
        settings_factory()
        ctx.obj = {
            "cli_ctx": CLIContext.from_options(
                json_only=json,
                quiet=quiet,
                structured_logs=verbose,
                no_color=no_color,
            )
        }

    return app


__all__ = ["make_vds_app"]
