<!-- diátaxis: explanation -->

<!-- TODO: translate — Vietnamese translation pending -->

# Runtime Verification and Gap Reporting (Phase 3)

Phase 3 of the WHO ecosystem alignment introduces a strict separation between
file/catalog alignment and live runtime verification. A skills/doc surface can
be internally aligned yet still fail in practice because the required runtime,
credentials, network path, or active skill-discovery surface is incomplete.

This guide defines the operator-facing contract for verifying runtime state
without claiming unsupported CLI surfaces.

## Runtime-Discovery Contract

Runtime verification should confirm the state of the environment actually used
by operators or agents in practice. The contract is evidence-based and should
prefer existing supported commands over hypothetical convenience flags.

### Discovery mechanisms

- **Environment inspection**: confirm required environment variables, config
  roots, and credentials locations are present and point to the expected VDS
  paths.
- **Credential verification**: confirm auth material is usable with existing
  doctor commands such as `vds-cli audit --json-only doctor credentials`.
- **Provider/profile verification**: confirm the configured profile set is
  resolvable and available with existing commands such as
  `vds-cli audit --json-only doctor profile-availability ...`.
- **Readiness verification**: confirm project or repo state is materially ready
  with existing commands such as `vds-cli audit --json-only state readiness ...`.
- **Checklist/source verification**: confirm checklist retrieval and related
  source surfaces with `vds-cli audit query-checklist ...` when the issue involves
  source-checklist reachability rather than repo/project readiness.

### Verification levels

- **L1: Connectivity** — can the operator environment reach the required
  service or source surface?
- **L2: Authentication** — do the configured credentials authenticate
  successfully for the intended surface?
- **L3: Functional** — can an existing supported command perform a real,
  minimal operation such as resolving readiness, listing checklist rows, or
  validating profile availability?
- **L4: Operational suitability** — is the surface usable enough for the
  intended workflow within the expected timeout and environment constraints?

## Known Runtime Gaps

When runtime availability does not match the documented or cataloged
expectation, the gap should be recorded explicitly rather than hidden behind a
generic failure summary.

### Gap classes

- **Connectivity gap** — network path, host resolution, firewall, or transport
  failure prevents access.
- **Authentication gap** — credentials are missing, invalid, expired, or lack
  sufficient permissions.
- **Functional gap** — the service is reachable but the required operation or
  workflow surface still fails.
- **Environment gap** — local profile/config/runtime setup does not match the
  documented expectation.

### Reporting shape

Each verified gap should record:

- **Runtime status**: `READY`, `DEGRADED`, or `UNAVAILABLE`
- **Gap ID**: stable identifier such as `GAP-RT-001`
- **Surface**: which runtime surface failed (credentials, profile availability,
  readiness, checklist retrieval, active skill-discovery, etc.)
- **Description**: what did not match the documented expectation
- **Impact**: what workflows are blocked or degraded
- **Evidence**: exact command output or observed runtime signal
- **Remediation**: next action to resolve or narrow the gap
- **Status**: `OPEN`, `IN_PROGRESS`, or `RESOLVED`

## Supported Operator Verification Pattern

Use only commands already documented and supported in the current repo surface.

### Credentials

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only doctor credentials --require-state-dsn
```

### Profile / provider availability

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only doctor profile-availability --mode active
```

### Project or repo readiness

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only state readiness --project <PROJECT_PAGE_ID>
```

### Checklist/source surface verification

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit query-checklist --checklist-page 88722450 --summary-only
```

## What This Guide Does Not Assume

This guide does **not** assume the existence of convenience commands such as
`vds-cli doctor --runtime-only` or `vds-cli status --show-gaps` unless those
surfaces are implemented and documented elsewhere in the maintained repo.

If such convenience surfaces are introduced later, they should be documented as
an additive follow-up rather than retroactively treated as if they already
exist.

## Relation To Phase 3 Tasks

- **TSK-3.14 / TSK-3.15**: define the runtime-discovery contract and compare
  documented expectations against the active runtime surface used in practice.
- **TSK-3.16 / TSK-3.17 / TSK-3.18**: document fallback behavior, runtime-status,
  and known runtime gaps separately from file/catalog alignment.
- **TSK-3.20 / TSK-3.21 / TSK-3.22**: support deterministic validation and clear
  classification of runtime/tooling failures.
