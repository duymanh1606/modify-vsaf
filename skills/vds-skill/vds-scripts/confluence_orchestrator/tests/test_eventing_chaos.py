from __future__ import annotations

from pathlib import Path
from typing import Any

from confluence_orchestrator.eventing import Poller


class SingleRunClient:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = results
        self.calls = 0

    def search_cql(self, *_, **kwargs) -> dict[str, Any]:
        limit = kwargs.get("limit")
        if self.calls == 0:
            payload = {"results": self._results, "start": 0, "limit": len(self._results)}
            if limit is not None:
                payload["results"] = self._results[:limit]
        else:
            payload = {"results": [], "start": 0, "limit": 0}
        self.calls += 1
        return payload


def test_poller_persists_state_across_runs(tmp_path: Path) -> None:
    state_file = tmp_path / "cursor.json"

    poller = Poller(SingleRunClient([{"id": "10", "version": {"when": "2024-01-02T00:00:00Z"}}]))  # type: ignore[arg-type]
    poller.poll_once(base_cql="type=page", state_file=state_file)
    assert "2024-01-02T00:00:00Z" in state_file.read_text()

    poller = Poller(SingleRunClient([{"id": "11", "version": {"when": "2024-01-04T00:00:00Z"}}]))  # type: ignore[arg-type]
    poller.poll_once(base_cql="type=page", state_file=state_file)
    contents = state_file.read_text()
    assert "2024-01-04T00:00:00Z" in contents
    assert '"10"' in contents and '"11"' in contents
