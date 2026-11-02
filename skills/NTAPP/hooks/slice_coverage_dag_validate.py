#!/usr/bin/env python3
"""Hook 15 — slice-coverage-dag-validate (NEW)

Event: SubagentStop after /ntapp-slice-planning.

Invariants (Manual §4 Stage 2b step 3):
    1. Coverage — every P0 unit in WBS must be in ≥1 slice.
    2. DAG no-cycle — blocked_by graph has no cycle.

Output: writes _drift_report_slice.md on fail; warns (not blocks) — downstream
        Hook 1 approval-gate blocks anyway.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOK_DIR / "lib"))
from wbs_parser import Unit, is_external, is_growable, parse_wbs  # noqa: E402
from hookcommon import hook_disabled  # noqa: E402

# A bare WBS id is an uppercase prefix, a hyphen, then an alnum tail, no spaces.
# Prose tokens and external system names are descriptive, not graph references.
_ID_SHAPED = re.compile(r"^[A-Z][A-Z0-9]*-[A-Za-z0-9-]+$")


def _is_id_ref(ref: str) -> bool:
    """True when `ref` is a real graph edge to validate (id-shaped, non-external)."""
    ref = (ref or "").strip()
    return bool(_ID_SHAPED.match(ref)) and not is_external(ref)


def _is_feature_unit(u: Unit) -> bool:
    """Skip as-built brownfield baseline (epic starts with 'BL:')."""
    return not (u.epic or "").strip().upper().startswith("BL:")


def repo_root() -> Path:
    try:
        return Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        ).decode().strip())
    except Exception:
        return Path.cwd()


def spec_root() -> Path:
    root = repo_root()
    cfg = root / ".bmm-config.yaml"
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*spec_repo_root:\s*['\"]?([^'\"]+)['\"]?", line)
            if m:
                rel = m.group(1).strip()
                if rel and rel != ".":
                    p = (root / rel).resolve()
                    if p.is_dir():
                        return p
    return root


_GROWABLE_RE = re.compile(r"\bgrowable:\s*(?:true|yes|1|y)\b", re.IGNORECASE)
_UNIT_ID_RE = re.compile(r"\bid:\s*([A-Za-z0-9_-]+)")


def _parse_growable_units(fm: str) -> set[str]:
    """Ids in units[] explicitly flagged growable — inline `{id: X, growable: true}`
    or block form where `growable:` follows the unit's `id:` line."""
    growable: set[str] = set()
    current_id = ""
    for line in fm.splitlines():
        m_id = _UNIT_ID_RE.search(line)
        if m_id:
            current_id = m_id.group(1)
        if _GROWABLE_RE.search(line):
            gid = m_id.group(1) if m_id else current_id
            if gid:
                growable.add(gid)
    return growable


def parse_slice(path: Path) -> dict:
    """Extract slice_id, units, blocked_by from a slice manifest."""
    text = path.read_text(encoding="utf-8")
    info = {
        "slice_id": "",
        "path": str(path),
        "units": [],
        "blocked_by": [],
        "growable_units": set(),
    }

    # Front-matter parsing
    fm_match = re.search(r"^---\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    if fm_match:
        fm = fm_match.group(1)
        sid = re.search(r"^slice_id:\s*([^\s]+)", fm, re.MULTILINE)
        if sid:
            info["slice_id"] = sid.group(1).strip().strip('"')

        # blocked_by: [SLICE-01, SLICE-02]  OR yaml list
        bb = re.search(r"^blocked_by:\s*\[(.*?)\]", fm, re.MULTILINE)
        if bb:
            info["blocked_by"] = [x.strip().strip('"') for x in bb.group(1).split(",") if x.strip()]
        else:
            # yaml list form
            in_bb = False
            for line in fm.splitlines():
                if re.match(r"^blocked_by:\s*$", line):
                    in_bb = True; continue
                if in_bb:
                    m = re.match(r"^\s*-\s*(\S+)", line)
                    if m:
                        info["blocked_by"].append(m.group(1).strip('"'))
                    elif line and not line.startswith(" "):
                        in_bb = False

        # units: [{id: X, ...}, ...]
        for m in re.finditer(r"\{?\s*id:\s*([A-Za-z0-9_-]+)", fm):
            info["units"].append(m.group(1))

        # per-unit growable flag from plan S-U3, inline or block YAML form
        info["growable_units"] = _parse_growable_units(fm)

    # Fallback: extract unit IDs from body table
    if not info["units"]:
        for m in re.finditer(r"\b((?:SCR|WGT|HUB|MPF|PCM|PMT|POL|INT|HOK)-[A-Z0-9_-]+)", text):
            info["units"].append(m.group(1))
        info["units"] = list(dict.fromkeys(info["units"]))  # dedup, keep order

    if not info["slice_id"]:
        # infer from filename
        info["slice_id"] = path.stem.split("-")[0:2]
        info["slice_id"] = "-".join(info["slice_id"]) if isinstance(info["slice_id"], list) else info["slice_id"]

    return info


def detect_cycle(slices: list[dict]) -> list[str]:
    """Return list of cycle paths if any."""
    graph: dict[str, list[str]] = {s["slice_id"]: s["blocked_by"] for s in slices}
    cycles = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in graph}

    def dfs(node: str, path: list[str]):
        color[node] = GRAY
        path.append(node)
        for nb in graph.get(node, []):
            if nb not in color:  # blocked_by references unknown slice
                cycles.append(f"{node} → {nb} (unknown slice)")
                continue
            if color[nb] == GRAY:
                idx = path.index(nb) if nb in path else 0
                cycles.append(" → ".join(path[idx:] + [nb]))
            elif color[nb] == WHITE:
                dfs(nb, path)
        path.pop()
        color[node] = BLACK

    for n in list(graph.keys()):
        if color[n] == WHITE:
            dfs(n, [])

    return cycles


