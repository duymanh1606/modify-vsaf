<!-- diátaxis: how-to -->

# Phase 131 Confluence Upload and Recovery

Use this guide when enabling Confluence publication through `workflow-projects`.
When running from a dedicated `vds-scripts` worktree, prefer `./scripts/worktree_uv.sh run --project audit_orchestrator ...` over plain `uv run ...` so a different checkout's active `.venv` does not leak into the current worktree.

> **Note — interactive use vs. shell scripts**: The `uv run --project <path>` commands below are for interactive terminal or agent use from the repo root. When writing shell scripts, use `vds_uv_run_package <member>` from `scripts/vds_sh_helpers.sh` instead — see `scripts/README.md` for the canonical contract.

Default child publication writes a rich Confluence page body. `--upload-to-confluence` alone should still publish summary, findings, checklist, and provenance content; `--upload-attachments` only controls whether files are attached alongside that page body.

## Upload ownership model

Upload remains child-owned.

Parent `workflow-projects` does **not** replace child publication logic. Instead it:

- forwards `--upload-to-confluence`
- forwards `--confluence-parent`
- collects child upload outcomes in parent artifacts

Repo-page publication now defaults to the canonical project page as the hierarchy anchor. You do not need to supply `--confluence-parent` for normal runs. The publisher creates one shared `Project Audit - <project name> (<project page id>)` node under that project page and places each repo report page beneath it. When `--confluence-parent` is supplied, it overrides the default anchor for all projects in that invocation — use this only for manual routing corrections. Do not pass `--confluence-parent 88716694` as a global override for Payment publication, as it pins all project audit pages under the department page.

Child `workflow-project` still owns:

- repo page uploads
- project aggregate uploads
- upload error details

Default publication should still produce rich Confluence storage-format page bodies for both repo pages and the project aggregate page. `--upload-attachments` only controls attachment transfer; it must not downgrade the page body to a plain/minimal upload.

## Enabling upload

`--confluence-parent` is no longer required when enabling upload. The normal runtime path anchors repo-page publication on the canonical project page for each child project.

Normal upload invocation (no explicit parent needed):

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --project-storage-keys 88727304,88718940 \
  --prepare-materials \
  --upload-to-confluence \
  --max-projects-prepare-concurrent 2 \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

Use `--confluence-parent` only as a manual override when auto-resolution is insufficient (e.g., routing a project to a non-department parent page):

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --project-storage-keys 88727304 \
  --prepare-materials \
  --upload-to-confluence \
  --confluence-parent 12345 \
  --max-projects-prepare-concurrent 2 \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

> **Note**: `--confluence-parent` supplied to `workflow-projects` overrides auto-resolution for ALL projects in that run. Do not supply it for multi-department runs where projects belong to different departments.

## FR-150 — Confluence parent auto-resolution

FR-150 introduced `_resolve_confluence_parent_for_project`, a utility that auto-derives the correct Confluence parent for each project. It uses a three-tier fallback:

1. **Explicit `--confluence-parent`** — overrides everything; applies to all projects in the run
2. **canonical project page id** — derived from `project_page.page_id`, top-level `page_id`, or `_project_and_department_page_metadata`; routes each project to its own project page
3. **`project_storage_key`** — last-resort fallback when richer project-page metadata is unavailable

This means:
- Payment department projects publish under their own canonical project pages by default
- Finance Platform projects publish under their own canonical project pages by default
- Admin Products projects publish under their own canonical project pages by default
- Operators running multi-project publication get per-project project-page anchoring without any extra flags

Auto-resolution is logged with `confluence_parent_auto_resolved` when the resolved parent differs from an explicit argument. Check `dispatch-manifest.json` for `resolved_parent` per child project.

### Payment department — publication examples

Single project without explicit parent (normal case):

```bash
vds-cli audit workflow-project \
  --project-storage-key 91334048 \
  --thread-id <thread_id> \
  --checklist-page-id 88722450 \
  --upload-to-confluence
```

