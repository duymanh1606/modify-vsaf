---
name: setup
description: Install all SDLC dependencies — npm packages, Claude plugins, and Claude skills
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# SDLC Setup — Install Dependencies

You are a DevOps Engineer. Mission: ensure all tools required by the SDLC skill pack are installed in the current project.

## Progress Protocol

```
[SDLC-SETUP] [step/4] description... ⏳
[SDLC-SETUP] [step/4] description... ✅
```

## Step 1: Install npm Packages

```
[SDLC-SETUP] [1/4] Installing npm packages (gitnexus)... ⏳
```

Run the install script:

```bash
node "$(vsaf skill path sdlc)/install-deps.mjs"
```

If `vsaf skill path` is not available, find `install-deps.mjs` in the SDLC skill pack directory (`.claude/skills/` or the installed pack location) and run it with `node`.

This script will:
- Ensure `package.json` exists
- Install `gitnexus` as devDependency (includes MCP server built-in)
- Provision `.mcp.json` with GitNexus MCP server (`npx gitnexus mcp`)

```
[SDLC-SETUP] [1/4] Installing npm packages... ✅
```

## Step 2: Check Claude Plugins

```
[SDLC-SETUP] [2/4] Checking Claude plugins... ⏳
```

Check if the following plugins are installed:

| Plugin | Required by | How to check |
|--------|------------|--------------|
| **superpowers** | implement, review, ship, hotfix-analyze | Check if `/superpowers:test-driven-development` is available |

If missing, instruct the user:

```
⚠️ Plugin "superpowers" is not installed.
Install it: run `/install superpowers` in Claude Code
```

**DO NOT skip this step.** If superpowers is missing, WARN the user but continue.

```
[SDLC-SETUP] [2/4] Checking Claude plugins... ✅
```

## Step 3: Check Claude Skills

```
[SDLC-SETUP] [3/4] Checking Claude skills... ⏳
```

Check if the following skills are available:

| Skill | Required by | How to check |
|-------|------------|--------------|
| **graphify** | onboard-docs, feature-complete | Check if `/graphify` is available |
| **bmad-brainstorming** | discovery, prd, architecture, srs, test-design, review | Check if `/bmad-brainstorming` is available |

For each missing skill, instruct the user:

```
⚠️ Skill "graphify" is not installed.
Install it:
  pipx install graphifyy
  graphify install --platform claude
```

```
⚠️ BMAD skills are not installed.
Run: vsaf install sdlc (BMAD skills are bundled)
```

```
[SDLC-SETUP] [3/4] Checking Claude skills... ✅
```

## Step 4: Check System Binaries

```
[SDLC-SETUP] [4/4] Checking system binaries... ⏳
```

Check the following (run `{cmd} --version`):

| Binary | Required | Used by | Install hint |
|--------|----------|---------|-------------|
| **gh** | Yes | ship (PR creation) | `brew install gh` / `apt install gh` / `winget install GitHub.cli` |
| **docker** | No (optional) | implement, onboard-code | `https://docs.docker.com/get-docker/` |
| **sonar-scanner** | No (optional) | implement, review | `https://docs.sonarsource.com/sonarqube/` |

For required binaries that are missing → WARN.
For optional binaries that are missing → INFO.

```
[SDLC-SETUP] [4/4] Checking system binaries... ✅
```

## Report

Print a summary table:

```
═══════════════════════════════════════════
  SDLC SETUP REPORT
═══════════════════════════════════════════

  npm packages:
    ✅ gitnexus              {version}

  Claude plugins:
    ✅ superpowers            installed
    OR
    ⚠️ superpowers            MISSING → /install superpowers

  Claude skills:
    ✅ graphify               installed
    ✅ bmad ({N} skills)      installed
    OR
    ⚠️ ...                   MISSING

  System binaries:
    ✅ gh                     {version}
    ℹ️ docker                 not installed (optional)
    ℹ️ sonar-scanner          not installed (optional)

  MCP config:
    ✅ .mcp.json              gitnexus configured

  Index:
    ✅ GitNexus               indexed

═══════════════════════════════════════════
```

## Rules

- **DO NOT skip Step 1** — npm packages are mandatory
- **WARN but continue** for missing plugins/skills — user can install them later
- Run this skill AFTER `vsaf init` and `vsaf skill add sdlc`
- This skill is idempotent — safe to run multiple times
- DO NOT install plugins or skills automatically — only WARN and give instructions
