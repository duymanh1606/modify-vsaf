<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# Using VDS AI Memory from External Agent CLIs

This guide covers how external agent runtimes — Codex, OpenCode, and Qwen — can
read from and write to VDS AI Memory using the `vds-cli memory` subcommand.

## Prerequisites

The VDS AI Memory API must be running and reachable. Start the active runtime stack if needed:

```bash
cd WHO-project/vds-scripts/memory_orchestrator
docker compose --profile dev --profile mem0 up -d
```

This starts the active memory runtime stack from `memory_orchestrator/`.

> `WHO-project/vds-ai-memory/` is historical/archive-only and should not be used for current startup or runtime guidance.

## Runtime Environment Resolution

| Variable | Purpose | Default |
|---|---|---|
| `VDS_MEMORY_API_URL` | Explicit base URL of the memory API | If unset: `http://localhost:${API_PORT:-8000}` |

`vds-cli memory` loads `~/.vds/.env` automatically. Set an explicit URL only
when the runtime is on a non-default host/port:

```bash
export VDS_MEMORY_API_URL="http://localhost:8010"
```

> **Note:** The memory API does not require an API key in its default
> local-dev configuration. For current runtime/deployment guidance, prefer
> `WHO-project/vds-scripts/memory_orchestrator/README.md` and the canonical spec
> triplet under `.gpt-5.4/specs/vds-ai-memory/`.

## Storing a Decision

```bash
# Store a decision scoped to a project using tags
vds-cli memory store "decided to use Kafka for async event dispatch" \
  --category business-logic --importance high \
  --tags PAR,architecture,kafka

# Minimal store
vds-cli memory store "merchant-billing uses Spring Boot 3.2"
```

## Searching Memories

```bash
# Semantic search across all memories
vds-cli memory search "kafka event dispatch" --limit 5

# Filter by category
vds-cli memory search "auth patterns" --category business-logic --limit 10
```

## Usage from Each Agent CLI

All agent CLIs that can run shell commands can call `vds-cli` directly.
Inherit `~/.vds/.env` via the shell session that launches the agent. Set
`VDS_MEMORY_API_URL` only if you need an explicit override.

### Codex

```bash
codex exec --skip-git-repo-check -m gpt-5.4 "your prompt here"
```

Within the Codex session, the agent runs shell commands:

```bash
vds-cli memory store "Codex discovered that merchant-report uses JPA auditing"
vds-cli memory search "merchant-report auditing"
```

### OpenCode (Z.AI / GLM)

```bash
opencode run -m "zai-coding-plan/glm-5.1" "your prompt here"
```

The OpenCode agent shell-executes:

```bash
vds-cli memory store "OpenCode: PAR project checklist page is 88722450" \
  --category business-logic --importance high
vds-cli memory search "PAR checklist"
```

### Qwen

```bash
qwen -m qwen3-coder "your prompt here"
```

Qwen agents call:

```bash
vds-cli memory store "Qwen: insurance hexagonal boundary violations found in 3 repos"
vds-cli memory search "hexagonal boundary violations"
```

## Project Scoping via Tags

To keep memories scoped to a project, include the project key as a tag:

```bash
# Store scoped to project PAR
vds-cli memory store "billing service auth pattern confirmed" \
  --tags PAR,billing,auth

# Search within PAR context (post-filter by tags)
vds-cli memory search "billing auth" --limit 10
```

## Health Check

Before a long agent run, verify the memory service is reachable:

```bash
vds-cli memory health
```

Expected output: `{"status": "healthy", ...}`

## Practical Rules

- Store decisions immediately after they are made — do not batch at end of session.
- Include project key, service name, and date context in the content string.
- Keep content under 500 characters per memory for searchability.
- Do not store secrets, credentials, or personal data.
- Use `--importance high` for irreversible architectural decisions.

---

## Python SDK: `vds_memory_client` (VAMI-003)

Since VAMI-003, a standalone Python package `vds_memory_client` provides
programmatic access to VDS AI Memory for any Python agent or script — no
`vds-cli` installation required.

