"""Run reporting utilities for the Jira orchestrator."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

TIMESTAMP_FMT = "%Y-%m-%dT%H-%M-%SZ"


@dataclass(slots=True)
class RunSummary:
    command: str
    args: list[str]
    exit_code: int
    duration_ms: int
    started_at: datetime
    finished_at: datetime

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def _ensure_directory(base: Path, timestamp: datetime) -> Path:
    day_dir = base / str(timestamp.year) / f"{timestamp.month:02d}" / f"{timestamp.day:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    return day_dir


def write_reports(summary: RunSummary, *, base_dir: Path, include_markdown: bool = True) -> Path:
    """Persist JSON (and optional Markdown) reports and return JSON path."""
    timestamp = summary.finished_at.astimezone(UTC)
    directory = _ensure_directory(base_dir, timestamp)
    slug = f"{timestamp.strftime(TIMESTAMP_FMT)}_{summary.command}"

    json_path = directory / f"{slug}.json"
    json_payload = {
        "command": summary.command,
        "args": summary.args,
        "exit_code": summary.exit_code,
        "duration_ms": summary.duration_ms,
        "started_at": summary.started_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "finished_at": summary.finished_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "success": summary.success,
    }
    json_path.write_text(json.dumps(json_payload, indent=2, sort_keys=True))

    if include_markdown:
        md_path = directory / f"{slug}.md"
        status = "✅ Success" if summary.success else "❌ Failure"
        md_lines = [
            f"# Jira Run Report — {summary.command}",
            "",
            f"- **Status**: {status} (exit code {summary.exit_code})",
            f"- **Duration**: {summary.duration_ms} ms",
            f"- **Started**: {json_payload['started_at']}",
            f"- **Finished**: {json_payload['finished_at']}",
        ]
        if summary.args:
            md_lines.append(f"- **Arguments**: {' '.join(summary.args)}")
        md_path.write_text("\n".join(md_lines) + "\n")

    return json_path
