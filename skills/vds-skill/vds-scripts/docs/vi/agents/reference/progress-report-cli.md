<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# Progress Report CLI Reference

## Overview

The `vds-cli progress` CLI generates multi-dimensional alignment progress reports for
INSURANCE-AI projects. It parses a BMAD knowledge graph, runs structural analysis
across repos, and optionally scores with LLMs.

Entry point: `vds-cli progress` (direct) or `vds-cli progress` (router)

## Commands

### `vds-cli progress report`

Generate a progress report.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-p` / `--bitbucket-project` | TEXT | *required* | Bitbucket project key |
| `--bmad-repo` | TEXT | `bmad_ntbh` | Knowledge graph repo |
| `--output-dir` | PATH | `~/.vds/cache/progress-reports` | Report output directory |
| `--max-concurrent` | INT | `4` | Max parallel structural + LLM analyses |
| `--profile` | TEXT | None | LLM runtime profile |
| `--llm-provider` | TEXT | `auto` | `auto`, `openai`, `anthropic`, `ollama`, `none` |
| `--dimensions` | TEXT | `all` | `all` or `structural` |
| `--fr` | TEXT | None | Single FR deep-dive (e.g. `FR8`) |
| `--format` | TEXT | `markdown` | `markdown` or `json` |
| `--skip-sync` | FLAG | False | Skip repo sync |
| `--resume-run-id` | TEXT | None | Resume interrupted run |
| `--mode` | TEXT | `standard` | Rendering tier: `exec` (≤20 lines), `summary` (≤100), `standard` (Phase 3 backward-compat), `full` (everything) |
| `--fail-under` | FLOAT | None | Exit 2 if overall_score below threshold (CI gate) |
| `--fail-on-regression` | FLAG | False | Exit 2 if any FR has critical regression (Δ ≤ -15) |
| `--baseline` | TEXT | None | Explicit baseline run_id for regression comparison (overrides "previous run" default) |
| `-v` / `--verbose` | FLAG | False | DEBUG-level logging |
| `-q` / `--quiet` | FLAG | False | Suppress all log output |

### `vds-cli progress topology`

Dump the parsed knowledge graph as JSON.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-p` / `--bitbucket-project` | TEXT | *required* | Bitbucket project key |
| `--bmad-repo` | TEXT | `bmad_ntbh` | Knowledge graph repo |
| `-q` / `--quiet` | FLAG | False | Suppress log output |

### `vds-cli progress db init`

Create all 5 tables (idempotent).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dsn` | TEXT | env | Postgres DSN |

### `vds-cli progress db status`

Show table presence, run count, and last score.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dsn` | TEXT | env | Postgres DSN |

## LLM Provider Semantics (`--llm-provider`)

| Value | Behavior |
|-------|----------|
| `auto` (default) | Detect cloud LLM from env vars (`OPENAI_API_KEY`, `ANTHROPIC_AUTH_TOKEN`). If none found, degrade gracefully: dims 7-8 stay `None`, score renormalizes across structural dims. Produces the **same score as `none`** when no credentials are available. |
| `openai` | Force OpenAI — requires `OPENAI_API_KEY` or `VDS_AUDIT_LLM__API_KEY`. |
| `anthropic` | Force Anthropic — requires `ANTHROPIC_AUTH_TOKEN` or `VDS_AUDIT_LLM__API_KEY`. |
| `ollama` | Force Ollama at `localhost:11434`. **Not** part of auto-detect — must be explicit. |
| `none` | Hard-disable LLM scoring. Dims 7-8 stay `None`, structural-only renormalization applies. |

**Why Ollama is opt-in only:** Local Ollama installations may have cloud-routed models (need auth), embedding-only models (no chat support), or reasoning models that need larger `max_tokens`. Aggressive auto-detection caused score regressions. Users who want Ollama scoring must pass `--llm-provider ollama` explicitly.

## Rendering Modes (`--mode`, Phase 4)

Four-tier progressive disclosure. Every mode uses the same underlying
computation — modes are purely rendering flags.

| Mode | Line budget | Content | Use case |
|------|------------|---------|----------|
| `exec` | ≤ 20 | Title, overall score, delta, one-line distribution, top-1 action | Slack/email notifications, GitHub status checks |
| `summary` | ≤ 100 | Exec content + full summary table + top-3 + score distribution + bimodal callout + dimension coverage | Standup view, code review context |
| `standard` (default) | ≈ 564 | Phase 3 backward-compat output (heatmap, repo health, per-FR detail, trend, risk register). **Byte-identical to Phase 3** — guarded by G-Q11c snapshot gate | Daily development review |
| `full` | ≈ 581 | Standard + stratified cluster sub-reports + appendices | Audit / compliance / retrospective |

**Backward compatibility guarantee**: `--mode standard` produces the same
markdown output as pre-Phase-4 default mode. Phase 4 features (bimodal
callout, stratified sub-reports, dual-metric coverage with sparklines,
regression subsections) appear only in `summary` and `full` modes.

