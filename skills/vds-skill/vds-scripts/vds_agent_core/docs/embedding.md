# VDS AI Memory: Pluggable Embedding (Phase 225)

> Operator + developer guide for the Phase 225 pluggable embedding SDK.
> Authoritative spec: `.gpt-5.4/specs/vds-ai-memory/` v20.6.1.
> Architectural decisions: ADR-98 (Ollama default on Metal GPU),
> ADR-99 (Generic provider registry), ADR-100 (3-layer cascade settings).

This guide answers operator-facing "How do I..." questions for the embedding
subsystem introduced in Phase 225. The embedding SDK lives in
`vds_agent_core.llm.embedding` and is the single canonical surface across all
orchestrators (memory, audit, progress_report, evolution).

---

## Quick start

The minimum operator config to switch the production embedding provider:

```bash
# ~/.vds/.env  (operator-private, NOT in this repo)
VDS_AGENT_CORE_EMBED__PROVIDER=ollama
VDS_AGENT_CORE_EMBED__BASE_URL=http://host.docker.internal:11434
VDS_AGENT_CORE_EMBED__MODEL_STANDARD=bge-m3
```

Three env vars are enough for the default Ollama path. Cloud providers add an
`API_KEY` (see playbook below).

---

## Call-site parallelism

The chat-LLM and embedding SDKs use the same idiom — `settings.build_client()`
+ `select_model("standard")`. The operator-facing knobs mirror each other:

| Concern | Chat LLM (`vds_agent_core.llm.provider`) | Embedding (`vds_agent_core.llm.embedding`) |
|---|---|---|
| Settings class | `LLMSettings` | `EmbeddingSettings` |
| Env prefix | `VDS_AGENT_CORE_LLM__` | `VDS_AGENT_CORE_EMBED__` |
| Model tier selector | `select_model("standard")` | `select_model("standard")` |
| Builder | `settings.build_client()` | `settings.build_client()` |
| Per-agent cascade | `LLMSettings.for_agent(...)` | `EmbeddingSettings.for_agent(...)` |
| Async lifetime | `await client.aclose()` | `await client.aclose()` |

```python
from vds_agent_core.llm.embedding import EmbeddingSettings
from vds_agent_core.llm.provider import LLMSettings

# Chat completions
llm = LLMSettings()
chat = llm.build_client()
reply = await chat.complete("hi", model=llm.select_model("standard"))

# Embeddings — identical idiom
emb = EmbeddingSettings()
client = emb.build_client()
vector = await client.embed("hi", model=emb.select_model("standard"))

await chat.aclose()
await client.aclose()
```

The two clients are independent; you can mix providers freely (e.g. chat via
OpenAI, embeddings via local Ollama).

---

## Provider switching matrix

The same four env vars switch every supported provider. Pick a row, paste it
into `~/.vds/.env`, restart memory orchestrator.

| Provider | `PROVIDER` | `BASE_URL` | `MODEL_STANDARD` | Default `DIMENSION` |
|---|---|---|---|---|
| Ollama (default, local) | `ollama` | `http://host.docker.internal:11434` | `bge-m3` | 1024 |
| OpenAI | `openai` | `https://api.openai.com/v1` | `text-embedding-3-small` | 1536 |
| OpenAI (matryoshka) | `openai` | `https://api.openai.com/v1` | `text-embedding-3-large` | 1024 or 3072 |
| Cohere | `cohere` | `https://api.cohere.ai/v1` | `embed-english-v3.0` | 1024 |
| Voyage | `voyage` | `https://api.voyageai.com/v1` | `voyage-3` | 1024 |
| Mistral | `mistral` | `https://api.mistral.ai/v1` | `mistral-embed` | 1024 |
| Jina | `jina` | `https://api.jina.ai/v1` | `jina-embeddings-v3` | 1024 |
| Local sentence-transformers | `local` | _(unused)_ | `BAAI/bge-m3` | 1024 |
| Hash (deterministic test) | `hash` | _(unused)_ | _(any)_ | 1024 |
| Self-hosted bge-m3 (Ollama) | `ollama` | `http://your-host:11434` | `bge-m3` | 1024 |

Cloud providers also need an API key — supplied via `..._EMBED__API_KEY` in
`~/.vds/.env`, or via the credential-reference indirection
(`${env:OPENAI_API_KEY}`) in a profile YAML (see Track-B section below).

---

## Dimension constraints

Qdrant collections are created with a fixed dimension at first deploy. After
that, dimension is immutable for the life of the collection. Phase 225
enforces three validator invariants in `EmbeddingRuntimeConfig` to catch
mismatches at startup, before any vector hits the index.

