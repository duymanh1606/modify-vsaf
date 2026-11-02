#!/usr/bin/env python3
"""
Sync PDF files from markdown sources.

This script:
1. Scans directory for markdown files
2. Checks if corresponding PDF exists
3. Compares modification times
4. Regenerates PDFs using vds-cli pdf md2pdf when markdown is newer
5. Reports summary of regenerated/skipped files
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="Sync PDF files from markdown sources")
console = Console()

# Path to vds-scripts for running vds-cli (relative to script location)
VDS_SCRIPTS = Path(__file__).resolve().parent.parent


def find_markdown_files(directory: Path, pattern: str | None = None, recursive: bool = True) -> list[Path]:
    """Find all markdown files in directory, optionally matching pattern."""
    md_files = sorted(directory.rglob("*.md")) if recursive else sorted(directory.glob("*.md"))
    if pattern:
        md_files = [f for f in md_files if pattern.lower() in f.name.lower()]
    return md_files


def get_corresponding_pdf(md_file: Path) -> Path:
    """Get corresponding PDF path for a markdown file."""
    return md_file.with_suffix(".pdf")


def needs_regeneration(md_file: Path, pdf_file: Path, force: bool = False) -> bool:
    """Check if PDF needs regeneration based on modification times."""
    if force:
        return True
    if not pdf_file.exists():
        return True
    # Regenerate if markdown is newer than PDF
    md_mtime = md_file.stat().st_mtime
    pdf_mtime = pdf_file.stat().st_mtime
    return md_mtime > pdf_mtime


def regenerate_pdf(md_file: Path, pdf_file: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Regenerate PDF from markdown using vds-cli pdf md2pdf."""
    if dry_run:
        return True, "Would regenerate (dry-run)"

    try:
        # Ensure output directory exists
        pdf_file.parent.mkdir(parents=True, exist_ok=True)

        # Call vds-cli pdf md2pdf
        cmd = [
            "uv",
            "run",
            "--project",
            "vds_cli",
            "vds-cli",
            "pdf",
            "--",
            "md2pdf",
            str(md_file),
            "--output",
            str(pdf_file),
        ]

        result = subprocess.run(
            cmd,
            cwd=str(VDS_SCRIPTS),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            return True, "Regenerated successfully"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return False, f"Error: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "Timeout after 5 minutes"
    except Exception as e:
        return False, f"Exception: {e!s}"


@app.command()
def sync(
    directory: Path = typer.Argument(Path(), help="Directory to scan for markdown files"),
    pattern: str | None = typer.Option(None, "--pattern", "-p", help="Filter markdown files by pattern"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without regenerating PDFs"),
    force: bool = typer.Option(False, "--force", help="Regenerate all PDFs regardless of timestamps"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Scan subdirectories recursively"),
) -> None:
    """Sync PDFs from markdown sources."""

    directory = directory.resolve()
    if not directory.exists() or not directory.is_dir():
        console.print(f"[red]Error: Directory not found: {directory}[/red]")
        raise typer.Exit(code=1) from None

    try:
        # Find markdown files
        console.print(f"[bold]Scanning markdown files in:[/bold] {directory}")
        md_files = find_markdown_files(directory, pattern, recursive)

        if not md_files:
            console.print("[yellow]No markdown files found[/yellow]")
            raise typer.Exit(code=0) from None

        console.print(f"Found [green]{len(md_files)}[/green] markdown file(s)")

        # Check each markdown file
        to_regenerate: list[tuple[Path, Path]] = []
        skipped: list[tuple[Path, Path]] = []
        errors: list[tuple[Path, str]] = []

        console.print("\n[bold]Checking PDF status...[/bold]")
        for md_file in md_files:
            pdf_file = get_corresponding_pdf(md_file)
            if needs_regeneration(md_file, pdf_file, force):
                to_regenerate.append((md_file, pdf_file))
            else:
                skipped.append((md_file, pdf_file))

        # Display sync plan
        table = Table(title="Sync Plan", show_header=True, header_style="bold magenta")
        table.add_column("Markdown File", style="cyan")
        table.add_column("PDF File", style="green")
        table.add_column("Action", style="yellow")

        for md_file, pdf_file in to_regenerate:
            status = "REGENERATE" if pdf_file.exists() else "CREATE"
            table.add_row(
                str(md_file.relative_to(directory)),
                str(pdf_file.relative_to(directory)),
                f"[yellow]{status}[/yellow]",
            )

        for md_file, pdf_file in skipped:
            table.add_row(
                str(md_file.relative_to(directory)),
                str(pdf_file.relative_to(directory)),
                "[green]SKIP (in sync)[/green]",
            )

        if to_regenerate:
            console.print(table)
            console.print(f"\n[bold]Summary:[/bold] {len(to_regenerate)} to regenerate, {len(skipped)} skipped")

            if dry_run:
                console.print("\n[yellow]DRY RUN: No PDFs regenerated[/yellow]")
                raise typer.Exit(code=0) from None

            # Regenerate PDFs
            console.print("\n[bold]Regenerating PDFs...[/bold]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                for md_file, pdf_file in to_regenerate:
                    task = progress.add_task(f"Regenerating {md_file.name}...", total=None)

                    success, message = regenerate_pdf(md_file, pdf_file, dry_run=False)
                    progress.update(task, completed=True)

                    if success:
                        console.print(f"  [green]✓[/green] {md_file.name} → {pdf_file.name}")
                    else:
                        console.print(f"  [red]✗[/red] {md_file.name}: {message}")
                        errors.append((md_file, message))

            if errors:
                console.print(f"\n[yellow]Completed with {len(errors)} error(s)[/yellow]")
                for md_file, error_msg in errors:
                    console.print(f"  • {md_file.name}: {error_msg}")
                raise typer.Exit(code=2) from None
            else:
                console.print("\n[bold green]✓ All PDFs regenerated successfully![/bold green]")
        else:
            console.print("\n[green]All PDFs are in sync with markdown sources[/green]")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
