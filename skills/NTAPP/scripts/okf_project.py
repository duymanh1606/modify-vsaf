#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""okf_project.py — project-neutral OKF v0.2 projector for NTAPP artifacts.

Projects NTAPP artifacts into an OKF bundle (`<output_folder>/.okf/`): one
markdown file per node, relationships carried in frontmatter, so an agent can
navigate by field query instead of loading whole documents.

Design constraints this file is required to honour
---------------------------------------------------
Nothing project-specific lives in the script.  Directories, families and
adapters come from config, following the precedent set by
``scripts/reachability_check.py``.  The inverse also holds: defaults that are
*not* project-specific must live **here**, because ``scripts/*.py`` is the only
path that actually propagates to a project.  ``_bmad/bmm/config.yaml`` (Layer 1)
is seeded once by the project template and never updated again, so a new key
added there would never reach a running project.  Hence L0 below.

Standard library only.  PyYAML is *not* installed on the reference machines, so
this module ships a minimal YAML reader/writer covering the subset the config
and the node frontmatter actually use.  No shell, no symlinks, no cron
assumptions — the OKF layer runs on macOS, Linux and Windows alike (decision D3).

Two hashes, both over *normalised* text
---------------------------------------
``source_sha``  — the whole master file.  Cheap gate for the scan pass.
``content_sha`` — one section's own text.  Answers "is this node still right?"

Hashing raw bytes would make the same file produce two different digests on
Windows and macOS, and every node in the bundle would report stale on each
machine switch.  See ``normalise_text``.

One-way derivation
------------------
Masters are written and signed by people; nodes are derived.  Never the other
way round, and never a hand edit inside the bundle.  The single exception is
``--verify``, which appends to a node's ``verified[]`` — a person signs, the
machine writes.

Usage
-----
    python3 scripts/okf_project.py --dry-run
    python3 scripts/okf_project.py                     # incremental
    python3 scripts/okf_project.py --full
    python3 scripts/okf_project.py --audit
    python3 scripts/okf_project.py --verify design-section/BE-INV-09/04-...
    python3 scripts/okf_project.py --self-test
"""

from __future__ import annotations

import argparse
import fnmatch  # noqa: F401  (kept for parity with _seg_re fallback semantics)
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SPEC_VERSION = "0.2"
PRODUCER = "okf-projector"
PRODUCER_VERSION = "v1"

# ─────────────────────────────────────────────────────────────────────────────
# L0 — defaults that ship with the script.
#
# A project does NOT need to restate any of this.  Layer 1 may override, Layer 2
# declares `families`.  Both are optional except `families`, without which there
# is nothing to project.
# ─────────────────────────────────────────────────────────────────────────────

DEFAULTS = {
    # Follows the existing `output_folder` rather than restating "NTAPP-output".
    # Restating it would encode the same fact twice, and a project that moved
    # its output folder would silently point the bundle at nothing.
    "root": "{output_folder}/.okf",
    "spec_version": SPEC_VERSION,
    "actor_default": f"process:{PRODUCER}",
    "slug_max_len": 60,
    "log_max_lines": 500,
    "deprecate_grace_days": 30,
    "lock_ttl_seconds": 7200,
    "token_bytes_per_token": 3.5,
    # NEVER projected.  Cumulative across L0/L1/L2 — see merge_exclude().
    "exclude": [
        # The bundle is a sibling of Stage_1..Stage_5 inside the output folder.
        # Any family with a broad glob under the output folder would eat its own
        # nodes, and node files carry valid frontmatter so they look like real
        # sources.  This line must stay first.
        "**/.okf/**",
        "**/archive/**",
        "**/*_parts/**",
        "**/_parts/**",
        "**/.work/**",
        # Code-repo noise (P2).  node_modules does not exist in the FE repos
        # today, which is exactly why it is easy to forget: the first
        # `npm install` turns a ~2,500-file scan into hundreds of thousands.
        "**/node_modules/**",
        "**/.git/**",
        "**/target/**",
        "**/dist/**",
        "**/build/**",
        "**/.venv/**",
        "**/__pycache__/**",
    ],
    # Directories that must not be mistaken for a feature name when matching
    # `*/SLICE-*.md`.  `Bugs_Issues/assets/` already sits at exactly that depth.
    "reserved_dirs": ["archive", "assets", "reviews", "test", "_parts"],
    # Machine-written files inside the bundle.  Kept out of git so that two
    # consecutive runs over unchanged sources leave `git status` clean while the
    # node files themselves stay diffable — which is the whole reason for
    # putting trust metadata in frontmatter.
    "untracked_bundle_files": [".lock", "status.md", "log.md", "log/"],
}

# Per-type table of contents, written at the root of each type directory.
# It is NOT a node: it carries no frontmatter, resolves to no master document,
# and must never be counted, deprecated or swept.  Every place that walks the
# bundle for node files has to skip it by this exact name — a table of contents
# that got counted as content would inflate every total the graph reports.
TYPE_INDEX_NAME = "_index.md"

# Frontmatter keys the projector owns.  Everything else found in an existing
# node is human-authored and is preserved verbatim on reprojection.
MACHINE_KEYS = frozenset(
    {
        "type", "title", "description", "resource", "anchor", "anchor_text", "tags",
        "sources", "generated", "status", "deprecated_at",
        "okf_spec_version",
        "ntapp_unit", "ntapp_module", "ntapp_layer", "size_tokens", "epic",
        "code_repo", "dd_version", "dd_version_drift",
        "heading_level", "subsections", "source_note", "doc_version", "section_id",
        "source_sha", "content_sha",
        "governed_by", "implements", "built_as",
        "consumes", "used_by", "consumes_external", "used_by_external",
        "slice", "slice_key", "slice_title", "slice_ordinal", "slice_set",
        # P3
        "adr_number", "slice_type", "demo_status", "slice_units",
        "blocked_by", "enhanced_by",
        "bug_id", "bug_severity", "bug_state", "bug_surface",
        "bug_reporter", "bug_reported_at",
        "ui_id", "ui_kind", "ui_controls", "ui_states", "ui_drift_notes",
        "design_system", "figma_ref",
        # P5
        "lesson_section", "lesson_severity", "title_derived", "related_slices",
    }
)

# Emission order.  Groups mirror the frontmatter contract so a `git diff` reads
# the same way the spec does.
KEY_ORDER = [
    ("OKF core", ["type", "title", "description", "resource", "anchor", "anchor_text", "tags"]),
    ("v0.2 provenance", ["sources"]),
    ("v0.2 trust", ["generated", "verified", "status", "deprecated_at"]),
    (
        "NTAPP extension",
        [
            "okf_spec_version", "ntapp_unit", "ntapp_module", "ntapp_layer",
            "size_tokens", "epic",
            "code_repo", "dd_version", "dd_version_drift",
            "heading_level", "section_id", "doc_version", "subsections", "source_note",
            "adr_number",
            "slice", "slice_key", "slice_title", "slice_ordinal", "slice_set",
            "slice_type", "demo_status", "slice_units",
            "bug_id", "bug_severity", "bug_state", "bug_surface",
            "bug_reporter", "bug_reported_at",
            "ui_id", "ui_kind", "ui_controls", "ui_states", "ui_drift_notes",
            "design_system", "figma_ref",
            "source_sha", "content_sha",
            "governed_by", "implements", "built_as",
            "blocked_by", "enhanced_by",
            "consumes", "used_by", "consumes_external", "used_by_external",
            "lesson_section", "lesson_severity", "title_derived", "related_slices",
        ],
    ),
]

# Every field whose values are node ids.  One list, because the audit's dangling
# edge check reads it: an edge type added to an adapter but forgotten here would
# be the one edge in the bundle nothing ever validates — and it would look
# perfectly healthy in `--audit`.
#
# `consumes_external` / `used_by_external` are deliberately absent: they name
# systems outside the bundle, so having no node is their normal state.
# `derives_from` was declared here, and in `MACHINE_KEYS` and `KEY_ORDER`, for
# three registries' worth of a promise no adapter ever kept: 0 edges.  Nothing
# said so until `--audit` began counting each edge type by name.  Removed rather
# than left reserved, because a declared-but-empty key reads as "not populated
# yet" when the truth is "cannot be populated at this granularity".
#
# What the corpus can actually support, measured: file-level provenance is
# already carried by `sources[]` (357 nodes, 3–11 entries each, from
# `inherits_from` / `parent_techspec` / `inputDocuments`).  A node→node edge at
# *file* level would be worse than nothing — `inherits_from: project_wbs.md`
# fans one reference out to 161 nodes.  The only granularity worth an edge is
# section level, from the `§` references inside `Nguồn:` lines, and the whole
# corpus holds **12** of those (9 DD + 3 techspec).  Too thin for a family.
#
# Re-add it when documents cite sections rather than files, not before.
EDGE_KEYS = (
    "governed_by", "implements", "built_as",
    "consumes", "used_by",
    "blocked_by", "enhanced_by", "slice_units", "slice", "related_slices",
)

WINDOWS_RESERVED = frozenset(
    ["con", "prn", "aux", "nul"]
    + [f"com{i}" for i in range(1, 10)]
    + [f"lpt{i}" for i in range(1, 10)]
)


class OkfError(Exception):
    """Base class for errors that should stop the run with a clear message."""


class UnknownAdapterError(OkfError):
    """A family named an adapter that is not registered."""


class LockedError(OkfError):
    """Another projection run holds the bundle lock."""


# ─────────────────────────────────────────────────────────────────────────────
# Minimal YAML reader
#
# Covers exactly the subset used by the config blocks and node frontmatter:
# nested mappings, block lists (of scalars and of mappings), flow lists and flow
# mappings, folded/literal block scalars, comments.  Anything richer is out of
# contract and will be reported rather than silently misread.
# ─────────────────────────────────────────────────────────────────────────────

def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _next_content(lines: list[str], i: int) -> int:
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#"):
            return i
        i += 1
    return len(lines)


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}


def _read_quoted(text: str) -> tuple[str, int]:
    """Read one quoted scalar, honouring backslash escapes. Returns (value, end).

    The writer escapes `"` and `\\`, so the reader has to undo both.  Stopping at
    the first bare quote instead would truncate any value containing one — and
    since the truncated value is then written back, the text erodes a little on
    every pass with nothing to show that it happened.
    """
    quote = text[0]
    out: list[str] = []
    index = 1
    while index < len(text):
        char = text[index]
        if quote == '"' and char == "\\" and index + 1 < len(text):
            out.append(_ESCAPES.get(text[index + 1], text[index + 1]))
            index += 2
            continue
        if char == quote:
            return "".join(out), index + 1
        out.append(char)
        index += 1
    return "".join(out), len(text)


def _split_top(text: str) -> list[str]:
    """Split on commas that are not nested inside quotes or brackets."""
    out, buf, depth, quote = [], [], 0, ""
    escaped = False
    for ch in text:
        if quote:
            buf.append(ch)
            if escaped:
                escaped = False
            elif quote == '"' and ch == "\\":
                escaped = True
            elif ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        out.append("".join(buf))
    return out


def _strip_comment(text: str) -> str:
    """Remove a trailing ` # ...` comment that is not inside quotes."""
    quote = ""
    for idx, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch == "#" and (idx == 0 or text[idx - 1] in " \t"):
            return text[:idx].rstrip()
    return text


def _scalar(text: str):
    text = text.strip()
    if not text:
        return None
    if text[0] in "\"'":
        value, _ = _read_quoted(text)
        return value
    if text.startswith("{") and text.endswith("}"):
        return _flow_map(text[1:-1])
    if text.startswith("[") and text.endswith("]"):
        return _flow_list(text[1:-1])
    text = _strip_comment(text).strip()
    low = text.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?\d*\.\d+", text):
        return float(text)
    return text


def _flow_map(inner: str) -> dict:
    out = {}
    for chunk in _split_top(inner):
        key, sep, val = chunk.partition(":")
        if not sep:
            continue
        out[key.strip().strip("\"'")] = _scalar(val)
    return out


def _flow_list(inner: str) -> list:
    return [_scalar(chunk) for chunk in _split_top(inner)]


def _parse_block_scalar(lines: list[str], i: int, parent_indent: int, style: str):
    buf: list[str] = []
    base: int | None = None
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            buf.append("")
            i += 1
            continue
        cur = _indent_of(line)
        if cur <= parent_indent:
            break
        if base is None:
            base = cur
        buf.append(line[base:] if len(line) >= base else line.strip())
        i += 1
    while buf and not buf[-1]:
        buf.pop()
    if style.startswith(">"):
        paragraphs, para = [], []
        for entry in buf:
            if entry:
                para.append(entry.strip())
            else:
                paragraphs.append(" ".join(para))
                para = []
        if para:
            paragraphs.append(" ".join(para))
        text = "\n".join(paragraphs)
    else:
        text = "\n".join(buf)
    return text, i


def _parse_map(lines: list[str], i: int, indent: int):
    out: dict = {}
    while True:
        i = _next_content(lines, i)
        if i >= len(lines):
            break
        cur = _indent_of(lines[i])
        if cur < indent:
            break
        stripped = lines[i].strip()
        if cur > indent:  # stray deeper line, nothing claims it
            i += 1
            continue
        if stripped.startswith("- "):
            break
        key, sep, rest = stripped.partition(":")
        if not sep:
            i += 1
            continue
        key = key.strip().strip("\"'")
        rest = rest.strip()
        if rest in (">", "|", ">-", "|-", ">+", "|+"):
            out[key], i = _parse_block_scalar(lines, i + 1, indent, rest)
        elif rest == "" or rest.startswith("#"):
            value, i = _parse_block(lines, i + 1, indent + 1)
            out[key] = value
        else:
            out[key] = _scalar(rest)
            i += 1
    return out, i


def _parse_list(lines: list[str], i: int, indent: int):
    out: list = []
    while True:
        i = _next_content(lines, i)
        if i >= len(lines):
            break
        cur = _indent_of(lines[i])
        if cur != indent:
            break
        stripped = lines[i].strip()
        if stripped == "-":
            value, i = _parse_block(lines, i + 1, indent + 1)
            out.append(value)
            continue
        if not stripped.startswith("- "):
            break
        item = stripped[2:]
        item_stripped = item.strip()
        if item_stripped.startswith(("{", "[")) or item_stripped[:1] in "\"'":
            out.append(_scalar(item_stripped))
            i += 1
            continue
        head_key, sep, _ = item_stripped.partition(":")
        if sep and " " not in head_key.strip():
            # `- key: value` possibly followed by sibling keys one level in.
            # Rewrite the dash away so the item becomes an ordinary map opening
            # at column indent+2, then let _parse_map consume the whole item.
            lines[i] = " " * (indent + 2) + item
            value, i = _parse_map(lines, i, indent + 2)
            out.append(value)
            continue
        out.append(_scalar(item_stripped))
        i += 1
    return out, i


def _parse_block(lines: list[str], i: int, indent: int):
    i = _next_content(lines, i)
    if i >= len(lines):
        return None, i
    cur = _indent_of(lines[i])
    if cur < indent:
        return None, i
    if lines[i].strip().startswith(("- ",)) or lines[i].strip() == "-":
        return _parse_list(lines, i, cur)
    return _parse_map(lines, i, cur)


def yaml_load(text: str) -> dict:
    """Parse the supported YAML subset.  Always returns a mapping."""
    lines = normalise_text(text).split("\n")
    value, _ = _parse_block(lines, 0, 0)
    return value if isinstance(value, dict) else {}


# ─────────────────────────────────────────────────────────────────────────────
# Minimal YAML writer — emits only what yaml_load can read back.
# ─────────────────────────────────────────────────────────────────────────────

_SAFE_SCALAR = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./+@-]*$")


def _emit_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text:
        return '""'
    if "\n" in text:  # handled by caller as a block scalar
        raise ValueError("multi-line scalar must be emitted as a block")
    if _SAFE_SCALAR.match(text) and text.lower() not in (
        "true", "false", "yes", "no", "null", "~"
    ):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _emit_flow(value) -> str:
    if isinstance(value, dict):
        return "{" + ", ".join(
            f"{k}: {_emit_scalar(v)}" for k, v in value.items()
        ) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(
            _emit_flow(v) if isinstance(v, (dict, list)) else _emit_scalar(v)
            for v in value
        ) + "]"
    return _emit_scalar(value)


def _is_flat(value) -> bool:
    """True when a container holds only scalars (safe to emit inline)."""
    if isinstance(value, dict):
        return all(not isinstance(v, (dict, list)) for v in value.values())
    if isinstance(value, list):
        return all(not isinstance(v, (dict, list)) for v in value)
    return True


def yaml_emit(key: str, value, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, str) and "\n" in value:
        out = [f"{pad}{key}: |"]
        out.extend(f"{pad}  {line}".rstrip() for line in value.split("\n"))
        return out
    if isinstance(value, dict):
        if not value:
            return [f"{pad}{key}: {{}}"]
        if _is_flat(value) and len(_emit_flow(value)) + len(key) + indent < 100:
            return [f"{pad}{key}: {_emit_flow(value)}"]
        out = [f"{pad}{key}:"]
        for sub_key, sub_val in value.items():
            out.extend(yaml_emit(sub_key, sub_val, indent + 2))
        return out
    if isinstance(value, list):
        if not value:
            return [f"{pad}{key}: []"]
        if _is_flat(value) and len(_emit_flow(value)) + len(key) + indent < 100:
            return [f"{pad}{key}: {_emit_flow(value)}"]
        out = [f"{pad}{key}:"]
        for item in value:
            if isinstance(item, dict) and _is_flat(item):
                out.append(f"{pad}  - {_emit_flow(item)}")
            elif isinstance(item, (dict, list)):
                rendered = yaml_emit("_", item, indent + 4)[1:]
                out.append(f"{pad}  -")
                out.extend(rendered)
            else:
                out.append(f"{pad}  - {_emit_scalar(item)}")
        return out
    return [f"{pad}{key}: {_emit_scalar(value)}"]


# ─────────────────────────────────────────────────────────────────────────────
# Text normalisation and hashing
# ─────────────────────────────────────────────────────────────────────────────

def normalise_text(raw) -> str:
    """Decode UTF-8, unify line endings, drop trailing whitespace per line.

    Every hash in the bundle is taken over the output of this function.  Hashing
    raw bytes instead would give a file two different digests depending on the
    checkout's line endings; the bundle would then report every node stale on
    each machine switch, and the two machines would rewrite it at each other
    indefinitely.
    """
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = raw
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalise_text(text).encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    """Read a file as UTF-8, normalised.

    `encoding` is explicit because Python on Windows defaults to the ANSI code
    page, which would either raise on this Vietnamese corpus or — worse — decode
    it into mojibake and hash a perfectly valid-looking digest.
    """
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return normalise_text(handle.read())


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 with explicit LF, never the platform default.

    The text is normalised on the way out so that what lands on disk is exactly
    what `read_text` will hand back.  Otherwise any field value that happens to
    end in a space makes the write-if-changed probe compare a rendered line
    against its stripped self, disagree forever, and rewrite that node on every
    single run — which is how this was found.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalise_text(text))


def estimate_tokens(text: str, bytes_per_token: float) -> int:
    return int(len(text.encode("utf-8")) / bytes_per_token)


# ─────────────────────────────────────────────────────────────────────────────
# slugify — mandatory for every path segment in the bundle
# ─────────────────────────────────────────────────────────────────────────────

_VIET_D = str.maketrans({"đ": "d", "Đ": "D"})


def slugify(title: str, max_len: int = 60) -> str:
    """Fold an arbitrary heading into a portable path segment.

    Handles, in one place, six problems that would otherwise appear one at a
    time on somebody else's machine: characters Windows forbids in a filename,
    reserved device names, MAX_PATH, trailing dots and spaces, NFC/NFD drift
    between APFS and NTFS/ext4, and case-insensitive filesystems collapsing two
    distinct sources into one node.  Folding to lowercase ASCII settles all six.
    """
    text = str(title).translate(_VIET_D)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    if not text:
        text = "untitled"
    if text in WINDOWS_RESERVED:
        text = f"{text}-node"
    return text


_SAFE_ID_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def safe_id_segment(text: str, max_len: int = 60) -> str:
    """Path segment for an *identifier* rather than a prose title.

    `slugify` exists to tame free text written by people, and folding case is
    part of that job.  An identifier such as `BE-INV-09` or `C-01` comes from a
    controlled vocabulary that is already portable, and lowercasing it would cut
    the visual tie to the id used in every other document and every code header.
    So identifiers pass through when they are provably safe, and only fall back
    to slugify when they are not.  Case-insensitive collisions are still a real
    hazard on APFS and NTFS, so callers must check for them — see
    `CaseGuard`.
    """
    candidate = str(text).strip()
    if (
        _SAFE_ID_SEGMENT.match(candidate)
        and len(candidate) <= max_len
        and candidate.lower() not in WINDOWS_RESERVED
        and not candidate.endswith((".", " "))
    ):
        return candidate
    return slugify(candidate, max_len)


class CaseGuard:
    """Catch two ids that differ only by case before the filesystem does.

    macOS and NTFS would silently merge them into one node; CI on Linux would
    keep both.  The same bundle then has a different node count depending on
    where it was built, and nothing reports it.
    """

    def __init__(self):
        self._seen: dict[str, str] = {}

    def check(self, segment: str) -> str | None:
        previous = self._seen.get(segment.lower())
        if previous is not None and previous != segment:
            return previous
        self._seen[segment.lower()] = segment
        return None


def unique_slug(base: str, taken: set[str]) -> str:
    """Deterministic de-duplication: `-2`, `-3`, … in first-seen order."""
    if base not in taken:
        taken.add(base)
        return base
    counter = 2
    while f"{base}-{counter}" in taken:
        counter += 1
    result = f"{base}-{counter}"
    taken.add(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Path matching
# ─────────────────────────────────────────────────────────────────────────────

def _seg_re(segment: str) -> str:
    out = []
    idx = 0
    while idx < len(segment):
        ch = segment[idx]
        if ch == "*":
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        elif ch == "[":
            end = segment.find("]", idx)
            if end == -1:
                out.append(re.escape(ch))
            else:
                out.append(segment[idx:end + 1])
                idx = end
        else:
            out.append(re.escape(ch))
        idx += 1
    return "".join(out)


def compile_glob(pattern: str) -> re.Pattern:
    """Translate a `**`-aware glob into a regex over POSIX relative paths.

    `pathlib.PurePath.match()` does not implement `**` recursively on any
    platform, and `str(path)` yields backslashes on Windows, so a pattern
    written with `/` matches nothing there.  Both failures are silent: the
    exclude list looks like it is protecting the scan while filtering nothing.
    """
    segments = pattern.split("/")
    out = ["^"]
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        if segment == "**":
            out.append(".*" if last else "(?:[^/]*/)*")
            continue
        out.append(_seg_re(segment))
        if not last:
            out.append("/")
    out.append("$")
    return re.compile("".join(out))


def to_posix_rel(path, root) -> str:
    """Normalise any path to a POSIX relative string — once, at the boundary.

    Everything downstream (exclude matching, `resource:` values, node ids)
    compares against this form.  A backslash never enters the bundle.
    """
    text = str(path).replace("\\", "/")
    root_text = str(root).replace("\\", "/").rstrip("/")
    if root_text and text.startswith(root_text + "/"):
        text = text[len(root_text) + 1:]
    return PurePosixPath(text).as_posix()


class ExcludeSet:
    def __init__(self, patterns: list[str]):
        self.patterns = list(dict.fromkeys(patterns))
        self._compiled = [compile_glob(pat) for pat in self.patterns]

    def matches(self, rel_posix: str) -> str | None:
        for pattern, regex in zip(self.patterns, self._compiled):
            if regex.match(rel_posix):
                return pattern
        return None

    def __contains__(self, rel_posix: str) -> bool:
        return self.matches(rel_posix) is not None


# ─────────────────────────────────────────────────────────────────────────────
# Configuration — L0 defaults, L1 optional override, L2 project declaration
# ─────────────────────────────────────────────────────────────────────────────

def interpolate(value: str, variables: dict) -> str:
    out = str(value)
    for _ in range(5):  # placeholders may nest one level (root -> output_folder)
        replaced = out
        for key, val in variables.items():
            replaced = replaced.replace("{" + key + "}", str(val))
        if replaced == out:
            break
        out = replaced
    return out


def merge_exclude(*layers: list) -> list:
    """Union, never replacement.

    If a later layer replaced the list, every project would have to restate all
    defaults; missing one line would silently drop a guard with nothing to
    report it.
    """
    merged: list[str] = []
    for layer in layers:
        for pattern in layer or []:
            if pattern not in merged:
                merged.append(pattern)
    return merged


class Config:
    def __init__(self, project_root: Path, layer1: dict, layer2: dict):
        self.project_root = project_root
        self.layer1 = layer1 or {}
        self.layer2 = layer2 or {}

        okf1 = self.layer1.get("okf") or {}
        okf2 = self.layer2.get("okf") or {}

        output_folder = (
            okf2.get("output_folder")
            or okf1.get("output_folder")
            or self.layer2.get("output_folder")
            or self.layer1.get("output_folder")
            or "{project-root}/NTAPP-output"
        )
        variables = {"project-root": str(project_root)}
        self.output_folder = Path(interpolate(output_folder, variables))
        variables["output_folder"] = str(self.output_folder)

        merged = dict(DEFAULTS)
        for layer in (okf1, okf2):
            for key, value in layer.items():
                if key == "exclude":
                    continue
                merged[key] = value
        merged["exclude"] = merge_exclude(
            DEFAULTS["exclude"], okf1.get("exclude"), okf2.get("exclude")
        )

        self.values = merged
        self.root = Path(interpolate(merged["root"], variables))
        self.exclude = ExcludeSet(merged["exclude"])
        self.families = okf2.get("families") or {}
        self.code_repos = okf2.get("code_repos") or []
        self.reserved_dirs = set(merged.get("reserved_dirs") or [])

    def get(self, key, default=None):
        return self.values.get(key, default)


def find_project_root(start: Path) -> Path:
    """Walk up looking for a spec repo marker; fall back to the git toplevel."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".bmm-config.yaml").exists():
            return candidate
        if (candidate / "_bmad" / "bmm" / "config.yaml").exists():
            return candidate
    return current


