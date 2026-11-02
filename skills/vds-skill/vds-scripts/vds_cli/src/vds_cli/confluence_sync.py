"""Confluence documentation hub sync — renders repo-local templates to Confluence pages."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import Any

import yaml
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoConfig:
    slug: str
    name: str
    active: bool
    description: str = ""


@dataclass(frozen=True)
class PageConfig:
    title: str
    page_id: str | None
    page_type: str
    description: str
    template: str
    source_files: list[str] = field(default_factory=list)
    bitbucket_links: list[dict[str, str]] = field(default_factory=list)
    repo: str = "vds-scripts"
    generated: bool = False
    generation_command: str = ""


@dataclass(frozen=True)
class ConfluenceHubConfig:
    parent_page_id: str
    space_key: str
    bitbucket_project: str
    bitbucket_base_url: str
    bitbucket_server: str
    repos: list[RepoConfig]
    pages: list[PageConfig]


@dataclass(frozen=True)
class DocEntry:
    path: Path
    title: str
    quadrant: str
    line_count: int
    last_modified: float
    repo: str
    team_tag: str = ""


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

_NAVIGATION_HUB_TEMPLATE = Template(
    """<h1>VDS Ecosystem Documentation</h1>
<p>This page provides navigation to all VDS repositories and their documentation.</p>

<h2>Repositories</h2>
<table>
<colgroup>
<col />
<col />
<col />
<col />
</colgroup>
<tbody>
<tr>
<th>Repository</th>
<th>Status</th>
<th>Description</th>
<th>Links</th>
</tr>
${repo_rows}
</tbody>
</table>

<h2>Quick Links</h2>
<ul>
<li><a href="${bitbucket_project_url}">Bitbucket Project (WHO)</a></li>
</ul>

<h2>Child Pages</h2>
<ul>
${child_page_links}
</ul>
"""
)

_INSTALLATION_GUIDE_TEMPLATE = Template(
    """<h1>Ecosystem Installation Guide</h1>
<p>Step-by-step setup for new developers joining the VDS ecosystem.</p>

<h2>Prerequisites</h2>
<ul>
<li>Python 3.12+</li>
<li>uv package manager</li>
<li>Git with worktree support</li>
<li>Access to Bitbucket and Confluence</li>
</ul>

<h2>Quick Start</h2>
<ol>
<li>Clone vds-scripts: <code>git clone http://bitbucket.digital.vn/scm/WHO/vds-scripts.git</code></li>
<li>Sync dependencies: <code>./scripts/worktree_uv.sh sync --all-packages</code></li>
<li>Configure environment: <code>cp .env.example ~/.vds/.env</code></li>
<li>Verify: <code>vds-cli doctor</code></li>
</ol>

<h2>Detailed Guides</h2>
<ul>
${bitbucket_links}
</ul>

<h2>Troubleshooting</h2>
<ul>
<li><strong>Module not found:</strong> Run <code>./scripts/worktree_uv.sh sync --all-packages</code></li>
<li><strong>Auth failures:</strong> Check <code>~/.vds/.env</code> has valid tokens</li>
<li><strong>Worktree issues:</strong> Ensure git <code>core.symlinks=true</code></li>
</ul>
"""
)

_QUICK_REFERENCE_TEMPLATE = Template(
    """<h1>${title}</h1>
<p>${description}</p>

<h2>Quick Reference</h2>
${content}

<h2>Detailed Documentation</h2>
<ul>
${bitbucket_links}
</ul>
"""
)

_HEALTH_DASHBOARD_TEMPLATE = Template(
    """<h1>Documentation Health Dashboard</h1>
<p>Auto-generated validation status for VDS documentation.</p>

<h2>Validation Results</h2>
<table>
<colgroup>
<col />
<col />
<col />
<col />
<col />
</colgroup>
<tbody>
<tr>
<th>Repository</th>
<th>AGENTS.md</th>
<th>llms.txt</th>
<th>Freshness</th>
<th>Last Validated</th>
</tr>
${validation_rows}
</tbody>
</table>

