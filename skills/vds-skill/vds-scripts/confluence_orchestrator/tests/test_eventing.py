from __future__ import annotations

from pathlib import Path
from typing import Any

from confluence_orchestrator.eventing import Poller


class FakeClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses
        self.calls = 0

    def search_cql(self, *_, **kwargs) -> dict[str, Any]:
        limit = kwargs.get("limit")
        if self.calls < len(self._responses):
            resp = self._responses[self.calls]
            payload = dict(resp)
            if limit is not None and "results" in payload:
                payload["results"] = payload["results"][:limit]
        else:
            payload = {"results": [], "start": 0, "limit": 0}
        self.calls += 1
        return payload


def test_poller_updates_cursor(tmp_path: Path) -> None:
    client = FakeClient(
        [
            {
                "results": [
                    {"id": "10", "version": {"when": "2024-01-02T00:00:00Z"}},
                    {"id": "11", "version": {"when": "2024-01-03T00:00:00Z"}},
                ],
                "start": 0,
                "limit": 25,
            }
        ]
    )

    poller = Poller(client)  # type: ignore[arg-type]
    state_file = tmp_path / "cursor.json"
    count = poller.poll_once(
        base_cql="type=page", state_file=state_file, expand=["version"], out_jsonl=tmp_path / "out.jsonl"
    )

    assert count == 2
    data = state_file.read_text()
    assert "2024-01-03T00:00:00Z" in data
    jsonl_contents = (tmp_path / "out.jsonl").read_text().strip().splitlines()
    assert len(jsonl_contents) == 2


def test_poller_limits_results(tmp_path: Path) -> None:
    client = FakeClient(
        [
            {
                "results": [
                    {"id": "10", "version": {"when": "2024-01-02T00:00:00Z"}},
                    {"id": "11", "version": {"when": "2024-01-03T00:00:00Z"}},
                ],
                "start": 0,
                "limit": 25,
            }
        ]
    )

    poller = Poller(client)  # type: ignore[arg-type]
    state_file = tmp_path / "cursor.json"
    count = poller.poll_once(base_cql="type=page", state_file=state_file, max_results=1)

    assert count == 1
    assert "2024-01-02T00:00:00Z" in state_file.read_text()
