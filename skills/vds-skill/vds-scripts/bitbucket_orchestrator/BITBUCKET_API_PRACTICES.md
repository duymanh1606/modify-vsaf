# Bitbucket API Practices - VDS Orchestrator

This document outlines the practices used in the VDS Bitbucket Orchestrator, aligned with the
[Atlassian Python API documentation](https://atlassian-python-api.readthedocs.io/bitbucket.html).

## Implementation Approach

### 1. SDK Usage

We use the `atlassian-python-api` SDK (v4.0.7) as the **exclusive** method for all Bitbucket operations. This ensures:

- ✅ Consistent API interactions across all operations
- ✅ Automatic handling of Server/DC vs Cloud mode differences
- ✅ Built-in retry logic and error handling
- ✅ Type safety and validation

**Reference**: [Atlassian Python API - BitBucket module](https://atlassian-python-api.readthedocs.io/bitbucket.html)

### 2. Method Mapping

Our client wrapper maps directly to SDK methods:

| SDK Method | Our Wrapper | Documentation Reference | |------------|-------------|-------------------------| |
`create_repo()` | `create_repository()` |
[Create repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#create-a-new-repository) | | `get_repo()`
| `get_repository()` |
[Get repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#get-single-repository) | | `update_repo()` |
`update_repository()` |
[Update repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#update-single-repository) | |
`fork_repository()` | `fork_repository()` |
[Fork repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#fork-repo-inside-same-project) | |
`fork_repository_new_project()` | `fork_repository()` |
[Fork to new project](https://atlassian-python-api.readthedocs.io/bitbucket.html#fork-repo-to-new-project) | |
`get_repo_labels()` | `get_repository_labels()` |
[Get labels](https://atlassian-python-api.readthedocs.io/bitbucket.html#get-labels-for-a-single-repository) | |
`set_repo_label()` | `set_repository_label()` |
[Set label](https://atlassian-python-api.readthedocs.io/bitbucket.html#set-label-for-a-single-repository) |

### 3. Repository Management

#### Create Repository

```python
# SDK method (from documentation)
bitbucket.create_repo(project_key, repository, forkable=False, is_private=True)

# Our implementation
client.create_repository(
    project_key="INSURANCE",
    repository="vds-ai-memory",
    forkable=False,
    is_private=True
)
```

**Reference**: [Create repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#create-a-new-repository)

#### Get Repository

```python
# SDK method
bitbucket.get_repo(project_key, repository_slug)

# Our implementation
client.get_repository(project_key="INSURANCE", repository_slug="vds-ai-memory")
```

**Reference**: [Get repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#get-single-repository)

#### Update Repository

```python
# SDK method
bitbucket.update_repo(project_key, repository_slug, description="Repo description")

# Our implementation
client.update_repository(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory",
    description="Updated description"
)
```

**Reference**: [Update repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#update-single-repository)

#### Delete Repository

```python
# SDK method (DANGER!)
bitbucket.delete_repo(project_key, repository_slug)

# Our implementation
client.delete_repository(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory"
)
```

**⚠️ Warning**: This operation is irreversible. Use with extreme caution.

**Reference**:
[Delete repository](https://atlassian-python-api.readthedocs.io/bitbucket.html#delete-a-repository-danger)

#### Fork Repository

```python
# SDK method - Fork within same project
bitbucket.fork_repository(project_key, repository_slug, new_repository_slug)

# SDK method - Fork to new project
bitbucket.fork_repository_new_project(
    project_key, repository_slug, new_project_key, new_repository_slug
)

# Our implementation (handles both cases)
client.fork_repository(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory",
    new_project_key="LEP",  # Optional - if None, forks within same project
    new_repository_slug="vds-ai-memory-fork"
)
```

**Reference**:

- [Fork within same project](https://atlassian-python-api.readthedocs.io/bitbucket.html#fork-repo-inside-same-project)
- [Fork to new project](https://atlassian-python-api.readthedocs.io/bitbucket.html#fork-repo-to-new-project)

### 4. Project Management

#### List Projects

```python
# SDK method
bitbucket.project_list()

# Our implementation
client.list_projects(limit=50)
```

**Reference**: [Project list](https://atlassian-python-api.readthedocs.io/bitbucket.html#project-list)

#### Create Project

```python
# SDK method
bitbucket.create_project(key, name, description="My pretty project")

# Our implementation
client.create_project(
    key="INSURANCE",
    name="Insurance Platform",
    description="Digital Insurance Platform"
)
```

**Reference**: [Create project](https://atlassian-python-api.readthedocs.io/bitbucket.html#create-project)

### 5. Pull Request Management

#### List Pull Requests

```python
# SDK method
bitbucket.get_pull_requests(project, repository, state='OPEN', order='newest', limit=100)

# Our implementation
client.list_pull_requests(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory",
    state="OPEN",
    order="newest",
    limit=100
)
```

**Reference**: [Get pull requests](https://atlassian-python-api.readthedocs.io/bitbucket.html#get-pull-requests)

#### Create Pull Request

```python
# SDK method
bitbucket.open_pull_request(
    source_project, source_repo, dest_project, dest_repo,
    source_branch, destination_branch, title, description
)

# Our implementation
client.create_pull_request(
    source_project="INSURANCE",
    source_repo="vds-ai-memory",
    dest_project="INSURANCE",
    dest_repo="vds-ai-memory",
    source_branch="feature/new-feature",
    destination_branch="main",
    title="Add new feature",
    description="Description of changes"
)
```

**Reference**:
[Create pull request](https://atlassian-python-api.readthedocs.io/bitbucket.html#create-a-new-pull-request-between-two-branches)

### 6. Permission Management

#### Grant Repository Permissions

```python
# SDK method - User permissions
bitbucket.repo_grant_user_permissions(project_key, repo_key, username, permission)

# SDK method - Group permissions
bitbucket.repo_grant_group_permissions(project_key, repo_key, groupname, permission)

# Our implementation
client.grant_user_repository_permissions(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory",
    username="developer",
    permission="REPO_WRITE"
)

client.grant_group_repository_permissions(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory",
    group_name="developers",
    permission="REPO_READ"
)
```

**Reference**:

- [Grant user permissions](https://atlassian-python-api.readthedocs.io/bitbucket.html#grant-repository-permission-to-an-specific-user)
- [Grant group permissions](https://atlassian-python-api.readthedocs.io/bitbucket.html#grant-repository-permission-to-an-specific-group)

### 7. Code Operations

#### Get Commits

```python
# SDK method
bitbucket.get_commits(project, repository, hash_oldest, hash_newest, limit=99999)

# Our implementation
client.get_commits(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory",
    from_hash="abc123",
    to_hash="def456",
    limit=50
)
```

**Reference**: [Get commit list](https://atlassian-python-api.readthedocs.io/bitbucket.html#get-commit-list-from-repo)

#### Get Diff

```python
# SDK method
bitbucket.get_diff(project, repository, path, hash_oldest, hash_newest)

# Our implementation
client.get_diff(
    project_key="INSURANCE",
    repository_slug="vds-ai-memory",
    file_path="app/main.py",
    from_hash="abc123",
    to_hash="def456"
)
```

**Reference**: [Get diff](https://atlassian-python-api.readthedocs.io/bitbucket.html#get-diff)

### 8. Error Handling

Our implementation wraps SDK methods with comprehensive error handling:

```python
def create_repository(self, project_key: str, repository: str, ...):
    """Create a new repository."""
    try:
        result = self._client.create_repo(project_key, repository, ...)
        self._log.info("repository_created", ...)
        return result
    except Exception as exc:
        self._handle_api_error(exc, f"create_repository {repository}")
```

**Benefits**:

- ✅ Consistent error types across all operations
- ✅ Structured logging for debugging
- ✅ Context preservation in error messages
- ✅ Automatic retry for transient errors

### 9. Cloud vs Server/DC Mode

The SDK automatically handles differences between Bitbucket Cloud and Server/DC:

```python
# Our implementation detects mode automatically
if settings.is_cloud_mode:
    self._client = AtlassianBitbucket(
        url=url, timeout=self._timeout, cloud=True,
        workspace=settings.cloud_workspace, **auth_kwargs
    )
else:
    self._client = AtlassianBitbucket(
        url=url, timeout=self._timeout, **auth_kwargs
    )
```

**Reference**: The SDK handles mode differences automatically based on URL and configuration.

### 10. Retry Logic

We implement exponential backoff for transient errors:

```python
@retry_with_backoff(max_retries=3, backoff_factor=1.0)
def create_repository(self, ...):
    # Automatically retries on transport/rate limit errors
    ...
```

**Benefits**:

- ✅ Handles rate limiting gracefully
- ✅ Retries transient network errors
- ✅ Prevents unnecessary failures

## CLI Usage Examples

### Create Repository

```bash
# Using VDS CLI
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repositories INSURANCE

# Or using orchestrator directly
cd vds-scripts/bitbucket_orchestrator
uv run --project bitbucket_orchestrator python -m vds_bitbucket_orchestrator.cli repositories INSURANCE
```

### Create Repository via Python

```python
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import load_settings

settings = load_settings(strict=True)
client = BitbucketClient(settings)

# Create repository (as we did for vds-ai-memory)
result = client.create_repository(
    project_key="INSURANCE",
    repository="vds-ai-memory",
    forkable=False,
    is_private=True
)
```

## Best Practices

1. **Always use the SDK methods**: Never make direct HTTP calls
1. **Use our wrapper**: Provides consistent error handling and logging
1. **Handle errors properly**: Use try/except with our error types
1. **Log operations**: All operations are automatically logged
1. **Respect rate limits**: Retry logic handles this automatically
1. **Check mode**: Cloud vs Server/DC differences are handled automatically

## Verification

To verify our implementation matches the SDK:

```bash
# Check available SDK methods
cd vds-scripts/bitbucket_orchestrator
uv run --project bitbucket_orchestrator python -c "
from atlassian import Bitbucket
import inspect
methods = [m for m in dir(Bitbucket) if 'repo' in m.lower() and not m.startswith('_')]
print('\n'.join(sorted(methods)))
"
```

## References

- **Official Documentation**:
  [Atlassian Python API - BitBucket module](https://atlassian-python-api.readthedocs.io/bitbucket.html)
- **VDS Orchestrator**: `vds-scripts/bitbucket_orchestrator/`
- **CLI Usage**: `vds-scripts/bitbucket_orchestrator/README.md`
- **Repository**: `http://bitbucket.digital.vn/scm/insurance/vds-scripts.git`
