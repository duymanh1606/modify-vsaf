"""CLI for markdown validation and formatting."""

from __future__ import annotations

import subprocess
from pathlib import Path

import mdformat
import typer
from rich.console import Console

from vds_markdown_orchestrator import __version__

app = typer.Typer(name="vds-markdown", help="Markdown formatting and validation orchestrator")
console = Console()


def _tracked_markdown_files(*, staged: bool) -> list[Path]:
    cmd = ["git", "diff", "--name-only"]
    if staged:
        cmd.append("--cached")
    cmd.extend(["--", "*.md"])
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError:
        return []
    if result.returncode != 0:
        return []
    files = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    return [path for path in files if path.exists() and path.is_file()]


def _resolve_files(paths: list[str], *, staged: bool) -> list[Path]:
    if paths:
        resolved = [Path(path) for path in paths]
        return [path for path in resolved if path.exists() and path.is_file() and path.suffix.lower() == ".md"]
    return _tracked_markdown_files(staged=staged)


def _format_text(content: str, *, wrap: int) -> str:
    return mdformat.text(content, options={"wrap": wrap})


@app.command("check")
def check_cmd(
    paths: list[str] = typer.Argument(None, help="Markdown file paths"),
    staged: bool = typer.Option(False, "--staged", help="Check staged markdown files"),
    wrap: int = typer.Option(120, "--wrap", help="Target line wrap width"),
) -> None:
    """Check markdown formatting and exit non-zero if changes are needed."""
    files = _resolve_files(paths, staged=staged)
    if not files:
        console.print("[yellow]No markdown files found.[/yellow]")
        raise typer.Exit(0)

    not_formatted: list[Path] = []
    for file_path in files:
        original = file_path.read_text(encoding="utf-8")
        formatted = _format_text(original, wrap=wrap)
        if formatted != original:
            not_formatted.append(file_path)

    if not_formatted:
        for file_path in not_formatted:
            console.print(f"[red]needs formatting[/red] {file_path}")
        raise typer.Exit(1)

    console.print(f"[green]All {len(files)} markdown files are formatted.[/green]")


@app.command("format")
def format_cmd(
    paths: list[str] = typer.Argument(None, help="Markdown file paths"),
    staged: bool = typer.Option(False, "--staged", help="Format staged markdown files"),
    wrap: int = typer.Option(120, "--wrap", help="Target line wrap width"),
) -> None:
    """Format markdown files in place."""
    files = _resolve_files(paths, staged=staged)
    if not files:
        console.print("[yellow]No markdown files found.[/yellow]")
        raise typer.Exit(0)

    changed = 0
    for file_path in files:
        original = file_path.read_text(encoding="utf-8")
        formatted = _format_text(original, wrap=wrap)
        if formatted != original:
            file_path.write_text(formatted, encoding="utf-8")
            changed += 1
            console.print(f"[green]formatted[/green] {file_path}")

    console.print(f"[green]Updated {changed} file(s).[/green]")


@app.command("version")
def version_cmd() -> None:
    """Show version."""
    console.print(__version__)


if __name__ == "__main__":
    app()
