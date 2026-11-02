from __future__ import annotations

from pathlib import Path

from vds_brd_orchestrator.validator import REQUIRED_BRD_SECTIONS, validate_brd_coverage


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_validate_brd_coverage_missing_sections(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    _write(docs_root / "doc.md", "BRD 3.1\n")

    report = validate_brd_coverage(docs_root)
    assert report["total_required"] == len(REQUIRED_BRD_SECTIONS)
    assert report["total_covered"] == 1
    assert "3.1" in report["covered_sections"]
    assert "3.2" in report["missing_sections"]


def test_validate_brd_coverage_all_sections(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()

    content = "\n".join(f"BRD {section}" for section in REQUIRED_BRD_SECTIONS)
    _write(docs_root / "doc.md", content)

    report = validate_brd_coverage(docs_root)
    assert report["total_covered"] == len(REQUIRED_BRD_SECTIONS)
    assert report["missing_sections"] == []
