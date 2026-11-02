"""Generic structured output schemas for LLM responses.

Generic, audit-independent types extracted from audit_orchestrator.llm.schemas.
Audit-specific schemas (GapFinding, RowEvaluationRequest/Response, etc.) live in
audit_orchestrator.llm.audit_schemas.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field


class ProbeScore(BaseModel):
    """Score from a single evaluation probe."""

    name: str
    score: float = Field(ge=0.0, le=10.0)
    max_score: float = 10.0
    reasoning: str
    evidence_refs: list[str] = Field(default_factory=list)


def parse_llm_response(response_text: str, schema_class: type[BaseModel]) -> BaseModel:
    """Parse LLM response text into structured schema."""
    text = response_text.strip()

    # Handle markdown code blocks
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    try:
        data = json.loads(text)
        return schema_class.model_validate(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to validate LLM response: {e}") from e
