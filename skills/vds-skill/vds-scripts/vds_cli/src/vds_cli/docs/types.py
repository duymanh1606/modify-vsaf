"""Shared types for docs observability to resolve circular imports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationIssue:
    repo: str
    check: str
    message: str
    path: Path | None = None
    fixed: bool = False


@dataclass(frozen=True)
class FreshnessIssue:
    doc: str
    source: str
    max_lag_days: int
    lag_days: float
    message: str


FreshnessStatus = str  # "fresh" | "stale" | "draft" | "orphan_vi"
