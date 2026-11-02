# vds-agent-core

Shared agent infrastructure for VDS orchestrators — LLM client Protocol, runtime profiles, skill policy, budget enforcement, bounded agent loop, and config models.

**Branch**: `wave1/agent-core-extraction` | **Status**: Branch-complete, pending merge to master

---

## Why This Package Exists

Before this extraction, `audit_orchestrator` was a fat monolith that owned all shared LLM/agent infrastructure. Any new orchestrator that needed LLM access, runtime profiles, or skill policy had two bad choices:

1. Re-implement everything from scratch (duplication)
2. Depend on `vds-audit-orchestrator` (heavyweight coupling — pulls in Confluence, Bitbucket, Excel, PDF, SonarQube orchestrators)

`vds_agent_core` is the third option: a pure, stateless platform library with no audit-domain knowledge.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        vds-scripts workspace                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    vds_agent_core                        │   │
│  │  (pure library — no CLI, no audit domain, no DB)         │   │
│  │                                                          │   │
│  │  config.py          LLMRuntimeConfig(BaseSettings)       │   │
│  │                     AgenticConfig, LangGraphConfig       │   │
│  │                     VDS_BASE_SETTINGS_CONFIG             │   │
│  │                                                          │   │
│  │  profiles.py        apply_runtime_profile()              │   │
│  │                     ConfigHooks Protocol                 │   │
│  │                                                          │   │
│  │  llm/               LLMClient Protocol                   │   │
│  │    provider.py      LiteLLMClient, HttpxDirectClient     │   │
│  │    cache.py         LLMResponseCache (injectable root)   │   │
│  │    budget.py        BudgetEnforcer (injectable path)     │   │
│  │    schemas.py       ProbeScore, parse_llm_response       │   │
│  │                                                          │   │
│  │  skills/            SkillPolicyEnforcer (stdlib only)    │   │
│  │    policy.py        SkillManager (injectable validator)  │   │
│  │    manager.py       SkillExecutor (CommandRunner Proto)  │   │
│  │    executor.py                                           │   │
│  │                                                          │   │
│  │  agents/            ToolRegistry Protocol                │   │
│  │    tools.py         LoopBehaviorHooks Protocol           │   │
│  │    hooks.py         BoundedAgentLoop                     │   │
│  │    loop.py                                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│           ▲                          ▲                          │
│           │ depends on               │ depends on              │
│  ┌────────┴──────────┐   ┌───────────┴──────────────────────┐   │
│  │ progress_report_  │   │       audit_orchestrator         │   │
│  │ orchestrator      │   │  (injects AuditLoopHooks,        │   │
│  │                   │   │   VDSCLIRunner, AuditConfigHooks) │   │
│  └───────────────────┘   └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Rules

- `vds_agent_core` depends only on `vds-cli-common` from the workspace
- `vds_agent_core` has **zero** module-level imports from `vds_audit_orchestrator`
- `audit_orchestrator` and `progress_report_orchestrator` both depend on `vds_agent_core`
- No circular dependencies — verified by `uv sync --all-packages`

---

## Package Layout

```
vds_agent_core/
├── pyproject.toml
└── src/vds_agent_core/
    ├── __init__.py
    ├── config.py          # Config models and enums
    ├── profiles.py        # Runtime profile activation
    ├── errors.py          # BaseAgentCoreError
    ├── llm/
    │   ├── __init__.py
    │   ├── provider.py    # LLMClient Protocol + LiteLLM/httpx backends
    │   ├── cache.py       # LLMResponseCache, AnalysisCache
    │   ├── budget.py      # BudgetEnforcer, BudgetScope, BudgetStatus
    │   └── schemas.py     # ProbeScore, parse_llm_response
    ├── skills/
    │   ├── __init__.py
    │   ├── policy.py      # SkillPolicyEnforcer (stdlib only, zero audit coupling)
    │   ├── manager.py     # SkillManager (ContentHashValidator Protocol)
    │   └── executor.py    # SkillExecutor (CommandRunner Protocol)
    └── agents/
        ├── __init__.py
        ├── tools.py       # ToolRegistry Protocol, ToolName type alias
        ├── hooks.py       # LoopBehaviorHooks Protocol, NoOpHooks
        └── loop.py        # BoundedAgentLoop
```

