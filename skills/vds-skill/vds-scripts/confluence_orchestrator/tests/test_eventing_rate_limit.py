from __future__ import annotations

from pathlib import Path
from typing import Any

from confluence_orchestrator.eventing import Poller


class DuplicateClient:
    def __init__(self) -> None:
        self.responses: list[dict[str, Any]] = [
            {
                "results": [
                    {"id": "10", "version": {"when": "2024-01-02T00:00:00Z"}},
                    {"id": "10", "version": {"when": "2024-01-02T00:00:00Z"}},
                    {"id": "11", "version": {"when": "2024-01-03T00:00:00Z"}},
                ],
                "start": 0,
                "limit": 25,
            }
        ]
        self.calls = 0

    def search_cql(self, *_, **kwargs) -> dict[str, Any]:
        limit = kwargs.get("limit")
        if self.calls == 0:
            resp = dict(self.responses[0])
            if limit is not None:
                resp["results"] = resp["results"][:limit]
        else:
            resp = {"results": [], "start": 0, "limit": 0}
        self.calls += 1
        return resp


def test_poller_skips_duplicate_ids(tmp_path: Path) -> None:
    client = DuplicateClient()
    poller = Poller(client)  # type: ignore[arg-type]

    state_file = tmp_path / "cursor.json"
    count = poller.poll_once(base_cql="type=page", state_file=state_file, limit=10)

    assert count == 2  # one duplicate skipped
    assert client.calls == 2  # second call returns empty page
