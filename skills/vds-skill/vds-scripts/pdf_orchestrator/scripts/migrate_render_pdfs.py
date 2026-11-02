#!/usr/bin/env python3
"""
Migration script to transition from render_pdfs.py to VDS PDF Orchestrator.

This script helps migrate existing workflows that use the old render_pdfs.py
to the new consolidated VDS PDF Orchestrator with enhanced security and styling.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vds_pdf_orchestrator.vds_styling import create_vds_styling_converter

from vds_pdf_orchestrator.config import load_settings


def find_render_pdfs_usage(root_dir: Path) -> list[dict]:
    """Find files that reference render_pdfs.py."""
    usage_patterns = []

    # Search for files that reference render_pdfs.py
    for file_path in root_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in [
            ".py",
            ".sh",
            ".md",
            ".yml",
            ".yaml",
        ]:
            try:
                content = file_path.read_text(encoding="utf-8")
                if "render_pdfs.py" in content:
                    usage_patterns.append(
                        {
                            "file": str(file_path),
                            "type": file_path.suffix,
                            "lines": [
                                f"Line {i + 1}: {line.strip()}"
                                for i, line in enumerate(content.split("\n"))
                                if "render_pdfs.py" in line
                            ],
                        }
                    )
            except (UnicodeDecodeError, PermissionError):
                continue

    return usage_patterns


def generate_migration_commands(usage_patterns: list[dict]) -> list[dict]:
    """Generate migration commands for each usage pattern."""
    migrations = []

    for usage in usage_patterns:
        file_path = Path(usage["file"])

        if usage["type"] == ".py":
            # Python file migration
            migrations.append(
                {
                    "file": str(file_path),
                    "type": "python",
                    "description": "Update Python script to use VDS PDF Orchestrator",
                    "old_command": "python render_pdfs.py <folder>",
                    "new_command": "uv run vds-pdf batch-md2pdf <folder>",
                    "migration_steps": [
                        "Install VDS PDF Orchestrator: pip install vds-pdf-orchestrator",
                        "Replace render_pdfs.py calls with vds-pdf batch-md2pdf",
                        "Update any output path handling",
                    ],
                }
            )

        elif usage["type"] == ".sh":
            # Shell script migration
            migrations.append(
                {
                    "file": str(file_path),
                    "type": "shell",
                    "description": "Update shell script to use VDS PDF Orchestrator",
                    "old_command": "./pdf-env/bin/python render_pdfs.py <folder>",
                    "new_command": "vds-pdf batch-md2pdf <folder>",
                    "migration_steps": [
                        "Remove pdf-env dependency",
                        "Replace render_pdfs.py calls with vds-pdf commands",
                        "Update error handling for new CLI output format",
                    ],
                }
            )

        elif usage["type"] in [".yml", ".yaml"]:
            # YAML/CI configuration migration
            migrations.append(
                {
                    "file": str(file_path),
                    "type": "ci",
                    "description": "Update CI/CD pipeline to use VDS PDF Orchestrator",
                    "old_command": "./pdf-env/bin/python render_pdfs.py",
                    "new_command": "vds-pdf batch-md2pdf",
                    "migration_steps": [
                        "Update CI environment to install vds-pdf-orchestrator",
                        "Replace render_pdfs.py commands in pipeline",
                        "Remove pdf-env caching and setup steps",
                    ],
                }
            )

    return migrations


def create_migration_backup(files_to_migrate: list[Path]) -> Path:
    """Create backup of files that will be migrated."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"migration_backup_{timestamp}")
    backup_dir.mkdir(exist_ok=True)

    for file_path in files_to_migrate:
        if file_path.exists():
            relative_path = file_path.relative_to(Path.cwd())
            backup_path = backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(file_path.read_text(encoding="utf-8"))

    return backup_dir


