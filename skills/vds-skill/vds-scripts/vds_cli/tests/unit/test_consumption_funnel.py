"""Tests for vds_cli.docs.consumption.funnel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from vds_cli.docs.consumption.funnel import (
    FunnelRow,
    FunnelStageSummary,
    aggregate_reads,
    dead_weight,
    funnel_summary,
)
from vds_cli.docs.consumption.scanner import DocRead


def _dt(days_ago: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days_ago)


class TestDiataxisBucketing:
    def test_diataxis_bucketing(self) -> None:
        rows = [
            FunnelRow(
                path=Path("a.md"),
                reads=1,
                unique_sessions=1,
                last_read=_dt(1),
                diataxis="tutorial",
            ),
            FunnelRow(
                path=Path("b.md"),
                reads=2,
                unique_sessions=1,
                last_read=_dt(1),
                diataxis="how-to",
            ),
        ]
        summary = funnel_summary(rows)
        assert summary == [
            FunnelStageSummary(stage="tutorial", read_count=1, unique_docs=1),
            FunnelStageSummary(stage="how-to", read_count=2, unique_docs=1),
            FunnelStageSummary(stage="reference", read_count=0, unique_docs=0),
            FunnelStageSummary(stage="explanation", read_count=0, unique_docs=0),
        ]


class TestDeadWeightBoundary:
    def test_dead_weight_boundary(self) -> None:
        path_a = Path("stale.md")
        path_b = Path("fresh.md")
        docs = [
            DocRead(path=path_a, session_id="s1", read_at=_dt(70), diataxis="reference"),
            DocRead(path=path_b, session_id="s1", read_at=_dt(30), diataxis="how-to"),
        ]
        result = dead_weight(docs, window_days=60)
        assert len(result) == 1
        assert result[0].path == path_a
        assert result[0].reads == 0
        assert result[0].unique_sessions == 0
        assert result[0].last_read is None
        assert result[0].diataxis == "reference"

    def test_dead_weight_window_zero(self) -> None:
        path_a = Path("a.md")
        docs = [DocRead(path=path_a, session_id="s1", read_at=_dt(1), diataxis=None)]
        result = dead_weight(docs, window_days=0)
        assert len(result) == 1
        assert result[0].reads == 0


class TestAggregateReads:
    def test_same_doc_three_times_one_session(self) -> None:
        path = Path("x.md")
        docs = [
            DocRead(path=path, session_id="s1", read_at=_dt(1), diataxis="tutorial"),
            DocRead(path=path, session_id="s1", read_at=_dt(2), diataxis="tutorial"),
            DocRead(path=path, session_id="s1", read_at=_dt(3), diataxis="tutorial"),
        ]
        rows = aggregate_reads(docs)
        assert len(rows) == 1
        assert rows[0].reads == 3
        assert rows[0].unique_sessions == 1

    def test_same_doc_three_times_two_sessions(self) -> None:
        path = Path("y.md")
        docs = [
            DocRead(path=path, session_id="s1", read_at=_dt(1), diataxis="how-to"),
            DocRead(path=path, session_id="s2", read_at=_dt(2), diataxis="how-to"),
            DocRead(path=path, session_id="s2", read_at=_dt(3), diataxis="how-to"),
        ]
        rows = aggregate_reads(docs)
        assert len(rows) == 1
        assert rows[0].reads == 3
        assert rows[0].unique_sessions == 2


class TestFunnelSummaryEmpty:
    def test_funnel_summary_empty(self) -> None:
        assert funnel_summary([]) == [
            FunnelStageSummary(stage="tutorial", read_count=0, unique_docs=0),
            FunnelStageSummary(stage="how-to", read_count=0, unique_docs=0),
            FunnelStageSummary(stage="reference", read_count=0, unique_docs=0),
            FunnelStageSummary(stage="explanation", read_count=0, unique_docs=0),
        ]
