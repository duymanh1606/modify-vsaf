# VDS Evolution Loop: Deep Integration Analysis

> **Canonical Spec:** [.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md](../.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md)

## Executive Summary

The VDS Evolution Loop is a sophisticated automated system that evolves VDS skills based on real execution data. It integrates OpenSpace's MCP tools and SQLite store with a multi-gate quality pipeline, HMAC-verified verdicts, and optional auto-promotion.

**Key Statistics:**
- **26 skills** in canonical vds-skills/skills/
- **205 tests** passing
- **10 functional requirements** verified
- **4 non-functional requirements** satisfied
- **3-phase architecture**: OpenSpace → Gate Pipeline → Promotion

---

## 1. Integration Architecture

### 1.1 Layer Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Layer 0: Data Source                         │
│              OpenSpace SQLite (.openspace/openspace.db)            │
│                    execution_analyses + skill_judgments            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Layer 1: OpenSpace Integration                    │
│              OpenSpaceClient (openspace_integration.py)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ MCP Tools   │  │ Store Access │  │  Transport   │              │
│  │ execute_task│  │ load_candidate│  │ stdio/SSE/HTTP│            │
│  │ search_skill│  │ get_stats    │  │              │              │
│  │ fix_skill   │  │ mark_processed│ │              │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Layer 2: Gate Pipeline                          │
│                    router.py → Three-Gate Evaluation               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Gate 1     │  │   Gate 2     │  │   Gate 3     │              │
│  │ Structural  │  │ Behavioral   │  │ Semantic     │              │
│  │ - queue depth│ │ - regression │  │ - Claude     │              │
│  │ - budget cap│  │ - patterns   │  │ - ensemble   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Layer 3: Verdict & Sign                         │
│            Verdict + HMAC Binding + Promotion                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Verdict    │  │ hmac_binding │  │  promote.py │              │
│  │ - mechanism │  │ - SHA256 sig  │  │ - git branch│              │
│  │ - eligibility│ │ - key rotation│  │ - PR workflow│             │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Layer 4: Auto-Promote Daemon                       │
│                 auto_promote.py (optional, Phase 3+)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Poll Loop   │  │ Backoff      │  │ HMAC Verify │              │
│  │ - interval  │  │ - failures   │  │ - before    │              │
│  │ - pending   │  │ - max_backoff│  │   promote   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow Analysis

#### Candidate Loading Flow

```
OpenSpace Store
    │
    ▼ (SQL JOIN)
┌─────────────────────────────┐
│ execution_analyses         │
│ LEFT JOIN skill_judgments  │
│ WHERE evolution_suggestions │
│   IS NOT NULL             │
│   AND evolution_processed_│
│   at IS NULL              │
└─────────────────────────────┘
    │
    ▼ (Deserialization)
┌─────────────────────────────┐
│ ExecutionAnalysis Object   │
│ - task_id, timestamp      │
│ - tool_issues (JSON)      │
│ - skill_judgments (JSON)  │
│ - evolution_suggestions   │
│ - analyzed_by/at          │
└─────────────────────────────┘
```

#### Gate Pipeline Flow

```
ExecutionAnalysis
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Gate 1: Structural Check                                             │
│   ├─ Queue depth < threshold?                                      │
│   ├─ Budget cap: 120s max                                          │
│   └─ Result: GATE_1_PASS | GATE_1_QUEUE_FULL | GATE_1_BUDGET_EXCEEDED│
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼ (if pass)
┌─────────────────────────────────────────────────────────────────────┐
│ Gate 2: Behavioral Analysis                                         │
│   ├─ Regression test execution                                    │
│   ├─ Pattern analysis (import cycles, error patterns)             │
│   └─ Result: GATE_2_PASS | GATE_2_REJECTED                         │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼ (if pass)
┌─────────────────────────────────────────────────────────────────────┐
│ Gate 3: Semantic Quality (Optional)                                  │
│   ├─ Claude evaluation (if ANTHROPIC_API_KEY set)                   │
│   ├─ Ensemble judge (Phase 3+)                                     │
│   └─ Result: GATE_3_PASS | GATE_3_SKIPPED | GATE_3_REJECTED         │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
Verdict(eligible|ineligible)
```

### 1.3 Integration Points Matrix

