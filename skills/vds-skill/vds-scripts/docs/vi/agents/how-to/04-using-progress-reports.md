<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# How To: Generate Progress Reports

## Prerequisites

1. **Repos synced**: `vds-cli audit sync repos --bitbucket-project INSURANCE-AI`
2. **BMAD knowledge graph**: Must exist at `~/.vds/cache/repos/INSURANCE-AI-project/bmad_ntbh/`
3. **Database** (optional): Set `VDS_PROGRESS_STATE_DSN` in `~/.vds/.env` for persistence

## Quick Start

```bash
# Structural-only report (fast, ~2s)
vds-cli progress report -p INSURANCE-AI --dimensions structural --skip-sync

# Check your score
vds-cli progress db status
```

## Common Workflows

### Daily Score Check

```bash
# Generate report and check trend
vds-cli progress report -p INSURANCE-AI --dimensions structural --skip-sync -q
vds-cli progress db status
```

### Deep-Dive a Specific FR

```bash
# FR8 analysis in JSON
vds-cli progress report -p INSURANCE-AI --fr FR8 --dimensions structural --format json --skip-sync -q
```

### Scripted/CI Usage

Use `--quiet` (`-q`) and `--format json` for clean machine-readable output:

```bash
SCORE=$(vds-cli progress report -p INSURANCE-AI --dimensions structural --format json --skip-sync -q \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['overall_score'])")
echo "Current score: $SCORE"
```

### Resume an Interrupted Run

If a run fails mid-pipeline, the checkpoint is saved in the DB:

```bash
# The run_id is printed in the log output
vds-cli progress report -p INSURANCE-AI --resume-run-id <uuid-from-failed-run>
```

### Topology Exploration

```bash
# List all FRs in the knowledge graph
vds-cli progress topology -p INSURANCE-AI -q | jq '.fr_modules[].fr_id'

# Count services
vds-cli progress topology -p INSURANCE-AI -q | jq '.service_catalog | length'
```

## LLM Provider Selection (Phase 3)

Use `--llm-provider` to control which LLM backend scores dimensions 7-8:

```bash
# Auto-detect from environment (default)
vds-cli progress report -p INSURANCE-AI --llm-provider auto

# Explicit provider
vds-cli progress report -p INSURANCE-AI --llm-provider openai    # requires OPENAI_API_KEY
vds-cli progress report -p INSURANCE-AI --llm-provider anthropic # requires ANTHROPIC_AUTH_TOKEN
vds-cli progress report -p INSURANCE-AI --llm-provider ollama    # requires Ollama on localhost:11434

# Disable LLM entirely (equivalent to --dimensions structural)
vds-cli progress report -p INSURANCE-AI --llm-provider none --skip-sync
```

Auto-detect order: explicit `--profile` → `VDS_AUDIT_LLM_ENABLED=0` hard-disable → `OPENAI_API_KEY` / `ANTHROPIC_AUTH_TOKEN` env → structural-only.

**Ollama is NOT auto-detected** — it must be requested via `--llm-provider ollama` explicitly. This is because Ollama's installed models may be cloud-routed, embedding-only, or reasoning models that need different token budgets, so aggressive auto-detection caused score regressions. When auto mode finds no provider, it leaves dims 7-8 as `None` and scores renormalize across structural dimensions only — **auto-detect is guaranteed to produce the same score as `--llm-provider none`**.

## JSON Report Schema (Phase 3)

Phase 3 reports include three new top-level keys in `--format json` output:

```bash
vds-cli progress report -p INSURANCE-AI --dimensions structural --format json --skip-sync -q \
  | jq '{heatmap: .heatmap, repo_health: .repo_health, coverage: .dimension_coverage}'
```

- **`heatmap`**: List of FR × dimension objects — boolean pass/fail and numeric scores per FR
- **`repo_health`**: Per-repo test ratio and `green`/`yellow`/`red` health indicator
- **`dimension_coverage`**: Pass-rates and averages across all FRs (e.g. `service_exists: 0.9`)

## Scripted Score + Coverage

```bash
vds-cli progress report -p INSURANCE-AI --dimensions structural --format json --skip-sync -q | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Score: {d[\"overall_score\"]}')
print(f'Doc chain: {d[\"dimension_coverage\"].get(\"doc_chain_complete\", \"N/A\")}')
print(f'Recommendations: {sum(len(s[\"recommendations\"]) for s in d[\"sections\"])}')
"
```

## Progressive Disclosure Modes (Phase 4)

`--mode` picks a rendering tier. All four modes use the same underlying computation — only the rendered output differs:

```bash
# Exec: ≤20 lines. Slack pastes, email digests, GitHub status checks.
vds-cli progress report -p INSURANCE-AI --mode exec --skip-sync -q

# Summary: ≤100 lines. Standup review, code-review context, daily digest.
vds-cli progress report -p INSURANCE-AI --mode summary --skip-sync -q

# Standard: ~564 lines. Default. Byte-identical to pre-Phase-4 output (heatmap,
# per-FR detail, trend, risk register). Use when daily development review.
vds-cli progress report -p INSURANCE-AI --skip-sync -q   # --mode standard is implicit

# Full: ~581 lines. Standard + stratified cluster sub-reports + appendices.
# Use for quarterly audits, retrospectives, compliance packets.
vds-cli progress report -p INSURANCE-AI --mode full --skip-sync -q
```

