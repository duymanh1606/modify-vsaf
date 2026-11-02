"""Source contract helpers for ULNC alignment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .ulnc_alignment import extract_source_contract


def build_source_contract_snapshot(current_ulnc: Path) -> dict[str, Any]:
    """Return a normalized source snapshot for ULNC alignment workflows."""
    snapshot = extract_source_contract(current_ulnc)

    # Backward-compatible normalization: older callers can keep using `service`,
    # while newer ULNC alignment flows can rely on canonical + sheet alias identity.
    normalized_rows: list[dict[str, Any]] = []
    for row in snapshot.get("rows", []):
        canonical = row.get("service_canonical") or row.get("service", "")
        alias = row.get("service_sheet_alias") or canonical
        normalized_row = dict(row)
        normalized_row.setdefault("service", canonical)
        normalized_row.setdefault("service_canonical", canonical)
        normalized_row.setdefault("service_sheet_alias", alias)
        normalized_row.setdefault("source_row_index", 0)
        normalized_rows.append(normalized_row)

    snapshot["rows"] = normalized_rows
    return snapshot
