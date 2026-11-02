"""Version callback factory for VDS CLIs.

This module provides a factory function for creating --version flag callbacks
that work consistently across all VDS CLIs.

Usage:
    from vds_cli_common import create_version_callback

    version_callback = create_version_callback("vds-elastic-orchestrator")

    @app.callback()
    def main(
        version: bool = typer.Option(
            False,
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ):
        pass
"""

from __future__ import annotations

import importlib.metadata
from collections.abc import Callable

import typer


def create_version_callback(package_name: str) -> Callable[[bool], None]:
    """Create a version callback for a package.

    The callback prints the package version and exits when --version is provided.

    Args:
        package_name: The package name to look up version for

    Returns:
        A callback function suitable for typer.Option

    Example:
        version_callback = create_version_callback("vds-elastic-orchestrator")

        @app.callback()
        def main(
            version: bool = typer.Option(
                False,
                "--version",
                "-V",
                callback=version_callback,
                is_eager=True,
                help="Show version and exit",
            ),
        ):
            pass
    """

    def callback(value: bool) -> None:
        if value:
            try:
                version = importlib.metadata.version(package_name)
            except importlib.metadata.PackageNotFoundError:
                version = "unknown"
            typer.echo(f"{package_name} {version}")
            raise typer.Exit(0)

    return callback


def get_package_version(package_name: str) -> str:
    """Get the version of an installed package.

    Args:
        package_name: The package name to look up

    Returns:
        Version string or "unknown" if not found
    """
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"
