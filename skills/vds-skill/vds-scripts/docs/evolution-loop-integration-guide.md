# VDS Evolution Loop: Integration Guide

> **Canonical Spec:** [.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md](../.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md)

## Overview

The VDS Evolution Loop is an automated system for evolving VDS skills based on real execution data from OpenSpace. It integrates with OpenSpace's MCP tools and SQLite store to:

1. **Load** evolution candidates from execution analyses
2. **Evaluate** them through a three-gate pipeline
3. **Sign** verdicts with HMAC for integrity
4. **Promote** approved skills automatically or manually

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Evolution Loop                                │
├─────────────────────────────────────────────────────────────────────┤
│  OpenSpace Store (.openspace/openspace.db)                          │
│    ├── execution_analyses (candidates)                              │
│    ├── skill_judgments                                              │
│    └── evolution_suggestions                                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OpenSpaceClient (openspace_integration.py)                         │
│    ├── MCP tools: execute_task, search_skills, fix_skill            │
│    ├── Transport: stdio, SSE, streamable-http                       │
│    └── Store access: load_evolution_candidates, stats               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Router (router.py) → Three-Gate Pipeline                            │
│    ├── Gate 1 (structural): Queue depth, budget check              │
│    ├── Gate 2 (behavioral): Regression test, pattern analysis    │
│    └── Gate 3 (semantic): Claude quality assessment                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Verdict (models.py, router.py)                                      │
│    ├── mechanism: "fix" | "derived" | "captured"                    │
│    ├── final_eligibility: "eligible" | "ineligible"                │
│    └── state: pending → promoted | rejected | needs-review         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 3+ Infrastructure                                             │
│    ├── HMAC Binding: Verdict integrity signatures                  │
│    ├── Ensemble Judge: Multi-judge consensus                      │
│    └── Auto-Promote: Daemon for automatic promotion               │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Inventory

### Core Modules

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `openspace_integration.py` | MCP client & store access | `OpenSpaceClient`, `ExecutionAnalysis`, `OpenSpaceStats` |
| `router.py` | Gate pipeline orchestration | `route()`, `route_sync()` |
| `models.py` | Data models | `Verdict`, `ExecutionAnalysis`, `VerdictSchema` |
| `switch.py` | Kill switch & store | `KillSwitch`, `get_store()` |

### Gate Modules

| Module | Gate | Purpose |
|--------|------|---------|
| `gates/structural.py` | Gate 1 | Queue depth, budget cap check |
| `gates/behavioral.py` | Gate 2 | Regression test, pattern analysis |
| `gates/semantic.py` | Gate 3 | Claude quality assessment |
| `gates/ensemble_judge.py` | Ensemble | Three-judge consensus |

### Phase 3+ Modules

| Module | Purpose |
|--------|---------|
| `auto_promote.py` | Automatic verdict promotion daemon |
| `hmac_binding.py` | HMAC-SHA256 verdict signatures |
| `gates/ensemble_judge.py` | Multi-judge evaluation |

### Supporting Modules

| Module | Purpose |
|--------|---------|
| `promote.py` | Git branch creation & PR workflow |
| `verdict.py` | Verdict persistence |
| `reconciler.py` | Skill registry reconciliation |
| `shadow.py` | Canonical-to-shadow sync |
| `audit.py` | Audit log writer |

## Data Flow

### 1. Candidate Loading

```python
from vds_evolution.openspace_integration import OpenSpaceClient

client = OpenSpaceClient()
candidates = client.load_evolution_candidates(limit=50)
```

**SQL:**
```sql
SELECT ea.*, sj.skill_id, sj.skill_applied, sj.note
FROM execution_analyses ea
LEFT JOIN skill_judgments sj ON ea.task_id = sj.task_id
WHERE ea.evolution_suggestions IS NOT NULL
  AND ea.evolution_processed_at IS NULL
ORDER BY ea.timestamp DESC
LIMIT :limit
```

### 2. Gate Pipeline

```python
from vds_evolution.router import route_sync
from vds_evolution.models import ExecutionAnalysis

# Create execution analysis from candidate
analysis = ExecutionAnalysis(
    task_id=candidate.task_id,
    timestamp=candidate.timestamp,
    evolution_suggestions=candidate.evolution_suggestions,
    ...
)

# Run through gates
verdict = await route_sync(analysis, kill_switch)
```

**Flow:**
```
Candidate → Gate1 (structural)
              ├─ Pass: → Gate2 (behavioral)
              │          ├─ Pass: → Gate3 (semantic)
              │          │          ├─ Pass: eligible
              │          │          └─ Fail: ineligible
              │          └─ Fail: ineligible
              └─ Fail: ineligible
```

### 3. Verdict Signing (Phase 3+)

```python
from vds_evolution.hmac_binding import sign_and_attach, verify_and_detach

# Sign verdict before promotion
signed_verdict = sign_and_attach(verdict.to_dict())

# Verify before promotion
verified = verify_and_detach(signed_verdict)
if not verified.valid:
    raise ValueError(f"Invalid signature: {verified.error}")
```

### 4. Auto-Promote

