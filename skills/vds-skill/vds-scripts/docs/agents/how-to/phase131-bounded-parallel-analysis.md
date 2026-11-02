<!-- diátaxis: how-to -->

# Phase 131 Bounded Parallel Analysis

Use this guide when running the landed `workflow-projects` parent command with explicit outer-project and inner child concurrency settings.
When running from a dedicated `vds-scripts` worktree, prefer `./scripts/worktree_uv.sh run --project audit_orchestrator ...` over plain `uv run ...` so a different checkout's active `.venv` does not leak into the current worktree.

> **Note — interactive use vs. shell scripts**: The `uv run --project <path>` commands below are for interactive terminal or agent use from the repo root. When writing shell scripts, use `vds_uv_run_package <member>` from `scripts/vds_sh_helpers.sh` instead — see `scripts/README.md` for the canonical contract.

## The three concurrency layers

Keep these separate:

1. `--max-projects-prepare-concurrent`
   - parent preparation fan-out ceiling
2. `--max-projects-concurrent`
   - parent project-analysis fan-out ceiling
3. `--max-concurrent`
   - child `workflow-project` repo-dispatch ceiling

The parent runtime now surfaces pressure diagnostics in parent artifacts so operators can distinguish these lanes.

## Recommended starting posture

For bounded verification, start conservatively:

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --registry-page <REGISTRY_PAGE_ID> \
  --prepare-materials \
  --max-projects-prepare-concurrent 2 \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

Then increase only after checking:

- provider launch-readiness
- DB and state responsiveness
- Confluence upload expectations
- child artifact generation rate

## Example bounded runs

### Small explicit slice

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --project-storage-keys 88727304,88718940 \
  --profiles zai-openai \
  --profile-availability active \
  --prepare-materials \
  --max-projects-prepare-concurrent 2 \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

### Registry-driven bounded run

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --registry-page <REGISTRY_PAGE_ID> \
  --max-projects 3 \
  --prepare-materials \
  --max-projects-prepare-concurrent 3 \
  --max-projects-concurrent 2 \
  --max-concurrent 16
```

## Pressure diagnostics to inspect

Parent artifacts may now include a pressure/parallelism section that helps estimate runtime pressure:

- selected projects
- blocked projects
- runnable projects
- effective preparation concurrency
- effective analysis concurrency
- child max concurrent
- maximum parallel repo slots
- counts snapshot

Interpretation:

- effective preparation concurrency = min(selected projects, `--max-projects-prepare-concurrent`)
- effective analysis concurrency = min(runnable projects, `--max-projects-concurrent`)
- maximum parallel repo slots = effective analysis concurrency × child `--max-concurrent`

This is an operator aid, not a promise of perfectly uniform scheduling.

## Resume guidance

The parent command supports:

- `--resume`
- `--resume-dispatch-manifest <path>`

Use resume when you want to continue from an existing parent manifest scope while preserving child lineage and report roots.
Use the effective VDS cache root for your environment as defined by the portable Phase 2 contract in `../reference/portable-paths-and-config.md`.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --resume \
  --report-dir <cache-root>/audit_runs/workflow-projects/<thread_id>
```

Or explicitly:

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --resume-dispatch-manifest <cache-root>/audit_runs/workflow-projects/<thread_id>/dispatch-manifest.json
```

Resume scope is derived from parent artifacts, but readiness, completeness, and launch gating still need authoritative runtime revalidation.

## Operational rule

Do not describe outer-project concurrency as equivalent to child repo concurrency. The parent command and child command each have separate responsibilities and separate limits.