---

## Core Design Patterns

### 1. Protocol-Based Dependency Injection

All injectable seams use `typing.Protocol` — no abstract base classes, no inheritance required. Production and test doubles satisfy protocols structurally.

**ToolRegistry** — generic tool dispatch contract:
```python
# vds_agent_core/agents/tools.py
class ToolRegistry(Protocol):
    def get_tool(self, name: str) -> Callable[..., Any]: ...
    def list_tools(self) -> list[str]: ...
    def invoke(self, tool: str, payload: dict[str, Any]) -> ToolResponseEnvelope: ...
```

`audit_orchestrator` provides the concrete `AuditToolRegistry` that satisfies this protocol. The `BoundedAgentLoop` only knows about the protocol.

**LoopBehaviorHooks** — audit-specific branching extracted from the loop:
```python
# vds_agent_core/agents/hooks.py
class LoopBehaviorHooks(Protocol):
    def should_skip_first_step(self, tool: str, context: dict) -> bool: ...
    def is_evidence_recording(self, tool: str) -> bool: ...
    def is_context_query(self, tool: str) -> bool: ...
    def has_read_activity(self, trace: list) -> bool: ...
    def count_doc_reads(self, trace: list) -> int: ...
    def lookup_evidence_requirements(self, context: dict) -> dict: ...

class NoOpHooks:
    """Default — all hooks return neutral values. No audit coupling."""
    ...
```

**CommandRunner** — injectable subprocess execution:
```python
# vds_agent_core/skills/executor.py
class CommandRunner(Protocol):
    def run(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess: ...

class SkillExecutor:
    def __init__(self, runner: CommandRunner | None = None):
        self._runner = runner or SubprocessRunner()
```

**ConfigHooks** — injectable config get/set/reset for profile activation:
```python
# vds_agent_core/profiles.py
class ConfigHooks(Protocol):
    def get_config(self) -> Any: ...
    def set_config(self, cfg: Any) -> None: ...
    def reset_config(self) -> None: ...
```

---

### 2. LLM Provider Abstraction (LiteLLM-backed)

The `LLMClient` Protocol defines a generic async chat interface. The default implementation uses LiteLLM for unified provider support (OpenAI, Anthropic, Gemini, Ollama, and 100+ others). A minimal `HttpxDirectClient` is the fallback when LiteLLM is not installed.

```
LLMClient (Protocol)
    ├── LiteLLMClient       ← default when vds-agent-core[litellm] installed
    │     └── litellm.acompletion()
    └── HttpxDirectClient   ← fallback, OpenAI-compatible endpoints only
          └── httpx.AsyncClient.post("/chat/completions")
```

**LLMSettings** is the config-backed factory:
```python
from vds_agent_core.llm.provider import LLMSettings

# Loads from env vars and ~/.vds/.env automatically (BaseSettings)
settings = LLMSettings()

# Build client — auto-selects LiteLLM or httpx
client = settings.build_client()
response = await client.chat(messages, model=settings.select_model("standard"))

# Build pydantic-ai model (requires litellm extra)
model = settings.build_pydantic_ai_model(tier="complex")
```

Model strings use LiteLLM's `provider/model` format:
- `"openai/gpt-4o"`, `"openai/gpt-4o-mini"`
- `"anthropic/claude-opus-4-5"`, `"anthropic/claude-sonnet-4-5"`
- `"ollama/llama3.2"`, `"gemini/gemini-2.0-flash"`

---

### 3. Config Precedence (pydantic-settings)

`LLMRuntimeConfig` uses `pydantic-settings BaseSettings` to enforce a strict 5-level precedence:

```
Priority (highest → lowest):
1. CLI flags          → model_validate({...}) at call site
2. Env vars           → VDS_AGENT_CORE__API_KEY, VDS_AGENT_CORE__MODEL_STANDARD
3. Shared env file    → ~/.vds/.env  (dotenv_filtering="match_prefix" prevents pollution)
4. Defaults           → defined in LLMRuntimeConfig fields
```

**Two env_prefix styles coexist intentionally:**

