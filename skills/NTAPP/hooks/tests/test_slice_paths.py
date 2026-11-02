#!/usr/bin/env python3
"""Tests for hooks/lib/slice_paths.py.

Fixtures are synthetic and self-contained: a framework test that needs a
particular project checked out beside it is a test that stops running the day
someone clones only the framework.  The fixture reproduces the exact filename
shapes that produced the three live defects found on 2026-08-16, so the cases
are real even though the corpus is not:

    BUGS-SLICE-2.md / -20 / -21 / -24      prefix collision  (defect B)
    SLICE-09-… on disk, SLICE-9 in hand    zero-pad mismatch (defect C)
    a slices_dir that does not exist       silent empty      (defect A)

Run:   python3 hooks/tests/test_slice_paths.py
Exit:  0 all pass · 1 some failed
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / "lib"
MOD = LIB / "slice_paths.py"
sys.path.insert(0, str(LIB))
import slice_paths as sp  # noqa: E402

GREEN, RED, OFF = "\033[0;32m", "\033[0;31m", "\033[0m"
_fails: list[str] = []


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  {GREEN}ok  {OFF} {name}")
    else:
        print(f"  {RED}FAIL{OFF} {name}\n        got  {got!r}\n        want {want!r}")
        _fails.append(name)


def names(paths) -> list[str]:
    return sorted(p.name for p in paths)


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def manifest(slice_id: str, *units: str) -> str:
    body = "\n".join(f"  - {{ id: {u}, type: backend }}" for u in units)
    return f"---\nslice_id: {slice_id}\nunits:\n{body}\n---\n\n## What to build\n"


def build_fixture(root: Path) -> None:
    """A project shaped like paybiz: flat slices, flat bug logs, no account
    suffix, and the 2/20/21/24 collision that broke the old glob."""
    write(root / ".bmm-config.yaml", "spec_repo_root: .\n")
    sd = root / sp.DEFAULT_SLICES_DIR
    bd = root / sp.DEFAULT_BUGS_DIR
    write(sd / "SLICE-1-khai-bao-mc.md", manifest("SLICE-1", "BE-MM-08"))
    write(sd / "SLICE-2-tao-hoa-don.md", manifest("SLICE-2", "BE-INV-01", "BE-BMS-1"))
    write(sd / "SLICE-20-doi-soat.md", manifest("SLICE-20", "BE-BMS-10"))
    write(sd / "SLICE-21-bao-cao.md", manifest("SLICE-21", "BE-RPT-01"))
    write(sd / "SLICE-24-huy-don.md", manifest("SLICE-24", "BE-INV-09"))
    for n in (2, 20, 21, 24):
        write(bd / f"BUGS-SLICE-{n}.md", f"# bugs for slice {n}\n")


def main() -> int:
    print("── canonical_slice_id ──")
    for ref, want in [("SLICE-1", "SLICE-1"), ("SLICE-01", "SLICE-1"),
                      ("slice-1", "SLICE-1"), ("slice_1", "SLICE-1"),
                      ("1", "SLICE-1"), ("SLICE-10", "SLICE-10"),
                      ("SLICE-007", "SLICE-7"), ("SLICE-1-khai-bao", "SLICE-1"),
                      ("  SLICE-3  ", "SLICE-3")]:
        check(f"{ref!r} -> {want}", sp.canonical_slice_id(ref), want)
    for bad in ["", "SLICE-", "BE-INV-03", "abc", "SLICE-x"]:
        try:
            sp.canonical_slice_id(bad)
            check(f"{bad!r} rejected", "no error", "SliceRefError")
        except sp.SliceRefError:
            check(f"{bad!r} rejected", "SliceRefError", "SliceRefError")

    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "proj"
        build_fixture(root)

        print("\n── defect B: boundary, not prefix ──")
        # The old glob `BUGS-SLICE-2*.md` returned all four of these for SLICE-2.
        for n in (2, 20, 21, 24):
            r = sp.resolve_slice_paths(f"SLICE-{n}", root)
            check(f"SLICE-{n} -> exactly one bug file",
                  names(r.bug_files), [f"BUGS-SLICE-{n}.md"])
            check(f"SLICE-{n} -> exactly one manifest", len(r.slice_files), 1)

        print("\n── defect C: zero-pad folds one way ──")
        r = sp.resolve_slice_paths("SLICE-02", root)
        check("SLICE-02 finds SLICE-2", names(r.slice_files),
              ["SLICE-2-tao-hoa-don.md"])
        check("SLICE-02 finds its bug log", names(r.bug_files), ["BUGS-SLICE-2.md"])
        write(root / sp.DEFAULT_SLICES_DIR / "SLICE-09-padded.md",
              manifest("SLICE-09", "BE-PAD-01"))
        r = sp.resolve_slice_paths("SLICE-9", root)
        check("disk padded, query unpadded", names(r.slice_files),
              ["SLICE-09-padded.md"])
        r = sp.resolve_slice_paths("SLICE-009", root)
        check("both padded", names(r.slice_files), ["SLICE-09-padded.md"])

        print("\n── defect A: unit -> slice, and it is loud when it cannot look ──")
        hits, warns = sp.slices_for_unit("BE-MM-08", root)
        check("BE-MM-08 -> SLICE-1", names(hits), ["SLICE-1-khai-bao-mc.md"])
        check("no warnings", warns, [])
        hits, _ = sp.slices_for_unit("be-mm-08", root)
        check("unit lookup is case-insensitive", names(hits),
              ["SLICE-1-khai-bao-mc.md"])
        hits, _ = sp.slices_for_unit("BE-BMS-1", root)
        check("BE-BMS-1 does not match BE-BMS-10", names(hits),
              ["SLICE-2-tao-hoa-don.md"])
        hits, _ = sp.slices_for_unit("BE-BMS-10", root)
        check("BE-BMS-10 does not match BE-BMS-1", names(hits),
              ["SLICE-20-doi-soat.md"])
        hits, warns = sp.slices_for_unit("BE-NOPE-99", root)
        check("unknown unit: looked, found none", (hits, warns), ([], []))

        print("\n── three kinds of empty ──")
        empty = tmp / "empty"
        write(empty / ".bmm-config.yaml", "spec_repo_root: .\n")
        r = sp.resolve_slice_paths("SLICE-1", empty)
        check("dirs missing -> ok False", r.ok, False)
        check("dirs missing -> both warned", len(r.warnings), 2)
        check("dirs missing -> lists empty", (r.slice_files, r.bug_files), ([], []))
        _, warns = sp.slices_for_unit("BE-MM-08", empty)
        check("find-unit on missing dir warns", len(warns), 1)
        (empty / sp.DEFAULT_SLICES_DIR).mkdir(parents=True)
        (empty / sp.DEFAULT_BUGS_DIR).mkdir(parents=True)
        r = sp.resolve_slice_paths("SLICE-1", empty)
        check("dirs present, nothing matched -> ok True", r.ok, True)
        check("dirs present, nothing matched -> no warnings", r.warnings, [])
        r = sp.resolve_slice_paths("SLICE-1", root)
        check("slice with no bug log -> ok True, empty list",
              (r.ok, r.bug_files), (True, []))

        print("\n── layout tolerance: feature subdirectories ──")
        feat = tmp / "feat"
        write(feat / ".bmm-config.yaml", "spec_repo_root: .\n")
        write(feat / sp.DEFAULT_SLICES_DIR / "invoice-link" / "SLICE-5-x.md",
              manifest("SLICE-5", "BE-FOO-01"))
        write(feat / sp.DEFAULT_BUGS_DIR / "invoice-link" / "BUGS-SLICE-5.md")
        write(feat / sp.DEFAULT_BUGS_DIR / "invoice-link" / "BUGS-SLICE-50.md")
        r = sp.resolve_slice_paths("SLICE-5", feat)
        check("nested manifest found", names(r.slice_files), ["SLICE-5-x.md"])
        check("nested bug found, 50 not caught", names(r.bug_files),
              ["BUGS-SLICE-5.md"])
        hits, _ = sp.slices_for_unit("BE-FOO-01", feat)
        check("find-unit works nested", names(hits), ["SLICE-5-x.md"])

        print("\n── mixed layout: flat and nested at once ──")
        write(feat / sp.DEFAULT_BUGS_DIR / "BUGS-SLICE-6.md")
        write(feat / sp.DEFAULT_BUGS_DIR / "other-feature" / "BUGS-SLICE-6-dinhtq8.md")
        r = sp.resolve_slice_paths("SLICE-6", feat)
        check("both layouts returned together", names(r.bug_files),
              ["BUGS-SLICE-6-dinhtq8.md", "BUGS-SLICE-6.md"])

        print("\n── account suffix (framework naming) ──")
        acc = tmp / "acc"
        write(acc / ".bmm-config.yaml", "spec_repo_root: .\n")
        write(acc / sp.DEFAULT_BUGS_DIR / "BUGS-SLICE-6-dinhtq8.md")
        write(acc / sp.DEFAULT_BUGS_DIR / "BUGS-SLICE-6-ngocnm13.md")
        write(acc / sp.DEFAULT_BUGS_DIR / "BUGS-SLICE-60-someone.md")
        (acc / sp.DEFAULT_SLICES_DIR).mkdir(parents=True)
        r = sp.resolve_slice_paths("SLICE-6", acc)
        check("both accounts, not SLICE-60", names(r.bug_files),
              ["BUGS-SLICE-6-dinhtq8.md", "BUGS-SLICE-6-ngocnm13.md"])

        print("\n── assets_dir ──")
        r = sp.resolve_slice_paths("SLICE-06", acc)
        check("assets dir uses canonical id", r.assets_dir.name, "SLICE-6")

        print("\n── config override ──")
        ovr = tmp / "ovr"
        write(ovr / ".bmm-config.yaml",
              "spec_repo_root: .\nslices_dir: custom/slices\n")
        write(ovr / "custom/slices/SLICE-7-alt.md", manifest("SLICE-7", "X-1"))
        r = sp.resolve_slice_paths("SLICE-7", ovr)
        check("slices_dir override honoured", names(r.slice_files),
              ["SLICE-7-alt.md"])

        print("\n── CLI ──")

        def cli(*args, cwd=root):
            p = subprocess.run([sys.executable, str(MOD), *args], cwd=str(cwd),
                               capture_output=True, text=True)
            return p.returncode, p.stdout, p.stderr

        rc, out, _ = cli("--resolve", "SLICE-2", "--root", str(root))
        check("resolve found -> exit 0", rc, 0)
        check("resolve prints bug file", "BUGS-SLICE-2.md" in out, True)
        rc, _, err = cli("--resolve", "SLICE-2", "--root", str(tmp / "nope"))
        check("cannot look -> exit 3", rc, 3)
        check("cannot look -> warning on stderr", "WARNING" in err, True)
        rc, _, _ = cli("--resolve", "not-a-slice", "--root", str(root))
        check("bad ref -> exit 2", rc, 2)
        rc, out, _ = cli("--find-unit", "BE-MM-08", "--root", str(root))
        check("find-unit -> exit 0", rc, 0)
        check("find-unit prints manifest", "SLICE-1-khai-bao-mc.md" in out, True)
        rc, _, _ = cli("--find-unit", "BE-NOPE-99", "--root", str(root))
        check("find-unit found none -> exit 0 (not 3)", rc, 0)
        rc, _, _ = cli("--root", str(root))
        check("no mode -> exit 2", rc, 2)
        rc, out, _ = cli("--resolve", "SLICE-2", "--root", str(root), "--json")
        payload = json.loads(out)
        check("--json is a dict", isinstance(payload, dict), True)
        check("--json carries ok", payload["ok"], True)
        check("--json slice_id canonical", payload["slice_id"], "SLICE-2")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if _fails:
        print(f"{RED}✗ {len(_fails)} failed{OFF}: {', '.join(_fails)}")
        return 1
    print(f"{GREEN}✓ all checks passed{OFF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
