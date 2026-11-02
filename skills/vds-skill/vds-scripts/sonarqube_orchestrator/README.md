# VDS SonarQube Orchestrator

Python CLI for SonarQube code quality scanning and issue management in the VDS platform.

## Features

### Core Features
- **Remote Issue Checking**: Query and analyze issues from SonarQube server
- **Local Scanning**: Support local Maven-based code quality scans
- **Quality Gates**: Check quality gate status for projects
- **Metrics Retrieval**: Get code quality metrics (bugs, vulnerabilities, coverage, etc.)
- **Environment Migration**: Copy credentials from project `.env` files to the shared VDS env file
- **vds-cli Integration**: Accessible via unified CLI interface

### 2025 Enhancements

#### External SCA Integration
- **Multi-Tool Support**: Works with Snyk CLI, Trivy, Syft, and Grype
- **Vulnerability Scanning**: Scan dependencies for security vulnerabilities
- **SBOM Generation**: Generate Software Bill of Materials in CycloneDX format
- **Quality Gate Checking**: Enforce security standards with vulnerability quality gates
- **Tool Detection**: Automatically detect and use available SCA tools

#### PR Decoration
- **Bitbucket Code Insights**: Decorate pull requests with SonarQube analysis results
- **Quality Gate Status**: Show pass/fail status directly in PR
- **Issue Annotations**: Add inline annotations for code issues found
- **Metrics Display**: Show key metrics (bugs, coverage, etc.) in PR view

#### Batch Operations
- **Parallel Processing**: Check quality gates for multiple projects simultaneously
- **Bulk Issue Fetching**: Retrieve issues from multiple projects at once
- **Aggregated Metrics**: Get metrics across multiple projects in a single operation

#### Report Generation
- **HTML Reports**: Generate detailed HTML quality reports
- **PDF Reports**: Generate PDF reports (requires vds-pdf-orchestrator)
- **Trend Analysis**: Include historical trend data for metrics
- **Customizable Templates**: Support for custom report templates

#### Diff Analysis
- **Branch Comparison**: Compare issues between two branches
- **New Issues**: Identify newly introduced issues
- **Resolved Issues**: Track issues that have been fixed

#### Portfolio Management
- **Cross-Project Metrics**: Aggregate metrics across multiple projects
- **Portfolio Dashboards**: Get overview metrics for entire portfolios
- **Trend Analysis**: Track quality trends across projects

#### Webhook Support
- **Event Notifications**: Receive notifications for SonarQube events
- **Webhook Management**: Register, list, and delete webhooks
- **Event Types**: Support for scan_complete, quality_gate_change, issue_created, issue_resolved
- **HMAC Signatures**: Secure webhook delivery with signature verification

## Installation

The orchestrator is part of the VDS scripts monorepo. Dependencies are managed via `uv`:

```bash
cd WHO-project/vds-scripts
uv sync --project sonarqube_orchestrator
```

**Important**: After running `uv sync`, ensure the editable install symlink exists:

```bash
./sonarqube_orchestrator/scripts/ensure_symlink.sh
```

This script creates the required symlink for the editable install to work correctly with paths containing spaces.

## Configuration

### Environment Variables

Configure in the shared VDS env file (recommended) or project `.env`:

```bash
# SonarQube Server (required)
VDS_SONAR_HOST_URL=http://sonar-10.digital.vn

# Authentication (token preferred)
VDS_SONAR_TOKEN=squ_49bef5fafd6e111428b972b1cf10c83db10ad7b4

# Alternative: username/password (fallback)
# VDS_SONAR_USER=dev
# VDS_SONAR_PASSWORD=Dev123123aA@

# Default project (optional)
VDS_SONAR_PROJECT_KEY=ekyc-business
VDS_SONAR_BRANCH_NAME=release

# Connection settings (optional)
VDS_SONAR_CONNECT_TIMEOUT=10
VDS_SONAR_REQUEST_TIMEOUT=30
VDS_SONAR_MAX_RETRIES=3
VDS_SONAR_VERIFY_CERTS=false
```

### Environment Migration

Migrate existing `SONAR_*` variables from project `.env` to the shared VDS env file:

```bash
# Preview changes (dry-run)
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- migrate-env --source EKYC-project/ekyc-business --dry-run

# Apply migration
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- migrate-env --source EKYC-project/ekyc-business
```

## Usage

### Via vds-cli (Recommended)

```bash
# Test connectivity
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- ping

# List projects
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- projects list

# Get issues for a project
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- issues list --project ekyc-business --severities CRITICAL,MAJOR

# Check quality gate status
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- qualitygate status --project ekyc-business

# Get metrics
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- measures get --project ekyc-business

# Run local Maven scan
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- scan maven --project-dir /path/to/project --project-key my-project

# Run sonar-scanner
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- scan scanner --project-dir /path/to/project --project-key my-project
```

### Direct CLI

```bash
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube ping
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube projects list
```

## CLI Commands

### Server Operations

```bash
# Test connectivity
ping

# List all projects
projects list [--query TEXT] [--limit N]

# Get project details
project get --key PROJECT_KEY
```

