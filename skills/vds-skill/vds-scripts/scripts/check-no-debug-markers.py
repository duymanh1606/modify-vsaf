"""Gate FR-10.13: vds_agent_core/src/ must not contain TODO/FIXME/XXX/HACK."""

import pathlib
import re
import sys

pattern = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
src = pathlib.Path("vds_agent_core/src")
if not src.exists():
    sys.exit(0)

violations = []
for f in src.rglob("*.py"):
    for i, line in enumerate(f.read_text().splitlines(), 1):
        if pattern.search(line):
            violations.append(f"{f}:{i}: {line.strip()}")

if violations:
    for v in violations:
        print(v)
    sys.exit(1)