def _unit_to_slices(all_slices: list[dict]) -> dict[str, set[str]]:
    """unit id -> set of slices that BUILD it."""
    out: dict[str, set[str]] = {}
    for s in all_slices:
        for uid in s["units"]:
            out.setdefault(uid, set()).add(s["slice_id"])
    return out


def _manifest_growable_ids(all_slices: list[dict]) -> set[str]:
    out: set[str] = set()
    for s in all_slices:
        out |= s.get("growable_units", set())
    return out


def _consumer_slices_of(units: list[Unit], unit_slices: dict[str, set[str]]) -> dict[str, set[str]]:
    """provider id -> set of distinct slices whose feature-unit consumers use it."""
    out: dict[str, set[str]] = {}
    for u in units:
        if not _is_feature_unit(u):
            continue
        u_slices = unit_slices.get(u.id, set())
        if not u_slices:
            continue
        for p in u.consumes:
            if _is_id_ref(p):
                out.setdefault(p, set()).update(u_slices)
    return out


def _ancestors(slice_id: str, graph: dict[str, list[str]], cache: dict[str, set[str]]) -> set[str]:
    """All slices reachable from `slice_id` via blocked_by (cycle-safe)."""
    if slice_id in cache:
        return cache[slice_id]
    seen: set[str] = set()
    stack = list(graph.get(slice_id, []))
    while stack:
        s = stack.pop()
        if s in seen:
            continue
        seen.add(s)
        stack.extend(graph.get(s, []))
    cache[slice_id] = seen
    return seen


def _shared_hub_findings(consumer_slices: dict[str, set[str]], unit_slices: dict[str, set[str]],
                         by_id: dict[str, Unit], growable_ids: set[str]) -> list[str]:
    findings: list[str] = []
    for provider, cslices in consumer_slices.items():
        pu = by_id.get(provider)
        if pu is None or not _is_feature_unit(pu):
            continue  # unknown/external or pre-existing baseline — not a shared hub of ours
        built_in = unit_slices.get(provider, set())
        exempt = is_growable(pu) or provider in growable_ids
        if len(cslices) > 1 and len(built_in) == 1 and not exempt:
            findings.append(
                f"[shared-hub] {provider} consumed across {len(cslices)} slices built once (not growable)"
            )
    return findings


def _provider_available(p: str, su: str, unit_slices: dict[str, set[str]],
                        bb_graph: dict[str, list[str]], by_id: dict[str, Unit],
                        cache: dict[str, set[str]]) -> bool:
    pu = by_id.get(p)
    if pu is not None and not _is_feature_unit(pu):
        return True  # pre-existing baseline unit — already available
    built_in = unit_slices.get(p, set())
    if su in built_in:
        return True
    return bool(built_in & _ancestors(su, bb_graph, cache))


def _precedence_for_unit(u: Unit, unit_slices: dict[str, set[str]], bb_graph: dict[str, list[str]],
                         by_id: dict[str, Unit], cache: dict[str, set[str]]) -> list[str]:
    findings: list[str] = []
    for su in unit_slices.get(u.id, set()):
        for p in u.consumes:
            if not _is_id_ref(p):
                continue
            if _provider_available(p, su, unit_slices, bb_graph, by_id, cache):
                continue
            findings.append(f"[precedence] {p} consumed by {u.id} in {su} but built later/never")
    return findings