### Issue Operations

```bash
# List issues
issues list --project PROJECT_KEY \
    [--severities BLOCKER,CRITICAL,MAJOR,MINOR,INFO] \
    [--types BUG,VULNERABILITY,CODE_SMELL] \
    [--statuses OPEN,CONFIRMED,REOPENED,RESOLVED,CLOSED] \
    [--limit N]
```

### Metrics & Quality Gates

```bash
# Get quality metrics
measures get --project PROJECT_KEY \
    [--metrics "bugs,vulnerabilities,coverage"] \
    [--branch BRANCH]

# Check quality gate
qualitygate status --project PROJECT_KEY [--branch BRANCH]
```

### Local Scanning

```bash
# Maven scan
scan maven --project-dir PATH --project-key KEY \
    [--branch BRANCH] [--wait] [--timeout SECONDS]

# sonar-scanner
scan scanner --project-dir PATH --project-key KEY \
    [--branch BRANCH] [--wait] [--timeout SECONDS]
```

### Task Operations

```bash
# Check task status
task --status --id TASK_ID
```

### External SCA Commands

```bash
# Show available SCA tools and installation status
sca-status

# Scan dependencies for vulnerabilities
dependencies --project-dir PATH [--tool snyk|trivy|gruby|syft] \
    [--fail-threshold CRITICAL|HIGH|MEDIUM|LOW] \
    [--output json|text]

# Generate SBOM in CycloneDX format
sbom --project-dir PATH [--tool syft] [--output FILE]

# Check dependency quality gate
dependencies-check --project-dir PATH \
    [--fail-threshold CRITICAL|HIGH|MEDIUM|LOW] \
    [--max-vulnerabilities N]
```

### PR Decoration Commands

```bash
# Decorate PR with SonarQube results (requires vds-bitbucket-orchestrator)
pr-comment --project PROJECT --repository REPO --pr-id PR_ID \
    [--sonar-project KEY] [--branch BRANCH]

# Check PR analysis status
pr-status --project PROJECT --repository REPO --pr-id PR_ID \
    [--branch BRANCH]
```

### Batch Operations

```bash
# Batch quality gate check (parallel processing)
batch-qualitygate --projects proj1,proj2,proj3 [--branch BRANCH] \
    [--concurrency 3]

# Batch issue fetching
batch-issues --projects proj1,proj2,proj3 \
    [--severities CRITICAL,MAJOR] [--limit 100] \
    [--concurrency 3]

# Batch metrics retrieval
batch-measures --projects proj1,proj2,proj3 \
    [--metrics "bugs,vulnerabilities,coverage"] \
    [--branch BRANCH]
```

### Report Generation

```bash
# Generate HTML report
report html --project PROJECT_KEY --output report.html \
    [--branch BRANCH] [--include-trends] [--trend-days 30]

# Generate PDF report (requires vds-pdf-orchestrator)
report pdf --project PROJECT_KEY --output report.pdf \
    [--branch BRANCH] [--template detailed|summary]
```

### Diff Analysis

```bash
# Compare issues between branches
diff compare --project PROJECT_KEY \
    --source-branch BRANCH1 --target-branch BRANCH2 \
    [--show-new] [--show-resolved]

# Get diff summary
diff summary --project PROJECT_KEY \
    --source-branch BRANCH1 --target-branch BRANCH2
```

### Portfolio Management

```bash
# Get portfolio metrics
portfolio metrics --projects proj1,proj2,proj3 \
    [--metrics "bugs,vulnerabilities,coverage"]

# Get portfolio trends
portfolio trends --projects proj1,proj2,proj3 \
    [--days 30] [--metrics "bugs,vulnerabilities"]
```

### Webhook Management

```bash
# List webhooks
webhook list [--project PROJECT_KEY]

# Register a webhook
webhook register --url URL --events scan_complete,quality_gate_change \
    [--secret SECRET] [--project PROJECT_KEY]

# Get webhook details
webhook get --id WEBHOOK_ID

# Delete a webhook
webhook delete --id WEBHOOK_ID

# Trigger webhooks manually (for testing)
webhook trigger --event scan_complete --payload '{"test": "data"}'
```

## Python API

### 2025 Enhancement APIs

