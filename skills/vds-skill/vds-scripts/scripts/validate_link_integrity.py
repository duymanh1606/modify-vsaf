#!/usr/bin/env python3
"""
Link Integrity Validation Script (Internal Links Only)
Validates that all internal links in documentation resolve correctly.
"""

import json
import re
import sys
from pathlib import Path

# Link patterns to match
MARKDOWN_LINK_PATTERN = r"\[([^\]]*)\]\(([^)]+)\)"
REFERENCE_LINK_PATTERN = r"\[([^\]]*)\]:\s*([^\s]+)"


def extract_links_from_file(file_path: Path) -> list[tuple[str, str, int]]:
    """Extract all links from a markdown file."""
    links = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find markdown links [text](url)
            for match in re.finditer(MARKDOWN_LINK_PATTERN, line):
                text, url = match.groups()
                links.append((text, url, line_num))

            # Find reference links [text]: url
            for match in re.finditer(REFERENCE_LINK_PATTERN, line):
                text, url = match.groups()
                links.append((text, url, line_num))

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return links


def categorize_link(url: str, _base_path: Path) -> str:
    """Categorize a link as internal, external, or anchor."""

    # Remove fragments (anchors)
    clean_url = url.split("#", maxsplit=1)[0]

    if not clean_url:
        return "anchor"
    elif clean_url.startswith(("http://", "https://")):
        return "external"
    elif clean_url.startswith("mailto:"):
        return "email"
    else:
        return "internal"


def validate_internal_link(url: str, source_file: Path, docs_root: Path) -> dict:
    """Validate an internal link."""

    # Remove anchor fragment
    clean_url = url.split("#", maxsplit=1)[0]

    if not clean_url:
        return {"valid": True, "type": "anchor", "message": "Anchor link"}

    # Resolve relative path
    if clean_url.startswith("/"):
        # Absolute path from docs root
        target_path = docs_root / clean_url.lstrip("/")
    else:
        # Relative path from source file
        target_path = source_file.parent / clean_url

    # Normalize path
    try:
        target_path = target_path.resolve()
    except Exception as e:
        return {"valid": False, "type": "internal", "message": f"Path resolution error: {e}"}

    # Check if target exists
    if target_path.exists():
        return {"valid": True, "type": "internal", "message": "File exists"}
    else:
        return {"valid": False, "type": "internal", "message": f"File not found: {target_path}"}


def validate_links_in_file(file_path: Path, docs_root: Path) -> dict:
    """Validate all links in a single file."""

    links = extract_links_from_file(file_path)

    results = {
        "file": str(file_path.relative_to(docs_root)),
        "total_links": len(links),
        "internal_links": 0,
        "external_links": 0,
        "valid_internal": 0,
        "broken_internal": 0,
        "link_results": [],
    }

    for text, url, line_num in links:
        link_type = categorize_link(url, file_path)

        if link_type in {"internal", "anchor"}:
            results["internal_links"] += 1
            validation = validate_internal_link(url, file_path, docs_root)

            if validation["valid"]:
                results["valid_internal"] += 1
            else:
                results["broken_internal"] += 1

        elif link_type == "external":
            results["external_links"] += 1
            validation = {"valid": True, "type": "external", "message": "External link (not validated)"}
        elif link_type == "email":
            validation = {"valid": True, "type": "email", "message": "Email link"}
        else:
            validation = {"valid": False, "type": "unknown", "message": "Unknown link type"}

        link_result = {
            "text": text,
            "url": url,
            "line": line_num,
            "type": link_type,
            "valid": validation["valid"],
            "message": validation["message"],
        }

        results["link_results"].append(link_result)

    return results