### Installing

```bash
# From the VDS monorepo (worktree or vds-scripts)
uv run --project WHO-project/vds-scripts/vds_memory_client python3 -c "import vds_memory_client"

# Or add as a dependency in your pyproject.toml
[tool.uv.sources]
vds_memory_client = { path = "../../vds_memory_client" }
```

### Basic Usage

```python
import asyncio
from vds_memory_client import VDSMemoryClient

async def main():
    import os

    base_url = os.getenv("VDS_MEMORY_API_URL") or f"http://localhost:{os.getenv('API_PORT', '8000')}"
    client = VDSMemoryClient(base_url=base_url, timeout=10.0)

    # Health check
    status = await client.health()
    print(status)  # {"status": "healthy", ...}

    # Store a decision
    result = await client.store(
        content="Decided to use Kafka for async event dispatch",
        category="business-logic",
        importance="high",
        tags=["PAR", "architecture"],
    )
    print(result["memory_id"])

    # Search
    results = await client.search(query="kafka event dispatch", limit=5)
    for m in results["results"]:
        print(f"[{m['category']}] {m['content'][:80]}")

asyncio.run(main())
```

### Session State Caching

`VDSMemoryClient` caches the health-check result in `~/.vds/.memory-session.json`
using an atomic write (`tempfile.mkstemp` + `os.replace`). This file is:
- **Not** in iCloud (lives in `~/.vds/`, not `~/Library/Mobile Documents/`)
- Safe for concurrent writes from multiple agent processes
- Valid for 60 minutes by default before the client re-checks health

### iCloud Path Compatibility

`vds_memory_client` runs correctly from iCloud-backed project paths
(e.g. `~/Library/Mobile Documents/com~apple~CloudDocs/...`). The key properties
that make this safe:

| Concern | How it is handled |
|---------|-------------------|
| Spaces in path arguments | Wrap variables in double-quotes: `"$CLAUDE_PROJECT_DIR/..."` |
| Atomic session writes | Written to `~/.vds/` (outside iCloud), using `os.replace()` |
| `uv run --project <path>` | Path passed as a quoted argument; uv handles spaces correctly |

### Hook Integration (now via Claude Code plugins)

**Status (2026-04-24)**: The `vds_hooks` Python package was retired by
`vds-hooks-claude-plugin-packaging` Phase 6. Hook integration with VDS AI Memory
now lives entirely in the **Claude Code plugin format**:

- `WHO-project/vds-skills/plugins/vds-hooks-core/` — generic hooks
- `WHO-project/vds-skills/plugins/vds-hooks-extras/` — VDS-specific hooks (memory, audit, agent context)

Plugins are installed via `/plugin marketplace add` + `/plugin install` and fire
automatically on Claude Code events (`SessionStart`, `Stop`, `SessionEnd`,
`UserPromptSubmit`, etc.) — no manual `vds-cli` invocation required.

For the HTTP proxy endpoints, see
`WHO-project/vds-scripts/memory_orchestrator/` — those endpoints are
independent of the Python-package retirement and continue to serve
`POST /api/v1/hooks/session-context` and `POST /api/v1/hooks/session-persist`.

For SDK-level memory access from your own scripts, use `vds_memory_client`
(see "Python SDK" section above). For the canonical hook semantics + dual-path
safety-net design, see the spec at
`.gpt-5.4/specs/vds-hooks-claude-plugin-packaging/` (Phase 6 archive +
predecessor `hooks.RETIRED-2026-05-02/`).

### Environment Variables

| Variable | Effect | Default |
|----------|--------|---------|
| `VDS_MEMORY_API_URL` | API base URL | If unset: `http://localhost:${API_PORT:-8000}` |
| `VDS_HOOK_SESSION_MEMORY` | Set to `"0"` to disable session context hook | `"1"` |
| `VDS_HOOK_MEMORY_PERSIST` | Set to `"0"` to disable persist-stop hook | `"1"` |
| `VDS_HOOK_MEMORY_DECISIONS` | Set to `"0"` to skip decision extraction | `"1"` |