### The 1024 baseline

Ollama `bge-m3` (the default) emits 1024-dim vectors. Most non-OpenAI cloud
providers also default to 1024, so 1024 is the de-facto VDS baseline. Switching
to a different-dimensional model requires a Qdrant collection rebuild — see
"Switching to a different-dimensional cloud model" below.

### OpenAI matryoshka

`text-embedding-3-large` supports matryoshka truncation: the model is trained
so the first N dimensions of its 3072-dim output are usable as a smaller
embedding. So `dimension=1024` truncates the 3072-dim output and stays
compatible with the Qdrant 1024 baseline.

`text-embedding-3-small` does NOT support truncation; its native dim is 1536
and it must be used at 1536.

### The three validator invariants (FR-225.16)

1. **(a) Dim stability vs live Qdrant collection** — at startup, if
   `verify_dim_against_qdrant=true` (default), a probe checks the live
   collection dim and fails fast on mismatch.
2. **(b) OpenAI matryoshka safety** — `text-embedding-3-small` + dim != 1536
   raises `ConfigError`.
3. **(c) First-deploy guard** — the requested dim must be either the
   provider default (e.g. 1536 for openai) OR 1024 (the VDS baseline). Any
   other value fails fast.

```python
from vds_agent_core.llm.embedding import EmbeddingSettings, ConfigError

# This raises ConfigError: 3072 is neither openai default (1536) nor 1024
EmbeddingSettings(provider="openai", model_standard="text-embedding-3-large", dimension=3072)
```

---

## Cloud-failover playbook

Addresses R-225.1: Linux deploy targets without Ollama on the host.

When the local Ollama host is unavailable (e.g. the production Linux host
lacks Metal GPU or has Ollama disabled), switch the orchestrator to OpenAI:

1. Provision an OpenAI API key with embedding access.
2. Add to `~/.vds/.env`:
   ```bash
   VDS_AGENT_CORE_EMBED__PROVIDER=openai
   VDS_AGENT_CORE_EMBED__BASE_URL=https://api.openai.com/v1
   VDS_AGENT_CORE_EMBED__API_KEY=sk-...                 # provider key
   VDS_AGENT_CORE_EMBED__MODEL_STANDARD=text-embedding-3-large
   VDS_AGENT_CORE_EMBED__DIMENSION=1024                 # matryoshka → 1024
   ```
3. Restart memory orchestrator. The validator (b) accepts
   `text-embedding-3-large@1024` (matryoshka). The Qdrant collection at the
   1024 baseline is reusable as-is — no rebuild needed.
4. Confirm via `vds-cli doctor` — the embedding-health probe must pass.

If the deploy uses a different dim (e.g. native 1536 with `-small`), follow the
collection-rebuild playbook in the next section.

---

## Per-orchestrator subclass pattern

Some orchestrators (audit, progress_report, evolution) need their OWN
embedding settings — distinct env namespace, distinct override surface — so
they don't stomp on `VDS_AGENT_CORE_EMBED__*` shared keys.

The pattern (NFR-225.6 / NFR-225.7 / FR-225.9): subclass `EmbeddingSettings`
and override `model_config` with a custom env_prefix.

```python
from pydantic_settings import SettingsConfigDict
from vds_agent_core.config import VDS_BASE_SETTINGS_CONFIG
from vds_agent_core.llm.embedding import EmbeddingSettings

class AuditEmbeddingSettings(EmbeddingSettings):
    """Audit orchestrator embedding settings — own env namespace."""

    model_config = SettingsConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix="VDS_AUDIT_EMBED__",
        **VDS_BASE_SETTINGS_CONFIG,
    )
```

The subclass inherits all validator invariants, `build_client()`, the registry
lookup, and `for_agent()`. Operators read from `VDS_AUDIT_EMBED__*` instead of
the shared core prefix; that means the audit orchestrator can run a different
provider than memory_orchestrator on the same host.

---

## Per-agent provider config (Track-B)

Phase 225 Track-B introduces per-agent provider configuration via a 3-layer
cascade resolved by `EmbeddingSettings.for_agent(agent_id, ...)`. The same
mechanism applies to `LLMSettings.for_agent(...)`.

### The 3-layer cascade

