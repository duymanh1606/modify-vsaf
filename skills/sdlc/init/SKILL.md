---
name: init
description: Initialize SDLC artifact structure — create .vsaf/docs/, CONTEXT.md, .gitignore
version: 2.0.0
author: "@ngocsangairvds/vsaf"
---

# Init — Initialize SDLC Artifact Structure

You are a DevOps Engineer. Mission: create the SDLC artifact directory structure and project templates.

**Prerequisite:** Run `/sdlc-setup` first to install dependencies (npm packages, plugins, MCP config, GitNexus index).

## Progress Protocol

Each step prints progress:
```
[INIT] [1/5] Check project path... (icon)
```
Icon: `⏳` running, `✅` done, `❌` error.

## Index Protection

> ⛔ DO NOT modify `graphify-out/` or `.gitnexus/` — only READ and DO NOT write to these directories.

## Input

- Project path: `$ARGUMENTS` (or current directory)

## Steps

### Step 1: Check Prerequisites

```
[INIT] [1/5] Checking prerequisites... ⏳
```

1. Confirm project path exists and is a valid directory
2. Check if `.mcp.json` exists with `gitnexus` entry — if not → STOP: "Run `/sdlc-setup` first."
3. Check if `.vsaf/docs/` already exists:
   - Already exists → Print warning: "`.vsaf/docs/` already exists. Will merge, NOT overwrite."
   - Does not exist → Proceed to create new

```
[INIT] [1/5] Checking prerequisites... ✅
```

### Step 2: Create .vsaf/docs/ Structure

```
[INIT] [2/5] Create .vsaf/docs/ structure... ⏳
```

Create directory structure:
```
.vsaf/
  docs/
    STATUS.md          ← Feature tracking (name, phase, status)
    KNOWLEDGE.md       ← Accumulated domain knowledge
    features/          ← Feature artifacts (01-discovery.md, 02-prd.md, ...)
    hotfixes/          ← Hotfix artifacts (01-analysis.md, 02-review.md, ...)
    onboarding/        ← Onboarding imports (doc-imports/, env-setup.md)
```

**STATUS.md** template:
```markdown
# SDLC Status Tracker

## Active Features

| Feature | Phase | Status | Last Updated |
|---------|-------|--------|-------------|

## Active Hotfixes

| Bug ID | Phase | Status | Last Updated |
|--------|-------|--------|-------------|

## Completed Features

## Completed Hotfixes
```

**KNOWLEDGE.md** template:
```markdown
# Domain Knowledge

Accumulated knowledge from all phases.
```

```
[INIT] [2/5] Create .vsaf/docs/ structure... ✅
```

### Step 3: Create CONTEXT.md

```
[INIT] [3/5] Create CONTEXT.md template... ⏳
```

1. Check if `CONTEXT.md` already exists:
   - Already exists → **DO NOT overwrite**, print: "CONTEXT.md already exists, keeping as-is."
   - Does not exist → Create template:

```markdown
# Project Context

## Project Overview
{Brief project description — fill after onboarding}

## Tech Stack
{Will be updated by onboard-code}

## Shared Language

| Term | Definition | Example |
|------|-----------|---------|
| {term} | {1-line definition} | {concrete example} |

## Architecture Decisions
{Will be updated by sdlc-architecture}
```

```
[INIT] [3/5] Create CONTEXT.md template... ✅
```

### Step 4: Setup .gitignore

```
[INIT] [4/5] Setup .gitignore... ⏳
```

1. Check if `.gitignore` exists
2. If does not exist: create new
3. Check and add the following entries (if not already present):
   ```
   graphify-out/
   .gitnexus/
   ```
4. DO NOT remove any existing entries from `.gitignore`

```
[INIT] [4/5] Setup .gitignore... ✅
```

### Step 5: Verify & Report

```
[INIT] [5/5] Verify & create report... ⏳
```

Check everything and print STATUS TABLE:

```
=== SDLC Init Report ===

| Item              | Status |
|-------------------|--------|
| .vsaf/docs/    | ✅ Created / ⚠️ Already existed |
| STATUS.md         | ✅ Created / ⚠️ Already existed |
| KNOWLEDGE.md      | ✅ Created / ⚠️ Already existed |
| features/         | ✅ Created / ⚠️ Already existed |
| hotfixes/         | ✅ Created / ⚠️ Already existed |
| onboarding/       | ✅ Created / ⚠️ Already existed |
| CONTEXT.md        | ✅ Created / ⚠️ Already existed |
| .gitignore        | ✅ Updated |

=== Next steps ===
```

```
[INIT] [5/5] Verify & create report... ✅
```

## Artifact Auto-Save

After completion, print message:

> Artifacts saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Next Steps

Print suggestions:
1. `/sdlc-onboard-docs` — Build document knowledge graph
2. `/sdlc-onboard-code` — Index code + environment setup
3. `/sdlc-discovery` — Start Discovery for a new feature

## Rules

- DO NOT overwrite existing files — only MERGE or SKIP
- `.gitignore` only ADD entries, DO NOT REMOVE
- ⛔ DO NOT modify `graphify-out/` or `.gitnexus/`
- If any step FAILS: print clear error, continue remaining steps, record in report
- **DO NOT provision .mcp.json** — that is `/sdlc-setup`'s job
