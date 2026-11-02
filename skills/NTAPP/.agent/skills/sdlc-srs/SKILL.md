---
name: srs
description: Phase 4 — SRS via BMAD analyst + edge case hunter + GitNexus interface verification
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Phase 4: SRS (Software Requirements Specification)

You are a Senior Business Analyst. Your mission: write a detailed SRS with traceability, edge cases, and interface verification.

## Language Rule

All output documents (05-srs.md) MUST be written in Vietnamese. Section headers, requirements, edge case descriptions, analysis — all in Vietnamese. Only keep English for: IDs (FR-001, NFR-001, EC-001), technical terms (API, database, endpoint), and code references (class names, method signatures).

## Index Protection

⛔ **DO NOT modify** `graphify-out/` or `.gitnexus/` — READ only, never WRITE.

## Phase Entry Protocol

```
[SRS] [1/3] Checking input artifacts... ⏳
```

1. Input:
   - `.vsaf/docs/features/{feature-name}/02-prd.md`
   - `.vsaf/docs/features/{feature-name}/03-adr.md`
   - `.vsaf/docs/features/{feature-name}/04-epics.md`
2. Verify ALL 3 files exist:
   - Any file missing → Ask: "File not found. Have you pulled it yet?"
3. Read `.vsaf/docs/STATUS.md`
4. Read `CONTEXT.md`
5. Query `graph.json` for code structure + business mapping

```
[SRS] [1/3] Checking input artifacts... ✅
```

## Tasks

### Step 1: Write SRS

```
[SRS] [2/3] Writing SRS from PRD + ADR... ⏳
```

Use `/bmad-agent-analyst` — analyze PRD + ADR to identify gaps, ambiguities, and missing requirements before writing the SRS.

Derive SRS from PRD + ADR + analyst findings. For each FR/NFR:

1. **Unique ID** — FR-001, NFR-001 (sequential, no gaps)
2. **Traceability** — trace to PRD user story (US-xxx)
3. **Input/Output spec** — `{class}.{method}({params}): {return}` or API contract
4. **Constraints** — performance, security, data validation rules
5. **Pre/Post conditions** — system state before and after execution

Write to `05-srs.md`.

```
[SRS] [2/3] Writing SRS from PRD + ADR... ✅
```

### Step 2: Edge Case Analysis

```
[SRS] [2.5/3] Edge case analysis... ⏳
```

Use `/bmad-review-edge-case-hunter` — walk every boundary condition.
Write to `05-srs.md` §Edge Cases.

```
[SRS] [2.5/3] Edge case analysis... ✅
```

### Step 3: Interface Verification

```
[SRS] [3/3] Interface verification via GitNexus... ⏳
```

Use GitNexus `shape_check` — verify code structure matches SRS assumptions.
Write to `05-srs.md` §Interface Contracts.

```
[SRS] [3/3] Interface verification via GitNexus... ✅
```

## Gate

Human must approve SRS. Write `## Gate: APPROVED` at the end of the file.

## Output

Write file: `.vsaf/docs/features/{feature-name}/05-srs.md`

```markdown
# SRS: {feature-name}

## FR-001: {requirement}
- Traces to: PRD §US-{id}
- Interface: `{class}.{method}({params}): {return}`
- Constraints: ...
- Edge cases: EC-001, EC-002

## FR-002: ...

## NFR-001: ...

## Edge Cases
- EC-001: {boundary condition}
- EC-002: {race condition / null / overflow}

## Interface Contracts
{GitNexus shape_check result}

## Gate: {PENDING / APPROVED by {name} on {date}}
```

## Phase Exit Protocol

In PHASE REPORT:
- Output files: `.vsaf/docs/features/{feature-name}/05-srs.md`
- Suggestions: [1] Phase 5 Test Design (`/sdlc-test-design`) [2] Save artifacts

Update `.vsaf/docs/STATUS.md`.

**Notify the user:**
> Artifacts have been saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Rules

- Every FR/NFR MUST have a unique traceability ID
- DO NOT use vague language: "should", "might", "optionally" → replace with "MUST", "MUST NOT"
- All terms MUST exist in CONTEXT.md
- Every FR MUST be testable (have clear pass/fail criteria)
- ⛔ DO NOT modify `graphify-out/` or `.gitnexus/`
