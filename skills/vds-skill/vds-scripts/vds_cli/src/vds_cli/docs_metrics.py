"""Onboarding metrics and doc consumption observability."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class OnboardingFunnelStep:
    step_name: str
    step_number: int
    completion_count: int = 0
    drop_off_count: int = 0

    @property
    def completion_rate(self) -> float:
        return 0.0  # Placeholder — requires historical data


def generate_onboarding_funnel(repo_root: Path) -> dict[str, Any]:
    """Generate onboarding funnel report from repo evidence."""
    steps = [
        OnboardingFunnelStep("Clone repo", 1),
        OnboardingFunnelStep("Run vds-cli doctor", 2),
        OnboardingFunnelStep("Complete first audit", 3),
        OnboardingFunnelStep("Submit first PR", 4),
    ]

    # Heuristic: count git commits by new contributors as proxy
    # In production this would query a metrics database
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "repo": repo_root.name,
        "steps": [asdict(s) for s in steps],
        "note": "Historical completion rates require metrics backend integration.",
    }


def generate_freshness_heatmap(repos: list[Path]) -> dict[str, Any]:
    """Generate freshness heatmap data for all repos."""
    heatmap = {"generated_at": datetime.now(UTC).isoformat(), "repos": {}}
    for repo in repos:
        repo_data: dict[str, Any] = {"docs": [], "vi_lag_days": None}
        docs_dir = repo / "docs" / "agents"
        if docs_dir.exists():
            for md_path in sorted(docs_dir.rglob("*.md")):
                mtime = md_path.stat().st_mtime
                age_days = (datetime.now(UTC).timestamp() - mtime) / 86400
                repo_data["docs"].append(
                    {
                        "path": str(md_path.relative_to(repo)),
                        "age_days": round(age_days, 1),
                        "status": "fresh" if age_days < 30 else "stale" if age_days < 90 else "very_stale",
                    }
                )
        heatmap["repos"][repo.name] = repo_data
    return heatmap


def generate_monthly_consumption_report(repo_root: Path) -> dict[str, Any]:
    """Generate monthly doc consumption report."""
    return {
        "month": datetime.now(UTC).strftime("%Y-%m"),
        "repo": repo_root.name,
        "total_reads": 0,
        "unique_docs": 0,
        "sessions": 0,
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "Consumption metrics require Confluence API or Bitbucket analytics integration.",
        "top_docs": [],
        "least_read_docs": [],
    }