```python
from vds_sonarqube_orchestrator import (
    ExternalSCAClient,
    SonarqubePRDecorator,
    BatchExecutor,
    SonarqubeReportGenerator,
    WebhookManager,
)

# External SCA - Scan for vulnerabilities
sca_client = ExternalSCAClient()
vulnerabilities = sca_client.scan_dependencies(
    Path("/path/to/project"),
    tool="trivy"
)
print(f"Found {vulnerabilities.total_count} vulnerabilities")

# External SCA - Generate SBOM
sbom = sca_client.generate_sbom(
    Path("/path/to/project"),
    tool="syft"
)
print(f"SBOM has {sbom.component_count} components")

# PR Decoration
from vds_sonqube_orchestrator import load_settings
settings = load_settings()
decorator = SonarqubePRDecorator(settings, bb_client=bitbucket_client)
result = decorator.decorate_pr(
    project_key="INSURANCE",
    repository_slug="my-repo",
    pull_request_id="123",
    sonar_project_key="my-project"
)

# Batch Operations
executor = BatchExecutor(settings, concurrency=3)
batch_result = executor.batch_quality_gates(
    ["proj1", "proj2", "proj3"],
    branch="develop"
)
print(f"Success rate: {batch_result.success_rate:.1f}%")

# Report Generation
generator = SonarqubeReportGenerator(settings)
generator.generate_html_report(
    "my-project",
    Path("/path/to/report.html"),
    include_trends=True,
    trend_days=30
)

# Webhook Management
webhook_mgr = WebhookManager()
webhook = webhook_mgr.register_webhook(
    url="http://example.com/webhook",
    events=["scan_complete", "quality_gate_change"],
    secret="my_secret"
)
```

```python
from vds_sonarqube_orchestrator import SonarqubeClient, load_settings

# Load settings and create client
settings = load_settings()
with SonarqubeClient(settings) as client:
    # Test connectivity
    health = client.ping()
    print(health)

    # Get issues
    issues = client.get_issues(
        project_key="ekyc-business",
        severities=["CRITICAL", "MAJOR"],
    )
    for issue in issues:
        print(f"{issue['severity']}: {issue['message']}")

    # Check quality gate
    qg_status = client.get_quality_gate_status("ekyc-business")
    print(f"Quality Gate: {qg_status['status']}")

    # Get metrics
    measures = client.get_measures(
        "ekyc-business",
        ["bugs", "vulnerabilities", "coverage"],
    )
    print(f"Coverage: {measures.get('coverage', 'N/A')}%")
```

## Error Handling

The orchestrator uses a structured error hierarchy:

```python
from vds_sonarqube_orchestrator.errors import (
    SonarqubeClientError,
    SonarqubeAuthError,
    SonarqubePermissionError,
    SonarqubeNotFoundError,
    SonarqubeScannerError,
)

try:
    # client operations
    pass
except SonarqubeAuthError as e:
    print(f"Authentication failed: {e}")
except SonarqubePermissionError as e:
    print(f"Permission denied: {e}")
except SonarqubeScannerError as e:
    print(f"Scan failed: {e}")
except SonarqubeClientError as e:
    print(f"SonarQube error: {e}")
```

## Development

### Running Tests

```bash
cd sonarqube_orchestrator
uv run pytest -v
```

### Code Quality

```bash
# Linting
uv run ruff check .

# Type checking
uv run mypy src/
```

## Architecture

```
sonarqube_orchestrator/
├── src/vds_sonarqube_orchestrator/
│   ├── __init__.py       # Public API, lazy exports (version 0.2.0)
│   ├── config.py         # SonarqubeSettings (VDS_SONAR_* env vars)
│   ├── client.py         # SonarqubeClient (python-sonarqube-api wrapper)
│   ├── scanner.py        # SonarqubeScanner (Maven/sonar-scanner orchestration)
│   ├── errors.py         # Error hierarchy
│   ├── cli.py            # Typer CLI application (17 command groups)
│   ├── external_sca.py    # External SCA integration (Snyk, Trivy, Syft, Grype)
│   ├── pr.py              # PR decoration via Bitbucket Code Insights API
│   ├── batch.py           # Batch operations (concurrent multi-project)
│   ├── reports.py         # Report generation (HTML/PDF, trends)
│   ├── webhooks.py        # Webhook management (event notifications)
│   ├── diff.py            # Diff analysis (branch comparison)
│   └── portfolio.py      # Portfolio metrics aggregation
├── tests/
│   ├── conftest.py       # Shared fixtures
│   ├── test_config.py     # Config tests
│   ├── test_errors.py     # Error hierarchy tests
│   ├── test_client.py     # SonarqubeClient tests
│   ├── test_scanner.py    # Scanner tests
│   ├── test_external_sca.py # External SCA tests (50 tests)
│   ├── test_batch.py      # Batch operations tests
│   ├── test_reports.py    # Report generation tests
│   └── test_webhooks.py   # Webhook management tests
└── pyproject.toml        # Package configuration (pytest-asyncio, aiohttp, jinja2)
```

## VDS Standards Compliance

- **Technology Stack**: Python 3.11+, `python-sonarqube-api`, typer, pydantic
- **Configuration**: pydantic-settings with the shared VDS env/config layer
- **Error Handling**: Structured error hierarchy with context
- **CLI**: Typer-based with `vds-cli-common` integration
- **Testing**: pytest with fixtures for mocking
- **Code Quality**: ruff for linting, mypy for type checking

## References

- **SonarQube API Docs**: https://docs.sonarsource.com/sonarqube-server/extension-guide/web-api
- **python-sonarqube-api**: https://github.com/kako-nawao/python-sonarqube-api
- **VDS Standards**: `AGENTS.md` runtime baseline and `WHO-project/vds-scripts/docs/agents/reference/orchestrator-architecture.md`

## License

MIT
icense

MIT
icense

MIT
