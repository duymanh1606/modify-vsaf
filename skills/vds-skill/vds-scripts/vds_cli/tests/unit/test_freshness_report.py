"""Tests for docs.freshness.report module."""

from __future__ import annotations

import datetime
from pathlib import Path

from vds_cli.docs.freshness.report import (
    FreshnessRow,
    _file_mtime,
    _has_draft_marker,
    classify,
)


def _make_row(
    vi_path: str = "docs/vi/test.md",
    en_path: str = "docs/test.md",
    en_mtime: datetime.datetime | None = None,
    vi_mtime: datetime.datetime | None = None,
    lag_days: int | None = None,
    draft_marker: bool = False,
    max_lag_days: int = 7,
) -> FreshnessRow:
    return FreshnessRow(
        vi_path=Path(vi_path),
        en_path=Path(en_path),
        en_mtime=en_mtime,
        vi_mtime=vi_mtime,
        lag_days=lag_days,
        draft_marker_present=draft_marker,
        status="fresh",
        max_lag_days=max_lag_days,
    )


class TestFileMtime:
    def test_missing_file(self, tmp_path: Path) -> None:
        assert _file_mtime(tmp_path / "nope.md") is None

    def test_existing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "file.md"
        p.write_text("hello")
        mt = _file_mtime(p)
        assert mt is not None
        assert abs((datetime.datetime.now(datetime.UTC) - mt).total_seconds()) < 2


class TestHasDraftMarker:
    def test_present_in_first_20(self, tmp_path: Path) -> None:
        p = tmp_path / "draft.md"
        p.write_text("\n".join(["<!-- draft-translation: needs-human-review -->", "# Title"]))
        assert _has_draft_marker(p) is True

    def test_absent(self, tmp_path: Path) -> None:
        p = tmp_path / "clean.md"
        p.write_text("# Title\n")
        assert _has_draft_marker(p) is False

    def test_after_20_lines(self, tmp_path: Path) -> None:
        p = tmp_path / "late.md"
        p.write_text("\n".join(["# Title"] * 25 + ["<!-- draft-translation: needs-human-review -->"]))
        assert _has_draft_marker(p) is False


class TestClassify:
    def test_orphan_vi(self) -> None:
        row = _make_row(en_mtime=None)
        assert classify(row, threshold=None, include_drafts=False) == "orphan_vi"

    def test_draft_skips_stale(self) -> None:
        row = _make_row(
            en_mtime=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            vi_mtime=datetime.datetime(2025, 12, 1, tzinfo=datetime.UTC),
            lag_days=31,
            draft_marker=True,
            max_lag_days=7,
        )
        assert classify(row, threshold=None, include_drafts=False) == "draft"

    def test_include_drafts_allows_stale(self) -> None:
        row = _make_row(
            en_mtime=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            vi_mtime=datetime.datetime(2025, 12, 1, tzinfo=datetime.UTC),
            lag_days=31,
            draft_marker=True,
            max_lag_days=7,
        )
        assert classify(row, threshold=None, include_drafts=True) == "stale"

    def test_stale_breach(self) -> None:
        row = _make_row(
            en_mtime=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            vi_mtime=datetime.datetime(2025, 12, 1, tzinfo=datetime.UTC),
            lag_days=31,
            draft_marker=False,
            max_lag_days=7,
        )
        assert classify(row, threshold=None, include_drafts=False) == "stale"

    def test_fresh_healthy(self) -> None:
        row = _make_row(
            en_mtime=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            vi_mtime=datetime.datetime(2025, 12, 29, tzinfo=datetime.UTC),
            lag_days=3,
            draft_marker=False,
            max_lag_days=7,
        )
        assert classify(row, threshold=None, include_drafts=False) == "fresh"

    def test_threshold_override(self) -> None:
        row = _make_row(
            en_mtime=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            vi_mtime=datetime.datetime(2025, 12, 1, tzinfo=datetime.UTC),
            lag_days=31,
            draft_marker=False,
            max_lag_days=7,
        )
        # threshold=60 would make lag_days <= threshold → fresh
        assert classify(row, threshold=60, include_drafts=False) == "fresh"

    def test_orphan_never_stale(self) -> None:
        row = _make_row(en_mtime=None, lag_days=None, draft_marker=False, max_lag_days=7)
        # Even with a low threshold, orphan_vi takes priority
        assert classify(row, threshold=0, include_drafts=False) == "orphan_vi"
