#!/usr/bin/env python3
"""Slice path resolution — ONE implementation, shared by every bug skill.

Why this file exists
--------------------
Four skills used to resolve slice/bug paths by pasting a glob into prose.  An
audit on 2026-08-16 found the framework holding *two different answers* to the
single question "where do slice manifests live":

    Stage_2_Architecture/slices/   ← 6 files (correct; the dir that exists)
    Stage_5_Build_Verify/slices/   ← 3 files (does not exist anywhere)

The wrong three were all in the bug branch, so the bug branch's "identify the
SLICE" step had been dead on paybiz for as long as those lines existed.  Nothing
in the repo made the majority right — it just happened to be larger.  Patching
the three lines would make the count 9-0 today and leave the next author with
the same coin-flip, so the fix is a module with the authority instead.

Three kinds of empty
--------------------
The old failure was not the wrong path; it was that the wrong path returned
*nothing* and nothing is indistinguishable from "this slice is clean".  So every
lookup here reports which empty it hit:

    directory missing   → `warnings` gets a line, `ok` is False
    directory present, nothing matched → `ok` is True, list is empty
    matched             → `ok` is True, list is populated

A caller that only looks at `len(bug_files)` gets the old bug back.  Callers are
expected to surface `warnings`.

Matching rules (the other two live defects)
-------------------------------------------
* **Boundary, not prefix.**  `BUGS-SLICE-2*` matches BUGS-SLICE-2, -20, -21, -24.
  Ids are parsed out of the filename and compared as values, never as prefixes.
* **Zero-pad folded one way.**  Skills write `SLICE-01`; disk has `SLICE-1-…`.
  Both fold to the canonical unpadded `SLICE-1` before comparison.

Layout tolerance
----------------
Both the flat layout and a one-level feature-directory layout are searched, so
moving `Bugs_Issues/BUGS-*.md` into `Bugs_Issues/<feature>/BUGS-*.md` needs no
change here and no second edit to the four skills.

Stdlib only, no shell, no symlinks — runs on Windows unchanged (decision D3).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Defaults live in code (Layer 0), not in config.  Layer 1 today has exactly five
# directory keys and `slices_dir` is not one of them; adding a sixth would hit the
# non-propagation trap that §0.1 of the OKF plan is about — a new key only reaches
# projects that re-bootstrap, so every project that does not becomes a silent
# divergence.  Config may override, but is never required to be present.
DEFAULT_SLICES_DIR = "NTAPP-output/Stage_2_Architecture/slices"
DEFAULT_BUGS_DIR = "NTAPP-output/Stage_1_Discovery/Bugs_Issues"
DEFAULT_ASSETS_SUBDIR = "assets"

# `SLICE-01`, `slice-1`, or a bare `1`.  The trailing group is deliberately
# non-greedy about what follows: callers paste ids out of filenames too
# (`SLICE-10-trang-thanh-toan…`), and the slug must not become part of the id.
_SLICE_REF = re.compile(r"^(?:slice[-_]?)?(\d+)\b", re.IGNORECASE)

# A slice manifest: SLICE-<n> optionally followed by -<slug>.
_SLICE_FILE = re.compile(r"^SLICE-(\d+)(?:-.*)?\.md$", re.IGNORECASE)

# A bug log: BUGS-SLICE-<n> optionally followed by -<account>.
# paybiz has no account suffix; the framework writes one.  Both are accepted.
_BUG_FILE = re.compile(r"^BUGS-SLICE-(\d+)(?:-(.*))?\.md$", re.IGNORECASE)

# `- { id: BE-MM-08, type: backend, … }` or a block-form `- id: BE-MM-08`.
_UNIT_ID = re.compile(r"\bid:\s*([A-Za-z][A-Za-z0-9_-]*)")


class SliceRefError(ValueError):
    """The caller passed something that is not a slice reference."""


# ── roots ────────────────────────────────────────────────────────────────────

def repo_root() -> Path:
    """Same contract as slice_coverage_dag_validate.repo_root — kept identical
    on purpose; two helpers disagreeing about the root would be this file's own
    bug repeated one level up."""
    try:
        return Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        ).decode().strip())
    except Exception:
        return Path.cwd()


def spec_root(start: Path | None = None) -> Path:
    root = start or repo_root()
    cfg = root / ".bmm-config.yaml"
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*spec_repo_root:\s*['\"]?([^'\"]+)['\"]?", line)
            if m:
                rel = m.group(1).strip()
                if rel and rel != ".":
                    p = (root / rel).resolve()
                    if p.is_dir():
                        return p
    return root


def _config_override(spec: Path, key: str) -> str | None:
    """A project may pin `slices_dir:`/`bugs_dir:` in .bmm-config.yaml.  Read with
    a line regex like every other hook here — the repo has no YAML dependency and
    adding one for two optional strings is not a trade worth making."""
    env = os.environ.get("NTAPP_" + key.upper())
    if env:
        return env
    cfg = spec / ".bmm-config.yaml"
    if not cfg.exists():
        return None
    for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(rf"^\s*{re.escape(key)}:\s*['\"]?([^'\"#]+)['\"]?", line)
        if m:
            val = m.group(1).strip()
            if val:
                return val
    return None


# ── canonical ids ────────────────────────────────────────────────────────────

def canonical_slice_id(ref: str) -> str:
    """`SLICE-01` / `slice_1` / `1` / `SLICE-1-some-slug` → `SLICE-1`.

    Folding is one-way (padded → unpadded) so there is exactly one canonical
    spelling.  Folding the other way would need to know the project's pad width,
    which nothing declares.
    """
    m = _SLICE_REF.match((ref or "").strip())
    if not m:
        raise SliceRefError(
            f"{ref!r} is not a slice reference — expected SLICE-<n> (SLICE-01, "
            "slice-1 and a bare 1 are all accepted)")
    return f"SLICE-{int(m.group(1))}"


def _slice_num(canonical: str) -> int:
    return int(canonical.split("-", 1)[1])


# ── layout-tolerant listing ──────────────────────────────────────────────────

def _candidates(directory: Path) -> list[Path]:
    """Flat layout and one level of feature directories, in one list.

    Not `rglob`: unbounded depth would sweep in `assets/` (which holds no
    markdown today, but is a sibling that will grow) and any archive folder a
    project drops in.  One level is what the feature-directory move needs.
    """
    if not directory.is_dir():
        return []
    found = list(directory.glob("*.md"))
    for sub in sorted(p for p in directory.iterdir() if p.is_dir()):
        found.extend(sub.glob("*.md"))
    return sorted(found)


# ── the resolved answer ──────────────────────────────────────────────────────

@dataclass
class SlicePaths:
    ref: str
    slice_id: str
    slices_dir: Path
    bugs_dir: Path
    assets_dir: Path
    slice_files: list[Path] = field(default_factory=list)
    bug_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """False when a lookup could not be *performed* — distinct from a lookup
        that ran and found nothing."""
        return not self.warnings

    def as_dict(self) -> dict:
        return {
            "ref": self.ref,
            "slice_id": self.slice_id,
            "ok": self.ok,
            "slices_dir": str(self.slices_dir),
            "bugs_dir": str(self.bugs_dir),
            "assets_dir": str(self.assets_dir),
            "slice_files": [str(p) for p in self.slice_files],
            "bug_files": [str(p) for p in self.bug_files],
            "warnings": list(self.warnings),
        }


def resolve_slice_paths(ref: str, spec: Path | None = None) -> SlicePaths:
    spec = spec or spec_root()
    slice_id = canonical_slice_id(ref)
    num = _slice_num(slice_id)

    slices_dir = spec / (_config_override(spec, "slices_dir") or DEFAULT_SLICES_DIR)
    bugs_dir = spec / (_config_override(spec, "bugs_dir") or DEFAULT_BUGS_DIR)
    out = SlicePaths(
        ref=ref, slice_id=slice_id,
        slices_dir=slices_dir, bugs_dir=bugs_dir,
        assets_dir=bugs_dir / DEFAULT_ASSETS_SUBDIR / slice_id,
    )

    if not slices_dir.is_dir():
        out.warnings.append(
            f"slices_dir does not exist: {slices_dir} — this is NOT 'no slices'. "
            "Fix the path or the config; do not read the empty list as an answer.")
    else:
        for p in _candidates(slices_dir):
            m = _SLICE_FILE.match(p.name)
            if m and int(m.group(1)) == num:
                out.slice_files.append(p)

    if not bugs_dir.is_dir():
        out.warnings.append(
            f"bugs_dir does not exist: {bugs_dir} — this is NOT 'no bugs'.")
    else:
        for p in _candidates(bugs_dir):
            m = _BUG_FILE.match(p.name)
            if m and int(m.group(1)) == num:
                out.bug_files.append(p)

    return out


def slices_for_unit(unit_id: str, spec: Path | None = None) -> tuple[list[Path], list[str]]:
    """Slice manifests that BUILD `unit_id`, plus warnings.

    Reads the `units:` block rather than grepping the whole file, for two
    reasons.  A substring grep matches `BE-BMS-1` inside `BE-BMS-10` — the same
    boundary defect as the bug glob.  And a slice's prose legitimately names
    *other* slices' units ("SLICE-10 consumes this"), so a whole-file grep
    answers "which slices mention it", not "which slice builds it".
    """
    spec = spec or spec_root()
    warnings: list[str] = []
    slices_dir = spec / (_config_override(spec, "slices_dir") or DEFAULT_SLICES_DIR)
    if not slices_dir.is_dir():
        return [], [f"slices_dir does not exist: {slices_dir} — "
                    "this is NOT 'no slice builds that unit'."]

    wanted = (unit_id or "").strip().upper()
    if not wanted:
        raise SliceRefError("empty unit id")

    hits: list[Path] = []
    for p in _candidates(slices_dir):
        if not _SLICE_FILE.match(p.name):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            warnings.append(f"{p.name}: no frontmatter — skipped")
            continue
        end = text.find("\n---", 3)
        fm = text[3:end] if end != -1 else text
        block = fm.split("units:", 1)
        if len(block) < 2:
            continue
        if wanted in {m.group(1).upper() for m in _UNIT_ID.finditer(block[1])}:
            hits.append(p)
    return hits, warnings


# ── CLI ──────────────────────────────────────────────────────────────────────
# Skills are markdown and cannot import Python.  Without a CLI, "one shared
# implementation" degrades into four prose copies of the rule — the exact
# divergence this file was written to end.  So the CLI is the real interface.

def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key in ("slice_id", "slices_dir", "bugs_dir", "assets_dir"):
        if key in payload:
            print(f"{key}\t{payload[key]}")
    for key in ("slice_files", "bug_files", "unit_slices"):
        for item in payload.get(key, []):
            print(f"{key}\t{item}")
    for w in payload.get("warnings", []):
        print(f"WARNING\t{w}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="slice_paths.py",
        description="Resolve slice manifest / bug log / asset paths for a slice.")
    ap.add_argument("--resolve", metavar="SLICE",
                    help="slice reference (SLICE-3, SLICE-03, or 3)")
    ap.add_argument("--find-unit", metavar="UNIT-ID",
                    help="list slice manifests whose units[] build UNIT-ID")
    ap.add_argument("--root", help="spec repo root; default: auto-detect")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if not args.resolve and not args.find_unit:
        ap.error("one of --resolve or --find-unit is required")

    spec = Path(args.root).resolve() if args.root else spec_root()

    try:
        if args.find_unit:
            hits, warns = slices_for_unit(args.find_unit, spec)
            payload = {
                "unit": args.find_unit,
                "unit_slices": [str(p) for p in hits],
                "warnings": warns,
            }
            _emit(payload, args.json)
            # Exit 3 = could not look up.  Exit 0 with an empty list = looked and
            # found none.  A caller must be able to tell those apart; that
            # confusion is the defect this module exists to remove.
            return 3 if warns else 0

        out = resolve_slice_paths(args.resolve, spec)
        _emit(out.as_dict(), args.json)
        return 3 if out.warnings else 0
    except SliceRefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