| From Module | To Module | Integration Type | Purpose |
|-------------|-----------|------------------|---------|
| `openspace_integration.py` | `router.py` | Data | ExecutionAnalysis → gate evaluation |
| `router.py` | `models.py` | Model | Verdict creation |
| `router.py` | `verdict.py` | Persistence | JSON file write |
| `cli.py` | `auto_promote.py` | Command | Daemon invocation |
| `cli.py` | `ensemble_judge.py` | Command | Three-judge evaluation |
| `cli.py` | `hmac_binding.py` | Command | Sign/verify |
| `hmac_binding.py` | `promote.py` | Security | Verify before promote |
| `switch.py` | `router.py` | Control | Kill switch check |
| `switch.py` | `openspace_integration.py` | Store | SQLite connection |

---

## 2. MCP Transport Integration

### 2.1 Transport Selection Logic

```python
def _resolve_transport() -> str:
    """Resolve transport from env, default stdio."""
    transport = os.environ.get("OPENSPACE_TRANSPORT", "").strip().lower()
    if not transport:
        transport = "stdio"
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise OpenSpaceTransportError(...)
    return transport
```

### 2.2 Transport Endpoint Mapping

| Transport | Endpoint | Implementation |
|-----------|----------|----------------|
| `stdio` | subprocess | `openspace-mcp` CLI |
| `sse` | `/sse` | HTTP SSE stream |
| `streamable-http` | `/mcp` | HTTP POST/GET |

### 2.3 Transport Error Handling

```python
class OpenSpaceTransportError(Exception):
    """Raised when transport is invalid or unavailable."""
    
    def __init__(self, transport: str, message: str):
        self.transport = transport
        super().__init__(f"Transport {transport}: {message}")
```

---

## 3. Phase 3+ Infrastructure Deep Dive

### 3.1 Auto-Promote Daemon

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AutoPromoteDaemon                               │
├─────────────────────────────────────────────────────────────────────┤
│  Initialization                                                    │
│    ├─ AutoPromoteConfig(poll_interval, dry_run, ...)             │
│    └─ AutoPromoteDaemon(config)                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Run Loop                                                          │
│    while running:                                                 │
│      ├─ _get_pending_verdicts() → list[verdict_paths]             │
│      ├─ for each verdict:                                         │
│      │   ├─ sign_and_attach(verdict)                              │
│      │   ├─ verify_and_detach(signed_verdict)                     │
│      │   ├─ promote(verdict) if not dry_run                      │
│      │   └─ mark_evolution_processed()                           │
│      ├─ sleep(poll_interval * backoff)                            │
│      └─ handle signals (SIGTERM, SIGINT)                         │
├─────────────────────────────────────────────────────────────────────┤
│  Backoff Strategy                                                  │
│    ├─ failure_count++ on error                                    │
│    ├─ sleep = poll_interval * (backoff_multiplier ^ failure_count)│
│    └─ max backoff: 600s                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Three-Judge Ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EnsembleJudge                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Judges                                                            │
│    ├─ AnthropicJudge (Claude) - primary                           │
│    ├─ LocalModelJudge (Ollama/LM Studio) - optional               │
│    └─ ExternalJudge (API endpoint) - optional                      │
├─────────────────────────────────────────────────────────────────────┤
│  Strategies                                                        │
│    ├─ UNANIMOUS: All must agree                                   │
│    ├─ MAJORITY: >50% agreement                                    │
│    ├─ ANY_PASS: At least one approves                             │
│    └─ ADVISORY: Follow primary judge                               │
├─────────────────────────────────────────────────────────────────────┤
│  Output                                                           │
│    ├─ EnsembleResult(final_result, votes, explanation)           │
│    ├─ agreement_count, disagreement_count, abstain_count        │
│    └─ duration_ms per judge                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 HMAC Binding

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HMAC Binding                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Signature Creation                                                │
│    1. Compute payload_hash = SHA256(canonical_json(verdict))       │
│    2. Compute signature = HMAC-SHA256(key, payload_hash)         │
│    3. Attach HmacSignature {signature, payload_hash, algorithm, ...}│
├─────────────────────────────────────────────────────────────────────┤
│  Verification                                                      │
│    1. Extract HmacSignature from verdict._signature                │
│    2. Recompute payload_hash from current verdict content          │
│    3. Recompute expected_signature = HMAC-SHA256(key, payload_hash)│
│    4. Compare: signature == expected_signature                     │
├─────────────────────────────────────────────────────────────────────┤
│  Key Rotation                                                      │
│    ├─ Multiple keys supported (key-v1, key-v2, ...)               │
│    ├─ Sign with specific key_id                                    │
│    └─ Verify against any known key                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Skill Evolution Workflow

