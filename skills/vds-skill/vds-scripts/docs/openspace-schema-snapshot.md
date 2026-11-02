# OpenSpace SQLite Schema Snapshot

**Generated**: 2026-04-20
**Source**: `~/.tools/OpenSpace/.openspace/openspace.db`
**Verification**: `PRAGMA table_info(execution_analyses)`

## Schema Verification (TSK-0.1a Gate)

### execution_analyses Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| task_id | TEXT | Task identifier (UNIQUE constraint) |
| timestamp | TEXT | ISO-8601 timestamp |
| task_completed | INTEGER | Boolean (0/1) |
| execution_note | TEXT | Execution notes |
| tool_issues | TEXT | JSON list of tool issues |
| **candidate_for_evolution** | INTEGER | Evolution candidate flag (0/1) ✅ |
| **evolution_processed_at** | TEXT | ISO timestamp when evolution ran ✅ |
| evolution_suggestions | TEXT | JSON list of EvolutionSuggestion dataclass |
| analyzed_by | TEXT | Analyzer identity |
| analyzed_at | TEXT | Analysis timestamp |

### Key Observations

1. **candidate_for_evolution column**: Present ✅ (not `quality_indicator` as incorrectly assumed in v0.5.3)
2. **evolution_processed_at column**: Present ✅ (added by upstream commit `020a879`)
3. **evolution_suggestions field**: Uses full name `evolution_suggestions` (not shortened `suggestions`)

### API Contract (Consumed by VDS)

```python
# Gate 1 consumer API - TSK-1.5
store.load_evolution_candidates(limit=50, include_processed=False)
# Returns List[ExecutionAnalysis] where candidate_for_evolution=1 AND evolution_processed_at IS NULL

# Queue depth probe - TSK-1.5, TSK-1.11
store.get_stats()["unprocessed_evolution_candidates"]
# Returns int (NOT .n_unprocessed_candidates attribute access)

# Lifecycle marking - handled by openspace/skill_engine/evolver.py:306
# VDS MUST NOT write evolution_processed_at column
```

### Upstream Contract References

- `openspace/skill_engine/types.py:26` - EvolutionType enum
- `openspace/skill_engine/types.py:198` - EvolutionSuggestion dataclass (no `severity` field)
- `openspace/skill_engine/types.py:253` - ExecutionAnalysis dataclass
- `openspace/skill_engine/store.py` - SkillStore methods

### Other Tables

| Table | Purpose |
|-------|---------|
| skill_records | Canonical skill registry |
| skill_lineage_parents | Skill parent relationships |
| skill_judgments | Skill application judgments |
| skill_tool_deps | Skill tool dependencies |
| skill_tags | Skill tagging metadata |

## Phase 1 Opening Gate

This artifact is the hard gate for Phase 1 opening per tasks.md:

> "TSK-0.1a is a hard gate for Phase 1 — Gate 1 (TSK-1.5) cannot be built on an unverified schema."

**Verification checklist**:
- [x] `candidate_for_evolution INTEGER` column exists
- [x] `evolution_processed_at TEXT` column exists
- [x] `store.load_evolution_candidates()` returns expected shape
- [x] `store.get_stats()["unprocessed_evolution_candidates"]` returns int
