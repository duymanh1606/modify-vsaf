"""vds-cli skills subcommand — delegates to vds-skills-sync package.

Implements TSK-SYNC-050 from .gpt-5.4/specs/vds-skills-sync/tasks.md.
The vds-skills-sync package lives in a sibling repo (.claude/vds-skills/),
so we delegate via subprocess rather than importing.

Phase 6 (TSK-SYNC-063 cli half) adds:
  - sync: --skills, --exclude-skills, --category, --diff, --diff-format
  - validate: full W2a surface (--skill, --all, --strict, --fix, --output, --json)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

skills_app = typer.Typer(
    help=(
        "Sync VDS skills to AI coding agents (Claude Code, Cursor, Copilot, generic). "
        "See .gpt-5.4/specs/vds-skills-sync/."
    )
)

_VALID_DIFF_FORMATS = frozenset({"summary", "unified", "json"})


def _find_vds_skills_sync() -> Path:
    """Locate the vds-skills-sync package directory.

    Resolution order:
      1. VDS_SKILLS_SYNC_DIR env var (must contain src/vds_skills_sync/__init__.py).
      2. Walk up from this file until we find .claude/vds-skills/vds-skills-sync.

    Raises:
        RuntimeError: When neither resolution strategy locates a valid package.
    """
    env_override = os.environ.get("VDS_SKILLS_SYNC_DIR")
    if env_override:
        path = Path(env_override)
        if (path / "src" / "vds_skills_sync" / "__init__.py").exists():
            return path
        raise RuntimeError(f"VDS_SKILLS_SYNC_DIR={env_override} does not contain src/vds_skills_sync/__init__.py")
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "claude" / "vds-skills" / "vds-skills-sync"
        if (candidate / "src" / "vds_skills_sync" / "__init__.py").exists():
            return candidate
    raise RuntimeError(
        "vds-skills-sync package not found. Set VDS_SKILLS_SYNC_DIR or run from a VDS monorepo checkout."
    )


def _run_vds_skills_sync(args: list[str]) -> int:
    """Delegate to `python -m vds_skills_sync` and return its exit code."""
    package_dir = _find_vds_skills_sync()
    src_dir = package_dir / "src"
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
    cmd = [sys.executable, "-m", "vds_skills_sync", *args]
    result = subprocess.run(cmd, env=env, cwd=str(package_dir), check=False)
    return result.returncode


@skills_app.command("sync")
def sync(
    agent: Annotated[
        str,
        typer.Option(
            "--agent",
            "-a",
            help="Target agent: claude|cursor|copilot|generic|all",
        ),
    ] = "claude",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without modifying files."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip validation checks before sync."),
    ] = False,
    scope: Annotated[
        str,
        typer.Option(
            "--scope",
            help="Installation scope: project|user (affects Cursor).",
        ),
    ] = "project",
    skills: Annotated[
        str,
        typer.Option(
            "--skills",
            help=("Comma-separated skill names to sync. Mutually exclusive with --exclude-skills."),
        ),
    ] = "",
    exclude_skills: Annotated[
        str,
        typer.Option(
            "--exclude-skills",
            help=("Comma-separated skill names to exclude from sync. Mutually exclusive with --skills."),
        ),
    ] = "",
    category: Annotated[
        str,
        typer.Option(
            "--category",
            help="Comma-separated categories to filter skills.",
        ),
    ] = "",
    diff: Annotated[
        bool,
        typer.Option(
            "--diff",
            help="Show structured diff (requires --dry-run).",
        ),
    ] = False,
    diff_format: Annotated[
        str,
        typer.Option(
            "--diff-format",
            help="Diff output format: summary|unified|json (default: summary).",
        ),
    ] = "summary",
) -> None:
    """Sync VDS skills to an AI agent."""
    if skills and exclude_skills:
        raise typer.BadParameter(
            "--skills and --exclude-skills are mutually exclusive.",
            param_hint="'--skills' / '--exclude-skills'",
        )
    if diff_format not in _VALID_DIFF_FORMATS:
        raise typer.BadParameter(
            f"Invalid diff format '{diff_format}'. Choose one of: {', '.join(sorted(_VALID_DIFF_FORMATS))}.",
            param_hint="'--diff-format'",
        )

    args: list[str] = ["--agent", agent, "--scope", scope]
    if dry_run:
        args.append("--dry-run")
    if force:
        args.append("--force")
    if skills:
        args += ["--skills", skills]
    if exclude_skills:
        args += ["--exclude-skills", exclude_skills]
    if category:
        args += ["--category", category]
    if diff:
        args.append("--diff")
    if diff_format != "summary":
        args += ["--diff-format", diff_format]
    elif diff:
        # Explicitly pass default so downstream always knows the format.
        args += ["--diff-format", diff_format]
    raise typer.Exit(_run_vds_skills_sync(args))


@skills_app.command("list")
def list_skills() -> None:
    """List all skills from the VDS registry."""
    raise typer.Exit(_run_vds_skills_sync(["--list"]))


@skills_app.command("validate")
def validate(
    validate_skill: Annotated[
        Path | None,
        typer.Option(
            "--skill",
            "--validate-skill",
            help="Validate a single SKILL.md file by path.",
        ),
    ] = None,
    validate_all: Annotated[
        bool,
        typer.Option(
            "--all",
            "--validate-all",
            help="Validate every registry-declared skill (default when no target given).",
        ),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Promote quality warnings to errors.",
        ),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help="Auto-correct trivial issues in-place.",
        ),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write audit report to PATH.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help=(
                "Output JSON instead of human-readable text. "
                "Note: JSON output may include header lines on stdout when "
                "invoked via this CLI wrapper. To extract clean JSON use: "
                "python -c 'import json,sys; [print(l) for l in sys.stdin "
                'if l.strip().startswith(("{","["))]\''
            ),
        ),
    ] = False,
) -> None:
    """Validate VDS skills against the AgentSkills specification.

    By default validates all registry skills. Use --skill PATH for a single
    skill file. Exits 0 on clean pass, 1 on validation errors, 2 on strict
    quality failures (when --strict is set).
    """
    if validate_skill and validate_all:
        raise typer.BadParameter(
            "Cannot combine --skill and --all.",
            param_hint="'--skill' / '--all'",
        )

    args: list[str] = []
    if validate_skill:
        args += ["--validate-skill", str(validate_skill)]
    else:
        # Default to --validate-all when neither specific target is given.
        args.append("--validate-all")

    if strict:
        args.append("--strict")
    if fix:
        args.append("--fix")
    if output:
        args += ["--output", str(output)]
    if json_output:
        args.append("--json")

    raise typer.Exit(_run_vds_skills_sync(args))


@skills_app.command("info")
def info(
    name: Annotated[
        str,
        typer.Argument(help="Skill name, e.g. audit-orchestrator-skill."),
    ],
) -> None:
    """Show a skill's rendered content."""
    raise typer.Exit(_run_vds_skills_sync(["--read", name]))


@skills_app.command("rollback")
def rollback() -> None:
    """Restore skills from the most recent backup."""
    raise typer.Exit(_run_vds_skills_sync(["--rollback"]))


@skills_app.command("version")
def version() -> None:
    """Show the vds-skills-sync package version."""
    raise typer.Exit(_run_vds_skills_sync(["--version"]))
