"""Freshness report builder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from vds_cli.docs.types import FreshnessIssue

FreshnessStatus = Literal["stale", "draft", "orphan_vi", "fresh"]

_DRAFT_MARKER = "<!-- draft-translation: needs-human-review -->"


@dataclass(frozen=True)
class FreshnessRow:
    vi_path: Path
    en_path: Path
    en_mtime: datetime | None
    vi_mtime: datetime | None
    lag_days: int | None
    draft_marker_present: bool
    status: FreshnessStatus
    max_lag_days: int


def _file_mtime(path: Path) -> datetime | None:
    if not path.exists():
        return None
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=UTC)


def _has_draft_marker(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= 20:
                    break
                if _DRAFT_MARKER.lower() in line.lower():
                    return True
    except (OSError, UnicodeDecodeError):
        return False
    return False


def classify(row: FreshnessRow, threshold: int | None, include_drafts: bool) -> FreshnessStatus:
    if row.en_mtime is None:
        return "orphan_vi"
    if row.draft_marker_present and not include_drafts:
        return "draft"
    effective = threshold if threshold is not None else row.max_lag_days
    if row.lag_days is not None and row.lag_days > effective:
        return "stale"
    return "fresh"


def enrich(issues: list[FreshnessIssue]) -> list[FreshnessRow]:
    rows: list[FreshnessRow] = []
    for issue in issues:
        vi_path = Path(issue.doc)
        en_path = Path(issue.source)
        en_mtime = _file_mtime(en_path)
        vi_mtime = _file_mtime(vi_path)

        if en_mtime is not None and vi_mtime is not None:
            lag = max((en_mtime - vi_mtime).total_seconds() / 86400.0, 0.0)
            lag_days = int(lag)
        else:
            lag_days = None

        draft_marker_present = _has_draft_marker(vi_path)

        row = FreshnessRow(
            vi_path=vi_path,
            en_path=en_path,
            en_mtime=en_mtime,
            vi_mtime=vi_mtime,
            lag_days=lag_days,
            draft_marker_present=draft_marker_present,
            status="fresh",
            max_lag_days=issue.max_lag_days,
        )
        rows.append(row)
    return rows
