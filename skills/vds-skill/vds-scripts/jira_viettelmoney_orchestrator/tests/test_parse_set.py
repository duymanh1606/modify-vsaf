from __future__ import annotations

import pytest
import typer
from vds_jira_orchestrator.cli import _parse_set


def test_parse_set_parses_objects_and_arrays() -> None:
    result = _parse_set(
        [
            'customfield_1={"value": "Option"}',
            'labels=["alpha", "beta"]',
        ]
    )

    assert result["customfield_1"] == {"value": "Option"}
    assert result["labels"] == ["alpha", "beta"]


def test_parse_set_keeps_scalars_as_strings_by_default() -> None:
    result = _parse_set(["flag=true", "count=1"])

    assert result["flag"] == "true"
    assert result["count"] == "1"


def test_parse_set_allows_scalar_json_when_enabled() -> None:
    result = _parse_set(["flag=true", "count=1"], allow_scalar_json=True)

    assert result["flag"] is True
    assert result["count"] == 1


@pytest.mark.parametrize("value", ["missing", "=value"])
def test_parse_set_rejects_invalid_items(value: str) -> None:
    with pytest.raises(typer.BadParameter):
        _parse_set([value])