```text
+--------------------------------------------------------+
| Layer 1: programmatic overrides   (highest precedence) |
|   passed via for_agent(overrides={...})                |
+--------------------------------------------------------+
| Layer 2: API settings (Path B)                         |
|   api_settings.embedding_settings dict                 |
+--------------------------------------------------------+
| Layer 3: env vars (Path A)                             |
|   VDS_AGENT_<AGENT_ID>_EMBED__*                        |
+--------------------------------------------------------+
| Layer 4: defaults                                      |
|   profile YAML / class defaults                        |
+--------------------------------------------------------+
```

### Three resolution paths

- **Path A (env)** — `VDS_AGENT_<SANITIZED_AGENT_ID>_EMBED__PROVIDER=ollama` etc.
  Sanitized = uppercase, non-alphanumeric → `_`.
- **Path B (API)** — `api_settings.embedding_settings` dict, fetched from
  Postgres `vds_ai_memory.api_settings` (or any `BaseSettings`-compatible
  source). Wins on conflict over Path A.
- **Path C (programmatic)** — `for_agent(overrides={"provider": "..."})`
  forced at call time, highest precedence.

### Credential-reference indirection

Profile YAML and API rows MUST NEVER carry raw API keys. Instead, use
`${env:VAR_NAME}` references that resolve at runtime against the process env:

```yaml
# vds_agent_core/profiles/agent_audit.yaml
embedding:
  provider: openai
  base_url: https://api.openai.com/v1
  api_key: ${env:OPENAI_API_KEY}     # resolved at load
  model_standard: text-embedding-3-large
  dimension: 1024
```

A boot-time allowlist (`VDS_AGENT_CORE__ALLOWED_ENV_REFS`) restricts which
env vars may be referenced; unlisted refs fail closed (FR-226.7).

---

## Switching to a different-dimensional cloud model

Use this playbook ONLY when changing the Qdrant collection dimension is
unavoidable (e.g. you must use OpenAI native 1536 dim).

1. Stop the memory orchestrator: `docker compose stop memory_orchestrator`.
2. Drop the existing Qdrant collection:
   ```bash
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli memory \
       admin drop-collection --collection vds_memories --confirm
   ```
3. Update `~/.vds/.env` to the new model + dim:
   ```bash
   VDS_AGENT_CORE_EMBED__PROVIDER=openai
   VDS_AGENT_CORE_EMBED__MODEL_STANDARD=text-embedding-3-small
   VDS_AGENT_CORE_EMBED__DIMENSION=1536
   ```
4. Recreate the collection at the new dim (memory orchestrator does this
   automatically on first boot if the collection is absent).
5. Re-embed all memories from the source rows in Postgres:
   ```bash
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli memory \
       admin reindex --batch-size 100
   ```
6. Validate with a sanity query and `vds-cli doctor`.

This is destructive — every cached vector is recomputed. Plan for the
re-embedding cost (token cost * memory count for cloud providers).

---

## Disabling dimension verification

`EMBEDDING_VERIFY_DIM_AGAINST_QDRANT=false` skips invariant (a). This is
**unsupported in production**. Switching embedding models without dim
verification can silently corrupt the Qdrant collection (writes succeed but
queries return garbage cosine scores).

When set to false, the SDK emits a one-shot startup WARN
(`dimension_verification_disabled`). NFR-225.11: **Phase 228 DELIVERED 2026-05-03**
— `vds-cli doctor` now surfaces this as a WARN row via `_doctor_check_embedding()`,
and `/api/v1/health/full` exposes embedding sub-layer with reachability probe.
(was documentation-promised; now implementation-delivered).

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor
# WARN: VDS_AGENT_CORE_EMBED__VERIFY_DIM_AGAINST_QDRANT=false
#       Dimension verification is disabled — see docs/embedding.md.
```

---

## Adding a new provider (3-step recipe)

NFR-225.9 drop-in extensibility. To wire in (say) Cohere v4 as a distinct
provider without modifying core source files:

```python
# 1. Implement a client (or reuse OpenAIEmbeddingClient if API-shape matches)
from vds_agent_core.llm.embedding import (
    EMBEDDING_PROVIDERS, PROVIDER_DEFAULTS, OpenAIEmbeddingClient,
)

class CohereV4EmbeddingClient(OpenAIEmbeddingClient):
    @classmethod
    def from_settings(cls, config):
        return cls(config, provider_name="cohere-v4")

# 2. Register in EMBEDDING_PROVIDERS
EMBEDDING_PROVIDERS["cohere-v4"] = CohereV4EmbeddingClient.from_settings

