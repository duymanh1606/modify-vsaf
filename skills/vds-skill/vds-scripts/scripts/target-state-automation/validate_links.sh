#!/usr/bin/env bash
# UV-PATTERN: NO-UV — Uses inline python3 for link validation; no uv invocation.
# Root resolution goes through docs_root.sh shim (safe marker-based).
# No migration needed.
set -euo pipefail

# Validate relative markdown links within target-state docs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=WHO-project/vds-scripts/scripts/target-state-automation/docs_root.sh
source "$SCRIPT_DIR/docs_root.sh"

ROOT="$(resolve_repo_root)"
TARGET_STATE_ROOT="$(resolve_insurance_docs_root "$ROOT")/projects/INSURANCE/analysis/target-state"

TARGET_STATE_ROOT="$TARGET_STATE_ROOT" python3 - <<'PY'
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote

root = Path(os.environ["TARGET_STATE_ROOT"]).resolve()
md_files = sorted([p for p in root.rglob('*.md') if p.is_file()])

link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

errors: list[str] = []

for f in md_files:
    text = f.read_text(encoding='utf-8', errors='ignore')
    for raw in link_re.findall(text):
        link = raw.strip()
        if not link:
            continue
        # strip title part: (path "title")
        if ' ' in link and not link.startswith('http'):
            link = link.split(' ')[0]
        link = unquote(link)

        # Skip anchors/external links/schemes
        if link.startswith(('#', 'http://', 'https://', 'mailto:')):
            continue
        if '://' in link:  # includes file://
            continue
        if link.startswith(('ac:', 'ri:')):
            continue
        if '{' in link or '}' in link:  # template placeholders
            continue

        # strip fragment
        link = link.split('#', 1)[0]
        if not link or link.startswith('data:'):
            continue
        if link.endswith('/'):
            continue  # directory navigation links are allowed

        # Only validate links that look like local files
        allowed_ext = {'.md', '.pdf', '.puml', '.plantuml', '.png', '.svg', '.mmd'}
        if Path(link).suffix and Path(link).suffix.lower() not in allowed_ext:
            continue
        if not Path(link).suffix:
            continue

        target = (f.parent / link).resolve()
        # Skip links that point outside target-state root
        try:
            target.relative_to(root.resolve())
        except ValueError:
            continue

        if not target.exists():
            errors.append(f"{f.relative_to(root)} -> {raw}")

if errors:
    print('❌ Link validation failed (missing targets)')
    for e in errors[:200]:
        print('-', e)
    if len(errors) > 200:
        print(f"... and {len(errors)-200} more")
    raise SystemExit(1)

print('✅ Link validation passed')
print('Files scanned:', len(md_files))
PY
