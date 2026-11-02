"""CLI entry point for VDS Diagram Generator."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="vds-diagrams",
    help="VDS Diagram Generator - generate and validate diagram artifacts for the VDS codebase",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def generate() -> None:
    """Generate diagrams from codebase analysis.

    Placeholder command surface retained so AI agents and operators can discover
    the intended capability through `--help` even while the direct CLI remains a
    thin compatibility layer.
    """
    typer.echo(
        "Diagram generation is available through the maintained package surface, "
        "but this direct CLI compatibility layer remains intentionally minimal."
    )
    raise typer.Exit(0)


@app.command()
def validate() -> None:
    """Validate diagram definitions.

    Placeholder command surface retained so AI agents and operators can discover
    the intended capability through `--help`.
    """
    typer.echo(
        "Diagram validation is available through the maintained package surface, "
        "but this direct CLI compatibility layer remains intentionally minimal."
    )
    raise typer.Exit(0)


def main() -> None:
    """Main entry point for vds-diagrams CLI."""
    app()


if __name__ == "__main__":
    main()