def test_vds_orchestrator_setup() -> dict:
    """Test if VDS PDF Orchestrator is properly set up."""
    try:
        settings = load_settings()
        converter = create_vds_styling_converter(settings)

        # Test basic functionality with a minimal markdown file
        test_md = Path("test_migration.md")
        test_md.write_text("# Test\n\nThis is a test markdown file.", encoding="utf-8")

        test_pdf = Path("test_migration.pdf")
        result = converter.convert_markdown_to_vds_pdf(test_md, test_pdf, True)

        # Cleanup
        if test_md.exists():
            test_md.unlink()
        if test_pdf.exists():
            test_pdf.unlink()

        return {
            "success": result["success"],
            "styling_available": result["styling_used"] == "vds_corporate",
            "message": "VDS PDF Orchestrator is working correctly"
            if result["success"]
            else f"Setup issue: {result.get('error', 'Unknown error')}",
        }

    except Exception as e:
        return {
            "success": False,
            "styling_available": False,
            "message": f"Setup failed: {str(e)}",
        }


def main() -> int:
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate from render_pdfs.py to VDS PDF Orchestrator"
    )
    parser.add_argument(
        "root_dir",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Root directory to search for render_pdfs.py usage (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show migration plan without making changes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("migration_plan.json"),
        help="Output file for migration plan (default: migration_plan.json)",
    )
    parser.add_argument(
        "--test-setup",
        action="store_true",
        help="Test VDS PDF Orchestrator setup before migration",
    )

    args = parser.parse_args()

    print("🔍 VDS PDF Orchestrator Migration Tool")
    print("=" * 50)

    # Test setup if requested
    if args.test_setup:
        print("\n🧪 Testing VDS PDF Orchestrator setup...")
        test_result = test_vds_orchestrator_setup()
        if test_result["success"]:
            print(f"✅ {test_result['message']}")
            if test_result["styling_available"]:
                print("✅ VDS corporate styling is available")
            else:
                print("⚠️  VDS corporate styling not available, using fallback styling")
        else:
            print(f"❌ {test_result['message']}")
            return 1

    # Find usage patterns
    print(f"\n🔍 Searching for render_pdfs.py usage in: {args.root_dir}")
    usage_patterns = find_render_pdfs_usage(args.root_dir)

    if not usage_patterns:
        print("✅ No render_pdfs.py usage found. No migration needed.")
        return 0

    print(f"📊 Found {len(usage_patterns)} file(s) using render_pdfs.py:")
    for i, usage in enumerate(usage_patterns, 1):
        print(f"   {i}. {usage['file']} ({usage['type']})")
        for line in usage["lines"][:3]:  # Show first 3 lines
            print(f"      {line}")
        if len(usage["lines"]) > 3:
            print(f"      ... and {len(usage['lines']) - 3} more reference(s)")

    # Generate migration plan
    print("\n📋 Generating migration plan...")
    migrations = generate_migration_commands(usage_patterns)

    migration_plan = {
        "timestamp": str(args.root_dir),
        "total_files": len(usage_patterns),
        "migrations": migrations,
        "summary": {
            "python_files": len([m for m in migrations if m["type"] == "python"]),
            "shell_files": len([m for m in migrations if m["type"] == "shell"]),
            "ci_files": len([m for m in migrations if m["type"] == "ci"]),
        },
    }

    # Save migration plan
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(migration_plan, indent=2), encoding="utf-8")
    print(f"💾 Migration plan saved to: {args.output}")

    # Show migration summary
    print("\n📊 Migration Summary:")
    print(f"   Total files to migrate: {migration_plan['total_files']}")
    print(f"   Python scripts: {migration_plan['summary']['python_files']}")
    print(f"   Shell scripts: {migration_plan['summary']['shell_files']}")
    print(f"   CI/CD files: {migration_plan['summary']['ci_files']}")

    # Show sample migration
    if migrations:
        print("\n🔄 Sample Migration:")
        sample = migrations[0]
        print(f"   File: {sample['file']}")
        print(f"   Type: {sample['type']}")
        print(f"   Old command: {sample['old_command']}")
        print(f"   New command: {sample['new_command']}")
        print("   Steps:")
        for step in sample["migration_steps"]:
            print(f"      • {step}")

    if not args.dry_run:
        print("\n⚠️  Dry run mode. No changes made.")
        print("   Run with --dry-run=False to apply migrations.")
    else:
        print("\n🚀 Ready to apply migrations!")
        print("   Review the migration plan and run again to apply changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
