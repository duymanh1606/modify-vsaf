---
name: feature-complete
description: Phase 8 — Feature Completion — update CONTEXT, KNOWLEDGE, GitNexus re-index, Graphify rebuild + verify
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Phase 8: Feature Complete

You are Knowledge Engineer + DevOps. Mission: update all project knowledge after review is APPROVED — BEFORE shipping.

**Why this phase comes BEFORE ship:** Ensures shared knowledge (CONTEXT.md, KNOWLEDGE.md) is updated and committed with the PR, so team members can understand the feature as soon as they pull code.

## Progress Protocol

Print progress at each step in this format:
```
[FEATURE-COMPLETE] [step/5] description... ⏳
[FEATURE-COMPLETE] [step/5] description... ✅
```

## Artifact Auto-save

All artifacts are automatically saved to `.vsaf/docs/features/{feature-name}/` to ensure session continuity. If the session is interrupted, you can resume from the last artifact.

## Phase Entry Protocol

```
[FEATURE-COMPLETE] [1/5] Checking prerequisites... ⏳
```

1. Input: Feature name `$ARGUMENTS`
2. Check that `.vsaf/docs/features/{feature-name}/08-review.md` exists
3. Check for **Gate: APPROVED** in `08-review.md`
   - No Gate APPROVED → Stop: "Review has not been approved. Run `/sdlc-review` first."
4. Read `.vsaf/docs/STATUS.md`
5. Read `CONTEXT.md`

```
[FEATURE-COMPLETE] [1/5] Checking prerequisites... ✅
```

## Tasks

### Step 2: Update CONTEXT.md

```
[FEATURE-COMPLETE] [2/5] Updating CONTEXT.md — extracting new terminology... ⏳
```

Read all artifacts in `.vsaf/docs/features/{feature-name}/`:
- Extract new terminology that emerged during the development process
- Append to `CONTEXT.md` §Shared Language table
- Only add terminology that is TRULY new — no duplicates

```
[FEATURE-COMPLETE] [2/5] Updating CONTEXT.md... ✅
```

### Step 3: Update KNOWLEDGE.md

```
[FEATURE-COMPLETE] [3/5] Updating KNOWLEDGE.md — patterns, decisions, gotchas... ⏳
```

Append to `.vsaf/docs/KNOWLEDGE.md`:
- Lessons learned (patterns, anti-patterns)
- Noteworthy decisions (from ADR)
- Gotchas discovered during implementation

Format:
```markdown
## {feature-name} ({date})
- **Pattern**: {pattern learned}
- **Decision**: {key decision and rationale}
- **Gotcha**: {unexpected issue and solution}
```

```
[FEATURE-COMPLETE] [3/5] Updating KNOWLEDGE.md... ✅
```

### Step 4: Re-index GitNexus

```
[FEATURE-COMPLETE] [4/5] Re-index GitNexus + Rebuild Graphify graph... ⏳
```

1. Run GitNexus `group_sync` — re-index the latest code structure
   - MUST run BEFORE Graphify (Graphify needs the latest code structure)

2. Run `/graphify` — rebuild graph with **docs only** (DO NOT rebuild code graph)
   - Target: `.vsaf/docs/` folder — documents, artifacts, CONTEXT.md, KNOWLEDGE.md only
   - Output: `graphify-out/graph.json` updated

3. Claude verifies graph:
   - Do new domain terms from CONTEXT.md have nodes in the graph?
   - Do new patterns from KNOWLEDGE.md have nodes/edges?
   - Are feature artifacts linked correctly?
   - If missing → add to `graph.json`

**This is the ONLY phase (besides onboard) allowed to modify `graphify-out/` and `.gitnexus/`.**

```
[FEATURE-COMPLETE] [4/5] Re-index GitNexus + Rebuild Graphify graph... ✅
```

### Step 5: Update STATUS.md

```
[FEATURE-COMPLETE] [5/5] Updating STATUS.md... ⏳
```

Update `.vsaf/docs/STATUS.md`:
- Move feature to "Knowledge Updated" status
- Record completion timestamp

```
[FEATURE-COMPLETE] [5/5] Updating STATUS.md... ✅
```

## Output

Print FEATURE COMPLETE REPORT:

```
═══════════════════════════════════════════
  FEATURE COMPLETE: {feature-name}
═══════════════════════════════════════════
  Phase: 8 (Feature Complete — before ship)
  
  Knowledge updates:
    - CONTEXT.md: +{N} domain terms
    - KNOWLEDGE.md: +{N} patterns, +{M} decisions, +{K} gotchas
    - GitNexus: re-indexed
    - graph.json: +{N} nodes, +{M} edges (docs only)
    
  STATUS: Knowledge Updated — ready to ship
  
  Next: `/sdlc-ship` to create PR and ship
═══════════════════════════════════════════
```

## Phase Exit Protocol

Print PHASE REPORT:
- Output: CONTEXT.md, KNOWLEDGE.md, graph.json, GitNexus index updated
- Suggestion: `/sdlc-ship` to commit + create PR

Update `.vsaf/docs/STATUS.md`.

## Rules

- KNOWLEDGE.md is append-only — DO NOT edit old entries
- GitNexus re-index BEFORE Graphify rebuild
- Graph verification MUST run — do not skip
- Graphify rebuild is docs only — DO NOT rebuild code graph in this phase
- **This is the ONLY phase (besides onboard) allowed to modify `graphify-out/` and `.gitnexus/`**
- This phase MUST run BEFORE ship — so knowledge is committed with the PR