<h2>Ownership Model</h2>
<table>
<colgroup>
<col />
<col />
<col />
</colgroup>
<tbody>
<tr>
<th>Document</th>
<th>Owner</th>
<th>Update Trigger</th>
</tr>
<tr>
<td>AGENTS.md</td>
<td>Repo maintainer</td>
<td>Entry points, rules, or CLI flags change</td>
</tr>
<tr>
<td>llms.txt</td>
<td>Repo maintainer</td>
<td>New doc added to docs/</td>
</tr>
<tr>
<td>docs/agents/reference/</td>
<td>Feature author</td>
<td>Feature adds/changes CLI flags</td>
</tr>
<tr>
<td>docs/agents/how-to/</td>
<td>Feature author</td>
<td>Workflow changes</td>
</tr>
</tbody>
</table>

<p><em>Last updated: ${timestamp}</em></p>
"""
)

_DOC_INVENTORY_TEMPLATE = Template(
    """<h1>Documentation Inventory</h1>
<p>Auto-generated inventory of all documentation across the VDS ecosystem.</p>

<h2>Summary</h2>
<table>
<colgroup>
<col />
<col />
<col />
<col />
</colgroup>
<tbody>
<tr>
<th>Quadrant</th>
<th>Count</th>
<th>Total Lines</th>
<th>Avg Lines</th>
</tr>
${summary_rows}
</tbody>
</table>

<h2>Document Details</h2>
${inventory_table}

<p><em>Generated: ${timestamp}</em></p>
"""
)

_TEAM_VIEW_TEMPLATE = Template(
    """<h1>Team View: ${team_tag}</h1>
<p>Filtered documentation view for team scope <strong>${team_tag}</strong>.</p>

<h2>Team Documents</h2>
${team_table}

<p><em>Generated: ${timestamp}</em></p>
"""
)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _get_hub_page_id(config: ConfluenceHubConfig) -> str:
    """Return the navigation hub's page_id (used as parent for child pages)."""
    for page in config.pages:
        if page.page_type == "navigation_hub":
            return page.page_id or config.parent_page_id
    return config.parent_page_id