### 4.1 Full Evolution Cycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Evolution Cycle                                   │
├─────────────────────────────────────────────────────────────────────┤
│  1. OpenSpace executes task                                        │
│     └─ Records execution_analyses + skill_judgments              │
│                                                                  │
│  2. VDS Evolution Loop loads candidates                           │
│     └─ OpenSpaceClient.load_evolution_candidates()                │
│                                                                  │
│  3. Gate pipeline evaluates each candidate                        │
│     └─ route_sync(ExecutionAnalysis, KillSwitch)                  │
│                                                                  │
│  4. Verdict created with mechanism + eligibility                  │
│     └─ Written to verdict_root/verdicts/                          │
│                                                                  │
│  5. HMAC signature attached (optional, Phase 3+)                  │
│     └─ sign_and_attach(verdict)                                  │
│                                                                  │
│  6. Promotion (manual or auto)                                    │
│     ├─ Manual: vds-cli evolution promote VERDICT_ID                   │
│     └─ Auto: AutoPromoteDaemon polls and promotes                  │
│                                                                  │
│  7. Git workflow                                                  │
│     ├─ Create branch: evolution-promote/{skill-name}-{timestamp}  │
│     ├─ Cherry-pick changes                                        │
│     └─ Update skill in canonical vds-skills/                      │
│                                                                  │
│  8. Mark processed                                               │
│     └─ OpenSpaceClient.mark_evolution_processed(task_id)          │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Skill Directory Structure

```
WHO-project/
├── vds-skills/skills/          # Canonical skill directory (26 skills)
│   ├── research-skill/
│   │   └── SKILL.md
│   ├── code-review-graph-skill/
│   │   └── SKILL.md
│   └── ...
└── vds-scripts/               # Evolution loop implementation
    ├── .openspace/
    │   └── shadow/skills/    # Shadow copy for OpenSpace
    └── vds_evolution/        # Evolution loop modules
        ├── openspace_integration.py
        ├── router.py
        ├── gates/
        │   ├── structural.py
        │   ├── behavioral.py
        │   ├── semantic.py
        │   └── ensemble_judge.py
        ├── auto_promote.py
        ├── hmac_binding.py
        └── ...
```

---

## 5. Configuration Reference

### 5.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSPACE_WORKSPACE` | Project root | OpenSpace workspace directory |
| `OPENSPACE_HOST_SKILL_DIRS` | Canonical skills | Skill directories to monitor |
| `OPENSPACE_TRANSPORT` | `stdio` | MCP transport type |
| `OPENSPACE_AUTONOMOUS_ENABLED` | `false` | Enable auto-promote daemon |
| `OPENSPACE_MCP_HOST` | `localhost` | MCP server host |
| `OPENSPACE_MCP_PORT` | `8080` | MCP server port |
| `OPENSPACE_API_KEY` | (none) | Anthropic API key for Gate 3 |

### 5.2 Kill Switch States

| State | `OPENSPACE_AUTONOMOUS_ENABLED` | Behavior |
|-------|------------------------------|----------|
| Disabled | `false`, `0`, `no` | Evolution loop halted, human review required |
| Enabled | `true`, `1`, `yes` | Auto-promote daemon can run |

### 5.3 Budget Caps

| Gate | Budget Cap | Token Cap |
|------|----------|----------|
| Gate 1 | 120s | - |
| Gate 2 | 120s | - |
| Gate 3 | 60s | 10,000 tokens |

---

## 6. Testing Strategy

### 6.1 Test Categories

