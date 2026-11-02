<!-- diátaxis: tutorial -->

# Feature Progression Guide

Continue your WHO ecosystem journey beyond the [Zero to Productive Developer](../tutorials/zero-to-productive-developer.md) tutorial.

## Day 8 — Multi-Project Audit

Run audits across multiple repositories in a single command.

```bash
# Audit all projects in a department
vds-cli audit --department INSURANCE --checklist DEP-001

# Audit specific repos
vds-cli audit --repo repo-a,repo-b,repo-c --checklist PAR-001
```

**Learn:** Audit configuration, checklist selection, report interpretation.

## Day 9 — Confluence Integration

Upload audit evidence and reports to Confluence automatically.

```bash
# Sync evidence after audit
vds-cli docs confluence-sync --repo my-service

# Generate quality score report
vds-cli docs quality-score
```

**Learn:** Confluence sync targets, evidence format, page structure.

## Day 10 — Hexagonal Compliance

Verify your service follows clean architecture principles.

```bash
# Check hexagonal compliance
vds-cli hexagonal --repo my-service

# View detailed boundary report
vds-cli hexagonal --repo my-service --format json
```

**Learn:** Port/adapter boundaries, dependency direction, violation patterns.

## Day 11 — Circular Dependency Detection

Identify risky dependency cycles across microservices.

```bash
# Detect cycles in a project
vds-cli circular-dependency --project INSURANCE

# Export graph for visualization
vds-cli circular-dependency --project INSURANCE --format mermaid
```

**Learn:** Dependency manifests, cycle classification, remediation strategies.

## Day 12 — Git Worktree Management

Use worktrees for parallel feature development without branch switching.

```bash
# Create a worktree for a feature
vds-cli git worktree-create --branch feature/my-change

# List all worktrees
vds-cli git worktree-list
```

**Learn:** Worktree lifecycle, repair, cleanup, multi-repo workflows.

## Day 13 — Custom Orchestrator Exploration

Explore advanced orchestrators for specialized tasks.

```bash
# Research a topic combining local and web search
vds-cli research --query "best practices for API pagination"

# Generate a diagram from code
vds-cli diagrams --repo my-service --format png

# Convert schema formats
vds-cli schema --input openapi.yaml --output jsonschema
```

**Learn:** Orchestrator selection, output formats, chaining commands.

## Day 14 — Multi-Agent Workflows

Coordinate parallel agent teams for complex tasks.

```bash
# Run a multi-agent workflow
vds-cli multi-agent --workflow spec-to-impl --spec my-spec.md

# Monitor agent progress
vds-cli multi-agent --status
```

**Learn:** Workflow definitions, agent roles, result aggregation.

## Beyond Day 14

- [Contribute a new orchestrator](../how-to/contribute-new-orchestrator.md)
- [Author a custom skill](../how-to/add-a-skill.md)
- [Explore the full orchestrator index](../../reference/orchestrator-index.md)
