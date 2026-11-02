"""BRD coverage validation logic."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

REQUIRED_BRD_SECTIONS = [
    "3.1",
    "3.2",
    "3.3",
    "3.4",
    "3.5",
    "4.1",
    "4.2",
    "4.3",
    "4.4",
    "4.5",
    "4.6",
    "4.7",
    "4.8",
    "4.9",
    "4.10",
    "4.11",
]

HIGH_PRIORITY_SERVICES = {
    "insurance-policy-business": ["3.4", "4.5"],
    "insurance-proposal-business": ["3.3.5", "3.3.6", "3.3.7", "3.3.8"],
    "insurance-claim-business": ["3.5", "4.6"],
    "insurance-customer-business": ["3.1", "3.2", "4.4"],
    "insurance-product-catalog": ["4.3", "4.3.1"],
    "insurance-rating-engine": ["3.3.5", "4.3.3"],
    "insurance-renewal-process": ["3.4.2", "3.4.3", "3.4.4"],
}

BRD_PATTERN = re.compile(r"BRD.*?([34]\.\d+(?:\.\d+)*)", re.IGNORECASE)


def find_brd_references_in_file(file_path: Path) -> set[str]:
    """Find BRD section references in a file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        content = file_path.read_text(encoding="utf-8", errors="ignore")

    return set(BRD_PATTERN.findall(content))


def scan_documentation_for_brd_refs(docs_root: Path) -> dict[str, set[str]]:
    """Scan markdown files for BRD references."""
    coverage: dict[str, set[str]] = {}

    for md_file in docs_root.rglob("*.md"):
        if not md_file.is_file():
            continue
        refs = find_brd_references_in_file(md_file)
        if refs:
            coverage[str(md_file.relative_to(docs_root))] = refs

    return coverage


def _covered_sections(found_sections: set[str], required_sections: list[str]) -> set[str]:
    covered: set[str] = set()
    for found in found_sections:
        for required in required_sections:
            if found.startswith(required):
                covered.add(required)
    return covered


def _coverage_status(coverage: float) -> str:
    if coverage >= 100.0:
        return "EXCELLENT"
    if coverage >= 80.0:
        return "GOOD"
    return "POOR"


def validate_brd_coverage(
    docs_root: Path,
    required_sections: list[str] | None = None,
) -> dict[str, object]:
    """Validate BRD coverage completeness."""
    if not docs_root.exists():
        return {"error": f"Documentation root not found: {docs_root}"}

    required = required_sections or list(REQUIRED_BRD_SECTIONS)
    brd_coverage = scan_documentation_for_brd_refs(docs_root)

    found_sections: set[str] = set()
    for file_refs in brd_coverage.values():
        found_sections.update(file_refs)

    covered_sections = _covered_sections(found_sections, required)
    missing_sections = set(required) - covered_sections

    total_required = len(required)
    total_covered = len(covered_sections)
    coverage_percentage = (total_covered / total_required * 100.0) if total_required else 100.0

    return {
        "total_required": total_required,
        "total_covered": total_covered,
        "coverage_percentage": coverage_percentage,
        "covered_sections": sorted(covered_sections),
        "missing_sections": sorted(missing_sections),
        "found_references": {path: sorted(refs) for path, refs in brd_coverage.items()},
        "high_priority_services": HIGH_PRIORITY_SERVICES,
        "validation_timestamp": datetime.now().isoformat(),
        "status": _coverage_status(coverage_percentage),
    }


def write_report(report_path: Path, report: dict[str, object]) -> None:
    """Write JSON report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
