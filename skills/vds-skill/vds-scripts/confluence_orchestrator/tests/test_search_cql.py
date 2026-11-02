from __future__ import annotations

from typing import Any

import pytest
from confluence_orchestrator.content import ContentClient


class DummyClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def search_cql(
        self, cql: str, limit: int = 25, start: int = 0, expand: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        self.calls.append({"cql": cql, "limit": limit, "start": start, "expand": expand})
        return {
            "results": [
                {"id": "1", "type": "page", "title": "First"},
                {"id": "2", "type": "page", "title": "Second"},
            ],
            "start": start,
            "limit": limit,
        }


@pytest.fixture()
def content_client() -> ContentClient:
    return ContentClient(DummyClient())


def test_search_cql_basic(content_client: ContentClient) -> None:
    payload = content_client.search_cql("type=page", limit=2, start=0)
    assert payload["limit"] == 2
    assert len(payload["results"]) == 2
    assert payload["results"][0]["title"] == "First"
