"""Aggregate and summarize doc-consumption funnel data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vds_cli.docs.consumption.scanner import DocRead


@dataclass(frozen=True)
class FunnelRow:
    path: Path
    reads: int
    unique_sessions: int
    last_read: datetime | None
    diataxis: str | None


@dataclass(frozen=True)
class FunnelStageSummary:
    stage: str
    read_count: int
    unique_docs: int


def aggregate_reads(doc_reads: list[DocRead]) -> list[FunnelRow]:
    """Group DocRead events by path, counting reads and unique sessions."""
    groups: dict[Path, dict] = {}
    for dr in doc_reads:
        if dr.path not in groups:
            groups[dr.path] = {
                "reads": 0,
                "sessions": set(),
                "last_read": None,
                "diataxis": dr.diataxis,
            }
        info = groups[dr.path]
        info["reads"] += 1
        info["sessions"].add(dr.session_id)
        if info["last_read"] is None or dr.read_at > info["last_read"]:
            info["last_read"] = dr.read_at
    return [
        FunnelRow(
            path=path,
            reads=info["reads"],
            unique_sessions=len(info["sessions"]),
            last_read=info["last_read"],
            diataxis=info["diataxis"],
        )
        for path, info in sorted(groups.items())
    ]


def dead_weight(docs: list[DocRead], window_days: int) -> list[FunnelRow]:
    """Return docs with zero reads inside the look-back window."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=window_days)
    in_window = [d for d in docs if d.read_at >= cutoff]
    aggregated = {r.path: r for r in aggregate_reads(in_window)}
    all_paths = {d.path for d in docs}
    result: list[FunnelRow] = []
    for path in sorted(all_paths):
        if path in aggregated:
            continue
        diataxis = next((d.diataxis for d in docs if d.path == path), None)
        result.append(
            FunnelRow(
                path=path,
                reads=0,
                unique_sessions=0,
                last_read=None,
                diataxis=diataxis,
            )
        )
    return result


def funnel_summary(rows: list[FunnelRow]) -> list[FunnelStageSummary]:
    """Aggregate FunnelRows into per-Diátaxis stage summaries."""
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        stage = row.diataxis if row.diataxis is not None else "uncategorized"
        if stage not in counts:
            counts[stage] = {"read_count": 0, "unique_docs": 0}
        counts[stage]["read_count"] += row.reads
        counts[stage]["unique_docs"] += 1

    standard = ["tutorial", "how-to", "reference", "explanation"]
    for stage in standard:
        if stage not in counts:
            counts[stage] = {"read_count": 0, "unique_docs": 0}

    ordered = standard + [s for s in sorted(counts) if s not in standard]
    return [
        FunnelStageSummary(
            stage=stage,
            read_count=counts[stage]["read_count"],
            unique_docs=counts[stage]["unique_docs"],
        )
        for stage in ordered
    ]
