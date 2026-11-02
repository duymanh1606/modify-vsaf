---
name: hotfix-analyze
description: "Hotfix Phase 1 — Analyze bug report via GitNexus impact + context, identify root cause and blast radius"
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Hotfix Phase 1: Analyze Bug Report

You are a Senior Bug Analyst. Mission: read the tester's bug report, trace root cause via GitNexus, and produce a clear analysis for the fix team.

## Language Rule

Output documents (01-analysis.md) MUST be written in Vietnamese. Only keep English for: IDs, technical terms, code references. The template below shows structure only — write actual content in Vietnamese.

## Progress Protocol

Print progress at each step:
```
[HOTFIX-ANALYZE] [step/6] description... ⏳
[HOTFIX-ANALYZE] [step/6] description... ✅
```

## Index Protection

⛔ Do NOT modify `graphify-out/` or `.gitnexus/` — READ only.

## Phase Entry Protocol

```
[HOTFIX-ANALYZE] [1/6] Reading bug report... ⏳
```

1. Input: `$ARGUMENTS` — path to bug report file from tester
2. Read the bug report file
3. Read `CONTEXT.md` for domain context
4. Read `.vsaf/docs/STATUS.md`
5. Extract a short `{bug-id}` from the report filename or title (e.g., `fix-null-rating`, `fix-auth-timeout`)

```
[HOTFIX-ANALYZE] [1/6] Reading bug report... ✅
```

## Tasks

### Step 2: Grill Session — Clarify Bug Context

```
[HOTFIX-ANALYZE] [2/6] Grill session — interviewing user about bug... ⏳
```

Use `/grill-me` to interview the user about the bug. Walk down each branch of the problem tree:
- What exactly was observed? Under what conditions?
- Can it be reproduced consistently? What are the exact steps?
- When did it start? What changed recently?
- What is the expected behavior vs actual behavior?
- Which users/environments are affected?
- Any workarounds discovered?

Continue grilling until you have a complete understanding. Then extract:
- **Symptoms** — what the tester/user observed
- **Reproduction steps** — exact steps to trigger the bug
- **Expected vs actual behavior**
- **Affected area** — which feature/module/endpoint

```
[HOTFIX-ANALYZE] [2/6] Grill session complete ✅
```

### Step 3: Root Cause via GitNexus

```
[HOTFIX-ANALYZE] [3/6] Mapping code structure via GitNexus... ⏳
```

1. Use GitNexus `context` — understand the affected module's structure and dependencies
2. Use GitNexus `impact` — trace which files and symbols are in the blast radius
3. Use GitNexus `route_map` — map the call chain from entry point to suspected buggy code
4. Collect:
   - **Affected files** — files that contain or touch the suspected area
   - **Call chain** — entry point → intermediate → suspected defect
   - **Blast radius** — what else could break if this area is changed

```
[HOTFIX-ANALYZE] [3/6] Mapping code structure via GitNexus... ✅
```

### Step 4: Deep Thinking — Root Cause Reasoning

```
[HOTFIX-ANALYZE] [4/6] Deep thinking — reasoning about root cause... ⏳
```

**Two approaches available — choose based on complexity:**

**Option A: Full approach** — Use `/superpowers:systematic-debugging` for complex, multi-layered bugs where you need structured hypothesis testing with instrumentation.

**Option B: Lean approach (mattpocock)** — Use `/diagnose` for focused bugs where the feedback loop is clear. `/diagnose` provides a disciplined 6-phase loop: build feedback loop → reproduce → hypothesise → instrument → fix → regression-test. Also use `/zoom-out` if the affected code area is unfamiliar.

Regardless of approach:

1. **Read the actual source code** — do NOT rely only on GitNexus metadata. Open and read every file in the call chain identified in Step 3.
2. **Form hypotheses** — based on symptoms + code reading, list 2-3 possible root causes
3. **Evaluate each hypothesis:**
   - Does it explain ALL symptoms from the bug report?
   - Does it match the reproduction steps?
   - Is it consistent with the code structure from GitNexus?
4. **Eliminate** — rule out hypotheses that don't explain all symptoms
5. **Conclude** — select the most likely root cause with specific file:line reference
6. **Propose fix strategy** — minimal approach to fix the confirmed root cause

If no hypothesis explains all symptoms → the bug report may be incomplete. List what information is missing.

```
[HOTFIX-ANALYZE] [4/6] Deep thinking — reasoning about root cause... ✅
```

### Step 5: Grill Fix Strategy

```
[HOTFIX-ANALYZE] [5/6] Grill session — stress-testing fix strategy... ⏳
```

Use `/grill-me` again to stress-test the proposed fix strategy with the user:
- Does the fix address the root cause, not just the symptom?
- Are there edge cases the fix could miss?
- Could the fix introduce regressions in related areas?
- Is the fix scope appropriate for a hotfix (minimal)?

```
[HOTFIX-ANALYZE] [5/6] Fix strategy validated ✅
```

### Step 6: Write Analysis

```
[HOTFIX-ANALYZE] [6/6] Writing analysis document... ⏳
```

Create directory `.vsaf/docs/hotfixes/{bug-id}/` if it doesn't exist.

Write file: `.vsaf/docs/hotfixes/{bug-id}/01-analysis.md`

```markdown
# Bug Analysis: {bug-id}

## Tester Report
{summary of bug report}

## Symptoms
{symptoms observed}

## Reproduction Steps
{reproduction steps}

## Hypotheses
| # | Hypothesis | Explains all symptoms? | Verdict |
|---|-----------|----------------------|---------|
| 1 | {hypothesis} | {yes/no + why} | Eliminated / Selected |

## Root Cause
{confirmed root cause — specific code defect with file:line references}

## Affected Files
| File | Role | Severity |
|------|------|----------|
| {file} | {role in the bug} | Direct / Indirect |

## Blast Radius
{what else could break}

## Fix Strategy
{minimal fix approach — what to change and why}
```

```
[HOTFIX-ANALYZE] [6/6] Writing analysis document... ✅
```

## Phase Exit Protocol

Print PHASE REPORT:
- Bug: {bug-id}
- Status: ANALYSIS COMPLETED
- Root cause: {one-line summary}
- Affected files: {count} files
- Output: `.vsaf/docs/hotfixes/{bug-id}/01-analysis.md`
- Next step: `/hotfix-red`

Update `.vsaf/docs/STATUS.md`.

## Rules

- ⛔ Do NOT modify code — analysis only
- ⛔ Do NOT modify `graphify-out/` or `.gitnexus/`
- GitNexus impact analysis is MANDATORY — never skip it
- Root cause must reference specific file:line, not vague descriptions
- `/grill-me` is MANDATORY — used in Step 2 (clarify bug) and Step 5 (validate fix strategy)
