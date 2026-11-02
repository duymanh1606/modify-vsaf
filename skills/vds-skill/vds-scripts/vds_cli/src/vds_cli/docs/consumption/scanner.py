"""Scan Claude session JSONL files to discover doc consumption events."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_ALLOWED_TOOLS = frozenset({"Read", "Grep", "Glob"})
_DIATAXIS_RE = re.compile(r"<!--\s*di[\u00e1\u00e0]taxis:\s*([\w-]+)\s*-->", re.IGNORECASE)


@dataclass(frozen=True)
class DocRead:
    path: Path
    session_id: str
    read_at: datetime
    diataxis: str | None


def _slugify(text: str) -> str:
    """Simple slug: lowercase, non-alnum -> hyphen, strip edges."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "unknown"


def _redact_home(path: Path) -> Path:
    """Replace leading $HOME with ~ in a Path."""
    try:
        home = Path.home().resolve()
        resolved = path.resolve()
        if resolved == home or home in resolved.parents:
            rel = resolved.relative_to(home)
            return Path("~") / rel
    except (RuntimeError, ValueError, OSError):
        pass
    return path


def _extract_diataxis(file_path: Path) -> str | None:
    """Read first 2 KiB of a markdown file and extract diátaxis quadrant."""
    if file_path.suffix.lower() != ".md":
        return None
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        m = _DIATAXIS_RE.search(text)
        if m:
            return m.group(1).lower()
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _session_jsonl_paths(cwd: Path) -> list[Path]:
    """Discover session JSONL files under ~/.claude/projects/<slugified-cwd>."""
    try:
        home = Path.home()
    except RuntimeError:
        return []

    slug = _slugify(cwd.name)
    projects_dir = home / ".claude" / "projects" / slug
    if not projects_dir.exists():
        return []

    paths: list[Path] = []
    for entry in projects_dir.iterdir():
        if entry.is_file() and entry.suffix == ".jsonl" and not entry.name.startswith("."):
            paths.append(entry)
        elif entry.is_dir() and entry.name == "subagents":
            for sub in entry.iterdir():
                if sub.is_file() and sub.suffix == ".jsonl" and sub.name.startswith("agent-"):
                    paths.append(sub)
    return sorted(paths)


def _parse_iso_timestamp(value: str | None) -> datetime:
    """Parse an ISO-8601-ish string; fallback to now(UTC)."""
    if not value:
        return datetime.now(UTC)
    try:
        # Python 3.11+ fromisoformat handles 'Z' suffix; for safety strip it.
        value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return datetime.now(UTC)


def _extract_file_paths(event: dict) -> list[str]:
    """Yield file_path strings from a single JSONL event."""
    if not isinstance(event, dict):
        return []

    if event.get("type") != "assistant":
        return []

    message = event.get("message") or {}
    content_blocks = message.get("content") or []
    if not isinstance(content_blocks, list):
        return []

    paths: list[str] = []
    for block in content_blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_use":
            continue
        if block.get("name") not in _ALLOWED_TOOLS:
            continue
        tool_input = block.get("input") or {}
        # Tolerate scalar file_path or list file_path(s)
        raw = tool_input.get("file_path")
        if isinstance(raw, str):
            paths.append(raw)
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    paths.append(item)
    return paths


def scan_consumption(
    repo_root: Path,
    *,
    cwd: Path | None = None,
    session_dir: Path | None = None,
) -> list[DocRead]:
    """Scan Claude JSONL sessions and return deduplicated DocRead events.

    Parameters
    ----------
    repo_root:
        Root of the repository; used to resolve relative paths.
    cwd:
        Current working directory name used to build the default session path.
        Defaults to ``Path.cwd()``.
    session_dir:
        Optional explicit directory containing ``*.jsonl`` files. When provided,
        *cwd* is ignored for discovery.
    """
    repo_root = repo_root.resolve()
    if session_dir is not None:
        if session_dir.exists() and session_dir.is_dir():
            jsonl_files = sorted(p for p in session_dir.iterdir() if p.is_file() and p.suffix == ".jsonl")
        else:
            jsonl_files = []
    else:
        if cwd is None:
            cwd = Path.cwd()
        jsonl_files = _session_jsonl_paths(cwd)

    seen: set[tuple[str, str]] = set()
    reads: list[DocRead] = []

    for jsonl_path in jsonl_files:
        session_id = jsonl_path.stem
        try:
            with jsonl_path.open("r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug("Skipping malformed JSON line in %s", jsonl_path)
                        continue

                    file_paths = _extract_file_paths(event)
                    if not file_paths:
                        continue

                    ts = _parse_iso_timestamp(event.get("timestamp"))

                    for raw_path in file_paths:
                        # Resolve relative to repo_root if not absolute
                        p = Path(raw_path)
                        if not p.is_absolute():
                            p = repo_root / p
                        p = p.resolve()

                        # Redact HOME
                        p = _redact_home(p)

                        key = (str(p), session_id)
                        if key in seen:
                            continue
                        seen.add(key)

                        diataxis = _extract_diataxis(p) if p.is_absolute() else None

                        reads.append(
                            DocRead(
                                path=p,
                                session_id=session_id,
                                read_at=ts,
                                diataxis=diataxis,
                            )
                        )
        except (OSError, PermissionError):
            logger.debug("Cannot read session file %s", jsonl_path)
            continue

    return reads
