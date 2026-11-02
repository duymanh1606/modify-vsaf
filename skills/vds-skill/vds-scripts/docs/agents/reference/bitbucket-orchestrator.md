<!-- diátaxis: reference -->

# Bitbucket Orchestrator

> Interact with Bitbucket: clone repos, list branches, read file contents, check PRs, and trigger pipelines.

## Scope

**What this orchestrator does:**
- Clone or mirror Git repositories from Bitbucket Cloud.
- List branches and tags programmatically.
- Read file contents at a specific commit or branch.
- Check open pull requests and their statuses.
- Trigger pipeline runs (build/test) via REST.

**What it does NOT do:**
- Does not merge pull requests or modify branch protection rules.
- Does not provide full Bitbucket administration.

**Primary users:** AI agents provisioning workspace clones; CI/CD pipelines for build triggers.

## CLI Entry

```bash
vds-cli bitbucket --help
vds-cli bitbucket-cli --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `clone` | Clone a repo locally | `--repo`, `--branch` |
| `list-branches` | List refs in a repository | `--repo` |
| `read-file` | Get file content at a path | `--repo`, `--path`, `--branch` |
| `list-prs` | Show open pull requests | `--repo`, `--state` |
| `trigger-pipeline` | Run a pipeline step | `--repo`, `--branch`, `--step` |
| `archive` | Download repo archive | `--repo`, `--format` |

## Common Workflows

### Workflow 1: Workspace Bootstrap
1. List available repos: `vds-cli bitbucket list-repos --workspace=WHO-project`.
2. Clone target repo: `vds-cli bitbucket clone --repo=vds-scripts --branch=master`.
3. Verify with `vds-cli bitbucket read-file --repo=vds-scripts --path=AGENTS.md`.

### Workflow 2: Audit Evidence Download
1. Query PRs for a checkpoint: `vds-cli bitbucket list-prs --repo=vds-scripts --state=MERGED`.
2. Download specific source files at commit: `vds-cli bitbucket read-file --repo=vds-scripts --path=src/vds_cli/router.py --branch=master`.
3. Attach downloaded files to Confluence audit pages.

## Related

- **Orchestrators:** [git](git-orchestrator.md), [confluence](confluence-orchestrator.md), [audit](audit-triage-playbook.md)
- **Skills:** [gitnexus-exploring](../../../../vds-skills/skills/gitnexus-exploring/SKILL.md)
- **Bitbucket:** https://bitbucket.digital.vn/WHO-project/vds-scripts