# 3. Add provider defaults
PROVIDER_DEFAULTS["cohere-v4"] = {
    "model": "embed-english-v4.0",
    "dimension": 1024,
    "base_url": "https://api.cohere.ai/v2",
}
```

After registration, set `VDS_AGENT_CORE_EMBED__PROVIDER=cohere-v4` in
`~/.vds/.env`. Three lines of code change in your project; no patches to
`vds_agent_core` source needed.

For collision protection, prefer `register_provider("cohere-v4", factory)`
which raises `ConfigError` on name collisions unless `force=True`.

---

## Recommended `~/.vds/.env`

The canonical Phase 225 env block (operator-private file, NOT in this repo).
Legacy `EMBEDDING_*` env vars continue to work for one cycle for back-compat;
they should be migrated to the canonical names below.

```bash
# Phase 225 — canonical embedding env vars
VDS_AGENT_CORE_EMBED__PROVIDER=ollama
VDS_AGENT_CORE_EMBED__BASE_URL=http://host.docker.internal:11434
VDS_AGENT_CORE_EMBED__MODEL_STANDARD=bge-m3
VDS_AGENT_CORE_EMBED__MODEL_SIMPLE=bge-m3
VDS_AGENT_CORE_EMBED__MODEL_COMPLEX=bge-m3
VDS_AGENT_CORE_EMBED__DIMENSION=1024
VDS_AGENT_CORE_EMBED__TIMEOUT_SECONDS=30
VDS_AGENT_CORE_EMBED__FAIL_OPEN=false
VDS_AGENT_CORE_EMBED__VERIFY_DIM_AGAINST_QDRANT=true

# Cloud-failover (uncomment to activate)
# VDS_AGENT_CORE_EMBED__PROVIDER=openai
# VDS_AGENT_CORE_EMBED__BASE_URL=https://api.openai.com/v1
# VDS_AGENT_CORE_EMBED__API_KEY=sk-...
# VDS_AGENT_CORE_EMBED__MODEL_STANDARD=text-embedding-3-large
# VDS_AGENT_CORE_EMBED__DIMENSION=1024

