"""Validation and freshness checks for documentation surfaces."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_SKILL_MD_GLOB = "skills/*/SKILL.md"
_KNOWN_REPOS = ("vds-scripts", "vds-skills", "vds-ai-memory")


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


@dataclass(frozen=True)
class FreshnessPair:
    doc: str
    source: str
    max_lag_days: int


def discover_repo_roots(base_path: Path, repo: str | None) -> list[Path]:
    base = base_path.resolve()
    if repo:
        if base.name == repo:
            return [base]
        candidate = base / repo
        if candidate.exists() and candidate.is_dir():
            return [candidate.resolve()]
        raise ValueError(f"Repo '{repo}' was not found under {base}")

    discovered = [((base / name).resolve()) for name in _KNOWN_REPOS if (base / name).is_dir()]
    if discovered:
        return discovered
    return [base]


def validate_docs(
    base_path: Path,
    repo: str | None = None,
    fix: bool = False,
    check_vi: bool = False,
    check_diataxis: bool = False,
    cross_repo: bool = False,
    check_orchestrators: bool = False,
    check_skills: bool = False,
    check_ecosystem: bool = False,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for repo_root in discover_repo_roots(base_path, repo):
        repo_name = repo_root.name
        issues.extend(_validate_repo(repo_root, fix=fix))
        if check_vi:
            issues.extend(_check_vi_docs(repo_name, repo_root))
        if check_diataxis:
            issues.extend(_check_diataxis_headers(repo_name, repo_root))
        if cross_repo:
            issues.extend(_check_cross_repo_links(repo_name, repo_root, base_path))
        if check_orchestrators:
            issues.extend(_check_orchestrator_docs(repo_name, repo_root))
        if check_skills:
            issues.extend(_check_skill_docs(repo_name, repo_root))
        if check_ecosystem:
            issues.extend(_check_ecosystem_files(repo_name, repo_root))
    return issues


def _validate_repo(repo_root: Path, *, fix: bool) -> list[ValidationIssue]:
    repo_name = repo_root.name
    issues: list[ValidationIssue] = []
    agents_path = repo_root / "AGENTS.md"
    llms_path = repo_root / "llms.txt"
    claude_path = repo_root / "CLAUDE.md"

    if agents_path.exists():
        lines = _line_count(agents_path)
        if lines > 250:
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="agents_line_cap",
                    message=f"AGENTS.md exceeds 250 lines ({lines}).",
                    path=agents_path,
                )
            )

    else:
        issues.append(
            ValidationIssue(
                repo=repo_name,
                check="agents_exists",
                message="AGENTS.md is missing.",
                path=agents_path,
            )
        )

    if not llms_path.exists():
        if fix:
            llms_path.write_text(f"# {repo_name}\n\n> Repository index.\n", encoding="utf-8")
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="llms_exists",
                    message="Created missing llms.txt.",
                    path=llms_path,
                    fixed=True,
                )
            )
        else:
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="llms_exists",
                    message="llms.txt is missing.",
                    path=llms_path,
                )
            )
    else:
        issues.extend(_check_llms_links(repo_name, llms_path))

    issues.extend(_check_claude_symlink(repo_name, claude_path, fix=fix))
    issues.extend(_check_orphan_docs(repo_name, repo_root, llms_path, fix=fix))
    issues.extend(_check_skill_caps(repo_name, repo_root))
    issues.extend(_check_phase_changelog(repo_name, repo_root))
    return issues


def _check_claude_symlink(repo_name: str, claude_path: Path, *, fix: bool) -> list[ValidationIssue]:
    if claude_path.is_symlink() and claude_path.readlink() == Path("AGENTS.md"):
        return []
    if not claude_path.exists():
        if fix:
            claude_path.symlink_to("AGENTS.md")
            return [
                ValidationIssue(
                    repo=repo_name,
                    check="claude_symlink",
                    message="Created CLAUDE.md symlink -> AGENTS.md.",
                    path=claude_path,
                    fixed=True,
                )
            ]
        return [
            ValidationIssue(
                repo=repo_name,
                check="claude_symlink",
                message="CLAUDE.md is missing (expected symlink to AGENTS.md).",
                path=claude_path,
            )
        ]
    if fix:
        claude_path.unlink()
        claude_path.symlink_to("AGENTS.md")
        return [
            ValidationIssue(
                repo=repo_name,
                check="claude_symlink",
                message="Replaced CLAUDE.md with symlink -> AGENTS.md.",
                path=claude_path,
                fixed=True,
            )
        ]
    return [
        ValidationIssue(
            repo=repo_name,
            check="claude_symlink",
            message="CLAUDE.md is not a symlink to AGENTS.md.",
            path=claude_path,
        )
    ]


def _check_llms_links(repo_name: str, llms_path: Path) -> list[ValidationIssue]:
    text = llms_path.read_text(encoding="utf-8")
    issues: list[ValidationIssue] = []
    for target in _MARKDOWN_LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        resolved = (llms_path.parent / target).resolve()
        if not resolved.exists():
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="llms_links",
                    message=f"Broken llms.txt link: {target}",
                    path=llms_path,
                )
            )
    return issues


def _check_orphan_docs(
    repo_name: str,
    repo_root: Path,
    llms_path: Path,
    *,
    fix: bool,
) -> list[ValidationIssue]:
    docs_root = repo_root / "docs" / "agents"
    if not docs_root.exists():
        return []

    index_text = ""
    for path in (repo_root / "AGENTS.md", llms_path):
        if path.exists():
            index_text += "\n" + path.read_text(encoding="utf-8")

    md_files = sorted(p for p in docs_root.rglob("*.md") if p.is_file())
    orphans = [p for p in md_files if p.relative_to(repo_root).as_posix() not in index_text]
    if not orphans:
        return []

    issues: list[ValidationIssue] = []
    if fix:
        if not llms_path.exists():
            llms_path.write_text(f"# {repo_name}\n\n> Repository index.\n", encoding="utf-8")
        existing = llms_path.read_text(encoding="utf-8")
        if "## Docs Index" not in existing:
            existing += "\n\n## Docs Index\n"
        for orphan in orphans:
            rel = orphan.relative_to(repo_root).as_posix()
            existing += f"\n- [{orphan.stem}](./{rel})"
        llms_path.write_text(existing + "\n", encoding="utf-8")
        issues.append(
            ValidationIssue(
                repo=repo_name,
                check="orphan_docs",
                message=f"Added {len(orphans)} missing docs links to llms.txt.",
                path=llms_path,
                fixed=True,
            )
        )
        return issues

    for orphan in orphans:
        issues.append(
            ValidationIssue(
                repo=repo_name,
                check="orphan_docs",
                message=f"Orphan docs file: {orphan.relative_to(repo_root).as_posix()}",
                path=orphan,
            )
        )
    return issues


def _check_skill_caps(repo_name: str, repo_root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for skill_file in sorted(repo_root.glob(_SKILL_MD_GLOB)):
        lines = _line_count(skill_file)
        if lines > 200:
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="skill_line_cap",
                    message=f"{skill_file.relative_to(repo_root)} exceeds 200 lines ({lines}).",
                    path=skill_file,
                )
            )
    return issues


def _check_phase_changelog(repo_name: str, repo_root: Path) -> list[ValidationIssue]:
    if repo_name != "vds-scripts":
        return []
    issues: list[ValidationIssue] = []
    changelog = repo_root / "docs" / "phases" / "CHANGELOG.md"
    if not changelog.exists():
        issues.append(
            ValidationIssue(
                repo=repo_name,
                check="phase_changelog",
                message="docs/phases/CHANGELOG.md is missing.",
                path=changelog,
            )
        )
    agents_path = repo_root / "AGENTS.md"
    if agents_path.exists():
        agents_text = agents_path.read_text(encoding="utf-8")
        if "docs/phases/CHANGELOG.md" not in agents_text:
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="phase_changelog",
                    message="AGENTS.md does not reference docs/phases/CHANGELOG.md.",
                    path=agents_path,
                )
            )
    return issues


def load_freshness_pairs(config_path: Path) -> list[FreshnessPair]:
    if not config_path.exists():
        raise ValueError(f"Freshness config not found: {config_path}")
    lines = config_path.read_text(encoding="utf-8").splitlines()
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or line == "pairs:":
            continue
        if line.startswith("- "):
            if current:
                entries.append(current)
            current = {}
            payload = line[2:]
            if ":" in payload:
                key, value = payload.split(":", 1)
                current[key.strip()] = value.strip().strip("'\"")
            continue
        if current is None:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = value.strip().strip("'\"")
    if current:
        entries.append(current)

    pairs: list[FreshnessPair] = []
    for item in entries:
        doc = item.get("doc")
        source = item.get("source")
        if not doc or not source:
            raise ValueError("Each freshness pair must include doc and source")
        max_lag_days = int(item.get("max_lag_days", "7"))
        pairs.append(FreshnessPair(doc=doc, source=source, max_lag_days=max_lag_days))
    return pairs


def check_freshness(repo_root: Path, config_path: Path) -> list[FreshnessIssue]:
    repo = repo_root.resolve()
    issues: list[FreshnessIssue] = []
    for pair in load_freshness_pairs(config_path):
        doc_path = repo / pair.doc
        source_path = repo / pair.source
        if not doc_path.exists():
            issues.append(
                FreshnessIssue(
                    doc=pair.doc,
                    source=pair.source,
                    max_lag_days=pair.max_lag_days,
                    lag_days=0.0,
                    message=f"Missing doc file: {pair.doc}",
                )
            )
            continue
        if not source_path.exists():
            issues.append(
                FreshnessIssue(
                    doc=pair.doc,
                    source=pair.source,
                    max_lag_days=pair.max_lag_days,
                    lag_days=0.0,
                    message=f"Missing source file: {pair.source}",
                )
            )
            continue
        doc_ts = _git_or_mtime(repo, doc_path)
        source_ts = _git_or_mtime(repo, source_path)
        lag_days = max((source_ts - doc_ts) / 86400.0, 0.0)
        if lag_days > pair.max_lag_days:
            issues.append(
                FreshnessIssue(
                    doc=pair.doc,
                    source=pair.source,
                    max_lag_days=pair.max_lag_days,
                    lag_days=lag_days,
                    message=f"Freshness lag {lag_days:.1f}d > {pair.max_lag_days}d",
                )
            )
    return issues


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _git_or_mtime(repo_root: Path, file_path: Path) -> int:
    rel = str(file_path.relative_to(repo_root))
    cmd = ["git", "-C", str(repo_root), "log", "--follow", "-1", "--format=%ct", "--", rel]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = proc.stdout.strip()
    if proc.returncode == 0 and output.isdigit():
        return int(output)
    return int(file_path.stat().st_mtime)


# ---------------------------------------------------------------------------
# DOC-V2-023: Vietnamese doc validation
# ---------------------------------------------------------------------------


def _check_vi_docs(repo_name: str, repo_root: Path) -> list[ValidationIssue]:
    """Check Vietnamese docs exist and mirror English structure."""
    issues: list[ValidationIssue] = []

    # Check AGENTS.vi.md exists when AGENTS.md exists
    agents_path = repo_root / "AGENTS.md"
    agents_vi_path = repo_root / "AGENTS.vi.md"
    if agents_path.exists() and not agents_vi_path.exists():
        issues.append(
            ValidationIssue(
                repo=repo_name,
                check="vi_translation_missing",
                message="Missing Vietnamese translation: AGENTS.vi.md (EN: AGENTS.md).",
                path=agents_vi_path,
            )
        )

    # Check docs/vi/ exists when docs/agents/ exists
    docs_en = repo_root / "docs" / "agents"
    docs_vi = repo_root / "docs" / "vi" / "agents"
    if docs_en.exists() and not docs_vi.exists():
        issues.append(
            ValidationIssue(
                repo=repo_name,
                check="vi_docs_missing",
                message="Missing Vietnamese docs directory: docs/vi/agents/.",
                path=docs_vi,
            )
        )

    # Check llms.txt contains vi/ links
    llms_path = repo_root / "llms.txt"
    if llms_path.exists():
        text = llms_path.read_text(encoding="utf-8")
        if "vi/" not in text and "việt" not in text.lower():
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="vi_llms_missing",
                    message="llms.txt does not contain Vietnamese (vi/) doc links.",
                    path=llms_path,
                )
            )

    return issues


# ---------------------------------------------------------------------------
# DOC-V2-024: Diátaxis header validation
# ---------------------------------------------------------------------------

_VALID_QUADRANTS = frozenset({"tutorial", "how-to", "reference", "explanation"})


def _check_diataxis_headers(repo_name: str, repo_root: Path) -> list[ValidationIssue]:
    """Check all docs/agents/*.md have valid diátaxis headers."""
    import re

    issues: list[ValidationIssue] = []
    docs_dir = repo_root / "docs" / "agents"
    if not docs_dir.exists():
        return issues

    diataxis_re = re.compile(r"<!--\s*di[\u00e1\u00e0]taxis:\s*([\w-]+)\s*-->", re.IGNORECASE)

    for md_path in sorted(docs_dir.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        match = diataxis_re.search(text)
        if not match:
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="diataxis_header_missing",
                    message=f"Missing diátaxis header: {md_path.relative_to(repo_root)}.",
                    path=md_path,
                )
            )
        elif match.group(1).lower() not in _VALID_QUADRANTS:
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="diataxis_header_invalid",
                    message=f"Invalid diátaxis quadrant '{match.group(1)}' in {md_path.relative_to(repo_root)}.",
                    path=md_path,
                )
            )

    return issues


def _check_cross_repo_links(repo_name: str, repo_root: Path, _base_path: Path) -> list[ValidationIssue]:
    """Validate that cross-repo links (e.g., ../vds-skills/...) resolve to existing files."""
    issues: list[ValidationIssue] = []
    docs_dir = repo_root / "docs"
    if not docs_dir.exists():
        return issues
    known_repos = {"vds-scripts", "vds-skills", "vds-ai-memory"}
    # Only match links where the first segment after ../ is a known repo name
    cross_repo_re = re.compile(r"\]\((\.\./(" + "|".join(known_repos) + r")/[^)]+)\)")
    for md_path in sorted(docs_dir.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        for match in cross_repo_re.finditer(text):
            rel_link = match.group(1)
            target_repo = match.group(2)
            target_path = (repo_root.parent / target_repo / rel_link.replace(f"../{target_repo}/", "")).resolve()
            if not target_path.exists():
                issues.append(
                    ValidationIssue(
                        repo=repo_name,
                        check="cross_repo_link_broken",
                        message=f"Broken cross-repo link to '{rel_link}' in {md_path.relative_to(repo_root)}.",
                        path=md_path,
                    )
                )
    return issues


def _check_orchestrator_docs(repo_name: str, repo_root: Path) -> list[ValidationIssue]:
    """Warn if orchestrators from router.py lack corresponding documentation."""
    issues: list[ValidationIssue] = []
    router = repo_root / "vds_cli" / "src" / "vds_cli" / "router.py"
    if not router.exists():
        return issues
    text = router.read_text(encoding="utf-8")
    import re

    orch_names = set(re.findall(r'"([a-z_]+)":\s*\{', text))
    known = {"jira", "confluence", "bitbucket", "git", "scheduler"}
    for name in orch_names - known:
        doc_dir = repo_root / "docs" / "agents" / "reference"
        if doc_dir.exists():
            found = list(doc_dir.glob(f"*{name}*")) or list(doc_dir.glob(f"*{name.replace('_', '-')}*"))
            if not found:
                issues.append(
                    ValidationIssue(
                        repo=repo_name,
                        check="orchestrator_doc_missing",
                        message=f"Orchestrator '{name}' may lack documentation reference.",
                        path=router,
                    )
                )
    return issues


def _check_skill_docs(repo_name: str, repo_root: Path) -> list[ValidationIssue]:
    """Warn if skills from vds-skills lack QUALITY.md or references/."""
    issues: list[ValidationIssue] = []
    if repo_name != "vds-skills":
        return issues
    skills_dir = repo_root / "skills"
    if not skills_dir.exists():
        return issues
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        quality = skill_dir / "QUALITY.md"
        refs = skill_dir / "references"
        if not quality.exists():
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="skill_quality_doc",
                    message=f"Skill missing QUALITY.md: {skill_dir.name}",
                    path=quality,
                )
            )
        if not refs.exists():
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="skill_references",
                    message=f"Skill missing references/: {skill_dir.name}",
                    path=refs,
                )
            )
    return issues


def _check_ecosystem_files(repo_name: str, repo_root: Path) -> list[ValidationIssue]:
    """Warn if ECOSYSTEM-DOCS.md or ECOSYSTEM-CHANGELOG.md are missing/empty."""
    issues: list[ValidationIssue] = []
    for name in ("ECOSYSTEM-DOCS.md", "ECOSYSTEM-CHANGELOG.md"):
        path = repo_root / name
        if not path.exists():
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="ecosystem_files",
                    message=f"{name} is missing.",
                    path=path,
                )
            )
        elif path.stat().st_size == 0:
            issues.append(
                ValidationIssue(
                    repo=repo_name,
                    check="ecosystem_empty",
                    message=f"{name} exists but is empty.",
                    path=path,
                )
            )
    return issues


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# FR-4: Doc Quality Scoring
# ---------------------------------------------------------------------------


def score_doc(doc_path: Path) -> dict[str, Any]:
    """Score a single doc file on quality metrics."""
    text = doc_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    score = 0.0
    details: dict[str, Any] = {}

    # Length (0.3) — target 80 lines
    line_score = min(len(lines) / 80, 1.0)
    score += line_score * 0.3
    details["length"] = round(line_score, 2)

    # Commands (0.3) — has code blocks or command tables
    has_commands = "```bash" in text or ("| `" in text and "--" in text)
    cmd_score = 1.0 if has_commands else 0.0
    score += cmd_score * 0.3
    details["commands"] = cmd_score

    # Workflows (0.2) — has workflow section
    has_workflows = "Workflow" in text or "workflow" in text
    wf_score = 1.0 if has_workflows else 0.0
    score += wf_score * 0.2
    details["workflows"] = wf_score

    # Cross-links (0.2) — has related links
    has_links = "](" in text and ("orchestrator" in text or "skill" in text)
    link_score = 1.0 if has_links else 0.0
    score += link_score * 0.2
    details["cross_links"] = link_score

    details["total"] = round(score, 2)
    return details


def score_all_docs(repo_root: Path) -> dict[str, Any]:
    """Score all docs in a repo and return summary."""
    docs_dir = repo_root / "docs" / "agents"
    if not docs_dir.exists():
        return {"docs": {}, "average": 0.0, "count": 0}

    scores: dict[str, dict[str, Any]] = {}
    for md_path in sorted(docs_dir.rglob("*.md")):
        rel = str(md_path.relative_to(repo_root))
        scores[rel] = score_doc(md_path)

    avg = round(sum(s["total"] for s in scores.values()) / len(scores), 2) if scores else 0.0
    return {"docs": scores, "average": avg, "count": len(scores)}
