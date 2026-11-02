# Step 2: Warning Gate

## GOAL
Block apply nếu routing object có `warnings_pending` non-empty, trừ khi DSO cung cấp override note hợp lệ qua HITL. Log override vào build report.

## 1. Load Persona

Adopt role của **Warning Blocker** sub-agent tại `../agents/warning-blocker.md`. Persona declare: role + warning categories matrix (§4) + override section format (§5) + constraints. Pipeline + prompt template ở step file này.

## 2. Inputs

- Routing object (`warnings_pending`, `warnings_resolved`) từ Step 1.
- `_shared/proposal-schema.md` (warning categories reference).

## 3. Pipeline

### Stage 3.1: Scan PENDING

```
if routing.warnings_pending is empty:
  log "[WARN-BLOCKER] 0 pending, {M} resolved, override=false"
  → return PASS, không emit section.
```

### Stage 3.2: Hard-fail category check (pre-prompt)

Iterate `warnings_pending`, check category match hard-fail list (xem `warning-blocker.md` §4 — hiện tại: `library_wrap_undecided`):

```
for warning in warnings_pending:
  if warning.category in HARD_FAIL_CATEGORIES:
    → STOP unconditionally với message:
      "Hard-fail warning {warning.id} ({warning.category}): {warning.message}.
       Không cho phép DSO override. Quay lại Stage 4b Agent 1 fix proposal."
```

### Stage 3.3: HITL override prompt

Nếu vượt qua Stage 3.2 (warnings còn lại đều soft):

```
List tất cả PENDING warnings (id + message + category) cho DSO.

HITL prompt:
  "Có {N} PENDING warnings. Override để continue apply?
   Cung cấp note ≥20 chars (không chứa TODO/FIXME/fix later).
   Reply 'cancel' để abort build."

if DSO reply 'cancel':
  → STOP "Build cancelled by DSO. Resolve warnings trong proposal rồi chạy lại."

Validate note:
  - empty OR < 20 chars → re-prompt: "override note too vague — provide specific reason"
  - chứa 'TODO' / 'FIXME' / 'fix later' (case-insensitive) → re-prompt: "override note implies unresolved — not acceptable"
  - 1 lần re-prompt; lần 2 invalid → STOP.
```

### Stage 3.4: Emit override section

Note hợp lệ → resolve `By:`:

- Try `git config user.email` (cwd code repo).
- Fallback env var `DSO_EMAIL`.
- Both missing → use literal `unknown@local` + log warning.

Append section vào `build_report_sections[]` theo format ở `warning-blocker.md` §5. Set `routing.warning_override = { note, by, at }`.

### Stage 3.5: Catch-all unknown category

Nếu warning có category không match bảng `warning-blocker.md` §4 → treat as `medium` severity, allow override path (Stage 3.3), log `[WARN-BLOCKER] unknown category '{name}' treated as medium`.

## 4. Output

- Console log dòng `[WARN-BLOCKER] ...`.
- In-memory override section (nếu có) trong `build_report_sections[]`.
- Routing object enriched với `warning_override` (nếu có).

## DECISION POINTS

- Hard-fail category trong `warnings_pending` → STOP unconditionally (KHÔNG prompt override).
- DSO reply 'cancel' → STOP.
- Override note invalid 2 lần → STOP.
- Override all-or-nothing — DSO không thể override 1 trong N (phải resolve N-1 trong proposal trước).

> **[GATE]** HITL warning override (Stage 3.3) phải PASS — `warnings_pending` rỗng HOẶC DSO cung cấp note hợp lệ. Hard-fail category / DSO 'cancel' / note invalid 2 lần → STOP, KHÔNG đọc step kế.

**Next:** Read fully and follow `./step-03-apply-tokens.md`
