"""
Comprehensive BRD Coverage Verification

This script:
1. Extracts all BRD requirements in detail
2. Verifies each requirement is mapped to tasks
3. Identifies gaps in BRD coverage
4. Generates verification report
"""

import re
from pathlib import Path

from openpyxl import load_workbook

BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")
EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)


def extract_brd_requirements_detailed(brd_path: Path) -> dict:
    """Extract all BRD requirements with detailed subsections."""
    with open(brd_path, encoding="utf-8") as f:
        content = f.read()

    requirements = {
        "section3": {},  # Customer features
        "section4": {},  # Admin features
    }

    # Extract Section 3
    section3_start = content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO KHÁCH HÀNG**")
    section4_start = content.find("# **MÔ TẢ CHI TIẾT TÍNH NĂNG DÀNH CHO QUẢN TRỊ VIÊN**")

    if section3_start >= 0 and section4_start >= 0:
        section3_content = content[section3_start:section4_start]

        # Find all main sections (##)
        main_sections = list(re.finditer(r"^## (.*?)(?=\n|$)", section3_content, re.MULTILINE))

        for i, match in enumerate(main_sections):
            section_title = match.group(1).strip()
            section_title = re.sub(r"\*\*", "", section_title).strip()

            start = match.end()
            if i + 1 < len(main_sections):
                next_match = main_sections[i + 1]
                section_content = section3_content[start : next_match.start()]
            else:
                section_content = section3_content[start:]

            # Extract subsections (###)
            subsections = {}
            sub_matches = list(re.finditer(r"^### (.*?)(?=\n|$)", section_content, re.MULTILINE))

            for j, sub_match in enumerate(sub_matches):
                sub_title = sub_match.group(1).strip()
                sub_title = re.sub(r"\*\*", "", sub_title).strip()

                sub_start = sub_match.end()
                if j + 1 < len(sub_matches):
                    next_sub = sub_matches[j + 1]
                    sub_content = section_content[sub_start : next_sub.start()]
                else:
                    next_main = re.search(r"\n## ", section_content[sub_start:])
                    if next_main:
                        sub_content = section_content[sub_start : sub_start + next_main.start()]
                    else:
                        sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            requirements["section3"][section_title] = {
                "subsections": subsections,
                "content": section_content.strip(),
            }

    # Extract Section 4
    if section4_start >= 0:
        section4_content = content[section4_start:]

        main_sections = list(re.finditer(r"^## (.*?)(?=\n|$)", section4_content, re.MULTILINE))

        for i, match in enumerate(main_sections):
            section_title = match.group(1).strip()
            section_title = re.sub(r"\*\*", "", section_title).strip()

            start = match.end()
            if i + 1 < len(main_sections):
                next_match = main_sections[i + 1]
                section_content = section4_content[start : next_match.start()]
            else:
                section_content = section4_content[start:]

            subsections = {}
            sub_matches = list(re.finditer(r"^### (.*?)(?=\n|$)", section_content, re.MULTILINE))

            for j, sub_match in enumerate(sub_matches):
                sub_title = sub_match.group(1).strip()
                sub_title = re.sub(r"\*\*", "", sub_title).strip()

                sub_start = sub_match.end()
                if j + 1 < len(sub_matches):
                    next_sub = sub_matches[j + 1]
                    sub_content = section_content[sub_start : next_sub.start()]
                else:
                    next_main = re.search(r"\n## ", section_content[sub_start:])
                    if next_main:
                        sub_content = section_content[sub_start : sub_start + next_main.start()]
                    else:
                        sub_content = section_content[sub_start:]

                subsections[sub_title] = sub_content.strip()

            requirements["section4"][section_title] = {
                "subsections": subsections,
                "content": section_content.strip(),
            }

    return requirements


