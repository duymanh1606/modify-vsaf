from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from confluence_orchestrator.reporting import RunSummary, write_reports


def test_write_reports_creates_json_and_markdown(tmp_path: Path) -> None:
    summary = RunSummary(
        command="templates",
        args=["--server", "internal"],
        server="internal",
        exit_code=0,
        duration_ms=1200,
        started_at=datetime(2025, 11, 4, 10, 0, 0, tzinfo=UTC),
        finished_at=datetime(2025, 11, 4, 10, 0, 2, tzinfo=UTC),
    )

    json_path = write_reports(summary, base_dir=tmp_path, include_markdown=True)
    assert json_path.exists()
    md_path = json_path.with_suffix(".md")
    assert md_path.exists()
    assert "✅ Success" in md_path.read_text()
