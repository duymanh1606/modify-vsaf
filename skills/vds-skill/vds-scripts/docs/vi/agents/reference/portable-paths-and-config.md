<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# Portable path and configuration model

This reference defines the WHO `vds-scripts` Phase 2 path and configuration contract.
Use it when you need to understand where VDS stores configuration, cache, logs,
and shared `.env` data across macOS, Ubuntu/Linux, and Windows-oriented setups.

## Goals

- Remove machine-specific assumptions from maintained runtime guidance.
- Keep overrides explicit and predictable.
- Use a friendly portable-path contract for maintained runtime surfaces.
- Separate user-editable config from cache/data/log outputs.

## Canonical path taxonomy

| Surface | Meaning | Examples |
| --- | --- | --- |
| Workspace-relative | Paths inside the checked-out WHO workspace | `WHO-project/vds-scripts/`, `WHO-project/vds-skills/skills/` |
| User-config | User-editable shared configuration root | `VDS_CONFIG_DIR`, `~/.vds` |
| Shared env file | Shared secrets/credentials env file loaded by CLI bootstrap | `VDS_ENV_FILE`, `<config-root>/.env` |
| Cache/data/log | Derived runtime outputs and safe-to-regenerate state | `VDS_CACHE_DIR`, `VDS_DATA_DIR`, `VDS_LOG_DIR` |
| Machine-specific | Host-local absolute paths for ad hoc debugging only | `/Users/alice/...`, `C:\Users\Alice\...` |

## Directory resolution model

The shared helper layer lives in `vds_cli_common.paths` and uses one canonical user-home VDS root as the active default.

### Effective default roots

Resolution starts with explicit env overrides. If no override is provided, the runtime
uses the friendly user-home VDS defaults.

1. **Config root**
   - `VDS_CONFIG_DIR`
   - `~/.vds` on Unix-like systems
2. **Cache root**
   - `VDS_CACHE_DIR`
   - `<config-root>/cache`
3. **Data root**
   - `VDS_DATA_DIR`
   - `<config-root>/data`
4. **Log root**
   - `VDS_LOG_DIR`
   - `<config-root>/logs`

## Shared environment precedence

All CLI bootstrap flows load shared environment variables through `vds_cli_common.env`.
The precedence model is:

1. Runtime arguments for a command or orchestrator
2. Existing shell environment variables
3. Values from the shared env file (`VDS_ENV_FILE` or `<config-root>/.env`)
4. Derived defaults from code/config models

Important behavior:

- Existing shell values win by default and are not overwritten by `.env` loading.
- `load_shared_env(..., override=True)` is the explicit opt-in for replacing existing shell values.
- `ensure_shared_env()` creates the shared env file with safe defaults only and never overwrites existing values.

## Maintained Phase 2 contract

Maintained runtime surfaces in Phase 2 use a friendly portable-path contract.

- Explicit VDS overrides win.
- Otherwise, config/cache/data/log roots resolve from the canonical user-home VDS root.
- Maintained docs and examples should advertise only the active override-plus-user-home-VDS contract.

## Recommended operator patterns

### Monorepo or canonical WHO checkout

- Keep workspace-relative paths inside the repository.
- Keep secrets in the shared env file at `VDS_ENV_FILE` or `<config-root>/.env`.
- Use env overrides when you need non-default config/cache/log locations.

### External clone or CI environment

- Set `VDS_CONFIG_DIR`, `VDS_CACHE_DIR`, and `VDS_ENV_FILE` explicitly when reproducibility matters.
- Avoid baking host-specific absolute paths into checked-in scripts or docs.
- Keep the shared env file explicit; do not rely on repo-local `.env` fallback in maintained automation.

## Platform notes

### macOS

- Use `VDS_*` overrides when you need explicit locations.
- Otherwise rely on the active user-home VDS root defaults for maintained automation.

### Ubuntu/Linux

- Prefer explicit overrides or the active `~/.vds` defaults instead of hardcoding host-specific config roots in new automation.
- Keep shell examples POSIX-friendly, but document override variables rather than host-specific account paths.

### Windows-oriented environments

- Use `VDS_CONFIG_DIR`, `VDS_CACHE_DIR`, `VDS_DATA_DIR`, `VDS_LOG_DIR`, and `VDS_ENV_FILE` instead of hardcoded POSIX paths.
- Prefer environment-variable-driven examples over path separators embedded in commands.
- Treat Windows path separators as an operator concern solved by the override variables, not by checked-in absolute examples.

## Safe-to-edit vs safe-to-delete surfaces

| Surface | Editable | Safe to delete |
| --- | --- | --- |
| Shared env file | Yes | No |
| User config files | Yes | No |
| Cache/data/log outputs | Usually no | Yes, if you intend to regenerate them |
| Repo-local fallback `.env` | Only for local safe defaults | Yes, if not used locally |

## Practical checks

- Show current env/bootstrap status: `./scripts/worktree_uv.sh run --project vds_cli vds-cli env status`
- Confirm CLI health: `./scripts/worktree_uv.sh run --project vds_cli vds-cli status`
- Diagnose config/auth issues: `./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor`
- Review the verification lanes and evidence posture in `portable-paths-validation-matrix.md`
- Run Docker-based Ubuntu verification when Docker is available: `./scripts/verification/phase2_portable_paths_ubuntu_docker.sh`

Use this reference together with `cli-commands.md`, `vds-cli-reference.md`, and `portable-paths-validation-matrix.md` when updating docs, examples, bootstrap logic, or portability evidence.
