"""Gate FR-10.13: vds_agent_core/tests/ must not use unittest.TestCase or self.assert*."""

import pathlib
import re
import sys

pattern = re.compile(r"(unittest\.TestCase|self\.assert)")
tests = pathlib.Path("vds_agent_core/tests")
if not tests.exists():
    sys.exit(0)

violations = []
for f in tests.rglob("*.py"):
    for i, line in enumerate(f.read_text().splitlines(), 1):
        if pattern.search(line):
            violations.append(f"{f}:{i}: {line.strip()}")

if violations:
    for v in violations:
        print(v)
    sys.exit(1)
