from __future__ import annotations

from pathlib import Path
from typing import Any

from confluence_orchestrator.eventing import Poller


class PagedClient:
    def __init__(self) -> None:
        self.responses: list[dict[str, Any]] = [
            {
                "results": [
                    {"id": "10", "version": {"when": "2024-01-02T00:00:00Z"}},
                ],
                "start": 0,
                "limit": 1,
            },
            {
                "results": [
                    {"id": "11", "version": {"when": "2024-01-03T00:00:00Z"}},
                ],
                "start": 1,
                "limit": 1,
            },
        ]
        self.calls = 0

    def search_cql(self, *_, **kwargs) -> dict[str, Any]:
        limit = kwargs.get("limit")
        if self.calls < len(self.responses):
            resp = dict(self.responses[self.calls])
            if limit is not None:
                resp["results"] = resp["results"][:limit]
        else:
            resp = {"results": [], "start": 0, "limit": 0}
        self.calls += 1
        return resp


def test_poller_respects_max_results(tmp_path: Path) -> None:
    client = PagedClient()
    poller = Poller(client)  # type: ignore[arg-type]
    state_file = tmp_path / "cursor.json"

    count = poller.poll_once(base_cql="type=page", state_file=state_file, limit=1, max_results=1)

    assert count == 1
    assert client.calls == 1
