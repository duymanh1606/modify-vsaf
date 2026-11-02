<!-- diátaxis: reference -->

# Audit Triage Playbook

Use the audit orchestrator as the authoritative triage entrypoint.

## Flow

1. Check environment and credentials.
2. Check state readiness.
3. Inspect source checklist rows with `query-checklist` when checklist-page resolution or row identity is unclear.
4. Run targeted workflow or workflow-project.
4. Validate spec sync before accepting doc or spec changes.

## Checklist Inspection Commands

Use `query-checklist` to inspect source checklist content directly before a rerun when the operator needs to confirm row ids, category placement, or checklist bootstrap behavior without launching workflow evaluation.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit query-checklist --checklist-page 88722450 --summary-only

./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit query-checklist --checklist-page 88722450 --target row-1

./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit query-checklist --checklist-page 88722450 --target chk_1
```

Selector rule:
- Treat `query-checklist` as the canonical selector-discovery surface for source checklist pages.
- Prefer row ids (`row-1`) or numeric row selectors (`1`) from `query-checklist` output when targeting a unique source checklist row.
- Parser check ids such as `chk_1` are accepted but may repeat across sections on the same checklist page, so use them only when you intentionally want that broader match set.
- Do not copy `dispatch-manifest.json` internal payloads such as `explicit:88722450:...` into `workflow --target` or `query-checklist --target`; those are dispatch-internal row-key bundles, not operator-facing selector strings.

If the checklist page should be inferred from centralized state instead of passed explicitly:

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit query-checklist \
  --project-storage-key 88727304 \
  --checklist-profile default \
  --summary-only
```

## Targeted Rerun Commands

