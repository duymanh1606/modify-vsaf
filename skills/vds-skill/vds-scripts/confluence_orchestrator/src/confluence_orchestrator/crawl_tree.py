"""Confluence tree crawling and on-disk export helpers.

This module is intentionally dependency-light (std lib + BeautifulSoup) so the output
can be used as input for downstream LLM/document analysis pipelines.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import time
import zipfile
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .http import ConfluenceClient

_JIRA_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
_MIME_SUFFIX_MAP: dict[str, str] = {
    "application/json": ".json",
    "application/msword": ".doc",
    "application/pdf": ".pdf",
    "application/vnd.jgraph.mxfile": ".drawio",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "text/csv": ".csv",
    "text/plain": ".txt",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_filename(name: str) -> str:
    # Preserve unicode for VN titles, but remove path separators + control chars.
    cleaned = name.replace("/", "-").replace("\\", "-").replace("\0", "")
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned).strip()
    return cleaned or "untitled"


def _normalise_suffix(value: str) -> str:
    cleaned = (value or "").strip().lower()
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith(".") else f".{cleaned}"


def _guess_attachment_suffix(attachment: dict[str, Any]) -> str | None:
    extensions = attachment.get("extensions") or {}
    metadata = attachment.get("metadata") or {}

    if isinstance(extensions, dict):
        ext = extensions.get("fileExtension") or extensions.get("file_extension")
        if isinstance(ext, str) and ext.strip():
            normalised = _normalise_suffix(ext)
            return normalised if normalised else None

    media_type = None
    if isinstance(extensions, dict):
        media_type = extensions.get("mediaType") or extensions.get("media_type")
    if not media_type and isinstance(metadata, dict):
        media_type = metadata.get("mediaType") or metadata.get("media_type")

    if isinstance(media_type, str) and media_type.strip():
        mapped = _MIME_SUFFIX_MAP.get(media_type.strip().lower())
        if mapped:
            return mapped
    return None


def _safe_attachment_filename(attachment_id: str, title: str, *, fallback_suffix: str | None = None) -> str:
    safe_title = _safe_filename(title)
    path = Path(safe_title)
    stem = path.stem or "attachment"
    suffix = path.suffix
    if not suffix and fallback_suffix:
        suffix = _normalise_suffix(fallback_suffix)

    # Keep filenames under typical filesystem limits (255 bytes). We preserve the
    # attachment id prefix for stability and trim the human title if needed.
    max_stem_length = 180
    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length].rstrip()
    safe_title = f"{stem}{suffix}"
    return f"{attachment_id}_{safe_title}"


def _escape_cql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def resolve_page_ref(page_ref: str, http: ConfluenceClient) -> str:
    """Resolve a page reference to a numeric page ID.

    Supported forms:
    - numeric ID: "74014717"
    - viewpage: ".../pages/viewpage.action?pageId=74014717"
    - display URL: ".../display/TDOV/13.02.10.+BRD"
    """
    page_ref = (page_ref or "").strip()
    if not page_ref:
        raise ValueError("page_ref is empty")

    if page_ref.isdigit():
        return page_ref

    parsed = urlparse(page_ref)
    if parsed.query:
        qs = parse_qs(parsed.query)
        page_ids = qs.get("pageId") or qs.get("pageid")
        if page_ids and page_ids[0].isdigit():
            return page_ids[0]

    # /display/<SPACE>/<TITLE>
    match = re.search(r"/display/([^/]+)/(.+)$", parsed.path or "")
    if match:
        space = unquote(match.group(1))
        # Confluence "display" URLs often encode spaces as '+'
        title = unquote(match.group(2)).replace("+", " ").strip()
        cql = f'space="{_escape_cql(space)}" and title="{_escape_cql(title)}" and type=page'
        result = http.search_cql(cql, limit=5)
        results = result.get("results", []) if isinstance(result, dict) else []
        for item in results:
            if not isinstance(item, dict):
                continue
            # Confluence CQL results usually wrap content under `content`.
            raw_id = item.get("id")
            if raw_id is None and isinstance(item.get("content"), dict):
                raw_id = item["content"].get("id")
            if raw_id is not None and str(raw_id).isdigit():
                return str(raw_id)

        raise ValueError(f"Unable to resolve display URL to page ID (space={space!r}, title={title!r})")

    raise ValueError(f"Unsupported page reference: {page_ref}")


@dataclass(slots=True)
class CrawlOptions:
    max_depth: int = 3
    include_attachments: bool = True
    emit_corpus: bool = False
    emit_link_graph: bool = False
    emit_tables: bool = False
    emit_mentions: bool = False
    body_format: str = "view"
    chunk_max_chars: int | None = 4000
    resume: bool = False
    max_nodes: int | None = 500
    bundle: bool = False
    page_concurrency: int = 5
    staged_mode: str = "off"
    incremental_cql: bool = True
    incremental_overlap_minutes: int = 5
    full_reconciliation_interval_days: int = 7
    rate_limit_budget: int = 50_000
    runtime_event_sink: Callable[[str, dict[str, Any]], None] | None = None


def _emit_runtime_event(options: CrawlOptions, event: str, **payload: Any) -> None:
    if not callable(options.runtime_event_sink):
        return
    try:
        options.runtime_event_sink(event, payload)
    except Exception:
        return


def _create_bundle_zip(output_dir: Path, root_page_id: str, manifest_path: Path) -> Path:
    """Create a zip bundle of all crawl artifacts for offline handoff (TSK-189)."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"crawl_bundle_{root_page_id}_{timestamp}.zip"
    bundle_path = output_dir / bundle_name

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add all HTML files
        for html_file in output_dir.glob("*.html"):
            zf.write(html_file, html_file.name)

        # Add attachments directory
        attachments_dir = output_dir / "attachments"
        if attachments_dir.exists():
            for att_file in attachments_dir.iterdir():
                if att_file.is_file():
                    zf.write(att_file, f"attachments/{att_file.name}")

        # Add artifact files
        artifact_files = [
            "corpus.jsonl",
            "link-graph.json",
            "tables.jsonl",
            "mentions.jsonl",
            "crawl_state.json",
        ]
        for artifact_name in artifact_files:
            artifact_path = output_dir / artifact_name
            if artifact_path.exists():
                zf.write(artifact_path, artifact_name)

        # Add manifest
        if manifest_path.exists():
            zf.write(manifest_path, manifest_path.name)

    return bundle_path