def load_config(project_root: Path, config_path: Path | None) -> tuple[Config, list[str]]:
    notes: list[str] = []
    layer1_path = project_root / "_bmad" / "bmm" / "config.yaml"
    layer2_path = config_path or (project_root / ".bmm-config.yaml")

    layer1: dict = {}
    if layer1_path.exists():
        layer1 = yaml_load(read_text(layer1_path))
    else:
        notes.append(f"layer1 absent ({to_posix_rel(layer1_path, project_root)}) — using L0 defaults")

    layer2: dict = {}
    if layer2_path.exists():
        layer2 = yaml_load(read_text(layer2_path))
    else:
        notes.append(f"layer2 absent ({to_posix_rel(layer2_path, project_root)})")

    return Config(project_root, layer1, layer2), notes


# ─────────────────────────────────────────────────────────────────────────────
# Actor identity — derived, never typed
# ─────────────────────────────────────────────────────────────────────────────

def _git(root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def derive_actor(root: Path) -> str | None:
    """`git config` → `git check-mailmap` → local part of the address.

    Nobody types a name and there is no roster in config.  A roster would be
    defending against typos that only exist because somebody was asked to type.
    The multiplicity that does exist — one person under several addresses —
    lives in git *history*; at the moment of signing the machine has exactly one
    configured identity, and `.mailmap` is git's own way to canonicalise it.
    Absent a `.mailmap` this still works, it just does not merge the aliases.
    """
    email = _git(root, ["config", "user.email"])
    if not email:
        return None
    name = _git(root, ["config", "user.name"]) or ""
    canonical = _git(root, ["check-mailmap", f"{name} <{email}>".strip()])
    match = re.search(r"<([^>]+)>", canonical or "")
    address = match.group(1) if match else email
    local_part = address.split("@", 1)[0]
    return f"human:{slugify(local_part, 40)}"


def in_ci() -> bool:
    if str(os.environ.get("CI", "")).lower() in ("1", "true", "yes"):
        return True
    return not sys.stdin.isatty()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────────────────────────
# Node model and frontmatter I/O
# ─────────────────────────────────────────────────────────────────────────────

class Node:
    """One projected concept.  `node_id` is a POSIX path without the extension,
    because in OKF the file path *is* the concept's identity."""

    __slots__ = ("node_id", "fields", "body")

    def __init__(self, node_id: str, fields: dict, body: str = ""):
        self.node_id = node_id
        self.fields = fields
        self.body = body

    @property
    def type(self) -> str:
        return self.fields.get("type", "")


def split_frontmatter(text: str) -> tuple[dict, str]:
    text = normalise_text(text)
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[4:end]
    # Strip *all* leading blank lines, not one. `render_node` re-inserts exactly
    # one separator, so leaving any behind makes read-modify-write grow the body
    # by a line each time — and every such rewrite counts as a change, which is
    # the churn the write-if-unchanged rule exists to prevent.
    rest = text[end + 4:].lstrip("\n")
    return yaml_load(block), rest


def render_node(fields: dict, body: str) -> str:
    lines = ["---"]
    emitted: set[str] = set()
    for group, keys in KEY_ORDER:
        group_lines: list[str] = []
        for key in keys:
            if key in fields and fields[key] not in (None, [], {}):
                group_lines.extend(yaml_emit(key, fields[key]))
                emitted.add(key)
        if group_lines:
            lines.append(f"# ---------- {group} ----------")
            lines.extend(group_lines)
    leftovers = [k for k in fields if k not in emitted and fields[k] not in (None, [], {})]
    if leftovers:
        lines.append("# ---------- preserved (human-authored) ----------")
        for key in leftovers:
            lines.extend(yaml_emit(key, fields[key]))
    lines.append("---")
    text = "\n".join(lines) + "\n"
    if body:
        text += "\n" + body.rstrip("\n") + "\n"
    # Normalised here so the write-if-changed probe compares like with like:
    # `read_text` strips trailing whitespace, so a rendered line that keeps any
    # would never equal its own file and the node would rewrite forever.
    return normalise_text(text)


def merge_preserving(new_fields: dict, old_fields: dict,
                     also_preserve: frozenset = frozenset()) -> dict:
    """Machine keys are replaced; everything a human added survives.

    `verified[]` is append-only history that section 1.1 calls unreconstructible.
    A projector that rewrote node files wholesale would erase every signature on
    the first `--full`, and by its own definition they could not be recovered.
    So preservation is a hard rule of reprojection, not an option.

    `also_preserve` carries the fields owned by the link pass rather than by any
    family — `built_as` and its kind.  They are machine-written, but not by the
    family that owns the node, so a family write must leave them alone.  Without
    this the two passes fight: the family drops the edge, the link pass puts it
    back, and every run rewrites the same nodes forever.
    """
    merged = dict(new_fields)
    for key, value in (old_fields or {}).items():
        if key not in MACHINE_KEYS or key in also_preserve:
            merged[key] = value
    return merged


def derive_status(fields: dict) -> str:
    if fields.get("status") == "deprecated":
        return "deprecated"
    return "stable" if fields.get("verified") else "draft"


# ─────────────────────────────────────────────────────────────────────────────
# Bundle — writer, lock, log, status
# ─────────────────────────────────────────────────────────────────────────────

class Bundle:
    def __init__(self, config: Config):
        self.config = config
        self.root = config.root
        self.written = 0
        self.unchanged = 0
        self.created = 0
        self.deprecated = 0
        # Fields written by the link pass, not by the family that owns the node.
        self.link_fields = frozenset(
            str(link.get("back_edge")) for link in (config.get("links") or [])
            if link.get("back_edge")
        )

    def node_path(self, node_id: str) -> Path:
        return self.root / (node_id + ".md")

    def read_node(self, node_id: str) -> tuple[dict, str] | None:
        path = self.node_path(node_id)
        if not path.exists():
            return None
        return split_frontmatter(read_text(path))

    def write_node(self, node: Node, actor: str) -> str:
        """Write a node, preserving human keys, touching disk only on change.

        Rewriting `generated.at` on every pass would produce a full-bundle
        changeset each run and destroy the one property that makes frontmatter
        trust worth having: that `git diff` shows what actually moved.
        """
        path = self.node_path(node.node_id)
        existing = self.read_node(node.node_id)
        fields = dict(node.fields)
        fields.setdefault("okf_spec_version", self.config.get("spec_version"))

        if existing:
            old_fields, _ = existing
            fields = merge_preserving(fields, old_fields, self.link_fields)
            fields["status"] = derive_status(fields)
            previous_at = (old_fields.get("generated") or {}).get("at")
            probe = dict(fields)
            probe["generated"] = {"by": actor, "at": previous_at}
            if render_node(probe, node.body) == read_text(path):
                self.unchanged += 1
                return "unchanged"
            fields["generated"] = {"by": actor, "at": utc_now()}
            write_text(path, render_node(fields, node.body))
            self.written += 1
            return "updated"

        fields["generated"] = {"by": actor, "at": utc_now()}
        fields["status"] = derive_status(fields)
        write_text(path, render_node(fields, node.body))
        self.created += 1
        return "created"

    def existing_ids(self, prefix: str = "") -> set[str]:
        base = self.root / prefix if prefix else self.root
        if not base.exists():
            return set()
        out = set()
        for path in base.rglob("*.md"):
            rel = to_posix_rel(path, self.root)
            if rel in ("index.md", "status.md", "log.md") or rel.startswith("log/"):
                continue
            if path.name == TYPE_INDEX_NAME:
                continue
            out.add(rel[:-3])
        return out

    def is_deprecated(self, node_id: str) -> bool:
        existing = self.read_node(node_id)
        return bool(existing and existing[0].get("status") == "deprecated")

    def deprecate(self, node_id: str) -> None:
        """A removed source must remove its node — but not instantly.

        Incremental runs only touch sources that changed, so a deleted section
        would otherwise leave a node behind that still resolves and still has
        edges pointing at it: indistinguishable from a live one.  Deleting on
        sight is worse though — one transient glob mistake would take out a
        whole family — so the node is marked and swept later.
        """
        existing = self.read_node(node_id)
        if not existing:
            return
        fields, body = existing
        if fields.get("status") == "deprecated":
            return
        fields["status"] = "deprecated"
        fields["deprecated_at"] = utc_now()
        write_text(self.node_path(node_id), render_node(fields, body))
        self.deprecated += 1

    def sweep_deprecated(self, grace_days: int) -> list[str]:
        removed = []
        cutoff = time.time() - grace_days * 86400
        for node_id in sorted(self.existing_ids()):
            existing = self.read_node(node_id)
            if not existing:
                continue
            fields, _ = existing
            if fields.get("status") != "deprecated":
                continue
            stamp = fields.get("deprecated_at")
            try:
                marked = datetime.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ")
                marked = marked.replace(tzinfo=timezone.utc).timestamp()
            except (TypeError, ValueError):
                continue
            if marked < cutoff:
                self.node_path(node_id).unlink()
                removed.append(node_id)
        return removed

    # ── bookkeeping files ────────────────────────────────────────────────────

    def ensure_scaffold(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
            entries = self.config.get("untracked_bundle_files") or []
            write_text(
                gitignore,
                "# Machine-written bookkeeping. The node files themselves are\n"
                "# meant to be committed — trust metadata in frontmatter is only\n"
                "# worth having if `git diff` can show it moving. These four\n"
                "# change on every run and would bury that signal.\n"
                + "\n".join(entries) + "\n",
            )
        index = self.root / "index.md"
        if not index.exists():
            write_text(index, self._starter_index())

    def _starter_index(self) -> str:
        return (
            "# OKF bundle — điểm vào\n\n"
            "> File này do **người** viết và projector **không bao giờ ghi đè**.\n"
            "> Trạng thái máy sinh nằm ở `status.md`.\n\n"
            "## Giao thức 3 tầng\n\n"
            "1. **Định hướng** — hai bước, đừng bỏ bước đầu:\n"
            "   - `status.md` mục *\"Mỗi loại trả lời câu hỏi gì\"* → **chọn loại**.\n"
            "   - `<type>/_index.md` → **chọn node**: mã, tiêu đề, chi phí đọc.\n"
            "2. **Duyệt** — lọc và đi theo cạnh bằng trường frontmatter. Thẻ ~300 token,\n"
            "   thường trả lời thẳng được.\n"
            "3. **Resolve** — chỉ khi thẻ không đủ: theo `resource` + `anchor` vào tài liệu\n"
            "   gốc và đọc **nguyên văn**.\n\n"
            "## Ràng buộc bắt buộc\n\n"
            "Thẻ node là **chỉ mục truy hồi, không bao giờ là nguồn để viết**. Iron Rules\n"
            "R1/R2 cấm thay chi tiết nguồn bằng tóm tắt: mọi quyết định đặc tả phải\n"
            "resolve về master và đọc nguyên văn. Đồ thị thu hẹp *phạm vi* của một lần đọc\n"
            "nguyên văn, không thay thế nó.\n\n"
            "## Không sửa tay trong bundle\n\n"
            "Bundle là dẫn xuất một chiều, dựng lại được từ đầu. Đường duy nhất để người\n"
            "ghi vào đây là `/NTAPP-okf-refresh --verify <node>`.\n"
        )

    def write_status(self, payload: dict) -> None:
        lines = [
            "# Trạng thái bundle (máy ghi — không sửa tay)", "",
            f"- `last_refresh`: {payload.get('last_refresh')}",
            f"- `mode`: {payload.get('mode')}",
            f"- `spec_version`: {self.config.get('spec_version')}",
            f"- `actor`: {payload.get('actor')}", "",
            "## Node", "",
            "| Type | Số |", "|---|---:|",
        ]
        counts = payload.get("counts") or {}
        for type_name in sorted(counts):
            lines.append(f"| `{type_name}` | {counts[type_name]} |")
        lines.append(f"| **Tổng** | **{sum(counts.values())}** |")

        # Which type do I want?  Without this, the table above tells a newcomer
        # how much there is and nothing about what any of it answers, so the only
        # way to choose a type is to open one and guess.  Every family already
        # declares a `goal`; it just never reached a reader.
        family_counts = payload.get("families") or {}
        if family_counts:
            lines += ["", "## Mỗi loại trả lời câu hỏi gì", ""]
            for fam_name in sorted(family_counts):
                family = (self.config.families.get(fam_name) or {})
                goal = " ".join((family.get("goal") or "").split())
                lines.append(
                    f"### `{fam_name}` — {family_counts[fam_name]} node · "
                    f"mục lục: [`{fam_name}/{TYPE_INDEX_NAME}`]({fam_name}/{TYPE_INDEX_NAME})"
                )
                lines += ["", goal or
                          "⚠️ **Chưa khai `goal`** — khai vào `okf.families` "
                          "trong `.bmm-config.yaml`.", ""]

        lines += ["", "## Code repo đã quét", ""]
        scanned = payload.get("repos_scanned") or []
        missing = payload.get("repos_missing") or []
        if not scanned and not missing:
            lines.append("_Chưa khai `code_repos` (P2 chưa chạy)._")
        else:
            for name in scanned:
                lines.append(f"- ✅ `{name}`")
            for name in missing:
                lines.append(f"- ❌ `{name}` — **vắng mặt**")
        scan = (payload.get("stats") or {}).get("code_scan") or {}
        if scan:
            lines += [
                "", "## Độ phủ thẻ `id:` trong code", "",
                "| Repo | Quét | Gắn thẻ | Không truy vết |", "|---|---:|---:|---:|",
            ]
            totals = [0, 0, 0]
            for repo_name in sorted(scan):
                row = scan[repo_name]
                lines.append(
                    f"| `{repo_name}` | {row['scanned']} | {row['tagged']} | "
                    f"{row['untagged']} |"
                )
                totals = [totals[0] + row["scanned"], totals[1] + row["tagged"],
                          totals[2] + row["untagged"]]
            lines.append(f"| **Tổng** | **{totals[0]}** | **{totals[1]}** | "
                         f"**{totals[2]}** |")
        if missing:
            lines += [
                "",
                "> ⚠️ **Tập repo chưa đủ.** Mọi truy vấn về độ phủ (\"unit chưa build\")",
                "> phải từ chối trả số khi thấy dòng này. Thiếu repo là *chưa biết*,",
                "> không phải *chưa build* — và đó đúng là loại nhầm lẫn đồ thị sinh ra",
                "> để chấm dứt.",
            ]
        write_text(self.root / "status.md", "\n".join(lines) + "\n")

    def write_type_index(self, name: str, family: dict, nodes: list) -> None:
        """One table of contents per type — tier 1 of the read protocol.

        `index.md` and the `AGENTS.md` pointer both instruct a reader to open
        "this file plus one type index".  Until this existed, that instruction
        named an artifact nobody had built — a worse failure than a missing
        file, because the reader follows the instruction, finds nothing, and
        concludes the *bundle* is empty rather than the map.

        The `goal` a family declares has been sitting in config all along, read
        only to be printed to a terminal during `--dry-run` and then discarded.
        This is where it lands somewhere a reader will actually meet it.
        """
        if not nodes:
            return
        goal = " ".join((family.get("goal") or "").split())
        # Adapters do not agree on one key for "where this comes from":
        # `slice-manifest` reads `slice_dir`, `id-header-scan` and
        # `knowledge-bullets` read `unit_source`, and `source_glob` may hold a
        # single pattern or a list of them.  Reading only `source`/`source_glob`
        # printed an em dash for every family that declares another key — and an
        # index claiming its type has no source is worse than one that omits the
        # line, because the reader stops looking for a master to resolve to.
        source = next(
            (family[key] for key in
             ("source", "source_glob", "slice_dir", "unit_source")
             if family.get(key)), "—")
        if isinstance(source, (list, tuple)):
            source = ", ".join(str(item) for item in source)
        rows, total_tokens = [], 0
        for node in sorted(nodes, key=lambda n: n.node_id):
            rel = node.node_id
            if rel.startswith(name + "/"):
                rel = rel[len(name) + 1:]
            title = str(node.fields.get("title") or "").strip() or rel
            tokens = node.fields.get("size_tokens")
            tokens = tokens if isinstance(tokens, int) else 0
            total_tokens += tokens
            rows.append((rel, title.replace("|", "\\|"), tokens))

        lines = [
            f"# `{name}` — mục lục ({len(rows)} node)",
            "",
            "> Máy ghi mỗi lượt chiếu. **Không sửa tay** — sửa xong lượt sau mất.",
            "",
        ]
        if goal:
            lines += [f"**Dùng để:** {goal}", ""]
        else:
            # Rendered, not skipped.  A blank where the purpose belongs is the
            # only thing that makes anyone go and declare one.
            lines += [
                "> ⚠️ **Family này chưa khai `goal`** — không có gì nói nó tồn tại "
                "để trả lời câu hỏi nào. Khai vào `okf.families` trong "
                "`.bmm-config.yaml`.",
                "",
            ]
        lines += [
            f"- Nguồn: `{source}`",
            f"- Chi phí đọc cả loại: ~{total_tokens:,} token".replace(",", "."),
            "",
            "| Node | Tiêu đề | Token |",
            "|---|---|---:|",
        ]
        for rel, title, tokens in rows:
            lines.append(f"| [`{rel}`]({rel}.md) | {title} | {tokens:,} |".replace(",", "."))
        lines += [
            "",
            "> Thẻ node là **chỉ mục truy hồi, không bao giờ là nguồn để viết**.",
            "> Cần chi tiết thì theo `resource` + `anchor` của thẻ vào tài liệu gốc",
            "> và đọc nguyên văn (Iron Rules R1/R2).",
        ]
        write_text(self.root / name / TYPE_INDEX_NAME, "\n".join(lines) + "\n")

    def append_log(self, entries: list[str]) -> None:
        if not entries:
            return
        log_path = self.root / "log.md"
        stamp = utc_now()
        block = [f"## {stamp}", *[f"- {entry}" for entry in entries], ""]
        old = read_text(log_path).split("\n") if log_path.exists() else ["# Lịch sử chiếu", ""]
        merged = old + block
        limit = int(self.config.get("log_max_lines") or 500)
        if len(merged) > limit:
            cut = len(merged) - limit
            archive_name = datetime.now(timezone.utc).strftime("%Y-%m")
            archive_path = self.root / "log" / f"{archive_name}.md"
            previous = read_text(archive_path) if archive_path.exists() else ""
            write_text(archive_path, previous + "\n".join(merged[:cut]) + "\n")
            merged = ["# Lịch sử chiếu", "", f"_Phần cũ ở `log/{archive_name}.md`._", ""] + merged[cut:]
        write_text(log_path, "\n".join(merged).rstrip("\n") + "\n")


class BundleLock:
    """Guard against two overlapping runs.

    Removing the hook did not remove the race, it moved it: a nightly CI job and
    a person running the skill before a demo can still collide.  The second run
    must not wait and must not write — it reports and leaves.
    """

    def __init__(self, root: Path, ttl: int):
        self.path = root / ".lock"
        self.ttl = ttl
        self.held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if self._stale():
                try:
                    self.path.unlink()
                except OSError:
                    pass
                return self.acquire()
            raise LockedError(f"locked by {self._describe()}")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(f"pid: {os.getpid()}\nat: {utc_now()}\nepoch: {int(time.time())}\n")
        self.held = True

    def _read(self) -> dict:
        try:
            return yaml_load(read_text(self.path))
        except (OSError, UnicodeDecodeError):
            return {}

    def _describe(self) -> str:
        info = self._read()
        return f"pid {info.get('pid', '?')} since {info.get('at', '?')}"

    def _stale(self) -> bool:
        info = self._read()
        epoch = info.get("epoch")
        if isinstance(epoch, int) and time.time() - epoch > self.ttl:
            return True
        pid = info.get("pid")
        if not isinstance(pid, int):
            return True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except (OSError, AttributeError):
            return False  # Windows, or no permission — trust the TTL instead
        return False

    def release(self) -> None:
        if self.held and self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                pass
        self.held = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_exc):
        self.release()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Adapter registry
#
# Adapter contract:
#     fn(family_name: str, family_cfg: dict, ctx: Context) -> Iterable[Node]
#
# P0 registers none.  A family naming an adapter that does not exist must fail
# loudly — the alternative is a clean exit reporting zero nodes, which is the
# exact failure shape this whole design is built to stop.
# ─────────────────────────────────────────────────────────────────────────────

ADAPTERS: dict = {}


def adapter(name: str):
    def decorate(fn):
        ADAPTERS[name] = fn
        return fn
    return decorate


def resolve_adapter(name: str):
    if name not in ADAPTERS:
        known = ", ".join(sorted(ADAPTERS)) or "(none registered)"
        raise UnknownAdapterError(f"unknown adapter {name!r}; registered: {known}")
    return ADAPTERS[name]


class Context:
    def __init__(self, config: Config, bundle: Bundle, actor: str):
        self.config = config
        self.bundle = bundle
        self.actor = actor
        self.project_root = config.project_root
        self.output_folder = config.output_folder
        self.exclude = config.exclude
        self.warnings: list[str] = []
        self.stats: dict = {}
        # ADR number → node id, filled by the series families as they project
        # (see `register_adr_series`).  Keyed by the *literal digit string*, so
        # "001" and "0001" are already different keys and the two series cannot
        # collide without also colliding in width — which is the one case
        # `adr_ambiguous` exists to catch.
        self.adr_by_number: dict[str, str] = {}
        self.adr_owner: dict[str, str] = {}
        self.adr_ambiguous: set[str] = set()
        self.adr_series_seen: list[str] = []

    def iter_sources(self, pattern: str) -> list[Path]:
        """Expand a family glob, then apply exclude.

        Order matters and is fixed: the family glob selects, exclude filters,
        and a family can never overrule exclude.  Otherwise a family could grant
        itself permission to read a derived layer such as `_parts/`.
        """
        base = self.output_folder
        matches = sorted(base.glob(pattern)) if pattern else []
        kept = []
        for path in matches:
            if not path.is_file():
                continue
            rel = to_posix_rel(path, self.project_root)
            hit = self.exclude.matches(rel)
            if hit:
                continue
            kept.append(path)
        return kept

    def resolve_source(self, rel: str) -> Path:
        path = (self.output_folder / str(rel)).resolve()
        hit = self.exclude.matches(to_posix_rel(path, self.project_root))
        if hit:
            raise OkfError(
                f"source {rel!r} is matched by exclude pattern {hit!r}. "
                "A family may not grant itself permission to read a derived layer."
            )
        if not path.exists():
            raise OkfError(f"source not found: {path}")
        return path

    def token_estimate(self, text: str) -> int:
        return estimate_tokens(text, float(self.config.get("token_bytes_per_token") or 3.5))


# ─────────────────────────────────────────────────────────────────────────────
# Adapter helpers — markdown tables and document anchors
# ─────────────────────────────────────────────────────────────────────────────

_MD_NOISE = re.compile(r"\*\*|__|`")


def clean_cell(cell: str) -> str:
    return _MD_NOISE.sub("", str(cell or "")).strip()


def split_row(line: str) -> list[str]:
    return [clean_cell(c) for c in line.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(set(c) <= {"-", ":", " "} for c in cells)


def find_section(lines: list[str], heading_match: str) -> tuple[int, int, str]:
    """Locate a section by a case-insensitive substring of its heading.

    Returns (start, end, heading_text).  Ranges are line indices; `end` is the
    next heading at the same or shallower level.
    """
    needle = heading_match.lower()
    for index, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        level = len(line) - len(line.lstrip("#"))
        text = line[level:].strip()
        if needle in text.lower():
            for follow in range(index + 1, len(lines)):
                if lines[follow].startswith("#"):
                    next_level = len(lines[follow]) - len(lines[follow].lstrip("#"))
                    if next_level <= level:
                        return index, follow, text
            return index, len(lines), text
    raise OkfError(f"section not found: heading containing {heading_match!r}")


def read_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """First markdown table in `lines` → (headers, rows)."""
    headers: list[str] = []
    rows: list[list[str]] = []
    for line in lines:
        if not line.strip().startswith("|"):
            if headers:
                break
            continue
        cells = split_row(line)
        if not headers:
            headers = [c.lower() for c in cells]
            continue
        if is_separator_row(cells):
            continue
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        rows.append(cells)
    return headers, rows


def relative_resource(node_id: str, master: Path, bundle_root: Path) -> str:
    """POSIX path from a node file back to its master document.

    Kept relative so the bundle survives being cloned to a different absolute
    location, and POSIX so a Windows run does not write backslashes into it.
    """
    node_dir = (bundle_root / node_id).parent
    rel = Path(os.path.relpath(master, node_dir)).as_posix()
    if rel.count("../") > 8:
        # A sane bundle sits inside the output folder, so a master is a handful
        # of levels away. A ladder of `../` means `okf.root` was pointed outside
        # the project, and every `resource:` in the bundle would be unusable
        # after a clone.
        raise OkfError(
            f"resource path escapes {rel.count('../')} levels up ({rel}). "
            "`okf.root` should stay inside the project's output folder."
        )
    return rel


def anchor_for(heading: str) -> str:
    return slugify(heading, 120)


_ID_TOKEN = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b")


def unit_source_block(text: str, uid: str) -> str:
    """The lines where this unit is the *subject*, not merely mentioned.

    `content_sha` has to answer "does this node still match its own part of the
    master", so it is taken over the unit's own rows — not the whole file, which
    would make one edit anywhere report all 161 units stale.

    Matching every mention is just as wrong in the other direction: a widget row
    listing `used_by: SCR-CHK-CHECKOUT` would be pulled into the checkout unit's
    fingerprint, so editing the widget would report the screen stale.  A unit is
    the subject of a table row when its id is in the first cell, and of a tree
    line when its id is the first identifier on it.
    """
    pattern = re.compile(rf"(?<![A-Z0-9-]){re.escape(uid)}(?![A-Z0-9-])")
    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            first_cell = clean_cell(stripped.strip("|").split("|")[0])
            if pattern.search(first_cell):
                kept.append(line)
            continue
        found = _ID_TOKEN.search(line)
        if found and found.group(0) == uid:
            kept.append(line)
    return "\n".join(kept)


# ─────────────────────────────────────────────────────────────────────────────
# P1 adapters — the two registries
# ─────────────────────────────────────────────────────────────────────────────

def _load_wbs_parser():
    """Reuse the framework's existing WBS parser rather than reimplementing it.

    It already models a unit as identity plus edges, which is a node and its
    relationships under another name.  A second parser would be a second thing
    to keep in step with the table format.
    """
    lib = Path(__file__).resolve().parent.parent / "hooks" / "lib"
    if str(lib) not in sys.path:
        sys.path.insert(0, str(lib))
    try:
        import wbs_parser  # type: ignore
    except ImportError as exc:  # pragma: no cover - configuration error
        raise OkfError(f"cannot import hooks/lib/wbs_parser.py: {exc}") from exc
    return wbs_parser


@adapter("wbs-index")
def adapter_wbs_index(name: str, family: dict, ctx: Context):
    wbs_parser = _load_wbs_parser()
    master = ctx.resolve_source(family.get("source") or "")
    text = read_text(master)
    file_sha = sha256_text(text)
    lines = text.split("\n")

    try:
        _, _, heading = find_section(lines, family.get("anchor_section", "Machine-readable"))
    except OkfError:
        heading = "Machine-readable WBS Index"

    units = wbs_parser.parse_wbs(master)
    known = {unit.id for unit in units}
    node_type = family.get("type", "wbs-unit")
    guard = CaseGuard()

    for unit in units:
        segment = safe_id_segment(unit.id)
        clash = guard.check(segment)
        if clash:
            ctx.warnings.append(
                f"{name}: {unit.id!r} and {clash!r} differ only by case — "
                "they would merge into one node on macOS/NTFS"
            )
        node_id = f"{name}/{segment}"
        block = unit_source_block(text, unit.id)
        title = f"{unit.id} — {unit.feature_name}" if unit.feature_name else unit.id
        tags = [tag for tag in (unit.module, unit.type) if tag]

        fields = {
            "type": node_type,
            "title": title,
            "description": unit.summary or unit.feature_name or "",
            "resource": relative_resource(node_id, master, ctx.bundle.root),
            "anchor": anchor_for(heading),
            "anchor_text": heading,
            "tags": tags,
            "sources": [{"resource": relative_resource(node_id, master, ctx.bundle.root)}],
            "ntapp_unit": unit.id,
            "size_tokens": ctx.token_estimate(block),
            "source_sha": file_sha,
            "content_sha": sha256_text(block),
        }
        if unit.epic:
            fields["epic"] = unit.epic

        design_glob = family.get("design_doc")
        if design_glob:
            design_path = ctx.output_folder / str(design_glob).replace("{unit}", unit.id)
            if design_path.exists():
                version = design_version(design_path)
                if version:
                    fields["dd_version"] = version

        for edge, targets in (("consumes", unit.consumes), ("used_by", unit.used_by)):
            resolved, external, dangling = [], [], []
            for target in targets:
                if target in known:
                    resolved.append(target)
                elif wbs_parser.is_external(target):
                    external.append(target)
                else:
                    dangling.append(target)
            if resolved:
                fields[edge] = [f"{name}/{safe_id_segment(t)}" for t in resolved]
            if external:
                # An external system has no owning unit by definition, so it is
                # recorded as an attribute rather than an edge into nothing.
                fields[f"{edge}_external"] = external
            for target in dangling:
                # An edge to something the WBS never declares and that is not a
                # known external is a defect in the table, not noise to drop.
                ctx.warnings.append(
                    f"{unit.id}: `{edge}` names {target!r}, which is neither a WBS "
                    "unit nor an external system"
                )

        body = _wbs_body(unit, block)
        yield Node(node_id, fields, body)


def _wbs_body(unit, block: str) -> str:
    rows = [
        "| Trường | Giá trị |", "|---|---|",
        f"| ID | `{unit.id}` |",
        f"| Loại | {unit.type or '—'} |",
        f"| Module | {unit.module or '—'} |",
        f"| Epic | {unit.epic or '—'} |",
    ]
    if unit.consumes:
        rows.append(f"| Dùng | {', '.join(f'`{x}`' for x in unit.consumes)} |")
    if unit.used_by:
        rows.append(f"| Bị dùng bởi | {', '.join(f'`{x}`' for x in unit.used_by)} |")
    out = [f"# {unit.id}", ""]
    if unit.feature_name:
        out += [f"**{unit.feature_name}**", ""]
    if unit.summary:
        out += [unit.summary, ""]
    out += rows + ["", "## Dòng nguồn (nguyên văn)", "", "```", block, "```"]
    return "\n".join(out)


_ID_HEADER = re.compile(
    r"^\s*(?://+|/\*+|\#+|<!--)\s*id:\s*"
    r"(?P<id>[A-Z][A-Z0-9_]*(?:-[A-Z0-9_]+)+)"
    r"(?:\s*\|\s*dd_version:\s*(?P<version>[A-Za-z0-9._]+))?"
)

_VERSION_PARTS = re.compile(r"\d+")


def parse_version(text: str) -> tuple:
    """`v1` → (1,), `v1.2` → (1, 2). Unparseable sorts lowest."""
    return tuple(int(p) for p in _VERSION_PARTS.findall(str(text or ""))) or (-1,)


def version_behind(code: str, design: str) -> bool:
    """True when the code's version is genuinely older than the design's.

    Comparing the tuples directly would call `v1` older than `v1.0`, because a
    shorter tuple sorts first in Python.  The two designate the same version,
    and this corpus mixes both spellings, so the tuples are padded before they
    are compared.
    """
    left, right = parse_version(code), parse_version(design)
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) < right + (0,) * (width - len(right))


def walk_repo(root: Path, extensions: set[str], exclude: ExcludeSet):
    """Walk a code repo, pruning excluded directories instead of filtering after.

    The difference is not cosmetic.  `rglob` descends into a directory before
    anything gets a chance to reject it, so the first `npm install` would turn
    this scan from a few thousand files into hundreds of thousands — and the
    exclude list would be doing its job while the walk still paid the cost.
    """
    for current, dirnames, filenames in os.walk(root):
        here = Path(current)
        rel_dir = to_posix_rel(here, root)
        dirnames[:] = sorted(
            d for d in dirnames
            if not exclude.matches(f"{rel_dir}/{d}/x" if rel_dir != "." else f"{d}/x")
        )
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() not in extensions:
                continue
            path = here / filename
            rel = to_posix_rel(path, root)
            if exclude.matches(rel):
                continue
            yield path, rel


def read_id_header(path: Path, max_lines: int) -> tuple[str, str] | None:
    """First `id:` header within the opening lines of a source file."""
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            for index, line in enumerate(handle):
                if index >= max_lines:
                    return None
                found = _ID_HEADER.match(line)
                if found:
                    return found.group("id"), found.group("version") or ""
    except (OSError, UnicodeDecodeError):
        return None
    return None


def design_version(path: Path) -> str:
    """The design's own current version, from its change-history table.

    That section is metadata rather than specification, so it never becomes a
    node — but the version in its last column is exactly what a code header's
    `dd_version` has to be compared against.  Read as the highest version
    present rather than the bottom row, so the answer does not depend on
    whether the table is kept oldest-first or newest-first.
    """
    try:
        lines = read_text(path).split("\n")
        start, end, _ = find_section(lines, "LỊCH SỬ THAY ĐỔI")
    except (OSError, OkfError, UnicodeDecodeError):
        return ""
    headers, rows = read_table(lines[start:end])
    if not rows:
        return ""
    column = len(headers) - 1
    for index, header in enumerate(headers):
        if "phiên bản" in header or "version" in header:
            column = index
            break
    found = [row[column] for row in rows if column < len(row) and row[column]]
    return max(found, key=parse_version) if found else ""


@adapter("id-header-scan")
def adapter_id_header_scan(name: str, family: dict, ctx: Context):
    """One node per source file carrying a `// id: <UNIT> | dd_version: <v>` header.

    This is the step that closes the loop between specification and code, and it
    is the step with the trap.  A regex written to the backend id shape
    (`[A-Z]+-[A-Z]+-[0-9]+`) runs clean, reports success, and silently drops
    every frontend file, because frontend ids end in a word rather than a number
    and run to four or five segments.  So the pattern is deliberately general
    and the result is reconciled against the WBS unit list, which is the only
    authority on what a unit is.
    """
    wbs_parser = _load_wbs_parser()
    unit_source = ctx.resolve_source(
        family.get("unit_source") or "Stage_2_Architecture/project_wbs.md"
    )
    known = {unit.id for unit in wbs_parser.parse_wbs(unit_source)}

    repos = ctx.config.code_repos
    if not repos:
        raise OkfError(
            f"family {name!r}: no `code_repos` declared in Layer 2. Refusing to "
            "report an empty code index as success."
        )

    extensions = {
        str(e).lower() for e in
        (family.get("extensions") or [".java", ".ts", ".tsx", ".js", ".html", ".scss"])
    }
    max_lines = int(family.get("header_lines", 10))
    repo_min = family.get("repo_min") or {}
    node_type = family.get("type", name)
    per_repo: dict[str, int] = {}
    guard = CaseGuard()

    for repo in repos:
        repo_name = str(repo.get("name") or "")
        repo_root = (ctx.project_root / str(repo.get("path") or "")).resolve()
        if not repo_name:
            ctx.warnings.append(f"{name}: a `code_repos` entry has no `name`")
            continue
        if not repo_root.is_dir():
            # Deliberately not an error: a teammate may have cloned a subset.
            # status.md records the absence and coverage queries refuse to
            # answer, because a missing repo means "unknown", not "not built".
            ctx.warnings.append(f"{name}: repo {repo_name!r} not present at {repo_root}")
            continue

        count = 0
        scanned = 0
        for path, rel in walk_repo(repo_root, extensions, ctx.exclude):
            scanned += 1
            header = read_id_header(path, max_lines)
            if not header:
                # Untagged source: brownfield inventory, not an error. Counted so
                # the ratio is visible per repo rather than inferred by absence.
                continue
            unit_id, version = header
            if unit_id not in known:
                ctx.warnings.append(
                    f"{name}: {repo_name}/{rel} is tagged {unit_id!r}, which the WBS "
                    "does not declare"
                )
                continue

            segments = [safe_id_segment(part) for part in rel.split("/")]
            node_id = f"{name}/{safe_id_segment(repo_name)}/" + "/".join(segments)
            clash = guard.check(node_id)
            if clash:
                ctx.warnings.append(
                    f"{name}: {node_id!r} and {clash!r} differ only by case"
                )
            if len(node_id) > 200:
                ctx.warnings.append(
                    f"{name}: node path is {len(node_id)} characters — close to the "
                    f"Windows MAX_PATH ceiling ({node_id[:60]}…)"
                )

            fields = {
                "type": node_type,
                "title": f"{repo_name}/{rel}",
                "description": f"{path.suffix.lstrip('.')} · {unit_id}",
                # Two-part address on purpose. A code repo is a sibling checkout
                # whose location is a deployment fact, not a fact about the
                # bundle, so a `../../../..` ladder would break on any clone
                # laid out differently. `code_repo` names it; `resource` is the
                # path inside it.
                "code_repo": repo_name,
                "resource": rel,
                "tags": [repo_name, path.suffix.lstrip(".")],
                "sources": [{"resource": f"{repo_name}:{rel}"}],
                "ntapp_unit": unit_id,
                "dd_version": version,
                "size_tokens": ctx.token_estimate(rel),
                "source_sha": sha256_text(read_text(path)),
            }
            fields["content_sha"] = fields["source_sha"]  # node covers the whole file

            body = "\n".join([
                f"# {repo_name}/{rel}", "",
                "| Trường | Giá trị |", "|---|---|",
                f"| Repo | `{repo_name}` |",
                f"| Đường dẫn | `{rel}` |",
                f"| Unit | `{unit_id}` |",
                f"| `dd_version` | `{version or '—'}` |", "",
                "> Node này là **chỉ mục**, không chứa mã nguồn. Đọc mã thì mở",
                f"> `{repo_name}` tại đường dẫn trên.",
            ])
            count += 1
            yield Node(node_id, fields, body)

        per_repo[repo_name] = count
        ctx.stats.setdefault("code_scan", {})[repo_name] = {
            "scanned": scanned, "tagged": count, "untagged": scanned - count,
        }
        floor = repo_min.get(repo_name)
        if isinstance(floor, int) and count < floor:
            raise OkfError(
                f"family {name!r}: repo {repo_name!r} yielded {count} file(s), below "
                f"the declared floor of {floor}. A scan that narrows silently is the "
                "failure this check exists to stop — suspect the pattern, not the code."
            )

    ctx.warnings.append(
        "quét code: " + ", ".join(f"{k}={v}" for k, v in sorted(per_repo.items()))
    )


@adapter("table-rows")
def adapter_table_rows(name: str, family: dict, ctx: Context):
    """One node per row of a declared markdown table.

    The node body carries the row **verbatim**, not a paraphrase.  A card that
    said "paginated envelope" instead of the actual field list would hide
    exactly the field-level drift these nodes exist to expose.
    """
    master = ctx.resolve_source(family.get("source") or "")
    text = read_text(master)
    file_sha = sha256_text(text)
    lines = text.split("\n")

    start, end, heading = find_section(lines, family.get("section", ""))
    headers, rows = read_table(lines[start:end])
    if not headers:
        raise OkfError(f"family {name!r}: no markdown table under section {heading!r}")

    id_column = int(family.get("id_column", 0))
    node_type = family.get("type", name)
    id_pattern = family.get("id_pattern")
    seen: set[str] = set()
    guard = CaseGuard()

    for cells in rows:
        raw_id = cells[id_column] if id_column < len(cells) else ""
        if not raw_id or (id_pattern and not re.fullmatch(str(id_pattern), raw_id)):
            continue
        if raw_id in seen:
            ctx.warnings.append(f"{name}: duplicate id {raw_id!r} in {heading!r}")
            continue
        seen.add(raw_id)

        pairs = [(headers[i], cells[i]) for i in range(min(len(headers), len(cells)))]
        verbatim = "| " + " | ".join(cells) + " |"
        described = [v for k, v in pairs if k in ("description", "mô tả") and v]
        subject = [v for i, (k, v) in enumerate(pairs) if i != id_column and v][:2]

        segment = safe_id_segment(raw_id)
        clash = guard.check(segment)
        if clash:
            ctx.warnings.append(
                f"{name}: {raw_id!r} and {clash!r} differ only by case — "
                "they would merge into one node on macOS/NTFS"
            )
        node_id = f"{name}/{segment}"
        fields = {
            "type": node_type,
            "title": f"{raw_id} — {' → '.join(subject)}" if subject else raw_id,
            "description": described[0] if described else "",
            "resource": relative_resource(node_id, master, ctx.bundle.root),
            "anchor": anchor_for(heading),
            "anchor_text": heading,
            "tags": [name],
            "sources": [{"resource": relative_resource(node_id, master, ctx.bundle.root)}],
            "size_tokens": ctx.token_estimate(verbatim),
            "source_sha": file_sha,
            "content_sha": sha256_text(verbatim),
        }

        body_lines = [f"# {raw_id}", "", "| Trường | Giá trị |", "|---|---|"]
        body_lines += [f"| {k} | {v or '—'} |" for k, v in pairs]
        body_lines += [
            "", "## Nguyên văn dòng nguồn", "",
            "> Đây là **toàn văn quy phạm**, không phải mô tả. Mọi đối chiếu hợp đồng",
            "> phải đọc dòng này, không đọc phần tóm tắt ở trên.", "",
            "```", verbatim, "```",
        ]
        yield Node(node_id, fields, "\n".join(body_lines))


# ─────────────────────────────────────────────────────────────────────────────
# P4 adapter — splitting long documents at their headings
# ─────────────────────────────────────────────────────────────────────────────

_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def iter_headings(text: str):
    """Every ATX heading outside a fenced block, as (level, title, line_index).

    Fence tracking is not decoration: a DD's §3 routinely contains a code block
    holding SQL comments or a shell prompt, and `# something` inside one is not
    a heading.  Counting it would split a section in half and hand the second
    half a title that never appears in the master, so the anchor would never
    resolve.
    """
    fence: str | None = None
    for index, line in enumerate(text.split("\n")):
        marker = _FENCE.match(line)
        if marker:
            token = marker.group(1)[0]
            if fence is None:
                fence = token
            elif token == fence:
                fence = None
            continue
        if fence is not None:
            continue
        found = _HEADING.match(line)
        if found:
            yield len(found.group(1)), found.group(2).strip(), index


def split_sections(text: str, levels: set[int]) -> list[dict]:
    """Partition a document into sections at the declared heading levels.

    A section ends at the next heading that is *either* at a split level or
    shallower than this one.  Both halves of that rule are load-bearing:

    - stopping only at split levels would let an H2 node swallow its own H3
      children when both levels are declared, so the same paragraph would live
      in two nodes and the graph would double-count the corpus;
    - stopping at *any* heading would strand the prose under an H4 in no node
      at all.

    Together they make the sections a true partition of the document: every line
    below the first split heading belongs to exactly one section.
    """
    lines = text.split("\n")
    marks = list(iter_headings(text))
    sections: list[dict] = []
    for position, (level, title, start) in enumerate(marks):
        if level not in levels:
            continue
        end = len(lines)
        for follow_level, _, follow_start in marks[position + 1:]:
            if follow_level in levels or follow_level < level:
                end = follow_start
                break
        # The outline spans the heading's *semantic* extent, which reaches past
        # the end of its own text when the deeper level is also being split.
        # Without this an H2 container in a `[2, 3]` family gets an empty card:
        # its text stops at its first H3, so it would list no children and read
        # as though the document said nothing under it.
        scope_end = len(lines)
        for follow_level, _, follow_start in marks[position + 1:]:
            if follow_level <= level:
                scope_end = follow_start
                break
        inner = [
            (deep_level, deep_title)
            for deep_level, deep_title, deep_start in marks
            if start < deep_start < scope_end and deep_level > level
        ]
        sections.append({
            "level": level,
            "title": title,
            "start": start,
            "end": end,
            "text": "\n".join(lines[start:end]).strip("\n"),
            "subsections": inner,
            "okf_id": declared_section_id(lines[start + 1:end]),
        })
    return sections


_SECTION_ID = re.compile(r"^\s*<!--\s*okf-id:\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*-->\s*$")


def declared_section_id(body_lines: list[str]) -> str:
    """A stable id the document declares for itself, if it declares one.

    Matching a section by its heading text is a measurement, not a guarantee:
    the heading is editorial prose, and the day someone rewords it the node is
    reborn under a new path with every edge to it broken.  The framework's own
    templates therefore emit `<!-- okf-id: … -->` under each fixed heading, so
    artifacts generated from now on carry an identity that survives a rename.
    Title matching stays as the fallback for the existing inventory, and the
    fragile surface shrinks as documents are regenerated instead of growing
    with the corpus.
    """
    for line in body_lines[:3]:
        if not line.strip():
            continue
        found = _SECTION_ID.match(line)
        return found.group(1) if found else ""
    return ""


_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# Only `*` and backtick. Stripping `_` would rewrite `INV_techspec.md` into
# `INVtechspec.md` — a filename that does not exist — and `source_note` is
# precisely where the master names its own sources.
_INLINE_NOISE = re.compile(r"[*`]+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def strip_inline(text: str) -> str:
    return _INLINE_NOISE.sub("", _LINK.sub(r"\1", str(text))).strip()


def fold(text: str) -> str:
    """Case- and composition-insensitive form, for matching prose from config."""
    return unicodedata.normalize("NFC", str(text)).casefold()


_BULLET = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
_LEAD_LABEL = re.compile(r"^\s*\*\*[^*\n]{1,60}\.\*\*\s*(?=\S)")


def first_sentence(body: str, max_len: int = 240, drop_lead_label: bool = False) -> str:
    """The section's opening sentence — deterministic, never a model summary.

    Sections here open in three shapes: prose, a blockquote lede, or straight
    into a table.  The first two carry a real sentence; the third does not, and
    inventing one for it would put a machine's paraphrase where the frontmatter
    contract promises text a person wrote.  So a table-first section gets its
    first row instead, which is still the master's own words.
    """
    fence: str | None = None
    block: list[str] = []
    kind = ""
    for line in body.split("\n"):
        marker = _FENCE.match(line)
        if marker:
            token = marker.group(1)[0]
            fence = token if fence is None else (None if token == fence else fence)
            if block:
                break
            continue
        if fence is not None:
            continue
        stripped = line.strip()
        # A heading ends the search outright. The lede of a section is the
        # section's own opening block; borrowing prose from a subsection would
        # describe the wrong thing, and it would do so plausibly.
        if _HEADING.match(line):
            break
        if not stripped or stripped.startswith("<!--"):
            if block:
                break
            continue
        if set(stripped) <= {"-", "=", "*", " "} and len(stripped) > 2:
            if block:
                break
            continue
        here = "table" if stripped.startswith("|") else "prose"
        if block and here != kind:
            break
        kind = here
        if here == "table":
            cells = split_row(stripped)
            if is_separator_row(cells):
                continue
            if not block:
                block.append(" · ".join(c for c in cells if c))
            continue
        # A bullet marker is `-`/`*`/`+` *followed by a space*. `lstrip("-*+ ")`
        # cannot tell one from the opening `**` of a bold run, so it ate the
        # emphasis off every line that began with one — which is also why the
        # lead-label rule below could never see the label it was written for.
        block.append(_BULLET.sub("", stripped.lstrip("> ")))

    raw = " ".join(block)
    # A bolded lead-in label ending in a period — `**Mục đích chính.** <prose>` —
    # terminates the sentence split by itself, so the description comes out as
    # the label alone.  Whether that is a bug depends entirely on the family, so
    # it is opt-in and off by default.  Measured both ways on this corpus: the 13
    # service documents all open on the *same* boilerplate label, and dropping it
    # is the only way their cards differ from one another; but in the 663 P4
    # section nodes the bolded label is usually the tightest summary anybody
    # wrote — `**Verdict (Step 01): Module STATEFUL.**` beats the paragraph that
    # follows it — and dropping it there made 3 of 4 sampled nodes worse.
    if drop_lead_label:
        found = _LEAD_LABEL.match(raw)
        if found:
            raw = raw[found.end():]
    text = strip_inline(raw)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    return clip(_SENTENCE_END.split(text, maxsplit=1)[0].strip(), max_len)


def clip(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0].rstrip(",;:-") + "…"


def outline_description(subsections: list, max_len: int = 240) -> str:
    """What a section is about when it opens straight into its first subheading.

    Measured on the paybiz corpus: 35% of sections have no lede at all — §4 of a
    detailed design goes from its own heading to `### 4.1` with nothing in
    between.  Leaving those blank costs the card its whole scanning value, and
    writing a summary would be a machine paraphrase sitting in a field the
    contract says carries the master's words.  An inventory of the subheadings
    is neither: it is a count and a list, quoted from the document.
    """
    if not subsections:
        return ""
    names = [strip_inline(title) for _, title in subsections[:4]]
    tail = "; …" if len(subsections) > 4 else ""
    return clip(f"{len(subsections)} mục con: " + "; ".join(names) + tail, max_len)


_BLOCKQUOTE_FIELD = re.compile(r"\*\*([^*:]+):\*\*\s*(.+?)(?=\s+·\s+\*\*|$)")

# The same field, written without the bold.  `> Nguồn: HLD §3.1.3` and
# `> **Nguồn:** HLD §3.1.3` say the same thing; only the first was being read,
# and the miss was silent.  Measured on the corpus: `architecture_design.md`
# declares its source in the plain form on line 5, so all 47 `hld-section`
# nodes carried `source_note: ""` purely because of two asterisks.
#
# Deliberately *not* folded into `_BLOCKQUOTE_FIELD`: that pattern is also used
# by `block_fields`, which builds a dict of every label it finds.  Widening it
# there would let ordinary prose (`> Lưu ý: …`) become a field.  Here the risk
# is nil — `doc_meta` consumes four known keys and discards the rest — so the
# plain form is tried only as a fallback, and only in this function.
_PLAIN_BLOCKQUOTE_FIELD = re.compile(r"^([^*:]{1,40}):\s*(.+)$")

_BACKTICKED = re.compile(r"`([^`]+)`")


def doc_meta(text: str) -> dict:
    """Document-level metadata, from whichever of the two shapes this file uses.

    Measured on the paybiz corpus: of 54 detailed designs, 22 carry YAML
    frontmatter, 21 carry a `> **Unit:** …` blockquote, 1 carries both, and
    **12 carry neither**.  So neither shape can be the identity of the node —
    only the filename covers all 54, and it is already the contract the
    `wbs-unit` family resolves `design_doc` through.  This function supplies the
    *extra* facts (module, slice, parents) and leaves identity to the caller.
    """
    fields, body = split_frontmatter(text)
    meta: dict = {"unit": "", "module": "", "slice": "", "version": "",
                  "parents": [], "note": ""}

    def first_token(value) -> str:
        return str(value or "").strip().split()[0].strip("`,;") if str(value or "").strip() else ""

    meta["unit"] = str(fields.get("id") or "").strip()
    meta["module"] = first_token(fields.get("module") or fields.get("module_name"))
    meta["slice"] = first_token(fields.get("slice"))
    meta["version"] = str(fields.get("version") or fields.get("dd_version") or "").strip()
    # `inputDocuments` is the same fact under a third spelling.  `ux_design.md`
    # declares ten upstream documents there — the richest provenance block in the
    # corpus — and all 71 `ux-section` nodes were shipping `sources: [itself]`
    # because nobody had taught this function the key.  From the extractor's side
    # that is indistinguishable from a document that declares nothing, which is
    # the more dangerous of the two readings.
    for key in ("parent_techspec", "inherits_from", "inputDocuments"):
        value = fields.get(key)
        if isinstance(value, list):
            meta["parents"].extend(str(v).strip() for v in value)
        elif value:
            meta["parents"].append(str(value).strip())

    head = "\n".join(body.split("\n")[:40])
    for line in head.split("\n"):
        if not line.lstrip().startswith(">"):
            continue
        content = line.lstrip().lstrip(">").strip()
        pairs = _BLOCKQUOTE_FIELD.findall(content)
        if not pairs:
            plain = _PLAIN_BLOCKQUOTE_FIELD.match(content)
            if plain:
                pairs = [(plain.group(1), plain.group(2))]
        for label, value in pairs:
            key = slugify(label)
            value = value.strip().rstrip("·").strip()
            if key == "unit" and not meta["unit"]:
                meta["unit"] = strip_inline(value).split()[0] if value else ""
            elif key == "module" and not meta["module"]:
                meta["module"] = first_token(strip_inline(value))
            elif key == "slice" and not meta["slice"]:
                meta["slice"] = first_token(strip_inline(value))
            elif key == "nguon":
                meta["note"] = value
    return meta


def resolve_named_source(name: str, index: dict) -> str:
    """A bare filename → a real path, but only when the answer is unambiguous.

    The `Nguồn:` line names files without paths (`INV_techspec.md`).  Guessing a
    path for a name that matches two files would write a `sources[]` entry
    pointing at a document nobody cited — a fabricated provenance claim, which
    is worse than no claim.  Ambiguous and unknown names stay in `source_note`
    as the master's own words.
    """
    hits = index.get(Path(name).name.lower()) or []
    return hits[0] if len(hits) == 1 else ""


def build_name_index(root: Path, exclude: ExcludeSet, project_root: Path) -> dict:
    index: dict[str, list[str]] = {}
    for current, dirnames, filenames in os.walk(root):
        here = Path(current)
        rel_dir = to_posix_rel(here, project_root)
        dirnames[:] = sorted(
            d for d in dirnames if not exclude.matches(f"{rel_dir}/{d}/x")
        )
        for filename in filenames:
            if not filename.lower().endswith(".md"):
                continue
            rel = to_posix_rel(here / filename, root)
            if exclude.matches(to_posix_rel(here / filename, project_root)):
                continue
            index.setdefault(filename.lower(), []).append(rel)
    return index


_ADR_REF = re.compile(r"\bADR[\s-]*(\d{2,5})\b", re.IGNORECASE)


def adr_index(ctx: Context, name: str, family: dict) -> dict:
    """ADR number → node id, merged across every ADR series projected this run.

    The width is load-bearing, not decoration.  This corpus runs two series at
    once: `designed-adr`, the Stage 1 series in `Stage_1_Discovery/adr/` numbered
    `0001`…`0007` (four digits), and `runtime-adr`, the series that emerged later
    as `ADR-001`…`ADR-005` in `architecture_design.md` §6 (three digits).  The
    document says so in its own words — "Hai chuỗi ADR song song — đừng nhầm số
    hiệu" — and in running prose the width is the only thing telling them apart.

    Which is what makes the merge safe: the index is keyed by the literal digit
    string, so `"001"` and `"0001"` are already different keys routing to
    different families.  `governed_from` did not change when the second series
    was added; only what fills this dict did.
    """
    declared = family.get("adr_refs")
    if not declared:
        return {}
    if not ctx.adr_series_seen:
        # A consumer asked for ADR edges and no series projected this run — the
        # usual cause is `--only <consumer>`.  Saying so beats the alternative,
        # which is a stray warning claiming every ADR in the corpus is unknown.
        ctx.warnings.append(
            f"{name}: khai `adr_refs` nhưng không họ `adr_series` nào chiếu "
            "trong lần chạy này (thường do `--only`). Bỏ qua cạnh `governed_by` "
            "cho lần chạy này — KHÔNG phải là ADR đã biến mất."
        )
        return {}
    # `adr_refs: true` means every series; `adr_refs: [designed-adr]` means only
    # those.  The list form is how stage ordering gets stated: a `runtime-adr` is
    # constrained by the Stage 1 decisions it was taken under, but nothing at
    # Stage 1 can be governed by something decided after it.  Naming the series
    # keeps that edge pointing backwards in time instead of both ways.
    allowed: set[str] | None = None
    if isinstance(declared, (list, tuple, set)):
        allowed = {str(item) for item in declared}
        unknown = allowed - set(ctx.adr_series_seen)
        if unknown:
            raise OkfError(
                f"family {name!r}: adr_refs names {sorted(unknown)!r}, which "
                "declares no `adr_series`. Declared series this run: "
                f"{sorted(ctx.adr_series_seen)!r}"
            )
    resolvable = {key: value for key, value in ctx.adr_by_number.items()
                  if key not in ctx.adr_ambiguous}
    by_number = {key: value for key, value in resolvable.items()
                 if allowed is None or ctx.adr_owner.get(key) in allowed}
    # `known` is every number any series claims, `by_number` only the ones this
    # family follows.  The gap between them is a reference the family declined on
    # purpose — `runtime-adr` naming its own `ADR-001` in its own heading — and
    # declining is not the same as failing to recognise.  Reporting the gap as a
    # stray told the operator all five runtime ADRs were unknown numbers.
    return {"by_number": by_number, "known": set(resolvable),
            "widths": {len(k) for k in by_number}}


def adr_digits(key: str) -> str:
    """The digit run inside an ADR key, whatever decoration surrounds it.

    `0004-tach-den-han` and `ADR-004` both reduce to their number, so a series
    may name its keys however its source names them.
    """
    found = re.search(r"(\d{2,5})", str(key or ""))
    return found.group(1) if found else ""


def register_adr_series(ctx: Context, name: str, family: dict,
                        produced: list) -> None:
    """Record an ADR series' real node ids, taken from the nodes it just emitted.

    Deliberately not derived from the config a second time.  An index built by
    re-globbing `adr_dir` and re-deriving slugs is a *prediction* of what the
    adapter will produce, and predictions drift — the first version of this code
    hardcoded the family name `adr/` into the id it predicted, which quietly
    became wrong the moment the family was renamed.  Reading `produced` means
    the index and the nodes cannot disagree, because they are the same objects.

    Width is the discriminator between series (see `governed_from`), so two
    series sharing a width is the one arrangement this cannot resolve.  That is
    recorded in `adr_ambiguous` and routed nowhere, rather than guessed at.
    """
    key_field = str(family.get("key_field") or "")
    fresh: set[str] = set()
    for node in produced:
        digits = adr_digits(node.fields.get(key_field) if key_field else "")
        if not digits:
            continue
        owner = ctx.adr_owner.get(digits)
        if owner and owner != name:
            ctx.adr_ambiguous.add(digits)
            fresh.add(digits)
            continue
        ctx.adr_owner[digits] = name
        ctx.adr_by_number[digits] = node.node_id
    ctx.adr_series_seen.append(name)

    if fresh:
        listed = ", ".join(sorted(fresh)[:8]) + ("…" if len(fresh) > 8 else "")
        other = ", ".join(sorted(set(ctx.adr_series_seen) - {name}))
        ctx.warnings.append(
            f"{name}: {len(fresh)} số ADR bị nhận bởi CẢ `{other}` ({listed}). "
            "Bề rộng số là thứ duy nhất phân biệt các chuỗi ADR trong văn xuôi, "
            "nên hai chuỗi cùng bề rộng KHÔNG phân giải được. Không sinh cạnh "
            "`governed_by` cho những số này — hãy đổi bề rộng của một chuỗi."
        )


@adapter("heading-split")
def adapter_heading_split(name: str, family: dict, ctx: Context):  # noqa: C901
    """One node per heading, at the levels this family declares.

    `split_level` is a *list* because the corpus does not split at one depth.
    Measured: `architecture_design.md` is 21 H2 + 27 H3 and `ux_design.md` is
    18 H2 + 55 H3, while every detailed design and techspec splits cleanly at
    H2.  Declaring a single level for the first two would yield 21 and 18 nodes,
    drop 82 sections, and report success — which is why `min_nodes` is the
    companion of this field and not an optional extra.
    """
    levels = family.get("split_level") or [2]
    if isinstance(levels, int):
        levels = [levels]
    levels = {int(level) for level in levels}

    pattern = family.get("source_glob")
    if pattern:
        masters = ctx.iter_sources(str(pattern))
    else:
        masters = [ctx.resolve_source(str(family.get("source") or ""))]
    if not masters:
        raise OkfError(f"family {name!r}: source pattern matched no file")

    key_from = family.get("key_from")
    key_regex = re.compile(str(key_from)) if key_from else None
    key_field = str(family.get("key_field") or "")
    node_type = family.get("type", name)
    # Compared after NFC + casefold: the corpus mixes composed and decomposed
    # Vietnamese, so a plain `.lower()` substring test would match on one
    # machine and miss on another — and missing means the change-log section
    # quietly becomes a node instead of being skipped.
    skip = [fold(s) for s in (family.get("skip_headings") or [])]
    adrs = adr_index(ctx, name, family)
    strays: set[str] = set()
    names = build_name_index(ctx.output_folder, ctx.exclude, ctx.project_root)

    guard = CaseGuard()
    skipped = 0
    produced = 0

    for master in masters:
        text = read_text(master)
        file_sha = sha256_text(text)
        meta = doc_meta(text)

        key = ""
        if key_regex:
            found = key_regex.match(master.name)
            if not found:
                raise OkfError(
                    f"family {name!r}: {master.name!r} does not match "
                    f"key_from={key_from!r} — the glob is selecting files this "
                    "family was not written for"
                )
            key = found.group(1)
            if meta["unit"] and meta["unit"] != key:
                ctx.warnings.append(
                    f"{name}: {master.name} khai `id: {meta['unit']}` nhưng tên file "
                    f"nói {key!r} — tên file thắng (đó là khoá `design_doc` tra ra)"
                )

        parents = []
        for parent in meta["parents"]:
            candidate = ctx.project_root / parent
            if candidate.is_file():
                parents.append(candidate.resolve())
            else:
                # Dropping it is right — an unresolvable path must not become a
                # `sources[]` entry.  Dropping it *silently* is what was wrong:
                # a declared upstream that does not exist is a defect in the
                # document, and staying quiet makes it look like the document
                # never declared one.  Naming it is the whole difference.
                ctx.warnings.append(
                    f"{name}: {master.name} khai nguồn `{parent}` nhưng không "
                    "phân giải ra file — bỏ khỏi `sources[]`. Sai đường dẫn "
                    "trong tài liệu, KHÔNG phải nguồn biến mất."
                )
        if meta["note"]:
            for named in _BACKTICKED.findall(meta["note"]):
                hit = resolve_named_source(named, names)
                if hit:
                    parents.append((ctx.output_folder / hit).resolve())
        parents = list(dict.fromkeys(parents))

        prefix = f"{name}/{safe_id_segment(key)}" if key else name
        taken: set[str] = set()
        sections = split_sections(text, levels)
        if not sections:
            ctx.warnings.append(
                f"{name}: {master.name} có 0 heading ở mức {sorted(levels)}"
            )

        for section in sections:
            title = section["title"]
            if any(needle in fold(title) for needle in skip):
                skipped += 1
                continue

            declared = section["okf_id"]
            slug = (unique_slug(safe_id_segment(declared), taken) if declared
                    else unique_slug(slugify(title), taken))
            clash = guard.check(f"{prefix}/{slug}")
            if clash:
                ctx.warnings.append(
                    f"{name}: {prefix}/{slug} và {clash} chỉ khác nhau ở chữ hoa/thường"
                )
            node_id = f"{prefix}/{slug}"
            resource = relative_resource(node_id, master, ctx.bundle.root)

            sources = [{"resource": resource}]
            for parent in parents:
                sources.append(
                    {"resource": relative_resource(node_id, parent, ctx.bundle.root)}
                )

            tags = [name]
            for extra in (meta["module"], meta["slice"]):
                if extra and extra not in tags:
                    tags.append(extra)

            governed = governed_from(section["text"], adrs, node_id, strays)

            fields = {
                "type": node_type,
                "title": f"{key} — {title}" if key else title,
                "description": (
                    first_sentence("\n".join(section["text"].split("\n")[1:]))
                    or outline_description(section["subsections"])
                ),
                "resource": resource,
                "anchor": anchor_for(title),
                "anchor_text": title,
                "tags": tags,
                "sources": sources,
                # `generated` is stamped by the writer, not here: `by` answers
                # "who ran this", which is the actor, and the actor is what
                # separates a deterministic pass from P5's model pass.
                "heading_level": section["level"],
                "size_tokens": ctx.token_estimate(section["text"]),
                "source_sha": file_sha,
                "content_sha": sha256_text(section["text"]),
            }
            if declared:
                fields["section_id"] = declared
            if key and key_field:
                fields[key_field] = key
            if meta["module"]:
                fields["ntapp_module"] = meta["module"]
            if meta["slice"]:
                fields["slice_key"] = meta["slice"]
            if meta["version"]:
                fields["doc_version"] = meta["version"]
            if meta["note"]:
                fields["source_note"] = strip_inline(meta["note"])[:400]
            if section["subsections"]:
                fields["subsections"] = [
                    clip(strip_inline(sub_title), 90)
                    for _, sub_title in section["subsections"][:20]
                ]
            if governed:
                fields["governed_by"] = governed

            produced += 1
            yield Node(node_id, fields, _section_body(fields, section, master.name))

    report_adr_strays(name, adrs, strays, ctx)
    ctx.stats.setdefault("heading_split", {})[name] = {
        "files": len(masters), "nodes": produced, "skipped": skipped,
        "headings": produced + skipped,
    }
    ctx.warnings.append(
        f"{name}: {len(masters)} file → {produced + skipped} heading "
        f"= {produced} node + {skipped} bỏ qua"
    )


def _section_body(fields: dict, section: dict, filename: str) -> str:
    """The card — a pointer with a cost estimate, never the section itself.

    Copying the section in would defeat the whole exercise: §4 of a detailed
    design is around 10k tokens, so a bundle of 731 such copies costs more to
    read than the 71 documents it was built from.  The card exists to let a
    reader decide *whether* to pay that cost, so it carries the size, the
    outline, and the exact heading line to resolve against — and nothing that
    could be mistaken for the specification itself.
    """
    lines = [
        f"# {fields['title']}", "",
        f"> **Thẻ chỉ mục — không phải đặc tả.** Nội dung quy phạm nằm ở "
        f"`{filename}`, mục dưới đây. Mọi quyết định phải resolve và đọc nguyên văn.",
        "", "| Trường | Giá trị |", "|---|---|",
        f"| Tài liệu | `{filename}` |",
    ]
    for label, key in (("Unit", "ntapp_unit"), ("Module", "ntapp_module"),
                       ("Slice", "slice_key"), ("Phiên bản tài liệu", "doc_version")):
        if fields.get(key):
            lines.append(f"| {label} | `{fields[key]}` |")
    lines += [
        f"| Mức heading | H{section['level']} |",
        f"| Chi phí đọc | ~{fields['size_tokens']:,} token |".replace(",", "."),
    ]
    if fields.get("subsections"):
        lines += ["", "## Mục con", ""]
        lines += [f"- {sub}" for sub in fields["subsections"]]
    lines += [
        "", "## Neo resolve", "",
        "Dòng heading nguyên văn trong master — tìm đúng chuỗi này:", "",
        "```", "#" * section["level"] + " " + section["title"], "```",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# P3 — concepts the corpus already stores one per file (or one per clean block)
#
# Nothing here cuts a document up.  These four adapters exist because part of
# the corpus is *already* at the right granularity, so the only work left is to
# give each concept an identity, a reading cost, and its edges.
# ─────────────────────────────────────────────────────────────────────────────

def family_has_source(ctx: Context, family: dict) -> bool:
    """Is this family's declared source on disk yet?

    Read by the one caller that honours `allow_missing_source`, so that a family
    belonging to a stage the project has not reached can be declared up front
    without breaking the run.  A missing source is normally fatal — it almost
    always means a moved file or a typo, and skipping it would be the silently
    narrowed scan the projector refuses everywhere else.  The exception has to
    be asked for per family, in writing, and it is reported when it fires.

    Every source-bearing key is checked, not just `source`: `id-header-scan`
    reads `unit_source` and `slice-manifest` reads `slice_dir`, so a check
    written against `source` alone would call those two present on an empty
    project and hand the adapter nothing to open.

    `id-header-scan` reads a second half that is not a path at all — the repo
    list in `code_repos`.  Its adapter rightly refuses to call an empty code
    index a success, so without this the family would go from "pending" to
    "fatal" the moment the WBS landed, which on a new project is Stage 2: far
    too early to have tagged any code.  No repos declared means nothing to
    read, which is the same pending state as a file that is not there yet.
    """
    if family.get("adapter") == "id-header-scan" and not ctx.config.code_repos:
        return False

    patterns = family.get("source_glob")
    if patterns:
        if isinstance(patterns, str):
            patterns = [patterns]
        return any(ctx.iter_sources(str(pattern)) for pattern in patterns)
    for key in ("source", "unit_source"):
        rel = family.get(key)
        if rel and not (ctx.output_folder / str(rel)).exists():
            return False
    slice_dir = family.get("slice_dir")
    if slice_dir and not (ctx.output_folder / str(slice_dir)).is_dir():
        return False
    return True


def family_sources(ctx: Context, name: str, family: dict) -> list[Path]:
    """Expand `source` / `source_glob`, where `source_glob` may be a list.

    A list, because a slice set is flat for the first feature and nested under a
    feature directory from the second one on (§3.5), and during the changeover
    both layouts are live at once.  Forcing a single pattern would mean either
    migrating the existing feature's 271 path references or accepting a silent
    blind spot over the new one.
    """
    patterns = family.get("source_glob")
    if patterns:
        if isinstance(patterns, str):
            patterns = [patterns]
        seen: set = set()
        files: list[Path] = []
        for pattern in patterns:
            for path in ctx.iter_sources(str(pattern)):
                key = path.resolve()
                if key not in seen:
                    seen.add(key)
                    files.append(path)
        files.sort()
    else:
        files = [ctx.resolve_source(str(family.get("source") or ""))]
    if not files:
        declared = family.get("source_glob") or family.get("source")
        raise OkfError(f"family {name!r}: source pattern matched no file — {declared!r}")
    return files


def doc_title(text: str, fallback: str = "") -> str:
    """The document's own name: frontmatter `title:`, else its H1."""
    fields, body = split_frontmatter(text)
    declared = str(fields.get("title") or "").strip()
    if declared:
        return strip_inline(declared)
    for level, title, _ in iter_headings(body):
        if level == 1:
            return strip_inline(title)
    return fallback


def doc_outline(text: str, levels: set[int], skip: list[str]) -> list[tuple[int, str]]:
    _, body = split_frontmatter(text)
    return [
        (level, title)
        for level, title, _ in iter_headings(body)
        if level in levels and not any(needle in fold(title) for needle in skip)
    ]


# A run of `**Label:** value` pairs is a document header, not a description.
_META_PAIR = re.compile(r"\*\*[^*:]+:\*\*")
# A whole line that is only a label, e.g. `**Mô tả:**`.
_LABEL_LINE = re.compile(r"^\*{0,2}([^*:\n]{1,60}):\*{0,2}$")


def doc_lede(text: str, max_len: int = 240, drop_lead_label: bool = False) -> str:
    """The document's opening prose — its own words, never a machine summary.

    Skips a leading metadata block.  Measured: all 13 service documents open on
    `> **Phiên bản:** 1.0 — **Ngày tạo:** … — **Repo:** …`, which is a header.
    Letting it through would make all 13 cards read identically in a listing,
    which is the one thing a description exists to prevent.  Two or more
    `**Label:** value` pairs in a block is that header; one is a normal sentence.
    """
    _, body = split_frontmatter(text)
    lines = body.split("\n")
    start = 0
    for index, line in enumerate(lines):
        found = _HEADING.match(line)
        if found and len(found.group(1)) == 1:
            start = index + 1
            break
    rest = lines[start:]
    while True:
        while rest and not rest[0].strip():
            rest.pop(0)
        end = 0
        while end < len(rest) and rest[end].strip():
            end += 1
        block = rest[:end]
        if not block or _HEADING.match(block[0]):
            return ""
        # A block that is nothing but a label (`**Mô tả:**` on its own line)
        # describes the block after it, not itself.
        if len(block) == 1 and _LABEL_LINE.match(block[0].strip()):
            rest = rest[end:]
            continue
        if len(_META_PAIR.findall(" ".join(block))) >= 2:
            rest = rest[end:]
            continue
        return first_sentence("\n".join(block), max_len, drop_lead_label)


def section_lede(text: str, heading_match: str, max_len: int = 240,
                 drop_lead_label: bool = False) -> str:
    """First sentence of a named section, or "" when there is no such heading."""
    _, body = split_frontmatter(text)
    lines = body.split("\n")
    try:
        start, end, _ = find_section(lines, heading_match)
    except OkfError:
        return ""
    return first_sentence("\n".join(lines[start + 1:end]), max_len, drop_lead_label)


def describe_doc(text: str, family: dict, fields: dict, outline: list) -> str:
    """Description, in the order the family declares — never invented.

    Four sources, each of them the document's own words: a named frontmatter
    field, the first sentence of a named section, the opening prose, and finally
    an inventory of the headings.  A whole-file node with no description is a
    card that cannot be scanned, and inventing prose for it would put a machine
    paraphrase in the one field the contract reserves for a person's.
    """
    drop_label = bool(family.get("description_drop_label"))
    key = family.get("description_field")
    if key:
        value = str(fields.get(str(key)) or "").strip()
        if value:
            return clip(strip_inline(value), 240)
    section = family.get("description_section")
    if section:
        found = section_lede(text, str(section), drop_lead_label=drop_label)
        if found:
            return found
    return (doc_lede(text, drop_lead_label=drop_label)
            or outline_description(outline))


def report_adr_strays(name: str, adrs: dict, strays: set, ctx: Context,
                      own: set | None = None) -> None:
    """One line per family for ADR numbers that match no declared series.

    Not silence, and not an error.  Silence is what let 27 wrong edges through.
    An error would be wrong too: a document is allowed to write `ADR-0042` about
    a decision nobody ever filed.  What matters is that the count stays visible,
    so nobody has to rediscover the problem by reading edges one at a time.

    What a stray means under the two-series model: the number matched neither
    series' width, so it is a typo or a *third* series nobody declared.  Both are
    worth one line.  A number that resolves to the wrong series is the failure
    this cannot catch, which is why width is checked and not just value.
    """
    # A series does not report its own numbering as unknown.  It cannot see
    # itself through `adr_index` — a family registers the numbers it owns only
    # *after* it has finished producing, so while `runtime-adr` is running, the
    # index holds `designed-adr` alone.  Without this, all five runtime ADRs were
    # reported as unrecognised numbers, by the very family that defines them.
    if own:
        strays = set(strays) - own
    # An empty index means no series projected, so every mention is a "stray"
    # and the warning would be pure noise.  `--only <consumer>` is the usual way
    # in; `adr_index` has already said so in that case.
    if not strays or not adrs.get("widths"):
        return
    widths = ", ".join(f"{w} chữ số" for w in sorted(adrs["widths"]))
    listed = ", ".join(sorted(strays)[:8]) + ("…" if len(strays) > 8 else "")
    ctx.warnings.append(
        f"{name}: {len(strays)} số ADR được nhắc mà không thuộc chuỗi nào đã "
        f"khai ({listed}). Các chuỗi hiện có dùng {widths}; số khác bề rộng "
        "không phân giải được nên KHÔNG sinh cạnh `governed_by`. Hoặc là gõ "
        "nhầm, hoặc là một chuỗi ADR chưa được khai `adr_series`."
    )


def governed_from(section_text: str, adrs: dict, self_id: str = "",
                  strays: set | None = None) -> list[str]:
    """ADR ids referenced here, minus the node's own — never self-govern.

    See `report_adr_strays` for what happens to the ones that do not match.

    Matched on the *width* of the number, against the widths the ADR files on
    disk actually use.  Matching on the value alone mapped the Stage 2 series
    `ADR-001` onto the Stage 1 file `adr/0001-…`, which records a different
    decision entirely: 27 such edges existed across 25 nodes, and every one of
    them read as perfectly reasonable — the node for `ADR-001: Nâng
    invoice-service lên Java 17` claimed to be governed by `0001-sua-hoa-don-da
    -phat-hanh-tai-cho`.

    A reference whose width matches no file is *not* silently dropped: it goes
    into `strays` so the caller can report it, because it is either a second
    series or a typo, and both are worth knowing.
    """
    by_number = adrs.get("by_number") or {}
    known = adrs.get("known") or set(by_number)
    widths = adrs.get("widths") or set()
    hits: set[str] = set()
    for raw in _ADR_REF.findall(section_text):
        target = by_number.get(raw) if len(raw) in widths else None
        if target is not None:
            if target != self_id:
                hits.add(target)
        elif raw not in known and strays is not None:
            strays.add(raw)
    return sorted(hits)


def carry_declared(family: dict, source: dict, target: dict) -> None:
    """Copy `carry_fields: {<source key>: <node field>}` verbatim, when present.

    Verbatim on purpose: interpreting a value here would put the projector in
    the business of deciding what a document meant, and every such decision is
    a place where the graph can quietly disagree with the source it cites.
    """
    for src_key, dst_key in (family.get("carry_fields") or {}).items():
        value = source.get(str(src_key))
        if value not in (None, "", [], {}):
            target[str(dst_key)] = value


def _pointer_card(title: str, filename: str, rows: list[tuple[str, str]],
                  outline: list, extra: list[str] | None = None) -> str:
    """The card — a pointer with a cost estimate, never the document itself."""
    lines = [
        f"# {title}", "",
        f"> **Thẻ chỉ mục — không phải bản gốc.** Nội dung quy phạm nằm ở "
        f"`{filename}`. Mọi quyết định phải mở file đó và đọc nguyên văn.",
        "", "| Trường | Giá trị |", "|---|---|",
        f"| Tài liệu | `{filename}` |",
    ]
    lines += [f"| {label} | {value} |" for label, value in rows if value]
    if outline:
        lines += ["", "## Bố cục", ""]
        lines += [f"{'  ' * max(0, level - 2)}- {clip(strip_inline(t), 90)}"
                  for level, t in outline[:40]]
    if extra:
        lines += extra
    return "\n".join(lines)


@adapter("whole-file")
def adapter_whole_file(name: str, family: dict, ctx: Context):
    """One node per file, for documents that are already one concept each.

    `size_tokens` here is the cost of the whole document, which is exactly the
    number a reader needs: these files run from 2k to 40k tokens and look
    identical in a directory listing.

    `source_sha` and `content_sha` are deliberately equal.  For a section node
    they differ and the difference is the point; for a whole-file node the
    section *is* the file.  Emitting only one of them would make this family
    fail any consumer check written against the other, and equal is the truth
    here — cheaper than a special case at every reader.
    """
    files = family_sources(ctx, name, family)
    node_type = family.get("type", name)
    levels = family.get("outline_level") or [2]
    if isinstance(levels, int):
        levels = [levels]
    levels = {int(level) for level in levels}
    skip = [fold(s) for s in (family.get("skip_headings") or [])]
    key_from = family.get("key_from")
    key_regex = re.compile(str(key_from)) if key_from else None
    key_field = str(family.get("key_field") or "")
    adrs = adr_index(ctx, name, family)
    strays: set[str] = set()
    own: set[str] = set()
    repo_names = {str(repo.get("name")) for repo in ctx.config.code_repos}
    repo_by_path = {Path(str(repo.get("path", ""))).name: str(repo.get("name"))
                    for repo in ctx.config.code_repos}

    guard = CaseGuard()
    taken: set[str] = set()
    produced = 0
    unlinked: list[str] = []

    for path in files:
        text = read_text(path)
        meta, _ = split_frontmatter(text)
        file_sha = sha256_text(text)

        key = ""
        if key_regex:
            found = key_regex.match(path.name)
            if not found:
                raise OkfError(
                    f"family {name!r}: {path.name!r} does not match "
                    f"key_from={key_from!r} — the glob is selecting files this "
                    "family was not written for"
                )
            key = found.group(1)

        slug = unique_slug(slugify(path.stem), taken)
        clash = guard.check(slug)
        if clash:
            ctx.warnings.append(f"{name}: {slug} và {clash} chỉ khác nhau ở chữ hoa/thường")
        node_id = f"{name}/{slug}"
        resource = relative_resource(node_id, path, ctx.bundle.root)
        outline = doc_outline(text, levels, skip)

        fields = {
            "type": node_type,
            "title": doc_title(text, path.stem),
            "description": describe_doc(text, family, meta, outline),
            "resource": resource,
            "tags": [name],
            "sources": [{"resource": resource}],
            "size_tokens": ctx.token_estimate(text),
            "source_sha": file_sha,
            "content_sha": file_sha,
        }
        if key and key_field:
            fields[key_field] = key
        if key and family.get("adr_series"):
            own.add(adr_digits(key))
        carry_declared(family, meta, fields)

        # A repo name is an edge in waiting, so it may only be written when it
        # actually names a declared repo.  A value that looks like an id but
        # resolves to nothing is worse than no value: it survives review.
        declared_repo = str(fields.get("code_repo") or "").strip()
        if declared_repo:
            resolved = (declared_repo if declared_repo in repo_names
                        else repo_by_path.get(declared_repo, ""))
            if resolved:
                fields["code_repo"] = resolved
            else:
                fields.pop("code_repo")
                unlinked.append(declared_repo)

        governed = governed_from(text, adrs, node_id, strays)
        if governed:
            fields["governed_by"] = governed
        if outline:
            fields["subsections"] = [clip(strip_inline(t), 90) for _, t in outline[:20]]

        rows = [("Mã", f"`{key}`" if key else ""),
                ("Repo", f"`{fields['code_repo']}`" if fields.get("code_repo") else ""),
                ("Chi phí đọc", f"~{fields['size_tokens']:,} token".replace(",", "."))]
        produced += 1
        yield Node(node_id, fields, _pointer_card(fields["title"], path.name, rows, outline))

    report_adr_strays(name, adrs, strays, ctx, own)
    if unlinked:
        # One line, not one per file: this is a single fact about coverage —
        # these repos have a document but no entry in `code_repos`, so nothing
        # in the graph can connect them to code.  Repeating it per file buries
        # the real warnings underneath it on every run.
        ctx.warnings.append(
            f"{name}: {len(unlinked)} repo có tài liệu nhưng chưa khai trong "
            f"`code_repos` ({', '.join(sorted(unlinked))}) — node không mang "
            "`code_repo`, và không có cạnh nào tới code của chúng")
    ctx.stats.setdefault("whole_file", {})[name] = {"files": len(files), "nodes": produced}
    ctx.warnings.append(f"{name}: {len(files)} file → {produced} node")


# ── heading-blocks ───────────────────────────────────────────────────────────

@adapter("heading-blocks")
def adapter_heading_blocks(name: str, family: dict, ctx: Context):
    """One node per heading whose text matches a declared key pattern.

    The filter runs the opposite way round from `heading-split`.  There,
    `skip_headings` is a blacklist — right for a specification, where every
    section is normative unless named otherwise.  A bug log is the reverse: an
    append-only journal that also carries working notes, and on this corpus 3 of
    the 35 H2 headings are `## Ghi chú xử lý — …` entries that are not bugs.  A
    blacklist would need extending every time somebody invents a note heading,
    and its failure mode is a note silently becoming a bug node.  A whitelist
    keyed on the id pattern cannot fail that way.
    """
    files = family_sources(ctx, name, family)
    node_type = family.get("type", name)
    level = int(family.get("level") or 2)
    pattern = family.get("key_pattern")
    if not pattern:
        raise OkfError(f"family {name!r}: heading-blocks requires `key_pattern`")
    key_regex = re.compile(str(pattern))
    key_field = str(family.get("key_field") or "")
    # The key does double duty: it is the node id *and* the value stored in
    # `key_field`.  Those want different shapes when the id carries a prefix —
    # `runtime-adr/adr-001` is a good id, but `adr_number: ADR-001` cannot be
    # compared against `designed-adr`'s `adr_number: 0001`.  `key_strip` splits
    # the two: the id keeps the whole key, the field keeps what survives.
    key_strip = family.get("key_strip")
    strip_regex = re.compile(str(key_strip)) if key_strip else None
    field_map = {str(k): str(v) for k, v in (family.get("field_map") or {}).items()}
    slices = slice_index(ctx, family) if family.get("slice_dir") else None
    owner = family.get("slice_from_key")
    owner_regex = re.compile(str(owner)) if owner else None
    adrs = adr_index(ctx, name, family)
    strays: set[str] = set()
    own: set[str] = set()

    guard = CaseGuard()
    taken: set[str] = set()
    produced = 0
    skipped = 0
    missing: dict[str, int] = {}

    for path in files:
        text = read_text(path)
        file_sha = sha256_text(text)
        lines = text.split("\n")
        marks = [(index, title) for lvl, title, index in iter_headings(text) if lvl == level]

        for position, (start, title) in enumerate(marks):
            found = key_regex.match(title)
            if not found:
                skipped += 1
                continue
            end = marks[position + 1][0] if position + 1 < len(marks) else len(lines)
            block = "\n".join(lines[start:end]).strip("\n")
            key = found.group(1)
            label = found.group(2).strip() if found.re.groups >= 2 else title

            prefix = name
            if slices is not None:
                info = resolve_slice(name, slices, key, path, owner_regex)
                prefix = f"{name}/{safe_id_segment(info['feature'])}"
            slug = unique_slug(safe_id_segment(key), taken)
            clash = guard.check(f"{prefix}/{slug}")
            if clash:
                ctx.warnings.append(
                    f"{name}: {prefix}/{slug} và {clash} chỉ khác nhau ở chữ hoa/thường")
            node_id = f"{prefix}/{slug}"
            resource = relative_resource(node_id, path, ctx.bundle.root)

            fields = {
                "type": node_type,
                "title": f"{key} — {label}",
                "description": block_description(block, family.get("description_after")),
                "resource": resource,
                "anchor": anchor_for(title),
                "anchor_text": title,
                "tags": [name],
                "sources": [{"resource": resource}],
                "size_tokens": ctx.token_estimate(block),
                "source_sha": file_sha,
                "content_sha": sha256_text(block),
            }
            if key_field:
                fields[key_field] = strip_regex.sub("", key) if strip_regex else key
            if family.get("adr_series"):
                own.add(adr_digits(key))
            if slices is not None:
                # The bare ordinal, the same shape `heading-split` reads out
                # of front-matter.  It used to be `info["key"]` — the full file
                # stem — so one field carried two shapes: `SLICE-3` on 353 nodes
                # and `SLICE-3-danh-sach-hoa-don` on 57.  That is two fields
                # wearing one name, and neither shape resolved to anything.
                fields["slice_key"] = info["slice_id"]
                fields["slice"] = info["node_id"]
                fields["slice_set"] = info["feature"]
                fields["slice_ordinal"] = info["ordinal"]
                if info["feature"] not in fields["tags"]:
                    fields["tags"].append(info["feature"])

            # `- **Label:** value` lines carry the fields a person would filter
            # on.  Measured 32/32 on every one of the six declared labels, so a
            # miss is template drift and is reported rather than absorbed.
            found_labels = block_fields(block)
            for src_label, dst in field_map.items():
                value = found_labels.get(fold(src_label), "")
                if value:
                    fields[dst] = split_ids(value) if dst == "ntapp_unit" else value
                else:
                    missing[src_label] = missing.get(src_label, 0) + 1

            # `description_after` finds prose sitting *under* a label line.  Some
            # block families have no prose at all — an ADR block is six
            # `- **Label:** value` lines and nothing else — so the search finds
            # nothing and the card ships blank.  Naming a captured field is how
            # such a family says "the description is one of these values".
            if not fields["description"]:
                picked = str(family.get("description_field") or "")
                if picked and fields.get(picked):
                    fields["description"] = clip(strip_inline(str(fields[picked])), 240)

            governed = governed_from(block, adrs, node_id, strays)
            if governed:
                fields["governed_by"] = governed

            # Row labels come from `field_map` rather than a list in here: they
            # are the document's own words, in the document's own order, and a
            # generic adapter has no business inventing names for another
            # project's fields.
            rows = [(label, f"`{fields[dst]}`" if isinstance(fields[dst], str)
                     else ", ".join(f"`{v}`" for v in fields[dst]))
                    for label, dst in field_map.items() if fields.get(dst)]
            rows.append(("Chi phí đọc",
                         f"~{fields['size_tokens']:,} token".replace(",", ".")))
            extra = ["", "## Neo resolve", "",
                     "Dòng heading nguyên văn trong file gốc — tìm đúng chuỗi này:", "",
                     "```", "#" * level + " " + title, "```"]
            produced += 1
            yield Node(node_id, fields,
                       _pointer_card(fields["title"], path.name, rows, [], extra))

    report_adr_strays(name, adrs, strays, ctx, own)
    for label, count in sorted(missing.items()):
        ctx.warnings.append(f"{name}: {count} block thiếu trường `{label}`")
    ctx.stats.setdefault("heading_blocks", {})[name] = {
        "files": len(files), "nodes": produced, "skipped": skipped,
    }
    ctx.warnings.append(
        f"{name}: {len(files)} file → {produced + skipped} heading H{level} "
        f"= {produced} node + {skipped} không khớp `key_pattern`")


def block_description(block: str, lead) -> str:
    """The block's own prose, found past its metadata header.

    A bug entry opens on six `- **Label:** value` lines, and one of them is a
    running fix journal that can be pages long, so the naive first-block rule
    returns `Trạng thái: In Progress Ghi chú fix (2026-07-30): Đã xử lý…` — a
    description made of two unrelated fields.  The entry's actual prose sits
    under a declared label (`**Mô tả:**`), so the family names that label and
    the search starts after it.
    """
    lines = block.split("\n")
    if lead:
        needle = fold(str(lead))
        for index, line in enumerate(lines):
            found = _LABEL_LINE.match(line.strip())
            if found and needle in fold(found.group(1)):
                return first_sentence("\n".join(lines[index + 1:]))
    return doc_lede("\n".join(lines[1:]))


def block_fields(block: str) -> dict:
    """`- **Label:** value` lines → {folded label: value}, first occurrence wins."""
    out: dict[str, str] = {}
    for line in block.split("\n"):
        stripped = line.strip()
        if not stripped.startswith(("- **", "> **", "**")):
            continue
        for label, value in _BLOCKQUOTE_FIELD.findall(stripped):
            folded = fold(label.strip())
            if folded not in out:
                out[folded] = strip_inline(value).strip()
    return out


_ID_LIST_SEP = re.compile(r"\s*[,;·/]\s*|\s+và\s+")


def split_ids(value: str) -> list[str] | str:
    """One id stays a string; several become a list.  Never a list of one."""
    parts = [p for p in (p.strip() for p in _ID_LIST_SEP.split(value)) if p]
    return parts[0] if len(parts) == 1 else parts


# ── slice-manifest ───────────────────────────────────────────────────────────

def slice_index(ctx: Context, family: dict) -> dict:
    """`SLICE-N` → the manifest that defines it, grouped by feature.

    On the workflow as it stands, `slice_id` *is* globally unique: Stage 2b's
    re-run mode only ever appends (measured on paybiz — the `_v1` snapshot holds
    SLICE-1..22, the live set holds SLICE-1..25; three numbers added, none
    reused, none removed), and there is no path that renumbers from 1, because a
    non-empty `slices/` always branches to re-run.  Archived copies never enter
    this index at all: `**/archive/**` is excluded at every depth.

    So the grouping is not what keeps two slices apart — it answers "which
    feature produced this", which the manifest did not record before.  The flat
    view is still built defensively: an id claimed by two features is dropped
    from it, so if that convention ever changes, an unqualified lookup fails
    loudly instead of silently picking one of them.
    """
    declared = family.get("slice_dir")
    base = ctx.output_folder / str(declared)
    if not base.is_dir():
        raise OkfError(f"slice_dir not found: {base}")
    patterns = family.get("slice_glob") or ["SLICE-*.md", "*/SLICE-*.md"]
    if isinstance(patterns, str):
        patterns = [patterns]
    reserved = {str(d) for d in (ctx.config.get("reserved_dirs") or [])}

    by_feature: dict[str, dict] = {}
    seen: set = set()
    for pattern in patterns:
        for path in sorted(base.glob(str(pattern))):
            key = path.resolve()
            if key in seen or not path.is_file():
                continue
            seen.add(key)
            meta, _ = split_frontmatter(read_text(path))
            slice_id = str(meta.get("slice_id") or "").strip()
            if not slice_id:
                raise OkfError(f"slice manifest without `slice_id`: {path}")
            feature = str(meta.get("feature") or "").strip()
            if not feature:
                parent = path.parent.name
                if path.parent != base and parent not in reserved:
                    feature = parent
            if not feature:
                raise OkfError(
                    f"slice manifest {path.name} has no `feature:` field, and it "
                    "is not nested under a feature directory, so nothing says "
                    "which feature it belongs to. Every derived artifact — "
                    "ledger, lesson, OKF `slice_set` — groups through that "
                    "field. Add `feature:` to the front-matter (template in "
                    "NTAPP-slice-planning/workflow.md) or move the manifest into "
                    "a feature directory."
                )
            ordinal = int(re.sub(r"\D", "", slice_id) or 0)
            info = {
                "feature": feature, "slice_id": slice_id, "ordinal": ordinal,
                "title": strip_inline(str(meta.get("title") or "")).strip(),
                "key": path.stem, "path": path, "meta": meta,
                "node_id": f"slice/{safe_id_segment(feature)}/{slugify(path.stem)}",
            }
            bucket = by_feature.setdefault(feature, {})
            if slice_id in bucket:
                raise OkfError(
                    f"two manifests claim {slice_id} in feature {feature!r}: "
                    f"{bucket[slice_id]['path'].name} and {path.name}"
                )
            bucket[slice_id] = info

    flat: dict[str, dict] = {}
    ambiguous: set[str] = set()
    for bucket in by_feature.values():
        for slice_id, info in bucket.items():
            if slice_id in flat:
                ambiguous.add(slice_id)
            flat[slice_id] = info
    for slice_id in ambiguous:
        flat.pop(slice_id, None)
    return {"by_feature": by_feature, "flat": flat, "ambiguous": ambiguous}


def resolve_slice(name: str, slices: dict, key: str, path: Path,
                  owner_regex) -> dict:
    """Which slice a derived artifact belongs to — by directory, else by id.

    A bug log names `SLICE-3` and nothing else, so today it resolves through the
    flat view.  From the second feature on, two manifests answer to that name
    and the flat view drops it; the file's own directory is then the only honest
    answer, and a file that has neither raises rather than picking one.
    """
    slice_id = key
    if owner_regex is not None:
        found = owner_regex.match(key)
        if not found:
            raise OkfError(
                f"family {name!r}: key {key!r} in {path.name} does not match "
                f"slice_from_key={owner_regex.pattern!r}"
            )
        slice_id = found.group(1)

    feature = path.parent.name
    bucket = slices["by_feature"].get(feature)
    if bucket and slice_id in bucket:
        return bucket[slice_id]
    info = slices["flat"].get(slice_id)
    if info:
        return info
    if slice_id in slices["ambiguous"]:
        owners = ", ".join(sorted(
            f for f, b in slices["by_feature"].items() if slice_id in b))
        raise OkfError(
            f"family {name!r}: {path.name} refers to {slice_id}, which exists in "
            f"more than one feature ({owners}), and the file's own directory "
            f"({feature!r}) names none of them. Move it under a feature "
            "directory so the reference resolves."
        )
    known = ", ".join(sorted(slices["flat"])[:6]) or "(none)"
    raise OkfError(
        f"family {name!r}: {path.name} refers to {slice_id}, which has no slice "
        f"manifest. Known: {known}…"
    )


@adapter("slice-manifest")
def adapter_slice_manifest(name: str, family: dict, ctx: Context):
    """One node per slice manifest, with its ordinals resolved to real ids.

    A manifest writes `blocked_by: [SLICE-2]`.  Copying that number straight
    through would leave the graph holding a reference nothing can follow: the
    audit cannot tell a dangling edge from a valid one, because `SLICE-2` is not
    a node id.  So every bare ordinal is resolved here, within the manifest's own
    feature, into a real node id — which is also what makes `--audit` able to
    report `orphan edges 0` and mean it.
    """
    slices = slice_index(ctx, family)
    node_type = family.get("type", name)
    levels = family.get("outline_level") or [2]
    if isinstance(levels, int):
        levels = [levels]
    levels = {int(level) for level in levels}
    adrs = adr_index(ctx, name, family)
    strays: set[str] = set()
    unit_family = str(family.get("unit_family") or "wbs-unit")

    guard = CaseGuard()
    produced = 0
    for feature in sorted(slices["by_feature"]):
        bucket = slices["by_feature"][feature]
        for slice_id in sorted(bucket, key=lambda s: bucket[s]["ordinal"]):
            info = bucket[slice_id]
            path = info["path"]
            meta = info["meta"]
            text = read_text(path)
            node_id = info["node_id"]
            clash = guard.check(node_id)
            if clash:
                ctx.warnings.append(f"{name}: {node_id} và {clash} chỉ khác chữ hoa/thường")
            resource = relative_resource(node_id, path, ctx.bundle.root)
            outline = doc_outline(text, levels, [])

            def resolve_ref(ref: str) -> str:
                ref = str(ref).strip()
                if "/" in ref:
                    other, _, ident = ref.rpartition("/")
                    target = slices["by_feature"].get(other, {}).get(ident)
                else:
                    target = bucket.get(ref)
                if not target:
                    ctx.warnings.append(
                        f"{name}: {path.name} tham chiếu {ref!r} không có manifest "
                        f"trong feature {feature!r} — bỏ cạnh")
                    return ""
                return target["node_id"]

            units = [str(u.get("id") or "").strip()
                     for u in (meta.get("units") or []) if isinstance(u, dict)]
            units = [u for u in units if u]

            fields = {
                "type": node_type,
                "title": f"{slice_id} — {info['title']}" if info["title"] else slice_id,
                "description": describe_doc(text, family, meta, outline),
                "resource": resource,
                "tags": [name, feature],
                "sources": [{"resource": resource}],
                "size_tokens": ctx.token_estimate(text),
                "source_sha": sha256_text(text),
                "content_sha": sha256_text(text),
                "slice_key": info["slice_id"],
                "slice_title": info["title"],
                "slice_ordinal": info["ordinal"],
                "slice_set": feature,
            }
            if meta.get("type"):
                fields["slice_type"] = str(meta["type"]).strip()
            if meta.get("demo_status"):
                fields["demo_status"] = str(meta["demo_status"]).strip()
            if units:
                fields["slice_units"] = [f"{unit_family}/{safe_id_segment(u)}"
                                         for u in units]
            for key, dst in (("blocked_by", "blocked_by"), ("enhanced_by", "enhanced_by")):
                refs = meta.get(key) or []
                if isinstance(refs, str):
                    refs = [refs]
                resolved = [r for r in (resolve_ref(x) for x in refs) if r]
                if resolved:
                    fields[dst] = resolved
            carry_declared(family, meta, fields)
            governed = governed_from(text, adrs, node_id, strays)
            if governed:
                fields["governed_by"] = governed
            if outline:
                fields["subsections"] = [clip(strip_inline(t), 90) for _, t in outline[:20]]

            rows = [
                ("Feature", f"`{feature}`"),
                ("Loại", f"`{fields.get('slice_type', '')}`" if fields.get("slice_type") else ""),
                ("Demo", f"`{fields.get('demo_status', '')}`" if fields.get("demo_status") else ""),
                ("Unit", ", ".join(f"`{u}`" for u in units)),
                ("Chi phí đọc", f"~{fields['size_tokens']:,} token".replace(",", ".")),
            ]
            produced += 1
            yield Node(node_id, fields,
                       _pointer_card(fields["title"], path.name, rows, outline))

    report_adr_strays(name, adrs, strays, ctx)
    reconcile_slices(name, family, slices, ctx)
    ctx.stats.setdefault("slice_manifest", {})[name] = {
        "features": len(slices["by_feature"]), "nodes": produced,
    }
    ctx.warnings.append(
        f"{name}: {len(slices['by_feature'])} feature → {produced} node")


def reconcile_slices(name: str, family: dict, slices: dict, ctx: Context) -> None:
    """Manifest ∧ knowledge ∧ ledger — a three-way check, not a two-way one.

    A two-way "every manifest must appear in the ledger" check false-alarms
    forever on this corpus, because SLICE-23 and SLICE-25 were built by hand
    with the agent coding directly and never went through `slice-loop.yaml` at
    all.  Absent from *both* derived artifacts is the fingerprint of "the
    workflow never ran"; present in one and absent from the other is the
    fingerprint of "it ran and lost a write".  Only the second is a defect.

    Known limit, stated because it cannot be detected from here: a slice-loop
    run that dies *before* its code-review node leaves exactly the same trace as
    a hand-built slice.
    """
    ledger_rel = family.get("ledger")
    knowledge_rel = family.get("knowledge_dir")
    if not (ledger_rel and knowledge_rel):
        return

    ledger_path = ctx.output_folder / str(ledger_rel)
    knowledge_dir = ctx.output_folder / str(knowledge_rel)
    in_ledger: set[str] = set()
    if ledger_path.is_file():
        for _, title, _ in iter_headings(read_text(ledger_path)):
            found = re.match(r"^(SLICE-\d+)\b", title.strip())
            if found:
                in_ledger.add(found.group(1))
    else:
        ctx.warnings.append(f"{name}: không thấy ledger {ledger_rel} — bỏ đối chiếu")
        return
    in_knowledge = ({p.stem for p in knowledge_dir.glob("SLICE-*.md")}
                    if knowledge_dir.is_dir() else set())

    if slices["ambiguous"]:
        # Guarded on an ordinal actually being claimed twice, NOT on the feature
        # count.  Measured on the real history: Stage 2b re-run *appends*
        # (22 slices → 25, numbers 23–25 added, none reused, none removed) and
        # there is no code path that renumbers from 1 — a non-empty `slices/`
        # always branches to re-run mode.  So a second feature does not by
        # itself make `SLICE-3` in the ledger ambiguous, and disabling the check
        # on feature count would switch off the only three-way reconciliation
        # there is, for a collision that has not happened.
        clash = ", ".join(sorted(slices["ambiguous"]))
        ctx.warnings.append(
            f"{name}: {clash} bị nhiều feature cùng nhận, mà ledger và "
            f"`{knowledge_rel}` khoá theo số trần — BỎ đối chiếu, vì đối chiếu "
            "tiếp sẽ ra một câu trả lời tự tin và sai. Hai họ artifact này phải "
            "xuống thư mục feature trước (§3.6).")
        return

    manifests = set(slices["flat"])
    handmade = sorted(manifests - in_knowledge - in_ledger)
    lost_write = sorted((manifests & in_knowledge) - in_ledger)
    no_review = sorted((manifests & in_ledger) - in_knowledge)
    orphans = sorted((in_ledger | in_knowledge) - manifests)

    if handmade:
        ctx.warnings.append(
            f"{name}: {len(handmade)} slice không có cả ledger lẫn knowledge "
            f"({', '.join(handmade)}) — dấu vết của slice làm tay, không phải lỗi")
    if lost_write:
        ctx.warnings.append(
            f"⛔ {name}: {len(lost_write)} slice CÓ knowledge nhưng THIẾU ledger "
            f"({', '.join(lost_write)}) — slice-loop đã chạy và mất lượt ghi ledger")
    if no_review:
        ctx.warnings.append(
            f"⛔ {name}: {len(no_review)} slice CÓ ledger nhưng THIẾU knowledge "
            f"({', '.join(no_review)}) — qua node demo mà không qua node code-review")
    if orphans:
        ctx.warnings.append(
            f"⛔ {name}: {len(orphans)} mục ledger/knowledge không có manifest "
            f"({', '.join(orphans)})")


# ── knowledge-bullets ────────────────────────────────────────────────────────

# Section headings appear at BOTH depths in this corpus: 21 notes write
# `### Pattern`, but SLICE-10 and SLICE-12 write `## Pattern`.  Keying on one
# depth drops those two files and reports success — measured, 572 bullets
# instead of 592.  Same shape as the P4 `split_level` trap, so the field is a
# list here too and `min_nodes` is the net.
# Deliberately permissive on the heading tail.  The 23 notes annotate
# these headings nine different ways — `### Gotcha (vấn đề review phát
# hiện + sự cố dev + cách giải)` — and a character class tight enough to
# look safe rejects the ones containing `+`, dropping 122 of 592 bullets
# with no error.  Match the whole line, then decide on the first word.
_KB_SECTION = re.compile(r"^(#{2,3})\s+(\S.*?)\s*$")
# Top-level bullets only.  A nested `  - ` continues the bullet above it; making
# it a node splits one thought across two and gives the second the wrong title.
_KB_BULLET = re.compile(r"^[-*]\s+(\S.*)$")
_KB_LEAD = re.compile(r"^\*\*(.+?)\*\*")
# A clause ends at sentence punctuation, an em-dash, or a colon — but never at
# punctuation inside `**bold**`, because the run-in label *is* the title and
# `**Mục đích chính.**` would otherwise end it two words in.
_KB_CLAUSE = re.compile(r"(?<=[.!?])\s|\s+[—–]\s+|:\s+")
_KB_BOLD_RUN = re.compile(r"\*\*[^*]+\*\*")
_KB_SEVERITY = re.compile(r"\[(BLOCKER|HIGH|MEDIUM|LOW)\]", re.IGNORECASE)
# Not `\bSLICE-\d+\b` alone: `SLICE-3-BUG-01` must not read as a reference to
# SLICE-3 plus stray text — a bug id is its own identifier.
_SLICE_REF = re.compile(r"\bSLICE-\d+\b(?!-)")


def kb_title(text: str, max_len: int = 80) -> tuple[str, bool]:
    """(title, author_wrote_it) for one bullet.

    88% of bullets open with a bold run-in label the author wrote as a title —
    `**IDOR-by-type.**`, `**[HIGH] Contract drift envelope-vs-list.**`.  Those
    are used verbatim.  The remaining 12% get their first clause, which is still
    the author's words, just not words they marked as a title.

    Measured on all 592: 519 authored, 73 derived, and the 73 are distinct from
    one another.  That is the whole reason this family needs no model — the
    plan budgeted an LLM pass for work the corpus had already done.
    """
    lead = _KB_LEAD.match(text)
    if lead:
        return strip_inline(lead.group(1)).rstrip(".:").strip(), True
    flat = re.sub(r"\s+", " ", text).strip()
    masked = _KB_BOLD_RUN.sub(lambda m: "\x00" * len(m.group(0)), flat)
    found = _KB_CLAUSE.search(masked)
    cut = strip_inline(flat[:found.start()] if found else flat)
    if len(cut) > max_len:
        cut = cut[:max_len].rsplit(" ", 1)[0]
    return cut.strip(" ,;:—-") or "", False


def kb_bullets(text: str, sections: list[str], levels: set[int]):
    """(section, bullet_text) for every top-level bullet under a named section."""
    wanted = {fold(s) for s in sections}
    section: str | None = None
    current: str | None = None
    buffer: list[str] = []
    out: list[tuple[str, str]] = []

    def flush():
        if current is not None and section:
            out.append((section, "\n".join([current] + buffer).strip()))

    fence: str | None = None
    for line in text.split("\n"):
        marker = _FENCE.match(line)
        if marker:
            token = marker.group(1)[0]
            fence = token if fence is None else (None if token == fence else fence)
            if fence is not None or current is None:
                continue
        if fence is not None:
            if current is not None:
                buffer.append(line)
            continue
        found = _KB_SECTION.match(line)
        if found:
            flush()
            current, buffer = None, []
            depth = len(found.group(1))
            # `strip_inline` first: SLICE-12 writes `### **Pattern**` with the
            # heading itself bolded, and the raw text folds to `**pattern**`,
            # which matches nothing.  One file, 12 bullets, silently zero.
            head = strip_inline(found.group(2))
            # `### Pattern (seams thật trong code)` — the parenthetical is the
            # author annotating their own heading, 9 different ways across 23
            # files.  Match on the first word so the section survives it.
            # Guard the token AFTER the paren split, not before it: a heading
            # reading `## (ghi chú)` makes `head.split()` truthy while
            # `head.split("(")[0].split()` is empty — an IndexError, not a miss.
            words = head.split("(")[0].split()
            first = fold(words[0]) if words else ""
            section = head.split("(")[0].strip() if (
                depth in levels and first in wanted) else None
            continue
        if line.startswith("#"):
            flush()
            current, buffer, section = None, [], None
            continue
        if section is None:
            continue
        bullet = _KB_BULLET.match(line)
        if bullet:
            flush()
            current, buffer = bullet.group(1), []
            continue
        if current is not None and (line.strip() or buffer):
            buffer.append(line)
    flush()
    return out


@adapter("knowledge-bullets")
def adapter_knowledge_bullets(name: str, family: dict, ctx: Context):  # noqa: C901
    """One node per bullet in a per-slice knowledge note.

    This is the family the plan calls "the only one that needs a real model".
    It does not.  Every bullet already carries a title its author wrote, an
    inline set of unit and ADR ids, and a home slice named by the filename —
    so identity, title, attachment and provenance are all recoverable exactly.
    Running a model over it would put a paraphrase where the master's own words
    are, which is the one thing §3.2 reserves `description` against, and would
    trade an idempotent family for one that is re-bought on every projection.

    What the model *would* have been for — the 12% with no run-in label — is
    solved by quoting their first clause instead of inventing a summary.

    The node id is `lesson/<feature>/<slice-N>/<title>`, deliberately using the
    bare ordinal rather than the slice's full slug.  The full slug would add ~35
    characters to every path for no identity gain — the ordinal is already
    unique inside a feature — and this bundle has to survive Windows MAX_PATH.
    The resolvable form lives on the `slice` edge, where a consumer needs it.
    """
    slices = slice_index(ctx, family)
    if not slices["by_feature"]:
        raise OkfError(f"family {name!r}: slice_dir produced no manifest")
    node_type = family.get("type", name)
    sections = [str(s) for s in (family.get("sections") or
                                 ["Pattern", "Decision", "Gotcha", "Notes"])]
    levels = family.get("section_level") or [2, 3]
    if isinstance(levels, int):
        levels = [levels]
    levels = {int(level) for level in levels}
    owner = family.get("slice_from_key") or r"^(SLICE-\d+)"
    owner_regex = re.compile(str(owner))
    unit_family = str(family.get("unit_family") or "wbs-unit")
    # The unit list comes from the WBS, never from a regex over prose.  An
    # id-shaped token is not an id: measured on this corpus, matching
    # `[A-Z]{2,}(-[A-Z0-9]+)+` produced 405 edges of which 283 were false —
    # `SLICE-12`, `KB-03`, `HTTP-envelope`, `INV-Q3`.  Seventy percent wrong,
    # every one of them pointing at a node that does not exist, and `--audit`
    # would have called them orphans rather than fabrications.
    wbs_parser = _load_wbs_parser()
    unit_source = ctx.resolve_source(
        family.get("unit_source") or "Stage_2_Architecture/project_wbs.md")
    known_units = {unit.id for unit in wbs_parser.parse_wbs(unit_source)}
    adrs = adr_index(ctx, name, family)

    strays: set[str] = set()
    guard = CaseGuard()
    produced = 0
    derived = 0
    per_section: dict[str, int] = {}
    unresolved: list[str] = []

    for note in family_sources(ctx, name, family):
        info = resolve_slice(name, slices, note.stem, note, owner_regex)
        feature = info["feature"]
        text = read_text(note)
        file_sha = sha256_text(text)
        found = kb_bullets(text, sections, levels)
        if not found:
            ctx.warnings.append(
                f"{name}: {note.name} có 0 bullet ở mục {sections} mức "
                f"{sorted(levels)} — kiểm tra lại mức heading của file này")
        prefix = f"{name}/{safe_id_segment(feature)}/{slugify(info['slice_id'])}"
        taken: set[str] = set()

        for section, body in found:
            title, authored = kb_title(body)
            if not title:
                unresolved.append(f"{note.name}: bullet không rút được tiêu đề")
                continue
            if not authored:
                derived += 1
            slug = unique_slug(slugify(title), taken)
            node_id = f"{prefix}/{slug}"
            clash = guard.check(node_id)
            if clash:
                ctx.warnings.append(
                    f"{name}: {node_id} và {clash} chỉ khác chữ hoa/thường")
            resource = relative_resource(node_id, note, ctx.bundle.root)
            per_section[section] = per_section.get(section, 0) + 1

            # Every bare `SLICE-N` in the prose is frozen to a node id here.
            # The DoD's point is not that the string disappears — deleting an
            # ordinal out of the author's sentence damages the master's words to
            # satisfy a substring check — but that no mention is left that a
            # reader could resolve to the wrong feature's slice next cycle.
            related: list[str] = []
            for ref in sorted(set(_SLICE_REF.findall(body))):
                if ref == info["slice_id"]:
                    continue
                target = (slices["by_feature"].get(feature, {}).get(ref)
                          or slices["flat"].get(ref))
                if target:
                    related.append(target["node_id"])
                else:
                    unresolved.append(f"{note.name}: {title[:40]!r} → {ref}")

            units = sorted(set(_ID_TOKEN.findall(body)) & known_units)
            # `governed_from`, not a local lookup: it keys on the literal digit
            # string so `0002` (designed) and `002` (runtime) stay separate, and
            # it collects strays instead of dropping them.  The delivered block
            # indexed the wrapper dict returned by `adr_index` rather than its
            # `by_number`, so the guard never matched and all 631 nodes shipped
            # with zero `governed_by` — silently, with --audit clean.
            governed = governed_from(body, adrs, node_id, strays)
            severity = _KB_SEVERITY.search(body)

            fields = {
                "type": node_type,
                "title": title,
                "description": clip(strip_inline(
                    re.sub(r"\s+", " ", body)), 240),
                "resource": resource,
                "tags": [name, feature, slugify(section)],
                "sources": [{"resource": resource}],
                "size_tokens": ctx.token_estimate(body),
                "lesson_section": section,
                "slice_key": info["slice_id"],
                "slice_set": feature,
                "slice": info["node_id"],
                "source_sha": file_sha,
                "content_sha": sha256_text(body),
            }
            if severity:
                fields["lesson_severity"] = severity.group(1).upper()
            if not authored:
                # Says out loud that this title is the projector's cut of the
                # author's sentence rather than a heading they wrote.  Cheap
                # here, unrecoverable later.
                fields["title_derived"] = True
            if units:
                fields["implements"] = [f"{unit_family}/{safe_id_segment(u)}"
                                        for u in units]
            if related:
                fields["related_slices"] = related
            if governed:
                fields["governed_by"] = governed

            produced += 1
            yield Node(node_id, fields, _lesson_body(fields, body, note.name))

    ctx.stats.setdefault("knowledge_bullets", {})[name] = {
        "notes": len(slices["flat"]), "nodes": produced,
        "derived_titles": derived, "sections": per_section,
    }
    ctx.warnings.append(
        f"{name}: {produced} node ({derived} tiêu đề do máy cắt từ câu đầu, "
        f"{produced - derived} do tác giả tự đặt) — {per_section}")
    report_adr_strays(name, adrs, strays, ctx)
    for problem in unresolved[:10]:
        ctx.warnings.append(f"{name}: {problem}")


def _lesson_body(fields: dict, bullet: str, filename: str) -> str:
    """The card.  A lesson is short enough to quote in full — and must be.

    Everywhere else in this bundle the card is a pointer, because the target is
    a 10k-token section and copying it would cost more than the document it
    indexes.  A lesson is a median of 105 tokens.  Paraphrasing it to save 105
    tokens would spend the one thing the node exists to carry, so the bullet is
    reproduced verbatim and the frontmatter carries the edges.
    """
    lines = [
        f"# {fields['title']}", "",
        f"> **Trích nguyên văn** từ `{filename}`, mục *{fields['lesson_section']}*. "
        f"Không diễn giải lại — đây là chữ của người viết ledger.",
        "", "| Trường | Giá trị |", "|---|---|",
        f"| Slice | `{fields['slice_key']}` — `{fields['slice']}` |",
        f"| Mục | {fields['lesson_section']} |",
    ]
    if fields.get("lesson_severity"):
        lines.append(f"| Mức độ | **{fields['lesson_severity']}** |")
    if fields.get("implements"):
        lines.append("| Unit | " + ", ".join(
            f"`{u.split('/')[-1]}`" for u in fields["implements"]) + " |")
    if fields.get("title_derived"):
        lines.append("| Tiêu đề | máy cắt từ câu đầu (tác giả không đặt) |")
    lines += ["", "## Nguyên văn", "", bullet.rstrip()]
    if fields.get("related_slices"):
        lines += ["", "## Slice được nhắc tới", ""]
        lines += [f"- `{r}`" for r in fields["related_slices"]]
    return "\n".join(lines)


# ── json-doc ─────────────────────────────────────────────────────────────────

def count_label(path: str) -> str:
    """`state_machine.states` → `states`; `_drift_notes` → `drift notes`.

    The document's own vocabulary rather than a translation: these schemas are
    written in English, and renaming their keys in the card would break the tie
    between what the card says and what a reader finds on opening the file.
    """
    return str(path).rsplit(".", 1)[-1].lstrip("_").replace("_", " ")


def dotted(data, path: str):
    """`a.b.c` into nested dicts; None when any step is missing."""
    current = data
    for part in str(path).split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


@adapter("json-doc")
def adapter_json_doc(name: str, family: dict, ctx: Context):
    """One node per JSON document, described by counting what is inside it.

    These files carry no prose to quote, so `description` is built the same way
    `outline_description` is: a count and a list taken from the document, never a
    paraphrase.  The count *is* the useful fact here — the nine UI schemas run
    34–77 KB, and "42 control, 9 ghi chú lệch" is precisely what decides whether
    to spend ~20k tokens opening one.
    """
    files = family_sources(ctx, name, family)
    node_type = family.get("type", name)
    id_key = str(family.get("id_key") or "id")
    field_map = {str(k): str(v) for k, v in (family.get("fields") or {}).items()}
    counts = {str(k): str(v) for k, v in (family.get("counts") or {}).items()}
    preview = family.get("preview") or {}

    guard = CaseGuard()
    taken: set[str] = set()
    produced = 0

    for path in files:
        raw = read_text(path)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OkfError(f"family {name!r}: {path.name} is not valid JSON — {exc}") from exc
        if not isinstance(data, dict):
            raise OkfError(f"family {name!r}: {path.name} is a {type(data).__name__}, "
                           "expected an object")

        ident = str(data.get(id_key) or path.stem).strip()
        slug = unique_slug(safe_id_segment(ident), taken)
        clash = guard.check(slug)
        if clash:
            ctx.warnings.append(f"{name}: {slug} và {clash} chỉ khác nhau ở chữ hoa/thường")
        node_id = f"{name}/{slug}"
        resource = relative_resource(node_id, path, ctx.bundle.root)

        fields = {
            "type": node_type,
            "title": ident,
            "description": "",
            "resource": resource,
            "tags": [name],
            "sources": [{"resource": resource}],
            "size_tokens": ctx.token_estimate(raw),
            "source_sha": sha256_text(raw),
            "content_sha": sha256_text(raw),
        }
        # Both maps read {node field: path into the JSON}, the same direction the
        # frontmatter is written in.
        for dst, src in field_map.items():
            value = dotted(data, src)
            if isinstance(value, (str, int, float)) and str(value).strip():
                fields[dst] = str(value).strip()

        tally: list[str] = []
        for dst, src in sorted(counts.items()):
            value = dotted(data, src)
            if isinstance(value, list):
                fields[dst] = len(value)
                tally.append(f"{len(value)} {count_label(src)}")
        kind = str(fields.get("ui_kind") or node_type)
        fields["description"] = clip(
            f"{kind} `{ident}`" + (" — " + ", ".join(tally) if tally else ""), 240)

        rows = [(label, f"`{fields[dst]}`") for label, dst in
                (("Loại", "ui_kind"), ("Design system", "design_system"),
                 ("Phiên bản DD", "dd_version"))
                if fields.get(dst)]
        rows += [(count_label(counts[dst]).capitalize(), str(fields[dst]))
                 for dst in sorted(counts) if fields.get(dst)]
        rows.append(("Chi phí đọc", f"~{fields['size_tokens']:,} token".replace(",", ".")))

        extra: list[str] = []
        for label, spec in preview.items():
            values = dotted(data, str(spec.get("path") or ""))
            if not isinstance(values, list) or not values:
                continue
            field = str(spec.get("field") or "")
            limit = int(spec.get("limit") or 20)
            picked = [str(v.get(field, "")) if isinstance(v, dict) else str(v)
                      for v in values[:limit]]
            picked = [p for p in picked if p]
            if not picked:
                continue
            extra += ["", f"## {label} ({len(values)})", ""]
            extra += [f"- `{p}`" for p in picked]
            if len(values) > limit:
                extra.append(f"- … còn {len(values) - limit} mục")
        if fields.get("figma_ref"):
            extra += ["", "## Figma", "", f"`{fields['figma_ref']}`"]

        produced += 1
        yield Node(node_id, fields, _pointer_card(ident, path.name, rows, [], extra))

    ctx.stats.setdefault("json_doc", {})[name] = {"files": len(files), "nodes": produced}
    ctx.warnings.append(f"{name}: {len(files)} file → {produced} node")


# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────

def apply_links(config: Config, bundle: Bundle, log: list[str]) -> None:
    """Reconcile reverse edges across families, reading the whole bundle.

    `built_as` runs unit → code-file, but the code-file nodes are produced by a
    different family, and a family only ever writes its own nodes.  Nothing
    stops a family from *reaching over* — except that the next run of the owning
    family would rewrite the target node and drop the edge again, since edges
    are machine-owned fields.

    So the reconciliation is a pass over what is on disk rather than over what
    this run produced.  That makes it idempotent, and it makes it self-healing:
    projecting either side alone still leaves both sides agreeing.
    """
    for link in config.get("links") or []:
        field = str(link.get("back_edge") or "")
        from_family = str(link.get("from_family") or "")
        from_field = str(link.get("from_field") or "")
        to_family = str(link.get("to_family") or "")
        if not (field and from_family and from_field and to_family):
            raise OkfError(f"incomplete link declaration: {link!r}")

        grouped: dict[str, list[str]] = {}
        for node_id in sorted(bundle.existing_ids(from_family)):
            record = bundle.read_node(node_id)
            if not record:
                continue
            fields, _ = record
            if fields.get("status") == "deprecated":
                continue
            key = fields.get(from_field)
            if key:
                grouped.setdefault(str(key), []).append(node_id)

        touched = 0
        for node_id in sorted(bundle.existing_ids(to_family)):
            record = bundle.read_node(node_id)
            if not record:
                continue
            fields, body = record
            local = node_id.split("/", 1)[1] if "/" in node_id else node_id
            wanted = sorted(grouped.get(local, []))
            if list(fields.get(field) or []) == wanted:
                continue
            if wanted:
                fields[field] = wanted
            else:
                fields.pop(field, None)
            write_text(bundle.node_path(node_id), render_node(fields, body))
            touched += 1

        edges = sum(len(v) for v in grouped.values())
        log.append(f"link `{field}`: {edges} edge(s) over {len(grouped)} target(s), "
                   f"{touched} node(s) rewritten")


def select_families(config: Config, only: list[str] | None) -> dict:
    """Pick the families to run, failing on an unknown name.

    Called before the lock is taken, so a typo in `--family` is reported without
    touching the project.  This guard covers exactly that case; keeping an empty
    `.okf/` out of a project that has declared no families at all is a separate
    matter, handled where the scaffold is built.
    """
    families = config.families
    if not only:
        return families
    missing = [name for name in only if name not in families]
    if missing:
        known = ", ".join(sorted(families)) or "(none declared)"
        raise OkfError(f"no such family: {', '.join(missing)}; declared: {known}")
    return {name: families[name] for name in only}


def cmd_dry_run(config: Config, notes: list[str]) -> int:
    print(f"okf: root       = {config.root}")
    print(f"okf: output     = {config.output_folder}")
    print(f"okf: spec       = v{config.get('spec_version')}")
    print(f"okf: exclude    = {len(config.exclude.patterns)} pattern(s)")
    for note in notes:
        print(f"okf: note       = {note}")
    if not config.families:
        print("okf: families   = 0 — nothing declared in Layer 2 `okf.families`")
        return 0
    print(f"okf: families   = {len(config.families)}")
    for name in sorted(config.families):
        family = config.families[name] or {}
        adapter_name = family.get("adapter", "?")
        source = family.get("source") or family.get("source_glob") or "-"
        known = "ok" if adapter_name in ADAPTERS else "UNKNOWN"
        goal = (family.get("goal") or "").strip().replace("\n", " ")
        print(f"  - {name:<22} adapter={adapter_name} [{known}]  source={source}")
        if goal:
            print(f"    goal: {goal[:100]}")
        if not goal:
            print("    ⚠️  no `goal` — a family must declare what it exists for")
    return 0


def cmd_project(config: Config, bundle: Bundle, actor: str, *, full: bool,
                only: list[str] | None, allow_shrink: bool = False) -> int:
    # Resolve what we are about to do *before* creating anything on disk. A run
    # that is going to fail must not leave a half-built bundle behind.
    families = select_families(config, only)

    ctx = Context(config, bundle, actor)
    log: list[str] = []
    counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}

    # Nothing declared means nothing to project, and a run that projects nothing
    # must not leave the bundle directory behind.  The pointer files bootstrap
    # writes into every repo tell the reader that an absent `.okf/` means "never
    # projected"; creating an empty one here would erase that distinction and
    # drop a starter `index.md` that the projector, by design, never overwrites
    # again.  So the scaffold is built below, once there is something to put in it.
    if not families:
        print("okf: no families declared — nothing to project")
        return 0

    bundle.ensure_scaffold()

    # ADR series project first, and by declaration rather than alphabetical luck.
    # Consumers resolve `governed_by` against ids a series actually emitted, so
    # the series has to exist before anything can point at it.  That ordering was
    # accidental before: `adr` happened to sort first.  Renaming it to
    # `designed-adr` moves it *after* `design-section` (`-` sorts below `e`) and
    # would have emptied the index for exactly that one family, silently.
    def series_first(key: str) -> tuple:
        return (0 if (families[key] or {}).get("adr_series") else 1, key)

    for name in sorted(families, key=series_first):
        family = families[name] or {}
        adapter_fn = resolve_adapter(family.get("adapter", ""))

        # A family whose stage has not run yet, declared ahead of time on
        # purpose.  Announced on every pass rather than passed over quietly:
        # "skipped, nothing to read yet" and "projected, found nothing" are
        # different facts, and a bundle that reports neither reads as complete.
        if family.get("allow_missing_source") and not family_has_source(ctx, family):
            # `min_nodes` is a human asserting this family must produce at least
            # N nodes, which cannot be true of a source that is not there.  The
            # two keys together describe a lifecycle: tolerate the gap while the
            # stage is pending, then fill in the floor from a real run and the
            # tolerance switches itself off.  Without this the floor would be
            # unreachable — skipping jumps over the check that guards it, so a
            # source that later moved or got renamed would read as "not yet".
            minimum = family.get("min_nodes")
            if isinstance(minimum, int) and minimum > 0:
                raise OkfError(
                    f"family {name!r}: source not on disk, but min_nodes={minimum} "
                    "declares it must produce nodes. Drop `allow_missing_source` "
                    "once the floor is set, or find out where the source went."
                )
            log.append(f"family `{name}`: nguồn chưa tồn tại — bỏ qua (allow_missing_source)")
            print(f"okf: family {name!r} skipped — source not on disk yet")
            continue

        produced = list(adapter_fn(name, family, ctx))

        minimum = family.get("min_nodes")
        if isinstance(minimum, int) and len(produced) < minimum:
            raise OkfError(
                f"family {name!r} produced {len(produced)} node(s), below min_nodes={minimum}. "
                "Refusing to report success on a silently narrowed scan."
            )

        if family.get("adr_series"):
            register_adr_series(ctx, name, family, produced)

        expected = {node.node_id for node in produced}
        stale = sorted(bundle.existing_ids(name) - expected)
        # A tombstone is not a fresh shrink.  Nodes already marked `deprecated`
        # went through this decision on the run that removed them, and they sit
        # on disk until `sweep_deprecated` clears the grace period — so counting
        # them here would raise on *every* run until then.  That is worse than
        # useless: a guard that always fires teaches the operator to pass
        # `--allow-shrink` by reflex, which is precisely how a real regression
        # gets waved through. Only newly-missing nodes are a shrink.
        fresh_stale = [nid for nid in stale if not bundle.is_deprecated(nid)]
        if fresh_stale and not allow_shrink:
            # The other half of the `min_nodes` rule: a run may produce enough
            # nodes to clear the floor and still have lost some, because a glob
            # or a split level narrowed. Deprecating them quietly would report
            # success while the graph shrank, so a shrink needs a deliberate
            # flag — deleting a source is rare, and worth one keystroke.
            sample = ", ".join(fresh_stale[:5]) + ("…" if len(fresh_stale) > 5 else "")
            raise OkfError(
                f"family {name!r} would deprecate {len(fresh_stale)} existing node(s) "
                f"({sample}). If the sources really were deleted, re-run with "
                "--allow-shrink; otherwise the pattern or split_level narrowed."
            )

        for node in produced:
            bundle.write_node(node, actor)
            counts[node.type] = counts.get(node.type, 0) + 1

        for stale_id in stale:
            bundle.deprecate(stale_id)

        # The table of contents is a derivative of its family, so it is rewritten
        # exactly when that family is projected — including under `--family X`,
        # where only X's nodes moved and only X's index should.
        family_counts[name] = len(produced)
        bundle.write_type_index(name, family, produced)

        log.append(f"family `{name}`: {len(produced)} node(s)")

    apply_links(config, bundle, log)

    if full:
        removed = bundle.sweep_deprecated(int(config.get("deprecate_grace_days") or 30))
        if removed:
            log.append(f"swept {len(removed)} deprecated node(s) past grace period")

    for warning in ctx.warnings:
        log.append(f"⚠️ {warning}")

    log.append(
        f"created={bundle.created} updated={bundle.written} "
        f"unchanged={bundle.unchanged} deprecated={bundle.deprecated}"
    )
    bundle.append_log(log)
    bundle.write_status({
        "last_refresh": utc_now(), "mode": "full" if full else "incremental",
        "actor": actor, "counts": counts, "families": family_counts,
        "stats": ctx.stats,
        "repos_scanned": [r.get("name") for r in config.code_repos
                          if (config.project_root / str(r.get("path", ""))).exists()],
        "repos_missing": [r.get("name") for r in config.code_repos
                          if not (config.project_root / str(r.get("path", ""))).exists()],
    })
    print(f"okf: created={bundle.created} updated={bundle.written} "
          f"unchanged={bundle.unchanged} deprecated={bundle.deprecated}")
    return 0


def repos_complete(config: Config) -> tuple[bool, list[str]]:
    """Whether every declared code repo is actually present.

    A missing repo means "unknown", not "not built".  Answering a coverage
    question over a partial checkout returns a confidently wrong number in the
    pessimistic direction — precisely the class of mistake the graph exists to
    end — so the answer is withheld instead.
    """
    absent = [
        str(repo.get("name"))
        for repo in config.code_repos
        if not (config.project_root / str(repo.get("path", ""))).is_dir()
    ]
    return (not absent), absent


def cmd_audit(config: Config, bundle: Bundle, as_json: bool) -> int:
    findings: dict = {
        "counts": {}, "deprecated": 0, "unverified": 0,
        "orphan_edges": [], "missing_resource": [],
        # Counted per key, including the keys that counted nothing.  `orphan
        # edges 0` cannot tell "every edge resolves" from "no edge was emitted",
        # and a family shipped 631 nodes with zero `governed_by` behind exactly
        # that reading.  A zero printed next to its own name is not hideable.
        "edge_counts": {key: 0 for key in EDGE_KEYS},
        "edge_nodes": {key: 0 for key in EDGE_KEYS},
        "unbuilt_units": [], "dd_version_drift": [], "intra_unit_drift": [],
        "coverage_answerable": True, "repos_absent": [],
    }
    if not config.root.exists():
        print("okf: bundle absent — nothing to audit")
        return 0

    ids = bundle.existing_ids()
    nodes: dict[str, dict] = {}
    for node_id in sorted(ids):
        record = bundle.read_node(node_id)
        if not record:
            continue
        fields, _ = record
        nodes[node_id] = fields
        node_type = fields.get("type", "?")
        findings["counts"][node_type] = findings["counts"].get(node_type, 0) + 1
        if fields.get("status") == "deprecated":
            findings["deprecated"] += 1
        if not fields.get("verified"):
            findings["unverified"] += 1
        for edge in EDGE_KEYS:
            # An edge may be single-valued.  A bare string is iterable, so the
            # naive loop walked `slice/invoice-link/…` one character at a time
            # and reported 1859 orphans for 32 perfectly good edges.
            targets = fields.get(edge) or []
            if isinstance(targets, str):
                targets = [targets]
            if targets:
                findings["edge_counts"][edge] += len(targets)
                findings["edge_nodes"][edge] += 1
            for target in targets:
                if str(target) not in ids:
                    findings["orphan_edges"].append(f"{node_id} --{edge}--> {target}")
        resource = fields.get("resource")
        if resource and not fields.get("code_repo"):
            if not (config.root / node_id).parent.joinpath(str(resource)).exists():
                findings["missing_resource"].append(node_id)

    complete, absent = repos_complete(config)
    findings["coverage_answerable"] = complete
    findings["repos_absent"] = absent

    units = {nid: f for nid, f in nodes.items() if f.get("type") == "wbs-unit"}
    code = [f for f in nodes.values() if f.get("type") == "code-file"]

    if complete:
        findings["unbuilt_units"] = sorted(
            nid for nid, f in units.items() if not f.get("built_as")
        )

    by_unit: dict[str, set] = {}
    for fields in code:
        unit = str(fields.get("ntapp_unit") or "")
        version = str(fields.get("dd_version") or "")
        if unit:
            by_unit.setdefault(unit, set()).add(version)
        design = str((units.get(f"wbs-unit/{unit}") or {}).get("dd_version") or "")
        if design and version and version_behind(version, design):
            findings["dd_version_drift"].append(
                f"{fields.get('title')}: code {version} < thiết kế {design}"
            )
    findings["intra_unit_drift"] = sorted(
        f"{unit}: {', '.join(sorted(versions, key=parse_version))}"
        for unit, versions in by_unit.items() if len(versions) > 1
    )

    if as_json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
        return 0

    total = sum(findings["counts"].values())
    print(f"okf audit: {total} node(s)")
    for node_type in sorted(findings["counts"]):
        print(f"  {node_type:<24} {findings['counts'][node_type]}")
    print(f"  deprecated               {findings['deprecated']}")
    print(f"  unverified               {findings['unverified']}")
    print(f"  orphan edges             {len(findings['orphan_edges'])}")
    print(f"  unresolvable resource    {len(findings['missing_resource'])}")
    print("  cạnh theo loại — 0 ở đây nghĩa là KHÔNG SINH RA, không phải 'sạch':")
    for edge in EDGE_KEYS:
        count = findings["edge_counts"][edge]
        holders = findings["edge_nodes"][edge]
        flag = "   ← không có cạnh nào" if count == 0 else ""
        print(f"    {edge:<22} {count:>6} cạnh / {holders} node{flag}")
    if complete:
        print(f"  unit chưa build          {len(findings['unbuilt_units'])}/{len(units)}")
    else:
        print("  unit chưa build          TỪ CHỐI TRẢ SỐ — thiếu repo: "
              + ", ".join(absent))
        print("                           (thiếu repo là *chưa biết*, không phải "
              "*chưa build*)")
    print(f"  code sau thiết kế        {len(findings['dd_version_drift'])}")
    print(f"  unit lệch version nội bộ {len(findings['intra_unit_drift'])}")
    for line in findings["orphan_edges"][:10]:
        print(f"    ! {line}")
    for line in findings["intra_unit_drift"][:10]:
        print(f"    ~ {line}")
    for line in findings["dd_version_drift"][:10]:
        print(f"    ~ {line}")
    return 1 if findings["orphan_edges"] or findings["missing_resource"] else 0


def cmd_verify(config: Config, bundle: Bundle, node_id: str) -> int:
    """Append one signature. The person signs; the machine writes.

    `verified` here is a low bar on purpose: *I opened the master and this card
    points at the right place and describes it correctly.*  It is not "I agree
    with this specification" — approval authority already lives in the approval
    gates, and a node card is a retrieval index, not a source to write from.
    Setting the bar at module ownership would leave the field empty forever:
    the repo has no CODEOWNERS and no `owner` field to enforce it with.
    """
    if in_ci():
        print("okf: --verify refuses to run without a human (CI=true or no TTY). "
              "Signing is a person's act; the machine does not sign on their behalf.",
              file=sys.stderr)
        return 2

    actor = derive_actor(config.project_root)
    if not actor:
        print("okf: cannot derive an identity — `git config user.email` is unset.",
              file=sys.stderr)
        return 2

    node_id = node_id[:-3] if node_id.endswith(".md") else node_id
    existing = bundle.read_node(node_id)
    if not existing:
        print(f"okf: no such node: {node_id}", file=sys.stderr)
        return 2

    fields, body = existing
    signatures = list(fields.get("verified") or [])
    signatures.append({"by": actor, "at": utc_now()})
    fields["verified"] = signatures
    fields["status"] = derive_status(fields)
    write_text(bundle.node_path(node_id), render_node(fields, body))
    bundle.append_log([f"verified `{node_id}` by {actor}"])
    print(f"okf: {node_id} signed by {actor} ({len(signatures)} signature(s))")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Self-test — stdlib only, so it also runs on Windows where pytest is absent
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:  # noqa: C901 — a flat list of checks reads better here
    import tempfile

    failures: list[str] = []

    def check(label: str, got, want):
        if got != want:
            failures.append(f"{label}\n     got:  {got!r}\n     want: {want!r}")

    # slugify — the six cases the plan names, plus Vietnamese đ
    check("slug: colon in heading",
          slugify("Bề mặt được dựng lại: miễn trừ xác thực theo đường dẫn"),
          "be-mat-duoc-dung-lai-mien-tru-xac-thuc-theo-duong-dan")
    check("slug: trailing dot", slugify("Kết thúc bằng dấu chấm."), "ket-thuc-bang-dau-cham")
    long_slug = slugify("A" * 200)
    check("slug: max length", len(long_slug) <= 60, True)
    check("slug: diacritics fold together",
          slugify("Đặc tả dữ liệu") == slugify("Dac ta du lieu"), True)
    check("slug: case folds together",
          slugify("Read Path") == slugify("read path"), True)
    check("slug: reserved device name", slugify("NUL"), "nul-node")
    check("slug: empty input", slugify("→ ← ↑"), "untitled")

    taken: set[str] = set()
    check("slug: dedup 1", unique_slug("tong-quan", taken), "tong-quan")
    check("slug: dedup 2", unique_slug("tong-quan", taken), "tong-quan-2")
    check("slug: dedup 3", unique_slug("tong-quan", taken), "tong-quan-3")

    # identifier segments keep their case; prose segments do not
    check("id: identifier passes through", safe_id_segment("BE-INV-09"), "BE-INV-09")
    check("id: contract passes through", safe_id_segment("C-01"), "C-01")
    check("id: unsafe id falls back to slug",
          safe_id_segment("Đặc tả: dữ liệu"), "dac-ta-du-lieu")
    check("id: reserved device name still guarded", safe_id_segment("NUL"), "nul-node")
    check("id: trailing dot rejected", safe_id_segment("BE-INV-09."), "be-inv-09")

    guard = CaseGuard()
    check("caseguard: first is clean", guard.check("BE-INV-09"), None)
    check("caseguard: same again is clean", guard.check("BE-INV-09"), None)
    check("caseguard: case twin is caught", guard.check("be-inv-09"), "BE-INV-09")

    # content_sha must cover the unit's own rows and nothing else
    wbs_sample = "\n".join([
        "│   ├── SCR-CHK-CHECKOUT     Payment Checkout",
        "| SCR-CHK-CHECKOUT | Màn thanh toán | consumes: BE-PG2-02 | BL: CHK |",
        "| WGT-CHK-OTP | Ô nhập OTP | used_by: SCR-CHK-CHECKOUT | BL: CHK |",
        "| BE-PG2-02 | Giao dịch | — | BL: PG2 |",
    ])
    block = unit_source_block(wbs_sample, "SCR-CHK-CHECKOUT")
    check("content_sha: subject rows only", len(block.split("\n")), 2)
    check("content_sha: a mention does not pull the row in",
          "WGT-CHK-OTP" in block, False)
    check("content_sha: tree line counts as subject", "├──" in block, True)

    # version comparison — the corpus spells the same version two ways
    check("version: v1 is not behind v1.0", version_behind("v1", "v1.0"), False)
    check("version: v1.0 is not behind v1", version_behind("v1.0", "v1"), False)
    check("version: v1 is behind v2.0", version_behind("v1", "v2.0"), True)
    check("version: v2 is not behind v1", version_behind("v2", "v1"), False)
    check("version: v1.2 is behind v1.3", version_behind("v1.2", "v1.3"), True)
    check("version: max picks the highest",
          max(["v1", "v10", "v2"], key=parse_version), "v10")

    # the id header, in all four comment styles the corpus uses
    for sample, want in [
        ("// id: BE-INV-09 | dd_version: v1", ("BE-INV-09", "v1")),
        ("/* id: SCR-POR-INV-LIST | dd_version: v1.2 */", ("SCR-POR-INV-LIST", "v1.2")),
        ("# id: INT-DASH-01 | dd_version: v3", ("INT-DASH-01", "v3")),
        ("<!-- id: WGT-CHK-HEADER | dd_version: v2 -->", ("WGT-CHK-HEADER", "v2")),
        ("  // id: BE-PG2-12", ("BE-PG2-12", None)),
    ]:
        found = _ID_HEADER.match(sample)
        got = (found.group("id"), found.group("version")) if found else None
        check(f"header: {sample[:28]}", got, want)
    check("header: a five-segment frontend id is not dropped",
          bool(_ID_HEADER.match("// id: WGT-POR-INV-SEND-DIALOG | dd_version: v1")), True)
    check("header: prose mentioning id: is not a header",
          _ID_HEADER.match("const x = 1; // see id: BE-INV-09"), None)

    # merge_preserving must leave link-owned fields alone
    merged = merge_preserving(
        {"type": "wbs-unit", "title": "new"},
        {"type": "wbs-unit", "title": "old", "built_as": ["code-file/a"],
         "verified": [{"by": "human:x", "at": "z"}]},
        frozenset({"built_as"}),
    )
    check("merge: family value wins for its own key", merged["title"], "new")
    check("merge: link-owned field survives", merged["built_as"], ["code-file/a"])
    check("merge: human field survives", len(merged["verified"]), 1)

    # normalisation and hashing — a CRLF checkout must not restate the corpus
    check("hash: CRLF == LF",
          sha256_text("a\r\nb\r\n"), sha256_text("a\nb\n"))
    check("hash: trailing spaces ignored",
          sha256_text("a   \nb\n"), sha256_text("a\nb\n"))
    check("hash: BOM ignored", sha256_text("\ufeffa\n"), sha256_text("a\n"))

    # exclude — including the Windows-shaped path that silently defeats it
    excl = ExcludeSet(DEFAULTS["exclude"])
    check("exclude: bundle eats itself",
          excl.matches("NTAPP-output/.okf/contract/C-01.md") is not None, True)
    check("exclude: nested _parts",
          excl.matches("NTAPP-output/Stage_4_Design/feature_design_parts/a.md") is not None, True)
    check("exclude: archive", excl.matches("NTAPP-output/archive/_v1/x.md") is not None, True)
    check("exclude: node_modules",
          excl.matches("fe/node_modules/pkg/index.js") is not None, True)
    check("exclude: master survives",
          excl.matches("NTAPP-output/Stage_4_Design/detailed_design/BE-INV-09_detailed_design.md"),
          None)
    windows_style = to_posix_rel(
        r"C:\repo\NTAPP-output\Stage_4_Design\feature_design_parts\a.md", r"C:\repo")
    check("exclude: windows path normalises", windows_style,
          "NTAPP-output/Stage_4_Design/feature_design_parts/a.md")
    check("exclude: windows path still filtered",
          excl.matches(windows_style) is not None, True)

    # YAML subset round-trip
    sample = yaml_load(
        "okf:\n"
        "  exclude:\n"
        '    - "**/.okf/**"\n'
        "    - \"**/archive/**\"\n"
        "  reserved_dirs: [archive, assets, test]\n"
        "  code_repos:\n"
        "    - {name: invoice-service, path: ../paybiz-invoice-service}\n"
        "  families:\n"
        "    design-section:\n"
        "      adapter: heading-split\n"
        "      split_level: [2]\n"
        "      min_nodes: 400\n"
        "      goal: >\n"
        "        Resolve đúng một mục\n"
        "        thay vì nạp cả file.\n"
        "      notes:\n"
        '        - text: "Index thắng."\n'
        '          author: "human:anhln32"\n'
    )
    okf = sample.get("okf", {})
    check("yaml: exclude list", okf.get("exclude"), ["**/.okf/**", "**/archive/**"])
    check("yaml: flow list", okf.get("reserved_dirs"), ["archive", "assets", "test"])
    check("yaml: list of flow maps", okf.get("code_repos"),
          [{"name": "invoice-service", "path": "../paybiz-invoice-service"}])
    family = (okf.get("families") or {}).get("design-section", {})
    check("yaml: nested family adapter", family.get("adapter"), "heading-split")
    check("yaml: split_level is a list", family.get("split_level"), [2])
    check("yaml: min_nodes int", family.get("min_nodes"), 400)
    check("yaml: folded scalar", family.get("goal"), "Resolve đúng một mục thay vì nạp cả file.")
    check("yaml: block list of maps", family.get("notes"),
          [{"text": "Index thắng.", "author": "human:anhln32"}])

    # frontmatter round-trip through the emitter
    fields = {
        "type": "design-section",
        "title": "BE-INV-09 §4 — Đặc tả dữ liệu & tích hợp",
        "tags": ["INV", "read-path", "invoice-link/SLICE-3-danh-sach-hoa-don"],
        "generated": {"by": "heading-split/v1", "at": "2026-08-15T09:12:00Z"},
        "verified": [{"by": "human:anhln32", "at": "2026-08-15T14:03:00Z"}],
        "status": "stable",
        "implements": ["contract/C-39"],
    }
    reparsed, body = split_frontmatter(render_node(fields, "body text"))
    check("frontmatter: title survives", reparsed.get("title"), fields["title"])
    check("frontmatter: tags survive", reparsed.get("tags"), fields["tags"])
    check("frontmatter: generated survives", reparsed.get("generated"), fields["generated"])
    check("frontmatter: verified survives", reparsed.get("verified"), fields["verified"])
    check("frontmatter: body survives", body.strip(), "body text")

    # Read-modify-write must be a fixed point. The link pass reads a node, edits
    # one field and writes it back; if that round trip is not stable the bundle
    # drifts a line at a time and every pass reports work it did not really do.
    once = render_node(fields, "# Tiêu đề\n\nĐoạn thân bài.")
    twice = render_node(*split_frontmatter(once))
    thrice = render_node(*split_frontmatter(twice))
    check("frontmatter: round-trip is a fixed point", twice, once)
    check("frontmatter: still stable on a third pass", thrice, once)

    # Values carrying a quote or a backslash. The corpus has them — a WBS
    # description reads: Bổ sung dimension "nguồn thu".
    for awkward in [
        'Bổ sung dimension "nguồn thu" cho báo cáo',
        r"Đường dẫn C:\Users\x — ký tự lạ",
        'Cả hai: "trích dẫn" và \\ gạch ngược',
        "Dấu # không phải chú thích ở đây",
        "Khoá: giá trị — có dấu hai chấm",
    ]:
        parsed, _ = split_frontmatter(render_node({"type": "t", "title": awkward}, "b"))
        check(f"escape: {awkward[:26]}", parsed.get("title"), awkward)
    nested = {"type": "t", "sources": [{"resource": 'a "b" c'}], "tags": ['x "y"']}
    reread, _ = split_frontmatter(render_node(nested, "b"))
    check("escape: quote inside a flow map", reread.get("sources"), nested["sources"])
    check("escape: quote inside a flow list", reread.get("tags"), nested["tags"])

    # preservation, idempotence, lock, deprecation — on a scratch bundle
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config = Config(root, {"output_folder": str(root / "out")}, {})
        bundle = Bundle(config)
        bundle.ensure_scaffold()

        node = Node("design-section/BE-INV-09/04-du-lieu",
                    {"type": "design-section", "title": "Dữ liệu", "content_sha": "abc"},
                    "section body")
        check("write: first pass creates", bundle.write_node(node, "process:okf-projector"),
              "created")
        check("write: second pass is a no-op",
              bundle.write_node(node, "process:okf-projector"), "unchanged")

        # a human signs, then the machine reprojects the same source
        cmd_verify_fields, cmd_verify_body = bundle.read_node(node.node_id)
        cmd_verify_fields["verified"] = [{"by": "human:anhln32", "at": "2026-08-16T00:00:00Z"}]
        cmd_verify_fields["reviewer_note"] = "kiểm tay 16/08"
        write_text(bundle.node_path(node.node_id),
                   render_node(cmd_verify_fields, cmd_verify_body))

        node.fields["content_sha"] = "def"  # source changed → full reprojection
        bundle.write_node(node, "process:okf-projector")
        after, _ = bundle.read_node(node.node_id)
        check("preserve: verified survives reprojection",
              after.get("verified"), [{"by": "human:anhln32", "at": "2026-08-16T00:00:00Z"}])
        check("preserve: unknown human key survives",
              after.get("reviewer_note"), "kiểm tay 16/08")
        check("preserve: machine key was replaced", after.get("content_sha"), "def")
        check("status: verified promotes draft to stable", after.get("status"), "stable")

        # `_index.md` is a map OF the bundle, not a part of it.  Were it ever
        # counted as a node, every total the graph reports would drift up by one
        # per type — and silently, because an index file looks exactly like a
        # node file sitting in a node directory.  It would also show up as a
        # stale id and get deprecated on the next pass.
        ids_before = bundle.existing_ids()
        bundle.write_type_index(
            "design-section",
            {"goal": "Resolve đúng MỘT mục.", "source_glob": ["a/*.md", "b/*.md"]},
            [node])
        index_path = bundle.root / "design-section" / TYPE_INDEX_NAME
        check("type-index: written at the type root", index_path.exists(), True)
        check("type-index: never counted as a node", bundle.existing_ids(), ids_before)
        check("type-index: absent from its own family listing",
              "design-section/_index" in bundle.existing_ids("design-section"), False)
        listing = read_text(index_path)
        check("type-index: carries the family goal",
              "Resolve đúng MỘT mục." in listing, True)
        check("type-index: list source joined, not a Python repr",
              "a/*.md, b/*.md" in listing, True)
        check("type-index: links the node it lists",
              "BE-INV-09/04-du-lieu.md)" in listing, True)
        bundle.write_type_index("design-section", {"source": "x.md"}, [node])
        check("type-index: a missing goal is rendered, not skipped",
              "chưa khai `goal`" in read_text(index_path), True)
        bundle.write_type_index("design-section", {}, [])
        check("type-index: no nodes writes nothing new",
              "chưa khai `goal`" in read_text(index_path), True)

        bundle.deprecate(node.node_id)
        gone, _ = bundle.read_node(node.node_id)
        check("deprecate: marks, does not delete", gone.get("status"), "deprecated")
        check("deprecate: keeps the file", bundle.node_path(node.node_id).exists(), True)

        # The shrink guard reads `is_deprecated` to tell a fresh loss from a
        # tombstone still inside its grace period.  Without the split it raises
        # on every run until the sweep, and a guard that always fires is one the
        # operator learns to silence with `--allow-shrink` — the exact reflex
        # that lets a real regression through.
        live = Node("design-section/BE-INV-09/05-giao-dien",
                    {"type": "design-section", "title": "Giao diện", "content_sha": "ghi"},
                    "another section")
        bundle.write_node(live, "process:okf-projector")
        check("shrink guard: tombstone is not a fresh loss",
              bundle.is_deprecated(node.node_id), True)
        check("shrink guard: a live node is not a tombstone",
              bundle.is_deprecated(live.node_id), False)
        check("shrink guard: filters tombstones, keeps genuine losses",
              [nid for nid in sorted([node.node_id, live.node_id])
               if not bundle.is_deprecated(nid)],
              [live.node_id])

        check("deprecate: grace period holds",
              bundle.sweep_deprecated(30), [])
        check("deprecate: sweep after grace removes",
              bundle.sweep_deprecated(-1), [node.node_id])
        check("type-index: survives the deprecation sweep", index_path.exists(), True)

        lock = BundleLock(config.root, 7200)
        lock.acquire()
        second = BundleLock(config.root, 7200)
        try:
            second.acquire()
            failures.append("lock: a second concurrent run was allowed in")
        except LockedError:
            pass
        lock.release()

        check("adapter: unknown name fails loudly",
              isinstance(_expect_raise(lambda: resolve_adapter("nope")), UnknownAdapterError),
              True)

    # ── heading-split ────────────────────────────────────────────────────────
    doc = "\n".join([
        "# Tài liệu", "", "Mở đầu.", "",
        "## 1. TỔNG QUAN", "", "Câu đầu tiên. Câu thứ hai không được lấy.", "",
        "### 1.1 Chi tiết", "", "Nội dung 1.1.", "",
        "#### 1.1.1 Sâu hơn", "", "Nội dung sâu.", "",
        "## 2. DỮ LIỆU", "", "```", "## Không phải heading", "```", "",
        "| Cột | Giá trị |", "|---|---|", "| a | b |", "",
        "### 2.1 Bảng", "", "Đuôi.",
    ])

    marks = [(level, title) for level, title, _ in iter_headings(doc)]
    check("split: fenced `## ` is not a heading",
          any(title == "Không phải heading" for _, title in marks), False)
    check("split: heading count", len(marks), 6)

    at_two = split_sections(doc, {2})
    check("split: [2] gives two sections", [s["title"] for s in at_two],
          ["1. TỔNG QUAN", "2. DỮ LIỆU"])
    check("split: an H2 section keeps its H3 children when only [2] is declared",
          "### 1.1 Chi tiết" in at_two[0]["text"], True)
    check("split: subsection outline lists the deeper headings",
          [t for _, t in at_two[0]["subsections"]], ["1.1 Chi tiết", "1.1.1 Sâu hơn"])

    at_two_three = split_sections(doc, {2, 3})
    check("split: [2,3] gives four sections", len(at_two_three), 4)
    check("split: declaring H3 stops the H2 body at its first child",
          "### 1.1 Chi tiết" in at_two_three[0]["text"], False)
    check("split: prose under an H4 stays with its H3 parent",
          "Nội dung sâu." in at_two_three[1]["text"], True)
    check("split: an H2 container still lists children it no longer contains",
          [t for _, t in at_two_three[0]["subsections"]], ["1.1 Chi tiết", "1.1.1 Sâu hơn"])
    check("split: the outline stops at the next same-level heading",
          [t for _, t in at_two_three[2]["subsections"]], ["2.1 Bảng"])

    # The partition property the DoD turns on: no line counted twice, none lost.
    body_lines = doc.split("\n")[4:]          # everything from the first split heading
    covered = "\n".join(s["text"] for s in at_two_three).split("\n")
    check("split: sections partition the document exactly",
          len([ln for ln in covered if ln.strip()]),
          len([ln for ln in body_lines if ln.strip()]))

    check("split: description is the first sentence only",
          first_sentence("\n".join(at_two[0]["text"].split("\n")[1:])),
          "Câu đầu tiên.")
    check("split: a table-first section falls back to its first row",
          first_sentence("\n".join(at_two[1]["text"].split("\n")[1:])), "Cột · Giá trị")
    check("split: an empty section yields no invented description",
          first_sentence("\n\n"), "")
    check("split: markdown noise is stripped from the description",
          first_sentence("**Đậm** và `mã` và [liên kết](http://x). Sau."),
          "Đậm và mã và liên kết.")

    fm_doc = "---\nid: BE-INV-03\nmodule: INV (invoice-service)\nslice: SLICE-2\n" \
             "version: v2.0\nparent_techspec: a/b.md\n---\n\n# T\n"
    meta_fm = doc_meta(fm_doc)
    check("meta: frontmatter unit", meta_fm["unit"], "BE-INV-03")
    check("meta: frontmatter module is the leading token", meta_fm["module"], "INV")
    check("meta: frontmatter slice", meta_fm["slice"], "SLICE-2")
    check("meta: parents collected", meta_fm["parents"], ["a/b.md"])

    bq_doc = "# T\n\n> **Unit:** `BE-INV-09` · **module:** `INV` (container x)\n" \
             "> **Slice:** `SLICE-3` — Danh sách hóa đơn\n" \
             "> **Nguồn:** `INV_techspec.md` v1.0 · `project_wbs.md` dòng 319\n"
    meta_bq = doc_meta(bq_doc)
    check("meta: blockquote unit", meta_bq["unit"], "BE-INV-09")
    check("meta: blockquote module", meta_bq["module"], "INV")
    check("meta: blockquote slice", meta_bq["slice"], "SLICE-3")
    check("meta: Nguồn line kept verbatim",
          "INV_techspec.md" in meta_bq["note"], True)
    check("meta: a document with neither shape yields blanks",
          doc_meta("# T\n\nprose\n")["unit"], "")

    index = {"a.md": ["x/a.md"], "b.md": ["x/b.md", "y/b.md"]}
    check("source: an unambiguous name resolves", resolve_named_source("a.md", index), "x/a.md")
    check("source: an ambiguous name is left unresolved",
          resolve_named_source("b.md", index), "")
    check("source: an unknown name is left unresolved",
          resolve_named_source("c.md", index), "")

    decomposed = unicodedata.normalize("NFD", "BẢNG LỊCH SỬ THAY ĐỔI")
    check("skip: matches across case and NFC/NFD",
          fold("lịch sử thay đổi") in fold(decomposed), True)

    check("inline: underscore in a filename survives",
          strip_inline("`INV_techspec.md` và **đậm**"), "INV_techspec.md và đậm")
    check("outline: fallback lists the subheadings",
          outline_description([(3, "4.1 A"), (3, "4.2 B")]),
          "2 mục con: 4.1 A; 4.2 B")
    check("outline: fallback truncates past four",
          outline_description([(3, f"{i}") for i in range(9)]).endswith("; …"), True)
    check("outline: no subsections means no invented description",
          outline_description([]), "")
    check("clip: a cut never lands on a trailing space",
          clip("mot hai ba bon nam sau bay", 12).endswith(" "), False)

    # A value ending in a space used to survive `render_node` but not
    # `read_text`, so the probe disagreed with the file forever.
    trailing = render_node({"type": "t", "title": "x"}, "- ket thuc bang khoang trang \n")
    check("render: output survives its own normalisation",
          normalise_text(trailing), trailing)

    # A declared section id outlives a reworded heading; without one the node's
    # path is editorial prose and every edge to it breaks on a copy-edit.
    declared_doc = ("## Cũ\n<!-- okf-id: data-integration -->\n\nA.\n"
                    "## Không khai\n\nB.\n")
    marked = split_sections(declared_doc, {2})
    check("section id: read from the marker", marked[0]["okf_id"], "data-integration")
    check("section id: absent when not declared", marked[1]["okf_id"], "")
    check("section id: the marker is not mistaken for the lede",
          first_sentence("\n".join(marked[0]["text"].split("\n")[1:])), "A.")
    renamed = split_sections(
        declared_doc.replace("## Cũ", "## Tên hoàn toàn mới"), {2})
    check("section id: survives a heading rename",
          renamed[0]["okf_id"], marked[0]["okf_id"])

    # ── P3: whole-file, heading-blocks, slice-manifest, json-doc ─────────────

    # A bullet marker is `-`/`*`/`+` followed by a space. The old `lstrip("-*+ ")`
    # could not tell one from the opening `**` of a bold run.
    check("p3: bullet marker is stripped",
          first_sentence("- **pom.xml:** thêm actuator."), "pom.xml: thêm actuator.")
    check("p3: numbered marker is stripped, and does not become the description",
          first_sentence("1. **Un-bundling:** Tách rời từng hệ thống ngoài."),
          "Un-bundling: Tách rời từng hệ thống ngoài.")
    check("p3: a bold run at line start keeps its emphasis markers",
          first_sentence("**Đậm** rồi thường."), "Đậm rồi thường.")

    # The lead-label rule is opt-in, because on P4 sections the bolded label is
    # usually the tightest summary anyone wrote.
    labelled = "**Mục đích chính.** `svc` là service lõi. Câu hai."
    check("p3: lead label kept by default", first_sentence(labelled), "Mục đích chính.")
    check("p3: lead label dropped when the family asks",
          first_sentence(labelled, drop_lead_label=True), "svc là service lõi.")
    check("p3: the colon form is left alone even when dropping is on",
          first_sentence("**Mục đích chính:** svc là service lõi.", drop_lead_label=True),
          "Mục đích chính: svc là service lõi.")

    svc_doc = "\n".join([
        "---", "repo: paybiz-x", "---", "", "# Paybiz X — Tài liệu", "",
        "> **Phiên bản:** 1.0 — **Ngày tạo:** 2026-07-15 — **Repo:** paybiz-x", "",
        "Đây mới là câu mô tả thật.", "",
        "## Mục lục", "", "1. Executive Summary", "",
        "## 1. Executive Summary", "", "**Mục đích chính.** X là service lõi. Hai.", "",
        "## 2. Kiến trúc", "", "Nội dung.",
    ])
    check("p3: title comes from the H1", doc_title(svc_doc), "Paybiz X — Tài liệu")
    check("p3: a metadata blockquote is not the description",
          doc_lede(svc_doc), "Đây mới là câu mô tả thật.")
    check("p3: description_section reaches past the lede",
          section_lede(svc_doc, "Executive Summary", drop_lead_label=True),
          "X là service lõi.")
    check("p3: outline honours skip_headings",
          [t for _, t in doc_outline(svc_doc, {2}, [fold("mục lục")])],
          ["1. Executive Summary", "2. Kiến trúc"])

    # A block that is nothing but a label describes what comes after it.
    bug_block = "\n".join([
        "## SLICE-3-BUG-01 — Nút xác nhận không làm gì",
        "", "- **Trạng thái:** In Progress", "- **Severity:** High",
        "- **WBS unit:** SCR-POR-INV-LIST", "- **Ngày báo:** 2026-07-29", "",
        "**Mô tả:**", "", "Nhánh xác nhận được gán một hàm rỗng. Câu hai.",
    ])
    check("p3: description_after finds the prose past the metadata",
          block_description(bug_block, "Mô tả"),
          "Nhánh xác nhận được gán một hàm rỗng.")
    check("p3: without description_after the metadata run is still skipped",
          block_description(bug_block, None),
          "Nhánh xác nhận được gán một hàm rỗng.")
    fields_found = block_fields(bug_block)
    check("p3: block fields are read by label",
          fields_found.get(fold("WBS unit")), "SCR-POR-INV-LIST")
    check("p3: block field lookup folds case and composition",
          fields_found.get(fold("severity")), "High")
    check("p3: one id stays a string", split_ids("SCR-POR-INV-LIST"), "SCR-POR-INV-LIST")
    check("p3: several ids become a list",
          split_ids("BE-INV-09, SCR-POR-INV-LIST"), ["BE-INV-09", "SCR-POR-INV-LIST"])

    # The whitelist is the point: a working note must not become a bug node.
    key_pattern = re.compile(r"^(SLICE-\d+-BUG-\d+)\s*[—–-]\s*(.+)$")
    check("p3: a note heading does not match the key pattern",
          bool(key_pattern.match("Ghi chú xử lý — 2026-08-11 (tulv19)")), False)
    check("p3: a bug heading does match",
          key_pattern.match("SLICE-3-BUG-01 — Nút xác nhận").group(1), "SLICE-3-BUG-01")

    # ADR references — the two-series trap.  `designed-adr` (Stage 1 files)
    # numbers four wide; `runtime-adr` (`architecture_design.md` §6) runs a
    # SEPARATE three-wide series, and the width is the only thing separating them
    # in running prose.
    adrs = {"by_number": {"0002": "designed-adr/0002-x", "0003": "designed-adr/0003-y"},
            "widths": {4}}
    check("p3: adr refs resolve", governed_from("theo ADR 0002 và ADR-0003", adrs),
          ["designed-adr/0002-x", "designed-adr/0003-y"])
    check("p3: a node does not govern itself",
          governed_from("xem ADR 0002", adrs, "designed-adr/0002-x"), [])

    stray: set = set()
    check("p3: a narrower number is a DIFFERENT series, not this one",
          governed_from("theo ADR-002 và ADR-003", adrs, strays=stray), [])
    check("p3: and it is reported rather than dropped in silence",
          stray, {"002", "003"})
    check("p3: both series on one line — only the matching width wins",
          governed_from("ADR 0002 (Stage 1) vs ADR-002 (Stage 2)", adrs),
          ["designed-adr/0002-x"])
    # A project whose ADR files are three wide must still work.
    narrow = {"by_number": {"002": "designed-adr/002-x"}, "widths": {3}}
    check("p3: width comes from the files, not hard-coded to four",
          governed_from("theo ADR-002", narrow), ["designed-adr/002-x"])

    # Two series at once.  The index is keyed by the literal digit string, so
    # "001" and "0001" are different keys and route to different families with
    # no extra machinery — this is what makes the merge safe.
    both = {"by_number": {"0001": "designed-adr/0001-a", "001": "runtime-adr/ADR-001"},
            "known": {"0001", "001"}, "widths": {3, 4}}
    check("p4: designed and runtime resolve to different nodes from one line",
          governed_from("ADR 0001 quyết định, ADR-001 triển khai", both),
          ["designed-adr/0001-a", "runtime-adr/ADR-001"])

    # Declining a series is not the same as failing to recognise it.  A
    # `runtime-adr` names its own number in its own heading; reporting that as an
    # unknown number told the operator all five runtime ADRs were strays.
    declined = {"by_number": {"0001": "designed-adr/0001-a"},
                "known": {"0001", "001"}, "widths": {4}}
    stray2: set = set()
    check("p4: a series this family opted out of yields no edge",
          governed_from("ADR-001 nói vậy", declined, strays=stray2), [])
    check("p4: …and is NOT a stray — it is a known number, declined on purpose",
          stray2, set())
    stray3: set = set()
    governed_from("theo ADR-9999", declined, strays=stray3)
    check("p4: a number no series claims is still a stray", stray3, {"9999"})

    # Node id and stored number want different shapes: `runtime-adr/ADR-001`
    # reads well as an id, but `adr_number: ADR-001` cannot be compared against
    # designed-adr's `0001`.  `key_strip` is what separates the two.
    check("p4: key_strip leaves the digits that make series comparable",
          re.compile(r"^ADR-").sub("", "ADR-001"), "001")
    check("p4: adr_digits reads a number out of either series' key shape",
          [adr_digits("0004-tach-den-han"), adr_digits("ADR-004"), adr_digits("x")],
          ["0004", "004", ""])

    check("p3: json path walks nested objects",
          dotted({"_meta": {"dd_version": "v2"}}, "_meta.dd_version"), "v2")
    check("p3: a missing json path is None", dotted({"a": 1}, "a.b.c"), None)
    check("p3: count label uses the document's own word",
          [count_label("data_bindings.controls"), count_label("_drift_notes")],
          ["controls", "drift notes"])

    # Every edge field an adapter writes must be in the audit's registry, or it
    # is the one edge type nothing ever validates.
    check("p3: edge registry covers the P3 edges",
          {"blocked_by", "enhanced_by", "slice_units", "slice"} <= set(EDGE_KEYS), True)
    check("p3: every edge key is a machine key",
          set(EDGE_KEYS) <= MACHINE_KEYS, True)

    # A single-valued edge is a string, and a string is iterable.  Walking one
    # as a list yields characters, which is how 32 good edges became 1859
    # reported orphans.
    def edge_targets(value):
        targets = value or []
        return [targets] if isinstance(targets, str) else list(targets)

    check("p4: a single-valued edge is one target, not one per character",
          edge_targets("slice/invoice-link/slice-3-x"),
          ["slice/invoice-link/slice-3-x"])
    check("p4: a list-valued edge is unchanged",
          edge_targets(["a/b", "c/d"]), ["a/b", "c/d"])
    check("p4: an absent edge is no targets", edge_targets(None), [])

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "slices"
        (base / "banking-hub").mkdir(parents=True)
        for rel, feature in (("SLICE-3-danh-sach.md", "invoice-link"),
                             ("banking-hub/SLICE-3-doi-soat.md", "banking-hub")):
            (base / rel).write_text(
                f"---\nslice_id: SLICE-3\nfeature: {feature}\ntitle: T\n---\n\n# T\n",
                encoding="utf-8")

        class _Cfg:
            def get(self, key, default=None):
                return {"reserved_dirs": []}.get(key, default)

        class _Ctx:
            output_folder = Path(tmp)
            config = _Cfg()

        index = slice_index(_Ctx(), {"slice_dir": "slices"})
        check("p3: slice index is keyed by feature",
              sorted(index["by_feature"]), ["banking-hub", "invoice-link"])
        # The whole reason `slice_id` is not identity: two features, one number.
        check("p3: an id claimed by two features is dropped from the flat view",
              "SLICE-3" in index["flat"], False)
        check("p3: and is recorded as ambiguous", index["ambiguous"], {"SLICE-3"})
        check("p3: a nested file resolves through its own directory",
              resolve_slice("bug", index, "SLICE-3-BUG-01",
                            base / "banking-hub" / "BUGS-SLICE-3.md",
                            re.compile(r"^(SLICE-\d+)-BUG-"))["feature"],
              "banking-hub")
        # A flat file cannot resolve once two features answer to the name — and
        # that must raise rather than pick one.
        ambiguous = _expect_raise(
            lambda: resolve_slice("bug", index, "SLICE-3-BUG-01",
                                  base / "BUGS-SLICE-3.md",
                                  re.compile(r"^(SLICE-\d+)-BUG-")))
        check("p3: an ambiguous flat reference raises", isinstance(ambiguous, OkfError), True)
        check("p3: and the error names both owners",
              "banking-hub" in str(ambiguous) and "invoice-link" in str(ambiguous), True)

        # A manifest with no feature and no feature directory is not guessable.
        (base / "SLICE-9-khong-ro.md").write_text(
            "---\nslice_id: SLICE-9\ntitle: T\n---\n", encoding="utf-8")
        no_feature = _expect_raise(lambda: slice_index(_Ctx(), {"slice_dir": "slices"}))
        check("p3: a manifest without `feature:` raises",
              isinstance(no_feature, OkfError), True)
        check("p3: and the error says how to fix it",
              "feature:" in str(no_feature), True)

    if failures:
        print(f"self-test: {len(failures)} FAILED\n")
        for failure in failures:
            print(f"  ✗ {failure}")
        return 1
    print("self-test: all checks passed")
    return 0


def _expect_raise(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 — the test wants the exception object
        return exc
    return None


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okf_project.py",
        description="Project NTAPP artifacts into an OKF v0.2 bundle.",
    )
    parser.add_argument("--root", help="project (spec repo) root; default: auto-detect")
    parser.add_argument("--config", help="path to Layer 2 .bmm-config.yaml")
    parser.add_argument("--family", action="append", default=[],
                        help="restrict to one family (repeatable)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full", action="store_true",
                      help="reproject everything, ignoring hashes (still preserves verified[])")
    mode.add_argument("--audit", action="store_true", help="checks and report only; writes no nodes")
    mode.add_argument("--dry-run", action="store_true", help="list families and config; touch nothing")
    mode.add_argument("--verify", metavar="NODE", help="append your signature to a node")
    mode.add_argument("--self-test", action="store_true", help="run the built-in checks")
    parser.add_argument("--actor", help=(
        "who is running this pass, recorded as `generated.by` on every node "
        "written (default: config `actor_default`, else process:okf-projector). "
        "A model-driven pass MUST set this — a node extracted by a model and a "
        "node sliced by a regex do not carry the same trust."))
    parser.add_argument("--json", action="store_true", help="machine-readable output where supported")
    parser.add_argument("--allow-shrink", action="store_true",
                        help="permit a family to end up with fewer nodes than it has on disk")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.self_test:
        return _self_test()

    project_root = Path(args.root).resolve() if args.root else find_project_root(Path.cwd())
    config_path = Path(args.config).resolve() if args.config else None

    if config_path and not config_path.exists():
        print(f"okf: skipped — config not found: {config_path}")
        return 0

    try:
        config, notes = load_config(project_root, config_path)
    except OSError as exc:
        print(f"okf: skipped — cannot read config ({exc})")
        return 0

    if args.dry_run:
        return cmd_dry_run(config, notes)

    bundle = Bundle(config)

    if args.verify:
        return cmd_verify(config, bundle, args.verify)

    if args.audit:
        return cmd_audit(config, bundle, args.json)

    # `by` names who ran the pass, and that is what separates a deterministic
    # projection from a model-driven one (see `heading-split`).  The key existed
    # in the defaults and the comment described the behaviour, but nothing read
    # either: every node on disk claimed `process:okf-projector`, whatever
    # produced it.  Three adapters had tried to answer this locally by declaring
    # `generated: {by: "<adapter>/v1"}`; those never reached disk and have been
    # removed rather than honoured — the adapter is not who ran the pass.
    actor = str(args.actor or config.get("actor_default") or f"process:{PRODUCER}")
    try:
        # Both guards run before the lock, because taking the lock is itself a
        # write: it creates `.okf/` to hold the lock file.  Checking after it
        # would mean every refusal still left the bundle directory behind.
        if not select_families(config, args.family or None):
            print("okf: no families declared — nothing to project")
            return 0
        with BundleLock(config.root, int(config.get("lock_ttl_seconds") or 7200)):
            return cmd_project(config, bundle, actor, full=args.full,
                               only=args.family or None,
                               allow_shrink=args.allow_shrink)
    except LockedError as exc:
        print(f"okf: skipped: locked — {exc}")
        return 0
    except UnknownAdapterError as exc:
        print(f"okf: {exc}", file=sys.stderr)
        return 2
    except OkfError as exc:
        print(f"okf: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