def validate_link_integrity(max_files: int = 50) -> dict:
    """Validate link integrity across documentation."""

    # Get the documentation root
    script_dir = Path(__file__).parent
    docs_root = script_dir.parent / "insurance-document"

    if not docs_root.exists():
        docs_root = script_dir.parent.parent / "insurance-document"

    if not docs_root.exists():
        return {"error": "Documentation root not found"}

    print(f"🔍 Scanning links in documentation at: {docs_root}")

    # Find markdown files (limit to avoid overwhelming)
    md_files = list(docs_root.rglob("*.md"))[:max_files]

    print(f"📄 Found {len(md_files)} markdown files (limited to {max_files})")

    # Validate links in each file
    all_results = []
    total_links = 0
    total_internal = 0
    total_external = 0
    valid_internal = 0
    broken_internal = 0

    for i, md_file in enumerate(md_files, 1):
        print(f"   Processing {i}/{len(md_files)}: {md_file.name}")

        file_results = validate_links_in_file(md_file, docs_root)
        all_results.append(file_results)

        total_links += file_results["total_links"]
        total_internal += file_results["internal_links"]
        total_external += file_results["external_links"]
        valid_internal += file_results["valid_internal"]
        broken_internal += file_results["broken_internal"]

    # Calculate success rate for internal links only
    internal_success_rate = (valid_internal / total_internal * 100) if total_internal > 0 else 100

    # Generate summary report
    report = {
        "total_files": len(md_files),
        "total_links": total_links,
        "internal_links": total_internal,
        "external_links": total_external,
        "valid_internal": valid_internal,
        "broken_internal": broken_internal,
        "internal_success_rate": internal_success_rate,
        "file_results": all_results,
        "broken_internal_summary": [],
    }

    # Collect broken internal links summary
    for file_result in all_results:
        for link in file_result["link_results"]:
            if link["type"] in ["internal", "anchor"] and not link["valid"]:
                report["broken_internal_summary"].append(
                    {"file": file_result["file"], "line": link["line"], "url": link["url"], "message": link["message"]}
                )

    return report


def print_link_integrity_report(report: dict):
    """Print a formatted link integrity report."""

    if "error" in report:
        print(f"❌ {report['error']}")
        return

    print("\n" + "=" * 60)
    print("🔗 LINK INTEGRITY VALIDATION REPORT (Internal Links)")
    print("=" * 60)

    print("\n📊 Summary:")
    print(f"   Files Analyzed: {report['total_files']}")
    print(f"   Total Links: {report['total_links']}")
    print(f"   Internal Links: {report['internal_links']}")
    print(f"   External Links: {report['external_links']} (not validated)")
    print(f"   Valid Internal Links: {report['valid_internal']}")
    print(f"   Broken Internal Links: {report['broken_internal']}")
    print(f"   Internal Success Rate: {report['internal_success_rate']:.1f}%")

    if report["internal_success_rate"] >= 95:
        print("   ✅ Excellent internal link integrity!")
    elif report["internal_success_rate"] >= 80:
        print("   ⚠️  Good internal link integrity with some issues")
    else:
        print("   ❌ Poor internal link integrity - many broken links")

    if report["broken_internal"] > 0:
        print(f"\n❌ Broken Internal Links ({len(report['broken_internal_summary'])}):")
        for i, broken in enumerate(report["broken_internal_summary"][:10], 1):  # Show first 10
            print(f"   {i}. {broken['file']}:{broken['line']}")
            print(f"      URL: {broken['url']}")
            print(f"      Issue: {broken['message']}")

        if len(report["broken_internal_summary"]) > 10:
            print(f"   ... and {len(report['broken_internal_summary']) - 10} more broken links")

    print("\n📁 Files with Most Links:")
    sorted_files = sorted(report["file_results"], key=lambda x: x["total_links"], reverse=True)
    for file_result in sorted_files[:5]:
        status = "✅" if file_result["broken_internal"] == 0 else f"⚠️ {file_result['broken_internal']} broken"
        print(f"   • {file_result['file']}: {file_result['total_links']} links ({status})")


if __name__ == "__main__":
    print("🚀 Starting Link Integrity Validation (Internal Links Only)...")

    # Run validation with limited scope for performance
    report = validate_link_integrity(max_files=20)  # Limit to 20 files for demo
    print_link_integrity_report(report)

    # Save report to file
    script_dir = Path(__file__).parent
    report_file = script_dir / "link_integrity_report.json"

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Report saved to: {report_file}")

    # Exit with appropriate code
    if "error" in report:
        sys.exit(1)
    elif report["internal_success_rate"] < 80:
        print(f"\n⚠️  Internal link integrity below threshold: {report['internal_success_rate']:.1f}%")
        sys.exit(1)
    else:
        print(f"\n✅ Internal link integrity validation passed: {report['internal_success_rate']:.1f}%")
        sys.exit(0)