**Tip**: Start with `--mode exec` when piping into chat notifications and bump up to `summary` or `full` only when someone asks "why did the score move?"

## CI/CD Quality Gates (Phase 4)

Make progress report failures break your pipeline. `vds-cli progress report` exits with:

- `0` — report generated, no gates tripped
- `1` — runtime error (missing DSN, sync failed, crash)
- `2` — **quality gate failed** (report file still written)

```bash
# Fail the build if overall score drops below 60
vds-cli progress report -p INSURANCE-AI --skip-sync --fail-under 60 -q

# Fail if any FR regressed by more than 15 points vs the previous run
vds-cli progress report -p INSURANCE-AI --skip-sync --fail-on-regression -q

# Compare against a specific historical run instead of "previous"
vds-cli progress report -p INSURANCE-AI --skip-sync \
  --fail-on-regression --baseline <run-id> -q

# Combine gates — any trip exits 2
vds-cli progress report -p INSURANCE-AI --skip-sync \
  --fail-under 60 --fail-on-regression -q
echo $?   # 2 if either gate fails
```

**Important**: Unlike SonarQube's `sonar-scanner` (which silently exits 0 even on gate failure unless you pass `-Dsonar.qualitygate.wait=true`), `vds-cli progress` honors gate flags immediately when set. The report file is always written before the non-zero exit, so your CI can still upload it as an artifact.

**GitHub Actions example**:

```yaml
- name: Progress check
  run: |
    vds-cli progress report -p INSURANCE-AI --skip-sync \
      --fail-under 60 --mode exec -q > progress.txt
  continue-on-error: false   # exit 2 fails the step

- name: Upload report
  if: always()   # still upload when the step failed
  uses: actions/upload-artifact@v4
  with:
    path: ~/.vds/cache/progress-reports/
```

## Bimodal Distribution / Stratified Clusters (Phase 4)

When your FR scores split cleanly into "passing FRs" and "failing FRs" with no middle tier, the report emits a `bimodal_warning` block. This is the **valence-gap heuristic** — a UX signal, not statistical bimodality (ADR-Q7).

Detection rules (all must hold):

1. `total_frs ≥ 10`
2. `medium == 0`
3. `high_count > 0 AND low_count > 0`
4. `min(high, low) / total ≥ 0.25` (dominance guard — kills skewed-unimodal false positives like 14/0/1)

When detected, `summary` and `full` modes render **stratified sub-reports**: a high-cluster mini-report (passing FRs, avg score, weakest remaining dim, top remaining action) and a low-cluster mini-report (blocked FRs, dominant blocker, highest-priority fix).

Extract cluster data from JSON:

```bash
vds-cli progress report -p INSURANCE-AI --format json --skip-sync -q \
  | jq '.bimodal_warning'
# {
#   "detected": true,
#   "stratification_variable": "service_exists",
#   "high_cluster": {
#     "label": "passing",
#     "fr_ids": ["FR6", "FR7", "FR8", ...],
#     "avg_score": 83.6,
#     "dominant_blocker": "test_coverage",
#     "top_recommendation_fr": "FR8"
#   },
#   "low_cluster": { ... }
# }
```

**Interpretation**: A bimodal warning usually means *"the services that exist are healthy; the ones that are failing aren't built yet"* — your work is recipe-style scaffolding, not debugging the passing services. Use `dominant_blocker` to pick the next sprint focus and `top_recommendation_fr` as the starting FR.

## Trend Regression Bucketing (Phase 4)

When a previous run exists, the report bucketizes FR deltas vs baseline:

| Δ score | Bucket | Render |
|---------|--------|--------|
| `Δ ≤ -15` | **Critical regression** | Loud callout + risk register entry |
| `-15 < Δ ≤ -5` | Minor regression | Subtle callout |
| `-5 < Δ < 5` | Noise floor | Ignored |
| `5 ≤ Δ < 15` | Improvement | Noted |
| `Δ ≥ 15` | Major improvement | Highlighted |

Thresholds are intentionally simple for Phase 4. Phase 4.1 will upgrade to **Western Electric Rules** (3σ single-point, 2-of-3 at 2σ, 4-of-5 at 1σ) using rolling mean/stddev from `daily_scores`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "no DSN provided" | Set `VDS_PROGRESS_STATE_DSN` in `~/.vds/.env` |
| "bmad_ntbh not found" | Run `vds-cli audit sync repos --bitbucket-project INSURANCE-AI` |
| Structlog lines in output | Use `-q` flag or redirect stderr (`2>/dev/null`) |
| Score unchanged after code changes | Re-sync repos (remove `--skip-sync`) |
| LLM not detected | Check `OPENAI_API_KEY` / `ANTHROPIC_AUTH_TOKEN` in `~/.vds/.env`, or use `--llm-provider none` |
| CI shows exit 0 when score is low | Confirm `--fail-under <score>` flag is set — gates are opt-in |
| `--fail-on-regression` not tripping | No baseline exists yet (first run) or baseline is outside the noise floor — pass `--baseline <run-id>` explicitly |
| `bimodal_warning.detected: false` when I expected true | Check `total_frs ≥ 10`, `medium == 0`, dominance `≥ 0.25` — skewed distributions like 14/0/1 are rejected by design |
| `--mode exec` output missing trend | Exec mode is deliberately ≤20 lines; use `--mode summary` for trend sparklines |
| Standard mode output looks different | Should be byte-identical to Phase 3. File a bug if it's not — the G-Q11c structural invariants test guards this. |
