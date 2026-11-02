<!-- diátaxis: how-to -->

# Tips & Tricks

## Performance

### Run Audits in Parallel

```bash
# Audit multiple repos concurrently
vds-cli audit --repo repo-a,repo-b,repo-c --parallel

# Use worktrees to avoid branch switching overhead
vds-cli git worktree-create --branch feature/x
```

### Cache Warming

```bash
# Pre-load orchestrator metadata (saves 2–3s per command)
vds-cli docs ecosystem-report --warm-cache
```

### Fast Database Queries

```bash
# Use prepared queries instead of ad-hoc
vds-cli db-query --query-file saved-query.sql --connection production
```

## Productivity

### Shell Aliases

```bash
# Add to .bashrc or .zshrc
alias vd='vds-cli'
alias vda='vds-cli audit'
alias vdc='vds-cli confluence'
alias vdg='vds-cli git'
alias vdm='vds-cli memory'
```

### Fuzzy Finder Integration

```bash
# Find and open any orchestrator command
vds-cli --help | fzf

# Search skills
cat skills-index.md | fzf
```

### Git Worktree Shortcuts

```bash
# Quick create + enter worktree
worktree() {
    vds-cli git worktree-create --branch "$1"
    cd "$(vds-cli git worktree-list --format path --branch "$1")"
}
```

### Effective Agent Prompting

- Start with the goal: "Run an audit on the INSURANCE department"
- Provide context: "Use checklist DEP-001, target repo insurance-service"
- Specify output: "Generate a markdown report with severity levels"
- Reference skills: "Use the audit-orchestrator-skill"

## Debugging

### Log Inspection

```bash
# View recent orchestrator logs
vds-cli logs --orchestrator audit --last 100

# Follow live logs
vds-cli logs --orchestrator scheduler --follow
```

### Database Queries

```bash
# Check audit results
vds-cli db-query --connection postgres --query "SELECT * FROM audit_results WHERE repo='my-service' ORDER BY created_at DESC LIMIT 10"
```

### Test Isolation

```bash
# Run a single test file
pytest tests/test_audit.py -v

# Run with verbose output
pytest tests/ -v --tb=short

# Run only failed tests
pytest --lf
```

## Quality of Life

### IDE Setup

Recommended VS Code extensions:
- Python (Microsoft)
- Even Better TOML
- Markdown All in One
- Mermaid Markdown Syntax Highlighting

### Pre-Commit Hook

```bash
# Install the hook (run once)
vds-cli lint install-hook

# Or run manually before commit
vds-cli lint --all
```

### Auto-Complete

Enable shell completion for `vds-cli`:

```bash
# Bash
vds-cli --install-completion bash

# Zsh
vds-cli --install-completion zsh
```

## See Also

- [Troubleshooting Guide](../how-to/troubleshooting-guide.md)
- [Feature Progression Guide](../tutorials/feature-progression-guide.md)
