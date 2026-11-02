# Step 4: Aesthetic Self-Critique (TERMINAL, optional)
> 🎭 Hoá thân **Visual Composition Auditor**. Đọc persona đầy đủ: `../agents/visual_composition_auditor.md`. Global rules (U1–U5) ở `../workflow.md`.
> ⛔ Đây là step cuối — KHÔNG còn step kế. Chứa HITL visual gate (§4) khi rubric FAIL sau self-correct.

## GOAL
Kiểm chứng quyết định thẩm mỹ deterministic **TRƯỚC khi `ui_schema_{id}.json` bàn giao Stage 5** — cắt vòng lặp "render xấu → sửa tay". Chấm bố cục đã resolve token-value theo `_shared/aesthetic-rubric.md`, self-correct ≤3 vòng, escalate HITL nếu vẫn FAIL.

## 0. Applicability — feature-flag (default ON, opt-out)

Step 4 chạy **mặc định** cho mọi unit có bố cục đáng kể. Default **ON** (opt-out) — A5 contrast là hard floor a11y, tắt đồng nghĩa chấp nhận rủi ro ship contrast fail.

| Nguồn flag | Cách tắt |
|---|---|
| Per-run arg | User truyền `aesthetic_critique=off` cho run hiện tại. |
| Config | `.bmm-config.yaml` block skill `aesthetic_critique: off` → tắt cho mọi unit (KHÔNG khuyến nghị — ghi rõ lý do trong config comment). |

- Flag OFF → **skip Step 4 hoàn toàn**. `ui_schema_{id}.json` từ Step 3 là output cuối (backward-compatible — schema không có Step 4 vẫn valid, `visual_intent` optional). Lưu ý: tầng contrast proposal-time (Step 1 Stage 3.4 `WCAG_CONTRAST_FAIL`) vẫn chạy — flag này chỉ tắt tầng schema-compose.
- Flag ON nhưng unit là **widget pure presentational** (không có interactive control, không layout ≥2 sibling) → skip với log: *"Unit không có bố cục đáng chấm thẩm mỹ. Step 4 skip."*
- Chỉ áp dụng `SCR-*` / `WGT-*` có `layout` tree. BE unit không tới được Step 4 (đã stop ở workflow Bước 1).

## 1. Load Persona

Adopt role **Visual Composition Auditor** tại `../agents/visual_composition_auditor.md`. Persona declare: role + constraints (zero-fabrication, no-hardcode, deterministic, hard-pass) + responsibilities + output format.

## 2. Inputs

- **`ui_schema_{id}.json`** — output Step 3 (post DSO approve + drift reconciled). Đọc `layout`, `data_bindings`, `state_machine`, `visual_intent` (nếu có), component selectors.
- **`master_token.json`** — canonical token values (spacing scale, color tiers, font size/weight). **Cùng nguồn Stage 5 dùng** → preview value = runtime value, không drift.
- **`components_metadata.json`** — component state token declarations (cho A7 affordance) + layout-primitive inputs.
- **`_shared/aesthetic-rubric.md`** — 7 trục A1–A7, SSoT chấm. Cite `best-practices.md` cho A5 contrast / A6 type ratio.

> **Backward-compat:** schema thiếu `visual_intent` (Step 3 Stage 4.7 skip / không capture) → derive `visual_intent` tối thiểu từ `layout` + `state_machine` + component intent (per persona §2), rồi chấm. KHÔNG fail vì thiếu key.

## 3. Pipeline

### Stage 4b.1: Token Resolution

Resolve mọi token reference trong schema sang giá trị thật **trong bộ nhớ / artifact preview** (KHÔNG ghi vào schema — Rule 4):

| Schema field | → Resolve |
|---|---|
| `layout[].props.gap/padding/margin` | px từ `global.spacing.scale` |
| `visual_intent.vertical_rhythm` / `grouping[].separation` | px từ spacing tier |
| Component fg/bg token (qua `components_metadata.json` → `master_token.json`) | hex |
| Text size/weight token | px + weight |

Token reference orphan / thiếu tier → mark `RESOLVE_GAP` cho trục liên quan (KHÔNG fabricate giá trị). Resolution table này = input cho lint.

### Stage 4b.2: Visual-Lint (7 trục)

Chấm 7 trục theo `aesthetic-rubric.md` §4 (SSoT cho tiêu chí — KHÔNG restate ở đây, tránh drift): A1 Alignment, A2 Spacing rhythm, A3 Visual hierarchy, A4 Density balance, A5 Color & contrast, A6 Typographic scale, A7 Affordance clarity. Mỗi trục emit finding `{ axis, verdict, reason, tokens, suggested_fix, kind }` (schema rubric §5).

**Verdict tổng (hard-pass):** PASS ⟺ cả 7 trục PASS. ≥1 FAIL → vào self-correct loop.

### Stage 4b.3: Self-Correct Loop (cap N=3)

