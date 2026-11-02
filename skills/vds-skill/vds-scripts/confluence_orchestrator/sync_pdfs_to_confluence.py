#!/usr/bin/env python3
"""
Sync local PDF files with Confluence page attachments.

This script:
1. Lists local PDF files from a directory
2. Lists current attachments on a Confluence page
3. Matches PDF attachments by filename
4. Uploads/replaces PDF files on Confluence page
5. Optionally compares modification times with markdown sources
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from confluence_orchestrator.config import load_settings
from confluence_orchestrator.content import ContentClient
from confluence_orchestrator.http import ConfluenceClient
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="Sync local PDF files with Confluence page attachments")
console = Console()


def _build_http_client(settings, server: str) -> ConfluenceClient:
    """Build HTTP client for Confluence."""
    return ConfluenceClient(settings, server=server)


def _build_content_client(settings, server: str) -> ContentClient:
    """Build content client for Confluence."""
    http_client = _build_http_client(settings, server)
    return ContentClient(http_client)


def find_pdf_files(directory: Path, pattern: str | None = None, recursive: bool = True) -> list[Path]:
    """Find all PDF files in directory, optionally matching pattern."""
    pdf_files = sorted(directory.rglob("*.pdf")) if recursive else sorted(directory.glob("*.pdf"))
    if pattern:
        pdf_files = [f for f in pdf_files if pattern.lower() in f.name.lower()]
    return pdf_files


def match_attachments(
    local_pdfs: list[Path], confluence_attachments: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Match local PDF files with Confluence attachments by filename."""
    matches: dict[str, dict[str, Any]] = {}

    # Create lookup by filename (case-insensitive)
    attachment_lookup: dict[str, dict[str, Any]] = {}
    for att in confluence_attachments:
        filename = att.get("title", "").lower()
        attachment_lookup[filename] = att

    # Match local files to attachments
    for local_file in local_pdfs:
        filename_lower = local_file.name.lower()
        if filename_lower in attachment_lookup:
            matches[local_file.name] = {
                "local_file": local_file,
                "attachment": attachment_lookup[filename_lower],
                "action": "replace",
            }
        else:
            matches[local_file.name] = {
                "local_file": local_file,
                "attachment": None,
                "action": "upload",
            }

    return matches


