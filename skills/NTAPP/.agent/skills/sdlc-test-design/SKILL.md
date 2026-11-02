---
name: test-design
description: Phase 5 — Test Design via BMAD QA + edge case hunter + GitNexus coverage mapping
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Phase 5: Test Design

You are a QA Lead. Your mission: design test cases FROM the SRS (spec), NOT from code. Tests BEFORE code (#2 TDD).

## Index Protection

⛔ **DO NOT modify** `graphify-out/` or `.gitnexus/` — READ only, never WRITE.

## Phase Entry Protocol

```
[TEST-DESIGN] [1/4] Checking input artifacts... ⏳
```

1. Input: `.vsaf/docs/features/{feature-name}/05-srs.md`
2. Verify file exists + **check Gate: APPROVED**
   - No Gate → Stop: "SRS has not been approved"
3. Read `.vsaf/docs/STATUS.md`
4. Read `CONTEXT.md`

```
[TEST-DESIGN] [1/4] Checking input artifacts... ✅
```

## Tasks

### Step 1: Generate Test Cases

```
[TEST-DESIGN] [2/4] Generating test cases from SRS... ⏳
```

Use `/bmad-qa-generate-e2e-tests` — generate test cases from SRS FRs/NFRs.

For each requirement, ensure ≥1 test case with:

1. **Unique ID** — TC-001 (sequential)
2. **Traceability** — TC → FR/NFR → PRD user story (US-xxx)
3. **Type** — unit / integration / e2e (based on requirement scope)
4. **Precondition** — system state before test
5. **Steps** — exact actions to execute
6. **Expected result** — concrete, verifiable outcome (not "should work")

Prioritize: happy path first, then error paths, then edge cases.

```
[TEST-DESIGN] [2/4] Generating test cases from SRS... ✅
```

### Step 2: Boundary Tests

```
[TEST-DESIGN] [3/4] Boundary & edge case tests... ⏳
```

Use `/bmad-review-edge-case-hunter` — add boundary tests.
Race conditions, null/empty, overflow, concurrent access.

```
[TEST-DESIGN] [3/4] Boundary & edge case tests... ✅
```

### Step 3: Coverage Map

```
[TEST-DESIGN] [4/4] Coverage mapping via GitNexus... ⏳
```

Use GitNexus `detect_changes` — predict files that will be modified.
Map test cases → files requiring coverage.

```
[TEST-DESIGN] [4/4] Coverage mapping via GitNexus... ✅
```

## Output

Write file: `.vsaf/docs/features/{feature-name}/06-testcases.md`

```markdown
# Test Cases: {feature-name}

## TC-001 → FR-001 → US-003
- Type: unit
- File target: src/user/user.service.ts
- Precondition: ...
- Steps: ...
- Expected: ...

## TC-002 → FR-001 (edge case: empty input)
- Type: unit
- Precondition: ...
- Steps: ...
- Expected: ...

## Coverage Map
- src/user/user.service.ts → TC-001, TC-002
- src/user/user.controller.ts → TC-005, TC-006

## Traceability Matrix
| FR/NFR | Test Cases | Coverage |
|--------|-----------|----------|
| FR-001 | TC-001, TC-002 | ✓ |
| FR-002 | TC-003 | ✓ |
| NFR-001 | TC-010 | ✓ |
```

## Phase Exit Protocol

In PHASE REPORT:
- Output files: `.vsaf/docs/features/{feature-name}/06-testcases.md`
- Suggestions: [1] Phase 6 Implementation (`/sdlc-implement`) [2] Save artifacts

Update `.vsaf/docs/STATUS.md`.

**Notify the user:**
> Artifacts have been saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Rules

- Test cases derive from SRS (spec), NEVER from code
- Every FR/NFR MUST have ≥1 test case
- Traceability chain is mandatory: TC → FR → US
- DO NOT read source code when writing test cases
- ⛔ DO NOT modify `graphify-out/` or `.gitnexus/`
