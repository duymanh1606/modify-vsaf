<!-- diátaxis: how-to -->

# Contribute a New Orchestrator

## Prerequisites

- Python 3.14+
- uv installed
- Docker (for testing with Postgres/Redis)
- Familiarity with Typer and structlog

## Workflow

### 1. Create Branch

```bash
# From vds-scripts root
git checkout -b feature/my-new-orchestrator
```

### 2. Scaffold the Orchestrator

```bash
# Create directory
cd vds-scripts
mkdir my_orchestrator
cd my_orchestrator

# Initialize uv project
uv init --lib

# Add dependencies
uv add typer structlog pydantic-settings
```

### 3. Implement the CLI

Create `my_orchestrator/src/my_orchestrator/cli.py`:

```python
import typer
import structlog

app = typer.Typer(help="My new orchestrator")
logger = structlog.get_logger(__name__)

@app.command()
def run(input: str):
    """Run my orchestrator."""
    logger.info("starting", input=input)
    # Implementation here
    logger.info("completed", input=input)

if __name__ == "__main__":
    app()
```

### 4. Add Entry Point

Update `pyproject.toml`:

```toml
[project.scripts]
vds-my-orchestrator = "my_orchestrator.cli:app"
```

### 5. Register in Router

Add to `vds_cli/src/vds_cli/router.py`:

```python
ORCHESTRATORS = {
    # ... existing entries
    "my_orchestrator": {
        "module": "my_orchestrator.cli",
        "path": "my_orchestrator",
        "entry": "vds-my-orchestrator",
    },
}
```

### 6. Write Tests

Create `tests/test_my_orchestrator.py`:

```python
import pytest
from my_orchestrator.cli import app
from typer.testing import CliRunner

runner = CliRunner()

def test_run():
    result = runner.invoke(app, ["run", "test-input"])
    assert result.exit_code == 0
    assert "completed" in result.output
```

### 7. Add Documentation

Create `docs/agents/reference/my-orchestrator.md` following the Diátaxis pattern.

### 8. Update Ecosystem Files

- Add to `AGENTS.md` router section
- Append to `llms.txt`
- Update `ECOSYSTEM-DOCS.md`

### 9. Run Validation

```bash
vds-cli docs validate
pytest
```

### 10. Commit and PR

```bash
git add .
git commit -m "feat: add my-orchestrator orchestrator

- Implements X functionality
- Adds Y tests
- Updates docs and AGENTS.md"
```

## PR Checklist

- [ ] Tests pass (`pytest`)
- [ ] Docs validated (`vds-cli docs validate`)
- [ ] AGENTS.md line count ≤250
- [ ] New doc has YAML frontmatter
- [ ] Entry point registered in router
- [ ] No hardcoded secrets
- [ ] Error handling with context

## Code Review Criteria

Reviews check for:
- Correct Typer/structlog patterns
- Proper error handling
- Test coverage ≥80%
- Documentation completeness
- No external API calls in tests (use mocks)

## See Also

- [Orchestrator Architecture](../reference/orchestrator-architecture.md)
- [Add a Skill](../how-to/add-a-skill.md)
