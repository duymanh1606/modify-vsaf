<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# How To Use VDS AI Memory

Use the skill entrypoint first:

- Skill: `WHO-project/vds-skills/skills/vds-ai-memory-skill/SKILL.md`

Operational context:

- [WHO project baseline](../../../AGENTS.md)
- Skills catalog: `WHO-project/vds-skills/README.md`

## Prerequisites

Start the active VDS AI Memory runtime before using the CLI:

```bash
cd WHO-project/vds-scripts/memory_orchestrator
docker compose --profile dev --profile mem0 up -d
```

This starts the active memory runtime stack from `memory_orchestrator/`.

> `WHO-project/vds-ai-memory/` is historical/archive-only and should not be used for current startup or runtime guidance.

## Base URL Resolution

`vds-cli memory` (and direct `vds-memory`) load `~/.vds/.env` and resolve the
API base URL in this order:

1. `VDS_MEMORY_API_URL`
2. `http://localhost:${API_PORT}` (when `API_PORT` is set)
3. `http://localhost:8000`

In most sessions, you should not need to pass `--api-url` manually.

## CLI Commands (Recommended)

The `vds-cli memory` subcommand is the primary interface for agents and interactive use.

```bash
# Search memories by semantic query
vds-cli memory search "auth patterns" --limit 5

# Store a new memory
vds-cli memory store "PAR billing uses Spring Boot 3.2" \
  --category code --importance high --tags spring-boot,PAR

# Retrieve a specific memory by ID
vds-cli memory get <memory_id>

# List active sessions
vds-cli memory sessions

# Health check
vds-cli memory health

# Statistics (machine-readable)
vds-cli memory --json-only stats
```

## Command Discovery

- Use `vds-cli memory ...` for normal routed execution.
- Put global options before the subcommand, for example: `vds-cli memory --json-only stats`
- Use the direct package entrypoint for full command help:

```bash
./scripts/worktree_uv.sh run --project memory_orchestrator vds-memory --help
```

## Practical Rules

- Capture durable decisions with dates, paths, commands, and evidence.
- Prefer short decision records over long narrative summaries.
- Use tags to improve searchability across agents.
- Do not store secrets, tokens, or personal data.

## Hook Integration (automatic, since Phase 6 HX.2)

VDS AI Memory is wired into Claude Code via two parallel hook paths, both registered in `.claude/settings.local.json`:

1. **Command path** (fallback, works even when Docker is down) — uses the `vds-cli memory-*` console scripts installed in `WHO-project/vds-scripts/.venv/bin/`:
   - `vds-cli memory-session-context` on `SessionStart` (5s timeout) — pre-loads prior decisions
   - `vds-cli memory-persist-stop` on `Stop` (30s) — auto-persists session summary
   - `vds-cli memory-persist-stop --session-end` on `SessionEnd` (30s) — final summary
   - `vds-cli memory-prompt-search` on `UserPromptSubmit` (3s) — per-prompt memory search

2. **HTTP path** (low-latency, ~20× faster when Docker is up) — calls dedicated endpoints on the running memory service:
   - `POST <BASE_URL>/api/v1/hooks/session-context` on `SessionStart`
   - `POST <BASE_URL>/api/v1/hooks/session-persist` on `Stop`

`<BASE_URL>` follows the same resolution order in **Base URL Resolution** above.

Both paths run in parallel on the same events as a **dual-path safety net**. HTTP non-2xx responses are non-blocking in Claude Code, so if the memory service is unreachable (rebuilding, stopped, laptop offline), the command path still succeeds. You generally shouldn't need to do anything manually — just use `vds-cli memory store` for explicit saves and the hooks handle the rest.

Env-var toggles: `VDS_HOOK_SESSION_MEMORY=0` disables SessionStart pre-load, `VDS_HOOK_MEMORY_PERSIST=0` disables Stop auto-persist, `VDS_HOOK_MEMORY_DECISIONS=0` disables decision auto-capture. Default all on.