| System | Prefix style | Example | Used for |
|--------|-------------|---------|----------|
| Profiles (`profiles.py`) | `VDS_AUDIT_` (single `_`) | `VDS_AUDIT_ACTIVE_PROFILE` | Shell env mutation via `os.environ` |
| Config models (`LLMRuntimeConfig`) | `VDS_AGENT_CORE__` (double `__`) | `VDS_AGENT_CORE__API_KEY` | pydantic-settings loading |

Do not normalize these — they are different systems.

**Subclass pattern** — prevents config drift between parent and child:
```python
# vds_agent_core/config.py
VDS_BASE_SETTINGS_CONFIG = dict(
    env_file="~/.vds/.env",
    env_file_encoding="utf-8",
    extra="ignore",
    dotenv_filtering="match_prefix",
    env_nested_delimiter="__",
)

class LLMRuntimeConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VDS_AGENT_CORE__",
        **VDS_BASE_SETTINGS_CONFIG,
    )

# In audit_orchestrator/config.py:
from vds_agent_core.config import VDS_BASE_SETTINGS_CONFIG

class LLMConfig(LLMRuntimeConfig):
    model_config = SettingsConfigDict(
        env_prefix="VDS_AUDIT__",
        **VDS_BASE_SETTINGS_CONFIG,  # carries forward all shared settings
    )
    # audit-specific fields added here
```

---

### 4. Composition over Inheritance for Agents

`vds_agent_core` does **not** provide a `BaseAgent` class. It provides composable primitives. Orchestrators build agents by composing these via pydantic-ai's `RunContext[DepsT]`:

```python
from dataclasses import dataclass
from vds_agent_core.llm.provider import LLMSettings
from vds_agent_core.llm.budget import BudgetEnforcer
from vds_agent_core.skills.policy import SkillPolicyEnforcer

@dataclass
class AgentDeps:
    llm_settings: LLMSettings
    budget: BudgetEnforcer
    skill_policy: SkillPolicyEnforcer
    # orchestrator-specific fields added here

# pydantic-ai agent using DepsT
from pydantic_ai import Agent

agent = Agent(
    model=deps.llm_settings.build_pydantic_ai_model("standard"),
    deps_type=AgentDeps,
)
```

This keeps agents stateless and avoids deep inheritance trees that couple orchestrators to audit internals.

---

### 5. BoundedAgentLoop with Injectable Hooks

The loop was extracted from `audit_orchestrator/engine/agent_loop.py` after refactoring 6 hardcoded audit-specific `ToolName` branches into the `LoopBehaviorHooks` Protocol.

```
BoundedAgentLoop.run(registry, context, config, hooks)
    │
    ├── hooks.should_skip_first_step(tool, ctx)   ← audit: GET_ROW_CONTEXT wiring
    ├── hooks.is_evidence_recording(tool)          ← audit: RECORD_EVIDENCE_REFS
    ├── hooks.is_context_query(tool)               ← audit: GET_ROW_CONTEXT
    ├── hooks.has_read_activity(trace)             ← audit: doc/code read detection
    ├── hooks.count_doc_reads(trace)               ← audit: docs intent utilization
    └── hooks.lookup_evidence_requirements(ctx)    ← audit: tool_first_planner wiring
```

`NoOpHooks` provides neutral defaults — the loop works standalone without any orchestrator coupling. `audit_orchestrator` provides `AuditLoopHooks` that restores the original branching logic.

---

## Runtime Profiles

Full profile mechanics extracted from `audit_orchestrator/runtime_profiles.py` (1521 lines). Supports injectable `env_prefix` and `ConfigHooks`:

```python
from vds_agent_core.profiles import apply_runtime_profile

# Default — backward-compatible with audit callers
apply_runtime_profile("omniroute-dlg1-gpt-openai")

# Custom env prefix for non-audit orchestrators
apply_runtime_profile("my-profile", env_prefix="VDS_PROGRESS_")

# Injectable config hooks (for orchestrators with their own config singletons)
class MyConfigHooks:
    def get_config(self): return my_config
    def set_config(self, cfg): set_my_config(cfg)
    def reset_config(self): reset_my_config()

apply_runtime_profile("my-profile", config_hooks=MyConfigHooks())
```

