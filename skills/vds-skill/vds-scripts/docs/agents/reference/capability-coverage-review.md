<!-- diátaxis: reference -->

# Capability Coverage Review

This review compares the implemented WHO ecosystem alignment changes against the current capability inventory.

## Coverage status

### Covered by platform skill and routing docs

- bootstrap and discovery command families
- integration command families
- documentation and validation command families
- development and workflow command families
- specialist skill routing guidance
- canonical WHO ownership model for skills and scripts
- human and AI onboarding/routing docs

### Covered by capability inventory

- routed command surfaces
- standalone workspace capabilities such as markdown, hexagonal, MCP, and multi-agent support
- shared/internal support layers such as `vds_cli_common`
- skills-catalog linkage
- derived/generated surfaces

### Covered by skills-catalog alignment

- updated `vds-scripts-skill` role and metadata
- updated `llm-analysis-skill` catalog description
- updated skills-catalog guidance for platform routing

## Deferred to controlled root-level step

These items are intentionally not finalized inside the isolated repo worktrees:

- root generated `AGENTS.md` sync
- monorepo-root execution of `verify-alignment.sh`
- any root-surface updates that would escape the two isolated repo worktrees

## Conclusion

The worktree-local implementation covers the spec's repo-local skills/docs/routing requirements.
The remaining completion items are the controlled generated-surface sync and monorepo-root alignment verification step.

## Related Documents

- [VDS CLI Reference](vds-cli-reference.md)
- [Orchestrator Index](orchestrator-index.md)
- [Skills Reference](skills-reference.md)
- [Confluence Hub](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
