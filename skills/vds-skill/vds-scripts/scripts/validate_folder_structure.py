#!/usr/bin/env python3
"""
Folder Structure Consistency Validation Script
Validates that all services follow identical folder and file structure.
"""

import json
import sys
from pathlib import Path

# Expected project structure
EXPECTED_PROJECTS = ["INSURANCE", "LEP", "EKYC", "SAVING", "PLATFORM", "SECURITY"]

# Expected folder structure for each project
EXPECTED_FOLDERS = ["analysis", "business", "integrations", "operations", "overview", "security"]

# Expected files in each project root
EXPECTED_FILES = ["README.md"]


def analyze_project_structure(project_path: Path) -> dict:
    """Analyze the folder structure of a project."""

    if not project_path.exists():
        return {"error": f"Project path does not exist: {project_path}"}

    structure = {"folders": [], "files": [], "subfolders": {}}

    try:
        # Get immediate folders and files
        for item in project_path.iterdir():
            if item.is_dir():
                structure["folders"].append(item.name)
                # Analyze subfolders
                subfolders = []
                try:
                    for subitem in item.iterdir():
                        if subitem.is_dir():
                            subfolders.append(subitem.name)
                except PermissionError:
                    pass
                structure["subfolders"][item.name] = sorted(subfolders)
            elif item.is_file():
                structure["files"].append(item.name)

        structure["folders"] = sorted(structure["folders"])
        structure["files"] = sorted(structure["files"])

    except Exception as e:
        structure["error"] = str(e)

    return structure


def validate_folder_consistency() -> dict:
    """Validate folder structure consistency across all projects."""

    # Get the documentation root
    script_dir = Path(__file__).parent
    docs_root = script_dir.parent / "insurance-document"

    if not docs_root.exists():
        docs_root = script_dir.parent.parent / "insurance-document"

    if not docs_root.exists():
        return {"error": "Documentation root not found"}

    projects_root = docs_root / "projects"
    if not projects_root.exists():
        return {"error": "Projects directory not found"}

    print(f"🔍 Analyzing project structures at: {projects_root}")

    # Analyze each project
    project_structures = {}
    for project_name in EXPECTED_PROJECTS:
        project_path = projects_root / project_name
        if project_path.exists():
            structure = analyze_project_structure(project_path)
            project_structures[project_name] = structure
        else:
            project_structures[project_name] = {"error": "Project directory not found"}

    # Find common structure patterns
    all_folders = set()
    all_files = set()

    for _project, structure in project_structures.items():
        if "error" not in structure:
            all_folders.update(structure.get("folders", []))
            all_files.update(structure.get("files", []))

    # Check consistency
    consistency_report = {
        "total_projects": len(EXPECTED_PROJECTS),
        "analyzed_projects": len([p for p in project_structures.values() if "error" not in p]),
        "common_folders": sorted(all_folders),
        "common_files": sorted(all_files),
        "project_structures": project_structures,
        "consistency_issues": [],
        "missing_projects": [],
    }

    # Check for missing projects
    for project_name in EXPECTED_PROJECTS:
        if "error" in project_structures.get(project_name, {}):
            consistency_report["missing_projects"].append(project_name)

    # Check folder consistency
    reference_structure = None
    reference_project = None

    for project, structure in project_structures.items():
        if "error" not in structure:
            if reference_structure is None:
                reference_structure = structure
                reference_project = project
            else:
                # Compare with reference
                if set(structure["folders"]) != set(reference_structure["folders"]):
                    consistency_report["consistency_issues"].append(
                        {
                            "type": "folder_mismatch",
                            "project": project,
                            "reference": reference_project,
                            "missing_folders": list(set(reference_structure["folders"]) - set(structure["folders"])),
                            "extra_folders": list(set(structure["folders"]) - set(reference_structure["folders"])),
                        }
                    )

                if set(structure["files"]) != set(reference_structure["files"]):
                    consistency_report["consistency_issues"].append(
                        {
                            "type": "file_mismatch",
                            "project": project,
                            "reference": reference_project,
                            "missing_files": list(set(reference_structure["files"]) - set(structure["files"])),
                            "extra_files": list(set(structure["files"]) - set(reference_structure["files"])),
                        }
                    )

    # Calculate consistency score
    total_checks = len(EXPECTED_PROJECTS) * 2  # folders + files
    failed_checks = len(consistency_report["consistency_issues"]) + len(consistency_report["missing_projects"])
    consistency_score = max(0, (total_checks - failed_checks) / total_checks * 100)

    consistency_report["consistency_score"] = consistency_score

    return consistency_report


def print_consistency_report(report: dict):
    """Print a formatted consistency report."""

    if "error" in report:
        print(f"❌ {report['error']}")
        return

    print("\n" + "=" * 60)
    print("📁 FOLDER STRUCTURE CONSISTENCY REPORT")
    print("=" * 60)

    print("\n📊 Summary:")
    print(f"   Total Projects: {report['total_projects']}")
    print(f"   Analyzed Projects: {report['analyzed_projects']}")
    print(f"   Consistency Score: {report['consistency_score']:.1f}%")

    if report["consistency_score"] >= 95:
        print("   ✅ Excellent consistency!")
    elif report["consistency_score"] >= 80:
        print("   ⚠️  Good consistency with minor issues")
    else:
        print("   ❌ Poor consistency - significant issues found")

    if report["missing_projects"]:
        print(f"\n❌ Missing Projects ({len(report['missing_projects'])}):")
        for project in report["missing_projects"]:
            print(f"   • {project}")

    print("\n📂 Common Folder Structure:")
    for folder in report["common_folders"]:
        print(f"   • {folder}/")

    print("\n📄 Common Files:")
    for file in report["common_files"]:
        print(f"   • {file}")

    if report["consistency_issues"]:
        print(f"\n⚠️  Consistency Issues ({len(report['consistency_issues'])}):")
        for issue in report["consistency_issues"]:
            if issue["type"] == "folder_mismatch":
                print(f"   • {issue['project']}: Folder mismatch with {issue['reference']}")
                if issue["missing_folders"]:
                    print(f"     Missing: {', '.join(issue['missing_folders'])}")
                if issue["extra_folders"]:
                    print(f"     Extra: {', '.join(issue['extra_folders'])}")
            elif issue["type"] == "file_mismatch":
                print(f"   • {issue['project']}: File mismatch with {issue['reference']}")
                if issue["missing_files"]:
                    print(f"     Missing: {', '.join(issue['missing_files'])}")
                if issue["extra_files"]:
                    print(f"     Extra: {', '.join(issue['extra_files'])}")

    print("\n📋 Detailed Project Structures:")
    for project, structure in report["project_structures"].items():
        if "error" in structure:
            print(f"   • {project}: ❌ {structure['error']}")
        else:
            print(f"   • {project}: ✅ {len(structure['folders'])} folders, {len(structure['files'])} files")


if __name__ == "__main__":
    print("🚀 Starting Folder Structure Consistency Validation...")
    report = validate_folder_consistency()
    print_consistency_report(report)

    # Save report to file
    script_dir = Path(__file__).parent
    report_file = script_dir / "folder_structure_report.json"

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Report saved to: {report_file}")

    # Exit with appropriate code
    if "error" in report:
        sys.exit(1)
    elif report["consistency_score"] < 80:
        print(f"\n⚠️  Folder structure consistency below threshold: {report['consistency_score']:.1f}%")
        sys.exit(1)
    else:
        print(f"\n✅ Folder structure consistency validation passed: {report['consistency_score']:.1f}%")
        sys.exit(0)
