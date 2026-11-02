"""
Generate basic project metrics for documentation accuracy.

Outputs:
- src Python LOC (non-blank, non-comment)
- number of test files and test functions
"""

from __future__ import annotations

import json
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"


def count_loc(py_path: Path) -> int:
    lines = 0
    for line in py_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines += 1
    return lines


def collect_stats() -> dict[str, int]:
    src_files = list(SRC_DIR.rglob("*.py"))
    test_files = list(TESTS_DIR.rglob("*.py"))

    loc = sum(count_loc(p) for p in src_files)
    test_functions = 0
    for f in test_files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("def test_"):
                test_functions += 1

    return {
        "src_files": len(src_files),
        "tests_files": len(test_files),
        "loc": loc,
        "test_functions": test_functions,
    }


def main() -> None:
    stats = collect_stats()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
