"""Ecosystem-wide documentation index generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EcosystemDocEntry:
    repo: str
    path: Path
    title: str
    quadrant: str
    line_count: int
    language: str  # "en" | "vi"


def discover_repos(base_path: Path) -> list[Path]:
    """Discover all repos with doc surfaces under base_path."""
    known = ["vds-scripts", "vds-skills", "vds-ai-memory"]
    repos = []
    for name in known:
        candidate = base_path / name
        if candidate.is_dir() and (candidate / "AGENTS.md").exists():
            repos.append(candidate)
    return repos


def scan_repo_docs(repo_path: Path) -> list[EcosystemDocEntry]:
    """Scan a single repo for all docs."""
    entries: list[EcosystemDocEntry] = []
    diataxis_html_re = re.compile(r"\u003c!--\s*di[áà]taxis:\s*([\w-]+)\s*--\u003e", re.IGNORECASE)
    diataxis_yaml_re = re.compile(r"^di[áà]taxis:\s*([\w-]+)\s*$", re.IGNORECASE)

    for lang in ["en", "vi"]:
        docs_dir = repo_path / "docs" / (lang if lang == "vi" else "agents")
        if lang == "en":
            docs_dir = repo_path / "docs" / "agents"
        if not docs_dir.exists():
            continue

        for md_path in sorted(docs_dir.rglob("*.md")):
            text = md_path.read_text(encoding="utf-8")
            lines = text.splitlines()
            lines[0] if lines else ""

            quadrant = "uncategorized"
            for line in lines[:10]:
                m = diataxis_html_re.search(line)
                if m:
                    quadrant = m.group(1).lower()
                    break
                m = diataxis_yaml_re.search(line)
                if m:
                    quadrant = m.group(1).lower()
                    break

            # Handle YAML-frontmatter titles (--- block before H1)
            title = md_path.stem.replace("-", " ").title()
            for idx, line in enumerate(lines):
                if line.strip() == "---" and idx > 0:
                    # End of YAML frontmatter; next non-empty should be H1
                    for next_line in lines[idx + 1 :]:
                        title_match = re.match(r"^#\s+(.+)$", next_line)
                        if title_match:
                            title = title_match.group(1)
                            break
                    break
                if idx == 0 and line.strip() != "---":
                    # No YAML frontmatter; title may be first line
                    title_match = re.match(r"^#\s+(.+)$", line)
                    if title_match:
                        title = title_match.group(1)
                    break

            entries.append(
                EcosystemDocEntry(
                    repo=repo_path.name,
                    path=md_path.relative_to(repo_path),
                    title=title,
                    quadrant=quadrant,
                    line_count=len(lines),
                    language=lang,
                )
            )

    return entries


def generate_ecosystem_index(base_path: Path, output: Path) -> dict[str, Any]:
    """Generate ECOSYSTEM-DOCS.md from discovered repos."""
    repos = discover_repos(base_path)
    all_entries: list[EcosystemDocEntry] = []
    for repo in repos:
        all_entries.extend(scan_repo_docs(repo))

    lines = [
        "# WHO Ecosystem Documentation Index",
        "",
        "> Auto-generated from repo doc surfaces. Do not edit manually.",
        f"> Generated: {__import__('datetime').datetime.now(__import__('datetime').UTC).isoformat()}",
        "",
        "## By Repository",
        "",
    ]

    for repo in repos:
        repo_entries = [e for e in all_entries if e.repo == repo.name]
        lines.append(f"### {repo.name} ({len(repo_entries)} docs)")
        lines.append("")
        lines.append("| Doc | Quadrant | Lines | Language |")
        lines.append("|-----|----------|-------|----------|")
        for e in sorted(repo_entries, key=lambda x: (x.language, x.quadrant, x.title)):
            rel = str(e.path)
            lines.append(f"| [{e.title}](./{e.repo}/{rel}) | {e.quadrant} | {e.line_count} | {e.language} |")
        lines.append("")

    lines.extend(
        [
            "## By Diátaxis Quadrant",
            "",
        ]
    )

    quadrants = ["tutorial", "how-to", "reference", "explanation"]
    for q in quadrants:
        q_entries = [e for e in all_entries if e.quadrant == q]
        lines.append(f"### {q.title()}")
        lines.append("")
        for e in sorted(q_entries, key=lambda x: (x.repo, x.title)):
            lines.append(f"- [{e.title}](./{e.repo}/{e.path}) ({e.repo}, {e.language})")
        lines.append("")

    lines.extend(
        [
            "## By Language",
            "",
            "### English",
            "",
        ]
    )
    for e in sorted([x for x in all_entries if x.language == "en"], key=lambda x: (x.repo, x.title)):
        lines.append(f"- [{e.title}](./{e.repo}/{e.path}) ({e.repo})")

    lines.extend(
        [
            "",
            "### Vietnamese (Tiếng Việt)",
            "",
        ]
    )
    for e in sorted([x for x in all_entries if x.language == "vi"], key=lambda x: (x.repo, x.title)):
        lines.append(f"- [{e.title}](./{e.repo}/{e.path}) ({e.repo})")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "repos": len(repos),
        "docs": len(all_entries),
        "output": str(output),
    }
