"""Gate FR-10.13: every non-__init__ .py in vds_agent_core/src/ must start with
'from __future__ import annotations'.
"""

import pathlib
import sys

src = pathlib.Path("vds_agent_core/src")
if not src.exists():
    sys.exit(0)

missing = []
for f in src.rglob("*.py"):
    if f.name == "__init__.py":
        continue
    if "from __future__ import annotations" not in f.read_text():
        missing.append(str(f))

if missing:
    for path in sorted(missing):
        print(f"MISSING 'from __future__ import annotations': {path}")
    sys.exit(1)