```
round = 0
while verdict == FAIL and round < 3:
    round += 1
    for mỗi finding kind == AXIS_FAIL:
        apply suggested_fix → đổi token reference trong visual_intent (in-memory)
                              (deterministic pick: gần intent gốc → step nhỏ nhất → alphabetical)
    re-run Stage 4b.1 (resolve) + 4b.2 (lint)
    ghi round trace (token before→after, trục flip PASS) vào review log
```

- Chỉ fix `AXIS_FAIL` (fixable bằng đổi token reference). `RESOLVE_GAP` / `NEEDS_NEW_*` KHÔNG fix trong loop → escalate (§4).
- Loop hội tụ (PASS) → đi §4 PASS path. Hết N=3 vẫn FAIL → §4 HITL gate.
- Mỗi vòng deterministic: same input → same fix sequence (U4).

### Stage 4b.4: Resolve outcome

- **Mọi AXIS_FAIL flip PASS trong ≤3 vòng** → verdict PASS.
- **Còn AXIS_FAIL sau 3 vòng** → verdict FAIL → HITL visual gate (§4).
- **`RESOLVE_GAP` không fallback / `NEEDS_NEW_TOKEN` / `NEEDS_NEW_COMPONENT`** → escalate: emit gap note + hint `[NEW]` proposal qua cơ chế Step 1 (`/ntapp-ds-build-component` consume). Schema giữ `_rubric_score: "FAIL"` cho tới khi token/component bổ sung + re-run.

## 4. Decision Points

### PASS path
1. Patch `visual_intent` (token đã đổi qua self-correct) + `visual_intent._rubric_score = "PASS"` vào `ui_schema_{id}.json` (atomic, U1).
2. Emit `aesthetic_review_{id}.md` (template §5).
3. Schema sẵn sàng bàn giao Stage 5. Done.

### HITL VISUAL GATE (verdict FAIL sau N=3, hoặc escalate)

Present cho user — review content + USER MENU:

- **[A]** Accept fix-as-is — patch `visual_intent` với best-effort token + `_rubric_score = "FAIL"` + ghi trục FAIL còn lại vào review (ship có chủ ý, dev biết debt visual).
- **[O]** Override 1 trục FAIL → PASS với lý do (vd density intentional domain data-heavy) → ghi override vào review, set `_rubric_score = "PASS"`. **Ngoại lệ: A5 contrast < WCAG AA KHÔNG override** (a11y hard floor) — buộc đổi token hoặc proposal.
- **[P]** Proposal — trục cần token/component mới → quay lại Step 1, emit `[NEW]` vào `proposed_ds_updates.md`, re-run Step 4 sau khi `/ntapp-ds-build-component` apply.
- **[R]** Refine rubric — false-fail do tiêu chí quá cứng → sửa `_shared/aesthetic-rubric.md` (editable SSoT), re-run.
- **[S]** Stop — giữ schema không có `_rubric_score`, để debt cho HITL sau.

> Gate này chỉ mở khi rubric thực FAIL sau self-correct — KHÔNG thêm friction cho schema pass thẳng. Đây là HITL gate **mới** (visual), độc lập với HITL Step 2 (DS proposal approve) — giữ nguyên Step 2.

## 5. Output

- **`aesthetic_review_{id}.md`** — path: `{ui_schema_root}/{id}/aesthetic_review_{id}.md`. Structure:
  ```markdown
  # Aesthetic Review — {id}

  **Verdict:** PASS | FAIL
  **Rubric:** _shared/aesthetic-rubric.md v1.0
  **Self-correct rounds:** {0..3}

  ## 7-Axis Scorecard
  | Trục | Verdict | Reason | Tokens |
  |---|---|---|---|
  | A1 Alignment | PASS | ... | ... |
  | ... | ... | ... | ... |

  ## Self-Correct Trace
  - Round 1: A2 FAIL → đổi grouping[0].separation: scale.4(18px✗) → scale.6(24px✓) → A2 PASS
  - ...

  ## Remaining Findings / Escalation
  - (nếu có) A5 contrast FAIL → proposal [NEW] semantic token ...

  ## Override Log (nếu HITL override)
  - A4 density: override PASS — lý do: domain data-heavy, comfortable intentional.
  ```
- **Patch vào `ui_schema_{id}.json`** — `visual_intent` (token refs) + `visual_intent._rubric_score` (`"PASS"`/`"FAIL"`). KHÔNG chạm key khác. Schema vẫn 100% token reference (no hardcode).

## NEXT

`ui_schema_{id}.json` đã có `_rubric_score` → bàn giao Stage 5 với thẩm mỹ đã kiểm chứng deterministic.

Downstream không đổi:
- `proposed_ds_updates.md` có `[NEW]` (kể cả từ Step 4 escalation) → `/ntapp-ds-build-component` trước merge.
- Stage 4c (`/bmad-create-story`) consume schema làm input story scoping.
