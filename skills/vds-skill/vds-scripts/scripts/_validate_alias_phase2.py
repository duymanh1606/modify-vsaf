#!/usr/bin/env python3
"""Phase 2+3 validation: alias removal, doc consistency, and CLI standardization checks."""

import glob
import re
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

PASS = 0
FAIL = 0


def pass_check(msg):
    global PASS
    PASS += 1
    print(f"  PASS: {msg}")


def fail_check(msg):
    global FAIL
    FAIL += 1
    print(f"  FAIL: {msg}")


def check_aliases():
    print("11. Checking pyproject.toml aliases (main worktree only)...")
    found = False
    for p in glob.glob("*/pyproject.toml") + glob.glob("*/*/pyproject.toml"):
        if "worktree" in p or ".venv" in p or "__pycache__" in p:
            continue
        try:
            with open(p, "rb") as f:
                data = tomllib.load(f)
            entries = data.get("project", {}).get("scripts", {})
            targets = {}
            for name, target in entries.items():
                targets.setdefault(target, []).append(name)
            for names in targets.values():
                if len(names) > 1:
                    fail_check(f"Alias in {p}: {' | '.join(names)}")
                    found = True
        except Exception:
            pass
    if not found:
        pass_check("No alias entries in pyproject.toml")


def check_removed_alias_docs():
    print("\n12. Checking docs do not reference removed aliases...")
    aliases = [
        "mdformat-vds",
        "vds-task",
        "vds-grafana-cli",
        "vds-elastic-cli",
        "vds-sonarqube-cli",
    ]
    docs = glob.glob("docs/**/*.md", recursive=True) + glob.glob("docs_vi/**/*.md", recursive=True)
    total = 0
    for doc in docs:
        try:
            with open(doc) as f:
                text = f.read()
        except FileNotFoundError:
            continue
        for alias in aliases:
            pattern = re.compile(rf"(?i)(?:^[\s\`$>]){re.escape(alias)}\b(?!\w)")
            matches = pattern.findall(text)
            invalid = []
            for m in matches:
                idx = text.find(m, text.find(alias))
                if idx < 0:
                    continue
                before = text[max(0, idx - 50) : idx]
                if "vds-cli" not in before.lower():
                    invalid.append(m)
            if invalid:
                total += 1
                fail_check(f"{doc} references standalone command {alias}")
    if total == 0:
        pass_check("No removed alias references in docs")

    # md2pdf is special: valid as "vds-cli pdf md2pdf", ok to appear
    total_md2pdf = 0
    for doc in docs:
        try:
            with open(doc) as f:
                text = f.read()
        except FileNotFoundError:
            continue
        standalone = re.findall(r"(?i)(?:^|[\s\`$>])md2pdf\b(?!\w)", text)
        invalid = [m for m in standalone if "vds-cli pdf md2pdf" not in text.lower()]
        if invalid:
            fail_check(f"{doc} references md2pdf as standalone command")
            total_md2pdf += 1

    if total_md2pdf == 0:
        pass_check("No standalone md2pdf references in docs")


def check_direct_entry_points_in_docs():
    print("\n13. Checking docs do not legitimize direct executables...")
    # Scan for patterns suggesting direct entry points are OK
    docs = glob.glob("docs/**/*.md", recursive=True)
    violations = 0
    bad_patterns = [
        r"direct executable.*(?:valid|legitimate|primary|preferred)",
        r"(?:use|invoke|call).+direct entry",
        r"package-direct usage",
    ]
    for doc in docs:
        try:
            with open(doc) as f:
                text = f.read()
        except FileNotFoundError:
            continue
        for bp in bad_patterns:
            if re.search(bp, text, re.IGNORECASE):
                violations += 1
                fail_check(f"{doc} legitimizes direct entry point")
                break
    if violations == 0:
        pass_check("No doc legitimizes direct executables")


if __name__ == "__main__":
    check_aliases()
    check_removed_alias_docs()
    check_direct_entry_points_in_docs()
    print()
    print("=" * 40)
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 40)
    sys.exit(1 if FAIL > 0 else 0)