Profile YAML: `~/.vds/audit.profiles.yaml` — 11 profiles available (omniroute variants, dlg1/dlg2, gpt/claude/gemini).

---

## Skill Framework

```python
from vds_agent_core.skills.policy import SkillPolicyEnforcer, SkillPolicyMode
from vds_agent_core.skills.manager import SkillManager
from vds_agent_core.skills.executor import SkillExecutor, CommandRunner

# Policy — stdlib only, zero audit coupling
enforcer = SkillPolicyEnforcer(mode=SkillPolicyMode.ALLOWLIST)
decision = enforcer.gate(skill_name="my-skill", context={})

# Manager — injectable hash validator
class MyValidator:
    def validate(self, skill_item, *, raise_on_mismatch=False) -> bool: ...

manager = SkillManager(hash_validator=MyValidator())

# Executor — injectable runner
class MyRunner:
    def run(self, cmd: list[str], **kwargs) -> subprocess.CompletedProcess: ...

executor = SkillExecutor(runner=MyRunner())
result = executor.vds_cli_exec(["skills", "list"])
```

---

## Testing Conventions

### 1. Test agents without hitting a real LLM

```python
from pydantic_ai.models.test import TestModel

async def test_my_agent():
    with agent.override(model=TestModel()):
        result = await agent.run("test prompt", deps=my_deps)
    assert result.data == expected
```

### 2. Swap dependencies in tests

```python
from unittest.mock import MagicMock

async def test_with_mock_budget():
    mock_budget = MagicMock(spec=BudgetEnforcer)
    mock_budget.check.return_value = BudgetStatus.OK
    deps = AgentDeps(budget=mock_budget, ...)
    with agent.override(deps=deps):
        result = await agent.run("test", deps=deps)
```

### 3. Mock LiteLLM for unit tests

```python
async def test_litellm_client(mocker):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "hello"
    mocker.patch("litellm.acompletion", return_value=mock_response)

    client = LiteLLMClient()
    result = await client.chat([{"role": "user", "content": "hi"}], model="openai/gpt-4o")
    assert result == "hello"
```

### 4. Instantiate LLMSettings without env loading

```python
# Explicit values — bypasses env var loading
settings = LLMSettings(api_key="test-key", base_url="http://localhost:4000")

# Suppress dotenv loading entirely
settings = LLMSettings.model_validate({"api_key": "test"}, _env_file=None)
```

---

## Migration Guide

### Migrating from `vds-audit-orchestrator` to `vds-agent-core`

**Step 1** — Update `pyproject.toml`:
```toml
# Remove:
"vds-audit-orchestrator",

# Add:
"vds-agent-core",

# Add to [tool.uv.sources]:
vds-agent-core = { workspace = true }
```

**Step 2** — Update imports:
```python
# Before:
from vds_audit_orchestrator.runtime_profiles import apply_runtime_profile
from vds_audit_orchestrator.llm.budget import BudgetEnforcer
from vds_audit_orchestrator.agents.skill_policy import SkillPolicyEnforcer

# After:
from vds_agent_core.profiles import apply_runtime_profile
from vds_agent_core.llm.budget import BudgetEnforcer
from vds_agent_core.skills.policy import SkillPolicyEnforcer
```

**Step 3** — Sync:
```bash
uv sync --all-packages
```

### Backward-compat shims in `audit_orchestrator`

`audit_orchestrator` retains thin re-export shims so existing callers of `from vds_audit_orchestrator.llm.budget import BudgetEnforcer` continue to work without modification. These are permanent lightweight compat layers (11–29 lines each), not temporary scaffolding.

---

## Future Consumers

These packages are strong candidates for `vds_agent_core` adoption in future phases:

| Package | Likely need |
|---------|-------------|
| `multi_agent_orchestrator` | Agent loop + skill policy |
| `memory_orchestrator` | LLM config + profiles |
| `task_orchestrator` | Bounded agent loop |
| `spec_orchestrator` | LLM client |

---

## Spec Reference

- Spec: `.gpt-5.4/specs/vds-agent-core-extraction/` (requirements.md, design.md, tasks.md)
- Branch: `wave1/agent-core-extraction`
- Worktree: `WHO-project/worktrees/agent-core-w1`
- Tests: 349 passing, 86% coverage
