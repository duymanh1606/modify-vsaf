"""Tests for docs quality scoring (FR-4)."""

from pathlib import Path

from vds_cli.docs_cmd import score_all_docs, score_doc


class TestScoreDoc:
    def test_score_high_quality_doc(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text(
            "<!-- diátaxis: reference -->\n\n# Test\n\n## Scope\n\n- **Does:** things.\n"
            "## CLI Entry\n\n```bash\nvds-cli test --help\n```\n\n"
            "## Key Commands\n\n| Command | Purpose |\n|---------|---------|\n"
            "| `run` | Run thing |\n\n"
            "## Common Workflows\n\n### Workflow: Test\n\n1. Step one\n2. Step two\n\n"
            "## Related\n\n- [other](other-orchestrator.md)\n",
            encoding="utf-8",
        )
        result = score_doc(doc)
        assert result["total"] >= 0.8
        assert result["commands"] == 1.0
        assert result["workflows"] == 1.0
        assert result["cross_links"] == 1.0

    def test_score_low_quality_doc(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("# Test\n\nShort doc.\n", encoding="utf-8")
        result = score_doc(doc)
        assert result["total"] < 0.5
        assert result["commands"] == 0.0
        assert result["workflows"] == 0.0
        assert result["cross_links"] == 0.0

    def test_score_length_only(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        lines = ["# Test\n"] + ["More content.\n"] * 90
        doc.write_text("".join(lines), encoding="utf-8")
        result = score_doc(doc)
        assert result["length"] == 1.0
        assert result["commands"] == 0.0


class TestScoreAllDocs:
    def test_empty_repo(self, tmp_path: Path) -> None:
        result = score_all_docs(tmp_path)
        assert result["count"] == 0
        assert result["average"] == 0.0

    def test_single_doc(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "agents"
        docs.mkdir(parents=True)
        doc = docs / "test.md"
        doc.write_text(
            "<!-- diátaxis: reference -->\n# Test\n\n```bash\ncmd\n```\nWorkflow: test\n\n[link](other.md)\n",
            encoding="utf-8",
        )
        result = score_all_docs(tmp_path)
        assert result["count"] == 1
        assert "docs/agents/test.md" in result["docs"]
        assert result["average"] > 0.0
