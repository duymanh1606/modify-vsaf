# vds-agent-core Changelog

## 0.10.0 — Phase 10 dead-code purge (2026-05-02)

### Removed (FR-10.1..10.10, FR-10.19..10.21)

13 dead subpackages deleted (zero external production consumers, confirmed by
exhaustive grep across the full workspace):

| Subpackage | FR | Deleted symbols |
|---|---|---|
| `pipeline/` | FR-10.1 | `Pipeline`, `PipelineResult`, `PipelineStep` |
| `teams/` | FR-10.2 | `TeamCoordinator`, `TeamConfig`, `TeamResult`, `TeamRole`, `TeamTask`, `TeamTaskStatus`, `AggregationStrategy`, `DistributionStrategy` |
| `bridge/` | FR-10.3 | `LangGraphBridge`, `BridgeConfig` |
| `bus/` | FR-10.4 | `MessageBus`, `Message`, `Topic` |
| `factory/` | FR-10.5 | `AgentFactory`, `AgentConfig`, `create_agent` |
| `cost/` | FR-10.6 | `CostOptimizer`, `CostProfile`, `ModelTier`, `budget_units` |
| `output/` | FR-10.7 | `OutputValidator`, `OutputValidationError`, `FormatConstraint` |
| `tools/` | FR-10.8 | `DependencyGraph`, `CommunityDetector`, `GraphNode`, `GraphEdge`, `detect_cycles`, `find_communities`, `topological_sort`, `traverse_bfs`, `traverse_dfs` |
| `state/` | FR-10.9 | `AgentState`, `StateBackend`, `StateReducer`, `CheckpointManager`, `InMemoryStateBackend`, `FileSystemStateBackend` |
| `skill_runtime/` | FR-10.10 | `SkillRuntime`, `SkillManifest`, `execute_skill`, `load_manifest` |
| `resilience/` | FR-10.19 | `CircuitBreaker`, `CircuitBreakerConfig`, `CircuitBreakerOpenError`, `CircuitState`, `RateLimiter`, `RateLimitConfig`, `RateLimitExceededError`, `RetryPolicy`, `RetryConfig`, `RetryExhaustedError`, `ResilientConfig`, `TimeoutGuard`, `TimeoutConfig`, `TimeoutExceededError`, `TokenBucket`, `async_retry`, `sync_retry`, `resilient`, `is_retryable_error`, `parse_rate_string` |
| `memory/` | FR-10.20 | `MemoryClient`, `MemoryBackend`, `MemoryLayer`, `MemoryRecord`, `MemoryResult`, `MemorySearchResult` |
| `errors.py` | FR-10.21 | `VDSError`, `ConfigurationError`, `LLMError` (module-level) |

### Surviving surface (active, not removed)

- `observability/` — `AgentTracer`, `BudgetEvent`, `BudgetEventType`, `TokenUsage`, `TraceSpanType`, `trace_audit`, `trace_llm_call`, `trace_span`
- `llm/` — LLM provider abstraction
- `agents/` — `LoopBehaviorHooks`, `NoOpHooks`, agent loop
- `runtime/` — agent runtime contracts
- `security/` — credential sanitization
- `skills/` — skill execution machinery
- `workflows/` — LangGraph runner
- `profiles.py` — `DEFAULT_RUNTIME_PROFILES_FILE`, `CodexCredentialResolver`
- `config.py` — shared config models