@app.command("sync")
def sync_pdfs(
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    pdf_directory: Path = typer.Option(..., "--dir", "-d", help="Directory containing PDF files"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    pattern: str | None = typer.Option(None, "--pattern", "-p", help="Filter PDF files by pattern"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    comment: str | None = typer.Option(None, "--comment", "-c", help="Comment for attachment updates"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-confirm without prompting"),
) -> None:
    """Sync local PDF files with Confluence page attachments."""

    if not pdf_directory.exists() or not pdf_directory.is_dir():
        console.print(f"[red]Error: Directory not found: {pdf_directory}[/red]")
        raise typer.Exit(code=1) from None

    try:
        settings = load_settings(strict=True)
        server_key = server or settings.default_server
        client = _build_content_client(settings, server_key)

        # Get page info
        with console.status("[bold green]Fetching Confluence page info..."):
            page_info = client.get_page(page_id)
            page_title = page_info.get("title", "Unknown")

        console.print(f"\n[bold]Page:[/bold] {page_title} (ID: {page_id})")
        console.print(f"[bold]Server:[/bold] {server_key}\n")

        # List local PDF files
        console.print(f"[bold]Scanning PDF files in:[/bold] {pdf_directory}")
        local_pdfs = find_pdf_files(pdf_directory, pattern)

        if not local_pdfs:
            console.print("[yellow]No PDF files found in directory[/yellow]")
            raise typer.Exit(code=0) from None

        console.print(f"Found [green]{len(local_pdfs)}[/green] PDF file(s):")
        for pdf in local_pdfs:
            size = pdf.stat().st_size
            console.print(f"  • {pdf.name} ({size:,} bytes)")

        # List Confluence attachments
        console.print("\n[bold]Fetching Confluence attachments...[/bold]")
        attachments_result = client.list_attachments(page_id)
        # Handle both list and dict responses
        if isinstance(attachments_result, list):
            attachments = attachments_result
        elif isinstance(attachments_result, dict):
            attachments = attachments_result.get("results", [])
        else:
            attachments = []

        # Filter PDF attachments
        pdf_attachments = [att for att in attachments if att.get("title", "").lower().endswith(".pdf")]

        console.print(f"Found [green]{len(pdf_attachments)}[/green] PDF attachment(s) on page:")
        for att in pdf_attachments:
            name = att.get("title", "Unknown")
            size = att.get("size", 0)
            att_id = att.get("id", "Unknown")
            console.print(f"  • {name} (ID: {att_id}, {size:,} bytes)")

        # Match local files with attachments
        console.print("\n[bold]Matching files...[/bold]")
        matches = match_attachments(local_pdfs, pdf_attachments)

        # Display sync plan
        table = Table(title="Sync Plan", show_header=True, header_style="bold magenta")
        table.add_column("Local File", style="cyan")
        table.add_column("Action", style="yellow")
        table.add_column("Confluence Attachment", style="green")
        table.add_column("Size", justify="right")

        replace_count = 0
        upload_count = 0

        for filename, match_info in matches.items():
            local_file = match_info["local_file"]
            attachment = match_info["attachment"]
            action = match_info["action"]
            size = local_file.stat().st_size

            if action == "replace":
                replace_count += 1
                att_name = attachment.get("title", "Unknown") if attachment else "N/A"
                table.add_row(filename, "[yellow]REPLACE[/yellow]", att_name, f"{size:,} bytes")
            else:
                upload_count += 1
                table.add_row(filename, "[green]UPLOAD NEW[/green]", "—", f"{size:,} bytes")

        console.print(table)
        console.print(f"\n[bold]Summary:[/bold] {replace_count} to replace, {upload_count} to upload")

        if dry_run:
            console.print("\n[yellow]DRY RUN: No changes made[/yellow]")
            raise typer.Exit(code=0) from None

        # Confirm before proceeding
        if not yes and not typer.confirm("\n[bold]Proceed with sync?[/bold]"):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0) from None

        # Perform sync
        console.print("\n[bold]Syncing attachments...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Replace existing attachments
            for filename, match_info in matches.items():
                if match_info["action"] == "replace":
                    local_file = match_info["local_file"]
                    attachment = match_info["attachment"]
                    att_id = attachment.get("id")

                    task = progress.add_task(f"Replacing {filename}...", total=None)

                    # Update existing attachment
                    try:
                        client.update_attachment(
                            page_id,
                            att_id,
                            str(local_file),
                            filename=local_file.name,
                            content_type="application/pdf",
                            comment=comment or f"Updated from local file: {local_file.name}",
                        )
                        progress.update(task, completed=True)
                        console.print(f"  [green]✓[/green] Replaced {filename}")
                    except Exception as e:
                        progress.update(task, completed=True)
                        console.print(f"  [red]✗[/red] Failed to replace {filename}: {e}")

            # Upload new attachments
            for filename, match_info in matches.items():
                if match_info["action"] == "upload":
                    local_file = match_info["local_file"]

                    task = progress.add_task(f"Uploading {filename}...", total=None)

                    try:
                        client.upload_attachment(
                            page_id,
                            str(local_file),
                            filename=local_file.name,
                            content_type="application/pdf",
                            comment=comment or f"Uploaded: {local_file.name}",
                        )
                        progress.update(task, completed=True)
                        console.print(f"  [green]✓[/green] Uploaded {filename}")
                    except Exception as e:
                        progress.update(task, completed=True)
                        console.print(f"  [red]✗[/red] Failed to upload {filename}: {e}")

        console.print("\n[bold green]Sync completed![/bold green]")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from None


@app.command("list")
def list_attachments(
    page_id: str = typer.Argument(..., help="Confluence page ID"),
    server: str | None = typer.Option(None, "--server", "-s", help="internal|external"),
    pdf_only: bool = typer.Option(False, "--pdf-only", help="Show only PDF attachments"),
) -> None:
    """List attachments on a Confluence page."""

    try:
        settings = load_settings(strict=True)
        server_key = server or settings.default_server
        client = _build_content_client(settings, server_key)

        # Get page info
        page_info = client.get_page(page_id)
        page_title = page_info.get("title", "Unknown")

        console.print(f"\n[bold]Page:[/bold] {page_title} (ID: {page_id})")
        console.print(f"[bold]Server:[/bold] {server_key}\n")

        # List attachments
        attachments_result = client.list_attachments(page_id)
        attachments = (
            attachments_result if isinstance(attachments_result, list) else attachments_result.get("results", [])
        )

        if pdf_only:
            attachments = [att for att in attachments if att.get("title", "").lower().endswith(".pdf")]

        if not attachments:
            console.print("[yellow]No attachments found[/yellow]")
            raise typer.Exit(code=0) from None

        table = Table(title="Attachments", show_header=True, header_style="bold magenta")
        table.add_column("Filename", style="cyan")
        table.add_column("ID", style="green")
        table.add_column("Size", justify="right")
        table.add_column("Type", style="yellow")

        for att in attachments:
            name = att.get("title", "Unknown")
            att_id = att.get("id", "Unknown")
            size = att.get("size", 0)
            mime_type = att.get("metadata", {}).get("mediaType", "unknown")

            table.add_row(name, att_id, f"{size:,} bytes", mime_type)

        console.print(table)

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
