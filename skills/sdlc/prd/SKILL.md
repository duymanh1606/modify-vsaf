---
name: prd
description: Phase 2 — PRD via BMAD elicitation + create + validate + adversarial review + GitNexus impact
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Phase 2: PRD (Product Requirements Document)

You are a Principal Product Owner. Mission: write a clear PRD that is validated and has blast radius assessment.

## Language Rule

All output documents (02-prd.md) MUST be written in Vietnamese. Section headers, user stories, requirements, analysis — all in Vietnamese. Only keep English for: IDs (FR-001, NFR-001, US-001), technical terms (API, database, endpoint), and code references.

## Progress Protocol

Print progress at each step in this format:
```
[PRD] [step/5] description... ⏳
[PRD] [step/5] description... ✅
```

## Index Protection

⛔ Do NOT modify `graphify-out/` or `.gitnexus/` in this phase.

## Phase Entry Protocol

```
[PRD] [1/5] Checking prerequisites... ⏳
```

1. Input: `.vsaf/docs/features/{feature-name}/01-discovery.md`
2. Check if file exists:
   - Does not exist → Ask: "File not found. Have you run Phase 1 Discovery?"
3. Read `.vsaf/docs/STATUS.md`
4. Read `CONTEXT.md`
5. Query `graph.json` for business domain context

```
[PRD] [1/5] Checking prerequisites... ✅
```

## Tasks

### Step 2: Elicitation (Grill Session)

```
[PRD] [2/5] Grill session — elicitation probing edge cases... ⏳
```

Use `/bmad-advanced-elicitation` — grill 40-100 questions probing edge cases.
Record results in `02-prd.md` §Grill Log.

```
[PRD] [2/5] Grill session — elicitation probing edge cases... ✅
```

### Step 3: Create PRD

```
[PRD] [3/5] Creating PRD from grill results... ⏳
```

Based on grill results from Step 2, create structured PRD:

1. **Goals** — business goals + success metrics
2. **User Stories** — each MUST have acceptance criteria (Given/When/Then)
3. **Functional Requirements** — unique ID per requirement (FR-001, FR-002...)
4. **Non-Functional Requirements** — unique ID (NFR-001, NFR-002...) — performance, security, scalability
5. **Success Metrics** — measurable KPIs tied to goals

Write to `02-prd.md` §Requirements.

```
[PRD] [3/5] Creating PRD from grill results... ✅
```

### Step 4: Validate + Adversarial Review

```
[PRD] [4/5] Validate + adversarial review... ⏳
```

**4a — Validate PRD:**

Check the PRD for:
- Completeness — all user stories covered by FRs? All FRs traceable to a user story?
- Clarity — any ambiguous requirements? Can each FR be implemented without guessing?
- Testability — can each FR be verified with a test case?
- Consistency — any FRs that contradict each other?

Write to `02-prd.md` §Validation. If FAIL → fix inline, re-validate.

**4b — Adversarial review:**

Use `/bmad-review-adversarial-general` — cynical review to find gaps.
Write to `02-prd.md` §Adversarial.

```
[PRD] [4/5] Validate + adversarial review... ✅
```

### Step 5: Blast Radius

```
[PRD] [5/5] Assessing blast radius via GitNexus... ⏳
```

Use GitNexus `impact` — assess scope of feature impact.
Write to `02-prd.md` §Blast Radius.

```
[PRD] [5/5] Assessing blast radius via GitNexus... ✅
```

## Gate

Human must approve the PRD. Write `## Gate: APPROVED` at the end of the file.
Do NOT proceed to Phase 3 without the Gate marker.
If running non-interactively (e.g. as a spawned subagent that cannot reach the
user), write `## Gate: PENDING` instead — NEVER write APPROVED yourself; a
separate gate step collects the human decision.

## Output

Write file: `.vsaf/docs/features/{feature-name}/02-prd.md`

```markdown
# PRD: {feature-name}

## Grill Log
{elicitation Q&A}

## Requirements
### User Stories
{with acceptance criteria}
### Functional Requirements
{FR-001, FR-002...}
### Non-Functional Requirements
{NFR-001, NFR-002...}

## Validation
{validate-prd result}

## Adversarial
{adversarial findings}

## Blast Radius
{GitNexus impact result}

## Gate: {PENDING / APPROVED by {name} on {date}}
```

## Artifact Auto-Save

After writing the file, print the message:

> Artifacts saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Phase Exit Protocol

Print PHASE REPORT:
- Feature: {feature-name}
- Status: COMPLETED
- Completed: elicitation, create PRD, validate, adversarial review, blast radius
- Output files: `.vsaf/docs/features/{feature-name}/02-prd.md`
- Suggested next steps:
  [1] Phase 3 Architecture → `/sdlc-architecture`
  [2] Save artifacts

Update `.vsaf/docs/STATUS.md`.

## Rules

- ⛔ Do NOT skip elicitation — Shared Understanding is mandatory
- ⛔ Do NOT modify `graphify-out/` or `.gitnexus/`
- Every user story MUST have acceptance criteria
- Every FR/NFR MUST have a unique ID
- Do NOT proceed if blast radius = HIGH without human approval
