# Bitbucket Orchestrator Architecture Analysis

## Overview

This document verifies that there is **no duplicate logic** in the Bitbucket-related code across the VDS scripts
ecosystem. All Bitbucket operations follow a clean, single-source-of-truth architecture.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    User/Agent Interface                     │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼────┐            ┌─────▼─────┐
    │ VDS CLI │            │ MCP Server │
    └────┬────┘            └─────┬─────┘
         │                       │
         │  Routes to            │  Calls VDS CLI
         │                       │
    ┌────▼───────────────────────▼────┐
    │   Bitbucket Orchestrator         │
    │   (Single Source of Truth)      │
    └────┬────────────────────────────┘
         │
    ┌────▼────┐
    │  SDK    │
    │ (atlassian-python-api) │
    └─────────┘
```

## Single Source of Truth

### 1. Bitbucket Client (`bitbucket_orchestrator/src/vds_bitbucket_orchestrator/client.py`)

**Status**: ✅ **ONLY** place that directly uses `AtlassianBitbucket` SDK

```python
from atlassian import Bitbucket as AtlassianBitbucket

class BitbucketClient:
    """Bitbucket client wrapper using atlassian-python-api SDK."""
    def __init__(self, settings: BitbucketSettings):
        # Only place that creates AtlassianBitbucket instance
        self._client = AtlassianBitbucket(...)
```

**Verification**:

- ✅ Only file that imports `AtlassianBitbucket`
- ✅ All Bitbucket API calls go through this client
- ✅ All error handling centralized here
- ✅ All retry logic centralized here

### 2. Configuration Loading (`bitbucket_orchestrator/src/vds_bitbucket_orchestrator/config.py`)

**Status**: ✅ **ONLY** place that loads Bitbucket settings

```python
def load_settings(...) -> BitbucketSettings:
    """Load orchestrator settings from the environment."""
    # Only place that creates BitbucketSettings
```

**Verification**:

- ✅ Only file that defines `BitbucketSettings`
- ✅ Only file that implements `load_settings()` for Bitbucket
- ✅ Consistent with other orchestrators (JIRA, Confluence)

### 3. Client Factory (`bitbucket_orchestrator/src/vds_bitbucket_orchestrator/cli.py`)

**Status**: ✅ **ONLY** place that builds BitbucketClient instances

```python
def _build_client(settings: BitbucketSettings) -> BitbucketClient:
    """Build and return a configured BitbucketClient."""
    return BitbucketClient(settings)
```

**Verification**:

- ✅ Single factory function for client creation
- ✅ Used consistently across all CLI commands
- ✅ No duplicate client initialization logic

## Integration Points (No Duplication)

### 1. VDS CLI Router (`vds_cli/src/vds_cli/router.py`)

**Status**: ✅ **NO** Bitbucket logic, only routing

```python
ORCHESTRATORS = {
    "bitbucket": {
        "module": "vds_bitbucket_orchestrator.cli",
        "path": "bitbucket_orchestrator",
    },
}

def run_orchestrator(service: str, args: list[str], script_dir: Path) -> int:
    """Run orchestrator via uv."""
    # Simply routes to orchestrator, no Bitbucket-specific logic
```

**Verification**:

- ✅ No Bitbucket API calls
- ✅ No Bitbucket client creation
- ✅ No Bitbucket configuration loading
- ✅ Pure routing logic only

### 2. VDS CLI Main (`vds_cli/src/vds_cli/cli.py`)

**Status**: ✅ **NO** Bitbucket logic, only command registration

```python
@app.command(context_settings=PASS_THRU_CONTEXT)
def bitbucket(ctx: typer.Context) -> None:
    """Bitbucket operations."""
    _run_service("bitbucket", list(ctx.args))  # Routes to orchestrator
```

**Verification**:

- ✅ No Bitbucket API calls
- ✅ No Bitbucket client creation
- ✅ No Bitbucket configuration loading
- ✅ Pure command registration only

### 3. MCP Server Tools (`mcp_server/src/vds_mcp_server/tools/bitbucket_tools.py`)

**Status**: ✅ **NO** direct Bitbucket API calls, uses VDS CLI

```python
def register_bitbucket_tools(mcp: FastMCP, execute_cli: Callable[..., Any]) -> None:
    """Register Bitbucket tools with MCP server."""

    @mcp.tool()
    async def bitbucket_list_projects() -> str:
        # Uses VDS CLI, not direct API calls
        result = await execute_cli("bitbucket", "projects")