# Per-agent override example (audit orchestrator uses its own prefix subclass)
# VDS_AUDIT_EMBED__PROVIDER=ollama
# VDS_AUDIT_EMBED__MODEL_STANDARD=bge-m3
```

Legacy back-compat (deprecated, removed next cycle):

```bash
# Old names — still honored for one cycle
EMBEDDING_PROVIDER=ollama                 # → VDS_AGENT_CORE_EMBED__PROVIDER
EMBEDDING_BASE_URL=...                    # → VDS_AGENT_CORE_EMBED__BASE_URL
EMBEDDING_MODEL=bge-m3                    # → ..._MODEL_STANDARD
```

---

## Structured Log Events (W7+W8 Deferred Sections)

The embedding SDK emits structured log events via `structlog` for operator observability.
All events are routable via `VDS_AGENT_CORE__LOG_RESOLUTION=true` (one log per agent_id + kind).

### Health Check & Fallback Events

| Event Key | Severity | Trigger | Action |
|-----------|----------|---------|--------|
| `embedding_health_check_failed_fatal` | ERROR | Health-check probe timeout or permanent service unreachable | Startup fails; operator must resolve provider connectivity or change config |
| `embedding_health_check_failed_fallback_to_hash` | WARN | Health-check fails but `FAIL_OPEN=true` | Falls back to deterministic hash embeddings; production not recommended |
| `dimension_verification_disabled` | WARN | `VERIFY_DIM_AGAINST_QDRANT=false` at startup | Operator MUST ensure new vectors match collection dimension (silent corruption risk) |

### Provider & Model Resolution Events

| Event Key | Severity | Trigger | Action |
|-----------|----------|---------|--------|
| `provider_model_mismatch` | WARN | `PROVIDER=X` set + `MODEL_STANDARD=Y/model` parses to different provider | Explicit provider takes precedence; WARN clarifies the override |
| `for_agent_resolved` | INFO | Per-agent cascading resolution completes (Layer 1/2/3 precedence applied) | Logs winner (env / API / programmatic) for audit trail |
| `for_agent_path_conflict` | WARN | Layer B (API) differs from Layer A (env) at resolution time | Both values logged; Layer B wins; signals operator may have stale Redis state |
| `profile_embedding_resolved` | INFO | Subclass (e.g., `AuditEmbeddingSettings`) loads YAML profile with credential-ref indirection | `${env:VAR}` references logged after substitution (API key redacted) |

### HTTP & Provider-Specific Events

| Event Key | Severity | Trigger | Action |
|-----------|----------|---------|--------|
| `ollama_embed_http_error` | ERROR | HTTP error from Ollama `/api/embed` endpoint | Operator checks Ollama container logs + network connectivity |
| `ollama_embed_request_error` | ERROR | Ollama request-body validation or timeout | Operator reviews model name + dimension in Ollama config |
| `ollama_embed_batch_http_error` | ERROR | HTTP error from Ollama batch `/api/embed` (multi-doc) | Same as single-doc; batch retried individually |
| `ollama_embed_batch_request_error` | ERROR | Request validation on batch (one doc fails, others may pass) | Batch partially replayed via DLQ; operator reviews per-doc payloads |
| `openai_compat_embed_http_error` | ERROR | HTTP error from OpenAI-compatible provider (Cohere, Voyage, Mistral, Jina) | Operator checks provider status page + API quota |
| `openai_compat_embed_request_error` | ERROR | Request-body validation or timeout on OpenAI-compat provider | Operator reviews model name + dimension constraints for provider |

---

## Mem0 Cross-Service Embedding Architecture (W8 Deferred)

**CRITICAL OPERATIONAL NOTE**: Phase 225 embedding introduces TWO independent embedding paths. Operators must configure BOTH when switching providers.

### Path 1: vds_agent_core Embedding (New, Phase 225)

- **Config namespace**: `VDS_AGENT_CORE_EMBED__*`
- **Entry point**: `vds_agent_core.llm.embedding.EmbeddingSettings.build_client()`
- **Orchestrators using this path**: memory_orchestrator, audit_orchestrator, progress_report_orchestrator, evolution_orchestrator, multi_agent_orchestrator
- **Control surface**: All 9 providers (Ollama, OpenAI, Cohere, Voyage, Mistral, Jina, LiteLLM, local, hash)

### Path 2: Mem0 Self-Hosted Embedder (Legacy, Coexists)

- **Config namespace**: `MEM0_*` (separate from `VDS_AGENT_CORE_EMBED__*`)
- **Entry point**: `mem0_orchestrator/services/embedding_adapter.py:231` (Qdrant local embedder or cloud if configured)
- **Behavior**: Mem0 cloud manages embeddings server-side; self-hosted Mem0 uses its own LLM provider config
- **When active**: Only when `mem0_orchestrator` is the active memory backend OR mem0 cloud mode is enabled

### Provider Switching Checklist

When operators change the embedding provider, they MUST update:

1. **vds_agent_core path** (ALL orchestrators using memory):
   ```bash
   # Edit ~/.vds/.env
   VDS_AGENT_CORE_EMBED__PROVIDER=openai
   VDS_AGENT_CORE_EMBED__BASE_URL=https://api.openai.com/v1
   VDS_AGENT_CORE_EMBED__API_KEY=sk-...
   VDS_AGENT_CORE_EMBED__MODEL_STANDARD=text-embedding-3-large
   VDS_AGENT_CORE_EMBED__DIMENSION=1024
   ```

2. **Mem0 self-hosted path** (if `memory_orchestrator` uses mem0 local embedder):
   ```bash
   # Edit ~/.vds/.env or mem0_orchestrator/.env
   MEM0_EMBEDDING_PROVIDER=ollama  # or openai, cohere, etc.
   MEM0_EMBEDDING_BASE_URL=...
   MEM0_EMBEDDING_MODEL=...
   # See mem0_orchestrator/config.py for full MEM0_* namespace
   ```

3. **Mem0 cloud** (if using mem0 cloud mode):
   - No local config needed; mem0 cloud handles embeddings server-side
   - Verify `MEM0_CONFIG_API_KEY` points to your cloud account

**Consequence of missing either update**: Silent dimension mismatch or failed embedding calls. Always verify both paths after provider changes via `vds-cli doctor` (checks vds_agent_core path) + mem0 health probes (checks mem0 path).

---

## See also

- ADR-98 (Ollama default on Metal GPU) — `.gpt-5.4/specs/vds-ai-memory/design.md`
- ADR-99 (Generic provider registry) — same file
- ADR-100 (3-layer cascade settings) — same file
- FR-225.* (Track-A SDK foundation) — `.gpt-5.4/specs/vds-ai-memory/requirements.md`
- FR-226.* (Track-B per-agent cascade) — same file (audit-trail prefix preserved)
- Source: `vds_agent_core/src/vds_agent_core/llm/embedding.py`
- Tests: `vds_agent_core/tests/unit/llm/`
- Memory orchestrator integration: `memory_orchestrator/src/vds_memory_orchestrator/service/services/embedding_service.py`