## CI/CD Exit Codes (Phase 4)

| Exit code | Meaning |
|-----------|---------|
| `0` | Report generated, no gates tripped |
| `1` | Runtime error (DSN missing, sync failed, crash) |
| `2` | **Quality gate failed** — report file still written |

Gate flags:

| Flag | Effect |
|------|--------|
| `--fail-under <score>` | Exit 2 if `overall_score < score` |
| `--fail-on-regression` | Exit 2 if any FR has `Δ ≤ -15` vs baseline |
| `--baseline <run-id>` | Explicit baseline comparison (overrides "previous run" default) |

**⚠ SonarQube anti-pattern avoided**: The SonarQube `sonar-scanner` CLI
returns exit code 0 by default even when quality gates fail, unless you
explicitly pass `-Dsonar.qualitygate.wait=true`. This has silently broken
countless CI pipelines. `vds-cli progress report` does NOT have this trap —
`--fail-under` and `--fail-on-regression` are opt-in, but when set they
ARE honored immediately. Report file is ALWAYS written before exit 2, so
CI artifacts are always captured.

**Example CI usage**:
```bash
vds-cli progress report -p INSURANCE-AI --skip-sync --fail-under 60 -q
# exits 2 when score < 60; report still written to ~/.vds/cache/progress-reports/
echo $?  # 2
```

## Bimodal Detection / Valence-Gap Heuristic (ADR-Q7, Phase 4)

When the score distribution has a valence gap (no medium tier), the report
emits a `bimodal_warning` block in both markdown and JSON, with stratified
`high_cluster` / `low_cluster` sub-reports.

Detection rules (all 4 must hold):
1. `total_frs >= 10` (minimum N)
2. `medium == 0`
3. `high > 0 AND low > 0`
4. `min(high, low) / total >= 0.25` (dominance guard)

**Terminology**: the implementation uses `_detect_valence_gap` internally
per ADR-Q7 — this is a UX heuristic, NOT statistical bimodality. True
bimodal detection requires Hartigan's dip test with N ≥ 30. The JSON API
field name `bimodal_warning` is retained for API stability.

**`bimodal_warning` JSON schema** (when `detected: true`):

```json
{
  "detected": true,
  "high_count": 7,
  "low_count": 8,
  "interpretation": "Score splits into high-performers (7 FRs ≥ 60) and low-performers (8 FRs < 30) with no medium tier.",
  "stratification_variable": "service_exists",
  "high_cluster": {
    "label": "passing",
    "fr_ids": ["FR6", "FR7", "FR8"],
    "avg_score": 83.6,
    "dominant_blocker": "test_coverage",
    "top_recommendation_fr": "FR8"
  },
  "low_cluster": {
    "label": "blocked",
    "fr_ids": ["FR1", "FR2"],
    "avg_score": 12.4,
    "dominant_blocker": "service_exists",
    "top_recommendation_fr": "FR1"
  }
}
```

When `detected: false`, only `{"detected": false}` is returned.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VDS_PROGRESS_STATE_DSN` | PostgreSQL DSN for run persistence. Set in `~/.vds/.env`. |
| `VDS_AUDIT_LLM_ENABLED` | Set to `0`/`false`/`no` to hard-disable LLM in auto mode. |
| `OPENAI_API_KEY` | Auto-detected by auto mode → uses `openai` provider. |
| `ANTHROPIC_AUTH_TOKEN` | Auto-detected by auto mode → uses `anthropic` provider. |
| `VDS_AUDIT_LLM__BASE_URL` | Override LLM base URL (for explicit providers). |
| `VDS_AUDIT_LLM__MODEL_STANDARD` | Override LLM model name. |

## Database Schema

5 tables managed by `db init`:

| Table | Purpose |
|-------|---------|
| `progress_runs` | Run metadata, checkpoint phase, overall score |
| `fr_assessments` | Per-FR dimension scores (structural + LLM) |
| `document_hashes` | SHA-256 hashes for incremental analysis |
| `service_analyses` | Per-repo structural metrics (LOC, tests, endpoints) |
| `daily_scores` | One row per project per day for trend tracking |

## Output Files

Reports are written to `~/.vds/cache/progress-reports/<PROJECT>/`:

- `<date>.json` — Machine-readable JSON with all FR scores
- `<date>.md` — Markdown with executive summary, risk table, per-FR breakdown

## Examples

```bash
# Quick structural check
vds-cli progress report -p INSURANCE-AI --dimensions structural --skip-sync -q

# Pipe JSON to jq
vds-cli progress report -p INSURANCE-AI --dimensions structural --format json --skip-sync -q \
  | jq '.overall_score'

# Topology exploration
vds-cli progress topology -p INSURANCE-AI -q | jq '.fr_modules[].fr_id'

# Check last score
vds-cli progress db status
```
