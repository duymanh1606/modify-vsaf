#!/usr/bin/env python3
"""WBS parser — load project_wbs.md → structured units.

Two table shapes are understood and MERGED (a project may have either or both):

1. Coverage Matrix (4-col, human-authored, ALWAYS produced by
   NTAPP-architecture-design — the single source of truth):
       | WBS ID | Tên Feature | Mô tả ... & Data Flow | Epic / Story |
   Rows are grouped under bold cluster headers `**[PREFIX] Name** _(module_type)_`.
   Edges/attributes live as prose tags inside column 3, e.g.:
       ...- consumes: BE-PG2-02, EXT-recaptcha<br>- role: proxy<br>- growable: yes

2. Machine Index (8-col, optional, id-header — legacy / hand-added):
       | id | type | module | epic | consumes | used_by | provider | consumers |

Merge policy (A-U1): union edge lists, prefer non-empty scalars, preserve the
`BL:` baseline marker in `epic`. Result is strictly more informed than either
table alone, so enabling matrix parsing never *loses* data a project already had.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- Role taxonomy (A-U2) — shared source of truth for hooks -----------------
# Roles are read from the WBS (`- role:` prose tag / `role` index column); when
# absent they are derived from the ID prefix. Kept here so every hook classifies
# units identically. Projects may extend via env (comma-separated), never in code.
CONSUMER_ROLES = {"consumer", "frontend-app", "screen", "widget"}
PROXY_ROLES = {"proxy", "bff", "gateway", "aggregation"}
CONTRACT_ROLES = {"contract", "integration-contract"}

# External systems referenced by edges but owned by no WBS unit (3rd-party,
# other-team). Excluded from graph-integrity + graph-completeness checks.
EXTERNAL_PREFIXES = tuple(
    p.strip().upper()
    for p in os.environ.get("WBS_EXTERNAL_PREFIXES", "EXT-").split(",")
    if p.strip()
)

_EMPTY = {"", "-", "—", "n/a", "none"}
_EDGE_KEYWORDS = ("consumes", "used_by", "provider", "consumers", "role", "growable")


@dataclass
class Unit:
    id: str
    type: str = ""
    module: str = ""
    epic: str = ""
    consumes: list[str] = field(default_factory=list)
    used_by: list[str] = field(default_factory=list)
    provider: str = ""
    consumers: list[str] = field(default_factory=list)
    # Coverage Matrix prose columns. Deliberately NOT folded into `raw`:
    # slice_coverage_dag_validate.py scans `raw.values()` for the substring
    # "P0", so any key added there silently changes a live gate the moment a
    # feature name happens to contain it.
    feature_name: str = ""
    summary: str = ""
    raw: dict[str, str] = field(default_factory=dict)


def is_external(uid: str) -> bool:
    """True when `uid` names an external system (no owning WBS unit)."""
    u = (uid or "").strip().upper()
    return bool(u) and u.startswith(EXTERNAL_PREFIXES)


def unit_role(u: Unit) -> str:
    """Classify a unit — explicit `role` wins, else derive from ID prefix/type.

    Centralised so Change 1 (graph-completeness) and any other hook agree.
    """
    r = (u.raw.get("role") or "").strip().lower()
    if r:
        return r
    if u.id.startswith(("SCR-", "WGT-")):
        return "consumer"
    if u.id.startswith("INT-"):
        return "contract"
    return (u.type or "").strip().lower()


def is_growable(u: Unit) -> bool:
    """True when the unit is flagged as an intentional cross-slice hub (A-U6)."""
    v = (u.raw.get("growable") or "").strip().lower()
    return v in {"yes", "true", "1", "y"}


def _split_list(cell: str) -> list[str]:
    """Split a comma/whitespace-separated cell (8-col index columns)."""
    cell = (cell or "").strip()
    if not cell or cell.lower() in _EMPTY:
        return []
    return [x.strip() for x in re.split(r"[,\s]+", cell) if x.strip()]


def _split_csv(value: str) -> list[str]:
    """Split a comma-separated edge value (Coverage Matrix prose). Values may
    contain hyphens (BE-PG2-02, EXT-payment-business) so only commas separate."""
    value = (value or "").replace("<br>", " ").strip()
    if not value or value.lower() in _EMPTY:
        return []
    out = []
    for tok in value.split(","):
        tok = tok.strip().strip("`").strip()
        if tok and tok.lower() not in _EMPTY:
            out.append(tok)
    return out


def _normalize_headers(cells: list[str]) -> list[str]:
    return [c.strip().lower() for c in cells]


def _table_kind(headers: list[str]) -> str:
    """'index' (8-col id table), 'matrix' (4-col Coverage Matrix), or '' (ignore)."""
    if "id" in headers:
        return "index"
    first = headers[0] if headers else ""
    if first in {"wbs id", "wbsid"} or "wbs id" in headers:
        return "matrix"
    return ""


# --- Coverage Matrix column-3 prose tag extraction ---------------------------
_TAG_RE = re.compile(
    r"-\s*(?P<key>consumes|used_by|provider|consumers|role|growable)\s*:\s*"
    r"(?P<val>.*?)"
    r"(?=(?:<br>)?\s*-\s*(?:consumes|used_by|provider|consumers|role|growable|input|output)\s*:"
    r"|<br>|\||$)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_matrix_edges(col3: str) -> dict[str, object]:
    """Return {consumes:[..], used_by:[..], consumers:[..], provider:str,
    role:str, growable:str} from a Coverage Matrix description cell."""
    found: dict[str, object] = {}
    for m in _TAG_RE.finditer(col3 or ""):
        key = m.group("key").lower()
        val = m.group("val").strip()
        if key in {"consumes", "used_by", "consumers"}:
            found.setdefault(key, [])
            found[key] = list(dict.fromkeys(found[key] + _split_csv(val)))  # type: ignore[operator]
        else:  # provider / role / growable — scalar
            tok = val.replace("<br>", " ").strip().strip("`").split()
            if tok:
                found[key] = tok[0]
    return found


_CLUSTER_RE = re.compile(r"\*\*\s*\[(?P<mod>[^\]]+)\]")
_MODTYPE_RE = re.compile(r"_\((?P<mt>[^)]+)\)_")
_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Za-z0-9][A-Za-z0-9-]*$")


def _clean_cell(cell: str) -> str:
    return (cell or "").replace("**", "").replace("`", "").strip()


def _derive_type(uid: str, module_type: str) -> str:
    if uid.startswith("SCR-"):
        return "screen"
    if uid.startswith("WGT-"):
        return "widget"
    if uid.startswith("INT-"):
        return "contract"
    return module_type or ""


def _matrix_summary(col3: str) -> str:
    """The BA prose of a Coverage Matrix row, minus the edge tags.

    Column 3 mixes a human description with machine tags (`- consumes: …`).
    The tags are already lifted into structured fields, so keeping them here
    would leave every consumer stripping them again.
    """
    text = re.sub(r"<br\s*/?>", " ", col3 or "", flags=re.IGNORECASE)
    text = _TAG_RE.sub(" ", text)
    text = re.sub(
        r"-\s*(?:input|output)\s*:.*?(?=-\s*[a-z_]+\s*:|$)", " ", text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = text.replace("`", "").strip()
    return re.sub(r"\s{2,}", " ", text).strip(" -;")


def _fold(units: dict[str, Unit], order: list[str], p: Unit) -> None:
    """Merge partial unit `p` into the accumulator (union lists, prefer non-empty)."""
    if p.id not in units:
        units[p.id] = p
        order.append(p.id)
        return
    cur = units[p.id]
    cur.type = cur.type or p.type
    cur.module = cur.module or p.module
    # Prefer an epic that carries the BL: baseline marker (keeps feature-unit scope correct)
    if p.epic and (not cur.epic or (p.epic.upper().startswith("BL:") and not cur.epic.upper().startswith("BL:"))):
        cur.epic = p.epic
    cur.consumes = list(dict.fromkeys(cur.consumes + p.consumes))
    cur.used_by = list(dict.fromkeys(cur.used_by + p.used_by))
    cur.consumers = list(dict.fromkeys(cur.consumers + p.consumers))
    cur.provider = cur.provider or p.provider
    cur.feature_name = cur.feature_name or p.feature_name
    cur.summary = cur.summary or p.summary
    for k, v in p.raw.items():
        if v and not cur.raw.get(k):
            cur.raw[k] = v


def parse_wbs(path: Path) -> list[Unit]:
    if not path.exists():
        return []

    units: dict[str, Unit] = {}
    order: list[str] = []

    headers: list[str] = []
    kind = ""
    in_table = False
    cur_module = ""
    cur_modtype = ""

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]

        if not in_table:
            headers = _normalize_headers(cells)
            kind = _table_kind(headers)
            in_table = True
            continue

        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue  # separator row
        if not kind:
            continue

        if kind == "index":
            if len(cells) < len(headers):
                cells += [""] * (len(headers) - len(cells))
            row = dict(zip(headers, cells))
            uid = row.get("id", "").strip()
            if not uid or uid.lower() == "id":
                continue
            raw = dict(row)
            _fold(units, order, Unit(
                id=uid,
                type=row.get("type", ""),
                module=row.get("module", ""),
                epic=row.get("epic", "") or row.get("parent_epic", ""),
                consumes=_split_list(row.get("consumes", "")),
                used_by=_split_list(row.get("used_by", "")),
                provider=row.get("provider", "").strip(),
                consumers=_split_list(row.get("consumers", "")),
                raw=raw,
            ))
            continue

        # kind == "matrix"
        col1_raw = cells[0] if cells else ""
        # Cluster header row: bold **[PREFIX] Name** _(module_type)_ (no unit id)
        cm = _CLUSTER_RE.search(col1_raw)
        if cm and "**" in col1_raw:
            cur_module = cm.group("mod").strip()
            mt = _MODTYPE_RE.search(col1_raw)
            cur_modtype = mt.group("mt").strip().lower() if mt else ""
            continue

        uid = _clean_cell(col1_raw)
        if not _ID_RE.match(uid):
            continue  # not a unit row (blank, prose, etc.)

        col3 = cells[2] if len(cells) > 2 else ""
        col_epic = _clean_cell(cells[-1]) if len(cells) >= 4 else ""
        edges = _parse_matrix_edges(col3)

        raw = {"module_type": cur_modtype}
        for k in ("role", "growable", "provider"):
            if edges.get(k):
                raw[k] = str(edges[k])

        _fold(units, order, Unit(
            id=uid,
            type=_derive_type(uid, cur_modtype),
            module=cur_module or (uid.split("-")[1] if uid.count("-") >= 2 else ""),
            epic=col_epic,
            feature_name=_clean_cell(cells[1]) if len(cells) > 1 else "",
            summary=_matrix_summary(col3),
            consumes=list(edges.get("consumes", [])),   # type: ignore[arg-type]
            used_by=list(edges.get("used_by", [])),      # type: ignore[arg-type]
            provider=str(edges.get("provider", "")),
            consumers=list(edges.get("consumers", [])),  # type: ignore[arg-type]
            raw=raw,
        ))

    return [units[i] for i in order]


def has_id(path: Path, uid: str) -> bool:
    return any(u.id == uid for u in parse_wbs(path))


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("project_wbs.md")
    us = parse_wbs(p)
    print(f"# parsed {len(us)} unit(s) from {p}")
    for u in us:
        edges = []
        if u.consumes:
            edges.append("consumes=" + ",".join(u.consumes))
        if u.used_by:
            edges.append("used_by=" + ",".join(u.used_by))
        if u.provider:
            edges.append("provider=" + u.provider)
        if u.consumers:
            edges.append("consumers=" + ",".join(u.consumers))
        role = unit_role(u)
        flags = []
        if is_growable(u):
            flags.append("growable")
        print(f"{u.id}\t[{role}]\t{u.type}\t{u.module}\t{u.epic[:22]}\t{'; '.join(edges)}"
              + (f"\t<{','.join(flags)}>" if flags else ""))