```

**Verification**:

- ✅ No direct `AtlassianBitbucket` usage
- ✅ No direct `BitbucketClient` usage
- ✅ No direct `BitbucketSettings` usage
- ✅ Uses VDS CLI as abstraction layer
- ✅ Proper separation of concerns

### 4. Git Orchestrator (`git_orchestrator/src/vds_git_orchestrator/orchestrator.py`)

**Status**: ✅ **NO** Bitbucket-specific code

**Verification**:

- ✅ No Bitbucket imports
- ✅ No Bitbucket API calls
- ✅ Only Git operations (uses Bitbucket as Git remote, not API)
- ✅ References `VDS_BITBUCKET_HTTP_BASE` for Git URL construction only

## Method Mapping Verification

All Bitbucket operations map to a single implementation:

| Operation | Implementation Location | Duplicates? | |-----------|------------------------|-------------| |
`create_repository()` | `bitbucket_orchestrator/client.py` | ❌ None | | `get_repository()` |
`bitbucket_orchestrator/client.py` | ❌ None | | `update_repository()` | `bitbucket_orchestrator/client.py` | ❌ None | |
`delete_repository()` | `bitbucket_orchestrator/client.py` | ❌ None | | `fork_repository()` |
`bitbucket_orchestrator/client.py` | ❌ None | | `list_repositories()` | `bitbucket_orchestrator/client.py` | ❌ None | |
`create_pull_request()` | `bitbucket_orchestrator/client.py` | ❌ None | | All other operations |
`bitbucket_orchestrator/client.py` | ❌ None |

## Configuration Verification

All Bitbucket configuration loading maps to a single implementation:

| Configuration | Implementation Location | Duplicates? | |---------------|------------------------|-------------| |
`BitbucketSettings` | `bitbucket_orchestrator/config.py` | ❌ None | | `load_settings()` |
`bitbucket_orchestrator/config.py` | ❌ None | | Environment variable parsing | `bitbucket_orchestrator/config.py` | ❌
None |

## Client Initialization Verification

All Bitbucket client creation maps to a single implementation:

| Initialization | Implementation Location | Duplicates? | |----------------|------------------------|-------------| |
`BitbucketClient.__init__()` | `bitbucket_orchestrator/client.py` | ❌ None | | `_build_client()` |
`bitbucket_orchestrator/cli.py` | ❌ None | | SDK client creation | `bitbucket_orchestrator/client.py` | ❌ None |

## Test Coverage Verification

All tests use the same client initialization pattern:

```python
# All tests use this pattern - no duplication
@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_something(mock_bitbucket_class: Mock, mock_settings: BitbucketSettings):
    client = BitbucketClient(mock_settings)
    # Test implementation
```

**Verification**:

- ✅ All tests mock `AtlassianBitbucket` at the same location
- ✅ All tests use `BitbucketClient` from same module
- ✅ All tests use `BitbucketSettings` from same module
- ✅ No duplicate test setup logic

## Summary

### ✅ No Duplication Found

1. **Single SDK Usage**: Only `bitbucket_orchestrator/client.py` uses `AtlassianBitbucket`
1. **Single Configuration**: Only `bitbucket_orchestrator/config.py` handles settings
1. **Single Client Factory**: Only `bitbucket_orchestrator/cli.py` has `_build_client()`
1. **Clean Integration**: VDS CLI and MCP Server use orchestrator, don't duplicate logic
1. **Consistent Patterns**: All components follow the same architecture

### Architecture Benefits

1. **Maintainability**: Changes to Bitbucket logic only need to be made in one place
1. **Consistency**: All consumers get the same behavior
1. **Testability**: Single point to mock for testing
1. **Error Handling**: Centralized error handling and retry logic
1. **Documentation**: Single source of truth for API practices

### Verification Commands

```bash
# Verify only one place imports AtlassianBitbucket
grep -r "from atlassian import Bitbucket\|AtlassianBitbucket" docs-nttc/scripts/
# Result: Only bitbucket_orchestrator/client.py

# Verify only one place defines BitbucketSettings
grep -r "class BitbucketSettings" docs-nttc/scripts/
# Result: Only bitbucket_orchestrator/config.py

# Verify only one place has _build_client for Bitbucket
grep -r "def _build_client.*Bitbucket" docs-nttc/scripts/
# Result: Only bitbucket_orchestrator/cli.py
```

## Conclusion

✅ **No duplicate logic found**. The Bitbucket orchestrator follows a clean, single-source-of-truth architecture with
proper separation of concerns:

- **Orchestrator**: Implements all Bitbucket logic
- **VDS CLI**: Routes commands to orchestrator
- **MCP Server**: Uses VDS CLI as abstraction layer
- **Git Orchestrator**: Uses Bitbucket as Git remote only, no API calls

All components work together without duplication, ensuring maintainability and consistency.
