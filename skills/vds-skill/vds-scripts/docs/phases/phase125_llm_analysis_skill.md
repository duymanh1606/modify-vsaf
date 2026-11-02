# Phase 125: LLM-Analysis-Skill Documentation

**Task**: TSK-125.8  
**Status**: Complete  
**Effort**: ~1 hour  
**Type**: Documentation

## Overview

The `llm-analysis-skill` is **already integrated** into the audit orchestrator and requires **documentation only** - no new development work is needed.

## Integration Status

### Already Implemented ✅

The LLM analysis capability is integrated into the audit orchestrator via:

1. **CLI Flag**: `--enable-llm`
2. **Feature Flags**: 
   - `VDS_AUDIT_LLM_ENABLED`
   - `VDS_AUDIT_REQUIREMENT_LLM_ANALYSIS_ENABLED`
3. **Telemetry Tracking**: Built into the metrics system
4. **Evidence Classification**: Supplementary evidence (not authoritative)

### Usage

#### Command-Line Usage

```bash
# Enable LLM analysis for content evaluation
vds-cli audit workflow <repo_path> --thread-id <thread_id> --enable-llm

# Enable for specific checks
vds-cli audit workflow <repo_path> --thread-id <thread_id> --enable-llm --target CL-002
```

#### Environment Variables

```bash
# Enable LLM analysis globally
export VDS_AUDIT_LLM_ENABLED=true

# Enable requirement-level LLM analysis
export VDS_AUDIT_REQUIREMENT_LLM_ANALYSIS_ENABLED=true
```

## Capabilities

The LLM-analysis-skill provides content evaluation for:

1. **README Documentation** - Quality scoring and completeness analysis
2. **API Documentation** - Coverage and accuracy evaluation  
3. **Security Documentation** - Compliance and best practice verification

## Evidence Classification

**Important**: LLM-analysis-skill generates **supplementary evidence**, not authoritative evidence.

- **Role**: Provides additional context and quality scoring
- **Classification**: Supplementary/supporting evidence
- **Authority**: Does not replace primary code/docs/config evidence
- **Telemetry**: Tracked separately as `llm_analysis_evidence`

## Integration Points

### 1. Row Evaluation

When `--enable-llm` is active:
- LLM analysis runs after primary tool-first discovery
- Results are added to evidence context
- Quality scores are included in telemetry

### 2. Telemetry

LLM analysis is tracked in:
- `llm_analysis_invocations`: Count of LLM analysis calls
- `llm_analysis_duration_ms`: Execution duration
- `llm_analysis_evidence`: Evidence metadata
- `requirement_analysis`: LLM-generated insights

### 3. Quality Metrics

The skill contributes to:
- Documentation quality scores
- Evidence completeness metrics
- Requirement coverage analysis

## Configuration

### Profile Requirements

For LLM analysis to function:
- Profile must have LLM access configured
- `max_tokens` should be >= 100,000 for analysis tasks
- `timeout_sec` should be >= 300 seconds

### Example Profile

```yaml
profiles:
  anthropic-claude-sonnet-4:
    protocol: anthropic
    model: claude-sonnet-4-20250514
    timeout_sec: 600
    max_tokens: 200000
    reasoning_effort: high
```

## Comparison with Other Skills

| Skill | Type | Role | Evidence Type |
|-------|------|------|---------------|
| **llm-analysis-skill** | Content evaluation | Quality scoring | Supplementary |
| hexagonal-compliance-skill | Architecture analysis | Compliance checking | Authoritative |
| research-skill | External research | Source gathering | Authoritative |
| repomix-skill | Context packing | Companion context | Non-authoritative |
| code-review-graph-skill | Structural analysis | Companion context | Non-authoritative |

## Key Differences

### vs. Other Analysis Tools

- **vs. hexagonal-compliance-skill**: LLM-analysis evaluates content quality, not architecture compliance
- **vs. research-skill**: LLM-analysis is internal evaluation, not external research
- **vs. code-review-graph-skill**: LLM-analysis is content-focused, not code-structure-focused

### vs. Authoritative Evidence

- LLM analysis **complements** but does not **replace** primary evidence
- Quality scores are **supplementary** indicators
- Final decisions rely on **authoritative** code/docs/config evidence

## Best Practices

1. **Use as supplementary**: Enable LLM analysis for additional insights
2. **Don't rely solely**: Always combine with tool-first discovery
3. **Profile configuration**: Ensure sufficient timeout and token limits
4. **Telemetry review**: Monitor LLM analysis metrics in workflow reports

## Verification

To verify LLM analysis is working:

```bash
# Check feature flags
vds-cli audit --json-only doctor credentials

# Run with LLM enabled
vds-cli audit workflow <repo_path> --thread-id test --enable-llm

# Check telemetry for llm_analysis fields
cat tmp/<run_id>/evidence_context.jsonl | grep llm_analysis
```

## Implementation Reference

The LLM analysis integration is in:
- `audit_orchestrator/src/vds_audit_orchestrator/engine/llm_row_evaluator.py`
- `audit_orchestrator/src/vds_audit_orchestrator/llm/evaluator.py`
- Feature flags in `audit_orchestrator/src/vds_audit_orchestrator/config.py`

## Conclusion

The `llm-analysis-skill` is a fully integrated capability that provides supplementary content evaluation and quality scoring. It requires no additional development work - only proper documentation and configuration awareness. When enabled via `--enable-llm`, it enhances audit workflows with additional insights while maintaining the principle that authoritative evidence comes from primary code, documentation, and configuration sources.