| Category | Test File | Count | Coverage |
|----------|-----------|-------|----------|
| Integration | `test_openspace_integration.py` | ~50 | MCP transport, store access |
| Unit | `test_router.py` | ~20 | Gate pipeline |
| Unit | `test_models.py` | ~30 | Data models |
| Unit | `test_reconciler.py` | ~15 | Registry reconciliation |
| Phase 3+ | `test_auto_promote.py` | 5 | Daemon logic |
| Phase 3+ | `test_ensemble_judge.py` | 7 | Three-judge ensemble |
| Phase 3+ | `test_hmac_binding.py` | 10 | HMAC signatures |

### 6.2 Running Tests

```bash
# All tests
./.venv/bin/python -m pytest vds_evolution/tests/ -v

# With coverage
./.venv/bin/python -m pytest --cov=vds_evolution vds_evolution/tests/

# Specific test
./.venv/bin/python -m pytest vds_evolution/tests/unit/test_router.py -v
```

---

## 7. Troubleshooting Matrix

| Problem | Symptom | Cause | Solution |
|---------|---------|------|----------|
| OpenSpace not found | `FileNotFoundError: openspace-mcp` | Not installed | `pip install openspace-ai` |
| No candidates | Queue depth = 0 | No execution analyses | Execute tasks via OpenSpace |
| Gate 1 fail | `QUEUE_FULL` | High queue depth | Wait or increase threshold |
| Gate 2 fail | `REGRESSION` | Test failure | Fix skill before re-evolve |
| Gate 3 fail | `LOW_QUALITY` | Claude rejection | Improve skill content |
| Signature invalid | `Invalid HMAC` | Tampered verdict | Re-verify or re-sign |
| Transport error | `OpenSpaceTransportError` | Invalid transport | Set valid transport |

---

## 8. Future Work

### 8.1 Planned Enhancements

1. **Ensemble Judge Enhancement**: Implement LocalModelJudge with Ollama integration
2. **Transport Testing**: End-to-end tests for SSE and streamable-http transports
3. **Metrics Dashboard**: Real-time evolution metrics visualization
4. **GitHub Integration**: Native PR creation and merge automation
5. **Slack Notifications**: Alert on verdict state changes

### 8.2 Research Opportunities

1. **Quality Prediction**: ML model to predict Gate 3 outcomes
2. **Skill Similarity**: Cluster similar skills for batch evolution
3. **Historical Analysis**: Track evolution patterns over time
4. **Cross-Skill Dependencies**: Detect and manage skill interdependencies

---

## 9. Appendix: Module API Reference

### OpenSpaceClient

```python
class OpenSpaceClient:
    def __init__(self, transport: str | None = None, ...)
    def ensure_initialized(self) -> None
    def close(self) -> None
    def execute_task(self, task: dict) -> dict
    def search_skills(self, query: str, ...) -> list[dict]
    def fix_skill(self, skill_id: str, ...) -> dict
    def upload_skill(self, skill_path: Path, ...) -> dict
    def load_evolution_candidates(self, ...) -> list[ExecutionAnalysis]
    def mark_evolution_processed(self, task_id: str) -> None
    def get_stats(self) -> OpenSpaceStats
```

### router.route_sync

```python
async def route_sync(
    execution_analysis: ExecutionAnalysis,
    kill_switch: KillSwitch,
    verdict_root: Path | None = None,
) -> Verdict:
    """Run three-gate pipeline on execution analysis."""
    ...
```

### AutoPromoteDaemon

```python
@dataclass
class AutoPromoteConfig:
    poll_interval: float = 60.0
    dry_run: bool = False
    max_failures: int = 3
    backoff_multiplier: float = 2.0
    max_backoff: float = 600.0
    verdict_root: Path | None = None

class AutoPromoteDaemon:
    def __init__(self, config: AutoPromoteConfig)
    async def run(self) -> None
    def stop(self) -> None
```

### EnsembleJudge

```python
@dataclass
class EnsembleConfig:
    strategy: EnsembleStrategy = EnsembleStrategy.ADVISORY
    anthropic_enabled: bool = True
    local_enabled: bool = False
    external_enabled: bool = False
    local_url: str = "http://localhost:11434"
    local_model: str = "llama3.2:latest"
    external_api_url: str | None = None

async def run_ensemble(
    skill_name: str,
    old_content: str,
    new_content: str,
    prompt: str,
    config: EnsembleConfig | None = None,
) -> EnsembleResult:
    ...
```