def check_provider_precedence(all_slices: list[dict], units: list[Unit]) -> list[str]:
    """Shared-hub + precedence checks (Change 2), FEATURE units only.

    [shared-hub]: a non-growable provider consumed by consumers across >1 slice
    yet built in exactly 1 slice. [precedence]: a consumes-edge whose provider is
    built neither in the consumer's slice nor in any blocked_by-ancestor slice.
    """
    by_id = {u.id: u for u in units}
    unit_slices = _unit_to_slices(all_slices)
    growable_ids = _manifest_growable_ids(all_slices)
    bb_graph = {s["slice_id"]: list(s["blocked_by"]) for s in all_slices}
    consumer_slices = _consumer_slices_of(units, unit_slices)

    findings = _shared_hub_findings(consumer_slices, unit_slices, by_id, growable_ids)
    cache: dict[str, set[str]] = {}
    for u in units:
        if _is_feature_unit(u):
            findings.extend(_precedence_for_unit(u, unit_slices, bb_graph, by_id, cache))
    return findings


def main() -> int:
    if hook_disabled("slice_coverage_dag_validate"):
        return 0

    # Stop/SubagentStop re-entry guard — nếu đã block ≥1 lần và agent đang
    # chạy tiếp vì bị chặn dừng, thoát để tránh livelock (xem common.sh).
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    if payload.get("stop_hook_active") is True:
        return 0

    spec = spec_root()
    slices_dir = spec / "NTAPP-output/Stage_2_Architecture/slices"
    wbs_path = spec / "NTAPP-output/Stage_2_Architecture/project_wbs.md"
    report_path = spec / "NTAPP-output/Stage_2_Architecture/_drift_report_slice.md"

    if not slices_dir.is_dir():
        return 0

    # Only fire if a slice manifest was modified in last 5 min
    fresh = []
    import time
    cutoff = time.time() - 300
    for p in slices_dir.glob("SLICE-*.md"):
        if p.stat().st_mtime > cutoff:
            fresh.append(p)
    if not fresh:
        return 0

    all_slices = [parse_slice(p) for p in sorted(slices_dir.glob("SLICE-*.md"))]
    wbs_units = parse_wbs(wbs_path) if wbs_path.exists() else []
    findings: list[str] = []

    # 1) Coverage
    if wbs_units:
        # P0 heuristic: row has 'P0' in any field, or epic field is non-empty
        p0_ids = {u.id for u in wbs_units
                  if any("P0" in str(v) for v in u.raw.values()) or u.epic}
        if not p0_ids:
            p0_ids = {u.id for u in wbs_units}  # fallback — all units

        covered: set[str] = set()
        for s in all_slices:
            covered.update(s["units"])
        uncovered = p0_ids - covered
        if uncovered:
            findings.append(
                f"[coverage] {len(uncovered)} P0 unit(s) not in any slice: "
                + ", ".join(sorted(uncovered)[:10])
                + ("..." if len(uncovered) > 10 else "")
            )

    # 2) DAG no-cycle
    cycles = detect_cycle(all_slices)
    for c in cycles:
        findings.append(f"[DAG] cycle/unknown: {c}")

    # 3) Required front-matter
    for s in all_slices:
        if not s["slice_id"]:
            findings.append(f"[manifest] {Path(s['path']).name} missing slice_id front-matter")
        if not s["units"]:
            findings.append(f"[manifest] {Path(s['path']).name} has 0 units")

    # 4) Provider precedence and shared-hub checks, feature units only
    findings.extend(check_provider_precedence(all_slices, wbs_units))

    if not findings:
        return 0

    # Write report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    body = [
        "# Slice Planning Drift Report",
        "",
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
        f"**{len(findings)} finding(s):**",
        "",
    ]
    body.extend(f"- {f}" for f in findings)
    body.append("")
    body.append("Re-run /ntapp-slice-planning or edit slice manifests to fix.")
    report_path.write_text("\n".join(body), encoding="utf-8")

    print(
        f"\n\033[0;33m[HOOK WARN]\033[0m slice-planning issues ({len(findings)}). "
        f"Report: {report_path.relative_to(repo_root())}\n",
        file=sys.stderr,
    )
    for f in findings[:5]:
        print(f"  - {f}", file=sys.stderr)
    # Warn-only; Hook 1 approval-gate blocks downstream
    return 0


if __name__ == "__main__":
    sys.exit(main())
