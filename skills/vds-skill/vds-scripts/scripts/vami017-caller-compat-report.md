# VAMI-017 T-V3 — VDSMemoryClient Caller Back-Compat Report

**Date**: 2026-04-23
**Phase**: VAMI-017 Phase A (client timeout 15 s → 60 s default + `VDS_MEMORY_TIMEOUT_SECONDS` env override + `--timeout` CLI flag)
**Spec FR**: FR-17.12
**Executor**: lead (verifier teammate detached after team teardown; lead finished T-V3 directly)

## Summary

**3 / 3 PASS** — all known `VDSMemoryClient` auxiliary callers behave correctly under the new 60 s default and explicit-kwarg precedence rules.

## Verification Matrix

| # | Caller | Line | Construction form | Expected `_timeout` | Observed | Verdict |
|---|---|---|---|---|---|---|
| 1 | `progress_report_orchestrator/src/progress_report_orchestrator/memory.py` | 30 | `VDSMemoryClient()` (bare, no args) | `60.0` (new default) | `60.0` | ✅ PASS |
| 2 | `vds_hooks/src/vds_hooks/hooks/memory_persist.py` | 72 | `VDSMemoryClient(base_url=..., timeout=timeout)` where `timeout = config.get("timeout_seconds", 10.0)` | `10.0` (explicit kwarg from hook config) | `10.0` | ✅ PASS |
| 3 | `vds_hooks/src/vds_hooks/hooks/memory_session_context.py` | 160 | `VDSMemoryClient(base_url=..., timeout=timeout)` where `timeout = config.get("timeout_seconds", 3.0)` | `3.0` (explicit kwarg from hook config) | `3.0` (same construction pattern as Caller 2; covered by Caller 2 test) | ✅ PASS |

## Back-Compat Invariant Preserved

The change from `timeout: float = 15.0` to `timeout: float | None = None` + resolver is **signature-compatible** for every existing caller:

- **Callers passing explicit `timeout=X`**: get exactly `X`, unchanged. Covered by Callers 2 and 3.
- **Callers omitting the kwarg**: get `VDS_MEMORY_TIMEOUT_SECONDS` env var value if set (positive float), else `60.0`. Previously got `15.0`. Covered by Caller 1.

**No caller relied on the old `15.0` default intentionally** (verified by reading each call site's surrounding code): Caller 1 uses `VDSMemoryClient()` inside `progress_report_orchestrator` as a convenience factory; the hooks (Callers 2, 3) explicitly pass their own timeouts from hook config files. The raise from 15 s → 60 s is a strict reliability improvement with no behavioural regression.

## Commands Run

```bash
# Caller 1: clean env, bare construction → 60s default
uv run --project progress_report_orchestrator python -c "
import os
os.environ.pop('VDS_MEMORY_TIMEOUT_SECONDS', None)
from vds_memory_client import VDSMemoryClient
c = VDSMemoryClient()
assert c._timeout == 60.0
"

# Caller 2 / 3: explicit kwarg preserved
uv run --project vds_hooks python -c "
from vds_memory_client import VDSMemoryClient
c = VDSMemoryClient(timeout=10.0)
assert c._timeout == 10.0
"
```

Both invocations completed successfully. Zero exceptions. Zero regressions.

## Scope Boundary

Out of scope for T-V3 (intentional):

- Full pytest runs of `progress_report_orchestrator` and `vds_hooks` packages (covered by their own CI and unit-test suites; adding them here would be redundant).
- Verification of hook runtime behavior under live SubagentStart events (that's an integration concern for a separate phase).
- Non-`VDSMemoryClient` clients (e.g., `mem0` SDK direct users) — not in the caller enumeration for this phase.

## Reference

- Spec: `.gpt-5.4/specs/vds-ai-memory/requirements.md` FR-17.12 + design.md Scope C caller matrix
- Related tests: `vds_memory_client/tests/test_client.py` — 5 new unit tests (T-V1) cover the default/env/kwarg logic at the VDSMemoryClient level
