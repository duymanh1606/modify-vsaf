from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .orchestration import BatchRunner

if TYPE_CHECKING:
    from .http import ConfluenceClient


@dataclass(slots=True)
class CursorState:
    last_ts: str | None = None  # ISO8601 timestamp string
    seen_ids: set[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.seen_ids is None:
            self.seen_ids = set()


class CursorStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> CursorState:
        if not self._path.exists():
            return CursorState()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return CursorState(last_ts=data.get("last_ts"), seen_ids=set(data.get("seen_ids", [])))

    def save(self, state: CursorState) -> None:
        payload = {"last_ts": state.last_ts, "seen_ids": sorted(state.seen_ids)}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class Poller:
    """Polling-based eventing using CQL queries and a simple cursor state."""

    def __init__(self, http_client: ConfluenceClient) -> None:
        self._http = http_client

    @staticmethod
    def _augment_cql(base: str, last_ts: str | None) -> str:
        if not last_ts:
            return base
        # Confluence CQL uses lastmodified; store ISO timestamp
        return f'({base}) AND lastmodified > "{last_ts}"'

    @staticmethod
    def _extract_ts(item: dict[str, Any]) -> str | None:
        # Prefer version.when if present; otherwise None
        version = item.get("version")
        if isinstance(version, dict):
            when = version.get("when")
            if isinstance(when, str):
                return when
        return None

    def poll_once(
        self,
        *,
        base_cql: str,
        state_file: Path,
        limit: int = 25,
        max_results: int | None = None,
        expand: Iterable[str] | None = None,
        out_jsonl: Path | None = None,
    ) -> int:
        store = CursorStore(state_file)
        state = store.load()
        cql = self._augment_cql(base_cql, state.last_ts)
        runner = BatchRunner(self._http, expand=tuple(expand) if expand else None)

        written = 0
        max_ts: str | None = state.last_ts
        jsonl_fp = None
        try:
            if out_jsonl is not None:
                out_jsonl.parent.mkdir(parents=True, exist_ok=True)
                jsonl_fp = out_jsonl.open("a", encoding="utf-8")
            for item in runner.scan(cql, limit=limit, max_results=max_results):
                item_id = str(item.get("id", ""))
                if item_id and item_id in state.seen_ids:
                    continue
                ts = self._extract_ts(item)
                if ts and (max_ts is None or ts > max_ts):
                    max_ts = ts
                state.seen_ids.add(item_id)
                written += 1
                if jsonl_fp is not None:
                    jsonl_fp.write(json.dumps(item) + "\n")
        finally:
            if jsonl_fp is not None:
                jsonl_fp.close()

        if max_ts:
            # Normalize to ISO without microseconds if possible
            try:
                dt = datetime.fromisoformat(max_ts.replace("Z", "+00:00"))
                max_ts = dt.isoformat().replace("+00:00", "Z")
            except Exception:
                pass
            state.last_ts = max_ts
        store.save(state)
        return written
