# VDS Markdown Orchestrator

Modern Python-based markdown processing and validation tool for the VDS platform.

## Features

- **Markdown Validation**: Check formatting with mdformat
- **Auto-formatting**: Fix markdown issues automatically
- **Git Integration**: Work with staged or workspace files
- **VDS Standards**: Follows VDS CLI patterns and conventions

## Installation

This tool is part of the VDS scripts ecosystem. Use it via uv:

```bash
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown --help
```

## Usage

### Check Markdown Formatting
```bash
# Check all modified markdown files
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown check

# Check specific files
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown check README.md docs/*.md

# Check only staged files
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown check --staged
```

### Format Markdown Files
```bash
# Format all modified markdown files
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown format

# Format specific files
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown format README.md docs/*.md

# Format only staged files
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown format --staged
```

### Custom Line Width
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown check --wrap 100
./scripts/worktree_uv.sh run --project vds_cli vds-cli markdown format --wrap 100
```

## Console Scripts

- `vds-cli markdown` - Main CLI tool
- `mdformat-vds` - Alias for compatibility

## Migration from Bash Script

This tool replaces `WHO-project/insurance-document/scripts/lint-markdown.sh` (formerly `docs-nttc/scripts/lint-markdown.sh`) with:

- ✅ Same functionality (check/format modes)
- ✅ Git-aware file discovery
- ✅ Better error handling and output
- ✅ VDS-standardized CLI patterns
- ✅ Modern Python implementation

## Requirements

- Python 3.13+
- mdformat (install with `uv tool install mdformat`)
- Git repository context for file discovery
