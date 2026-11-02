# VAMI-017 Phase B — Implementation Status & Remaining Work

**Branch**: merged to `master` (commits `ae652ce7` + `e204b671`); `origin/phase181/vami017-scope-a-async` preserved for audit.
**Date**: 2026-04-23 (landed + deployed same day)
**Status**: **T-A1..T-A5 all LANDED and LIVE in running containers** (api/worker/beat rebuilt + restarted 2026-04-23 18:33 UTC). Only T-A6 (wall-clock-gated soak + flag flip) remains.

## What this branch delivers (landed & tested)

| Task | Status | Files | Notes |
|---|---|---|---|
| T-A1 Feature flag `mem0.store_async_mode` | ✅ LANDED | `service/core/config.py` Mem0Config | Default `False`; zero behavior change until flipped |
| T-A2 `POST /memories` 202-async branch | ✅ LANDED | `service/api/ai_memory_api.py` create_memory() | Returns 202 with `{memory_id, status: "queued", poll_url}` when flag on |
| T-A3 Async path in create_memory | ✅ LANDED | `service/services/memory_crud_service.py` elif branch at line ~687 | Skips inline mem0 add + event poll; queues `_enqueue_mem0_push` directly; stamps `mem0_status=pending` |
| T-A4 `GET /memories/{id}/status` endpoint | ✅ LANDED | `service/api/ai_memory_api.py` | Reads `metadata.mem0_status`; normalized taxonomy |
| T-A5 Client `wait_for_mem0_id()` + sync wrapper | ✅ LANDED | `vds_memory_client/.../client.py` | Configurable `poll_interval` + `max_wait`; raises TimeoutError |
| Unit tests for T-A5 | ✅ LANDED | `vds_memory_client/tests/test_client.py` | 3 tests: complete / failed / timeout |

## Remaining (time-gated)

| Task | Reason | Operator action |
|---|---|---|
| T-A6 7-day soak + flag flip default | Wall-clock gated | Enable `MEM0_STORE_ASYNC_MODE=true` (the actual env var name — pydantic-settings `env_prefix="MEM0_"` applied to Mem0Config.store_async_mode) OR set `mem0.store_async_mode=true` in config. Set in `~/.vds/.env` or compose service environment; requires `docker compose -p vds-ai-memory up -d --force-recreate api worker beat` to pick up. Monitor p95 store latency, error rate, DLQ entries over 7 days. If clean, flip the Mem0Config field's default from `False` to `True` in `config.py` via a follow-up PR. |

## Deployment needed to exercise async path

The server-side changes (T-A1, T-A2, T-A3, T-A4) live in `memory_orchestrator` code. The running `vds-ai-memory-api-1` container uses its built image and will NOT pick up these changes until the container is rebuilt and restarted. Canonical restart sequence (per skill `mem0-deploy-skill` + `COMPOSE_PROFILES=dev,mem0` feedback rule):

```bash
# From this repo's stack root (WHO-project/vds-ai-memory/ or memory_orchestrator/ depending on layout)
export COMPOSE_PROFILES=dev,mem0
docker compose build api worker beat
docker compose up -d --force-recreate api worker beat

# Verify the async branch is live
curl -sS http://localhost:8010/api/v1/health/full | jq .overall
# Smoke test with async flag ON. Two things to set:
#   1. Server side — the container reads Mem0Config.store_async_mode from env var MEM0_STORE_ASYNC_MODE.
#      Add to ~/.vds/.env or memory_orchestrator/.env:   MEM0_STORE_ASYNC_MODE=true
#      Then: docker compose -p vds-ai-memory up -d --force-recreate api worker beat
#   2. Client side (optional) — VDS_MEMORY_TIMEOUT_SECONDS is already set to 60s default,
#      no change needed for async smoke.
vds-cli memory store "async smoke payload" --category reference --importance low --tags vami017-async
# Expect (with MEM0_STORE_ASYNC_MODE=true):
#   HTTP 202 Accepted + {memory_id, status: "queued", poll_url: "/api/v1/memories/<id>/status"}
# Then poll:
curl -sS http://localhost:8010/api/v1/memories/<pg_id>/status
# Expect progression: queued → processing → complete (with mem0_id)
# Or use Python client helper:
#   python -c "import asyncio; from vds_memory_client import VDSMemoryClient; \
#     r = asyncio.run(VDSMemoryClient().wait_for_mem0_id('<pg_id>')); print(r)"
```

Until the container is rebuilt: flag reads default False, T-A2/T-A3/T-A4 are dormant, sync path is fully preserved. T-A5 client helper works independently against any live API endpoint.

## How to pick up this work later

```bash
# From monorepo root
cd WHO-project/vds-scripts
git fetch origin
git worktree add ../worktrees/vds-scripts-vami017-b phase181/vami017-scope-a-async
cd ../worktrees/vds-scripts-vami017-b

# Confirm Phase B scaffold
grep -n "store_async_mode" memory_orchestrator/src/vds_memory_orchestrator/service/core/config.py
grep -n "wait_for_mem0_id" vds_memory_client/src/vds_memory_client/client.py

# Run the new unit tests
uv run --project vds_memory_client pytest vds_memory_client/tests/test_client.py -k "wait_for_mem0_id" -v

# Then: implement T-A2 + T-A3 per spec design.md Scope A, add integration tests,
# restart API container, soak, flip flag default, merge to master.
```

## Spec cross-reference

- `.gpt-5.4/specs/vds-ai-memory/requirements.md` — FR-17.7..17.9 (Scope A functional reqs)
- `.gpt-5.4/specs/vds-ai-memory/design.md` — ADR-11..15 (async design decisions)
- `.gpt-5.4/specs/vds-ai-memory/tasks.md` — T-A1..T-A6 (Phase B work package)