def load_confluence_config(repo_root: Path) -> ConfluenceHubConfig:
    config_path = repo_root / "docs" / ".confluence.yaml"
    if not config_path.exists():
        raise ValueError(f"Confluence config not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    repos = [
        RepoConfig(
            slug=r["slug"],
            name=r["name"],
            active=r.get("active", True),
            description=r.get("description", ""),
        )
        for r in raw.get("repos", [])
    ]

    pages = []
    for p in raw.get("pages", []):
        pages.append(
            PageConfig(
                title=p["title"],
                page_id=p.get("page_id"),
                page_type=p.get("type", "quick_reference"),
                description=p.get("description", ""),
                template=p.get("template", "quick_reference"),
                source_files=p.get("source_files", []),
                bitbucket_links=p.get("bitbucket_links", []),
                repo=p.get("repo", "vds-scripts"),
                generated=p.get("generated", False),
                generation_command=p.get("generation_command", ""),
            )
        )

    return ConfluenceHubConfig(
        parent_page_id=raw["parent_page_id"],
        space_key=raw["space_key"],
        bitbucket_project=raw["bitbucket"]["project"],
        bitbucket_base_url=raw["bitbucket"]["base_url"],
        bitbucket_server=raw["bitbucket"].get("server", "internal"),
        repos=repos,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# Bitbucket URL helpers
# ---------------------------------------------------------------------------


def bitbucket_browse_url(base_url: str, project: str, repo: str, path: str = "") -> str:
    url = f"{base_url}/projects/{project}/repos/{repo}/browse"
    if path:
        url = f"{url}/{path}"
    return url


def render_repo_rows(config: ConfluenceHubConfig) -> str:
    rows = []
    for repo in config.repos:
        status = "Active" if repo.active else "Archived"
        agents_link = bitbucket_browse_url(config.bitbucket_base_url, config.bitbucket_project, repo.slug, "AGENTS.md")
        readme_link = bitbucket_browse_url(config.bitbucket_base_url, config.bitbucket_project, repo.slug, "README.md")
        row = (
            f"<tr>"
            f"<td><strong>{repo.name}</strong></td>"
            f"<td>{status}</td>"
            f"<td>{repo.description}</td>"
            f'<td><a href="{agents_link}">AGENTS.md</a> | '
            f'<a href="{readme_link}">README</a></td>'
            f"</tr>"
        )
        rows.append(row)
    return "\n".join(rows)


def render_child_page_links(pages: list[PageConfig]) -> str:
    links = []
    for page in pages:
        if page.page_type == "navigation_hub":
            continue
        links.append(f'<li><a href="/pages/viewpage.action?pageId={page.page_id}">{page.title}</a></li>')
    return "\n".join(links)


def render_bitbucket_links(config: ConfluenceHubConfig, page: PageConfig) -> str:
    links = []
    for link in page.bitbucket_links:
        url = bitbucket_browse_url(
            config.bitbucket_base_url,
            config.bitbucket_project,
            page.repo,
            link["path"],
        )
        links.append(f'<li><a href="{url}">{link["label"]}</a></li>')
    return "\n".join(links)


# ---------------------------------------------------------------------------
# DOC-V2-017: Word count check
# ---------------------------------------------------------------------------


def check_word_count(body: str, max_words: int = 800) -> int:
    """Count words in body and log WARNING if exceeding max_words."""
    words = body.split()
    count = len(words)
    if count > max_words:
        logger.warning("Word count %d exceeds %d (max_words)", count, max_words)
    return count


# ---------------------------------------------------------------------------
# DOC-V2-018: Doc tree scanner + inventory table renderer
# ---------------------------------------------------------------------------


def scan_docs_tree(repo_root: Path) -> list[DocEntry]:
    """Walk docs/agents/ tree, read <!-- diátaxis: X --> headers, return categorized entries."""
    docs_dir = repo_root / "docs" / "agents"
    entries: list[DocEntry] = []
    if not docs_dir.exists():
        return entries

    diataxis_re = re.compile(r"<!--\s*diátaxis:\s*([\w-]+)\s*-->", re.IGNORECASE)
    team_re = re.compile(r"<!--\s*team:\s*([\w-]+)\s*-->", re.IGNORECASE)

    for md_path in docs_dir.rglob("*.md"):
        text = md_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        first_line = lines[0] if lines else ""

        # Extract title from first H1
        title_match = re.match(r"^#\s+(.+)$", first_line)
        title = title_match.group(1) if title_match else md_path.stem.replace("-", " ").title()

        # Extract diátaxis quadrant from HTML comment
        quadrant = "uncategorized"
        for line in lines[:10]:
            m = diataxis_re.search(line)
            if m:
                quadrant = m.group(1).lower()
                break

        # Extract team tag
        team_tag = ""
        for line in lines[:10]:
            m = team_re.search(line)
            if m:
                team_tag = m.group(1).lower()
                break

        entries.append(
            DocEntry(
                path=md_path.relative_to(repo_root),
                title=title,
                quadrant=quadrant,
                line_count=len(lines),
                last_modified=md_path.stat().st_mtime,
                repo=repo_root.name,
                team_tag=team_tag,
            )
        )

    return sorted(entries, key=lambda e: (e.quadrant, e.title))


def render_inventory_table(docs: list[DocEntry]) -> str:
    """Generate XHTML table for Confluence doc_inventory page type."""
    if not docs:
        return "<p><em>No documents found.</em></p>"

    rows = []
    for doc in docs:
        rows.append(
            f"<tr>"
            f"<td><strong>{doc.title}</strong></td>"
            f"<td>{doc.quadrant}</td>"
            f"<td>{doc.repo}</td>"
            f"<td>{doc.line_count}</td>"
            f"<td>{doc.path}</td>"
            f"</tr>"
        )

    return (
        "<table>"
        "<colgroup><col /><col /><col /><col /><col /></colgroup>"
        "<tbody>"
        "<tr><th>Title</th><th>Quadrant</th><th>Repo</th><th>Lines</th><th>Path</th></tr>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


# ---------------------------------------------------------------------------
# DOC-V2-020: Team view renderer
# ---------------------------------------------------------------------------


def render_team_view(team_tag: str, docs: list[DocEntry]) -> str:
    """Filter docs by team scope and render status table."""
    filtered = [d for d in docs if d.team_tag.lower() == team_tag.lower()]
    if not filtered:
        return "<p><em>No documents found for this team.</em></p>"

    rows = []
    for doc in filtered:
        rows.append(
            f"<tr>"
            f"<td><strong>{doc.title}</strong></td>"
            f"<td>{doc.quadrant}</td>"
            f"<td>{doc.repo}</td>"
            f"<td>{doc.line_count}</td>"
            f"<td>{doc.path}</td>"
            f"</tr>"
        )

    return (
        "<table>"
        "<colgroup><col /><col /><col /><col /><col /></colgroup>"
        "<tbody>"
        "<tr><th>Title</th><th>Quadrant</th><th>Repo</th><th>Lines</th><th>Path</th></tr>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


# ---------------------------------------------------------------------------
# DOC-V2-022: Bitbucket link health checker
# ---------------------------------------------------------------------------


def check_bitbucket_links(config: ConfluenceHubConfig) -> list[dict[str, Any]]:
    """HEAD each Bitbucket link, report broken links."""
    import urllib.request

    results: list[dict[str, Any]] = []
    for page in config.pages:
        for link in page.bitbucket_links:
            url = bitbucket_browse_url(
                config.bitbucket_base_url,
                config.bitbucket_project,
                page.repo,
                link["path"],
            )
            try:
                req = urllib.request.Request(url, method="HEAD")
                req.add_header("User-Agent", "vds-cli/1.0")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status = resp.getcode()
            except Exception as exc:
                status = None
                logger.warning("Broken Bitbucket link: %s — %s", url, exc)

            results.append(
                {
                    "page_title": page.title,
                    "label": link.get("label", ""),
                    "url": url,
                    "status": "ok" if status and status < 400 else "broken",
                    "status_code": status,
                }
            )
    return results


# ---------------------------------------------------------------------------
# Page body rendering
# ---------------------------------------------------------------------------


def _read_repo_content(repo_root: Path, rel_path: str) -> str:
    """Read content from a repo file for embedding in Confluence pages."""
    path = repo_root / rel_path
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"<p><em>Content not found: {rel_path}</em></p>"


def _markdown_to_storage(md: str) -> str:
    """Minimal markdown → Confluence storage format conversion."""
    import re

    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", md, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Code blocks
    html = re.sub(
        r"```([\w-]+)?\n(.*?)```",
        lambda m: (
            f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{m.group(1) or ""}</ac:parameter><ac:plain-text-body><![CDATA[{m.group(2)}]]></ac:plain-text-body></ac:structured-macro>'
        ),
        html,
        flags=re.DOTALL,
    )

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Bold/italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links [text](url)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Lists
    lines = html.split("\n")
    result = []
    in_ul = False
    for line in lines:
        if line.startswith("- "):
            if not in_ul:
                result.append("<ul>")
                in_ul = True
            result.append(f"<li>{line[2:]}</li>")
        else:
            if in_ul:
                result.append("</ul>")
                in_ul = False
            result.append(line)
    if in_ul:
        result.append("</ul>")

    return "\n".join(result)


def render_page_body(
    config: ConfluenceHubConfig,
    page: PageConfig,
    repo_root: Path | None = None,
) -> str:
    if page.template == "navigation_hub":
        return _NAVIGATION_HUB_TEMPLATE.substitute(
            repo_rows=render_repo_rows(config),
            child_page_links=render_child_page_links(config.pages),
            bitbucket_project_url=f"{config.bitbucket_base_url}/projects/{config.bitbucket_project}",
        )

    if page.template == "installation_guide":
        return _INSTALLATION_GUIDE_TEMPLATE.substitute(
            bitbucket_links=render_bitbucket_links(config, page),
        )

    if page.template == "quick_reference":
        # Try to load content from sibling worktree template files
        content = "<p>See linked Bitbucket documentation for full details.</p>"
        if repo_root and page.repo != "vds-scripts":
            # Map repo name to worktree name and filename
            # vds-skills         → confluence-hub-skills     → vds-skills-quick-ref.md
            if page.repo == "vds-skills":
                wt_name = "confluence-hub-skills"
                file_name = "vds-skills-quick-ref.md"
            else:
                wt_name = f"confluence-hub-{page.repo.replace('vds-', '')}"
                file_name = f"{page.repo}-quick-ref.md"

            # Worktrees are siblings: confluence-hub-scripts/../confluence-hub-skills
            wt_content_path = (
                repo_root.parent  # .../worktrees/
                / wt_name
                / "docs"
                / "confluence"
                / file_name
            )
            if wt_content_path.exists():
                console.print(f"[dim]Loading content from {wt_content_path}[/dim]")
                md = wt_content_path.read_text(encoding="utf-8")
                content = _markdown_to_storage(md)

        return _QUICK_REFERENCE_TEMPLATE.substitute(
            title=page.title,
            description=page.description,
            content=content,
            bitbucket_links=render_bitbucket_links(config, page),
        )

    if page.template == "health_dashboard":
        # Try to populate from validate output
        validation_rows = '<tr><td colspan="5">Run <code>vds-cli docs validate</code> to populate</td></tr>'
        timestamp = "Not yet generated"

        if repo_root:
            import subprocess

            try:
                proc = subprocess.run(
                    ["vds-cli", "docs", "validate", "--repo-root", str(repo_root)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if proc.returncode == 0:
                    # Parse output for status
                    lines = proc.stdout.strip().split("\n")
                    rows = []
                    for line in lines:
                        if "✅" in line or "❌" in line:
                            rows.append(f'<tr><td colspan="5">{line}</td></tr>')
                    if rows:
                        validation_rows = "\n".join(rows)

                    timestamp = datetime.now(UTC).isoformat()
            except Exception:
                pass

        return _HEALTH_DASHBOARD_TEMPLATE.substitute(
            validation_rows=validation_rows,
            timestamp=timestamp,
        )

    if page.template == "doc_inventory":
        docs = scan_docs_tree(repo_root) if repo_root else []
        summary: dict[str, dict[str, Any]] = {}
        for doc in docs:
            q = doc.quadrant
            if q not in summary:
                summary[q] = {"count": 0, "lines": 0}
            summary[q]["count"] += 1
            summary[q]["lines"] += doc.line_count

        summary_rows = []
        for q, stats in sorted(summary.items()):
            avg = round(stats["lines"] / stats["count"], 1) if stats["count"] else 0
            summary_rows.append(
                f"<tr><td>{q}</td><td>{stats['count']}</td><td>{stats['lines']}</td><td>{avg}</td></tr>"
            )
        if not summary_rows:
            summary_rows.append('<tr><td colspan="4">No documents found</td></tr>')

        timestamp = datetime.now(UTC).isoformat()
        return _DOC_INVENTORY_TEMPLATE.substitute(
            summary_rows="\n".join(summary_rows),
            inventory_table=render_inventory_table(docs),
            timestamp=timestamp,
        )

    if page.template == "team_view":
        docs = scan_docs_tree(repo_root) if repo_root else []
        team_tag = page.description.split(":")[-1].strip() if ":" in page.description else page.description.strip()
        timestamp = datetime.now(UTC).isoformat()
        return _TEAM_VIEW_TEMPLATE.substitute(
            team_tag=team_tag,
            team_table=render_team_view(team_tag, docs),
            timestamp=timestamp,
        )

    return f"<h1>{page.title}</h1><p>{page.description}</p>"


# ---------------------------------------------------------------------------
# Confluence operations (dry-run aware)
# ---------------------------------------------------------------------------


def sync_page(
    config: ConfluenceHubConfig,
    page: PageConfig,
    *,
    dry_run: bool = False,
    create_missing: bool = False,
    repo_root: Path | None = None,
    validate_links: bool = False,
) -> dict[str, Any]:
    body = render_page_body(config, page, repo_root=repo_root)
    check_word_count(body)

    if dry_run:
        console.print(f"[cyan]DRY-RUN:[/cyan] Would sync page '{page.title}'")
        console.print(f"  Type: {page.page_type}")
        console.print(f"  Body length: {len(body)} chars")
        if page.page_id:
            console.print(f"  Page ID: {page.page_id} (update)")
        else:
            console.print(f"  Parent ID: {config.parent_page_id} (create)")
        if validate_links:
            link_results = check_bitbucket_links(config)
            broken = [r for r in link_results if r["status"] != "ok"]
            console.print(f"  Link check: {len(link_results)} total, {len(broken)} broken")
        return {"dry_run": True, "title": page.title}

    # Early return for skip case — no Confluence client needed
    if not page.page_id and not create_missing:
        console.print(f"[yellow]⚠️ Skipped:[/yellow] {page.title} (no page_id, use --create-missing)")
        return {"skipped": True, "title": page.title}

    # Import here to avoid dependency issues when just loading config
    try:
        from confluence_orchestrator.content import ContentClient

        from confluence_orchestrator import ConfluenceClient, load_settings
    except ImportError as exc:
        console.print(f"[red]❌ Cannot import ConfluenceClient: {exc}[/red]")
        console.print("[yellow]Hint: Run ./scripts/worktree_uv.sh sync --all-packages[/yellow]")
        raise

    settings = load_settings()
    client = ConfluenceClient(settings, server=config.bitbucket_server)
    content = ContentClient(client)

    try:
        if page.page_id:
            # Update existing page — determine correct parent
            # Navigation hub uses config.parent_page_id
            # Child pages use navigation hub page_id as their parent
            hub_page_id = _get_hub_page_id(config)
            target_parent = config.parent_page_id if page.page_type == "navigation_hub" else hub_page_id

            result = content.update_page(
                page_id=page.page_id,
                title=page.title,
                body=body,
                space_key=config.space_key,
                representation="storage",
                minor_edit=True,
                message="Synced from vds-cli docs confluence-sync",
                parent_id=target_parent,
            )
            console.print(f"[green]✅ Updated:[/green] {page.title} (pageId={result.get('id')})")
        elif create_missing:
            # Create new page
            hub_page_id = _get_hub_page_id(config)
            target_parent = config.parent_page_id if page.page_type == "navigation_hub" else hub_page_id

            result = content.create_page(
                space_key=config.space_key,
                title=page.title,
                body=body,
                parent_id=target_parent,
                representation="storage",
            )
            console.print(f"[green]✅ Created:[/green] {page.title} (pageId={result.get('id')})")
            return {"created": True, "page_id": result.get("id"), "title": page.title}
    finally:
        client.close()

    return {}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_confluence_sync(
    repo_root: Path,
    *,
    dry_run: bool = False,
    page_title: str | None = None,
    create_missing: bool = False,
    validate_links: bool = False,
) -> list[dict[str, Any]]:
    config = load_confluence_config(repo_root)

    results = []
    for page in config.pages:
        if page_title and page.title != page_title:
            continue
        result = sync_page(
            config,
            page,
            dry_run=dry_run,
            create_missing=create_missing,
            repo_root=repo_root,
            validate_links=validate_links,
        )
        results.append(result)

    return results
