# VDS-Evolution Ecosystem Alignment Report

## Status: FULLY ALIGNED ✓

---

## System Components

| Component | Location | Status |
|-----------|----------|--------|
| Scripts Repo | vds-scripts/ | HEAD: f7158c9 |
| Mono .venv | vds/.venv/ | 52 lines, fix applied |
| Tracked Shell | vds-evolution-mono.sh | Synced with mono |
| env.py | vds_cli_common/src/ | Permanently patched |
| router.py | vds_cli/src/ | Root-layout fix applied |

---

## Root Cause: Openspace __path_hook__

The openspace package installs a custom PathEntryFinder in `sys.path_hooks`:

1. **PATH_PLACEHOLDER** is added to `sys.path`:
   ```
   '__editable__.openspace-0.1.0.finder.__path_hook__'
   ```

2. **sys.path_hooks** is modified to include `_EditableNamespaceFinder`

3. **When Python imports vds_evolution**:
   - Iterates through `sys.path`
   - Encounters PATH_PLACEHOLDER
   - Calls path_hooks to get PathEntryFinder
   - Openspace hook interferes with the import resolution

4. **Result**: `find_spec()` returns `None` even though:
   - `sys.path` contains the absolute path to vds_evolution
   - The directory exists with `__init__.py`

5. **Why CWD matters**:
   - From scripts_repo: CWD + sys.path already primed
   - From /tmp: PATH_PLACEHOLDER breaks the path iteration

---

## Fix Applied: spec_from_file_location

All three scripts use this workaround:

```python
import importlib.util

# Bypass sys.path_hooks, directly load from file
spec = importlib.util.spec_from_file_location(
    "vds_evolution",
    "/path/to/vds_evolution/__init__.py"
)
module = importlib.util.module_from_spec(spec)
sys.modules["vds_evolution"] = module
spec.loader.exec_module(module)
```

This bypasses the entire `sys.path_hooks` machinery and loads directly from known file paths.

---

## UV Usage Assessment

**Current approach: CORRECT**

- `uv pip install -e` for editable development installs ✓
- Manual script fix for the openspace hook edge case ✓
- Editable install preserves source editing capability

**Alternative approaches considered**:
- Non-editable install: Would fix the hook issue, but loses source editing
- uv tool install: Global install, may still hit hook issue

**Recommendation**: Keep current approach, document the openspace hook issue.

---

## Repo-Boundary Component Status (per `who-ecosystem-alignment` Phase 4)

Phase 4 of `who-ecosystem-alignment` codifies the canonical separation between
`vds-scripts` (runtime Python only) and `vds-skills` (Claude-Code-facing
artifacts). Components in this repo that intersect the boundary rules:

| Component | Phase 4 status | Resolution path |
|---|---|---|
| `vds-scripts/vds_hooks/` (Python package) | **Retiring per FR-12** (Hook home: plugin format under `vds-skills/plugins/vds-hooks-*/` is the sole canonical hook surface) | `vds-hooks-claude-plugin-packaging` Phase 6 deletes the package (90 tracked files, 1.1 MB tracked content) |
| `vds-scripts/.claude/skills/gitnexus/` (vendored skill mirror) | **Violates FR-11** (Vendoring policy: `vds-scripts` MUST NOT contain `.claude/skills/<name>/`) | `vds-skills-catalog-alignment-cleanup` Phase 5 deletes the 6 vendored sub-skills + adds `.gitignore` rule preventing regeneration |
| `vds-scripts/*_orchestrator/` (31 orchestrators) | **Classified per FR-17** (Orchestrator coverage classification): 9 Tier A (have a corresponding skill), 0 Tier B (candidate for promotion), 22 Tier C (covered by `vds-scripts-skill` umbrella or too minimal) | No skill-creation work required; classification table in `who-ecosystem-alignment` Phase 4 design.md |
| `vds-cli`, `mcp_server`, `platform_core`, `vds_agent_core`, `vds_evolution`, etc. | **In scope per FR-8** (Repo purpose: runtime Python only) | No change; these are exactly what vds-scripts SHOULD hold |

---

## Git State

```
HEAD: f7158c9 docs: add first-audit-run tutorial (FR-1.5 gap fill)
Status: Clean (pushed to origin)
Worktrees: 1 (scripts repo only)
```

---

## Functional Tests

| Test | Result |
|------|--------|
| scripts .venv status | ✓ OK |
| mono .venv status | ✓ OK |
| mono from /tmp | ✓ OK |
| mono from scripts_repo | ✓ OK |
| tracked shell | ✓ OK |

---

## Key Findings

1. **Scripts consistency**: All 3 scripts use spec_from_file_location fix
2. **Mono matches tracked**: vds-evolution-mono.sh == mono/.venv/bin/vds-evolution
3. **Openspace hook**: Present in mono .venv, bypassed by fix
4. **Root cause**: sys.path_hooks modification by openspace
5. **Fix verified**: Works from any CWD
6. **Git clean**: All changes pushed

---

## Conclusion

The ecosystem is fully aligned and functioning correctly. The openspace __path_hook__ is a known issue with mixed venv environments (OpenSpace + vds-evolution). The spec_from_file_location workaround is the correct solution for this scenario.