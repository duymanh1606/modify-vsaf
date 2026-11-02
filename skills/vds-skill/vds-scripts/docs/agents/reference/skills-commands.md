<!-- diátaxis: reference -->

# Skills Commands Reference

> Unified VDS skill management via `vds-cli skills`. Delegates to `vds-skills-sync`.

## Summary Box

| Property | Value |
|---|---|
| Command family | `vds-cli skills` |
| Underlying package | `vds-skills-sync` (sibling repo) |
| Delegation mode | Subprocess (`python -m vds_skills_sync`) |
| Source file | `vds_cli/src/vds_cli/skills_cmd.py` |
| Target agents | Claude Code, Cursor, Copilot, generic |

**Important:** This command family is a thin wrapper. It does not import `vds-skills-sync`; it resolves the package path, injects it into `PYTHONPATH`, and spawns a subprocess. Exit codes and stdout/stderr are forwarded verbatim.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Subcommands](#subcommands)
  - [sync](#sync)
  - [list](#list)
  - [validate](#validate)
  - [info](#info)
  - [rollback](#rollback)
  - [version](#version)
- [Environment](#environment)
- [Exit Codes](#exit-codes)
- [See Also](#see-also)

## Quick Reference

| Subcommand | Purpose | Key Flags | Example |
|---|---|---|---|
| `sync` | Install skills to an AI agent | `--agent`, `--dry-run`, `--skills`, `--exclude-skills`, `--diff` | `vds-cli skills sync --agent cursor --dry-run` |
| `list` | List all registry skills | (none) | `vds-cli skills list` |
| `validate` | Check skills against the AgentSkills spec | `--skill`, `--all`, `--strict`, `--fix`, `--json` | `vds-cli skills validate --all --strict` |
| `info` | Show rendered content for one skill | `NAME` (positional) | `vds-cli skills info audit-orchestrator-skill` |
| `rollback` | Restore skills from the most recent backup | (none) | `vds-cli skills rollback` |
| `version` | Show vds-skills-sync package version | (none) | `vds-cli skills version` |

## Subcommands

### sync

Install or update VDS skills for a target AI agent.

```bash
vds-cli skills sync [OPTIONS]
```

#### Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--agent`, `-a` | string | `claude` | Target agent: `claude`, `cursor`, `copilot`, `generic`, `all` |
| `--dry-run` | bool | `False` | Preview changes without writing files |
| `--force` | bool | `False` | Skip validation checks before sync |
| `--scope` | string | `project` | Installation scope: `project` or `user` (affects Cursor) |
| `--skills` | string | `""` | Comma-separated skill names to sync. **Mutually exclusive with `--exclude-skills`.** |
| `--exclude-skills` | string | `""` | Comma-separated skill names to exclude. **Mutually exclusive with `--skills`.** |
| `--category` | string | `""` | Comma-separated categories to filter skills |
| `--diff` | bool | `False` | Show structured diff (requires `--dry-run`) |
| `--diff-format` | string | `summary` | Diff output format: `summary`, `unified`, or `json` |

#### Example: dry-run with diff

```bash
vds-cli skills sync --agent claude --dry-run --diff --diff-format unified
```

#### Example: sync specific skills

```bash
vds-cli skills sync --agent copilot --skills "audit-orchestrator-skill,spec-creation-skill"
```

#### Example: sync all except excluded

```bash
vds-cli skills sync --agent generic --exclude-skills "legacy-migration-skill"
```

#### Mutual Exclusion

Passing both `--skills` and `--exclude-skills` raises a `typer.BadParameter` error before delegation.

---

### list

List every skill declared in the VDS registry.

```bash
vds-cli skills list
```

#### Flags

This subcommand accepts no wrapper-level flags. Output formatting is determined by the underlying `vds-skills-sync` package.

#### Example

```bash
vds-cli skills list
```

---

### validate

Validate VDS skills against the AgentSkills specification.

```bash
vds-cli skills validate [OPTIONS]
```

#### Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `--skill`, `--validate-skill` | path | `None` | Validate a single `SKILL.md` file by path |
| `--all`, `--validate-all` | bool | `False` | Validate every registry-declared skill (default when no target given) |
| `--strict` | bool | `False` | Promote quality warnings to errors |
| `--fix` | bool | `False` | Auto-correct trivial issues in-place |
| `--output`, `-o` | path | `None` | Write audit report to `PATH` |
| `--json` | bool | `False` | Output JSON instead of human-readable text |

#### JSON Output Caveat

When invoked via this CLI wrapper, JSON output may include header lines on stdout. To extract clean JSON, pipe through a filter:

```bash
vds-cli skills validate --all --json | python -c 'import json,sys; [print(l) for l in sys.stdin if l.strip().startswith(("{","["))]'
```

#### Example: validate all skills strictly

```bash
vds-cli skills validate --all --strict
```

#### Example: validate one file and write a report

```bash
vds-cli skills validate --skill ./skills/my-skill/SKILL.md --output ./audit-report.txt
```

#### Example: auto-fix and validate

```bash
vds-cli skills validate --all --fix --strict
```

---

### info

Show the rendered content for a single skill.

```bash
vds-cli skills info NAME
```

#### Arguments

| Argument | Type | Description |
|---|---|---|
| `NAME` | string | Skill name, e.g. `audit-orchestrator-skill` |

#### Example

```bash
vds-cli skills info audit-orchestrator-skill
```

---

### rollback

Restore skills from the most recent backup.

```bash
vds-cli skills rollback
```

#### Flags

This subcommand accepts no wrapper-level flags or arguments.

#### Safety Notes

- Rollback operates on the backup created by the most recent successful `sync`.
- If no backup exists, the underlying package exits non-zero.
- Always run `vds-cli skills sync --dry-run` before a destructive sync if you need a predictable restore point.

#### Example

```bash
vds-cli skills rollback
```

### version

Show the installed version of the `vds-skills-sync` package.

```bash
vds-cli skills version
```

**Example output:**

```
vds-skills-sync 0.7.3
```

## Environment

| Variable | Effect |
|---|---|
| `VDS_SKILLS_SYNC_DIR` | Overrides the path to the `vds-skills-sync` package. Must contain `src/vds_skills_sync/__init__.py`. |
| `PYTHONPATH` | The wrapper prepends the resolved `vds-skills-sync/src` directory to the existing value (if any) before spawning the subprocess. |

### Path Resolution

The wrapper resolves the `vds-skills-sync` package in this order:

1. `VDS_SKILLS_SYNC_DIR` environment variable.
2. Walk up from `skills_cmd.py` until `WHO-project/vds-skills/vds-skills-sync` is found.
3. If neither succeeds, raise `RuntimeError`.

## Exit Codes

| Subcommand | Code | Meaning |
|---|---|---|
| **Any** | `0` | Success |
| **Any** | `1` | General validation or runtime error (forwarded from `vds-skills-sync`) |
| **Any** | `2` | Strict quality failure (`--strict` set) |
| **sync** | `1` | Invalid flag combination (e.g. `--skills` + `--exclude-skills`) or downstream sync error |
| **validate** | `1` | Validation errors or invalid flag combination (e.g. `--skill` + `--all`) |
| **validate** | `2` | Quality warnings promoted to errors by `--strict` |
| **list / info / rollback** | `1` | Downstream error (forwarded from `vds-skills-sync`) |

## See Also

- [AGENTS.md](../../../../AGENTS.md) — high-level agent entry point
- `vds-skills-sync` spec — `.gpt-5.4/specs/vds-skills-sync/`
- [VDS CLI Reference](vds-cli-reference.md) — command-family routing
- [Skills Reference](skills-reference.md) — canonical skills catalog
- [CLI Help Matrix](cli-help-matrix.md) — verified routed command inventory

---

*Generated from `skills_cmd.py` (Phase 179). Do not modify flag semantics without updating both the source and this document.*