> **Recommended for runs expected to take more than 5 minutes**: use `./scripts/run-audit-in-tmux.sh` to prevent session timeout orphaning. The parent process must stay alive while child workflow processes run — tmux ensures this. See [cli-commands.md](./cli-commands.md#persistent-execution) for the full pattern.
> `run-audit-in-tmux.sh` inherits the shared-env bootstrap behavior of `worktree_uv.sh`, so normal runs should load `VDS_AUDIT_STATE_DSN` and other shared runtime keys from `~/.vds/.env` automatically. Explicit `--state-dsn` is still propagated to child workflow lanes after the parent resolves it.

Use the effective repo-cache root for your environment as defined by the portable Phase 2 cache-root model documented in `portable-paths-and-config.md`.

The commands below use the convenient interactive form (`uv run --project <path>` from the monorepo root).
When calling from a shell script, use `vds_uv_run_package audit_orchestrator` instead — see
[`scripts/README.md`](../../scripts/README.md#uv-contract--canonical-usage).

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow <repo-cache-root>/PAR-project/merchant-report \
  --profile zai-openai \
  --project-storage-key 88727304 \
  --thread-id phase124-row2-par-mr-zai \
  --target row-2
```
Note: `--canonical-checklist` is no longer needed — full canonical 56-row evaluation is the default since Phase 133. Use `--target` to run specific rows within canonical mode.

Use `workflow-project` only for project-scope lanes. For single-row `workflow` reruns, use `--target`; do not use unsupported legacy selectors such as `--check-ids` or `--targeted-rows`.
For source-checklist single-row reruns, prefer selectors you already verified with `query-checklist`, for example `--target row-1`. Use `chk_*` only when you deliberately want every source row carrying that repeated parser-local id.

For `CL-002`, expect one of two valid outcome shapes only:
- strict skill routing resolves only `public-interface-boundary-skill`
- for multi-repo CL-002 review, one project-scope `vds-cli public-interface scan-project` artifact may be reused as shared companion context across repo rows
- when knowledge reuse is enabled, `workflow-project` may persist that shared project scan once and expose repo-keyed code-linked companion knowledge to later CL-002 row execution
- that shared artifact is not authoritative by itself; final CL-002 evidence must still stay repo-grounded for the row being finalized
- final exported evidence stays on boundary-relevant code refs; do not keep app-config, logging config, or generic build metadata as authoritative CL-002 evidence unless they directly prove the boundary rule
- decisive verified public-interface boundary violation anchors => `FAIL`
- no confirmed violation plus incomplete repo scan => `PARTIAL` with `evidence_gap_diagnostics.classification=evidence_gap`

For `CL-006`, expect one valid proof-complete pass shape:
- decisive verified production config excerpt => `PASS`
- exported excerpt must retain datasource plus pool-limit keys (`minimum-idle`, `maximum-pool-size`, `max-lifetime` or equivalent)
- generic caveats such as “chưa so sánh trực tiếp với service khác” or “không có bằng chứng trực tiếp để xác nhận ... KHÔNG dùng chung datasource” must not keep the row in `PARTIAL`/`FAIL` once the verified production trace already proves the required app-config keys
- when the row guidance is app-config-specific, strict skill routing should resolve only `app-config-discovery-skill`

For `CL-015`, keep environment precedence explicit:
- decisive production app-config evidence can support `PASS` or `FAIL`
- `staging`, `alpha`, or any lower-precedence env by itself remains `PARTIAL`
- when the row guidance is app-config-specific, strict skill routing should resolve only `app-config-discovery-skill`

For `CL-004`, expect one valid project-scope pass shape:
- strict skill routing recommends only `circular-dependency-skill`
- final exported evidence refs come from the project-scope dependency artifacts, not repo-local fallback files
- decisive pass exports should retain:
  - `project-dependency-graph.json`
  - `project-cycle-report.json`
  - `project-topology.json`

For `CL-007`, expect one migration-only evidence shape:
- strict skill routing resolves only `migration-script-detection-skill`
- once the strict single-skill lane shows an effective execution-class call, take that skill result as authoritative and skip extra unverified-ref corrective retry churn plus DSPy judge/arbitration churn
- final evidence should be migration manifests, changelogs, versioned SQL files, or execution/build wiring
- do not attach centralized app-config companion refs as authoritative `CL-007` evidence
- do not keep generic entities, services, adapters, or unrelated Java classes as authoritative `CL-007` evidence
- if the repo has no migration assets, conclude from that absence directly instead of degrading into arbitrary code refs

## Phase 3 Runtime Verification

Phase 3 requires runtime-availability verification to be separate from
file/catalog alignment. Use currently supported runtime checks and record any
mismatch explicitly instead of assuming convenience commands exist.

### Runtime verification flow

1. Verify credentials with supported doctor commands.
2. Verify active profile/provider availability.
3. Verify project/repo readiness when the workflow depends on prepared state.
4. Verify checklist/source retrieval separately when the problem is source-page
   access rather than repo/project readiness.
5. Record any verified mismatch in a dedicated runtime-status / known-runtime-
   gaps section.

### Supported checks

```bash
# Credentials
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only doctor credentials --require-state-dsn

# Profile / provider availability
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only doctor profile-availability --mode active

# Project readiness
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only state readiness --project <PROJECT_PAGE_ID>
```

### Common runtime-gap scenarios

- **Connectivity**: required services cannot be reached.
- **Auth**: configured credentials are invalid or insufficient.
- **Functional**: the service is reachable but the required operation still
  fails.
- **Environment**: local profile/config/runtime setup does not match the
  documented expectation.

For the full runtime-discovery and gap-reporting contract, see
[Runtime Verification and Gap Reporting](../explanation/runtime-verification-and-gap-reporting.md).

## Checklist Page Resolution Failures

### Symptom: workflow evaluates only 1-3 rows instead of full 56-row canonical

**Root cause**: Checklist auto-discovery failed — the checklist page is not a direct child of the project page, so the runtime falls back to targeted mode.

**Fix**: Pass `--checklist-page-id <CHECKLIST_PAGE_ID>` explicitly to restore full canonical evaluation.

For Payment department projects, the verified working command is:

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow <repo-cache-root>/<PROJECT-KEY>-project/<repo> \
  --project-storage-key <PSK> \
  --checklist-page-id 88722450 \
  --thread-id <thread_id>
```

Confirmed bootstrap signal: `canonical_checklist_bootstrap_preflight_passed: source=explicit_page_id`

For `workflow-project` (project scope):

```bash
vds-cli audit workflow-project \
  --project-storage-key <PSK> \
  --thread-id <thread_id> \
  --checklist-page-id 88722450
```

For one full prepared repo under project semantics, prefer `--scope-id` from `parse-repo` and omit `--profiles`:

```bash
./scripts/run-audit-in-tmux.sh <session-name> \
  workflow-project \
  --project-storage-key <PSK> \
  --scope-id <SCOPE_ID_FROM_PARSE_REPO> \
  --checklist-page-id 88722450 \
  --max-concurrent 6 \
  --upload-to-confluence \
  --incremental-upload \
  --new-run
```

Interpretation rules:
- Prefer `--scope-id` for deterministic DB-native one-repo narrowing on the current merged mainline baseline.
- Existing `--seed-payload` JSON remains a compatibility path only and emits deprecation warnings.
- Omitting `--profiles` means "use all currently available profiles after active preflight".
- `--max-concurrent` caps simultaneously active child lanes only. The total participating profile count may be larger over the full run.
- Use tmux for this path; parent `workflow-project` must stay alive while child profile lanes run.
- Phase 156 publication hardening re-parents reused Confluence pages automatically, skips cross-project page-id collisions during registry backfill, and strips `--incremental-upload` when upload is disabled by offline mode.
- Treat the full Phase 159 work-stealing scope as planned until the new flags appear in live help on mainline.

For `workflow-projects` (multi-project):

```bash
vds-cli audit workflow-projects \
  --project-storage-keys <PSK1,PSK2,...> \
  --checklist-page-id 88722450 \
  --prepare-materials \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

**Page ID facts**:
- `88722450` — standard backend checklist page; correct for Payment department. Use this one.
- `88716673` — Payment-specific page with `checklist_topology_report=null`; do NOT use as explicit checklist page; causes topology parse failure and 0/56 rows.
- `88716694` — Payment department parent page; use with `parse-registry --registry-page` to discover child projects.

**Diagnosis steps**:
1. Check workflow log for `checklist_discovery_failed` or `canonical_checklist=False`.
2. Confirm the project page ID is correct (not the department page).
3. Run `vds-cli audit doctor check-confluence --json` to confirm which Confluence endpoints are reachable before assuming a checklist bootstrap problem.
4. Use `query-checklist --checklist-page 88722450 --summary-only` to verify the source checklist page is reachable and parsable before rerunning workflow.
5. If direct CQL search looks suspicious, run `vds-cli confluence-cli search -s internal -q 'type=page' --limit 2 --json` to verify the internal server path preserves `start=0` correctly.
6. If checklist reads need the older external scope intentionally, set `VDS_AUDIT_CHECKLIST_READ_SERVER=external` explicitly before rerunning.
7. Re-run with `--checklist-page-id 88722450` and verify bootstrap signal shows `source=explicit_page_id`.
8. If publication is enabled, `--confluence-parent` is auto-resolved from department hierarchy (FR-150) — omit it in normal runs. If publication created pages in the wrong location, use DB-backed publish state plus parent workflow logs first; inspect `dispatch-manifest.json` only as a debug artifact when needed for historical run context.
9. When investigating a known prior run, prefer explicit resume-specific-run or publish-from-run-root surfaces over implicit auto-resume.

**Live log note**:
- Realtime JSONL logs are baseline behavior.
- When triaging with `--target`, root `--verbose`, `--trace`, `--debug-evidence-context`, or `--debug-batch-timing`, the workflow runtime now auto-enables richer live agent event logging for the lane and its child runs.
- Since Phase 155, `--debug-evidence-context`, `--debug-batch-timing`, and `--trace` are accepted on `workflow-project` and forwarded to child `workflow` lanes. They are still not accepted directly on `workflow-projects`.
- `--verbose` is a root-level flag: use `vds-cli audit --verbose workflow ...`, not `vds-cli audit workflow ... --verbose`.
- Expect full payload traces only for `--trace`, `--debug-evidence-context`, or `--debug-batch-timing`; targeted-only reruns keep the lighter live stream.

## Resilience Troubleshooting

### Symptom: all profiles circuit-tripped after a run with timeouts

**Root cause (pre-fix)**: `_classify_provider_failure` in `workflow_cmds.py` previously checked auth keywords before transient keywords. Timeout responses that contained an auth-adjacent substring were misclassified as auth failures, permanently tripping the circuit breaker.

**Fix**: transient keywords are now checked first; timeout handler always classifies as `transient`. Timeouts can no longer permanently trip the circuit breaker.

**If still occurring**: check whether the provider actually returned an auth error (401/403) vs a timeout. Run `vds-cli audit --json-only doctor profile-availability --mode active` to inspect current provider health state.

### Symptom: state manifest load timeouts when running concurrent workflows

**Root cause**: default `VDS_AUDIT_STATE_API_TIMEOUT_SECONDS` is 15 s, which is insufficient when multiple child workflows load the manifest simultaneously.

**Fix**: add `VDS_AUDIT_STATE_API_TIMEOUT_SECONDS=120` to `~/.vds/.env` and restart the workflow.

## Sources

- [Monorepo baseline](../../../../AGENTS.md)
- [Audit orchestrator guide](../../../audit_orchestrator/README.md)
- [Scripts workspace guide](../../README.md)