@dataclass(slots=True)
class CrawlState:
    """Persistent crawl state for resume/incremental crawling (TSK-188)."""

    root_page_id: str
    body_format: str
    visited_pages: dict[str, dict[str, Any]]  # page_id -> {version, html_sha256, visited_at}
    pending_queue: list[tuple[str, str | None, int]]  # [(page_id, parent_id, depth), ...]
    started_at: str
    last_updated_at: str
    completed: bool = False
    last_sync_timestamp: str | None = None
    last_full_reconciliation_timestamp: str | None = None
    run_diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to JSON-compatible dict."""
        return {
            "root_page_id": self.root_page_id,
            "body_format": self.body_format,
            "visited_pages": self.visited_pages,
            "pending_queue": [list(item) for item in self.pending_queue],
            "started_at": self.started_at,
            "last_updated_at": self.last_updated_at,
            "completed": self.completed,
            "last_sync_timestamp": self.last_sync_timestamp,
            "last_full_reconciliation_timestamp": self.last_full_reconciliation_timestamp,
            "run_diagnostics": self.run_diagnostics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrawlState:
        """Deserialize state from JSON-compatible dict."""
        return cls(
            root_page_id=data["root_page_id"],
            body_format=data.get("body_format", "view"),
            visited_pages=data.get("visited_pages", {}),
            pending_queue=[tuple(item) for item in data.get("pending_queue", [])],
            started_at=data.get("started_at", _now_iso()),
            last_updated_at=data.get("last_updated_at", _now_iso()),
            completed=data.get("completed", False),
            last_sync_timestamp=data.get("last_sync_timestamp"),
            last_full_reconciliation_timestamp=data.get("last_full_reconciliation_timestamp"),
            run_diagnostics=data.get("run_diagnostics", {}),
        )

    def is_page_unchanged(self, page_id: str, version: int | None, html_sha256: str | None) -> bool:
        """Check if a page is unchanged since last crawl."""
        if page_id not in self.visited_pages:
            return False
        prev = self.visited_pages[page_id]
        prev_version = prev.get("version")
        prev_hash = prev.get("html_sha256")
        # If both version and hash match, page is unchanged
        if prev_version is not None and version is not None and prev_version == version:
            return True
        return bool(prev_hash is not None and html_sha256 is not None and prev_hash == html_sha256)

    def record_page(self, page_id: str, version: int | None, html_sha256: str | None) -> None:
        """Record a visited page."""
        self.visited_pages[page_id] = {
            "version": version,
            "html_sha256": html_sha256,
            "visited_at": _now_iso(),
        }
        self.last_updated_at = _now_iso()


@dataclass(slots=True)
class _FetchedPage:
    page_id: str
    parent_id: str | None
    depth: int
    status: str  # fetched|unchanged|error
    page_payload: dict[str, Any] | None = None
    version_payload: dict[str, Any] | None = None
    children: list[tuple[str, str | None, int]] = field(default_factory=list)
    error: str | None = None


def _load_crawl_state(state_path: Path) -> CrawlState | None:
    """Load crawl state from disk if it exists."""
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return CrawlState.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _save_crawl_state(state: CrawlState, state_path: Path) -> None:
    """Persist crawl state to disk."""
    state.last_updated_at = _now_iso()
    state_path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _normalise_body_format(value: str | None) -> str:
    normalised = (value or "view").strip().lower().replace("-", "_")
    if normalised in {"view", "storage", "export_view"}:
        return normalised
    raise ValueError(f"Unsupported body format: {value!r} (expected: view|export_view|storage)")


def _normalise_page_concurrency(value: int | None) -> int:
    if value is None:
        return 5
    return max(1, int(value))


def _normalise_staged_mode(value: str | None) -> str:
    normalised = (value or "off").strip().lower().replace("-", "_")
    if normalised in {"off", "structure_first"}:
        return normalised
    raise ValueError(f"Unsupported staged mode: {value!r} (expected: off|structure_first)")


def _split_text_preserving_words(text: str, max_chars: int) -> list[str]:
    """Split a long string into <= max_chars chunks, preferring whitespace boundaries."""
    stripped = (text or "").strip()
    if not stripped:
        return []
    if max_chars <= 0:
        return [stripped]
    if len(stripped) <= max_chars:
        return [stripped]

    words = stripped.split()
    parts: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        parts.append(" ".join(current))
        current = []
        current_len = 0

    for word in words:
        if not current:
            current = [word]
            current_len = len(word)
        elif current_len + 1 + len(word) <= max_chars:
            current.append(word)
            current_len += 1 + len(word)
        else:
            flush()
            if len(word) <= max_chars:
                current = [word]
                current_len = len(word)
            else:
                # Pathological case: a single token exceeds max_chars; hard-split.
                for offset in range(0, len(word), max_chars):
                    parts.append(word[offset : offset + max_chars])

    flush()
    return parts


def _pack_segments(segments: list[str], max_chars: int) -> list[str]:
    if max_chars <= 0:
        joined = "\n".join([seg for seg in segments if seg.strip()]).strip()
        return [joined] if joined else []

    packed: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        packed.append("\n".join(current).strip())
        current = []
        current_len = 0

    for seg in segments:
        seg = (seg or "").strip()
        if not seg:
            continue
        sep_len = 1 if current else 0  # newline
        if not current or current_len + sep_len + len(seg) <= max_chars:
            if current:
                current_len += 1
            current.append(seg)
            current_len += len(seg)
            continue

        flush()
        current = [seg]
        current_len = len(seg)

    flush()
    return [chunk for chunk in packed if chunk.strip()]


def _extract_target_page_id(target_url: str | None) -> str | None:
    if not target_url:
        return None

    parsed = urlparse(target_url)
    if parsed.query:
        qs = parse_qs(parsed.query)
        for key, values in qs.items():
            if key.lower() != "pageid" or not values:
                continue
            candidate = values[0]
            if isinstance(candidate, str) and candidate.isdigit():
                return candidate

    match = re.search(r"/pages/(\d+)(?:/|$)", parsed.path or "")
    if match:
        return match.group(1)
    return None


def _classify_target_type(target_url: str | None) -> str | None:
    if not target_url:
        return None

    url = target_url.strip()
    if not url:
        return None
    if url.startswith("mailto:"):
        return "email"

    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if "/display/" in path or "viewpage.action" in path or re.search(r"/pages/\d+(?:/|$)", path):
        return "confluence_page"
    if "jira" in host or "/browse/" in path:
        return "jira"
    if "bitbucket" in host or "/scm/" in path:
        return "bitbucket"
    if parsed.scheme in {"http", "https"}:
        return "external"
    return "external"


def _extract_jira_key_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    match = re.search(r"/browse/([A-Z][A-Z0-9]+-\d+)", parsed.path or "")
    if match:
        return match.group(1)
    return None


def _extract_links(html: str, *, base_url: str | None = None) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[dict[str, Any]] = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        href = str(href).strip()
        if not href:
            continue
        text = a.get_text(" ", strip=True) or None
        links.append({"href": href, "text": text})
    if not base_url:
        return links

    normalized: list[dict[str, Any]] = []
    base = base_url.rstrip("/")
    for entry in links:
        href = entry["href"]
        if href.startswith("#"):
            continue
        if href.startswith(("http://", "https://")):
            url = href
        elif href.startswith("/"):
            url = f"{base}{href}"
        else:
            # best-effort: keep as-is (could be relative to current page)
            url = href
        # Drop fragments for canonicalization
        parsed = urlparse(url)
        url = parsed._replace(fragment="").geturl()
        normalized.append({"url": url, "text": entry.get("text")})
    return normalized


def _chunk_html_by_headings(html: str, *, max_chars: int | None = None) -> list[dict[str, Any]]:
    """Chunk HTML into heading-scoped blocks for JSONL corpus output."""
    soup = BeautifulSoup(html, "html.parser")

    chunks: list[dict[str, Any]] = []
    heading_stack: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        lines = [line for line in buffer if line.strip()]
        buffer = []
        if not lines:
            return

        segments: list[str] = []
        max_limit = max_chars if isinstance(max_chars, int) and max_chars > 0 else None
        for line in lines:
            if max_limit and len(line) > max_limit:
                segments.extend(_split_text_preserving_words(line, max_limit))
            else:
                segments.append(line.strip())

        if max_limit is None:
            text = "\n".join([seg for seg in segments if seg.strip()]).strip()
            if text:
                chunks.append({"heading_path": list(heading_stack), "text": text, "ordinal": 0})
            return

        for ordinal, text in enumerate(_pack_segments(segments, max_limit)):
            chunks.append({"heading_path": list(heading_stack), "text": text, "ordinal": ordinal})

    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre"]):
        name = el.name.lower()
        if name.startswith("h"):
            flush()
            level = int(name[1])
            title = el.get_text(" ", strip=True)
            if not title:
                continue
            heading_stack[:] = heading_stack[: max(0, level - 1)]
            heading_stack.append(title)
            continue

        text = el.get_text(" ", strip=True)
        if not text:
            continue
        buffer.append(text)

    flush()
    return chunks


def _extract_tables(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    extracted: list[dict[str, Any]] = []

    for index, table in enumerate(soup.find_all("table")):
        headers: list[str] | None = None
        rows: list[list[str]] = []

        # Prefer explicit <thead> headers when present.
        thead = table.find("thead")
        if thead:
            head_row = thead.find("tr")
            if head_row:
                header_cells = head_row.find_all(["th", "td"])
                header_texts = [cell.get_text(" ", strip=True) for cell in header_cells]
                headers = [h for h in header_texts if h]

        # Extract all row cells.
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            row = [cell.get_text(" ", strip=True) for cell in cells]
            row = [cell for cell in row if cell]
            if row:
                rows.append(row)

        # If we did not find a <thead>, treat the first row with <th> as headers.
        if headers is None and rows:
            first_tr = table.find("tr")
            if first_tr and first_tr.find("th"):
                headers = rows[0]
                rows = rows[1:]

        extracted.append(
            {
                "table_index": index,
                "headers": headers,
                "rows": rows,
                "row_count": len(rows),
                "col_count": max((len(row) for row in rows), default=0),
            }
        )

    return extracted


def _extract_mentions(html: str, *, base_url: str | None = None) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    extracted: list[dict[str, Any]] = []

    # 1) Link-based mentions (already normalized by base_url when provided).
    for link in _extract_links(html, base_url=base_url):
        url = str(link.get("url") or "").strip()
        if not url:
            continue

        mention_type = _classify_target_type(url)
        if mention_type == "confluence_page":
            value = _extract_target_page_id(url) or url
        elif mention_type == "jira":
            value = _extract_jira_key_from_url(url) or url
        elif mention_type == "email":
            value = url.removeprefix("mailto:").strip() or url
        else:
            value = url

        extracted.append(
            {
                "type": mention_type or "external",
                "value": value,
                "url": url,
                "anchor_text": link.get("text"),
                "source": "link",
            }
        )

    # 2) Plain-text Jira keys (best-effort).
    plain_text = soup.get_text(" ", strip=True)
    for key in sorted(set(_JIRA_KEY_RE.findall(plain_text or ""))):
        extracted.append(
            {
                "type": "jira_key",
                "value": key,
                "url": None,
                "anchor_text": None,
                "source": "text",
            }
        )

    # Deduplicate mentions by stable key and keep deterministic ordering.
    seen: set[tuple[str, str, str | None]] = set()
    unique: list[dict[str, Any]] = []
    for entry in extracted:
        mention_type = str(entry.get("type") or "").strip() or "external"
        value = str(entry.get("value") or "").strip()
        url = entry.get("url")
        url = str(url).strip() if isinstance(url, str) else None
        if not value:
            continue
        key = (mention_type, value, url)
        if key in seen:
            continue
        seen.add(key)
        unique.append({**entry, "type": mention_type, "value": value, "url": url})

    unique.sort(key=lambda m: (m.get("type") or "", m.get("value") or "", m.get("url") or ""))
    return unique


def crawl_tree_to_disk(
    *,
    http: ConfluenceClient,
    root_ref: str,
    output_dir: Path,
    options: CrawlOptions,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Crawl a Confluence page tree and download content/attachments to disk.

    Supports resume/incremental crawling (TSK-188):
    - resume=True: Load state from previous run, skip unchanged pages
    - max_nodes: Limit total pages processed (safety for large trees)
    """
    body_format = _normalise_body_format(options.body_format)
    page_concurrency = _normalise_page_concurrency(options.page_concurrency)
    staged_mode = _normalise_staged_mode(options.staged_mode)
    use_structure_first = staged_mode == "structure_first"
    chunk_max_chars = options.chunk_max_chars if isinstance(options.chunk_max_chars, int) else None
    resolved_root_id = resolve_page_ref(root_ref, http)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    attachments_dir = output_dir / "attachments"
    attachments_dir.mkdir(exist_ok=True)
    resolved_manifest_path = manifest_path or (output_dir / "crawl_manifest.json")

    def _meta_from_existing_html(
        *,
        page_id: str,
        parent_id: str | None,
        depth: int,
        page_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        html_candidates = sorted(output_dir.glob(f"{page_id}_*.html"))
        html_path = html_candidates[0] if html_candidates else None
        title = None
        page_url = None
        page_version = None
        page_updated = None
        space_key = None
        if isinstance(page_payload, dict):
            raw_title = page_payload.get("title")
            if raw_title:
                title = str(raw_title)
            links = page_payload.get("_links")
            if isinstance(links, dict):
                base_url = str(links.get("base") or "")
                web_ui = str(links.get("webui") or "")
                page_url = f"{base_url}{web_ui}" if base_url and web_ui else None
            version = page_payload.get("version")
            if isinstance(version, dict):
                page_version = version.get("number")
                page_updated = version.get("when")
            space = page_payload.get("space")
            if isinstance(space, dict):
                raw_space = space.get("key")
                if raw_space:
                    space_key = str(raw_space)
        if title is None and html_path is not None:
            title = html_path.stem.split("_", 1)[1] if "_" in html_path.stem else html_path.stem

        meta: dict[str, Any] = {
            "page_id": page_id,
            "title": title,
            "page_url": page_url,
            "parent_id": parent_id,
            "depth": depth,
            "status": "downloaded" if html_path is not None else "unchanged",
            "html_path": str(html_path) if html_path is not None else None,
            "html_sha256": None,
            "html_size_bytes": None,
            "source_format": "html-view",
            "space_key": space_key,
            "page_version": page_version,
            "page_updated": page_updated,
            "ancestor_ids": [],
            "ancestor_titles": [],
            "error": None,
        }
        if html_path is not None and html_path.exists():
            html_bytes = html_path.read_bytes()
            meta["html_sha256"] = _sha256_bytes(html_bytes)
            meta["html_size_bytes"] = html_path.stat().st_size
        return meta

    previous_page_meta_by_id: dict[str, dict[str, Any]] = {}
    previous_attachments_by_page: dict[str, list[dict[str, Any]]] = {}
    if options.resume and resolved_manifest_path.exists():
        try:
            loaded = json.loads(resolved_manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                root_meta = loaded.get("page")
                if isinstance(root_meta, dict):
                    root_id = root_meta.get("page_id")
                    if root_id:
                        previous_page_meta_by_id[str(root_id)] = root_meta
                raw_children = loaded.get("child_pages")
                if isinstance(raw_children, list):
                    for child in raw_children:
                        if not isinstance(child, dict):
                            continue
                        child_id = child.get("page_id")
                        if child_id:
                            previous_page_meta_by_id[str(child_id)] = child
                raw_attachments = loaded.get("attachments")
                if isinstance(raw_attachments, list):
                    for attachment in raw_attachments:
                        if not isinstance(attachment, dict):
                            continue
                        page_id = attachment.get("page_id")
                        if page_id is None:
                            continue
                        previous_attachments_by_page.setdefault(str(page_id), []).append(attachment)
        except Exception:
            previous_page_meta_by_id = {}
            previous_attachments_by_page = {}

    previous_corpus_chunks_by_page: dict[str, list[dict[str, Any]]] = {}
    if options.resume and options.emit_corpus:
        previous_corpus_path = output_dir / "corpus.jsonl"
        if previous_corpus_path.exists():
            try:
                with previous_corpus_path.open("r", encoding="utf-8") as previous_corpus_fp:
                    for raw_line in previous_corpus_fp:
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(payload, dict):
                            continue
                        page_id = str(payload.get("page_id") or "").strip()
                        if not page_id:
                            continue
                        previous_corpus_chunks_by_page.setdefault(page_id, []).append(payload)
            except Exception:
                previous_corpus_chunks_by_page = {}

    # State file for resume support (TSK-188)
    state_path = output_dir / "crawl_state.json"
    crawl_state: CrawlState | None = None
    skipped_unchanged: int = 0
    skipped_already_visited: int = 0
    nodes_processed: int = 0
    pages_fetched: int = 0
    pages_failed: int = 0
    termination_reason = "queue_exhausted"
    unchanged_page_ids: set[str] = set()

    # Track previously visited pages for skip-unchanged logic (separate from current run)
    previous_visited: dict[str, dict[str, Any]] = {}

    if options.resume:
        crawl_state = _load_crawl_state(state_path)
        if crawl_state is not None:
            # Validate state matches current crawl parameters
            if crawl_state.root_page_id != resolved_root_id:
                # Root changed, start fresh
                crawl_state = None
            elif crawl_state.body_format != body_format:
                # Format changed, start fresh
                crawl_state = None
            elif crawl_state.completed:
                # Previous crawl completed - keep visited_pages for skip-unchanged checks
                # but reset queue to re-crawl from root
                previous_visited = dict(crawl_state.visited_pages)
                previous_sync_timestamp = crawl_state.last_sync_timestamp
                previous_full_reconciliation_timestamp = crawl_state.last_full_reconciliation_timestamp
                crawl_state = CrawlState(
                    root_page_id=resolved_root_id,
                    body_format=body_format,
                    visited_pages=previous_visited,  # Keep for version checks
                    pending_queue=[(resolved_root_id, None, 0)],
                    started_at=_now_iso(),
                    last_updated_at=_now_iso(),
                    completed=False,
                    last_sync_timestamp=previous_sync_timestamp,
                    last_full_reconciliation_timestamp=previous_full_reconciliation_timestamp,
                )
            else:
                # Incomplete crawl - restore visited pages for skip logic
                previous_visited = dict(crawl_state.visited_pages)

    # Initialize state if needed
    if crawl_state is None:
        crawl_state = CrawlState(
            root_page_id=resolved_root_id,
            body_format=body_format,
            visited_pages={},
            pending_queue=[(resolved_root_id, None, 0)],
            started_at=_now_iso(),
            last_updated_at=_now_iso(),
            completed=False,
        )

    # For resume mode, track pages visited in current session to avoid re-processing
    visited_pages: set[str] = set()
    downloaded_attachments: set[str] = set()

    queue: list[tuple[str, str | None, int]] = list(crawl_state.pending_queue)
    discovered_page_ids: set[str] = {resolved_root_id}
    for queued_page_id, _, _ in queue:
        discovered_page_ids.add(queued_page_id)

    root_meta: dict[str, Any] | None = None
    child_pages: list[dict[str, Any]] = []
    attachments: list[dict[str, Any]] = []
    link_edges: list[dict[str, Any]] = []
    corpus_chunks: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    mentions: list[dict[str, Any]] = []
    telemetry_getter = getattr(http, "get_runtime_telemetry", None)
    configure_rate_limit_budget = getattr(http, "configure_rate_limit_budget", None)
    if callable(configure_rate_limit_budget):
        with contextlib.suppress(Exception):
            configure_rate_limit_budget(int(options.rate_limit_budget))

    def _children_for(page_id: str, depth: int) -> list[tuple[str, str | None, int]]:
        if options.max_depth >= 0 and depth >= options.max_depth:
            return []
        try:
            child_payload = http.get_child_pages(page_id)
        except Exception:
            return []
        collected: list[tuple[str, str | None, int]] = []
        for child in child_payload:
            if not isinstance(child, dict):
                continue
            child_id = child.get("id")
            if child_id is None:
                continue
            collected.append((str(child_id), page_id, depth + 1))
        return collected

    body_expands: list[str]
    if body_format == "export_view":
        body_expands = ["body.export_view", "body.view", "body.storage"]
    elif body_format == "storage":
        body_expands = ["body.storage", "body.view"]
    else:
        body_expands = ["body.view", "body.storage"]

    def _fetch_page(node: tuple[str, str | None, int]) -> _FetchedPage:
        page_id, parent_id, depth = node
        children: list[tuple[str, str | None, int]] = []
        children_future: Future[list[tuple[str, str | None, int]]] | None = None
        children_executor: ThreadPoolExecutor | None = None
        if not use_structure_first and (options.max_depth < 0 or depth < options.max_depth):
            children_executor = ThreadPoolExecutor(max_workers=1)
            children_future = children_executor.submit(_children_for, page_id, depth)

        try:
            if options.resume and page_id in crawl_state.visited_pages:
                try:
                    version_check = http.get_page(page_id, expand=["version"])
                except Exception as exc:
                    if children_future is not None:
                        children = children_future.result()
                    return _FetchedPage(
                        page_id=page_id,
                        parent_id=parent_id,
                        depth=depth,
                        status="error",
                        error=str(exc),
                        children=children,
                    )
                check_version = (version_check.get("version") or {}).get("number")
                if crawl_state.is_page_unchanged(page_id, check_version, None):
                    if children_future is not None:
                        children = children_future.result()
                    return _FetchedPage(
                        page_id=page_id,
                        parent_id=parent_id,
                        depth=depth,
                        status="unchanged",
                        version_payload=version_check,
                        children=children,
                    )

            try:
                page_payload = http.get_page(page_id, expand=[*body_expands, "version", "space", "ancestors"])
            except Exception as exc:
                if children_future is not None:
                    children = children_future.result()
                return _FetchedPage(
                    page_id=page_id,
                    parent_id=parent_id,
                    depth=depth,
                    status="error",
                    error=str(exc),
                    children=children,
                )

            if children_future is not None:
                children = children_future.result()

            return _FetchedPage(
                page_id=page_id,
                parent_id=parent_id,
                depth=depth,
                status="fetched",
                page_payload=page_payload,
                children=children,
            )
        finally:
            if children_executor is not None:
                children_executor.shutdown(wait=True)

    def _extract_page_id_from_search_item(item: Any) -> str | None:
        if not isinstance(item, dict):
            return None
        raw_id = item.get("id")
        if raw_id is None and isinstance(item.get("content"), dict):
            raw_id = item["content"].get("id")
        if raw_id is None:
            return None
        page_id = str(raw_id).strip()
        return page_id if page_id.isdigit() else None

    search_by_space_and_type = getattr(http, "search_by_space_and_type", None)

    def _search_space_page_ids(
        *,
        space_key: str,
        last_modified_after: datetime | None = None,
        overlap_minutes: int = 0,
    ) -> tuple[set[str], bool]:
        if not callable(search_by_space_and_type):
            return set(), False

        page_ids: set[str] = set()
        start = 0
        limit = 100
        successful = False
        max_pages = 500

        for _ in range(max_pages):
            response = search_by_space_and_type(
                space_key=space_key,
                content_type="page",
                limit=limit,
                start=start,
                expand=["version"],
                last_modified_after=last_modified_after,
                overlap_minutes=overlap_minutes,
            )
            if not isinstance(response, dict):
                break
            successful = True
            results = response.get("results")
            if not isinstance(results, list) or not results:
                break
            for item in results:
                page_id = _extract_page_id_from_search_item(item)
                if page_id:
                    page_ids.add(page_id)
            if len(results) < limit:
                break
            start += limit

        return page_ids, successful

    def _resolve_known_space_key() -> str | None:
        root_meta = previous_page_meta_by_id.get(resolved_root_id)
        if not isinstance(root_meta, dict):
            return None
        raw_space_key = root_meta.get("space_key")
        if not isinstance(raw_space_key, str):
            return None
        space_key = raw_space_key.strip()
        return space_key or None

    def _discover_structure_first_tree(
        initial_queue: list[tuple[str, str | None, int]],
    ) -> tuple[list[tuple[str, str | None, int]], list[tuple[str, str | None, int]], set[str]]:
        ordered: list[tuple[str, str | None, int]] = []
        pending: list[tuple[str, str | None, int]] = []
        discovered: set[str] = set()
        pending_ids: set[str] = set()
        seen: set[str] = set()
        current_level: list[tuple[str, str | None, int]] = list(initial_queue)
        for page_id, _, _ in current_level:
            discovered.add(page_id)

        while current_level:
            level_nodes: list[tuple[str, str | None, int]] = []
            for page_id, parent_id, depth in current_level:
                if page_id in seen:
                    continue
                if options.max_nodes is not None and len(ordered) >= options.max_nodes:
                    if page_id not in pending_ids:
                        pending.append((page_id, parent_id, depth))
                        pending_ids.add(page_id)
                    continue
                seen.add(page_id)
                ordered.append((page_id, parent_id, depth))
                level_nodes.append((page_id, parent_id, depth))

            if options.max_nodes is not None and len(ordered) >= options.max_nodes:
                for page_id, parent_id, depth in current_level:
                    if page_id in seen or page_id in pending_ids:
                        continue
                    pending.append((page_id, parent_id, depth))
                    pending_ids.add(page_id)
                break

            parents_for_children: list[tuple[str, int]] = []
            for page_id, _, depth in level_nodes:
                if options.max_depth >= 0 and depth >= options.max_depth:
                    continue
                parents_for_children.append((page_id, depth))

            if not parents_for_children:
                current_level = []
                continue

            child_batches: list[list[tuple[str, str | None, int]]]
            if len(parents_for_children) == 1:
                parent_id, parent_depth = parents_for_children[0]
                child_batches = [_children_for(parent_id, parent_depth)]
            else:
                max_workers = min(page_concurrency, len(parents_for_children))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures: list[Future[list[tuple[str, str | None, int]]]] = [
                        executor.submit(_children_for, parent_id, parent_depth)
                        for parent_id, parent_depth in parents_for_children
                    ]
                    child_batches = [future.result() for future in futures]

            next_level: list[tuple[str, str | None, int]] = []
            next_level_ids: set[str] = set()
            for children in child_batches:
                for child_id, child_parent, child_depth in children:
                    if child_id in seen or child_id in next_level_ids:
                        continue
                    discovered.add(child_id)
                    next_level_ids.add(child_id)
                    next_level.append((child_id, child_parent, child_depth))
            current_level = next_level

        return ordered, pending, discovered

    incremental_candidate_ids: set[str] = set()
    incremental_high_water_mark_ran = False
    incremental_high_water_mark_skipped = False
    incremental_high_water_mark_skip_reason: str | None = None
    incremental_known_page_count = 0
    full_reconciliation_deleted_ids: list[str] = []
    full_reconciliation_ran = False
    full_reconciliation_skipped = False
    full_reconciliation_skip_reason: str | None = None
    full_reconciliation_known_page_count = 0
    space_key_for_incremental = _resolve_known_space_key()
    if options.resume and options.incremental_cql and callable(search_by_space_and_type):
        known_page_ids = set(crawl_state.visited_pages.keys())
        incremental_known_page_count = len(known_page_ids)
        last_sync_dt = _parse_iso_timestamp(crawl_state.last_sync_timestamp)
        if space_key_for_incremental and last_sync_dt is not None:
            if incremental_known_page_count <= 1:
                incremental_high_water_mark_skipped = True
                incremental_high_water_mark_skip_reason = "known_pages_lte_1"
            else:
                incremental_high_water_mark_ran = True
                try:
                    incremental_ids, incremental_ok = _search_space_page_ids(
                        space_key=space_key_for_incremental,
                        last_modified_after=last_sync_dt,
                        overlap_minutes=max(0, int(options.incremental_overlap_minutes)),
                    )
                except Exception:
                    incremental_ids, incremental_ok = set(), False
                if incremental_ok:
                    incremental_candidate_ids = {page_id for page_id in incremental_ids if page_id in known_page_ids}
                    if incremental_candidate_ids:
                        queued_ids = {queued_page_id for queued_page_id, _, _ in queue}
                        for page_id in sorted(incremental_candidate_ids):
                            if page_id in queued_ids:
                                continue
                            previous_meta = previous_page_meta_by_id.get(page_id) or {}
                            parent_id = previous_meta.get("parent_id")
                            if parent_id is not None:
                                parent_id = str(parent_id)
                            depth = previous_meta.get("depth")
                            if not isinstance(depth, int) or depth < 0:
                                depth = 0
                            queue.append((page_id, parent_id, depth))
                            queued_ids.add(page_id)
                            discovered_page_ids.add(page_id)

        full_reconciliation_due = False
        last_full_reconciliation_dt = _parse_iso_timestamp(crawl_state.last_full_reconciliation_timestamp)
        if last_full_reconciliation_dt is None:
            full_reconciliation_due = True
        else:
            full_reconciliation_due = datetime.now(UTC) - last_full_reconciliation_dt >= timedelta(
                days=max(1, int(options.full_reconciliation_interval_days))
            )

        if space_key_for_incremental and full_reconciliation_due:
            known_page_ids = set(crawl_state.visited_pages.keys())
            full_reconciliation_known_page_count = len(known_page_ids)
            reconciliation_marker_timestamp = _now_iso()
            if full_reconciliation_known_page_count <= 1:
                full_reconciliation_skipped = True
                full_reconciliation_skip_reason = "known_pages_lte_1"
                crawl_state.last_full_reconciliation_timestamp = reconciliation_marker_timestamp
            else:
                try:
                    remote_page_ids, reconciliation_ok = _search_space_page_ids(space_key=space_key_for_incremental)
                except Exception:
                    remote_page_ids, reconciliation_ok = set(), False
                if reconciliation_ok:
                    full_reconciliation_ran = True
                    full_reconciliation_deleted_ids = sorted(known_page_ids - remote_page_ids)
                    if full_reconciliation_deleted_ids:
                        for page_id in full_reconciliation_deleted_ids:
                            crawl_state.visited_pages.pop(page_id, None)
                            previous_visited.pop(page_id, None)
                            previous_page_meta_by_id.pop(page_id, None)
                            previous_attachments_by_page.pop(page_id, None)
                            discovered_page_ids.discard(page_id)
                        _emit_runtime_event(
                            options,
                            "pages_deleted",
                            root_page_id=resolved_root_id,
                            deleted_count=len(full_reconciliation_deleted_ids),
                            page_ids=full_reconciliation_deleted_ids,
                        )
                    crawl_state.last_full_reconciliation_timestamp = reconciliation_marker_timestamp

    structure_first_pending_queue: list[tuple[str, str | None, int]] = []
    structure_pre_discovered_nodes = 0
    if use_structure_first:
        queue, structure_first_pending_queue, structure_discovered_ids = _discover_structure_first_tree(queue)
        structure_pre_discovered_nodes = len(queue) + len(structure_first_pending_queue)
        discovered_page_ids.update(structure_discovered_ids)

    crawl_started_at = time.perf_counter()
    max_inflight_workers = 0
    effective_page_concurrency = page_concurrency
    effective_concurrency_signal: float | None = None
    throttle_pressure_score: float | None = None

    while queue:
        if options.max_nodes is not None and nodes_processed >= options.max_nodes:
            termination_reason = "max_nodes_reached"
            break

        if options.max_nodes is None:
            remaining = len(queue)
        else:
            remaining = min(len(queue), options.max_nodes - nodes_processed)
            if remaining <= 0:
                termination_reason = "max_nodes_reached"
                break
        runtime_page_concurrency = page_concurrency
        if callable(telemetry_getter):
            try:
                telemetry_snapshot = telemetry_getter()
            except Exception:
                telemetry_snapshot = None
            if isinstance(telemetry_snapshot, dict):
                throttle = telemetry_snapshot.get("adaptive_throttle")
                if isinstance(throttle, dict):
                    signal = throttle.get("effective_concurrency_signal")
                    if isinstance(signal, (float, int)):
                        effective_concurrency_signal = float(signal)
                        scaled = round(page_concurrency * float(signal))
                        runtime_page_concurrency = max(1, min(page_concurrency, scaled))
                    pressure_score = throttle.get("pressure_score")
                    if isinstance(pressure_score, (float, int)):
                        throttle_pressure_score = float(pressure_score)
        effective_page_concurrency = runtime_page_concurrency
        batch_size = min(runtime_page_concurrency, remaining)
        max_inflight_workers = max(max_inflight_workers, batch_size)

        batch: list[tuple[str, str | None, int]] = []
        while queue and len(batch) < batch_size:
            page_id, parent_id, depth = queue.pop(0)
            if page_id in visited_pages:
                skipped_already_visited += 1
                continue
            visited_pages.add(page_id)
            nodes_processed += 1
            batch.append((page_id, parent_id, depth))

        crawl_state.pending_queue = list(queue)
        if not batch:
            continue

        fetched: list[_FetchedPage] = []
        if batch_size == 1:
            fetched = [_fetch_page(node) for node in batch]
        else:
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures: dict[Future[_FetchedPage], int] = {
                    executor.submit(_fetch_page, node): idx for idx, node in enumerate(batch)
                }
                fetched_by_index: dict[int, _FetchedPage] = {}
                for future, idx in futures.items():
                    fetched_by_index[idx] = future.result()
                fetched = [fetched_by_index[idx] for idx in range(len(batch))]

        for result in fetched:
            page_id = result.page_id
            parent_id = result.parent_id
            depth = result.depth

            if result.status == "unchanged":
                skipped_unchanged += 1
                unchanged_page_ids.add(page_id)
                previous_meta = previous_page_meta_by_id.get(page_id)
                if previous_meta is None:
                    previous_meta = _meta_from_existing_html(
                        page_id=page_id,
                        parent_id=parent_id,
                        depth=depth,
                        page_payload=result.version_payload if isinstance(result.version_payload, dict) else None,
                    )
                if previous_meta is not None:
                    if depth == 0:
                        root_meta = previous_meta
                    else:
                        child_pages.append(previous_meta)
                    if options.include_attachments:
                        for previous_attachment in previous_attachments_by_page.get(page_id, []):
                            attachment_id = previous_attachment.get("attachment_id")
                            if attachment_id is not None:
                                downloaded_attachments.add(str(attachment_id))
                            attachments.append(previous_attachment)
                for child_id, child_parent, child_depth in result.children:
                    if child_id in visited_pages:
                        continue
                    discovered_page_ids.add(child_id)
                    queue.append((child_id, child_parent, child_depth))
                continue

            if result.status == "error":
                pages_failed += 1
                meta = {
                    "page_id": page_id,
                    "title": None,
                    "page_url": None,
                    "parent_id": parent_id,
                    "depth": depth,
                    "status": "error",
                    "error": result.error,
                }
                if depth == 0:
                    root_meta = meta
                else:
                    child_pages.append(meta)
                continue

            pages_fetched += 1
            page = result.page_payload if isinstance(result.page_payload, dict) else {}
            title = str(page.get("title") or "untitled")
            safe_title = _safe_filename(title)
            body_obj = page.get("body") or {}
            view_html = (body_obj.get("view") or {}).get("value", "")
            export_html = (body_obj.get("export_view") or {}).get("value", "")
            storage_html = (body_obj.get("storage") or {}).get("value", "")
            candidates = {
                "view": view_html if isinstance(view_html, str) else "",
                "export_view": export_html if isinstance(export_html, str) else "",
                "storage": storage_html if isinstance(storage_html, str) else "",
            }
            chosen_html = candidates.get(body_format, "") or ""
            chosen_format = body_format
            if not chosen_html.strip():
                fallback_order = (
                    ["view", "storage", "export_view"]
                    if body_format == "view"
                    else ["storage", "view", "export_view"]
                    if body_format == "storage"
                    else ["export_view", "view", "storage"]
                )
                for fmt in fallback_order:
                    candidate = candidates.get(fmt, "") or ""
                    if isinstance(candidate, str) and candidate.strip():
                        chosen_html = candidate
                        chosen_format = fmt
                        break

            html = chosen_html if isinstance(chosen_html, str) else ""
            source_format = f"html-{chosen_format.replace('_', '-')}"

            links = page.get("_links", {}) if isinstance(page.get("_links"), dict) else {}
            base_url = str(links.get("base") or "")
            web_ui = str(links.get("webui") or "")
            page_url = f"{base_url}{web_ui}" if base_url and web_ui else None

            version = page.get("version") or {}
            page_version = version.get("number") if isinstance(version, dict) else None
            page_updated = version.get("when") if isinstance(version, dict) else None
            space_key = (page.get("space") or {}).get("key") if isinstance(page.get("space"), dict) else None

            ancestors = page.get("ancestors") or []
            ancestor_ids: list[str] = []
            ancestor_titles: list[str] = []
            if isinstance(ancestors, list):
                for entry in ancestors:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("id") is not None:
                        ancestor_ids.append(str(entry["id"]))
                    if entry.get("title"):
                        ancestor_titles.append(str(entry["title"]))

            html_path = output_dir / f"{page_id}_{safe_title}.html"
            html_path.write_text(html, encoding="utf-8")
            html_bytes = html.encode("utf-8")
            html_sha256 = _sha256_bytes(html_bytes)
            crawl_state.record_page(page_id, page_version, html_sha256)

            meta = {
                "page_id": page_id,
                "title": title,
                "page_url": page_url,
                "parent_id": parent_id,
                "depth": depth,
                "status": "downloaded",
                "html_path": str(html_path),
                "html_sha256": html_sha256,
                "html_size_bytes": html_path.stat().st_size,
                "source_format": source_format,
                "space_key": space_key,
                "page_version": page_version,
                "page_updated": page_updated,
                "ancestor_ids": ancestor_ids,
                "ancestor_titles": ancestor_titles,
                "error": None,
            }
            if depth == 0:
                root_meta = meta
            else:
                child_pages.append(meta)

            if options.emit_link_graph:
                for link in _extract_links(html, base_url=base_url):
                    target_url = link.get("url")
                    target_type = _classify_target_type(str(target_url)) if target_url else None
                    target_page_id = _extract_target_page_id(str(target_url)) if target_url else None
                    edge: dict[str, Any] = {
                        "source_page_id": page_id,
                        "source_page_url": page_url,
                        "target_url": target_url,
                        "anchor_text": link.get("text"),
                    }
                    if target_type:
                        edge["target_type"] = target_type
                    if target_type == "confluence_page" and target_page_id:
                        edge["target_page_id"] = target_page_id
                    link_edges.append(edge)

            if options.emit_corpus:
                for chunk in _chunk_html_by_headings(html, max_chars=chunk_max_chars):
                    heading_path = chunk.get("heading_path") or []
                    ordinal = chunk.get("ordinal") if isinstance(chunk.get("ordinal"), int) else 0
                    base_key = f"{page_id}|{'/'.join(heading_path)}"
                    key = base_key if ordinal == 0 else f"{base_key}|{ordinal}"
                    corpus_chunks.append(
                        {
                            "chunk_id": _sha256_text(key)[:16],
                            "page_id": page_id,
                            "page_url": page_url,
                            "title": title,
                            "depth": depth,
                            "parent_id": parent_id,
                            "ancestors": ancestor_ids,
                            "ancestor_ids": ancestor_ids,
                            "space_key": space_key,
                            "page_version": page_version,
                            "page_updated": page_updated,
                            "ancestor_titles": ancestor_titles,
                            "heading_path": heading_path,
                            "chunk_ordinal": ordinal,
                            "text": chunk.get("text"),
                            "source_type": "confluence",
                            "doc_class": "canonical_doc",
                            "generated_flag": False,
                            "historical_flag": False,
                            "discovery": "confluence_crawl_page",
                        }
                    )

            if options.emit_tables:
                for table in _extract_tables(html):
                    key = f"{page_id}|table|{table.get('table_index')}"
                    tables.append(
                        {
                            "table_id": _sha256_text(key)[:16],
                            "page_id": page_id,
                            "page_url": page_url,
                            "title": title,
                            "depth": depth,
                            "parent_id": parent_id,
                            "space_key": space_key,
                            "page_version": page_version,
                            "page_updated": page_updated,
                            "ancestor_titles": ancestor_titles,
                            "table_index": table.get("table_index"),
                            "headers": table.get("headers"),
                            "rows": table.get("rows"),
                            "row_count": table.get("row_count"),
                            "col_count": table.get("col_count"),
                        }
                    )

            if options.emit_mentions:
                for index, mention in enumerate(_extract_mentions(html, base_url=base_url)):
                    key = f"{page_id}|mention|{mention.get('type')}|{mention.get('value')}|{mention.get('url') or ''}"
                    mentions.append(
                        {
                            "mention_id": _sha256_text(key)[:16],
                            "page_id": page_id,
                            "page_url": page_url,
                            "title": title,
                            "depth": depth,
                            "parent_id": parent_id,
                            "space_key": space_key,
                            "page_version": page_version,
                            "page_updated": page_updated,
                            "ancestor_titles": ancestor_titles,
                            "mention_index": index,
                            **mention,
                        }
                    )

            if options.include_attachments:
                try:
                    attachment_results = http.get_attachments(page_id)
                except Exception as exc:
                    attachments.append(
                        {
                            "attachment_id": None,
                            "page_id": page_id,
                            "title": None,
                            "status": "error",
                            "error": str(exc),
                        }
                    )
                    attachment_results = []

                for att in attachment_results:
                    if not isinstance(att, dict):
                        continue
                    attachment_id = att.get("id") or att.get("attachment_id")
                    if attachment_id is None:
                        continue
                    attachment_id = str(attachment_id)
                    if attachment_id in downloaded_attachments:
                        continue
                    downloaded_attachments.add(attachment_id)

                    att_title = str(att.get("title") or att.get("name") or f"attachment_{attachment_id}")
                    out_path = attachments_dir / _safe_attachment_filename(
                        attachment_id, att_title, fallback_suffix=_guess_attachment_suffix(att)
                    )

                    try:
                        content = http.get_attachment_content(attachment_id)
                        out_path.write_bytes(content)
                        file_sha256 = _sha256_bytes(content)
                        status = "downloaded"
                        error = None
                    except Exception as exc:
                        file_sha256 = None
                        status = "error"
                        error = str(exc)

                    version_obj = att.get("version") or {}
                    attachment_version = version_obj.get("number") if isinstance(version_obj, dict) else None
                    extensions = att.get("extensions") or {}
                    attachment_size = None
                    if isinstance(extensions, dict):
                        attachment_size = extensions.get("fileSize") or extensions.get("size")

                    attachments.append(
                        {
                            "attachment_id": attachment_id,
                            "page_id": page_id,
                            "title": att_title,
                            "status": status,
                            "file_path": str(out_path) if status == "downloaded" else None,
                            "file_sha256": file_sha256,
                            "file_size_bytes": out_path.stat().st_size
                            if status == "downloaded" and out_path.exists()
                            else None,
                            "attachment_version": attachment_version,
                            "attachment_size": attachment_size,
                            "error": error,
                        }
                    )

            for child_id, child_parent, child_depth in result.children:
                if child_id in visited_pages:
                    continue
                discovered_page_ids.add(child_id)
                queue.append((child_id, child_parent, child_depth))

        _emit_runtime_event(
            options,
            "crawl_progress",
            root_page_id=resolved_root_id,
            pages_discovered=len(discovered_page_ids),
            pages_fetched=pages_fetched,
            pages_failed=pages_failed,
            pages_skipped_unchanged=skipped_unchanged,
            pages_skipped_total=skipped_unchanged + skipped_already_visited,
            pending_queue_size=len(queue),
            effective_page_concurrency=effective_page_concurrency,
            effective_concurrency_signal=effective_concurrency_signal,
            throttle_pressure_score=throttle_pressure_score,
        )

    if options.emit_corpus and previous_corpus_chunks_by_page:
        should_merge_unchanged_corpus = pages_fetched > 0 or bool(full_reconciliation_deleted_ids)
        if should_merge_unchanged_corpus:
            emitted_chunk_ids = {
                str(chunk.get("chunk_id") or "").strip()
                for chunk in corpus_chunks
                if isinstance(chunk, dict) and str(chunk.get("chunk_id") or "").strip()
            }
            for page_id in sorted(unchanged_page_ids):
                for previous_chunk in previous_corpus_chunks_by_page.get(page_id, []):
                    if not isinstance(previous_chunk, dict):
                        continue
                    chunk_id = str(previous_chunk.get("chunk_id") or "").strip()
                    if chunk_id and chunk_id in emitted_chunk_ids:
                        continue
                    corpus_chunks.append(dict(previous_chunk))
                    if chunk_id:
                        emitted_chunk_ids.add(chunk_id)

    if structure_first_pending_queue:
        queued_page_ids = {queued_page_id for queued_page_id, _, _ in queue}
        for pending_page_id, pending_parent_id, pending_depth in structure_first_pending_queue:
            if pending_page_id in visited_pages or pending_page_id in queued_page_ids:
                continue
            queue.append((pending_page_id, pending_parent_id, pending_depth))
            queued_page_ids.add(pending_page_id)
        if queue:
            termination_reason = "max_nodes_reached"

    # Update and save crawl state (TSK-188)
    http_telemetry: dict[str, Any] | None = None
    if callable(telemetry_getter):
        try:
            telemetry_payload = telemetry_getter()
            if isinstance(telemetry_payload, dict):
                http_telemetry = telemetry_payload
        except Exception:
            http_telemetry = None
    if http_telemetry is None:
        http_telemetry = {}

    elapsed_seconds = max(0.001, time.perf_counter() - crawl_started_at)
    throughput_pages_per_second = round(nodes_processed / elapsed_seconds, 3)
    latency_metrics = http_telemetry.get("latency_ms") if isinstance(http_telemetry, dict) else None
    p95_page_latency_ms = None
    if isinstance(latency_metrics, dict):
        operation_latency = latency_metrics.get("operation")
        if isinstance(operation_latency, dict):
            p95_value = operation_latency.get("p95")
            if isinstance(p95_value, (float, int)):
                p95_page_latency_ms = round(float(p95_value), 3)

    retry_events_total = None
    if isinstance(http_telemetry, dict):
        retry_events_list = http_telemetry.get("recent_retry_events")
        if isinstance(retry_events_list, list):
            retry_events_total = len(retry_events_list)

    if isinstance(http_telemetry, dict):
        http_telemetry["inflight_workers"] = max_inflight_workers
        http_telemetry["queue_depth"] = len(queue)
        http_telemetry["pages_per_second"] = throughput_pages_per_second
        http_telemetry["retry_events"] = retry_events_total
        http_telemetry["p95_page_latency_ms"] = p95_page_latency_ms
        adaptive_throttle = http_telemetry.get("adaptive_throttle")
        if isinstance(adaptive_throttle, dict):
            signal_value = adaptive_throttle.get("effective_concurrency_signal")
            if isinstance(signal_value, (float, int)):
                effective_concurrency_signal = float(signal_value)
            pressure_value = adaptive_throttle.get("pressure_score")
            if isinstance(pressure_value, (float, int)):
                throttle_pressure_score = float(pressure_value)

    crawl_state.last_sync_timestamp = _now_iso()
    pages_skipped = skipped_unchanged + skipped_already_visited
    progress_event = {
        "pages_discovered": len(discovered_page_ids),
        "pages_fetched": pages_fetched,
        "pages_failed": pages_failed,
        "pages_skipped": pages_skipped,
        "pages_skipped_unchanged": skipped_unchanged,
        "throttle": {
            "configured_page_concurrency": page_concurrency,
            "effective_page_concurrency": effective_page_concurrency,
            "effective_concurrency_signal": effective_concurrency_signal,
            "pressure_score": throttle_pressure_score,
        },
    }

    crawl_state.pending_queue = list(queue)
    crawl_state.completed = len(queue) == 0
    if crawl_state.completed:
        termination_reason = "queue_exhausted"
    crawl_state.run_diagnostics = {
        "termination_reason": termination_reason,
        "nodes_processed": nodes_processed,
        "skipped_unchanged": skipped_unchanged,
        "skipped_already_visited": skipped_already_visited,
        "pages_fetched": pages_fetched,
        "pages_failed": pages_failed,
        "pages_discovered": len(discovered_page_ids),
        "pages_skipped": pages_skipped,
        "pending_queue_size": len(queue),
        "page_concurrency": page_concurrency,
        "staged_mode": staged_mode,
        "incremental_cql": bool(options.incremental_cql),
        "rate_limit_budget": int(options.rate_limit_budget),
        "full_reconciliation_interval_days": max(1, int(options.full_reconciliation_interval_days)),
        "last_sync_timestamp": crawl_state.last_sync_timestamp,
        "last_full_reconciliation_timestamp": crawl_state.last_full_reconciliation_timestamp,
        "incremental_overlap_minutes": max(0, int(options.incremental_overlap_minutes)),
        "incremental_known_page_count": incremental_known_page_count,
        "incremental_candidate_count": len(incremental_candidate_ids),
        "incremental_high_water_mark_ran": incremental_high_water_mark_ran,
        "incremental_high_water_mark_skipped": incremental_high_water_mark_skipped,
        "incremental_high_water_mark_skip_reason": incremental_high_water_mark_skip_reason,
        "full_reconciliation_ran": full_reconciliation_ran,
        "full_reconciliation_deleted_ids": full_reconciliation_deleted_ids,
        "full_reconciliation_skipped": full_reconciliation_skipped,
        "full_reconciliation_skip_reason": full_reconciliation_skip_reason,
        "full_reconciliation_known_page_count": full_reconciliation_known_page_count,
        "structure_pre_discovered_nodes": structure_pre_discovered_nodes if use_structure_first else None,
        "progress_event": progress_event,
        "telemetry": http_telemetry,
        "http_telemetry": http_telemetry,
    }
    _save_crawl_state(crawl_state, state_path)

    payload: dict[str, Any] = {
        "root_ref": root_ref,
        "root_page_id": resolved_root_id,
        "out_dir": str(output_dir),
        "generated_at": _now_iso(),
        "body_format": body_format,
        "chunk_max_chars": chunk_max_chars,
        "crawl_mode": {
            "page_concurrency": page_concurrency,
            "staged_mode": staged_mode,
            "incremental_cql": bool(options.incremental_cql),
            "rate_limit_budget": int(options.rate_limit_budget),
            "incremental_overlap_minutes": max(0, int(options.incremental_overlap_minutes)),
            "full_reconciliation_interval_days": max(1, int(options.full_reconciliation_interval_days)),
        },
        "page": root_meta,
        "child_pages": child_pages,
        "attachments": attachments,
        "corpus_path": None,
        "link_graph_path": None,
        "tables_path": None,
        "mentions_path": None,
        "progress_event": progress_event,
        "resume_state": {
            "skipped_unchanged": skipped_unchanged,
            "skipped_already_visited": skipped_already_visited,
            "pages_fetched": pages_fetched,
            "pages_failed": pages_failed,
            "pages_discovered": len(discovered_page_ids),
            "pages_skipped": pages_skipped,
            "pages_skipped_unchanged": skipped_unchanged,
            "nodes_processed": nodes_processed,
            "completed": crawl_state.completed,
            "termination_reason": termination_reason,
            "pending_queue_size": len(queue),
            "state_path": str(state_path),
            "page_concurrency": page_concurrency,
            "staged_mode": staged_mode,
            "last_sync_timestamp": crawl_state.last_sync_timestamp,
            "last_full_reconciliation_timestamp": crawl_state.last_full_reconciliation_timestamp,
        },
        "telemetry": http_telemetry,
        "http_telemetry": http_telemetry,
    }

    if options.emit_corpus:
        corpus_path = output_dir / "corpus.jsonl"
        if corpus_chunks or not (options.resume and corpus_path.exists()):
            with corpus_path.open("w", encoding="utf-8") as fp:
                for item in corpus_chunks:
                    fp.write(json.dumps(item, ensure_ascii=False) + "\n")
        payload["corpus_path"] = str(corpus_path)

    if options.emit_link_graph:
        graph_path = output_dir / "link-graph.json"
        if link_edges or not (options.resume and graph_path.exists()):
            graph_payload = {
                "generated_at": payload["generated_at"],
                "root_page_id": resolved_root_id,
                "edges": [edge for edge in link_edges if edge.get("target_url")],
            }
            graph_path.write_text(json.dumps(graph_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["link_graph_path"] = str(graph_path)

    if options.emit_tables:
        tables_path = output_dir / "tables.jsonl"
        if tables or not (options.resume and tables_path.exists()):
            with tables_path.open("w", encoding="utf-8") as fp:
                for item in tables:
                    fp.write(json.dumps(item, ensure_ascii=False) + "\n")
        payload["tables_path"] = str(tables_path)

    if options.emit_mentions:
        mentions_path = output_dir / "mentions.jsonl"
        if mentions or not (options.resume and mentions_path.exists()):
            with mentions_path.open("w", encoding="utf-8") as fp:
                for item in mentions:
                    fp.write(json.dumps(item, ensure_ascii=False) + "\n")
        payload["mentions_path"] = str(mentions_path)

    resolved_manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["manifest_path"] = str(resolved_manifest_path)

    # Create bundle zip if requested (TSK-189)
    if options.bundle:
        bundle_path = _create_bundle_zip(output_dir, resolved_root_id, resolved_manifest_path)
        payload["bundle_path"] = str(bundle_path)

    return payload
