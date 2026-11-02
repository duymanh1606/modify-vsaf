---
name: hotfix-prd
description: "Hotfix Phase 2 — Lightweight PRD from analysis: fix requirements, acceptance criteria, scope"
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Hotfix Phase 2: PRD (Fix Requirements)

You are a Principal Product Owner focused on a surgical fix. Mission: define exactly what needs to change, acceptance criteria, and "done" definition — no discovery needed (grill already happened in analyze phase).

## Language Rule

Output documents (02-prd.md) MUST be written in Vietnamese. Only keep English for: IDs, technical terms, code references.

## Progress Protocol

Print progress at each step:
```
[HOTFIX-PRD] [step/4] description... ⏳
[HOTFIX-PRD] [step/4] description... ✅
```

## Index Protection

⛔ Do NOT modify `graphify-out/` or `.gitnexus/` — READ only.

## Phase Entry Protocol

```
[HOTFIX-PRD] [1/4] Checking input artifacts... ⏳
```

1. Input: `.vsaf/docs/hotfixes/{bug-id}/01-analysis.md`
2. Verify file exists:
   - Does not exist → Stop: "Analysis not found. Run `/sdlc-hotfix-analyze` first."
3. Read the analysis file — extract:
   - Root cause (file:line)
   - Blast radius
   - Fix strategy (proposed in analyze phase)
   - Affected files
4. Read `.vsaf/docs/STATUS.md`
5. Read `CONTEXT.md`

```
[HOTFIX-PRD] [1/4] Checking input artifacts... ✅
```

## Tasks

### Step 2: Define Fix Requirements

```
[HOTFIX-PRD] [2/4] Defining fix requirements from analysis... ⏳
```

Based on the analysis (NOT a new grill session — that already happened), define:

1. **Fix Goal** — one sentence: what the fix achieves
2. **Functional Requirements** — FR-001, FR-002... (typically 1-3 for a hotfix)
   - Each FR traces to the root cause or blast radius item
3. **Acceptance Criteria** — Given/When/Then for each FR
   - MUST include a regression test criterion: "Given the fix is applied, When {original reproduction steps}, Then {expected behavior}"
4. **Scope Boundary** — explicitly state what is OUT of scope (no refactoring, no enhancements)
5. **Non-Functional Requirements** — only if relevant (performance regression, security)

```
[HOTFIX-PRD] [2/4] Defining fix requirements... ✅
```

### Step 3: Validate + Risk Check

```
[HOTFIX-PRD] [3/4] Validating PRD... ⏳
```

Use `/bmad-validate-prd` — validate:
- Every FR is testable
- Acceptance criteria are unambiguous
- Scope is minimal (hotfix, not enhancement)
- Fix addresses root cause, not just symptom

If FAIL → fix inline, re-validate.

Use GitNexus `impact` — confirm blast radius from analysis is still accurate.

```
[HOTFIX-PRD] [3/4] Validating PRD... ✅
```

### Step 4: Write PRD

```
[HOTFIX-PRD] [4/4] Writing hotfix PRD... ⏳
```

Write file: `.vsaf/docs/hotfixes/{bug-id}/02-prd.md`

```markdown
# Hotfix PRD: {bug-id}

## Fix Goal
{one sentence}

## Source
- Analysis: `01-analysis.md`
- Root cause: {file:line — summary}

## Functional Requirements

### FR-001: {title}
{description}

**Acceptance Criteria:**
- Given {context}, When {action}, Then {expected result}

### FR-002: {title} (if needed)
...

## Non-Functional Requirements
{NFR-001 if applicable, otherwise "N/A — no NFR impact for this fix"}

## Scope Boundary
**In scope:** {what will change}
**Out of scope:** {what will NOT change — no refactoring, no enhancements}

## Blast Radius (confirmed)
{from GitNexus impact — files that may be affected}

## Gate: {PENDING / APPROVED by {name} on {date}}
```

```
[HOTFIX-PRD] [4/4] Writing hotfix PRD... ✅
```

## Gate

Human must approve the PRD. Write `## Gate: APPROVED` at the end of the file.
Do NOT proceed to implementation without the Gate marker.

## Phase Exit Protocol

Print PHASE REPORT:
- Bug: {bug-id}
- Status: PRD COMPLETED
- FRs: {count} functional requirements
- Output: `.vsaf/docs/hotfixes/{bug-id}/02-prd.md`
- Next step: `/sdlc-hotfix-implement`

Update `.vsaf/docs/STATUS.md`.

> Artifacts saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Rules

- ⛔ Do NOT start a new grill session — analysis already has grill results
- ⛔ Do NOT modify `graphify-out/` or `.gitnexus/`
- ⛔ Do NOT add enhancements — hotfix scope only
- Scope MUST be minimal — fix root cause, add regression test, nothing more
- Every FR MUST be directly traceable to the root cause or blast radius
