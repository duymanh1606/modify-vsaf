from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from .orchestrator import RepoResult, RunSummary


def print_summary(summary: RunSummary) -> None:
    console = Console()

    header = (
        f"Total: {summary.total} | "
        f"Successes: {summary.successes} | "
        f"Updated: {summary.updates} | "
        f"Failures: {summary.failures}"
    )
    console.print(f"[bold cyan]Git operation summary[/bold cyan] :: {header}")

    if summary.failures == 0:
        return

    console.print("[bold red]Failures:[/bold red]")
    table = Table("Repository", "Project", "Message", show_lines=False)
    for result in _failed(summary.results.values()):
        table.add_row(result.repo.name, result.repo.project, result.message or "")
    console.print(table)


def _failed(results: Iterable[RepoResult]) -> list[RepoResult]:
    return [result for result in results if not result.success]


def write_json_report(
    summary: RunSummary,
    report_dir: Path,
    metadata: dict | None = None,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "timestamp": timestamp,
        "metadata": metadata or {},
        "summary": summary.to_dict(),
    }
    path = report_dir / f"git-run-{timestamp}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return path
