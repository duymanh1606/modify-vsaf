"""Unit tests for vds_agent_core.llm.schemas — ProbeScore and parse_llm_response."""

from __future__ import annotations

import json

import pytest
from vds_agent_core.llm.schemas import ProbeScore, parse_llm_response


class TestProbeScore:
    def test_default_instantiation(self) -> None:
        probe = ProbeScore(name="existence", score=8.0, reasoning="Found evidence")
        assert probe.name == "existence"
        assert probe.score == 8.0
        assert probe.max_score == 10.0
        assert probe.evidence_refs == []

    def test_score_bounds(self) -> None:
        with pytest.raises(Exception):
            ProbeScore(name="x", score=11.0, reasoning="over max")
        with pytest.raises(Exception):
            ProbeScore(name="x", score=-1.0, reasoning="under min")

    def test_evidence_refs(self) -> None:
        probe = ProbeScore(
            name="content",
            score=5.0,
            reasoning="partial",
            evidence_refs=["path/to/file.py", "README.md"],
        )
        assert len(probe.evidence_refs) == 2

    def test_custom_max_score(self) -> None:
        probe = ProbeScore(name="quality", score=2.0, max_score=4.0, reasoning="ok")
        assert probe.max_score == 4.0


class TestParseLlmResponse:
    def test_parse_plain_json(self) -> None:
        data = {"name": "test", "score": 7.5, "reasoning": "good", "max_score": 10.0}
        result = parse_llm_response(json.dumps(data), ProbeScore)
        assert isinstance(result, ProbeScore)
        assert result.score == 7.5

    def test_parse_markdown_json_block(self) -> None:
        text = '```json\n{"name": "test", "score": 5.0, "reasoning": "ok"}\n```'
        result = parse_llm_response(text, ProbeScore)
        assert isinstance(result, ProbeScore)
        assert result.score == 5.0

    def test_parse_plain_code_block(self) -> None:
        text = '```\n{"name": "test", "score": 3.0, "reasoning": "low"}\n```'
        result = parse_llm_response(text, ProbeScore)
        assert result.score == 3.0

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_llm_response("not json at all", ProbeScore)

    def test_invalid_schema_raises(self) -> None:
        with pytest.raises(ValueError, match="Failed to validate"):
            parse_llm_response('{"score": 999}', ProbeScore)  # score > 10.0