```bash
# Start daemon
vds-cli evolution auto-promote --poll-interval 60 --dry-run

# Or in Python
from vds_evolution.auto_promote import AutoPromoteDaemon, AutoPromoteConfig

config = AutoPromoteConfig(poll_interval=60.0, dry_run=True)
daemon = AutoPromoteDaemon(config)
await daemon.run()
```

### 5. Ensemble Judge

```bash
# Run three-judge evaluation
vds-cli evolution ensemble-judge path/to/SKILL.md --strategy unanimous
```

**Strategies:**
- `unanimous`: All judges must agree
- `majority`: 2/3 agreement
- `any_pass`: At least one approves
- `advisory`: Follow primary judge

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENSPACE_WORKSPACE` | Project root | OpenSpace workspace directory |
| `OPENSPACE_HOST_SKILL_DIRS` | Canonical skills | Skill directories to monitor |
| `OPENSPACE_TRANSPORT` | `stdio` | MCP transport (stdio/sse/streamable-http) |
| `OPENSPACE_AUTONOMOUS_ENABLED` | `false` | Enable auto-promote daemon |
| `OPENSPACE_MCP_HOST` | `localhost` | MCP server host |
| `OPENSPACE_MCP_PORT` | `8080` | MCP server port |

### Kill Switch

```python
from vds_evolution.switch import KillSwitch

kill_switch = KillSwitch()
if not kill_switch.is_enabled():
    print("Evolution loop disabled by kill switch")
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `vds-cli evolution status` | Show kill-switch state, queue depth |
| `vds-cli evolution list` | List verdicts |
| `vds-cli evolution route SKILL.md` | Run gate pipeline on skill |
| `vds-cli evolution promote ID` | Promote verdict to master |
| `vds-cli evolution auto-promote` | Run auto-promote daemon |
| `vds-cli evolution ensemble-judge` | Run three-judge evaluation |
| `vds-cli evolution sign-verdict` | HMAC sign verdict |
| `vds-cli evolution verify-verdict` | Verify HMAC signature |
| `vds-cli evolution openspace-doctor` | Run OpenSpace readiness checks |
| `vds-cli evolution openspace-sync-shadow` | Sync canonical to shadow |

## Testing

```bash
# Run all tests
./.venv/bin/python -m pytest vds_evolution/tests/

# Run specific test file
./.venv/bin/python -m pytest vds_evolution/tests/unit/test_router.py

# Run with coverage
./.venv/bin/python -m pytest --cov=vds_evolution vds_evolution/tests/
```

## MCP Transport Selection

The system supports three MCP transports:

### stdio (default)
```bash
# Direct subprocess invocation
openspace-mcp --transport stdio
```

### SSE
```bash
OPENSPACE_TRANSPORT=sse vds-cli evolution ...
# Targets: http://localhost:8080/sse
```

### streamable-http
```bash
OPENSPACE_TRANSPORT=streamable-http vds-cli evolution ...
# Targets: http://localhost:8080/mcp
```

## Security

### HMAC Signature

Verdicts are signed with HMAC-SHA256 to ensure integrity:

```python
import hashlib
import hmac

def sign_verdict(verdict: dict) -> HmacSignature:
    payload_hash = hashlib.sha256(
        json.dumps(verdict, sort_keys=True).encode()
    ).hexdigest()
    
    signature = hmac.new(
        key=secret_key,
        msg=payload_hash.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return HmacSignature(signature=signature, payload_hash=payload_hash, ...)
```

### Key Rotation

```python
from vds_evolution.hmac_binding import sign_with_key_id

# Sign with specific key
sig = sign_with_key_id(verdict, key_id="key-v2")
```

## Troubleshooting

### OpenSpace Not Found

```bash
# Check OpenSpace installation
vds-cli evolution openspace-doctor

# Common fixes:
# 1. Install OpenSpace
pip install openspace-ai

# 2. Set workspace
export OPENSPACE_WORKSPACE=/path/to/workspace

# 3. Sync shadow skills
vds-cli evolution openspace-sync-shadow
```

### MCP Transport Errors

```bash
# Test stdio transport
openspace-mcp --help

# Check transport configuration
OPENSPACE_TRANSPORT=stdio vds-cli evolution status

# Enable debug logging
OPENSPACE_DEBUG=true vds-cli evolution route SKILL.md
```

### Verdict Signature Invalid

```bash
# Verify signature
vds-cli evolution verify-verdict path/to/verdict.json

# Re-sign if needed
vds-cli evolution sign-verdict path/to/verdict.json
```

## Dependencies

### Required
- Python 3.10+
- `vds-cli-common` - Shared CLI utilities
- `anthropic` - Claude API client
- `httpx` - HTTP transport

### Optional
- `openspace-ai` - OpenSpace MCP server
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support

## Glossary

| Term | Definition |
|------|------------|
| **Candidate** | Execution analysis with evolution suggestions |
| **Verdict** | Gate pipeline result (eligible/ineligible) |
| **Promotion** | Merging approved changes to master |
| **HMAC** | Hash-based Message Authentication Code |
| **Gate** | Quality checkpoint in the pipeline |
| **Ensemble** | Multi-judge consensus system |