def get_tasks_from_sheet(excel_path: Path) -> dict:
    """Get all tasks from the detailed breakdown sheet."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    tasks_by_service = {}
    tasks_by_brd = {}

    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        service_name = ws.cell(row, 2).value
        responsibility = ws.cell(row, 3).value
        task_category = ws.cell(row, 4).value
        task_id = ws.cell(row, 5).value
        task_name = ws.cell(row, 6).value
        brd_ref = ws.cell(row, 7).value
        complexity = ws.cell(row, 8).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            if service_id_int not in tasks_by_service:
                tasks_by_service[service_id_int] = {
                    "name": service_name,
                    "responsibility": responsibility,
                    "tasks": [],
                }

            task_data = {
                "task_id": task_id,
                "task_name": task_name,
                "category": task_category,
                "brd_ref": brd_ref,
                "complexity": complexity,
            }

            tasks_by_service[service_id_int]["tasks"].append(task_data)

            # Index by BRD reference
            if brd_ref and str(brd_ref) != "N/A":
                if brd_ref not in tasks_by_brd:
                    tasks_by_brd[brd_ref] = []
                tasks_by_brd[brd_ref].append(
                    {
                        "service_id": service_id_int,
                        "service_name": service_name,
                        "task": task_name,
                    }
                )

    return {"by_service": tasks_by_service, "by_brd": tasks_by_brd}


def verify_brd_coverage(requirements: dict, tasks_data: dict) -> dict:
    """Verify BRD coverage and identify gaps."""
    verification = {
        "covered": [],
        "partially_covered": [],
        "not_covered": [],
        "coverage_stats": {},
    }

    # Check Section 3 coverage
    for section_title, section_data in requirements["section3"].items():
        coverage = {
            "section": section_title,
            "type": "customer",
            "subsections": len(section_data["subsections"]),
            "tasks_found": 0,
            "services_involved": set(),
        }

        # Check if any tasks reference this section
        section_keywords = section_title.split()

        for brd_ref, tasks in tasks_data["by_brd"].items():
            brd_ref_lower = str(brd_ref).lower()
            section_title.lower()

            # Check if BRD reference matches this section
            if any(keyword.lower() in brd_ref_lower for keyword in section_keywords if len(keyword) > 3):
                coverage["tasks_found"] += len(tasks)
                for task in tasks:
                    coverage["services_involved"].add(task["service_name"])

        # Check subsections
        for sub_title in section_data["subsections"]:
            sub_keywords = sub_title.split()
            for brd_ref, tasks in tasks_data["by_brd"].items():
                brd_ref_lower = str(brd_ref).lower()
                if any(keyword.lower() in brd_ref_lower for keyword in sub_keywords if len(keyword) > 3):
                    coverage["tasks_found"] += len(tasks)

        coverage["services_involved"] = list(coverage["services_involved"])

        if coverage["tasks_found"] > 0:
            if coverage["tasks_found"] >= coverage["subsections"]:
                verification["covered"].append(coverage)
            else:
                verification["partially_covered"].append(coverage)
        else:
            verification["not_covered"].append(coverage)

    # Check Section 4 coverage
    for section_title, section_data in requirements["section4"].items():
        coverage = {
            "section": section_title,
            "type": "admin",
            "subsections": len(section_data["subsections"]),
            "tasks_found": 0,
            "services_involved": set(),
        }

        section_keywords = section_title.split()

        for brd_ref, tasks in tasks_data["by_brd"].items():
            brd_ref_lower = str(brd_ref).lower()
            section_title.lower()

            if any(keyword.lower() in brd_ref_lower for keyword in section_keywords if len(keyword) > 3):
                coverage["tasks_found"] += len(tasks)
                for task in tasks:
                    coverage["services_involved"].add(task["service_name"])

        coverage["services_involved"] = list(coverage["services_involved"])

        if coverage["tasks_found"] > 0:
            if coverage["tasks_found"] >= coverage["subsections"]:
                verification["covered"].append(coverage)
            else:
                verification["partially_covered"].append(coverage)
        else:
            verification["not_covered"].append(coverage)

    # Calculate stats
    total_sections = len(requirements["section3"]) + len(requirements["section4"])
    verification["coverage_stats"] = {
        "total_sections": total_sections,
        "covered": len(verification["covered"]),
        "partially_covered": len(verification["partially_covered"]),
        "not_covered": len(verification["not_covered"]),
        "coverage_percentage": ((len(verification["covered"]) / total_sections * 100) if total_sections > 0 else 0),
    }

    return verification


def generate_verification_report(requirements: dict, tasks_data: dict, verification: dict):
    """Generate comprehensive verification report."""
    report_lines = []

    report_lines.append("# BRD Coverage Verification Report")
    report_lines.append("")
    report_lines.append("## Overview")
    report_lines.append("")
    report_lines.append("**Verification Date**: 2025-01-XX")
    report_lines.append("**BRD Version**: NTBH 2.0")
    report_lines.append("")

    # Coverage statistics
    stats = verification["coverage_stats"]
    report_lines.append("## Coverage Statistics")
    report_lines.append("")
    report_lines.append(f"- **Total BRD Sections**: {stats['total_sections']}")
    report_lines.append(f"- **Fully Covered**: {stats['covered']} ({stats['coverage_percentage']:.1f}%)")
    report_lines.append(f"- **Partially Covered**: {stats['partially_covered']}")
    report_lines.append(f"- **Not Covered**: {stats['not_covered']}")
    report_lines.append("")

    # Covered sections
    report_lines.append("## Fully Covered Sections")
    report_lines.append("")
    for coverage in verification["covered"]:
        report_lines.append(f"### {coverage['section']} ({coverage['type']})")
        report_lines.append("")
        report_lines.append(f"- **Subsections**: {coverage['subsections']}")
        report_lines.append(f"- **Tasks Found**: {coverage['tasks_found']}")
        report_lines.append(f"- **Services Involved**: {', '.join(coverage['services_involved'][:5])}")
        if len(coverage["services_involved"]) > 5:
            report_lines.append(f"  - ... and {len(coverage['services_involved']) - 5} more")
        report_lines.append("")

    # Partially covered
    if verification["partially_covered"]:
        report_lines.append("## Partially Covered Sections")
        report_lines.append("")
        for coverage in verification["partially_covered"]:
            report_lines.append(f"### {coverage['section']} ({coverage['type']})")
            report_lines.append("")
            report_lines.append(f"- **Subsections**: {coverage['subsections']}")
            report_lines.append(f"- **Tasks Found**: {coverage['tasks_found']}")
            report_lines.append(f"- **Coverage**: {coverage['tasks_found']}/{coverage['subsections']} subsections")
            report_lines.append(f"- **Services Involved**: {', '.join(coverage['services_involved'][:3])}")
            report_lines.append("")

    # Not covered
    if verification["not_covered"]:
        report_lines.append("## Sections Not Covered")
        report_lines.append("")
        report_lines.append("⚠️ **Action Required**: These sections need task mapping")
        report_lines.append("")
        for coverage in verification["not_covered"]:
            report_lines.append(f"- **{coverage['section']}** ({coverage['type']})")
            report_lines.append(f"  - Subsections: {coverage['subsections']}")
            report_lines.append("")

    # Task distribution by responsibility
    report_lines.append("## Task Distribution by Responsibility")
    report_lines.append("")

    responsibility_stats = {}
    for _service_id, service_data in tasks_data["by_service"].items():
        resp = service_data["responsibility"]
        if resp not in responsibility_stats:
            responsibility_stats[resp] = {
                "services": 0,
                "tasks": 0,
                "services_list": [],
            }
        responsibility_stats[resp]["services"] += 1
        responsibility_stats[resp]["tasks"] += len(service_data["tasks"])
        responsibility_stats[resp]["services_list"].append(service_data["name"])

    for resp, stats in sorted(responsibility_stats.items()):
        report_lines.append(f"### {resp}")
        report_lines.append("")
        report_lines.append(f"- **Services**: {stats['services']}")
        report_lines.append(f"- **Tasks**: {stats['tasks']}")
        report_lines.append("")

    # Write report
    report_path = Path(
        "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/BRD_COVERAGE_VERIFICATION.md"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print("Generated verification report: BRD_COVERAGE_VERIFICATION.md")


def main():
    """Main execution."""
    print("=" * 80)
    print("Comprehensive BRD Coverage Verification")
    print("=" * 80)

    # Step 1: Extract BRD requirements
    print("\nStep 1: Extracting BRD requirements...")
    requirements = extract_brd_requirements_detailed(BRD_PATH)
    print(f"  Section 3: {len(requirements['section3'])} sections")
    print(f"  Section 4: {len(requirements['section4'])} sections")

    # Step 2: Get tasks from sheet
    print("\nStep 2: Reading tasks from sheet...")
    tasks_data = get_tasks_from_sheet(EXCEL_PATH)
    print(f"  Services with tasks: {len(tasks_data['by_service'])}")
    print(f"  BRD references: {len(tasks_data['by_brd'])}")

    # Step 3: Verify coverage
    print("\nStep 3: Verifying BRD coverage...")
    verification = verify_brd_coverage(requirements, tasks_data)

    stats = verification["coverage_stats"]
    print(f"  Fully Covered: {stats['covered']}/{stats['total_sections']} ({stats['coverage_percentage']:.1f}%)")
    print(f"  Partially Covered: {stats['partially_covered']}")
    print(f"  Not Covered: {stats['not_covered']}")

    # Step 4: Generate report
    print("\nStep 4: Generating verification report...")
    generate_verification_report(requirements, tasks_data, verification)

    print("\n" + "=" * 80)
    print("Verification completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
