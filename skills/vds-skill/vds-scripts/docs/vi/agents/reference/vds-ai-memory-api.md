<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# VDS AI Memory API

Operational usage currently centers on the skill contract and captured decision records.

## Sources

- `vds-ai-memory-skill` (`WHO-project/vds-skills/skills/vds-ai-memory-skill/SKILL.md`)
- [Use VDS AI memory](../how-to/02-using-vds-ai-memory.md)
- [WHO project baseline](../../../AGENTS.md)

## CLI Commands (Primary)

The `vds-cli memory` subcommand wraps the REST API with session management, auth, and error formatting.

```bash
vds-cli memory search "auth patterns" --limit 5
vds-cli memory store "decision text" --category code --importance high --tags tag1,tag2
vds-cli memory get <memory_id>
vds-cli memory sessions
vds-cli memory health
vds-cli memory --json-only stats
```

Use the routed form for normal execution. Place global flags like `--json-only` before the subcommand. For detailed subcommand help, use `./scripts/worktree_uv.sh run --project memory_orchestrator vds-memory --help`.

## REST API (curl fallback)

Base URL (`/api/v1`) resolves in this order:

1. `VDS_MEMORY_API_URL`
2. `http://localhost:${API_PORT}` (when `API_PORT` is set)
3. `http://localhost:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | POST | Create a session |
| `/memories` | POST | Store a memory |
| `/memories/search` | POST | Search memories |
| `/memories/<id>` | GET | Retrieve memory by ID |
| `/health` | GET | Health check |
| `/hooks/session-context` | POST | **Phase 6 HX.2** — Hook proxy for SessionStart pre-load (returns `{additionalContext}`) |
| `/hooks/session-persist` | POST | **Phase 6 HX.2** — Hook proxy for Stop auto-persist (session summary + decisions) |

See the skill file (`WHO-project/vds-skills/skills/vds-ai-memory-skill/SKILL.md`) for curl examples. The two `/hooks/*` endpoints are registered as `"type": "http"` hooks in `.claude/settings.local.json` alongside the corresponding `vds-cli memory-*` command hooks as a dual-path safety net (HTTP non-2xx is non-blocking in Claude Code, so the command path is the fallback).

## Practical Contract

- Read and write memory through the approved skill workflow.
- Store concise, durable decisions with supporting evidence.