Multi-project across Payment department without explicit parent:

```bash
vds-cli audit workflow-projects \
  --project-storage-keys 91334048,91335346 \
  --checklist-page-id 88722450 \
  --prepare-materials \
  --upload-to-confluence \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

Cross-department run (auto-resolution routes each project to its own department):

```bash
vds-cli audit workflow-projects \
  --project-storage-keys 91334048,88718940 \
  --checklist-page-id 88722450 \
  --prepare-materials \
  --upload-to-confluence \
  --max-projects-concurrent 2 \
  --max-concurrent 4
# 91334048 (Payment) → parent 88716694
# 88718940 (Core Technology) → parent 88718815
```

### When to use `publish-project-run` (Phase 147-E)

`publish-project-run` with `--resume-run` is the explicit publish-only surface (Phase 147-E, implemented in the phase147e worktree). Prefer it over `workflow-project --upload-to-confluence` when you need to publish a completed run without re-evaluating. Supply `--resume-run <thread_id>` to resolve the report directory from the prior run root automatically. FR-150 auto-resolution handles the Confluence parent — no `--confluence-parent` override needed.

## Confluence endpoint note

Current runtime treats configured Confluence URLs as explicit endpoints, not fallback targets. Operators may configure alternate internal or external URLs in the shared config for diagnostics, but runtime operations stay on the selected base URL.

Operational guidance:
- keep the normal internal/external server selection unchanged in commands unless a specific page URL implies the other server,
- treat alternate endpoint probes as connectivity diagnostics, not as a signal that page identity changed,
- if upload or checklist bootstrap fails with hostname reachability symptoms, inspect the configured Confluence URLs before assuming the page id or parent page is wrong.

## What to inspect after upload

### Parent artifacts

Inspect:

- `dispatch-manifest.json`
- `dispatch-progress.state`
- `cross-project-summary.json`

Useful fields include:

- project execution status
- recovery status
- upload summary
- upload errors
- project page identity as page id plus title/display name
- department page identity as page id plus title/display name when lineage is available
- if `parse-registry` starts from a department page or a direct project page, lineage reconstruction must still preserve those same additive `(page_id, title)` pairs before publication summaries are written
- child report directories
- collected `confluence_repo_page_ids`
- collected `confluence_aggregate_page_id`

### Child artifacts

Use child report roots for authoritative publication truth when triaging upload problems.

## Recovery states to watch

Parent rollups may classify child outcomes such as:

- `completed`
- `failed`
- `timed_out`
- `exception`
- `provider_blocked`
- `upload_failed`

These are recovery aids for project-scope triage. Final child truth still lives in child artifacts and centralized state.

## Resume after partial upload

If a parent run produced the expected manifest, prefer resuming from it rather than reconstructing scope manually.
Use the effective VDS cache root for your environment as defined by the portable Phase 2 contract in `../reference/portable-paths-and-config.md`.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --resume-dispatch-manifest <cache-root>/audit_runs/workflow-projects/<thread_id>/dispatch-manifest.json
```

Before resuming, verify:

- the manifest matches the intended parent run root
- current provider availability is acceptable
- centralized state is still valid for readiness/completeness gates
- the Confluence parent page is still the intended destination

Run-intent guidance:
- when reusing a known prior run, prefer an explicit resume-specific-run or publish-from-run-root path when available
- when you want a clean execution similar to a new Jenkins build, use a fresh run/thread id and do not rely on implicit auto-resume
- do not mix department-level selection with project-page-rooted publication anchors

## Suggested bounded verification sequence

1. Run one or two projects first.
2. Enable upload only after parent artifact shape looks correct.
3. Confirm child repo pages and aggregate page creation.
4. Resume from the parent manifest if upload recovery is needed.

## Caveat

The historical Phase 131 upload-pass-through work is now part of the merged parent runtime. For partial-upload and recovery scenarios, still validate the artifact shape on one or two bounded projects before broad parent reruns.
