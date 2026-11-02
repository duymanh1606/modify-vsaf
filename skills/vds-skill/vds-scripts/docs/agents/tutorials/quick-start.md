<!-- diátaxis: tutorial -->

# Quick Start

Get the WHO ecosystem running in under 5 minutes.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (for Postgres and Redis)

## Install

```bash
# Clone the main repository
git clone https://bitbucket.org/viettel-digital-services/vds-scripts
cd vds-scripts

# Sync dependencies
uv sync

# Verify installation
vds-cli --help
```

## First Command

```bash
# Run a health check
vds-cli docs validate --help

# Check ecosystem status
vds-cli docs ecosystem-report
```

## Common Workflows

After installation, most developers follow one of these common workflows to get productive quickly:

- [Run an audit with the orchestrator](../how-to/audit-orchestrator.md) — end-to-end project audit.
- [Sync skills across agents](../how-to/skill-sync.md) — keep skills up to date.
- [Validate documentation quality](../how-to/docs-quality.md) — check docs before a release.
- [Schedule recurring jobs with the scheduler](../how-to/scheduler-workflow.md) — cron-like task management.

## Next Steps

- [System Requirements](../reference/system-requirements.md)
- [Install and Bootstrap](../how-to/install-and-bootstrap-who-scripts-and-skills.md)
- [Zero to Productive Developer](../tutorials/zero-to-productive-developer.md)
