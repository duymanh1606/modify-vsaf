#!/usr/bin/env python3
"""
BRD Coverage Validation Script
Validates that all required BRD sections (3.1-3.5 and 4.1-4.11) are mapped to services.
"""

import json
import re
import sys
from pathlib import Path

# Required BRD sections
REQUIRED_BRD_SECTIONS = [
    # Customer features
    "3.1",
    "3.2",
    "3.3",
    "3.4",
    "3.5",
    # Admin features
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

# High-priority services with known BRD mappings
HIGH_PRIORITY_SERVICES = {
    "insurance-policy-business": ["3.4", "4.5"],
    "insurance-proposal-business": ["3.3.5", "3.3.6", "3.3.7", "3.3.8"],
    "insurance-claim-business": ["3.5", "4.6"],
    "insurance-customer-business": ["3.1", "3.2", "4.4"],
    "insurance-product-catalog": ["4.3", "4.3.1"],
    "insurance-rating-engine": ["3.3.5", "4.3.3"],
    "insurance-renewal-process": ["3.4.2", "3.4.3", "3.4.4"],
}


def find_brd_references_in_file(file_path: Path) -> set[str]:
    """Find all BRD section references in a file."""
    brd_refs = set()
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Pattern to match BRD references like "3.1", "4.5", "3.3.5", etc.
        pattern = r"BRD.*?([34]\.\d+(?:\.\d+)*)"
        matches = re.findall(pattern, content, re.IGNORECASE)

        for match in matches:
            brd_refs.add(match)

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return brd_refs


def scan_documentation_for_brd_refs(docs_root: Path) -> dict[str, set[str]]:
    """Scan all documentation files for BRD references."""
    brd_coverage = {}

    # Scan markdown files
    for md_file in docs_root.rglob("*.md"):
        if md_file.is_file():
            refs = find_brd_references_in_file(md_file)
            if refs:
                relative_path = str(md_file.relative_to(docs_root))
                brd_coverage[relative_path] = refs

    return brd_coverage


def validate_brd_coverage() -> dict:
    """Validate BRD coverage completeness."""

    # Get the documentation root
    script_dir = Path(__file__).parent
    docs_root = script_dir.parent / "insurance-document"

    if not docs_root.exists():
        docs_root = script_dir.parent.parent / "insurance-document"

    if not docs_root.exists():
        print(f"❌ Documentation root not found at {docs_root}")
        return {"error": "Documentation root not found"}

    print(f"🔍 Scanning documentation at: {docs_root}")

    # Scan for BRD references
    brd_coverage = scan_documentation_for_brd_refs(docs_root)

    # Collect all found BRD sections
    found_sections = set()
    for file_refs in brd_coverage.values():
        found_sections.update(file_refs)

    # Check coverage
    required_sections = set(REQUIRED_BRD_SECTIONS)
    covered_sections = set()

    # Map found sections to required sections
    for found in found_sections:
        for required in required_sections:
            if found.startswith(required):
                covered_sections.add(required)

    missing_sections = required_sections - covered_sections

    # Generate report
    report = {
        "total_required": len(required_sections),
        "total_covered": len(covered_sections),
        "coverage_percentage": (len(covered_sections) / len(required_sections)) * 100,
        "covered_sections": sorted(covered_sections),
        "missing_sections": sorted(missing_sections),
        "found_references": {k: sorted(v) for k, v in brd_coverage.items()},
        "high_priority_services": HIGH_PRIORITY_SERVICES,
    }

    return report


def print_coverage_report(report: dict):
    """Print a formatted coverage report."""

    if "error" in report:
        print(f"❌ {report['error']}")
        return

    print("\n" + "=" * 60)
    print("📊 BRD COVERAGE VALIDATION REPORT")
    print("=" * 60)

    print("\n📈 Coverage Summary:")
    print(f"   Total Required Sections: {report['total_required']}")
    print(f"   Covered Sections: {report['total_covered']}")
    print(f"   Coverage Percentage: {report['coverage_percentage']:.1f}%")

    if report["coverage_percentage"] >= 100:
        print("   ✅ 100% BRD coverage achieved!")
    elif report["coverage_percentage"] >= 80:
        print("   ⚠️  Good coverage, but some sections missing")
    else:
        print("   ❌ Insufficient BRD coverage")

    print(f"\n✅ Covered Sections ({len(report['covered_sections'])}):")
    for section in report["covered_sections"]:
        print(f"   • {section}")

    if report["missing_sections"]:
        print(f"\n❌ Missing Sections ({len(report['missing_sections'])}):")
        for section in report["missing_sections"]:
            print(f"   • {section}")

    print("\n🔍 High-Priority Service Mappings:")
    for service, sections in report["high_priority_services"].items():
        print(f"   • {service}: {', '.join(sections)}")

    print(f"\n📁 Files with BRD References ({len(report['found_references'])}):")
    for file_path, refs in list(report["found_references"].items())[:10]:  # Show first 10
        print(f"   • {file_path}: {', '.join(refs)}")

    if len(report["found_references"]) > 10:
        print(f"   ... and {len(report['found_references']) - 10} more files")


if __name__ == "__main__":
    print("🚀 Starting BRD Coverage Validation...")
    report = validate_brd_coverage()
    print_coverage_report(report)

    # Save report to file
    script_dir = Path(__file__).parent
    report_file = script_dir / "brd_coverage_report.json"

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Report saved to: {report_file}")

    # Exit with appropriate code
    if "error" in report:
        sys.exit(1)
    elif report["coverage_percentage"] < 100:
        print(f"\n⚠️  BRD coverage incomplete: {report['coverage_percentage']:.1f}%")
        sys.exit(1)
    else:
        print(f"\n✅ BRD coverage validation passed: {report['coverage_percentage']:.1f}%")
        sys.exit(0)
