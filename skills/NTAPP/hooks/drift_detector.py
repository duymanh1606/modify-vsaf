#!/usr/bin/env python3
"""Hook 2 — drift-detector

Event: UserPromptSubmit (pre-Stage 2b/3 trigger) + PostToolUse (Edit/Write on
       Stage 2 files).

Check 3-way consistency:
    project_wbs.md ↔ 00_system_connectivity_integration.md ↔
    architecture_design.md ↔ epics.md

Output: writes _drift_report.md when fails; exit code 2 to block.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOK_DIR / "lib"))
from wbs_parser import (  # noqa: E402
    CONSUMER_ROLES,
    CONTRACT_ROLES,
    PROXY_ROLES,
    is_external,
    parse_wbs,
    unit_role,
)
from hookcommon import hook_disabled  # noqa: E402

# A bare WBS id is an uppercase prefix, a hyphen, then an alnum tail, no spaces.
# Brownfield cells may instead carry descriptive prose or external system names,
# which are not graph references and so are never validated.
_ID_SHAPED = re.compile(r"^[A-Z][A-Z0-9]*-[A-Za-z0-9-]+$")


def _is_id_ref(ref: str) -> bool:
    """True when `ref` is a real graph edge to validate (id-shaped, non-external)."""
    ref = (ref or "").strip()
    return bool(_ID_SHAPED.match(ref)) and not is_external(ref)


def repo_root() -> Path:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        ).decode().strip()
        return Path(out)
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


def entry_mode() -> str:
    root = repo_root()
    marker = root / ".bmm-entry-mode"
    if marker.exists():
        for line in marker.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^mode:\s*(\S+)", line)
            if m:
                return m.group(1)
    return "full"


def extract_module_ids_from_hld(hld: Path) -> set[str]:
    """Extract module IDs from mermaid blocks in architecture_design.md."""
    if not hld.exists():
        return set()
    text = hld.read_text(encoding="utf-8")
    ids: set[str] = set()
    in_mermaid = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```mermaid"):
            in_mermaid = True; continue
        if s.startswith("```"):
            in_mermaid = False; continue
        if in_mermaid:
            for m in re.finditer(r"\b([A-Z][A-Z0-9_-]{1,})\b", s):
                ids.add(m.group(1))
    return ids


def extract_contract_ids_from_module0(m0: Path) -> set[str]:
    if not m0.exists():
        return set()
    text = m0.read_text(encoding="utf-8")
    return set(re.findall(r"\b(INT-[A-Z0-9_-]+)\b", text))


def extract_epics(epics_md: Path) -> set[str]:
    if not epics_md.exists():
        return set()
    text = epics_md.read_text(encoding="utf-8")
    return set(re.findall(r"\b(EPIC-[A-Z0-9_-]+)\b", text))


def _graph_integrity_findings(units, wbs_ids: set[str]) -> list[str]:
    """Flag dangling edge refs — only real id-shaped, non-external tokens count.

    Brownfield WBS cells may instead carry descriptive prose or external system
    names, which are not graph references and must not be flagged.
    """
    findings: list[str] = []
    for u in units:
        edges = (
            ("consumes", u.consumes),
            ("used_by", u.used_by),
            ("consumers", u.consumers),
            ("provider", [u.provider] if u.provider else []),
        )
        for field_name, refs in edges:
            for c in refs:
                if _is_id_ref(c) and c not in wbs_ids:
                    findings.append(f"[graph] {u.id}.{field_name} references missing {c}")
    return findings


def _is_feature_unit(u) -> bool:
    """Skip as-built brownfield baseline (epic starts with 'BL:')."""
    return not (u.epic or "").strip().upper().startswith("BL:")


def check_graph_completeness(units) -> list[str]:
    """Presence checks on the dependency graph (A-U3), FEATURE units only.

    A consumer with 0 consumes, a contract missing its provider or consumers,
    or a proxy consumed by a consumer yet declaring no downstream — each is an
    incomplete edge that leaves a seam invisible. Findings default to WARN
    (see main); promote to BLOCK via config.
    """
    findings: list[str] = []
    by_id = {u.id: u for u in units}
    consumers_of: dict[str, set[str]] = {}
    for u in units:
        for c in u.consumes:
            consumers_of.setdefault(c, set()).add(u.id)

    for u in units:
        if not _is_feature_unit(u):
            continue
        role = unit_role(u)
        if role in CONSUMER_ROLES and not u.consumes:
            findings.append(f"[graph-completeness] consumer {u.id} declares 0 consumes")
        if role in CONTRACT_ROLES:
            if not (u.provider or "").strip():
                findings.append(f"[graph-completeness] contract {u.id} has no provider")
            if not u.consumers:
                findings.append(f"[graph-completeness] contract {u.id} has no consumers")
        consumed_by_consumer = any(
            unit_role(by_id[c]) in CONSUMER_ROLES
            for c in consumers_of.get(u.id, set()) if c in by_id
        )
        if role in PROXY_ROLES and consumed_by_consumer and not u.consumes:
            findings.append(
                f"[graph-completeness] proxy {u.id} consumed by a consumer but declares no downstream"
            )
    return findings


def check_drift(spec: Path) -> list[str]:
    wbs_path = spec / "NTAPP-output/Stage_2_Architecture/project_wbs.md"
    hld_path = spec / "NTAPP-output/Stage_2_Architecture/architecture_design.md"
    m0_path = spec / "NTAPP-output/Stage_2_Architecture/00_system_connectivity_integration.md"
    epics_path = spec / "NTAPP-output/Stage_1_Discovery/epics.md"

    findings: list[str] = []

    if not wbs_path.exists():
        return [f"WBS missing: {wbs_path}"]

    units = parse_wbs(wbs_path)
    wbs_ids = {u.id for u in units}
    wbs_modules = {u.module for u in units if u.module}
    wbs_contracts = {u.id for u in units if u.type.lower() in {"contract", "integration-contract"}}
    wbs_epics_ref = {u.epic for u in units if u.epic}

    # WBS ↔ Module 0: contract IDs
    m0_contracts = extract_contract_ids_from_module0(m0_path)
    for cid in wbs_contracts:
        if cid not in m0_contracts:
            findings.append(f"[WBS→M0] contract {cid} declared in WBS but absent in Module 0")
    for cid in m0_contracts:
        if cid not in wbs_ids:
            findings.append(f"[M0→WBS] contract {cid} in Module 0 has no WBS entry")

    # WBS ↔ HLD: module IDs
    hld_ids = extract_module_ids_from_hld(hld_path)
    for mod in wbs_modules:
        if hld_ids and mod and mod not in hld_ids:
            findings.append(f"[WBS→HLD] module '{mod}' in WBS not referenced in HLD mermaid")

    # WBS ↔ Epics
    epic_ids = extract_epics(epics_path)
    for eid in wbs_epics_ref:
        if epic_ids and eid not in epic_ids:
            findings.append(f"[WBS→Epics] epic {eid} referenced in WBS not in epics.md")

    # Graph integrity dangling-ref scan, extracted to keep this scan simple
    findings.extend(_graph_integrity_findings(units, wbs_ids))

    # Naming convention — UI screens/widgets must use SCR-/WGT- prefix
    for u in units:
        t = u.type.lower()
        if t == "screen" and not u.id.startswith("SCR-"):
            findings.append(f"[naming] screen {u.id} should use SCR- prefix")
        elif t == "widget" and not u.id.startswith("WGT-"):
            findings.append(f"[naming] widget {u.id} should use WGT- prefix")
        elif t in {"contract", "integration-contract"} and not u.id.startswith("INT-"):
            findings.append(f"[naming] contract {u.id} should use INT- prefix")

    return findings


def write_report(spec: Path, findings: list[str]) -> Path:
    report = spec / "NTAPP-output/Stage_2_Architecture/_drift_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    body = ["# Drift Report", "", f"_Generated: {datetime.now(timezone.utc).isoformat()}_", ""]
    body.append(f"**{len(findings)} drift(s) found:**\n")
    for f in findings:
        body.append(f"- {f}")
    body.append("")
    body.append("Fix WBS / Module 0 / HLD / Epics consistency, then re-run hook.")
    report.write_text("\n".join(body), encoding="utf-8")
    return report


def graph_completeness_mode() -> str:
    """'warn' (default) or 'block'. env GRAPH_COMPLETENESS wins over config."""
    env = (os.environ.get("GRAPH_COMPLETENESS") or "").strip().lower()
    if env in {"warn", "block"}:
        return env
    cfg = repo_root() / ".bmm-config.yaml"
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*graph_completeness:\s*['\"]?(\w+)['\"]?", line)
            if m and m.group(1).strip().lower() in {"warn", "block"}:
                return m.group(1).strip().lower()
    return "warn"


def completeness_findings(spec: Path) -> list[str]:
    """Graph-completeness findings for the current WBS (empty when no WBS)."""
    wbs_path = spec / "NTAPP-output/Stage_2_Architecture/project_wbs.md"
    if not wbs_path.exists():
        return []
    return check_graph_completeness(parse_wbs(wbs_path))


def _print_completeness_warn(comp: list[str]) -> None:
    print(
        f"\n\033[0;33m[HOOK WARN]\033[0m graph-completeness ({len(comp)}), non-blocking "
        "(set graph_completeness: block to enforce).",
        file=sys.stderr,
    )
    for f in comp[:10]:
        print(f"  - {f}", file=sys.stderr)
    if len(comp) > 10:
        print(f"  ... +{len(comp) - 10} more", file=sys.stderr)


def _apply_completeness(spec: Path, findings: list[str]) -> list[str]:
    """Fold graph-completeness into the blocking set (block mode) or print it as
    a non-blocking warning (warn mode, default). Returns the blocking findings."""
    comp = completeness_findings(spec)
    if not comp:
        return findings
    if graph_completeness_mode() == "block":
        return findings + comp
    _print_completeness_warn(comp)
    return findings


def should_run_on_prompt(prompt: str) -> bool:
    return bool(re.search(
        r"/(ntapp-slice-planning|ntapp-technical-design|ntapp-ux-design|"
        r"ntapp-feature-design|bmad-create-story)",
        prompt,
    ))


def main() -> int:
    if hook_disabled("drift_detector"):
        return 0

    mode = entry_mode()
    if mode != "full":
        return 0  # skip per §3.2

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    event = payload.get("hook_event_name", "")
    prompt = payload.get("prompt", "")
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if event == "UserPromptSubmit" and not should_run_on_prompt(prompt):
        return 0

    if event == "PostToolUse" and tool_name in {"Edit", "Write"}:
        path = tool_input.get("file_path", "")
        if not re.search(r"(project_wbs|architecture_design|00_system_connectivity_integration|epics)\.md", path):
            return 0

    spec = spec_root()
    findings = _apply_completeness(spec, check_drift(spec))
    if not findings:
        return 0

    report = write_report(spec, findings)
    print(
        f"\n\033[0;31m[HOOK BLOCK]\033[0m drift detected ({len(findings)}). "
        f"Report: {report.relative_to(repo_root())}\n",
        file=sys.stderr,
    )
    for f in findings[:10]:
        print(f"  - {f}", file=sys.stderr)
    if len(findings) > 10:
        print(f"  ... +{len(findings) - 10} more (see report)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
