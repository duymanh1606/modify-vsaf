# Profile Patch Recommendation: ollama-local-anthropic

## Issue

The `ollama-local-anthropic` profile has `agent_timeout_max_seconds = 240s`, which is below the Phase 125 minimum requirement of 600s.

## Current Configuration

```yaml
profiles:
  ollama-local-anthropic:
    env:
      VDS_AUDIT_LLM__AGENT_TIMEOUT_SECONDS: "150"
      VDS_AUDIT_LLM__AGENT_TIMEOUT_MAX_SECONDS: "240"  # ❌ Below 600s minimum
      VDS_AUDIT_LLM__AGENT_TIMEOUT_EXTENSION_SECONDS: "60"
```

## Recommended Change

Update the profile in `~/.vds/audit.profiles.yaml`:

```yaml
profiles:
  ollama-local-anthropic:
    env:
      VDS_AUDIT_LLM__AGENT_TIMEOUT_SECONDS: "300"  # Increase from 150 to 300
      VDS_AUDIT_LLM__AGENT_TIMEOUT_MAX_SECONDS: "600"  # Increase from 240 to 600 ✅
      VDS_AUDIT_LLM__AGENT_TIMEOUT_EXTENSION_SECONDS: "120"  # Optional: increase extension
```

## Rationale

- Phase 125 requires minimum 600s (10 minutes) for skill-augmented workflows
- The current 240s (4 minutes) is insufficient for:
  - Skill loading and execution
  - Hexagonal-compliance-skill analysis
  - LLM-analysis-skill content evaluation
  - Complex multi-step audit workflows

## Alternative: Create Phase 125 Dedicated Profile

If you prefer to keep the existing profile unchanged, create a new Phase 125-specific profile:

```yaml
profiles:
  ollama-local-anthropic-phase125:
    # Inherit from base profile
    model:
      llm:
        type: anthropic
        base_url: http://127.0.0.1:11434
        api_key: sk-local
        stream: false
        simple: glm-4.7-flash
        standard: glm-4.7-flash
        complex: glm-4.7-flash
      dspy:
        type: anthropic
        base_url: http://127.0.0.1:11434
        api_key: sk-local
        model: anthropic/glm-4.7-flash
        max_tokens: 3072
        temperature: 0.0
    env:
      VDS_AUDIT_LLM_ENABLED: "true"
      VDS_AUDIT_LLM__API_KEY: sk-local
      VDS_AUDIT_LLM__MAX_TOKENS_PER_REQUEST: "4096"
      VDS_AUDIT_LLM__OLLAMA_NUM_CTX: "49152"
      VDS_AUDIT_LLM__CODE_REVIEW_MAX_FILES: "12"
      VDS_AUDIT_LLM__AGENT_RETRIES: "2"
      VDS_AUDIT_LLM__OUTPUT_RETRIES: "4"
      VDS_AUDIT_LLM__AGENT_EVENT_STREAM_ENABLED: "false"
      # ✅ Phase 125 compliant timeouts
      VDS_AUDIT_LLM__AGENT_TIMEOUT_SECONDS: "300"
      VDS_AUDIT_LLM__AGENT_TIMEOUT_MAX_SECONDS: "900"  # 15 minutes
      VDS_AUDIT_LLM__AGENT_TIMEOUT_EXTENSION_SECONDS: "120"
      VDS_AUDIT_LLM__AGENT_TIMEOUT_EXTENSION_ATTEMPTS: "2"
      # ✅ Skills enabled for Phase 125
      VDS_AUDIT_LLM__SKILLS_DIRECTORIES: '["/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds/skills"]'
      VDS_AUDIT_LLM__SKILLS_ALLOWED_TRUST_TIERS: '["internal","external-verified"]'
      VDS_AUDIT_LLM__SKILLS_DEFAULT_TRUST_TIER: internal
      VDS_AUDIT_LLM__SKILLS_TOOLSET_ENABLED: "true"
      VDS_AUDIT_AGENTIC_ENABLE_SKILLS_TOOLSET: "true"
      VDS_AUDIT_LLM__SKILLS_SUPPRESS_SIZE_WARNINGS: "true"
      # ✅ Generous agent budget
      VDS_AUDIT_AGENTIC_ENABLED: "true"
      VDS_AUDIT_AGENTIC_MAX_TURNS: "24"
      VDS_AUDIT_AGENTIC_MAX_TOOL_CALLS: "72"
      # ... rest of configuration inherited from ollama-local-anthropic
```

## Verification

After applying the patch, verify the configuration:

```bash
# Check profile timeout/budget
uv run vds-cli audit --json-only doctor profile --name ollama-local-anthropic

# Test skill readiness
uv run vds-cli audit --json-only doctor skills-policy

# Verify timeout meets requirement
# Expected: agent_timeout_max_seconds >= 600
```

## Impact

- **Breaking Change**: No - only timeout values increased
- **Performance Impact**: Minimal - longer timeout allows for more complex workflows
- **Compatibility**: Fully compatible with existing audit workflows
- **Skills Support**: Enables full Phase 125 skill integration

## Priority

**Medium** - This profile is not the default, but should be updated for Phase 125 compliance.

## Related

- Phase 125 Task: TSK-125.10
- Documentation: `AGENTS.md` - Phase 125 Skill Integration section
- Skill Documentation: `audit-orchestrator-skill/SKILL.md` - Phase 125 section