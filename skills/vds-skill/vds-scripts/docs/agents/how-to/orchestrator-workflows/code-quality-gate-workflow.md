<!-- diátaxis: how-to -->

# Code Quality Gate Workflow

> Run a comprehensive code quality pipeline combining SonarQube, hexagonal compliance, structure validation, and circular dependency detection.

## Prerequisites

- `vds-scripts` cloned and bootstrapped
- SonarQube server configured in `~/.vds/.env`
- Target repo has `pyproject.toml` or `package.json`

## Workflow Overview

```
SonarQube (static analysis)
    ↓
Hexagonal (architecture compliance)
    ↓
Structure (code organization)
    ↓
Circular Dependency (import cycles)
    ↓
Consolidated Quality Report
```

## Step 1: SonarQube Static Analysis

Run SonarQube analysis on the target repo:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli sonarqube analyze --repo vds-scripts --branch main
```

Expected output:

```
[sonarqube] Project: vds-scripts
[sonarqube] Issues: 12 (3 critical, 5 major, 4 minor)
[sonarqube] Coverage: 78%
[sonarqube] Duplications: 2.1%
```

Export the report:

```bash
vds-cli sonarqube report --repo vds-scripts --format json --output sonar-report.json
```

## Step 2: Hexagonal Compliance Check

Validate hexagonal architecture compliance:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli hexagonal check --path . --strict
```

Expected output:

```
[hexagonal] Checking dependency direction...
[hexagonal] Port/adapter boundaries: 24
[hexagonal] Violations: 2
[hexagonal] Report: hexagonal-report.json
```

## Step 3: Structure Validation

Validate code structure and organization:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli structure validate --path . --mode target-state
```

Expected output:

```
[structure] Validating folder structure...
[structure] Modules: 18
[structure] Violations: 1 (missing __init__.py)
[structure] Report: structure-report.json
```

## Step 4: Circular Dependency Detection

Detect import cycles:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli circular-dependency analyze --path . --language python
```

Expected output:

```
[circular_dependency] Analyzing imports...
[circular_dependency] Cycles found: 0
[circular_dependency] Status: PASS
```

## Step 5: Consolidated Quality Report

Generate a unified quality report:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli docs quality-report \
  --sonar sonar-report.json \
  --hexagonal hexagonal-report.json \
  --structure structure-report.json \
  --circular circular-report.json \
  --output quality-report.md
```

## CI Integration

Add to `.github/workflows/quality.yml`:

```yaml
- name: Code Quality Gate
  run: |
    vds-cli sonarqube analyze --repo ${{ github.repository }}
    vds-cli hexagonal check --path . --strict
    vds-cli structure validate --path . --mode target-state
    vds-cli circular-dependency analyze --path . --language python
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| SonarQube auth fails | Token expired | Refresh `SONAR_TOKEN` in `~/.vds/.env` |
| Hexagonal check too strict | `--strict` flag | Use `--strict=false` for gradual compliance |
| Circular dependency false positive | Test imports | Add `--exclude tests/` |
| Structure check fails on new module | Missing config | Update `target-state.yaml` |
