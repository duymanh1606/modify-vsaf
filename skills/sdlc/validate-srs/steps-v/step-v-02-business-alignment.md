---
# model: sonnet
# findingsOutput: '{output_folder}/_validation_temp/findings-business-alignment.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
---

# Step V-02: Business Alignment — Validate mục tiêu kinh doanh

Weight: **1.2** (highest — foundation of the entire SRS)

---

## 0. Load Context
Read `{contextFile}` → get `srs_path`, `kg.prd_key_sections`, `kg.brd_key_sections`. Use KG line ranges for all upstream document reads — do NOT read full PRD/BRD.

## 1. Problem Statement check

Kiểm tra mỗi SRS file:

- Có section mô tả **vấn đề cần giải quyết** (problem statement)?
- Problem statement rõ ràng: ai bị ảnh hưởng, ảnh hưởng như thế nào, tại sao cần giải quyết?
- Phân biệt được problem vs solution?

**Scoring:**
- Có rõ ràng, cụ thể → 1.0
- Có nhưng chung chung / generic → 0.5
- Chỉ có solution description, không có problem → 0.25
- Không có → 0.0

Item ID: `problem_statement_clear`

---

## 2. Business Goal & KPI check

Kiểm tra:

- Có **business goal** / mục tiêu kinh doanh cụ thể?
- Có **KPI hoặc success metrics** đo lường được?
  - Ví dụ: conversion rate, revenue target, NPS, error reduction %, SLA
- Metrics có SMART (Specific, Measurable, Achievable, Relevant, Time-bound)?

**Scoring:**
- Goal + KPI + SMART → 1.0
- Goal + KPI nhưng không SMART → 0.75
- Có goal nhưng không KPI → 0.5
- Chỉ mention feature, không có goal/KPI → 0.25
- Không có → 0.0

Item ID: `business_goal_kpi_defined`

---

## 3. Scope Alignment check

Kiểm tra SRS scope có aligned với business goal:

- Features trong SRS có trực tiếp address business goal không?
- Có features nào vượt quá / không liên quan business goal? → scope creep risk
- Có features nào cần thiết nhưng bị thiếu để đạt goal?

**Scoring:**
- Fully aligned, không gap, không excess → 1.0
- Mostly aligned, minor mismatch → 0.75
- Partial alignment, some gaps hoặc excess → 0.5
- Misaligned — features không rõ liên quan đến goal → 0.25
- Không thể đánh giá vì không có goal → 0.0

Item ID: `scope_aligned_with_goal`

---

## 4. Out-of-Scope Clarity check

Kiểm tra:

- Có section **ngoài phạm vi** (out-of-scope) rõ ràng?
- Out-of-scope có liệt kê các items explicitly?
- Có ranh giới rõ với các FRs liên quan (để tránh assumption)?

**Scoring:**
- Có explicit out-of-scope list + boundary rõ → 1.0
- Có out-of-scope nhưng generic → 0.75
- Implied nhưng không explicit → 0.5
- Không có → 0.0

Item ID: `out_of_scope_defined`

---

## 5. Stakeholder & Context check

Kiểm tra:

- Ai là stakeholders chính? (PO, Business, Dev, Legal, Partner)
- Context về regulatory / compliance requirements liên quan?
- Dependencies với business processes khác?

**Scoring:**
- Đầy đủ stakeholders + context → 1.0
- Có stakeholders nhưng thiếu context → 0.75
- Chỉ có actors technical, thiếu business stakeholders → 0.5
- Không có → 0.0

Item ID: `stakeholder_context_defined`

---

## 6. Business Rule assumptions check

Kiểm tra mỗi Business Rule (BR) trong SRS:

- BR có ghi nguồn xác nhận rõ ràng: PRD AC, BRD, nghị định, hoặc PO sign-off?
- **Không chấp nhận**: BR được viết sẵn trong luồng nhưng file ghi "câu hỏi cần confirm", "cần PO xác nhận", "giả định tạm", hoặc tương đương — đây là CONTRADICTION: luồng đã cứng hoá một quyết định chưa được chốt.
- BR có assumption ngầm (implicit business decision) mà không được ghi nhận?
  - VD: auto-cancel ngay sau grace period (không có final notice) — quyết định này từ đâu?
  - VD: không cho gia hạn khi có claim đang mở — quyết định này ai confirm?

**Scoring:**
- Tất cả BR có nguồn xác nhận rõ ràng → 1.0
- Phần lớn có nguồn, 1-2 BR implicit nhưng low-risk → 0.75
- Nhiều BR implicit, hoặc 1+ BR contradicts stated open question → 0.25
- Luồng đã cứng hoá quyết định chưa được business confirm → 0.0 (CRITICAL)

Item ID: `br_assumptions_confirmed`

---

## 6b. PRD Business Goal Alignment (cross-validation via KG)

**Token-efficient:** Read PRD entity → find FR section line range → targeted read.

1. From KG: read PRD entity `key_sections` to find the FR section matching this SRS's FR ID
2. Targeted read: `Read(prd_path, offset=section_start, limit=section_end-section_start)`
3. Compare:
   - SRS problem statement aligns with PRD FR description?
   - SRS business goals/KPIs match PRD acceptance criteria for this FR?
   - SRS scope matches PRD FR scope?

**Scoring:**
- Fully aligned with PRD → 1.0
- Minor misalignment → 0.75
- Significant gaps between SRS and PRD → 0.5
- Contradicts PRD → 0.25
- PRD has no matching FR → 0.0

Item ID: `prd_business_alignment`

## 6c. BRD Business Rule Coverage (cross-validation via KG)

**Token-efficient:** Read BRD entity → find FR section line range → targeted read.

1. From KG: read BRD entity `key_sections` to find the FR group matching this SRS's FR ID
2. Targeted read of BRD FR section
3. Compare:
   - BRD business rules for this FR are reflected in SRS Business Rules section?
   - BRD use case descriptions covered by SRS UCs?
   - Any BRD requirement silently dropped in SRS?

**Scoring:**
- All BRD requirements covered → 1.0
- Most covered, minor gaps → 0.75
- Significant BRD requirements missing from SRS → 0.5
- Major BRD requirements not addressed → 0.25
- Cannot assess (BRD has no matching section) → 0.0

Item ID: `brd_business_rule_coverage`

## 6d. Scope Invention Check (derived-from rule)

Check if SRS scope EXCEEDS what PRD/BRD authorize:

1. List all SRS use cases and features
2. For each: can it be derived from PRD FR scope + BRD business requirements?
3. Flag any SRS content that appears to be invented (not in upstream sources):
   - New actors not in PRD/BRD → CRITICAL
   - New business flows not in PRD user journeys → CRITICAL
   - Expanded scope beyond PRD FR boundaries → HIGH

Item ID: `scope_invention_check`

---

## 6f. Process Alignment — Current vs Future Process

Kiểm tra SRS có mô tả rõ sự chuyển đổi quy trình từ hiện tại sang tương lai:

- **AS-IS process**: SRS hoặc section phụ trợ có ghi nhận quy trình hiện tại (thủ công, tool cũ, pain point) không?
- **TO-BE process**: Flow mới trong SRS có giải quyết đúng pain point của AS-IS không?
- **Gap rõ ràng**: Sự khác biệt giữa AS-IS và TO-BE được phản ánh rõ trong scope + business rule không?
- **Stakeholder impact**: Người dùng hiện tại (ví dụ: nhân viên nghiệp vụ, agent) có quy trình thay đổi lớn nhưng SRS không mô tả transition plan / change impact?

**Không yêu cầu SRS phải có section riêng AS-IS/TO-BE.** Chỉ cần đảm bảo TO-BE flows phản ánh đúng bài toán thực tế, không viết trên giả định sai về trạng thái hiện tại.

**Dấu hiệu SAI:**
- SRS giả định flow đã hoàn toàn digital nhưng BRD ghi vẫn còn bước manual offline
- SRS bỏ qua bước hiện tại đang làm thủ công mà không nêu lý do
- TO-BE flow không address pain point nào được nêu trong BRD problem statement

**Scoring:**
- SRS phản ánh đúng TO-BE, có trace đến AS-IS pain points → 1.0
- TO-BE đúng nhưng không ghi rõ gap / change impact với AS-IS → 0.75
- TO-BE có chỗ giả định sai về quy trình hiện tại (minor) → 0.5
- TO-BE mâu thuẫn với AS-IS thực tế mô tả trong BRD → 0.25
- Không thể đánh giá (BRD không có mô tả quy trình hiện tại) → skip

Item ID: `process_alignment_current_future`

---

## 6e. Upstream Artifact Alignment (BRD/PRD vs SRS — general diff)

**Zero extra reads:** Reuses the BRD and PRD sections already loaded by 6b and 6c.

This check catches ANY structured artifact mismatch between upstream docs and SRS — not limited to state machines. It extracts all structured artifacts from both sides and runs a general diff.

#### Artifact Extraction Checklist

From the BRD and PRD sections already in context (loaded by 6b/6c), extract:

| # | Artifact Type | Extraction Method | SRS Counterpart |
|---|--------------|-------------------|-----------------|
| A1 | Entity status/lifecycle enum values | `entity_enum_values` pattern on BRD entity table | SRS Section 8 state diagram + entity tables |
| A2 | Entity field names (if in BRD/PRD only) | `entity_field_row` pattern on BRD entity table | SRS flow table "Bảng/Thực thể" column (no ERD in SRS) |
| A3 | State transitions + ordering | `plantuml_state` + `state_transition` patterns on BRD state diagram | SRS Section 8 PlantUML |
| A4 | Actor/role names | `actor_name_in_table` pattern on BRD requirement tables | SRS UC actor columns |
| A5 | Phase assignments (MVP/1.5/2) | `phase_assignment` pattern on BRD/PRD FR table | SRS scope section |
| A6 | Status names embedded in PRD ACs | `state_chain` pattern on PRD AC section | SRS canonical state names |
| A7 | Business rule references | BR-xxx pattern on BRD requirements | SRS Section 5 BR table |
| A8 | Vietnamese state flow text | `state_flow_text` pattern on BRD business reqs | SRS state diagram (translated) |

**Not all artifact types will be present for every FR.** Extract what's available; skip what's not.

#### Diff Algorithm

For each artifact type found in BOTH upstream and SRS:

1. **Build two lists:** `upstream_values` and `srs_values`
2. **Compute diff:**
   - **Additions** (in SRS but not upstream): may be legitimate decomposition or invention
   - **Removals** (in upstream but not SRS): may be a silent drop or intentional scope reduction
   - **Renames** (same position/semantics, different name): naming inconsistency
   - **Reorderings** (same items, different sequence): transition order conflict
   - **Type mismatches** (same field name, different data type): technical inconsistency

3. **Severity assignment** (LLM judgment per diff item):
   - Removal of upstream-defined item with no SRS note → **CRITICAL** (silent drop)
   - Addition in SRS with no upstream source → **HIGH** (invention — cross-ref with 6d)
   - Name mismatch for same concept → **HIGH** (causes Dev/QA confusion)
   - Transition order reversal → **HIGH** (changes business logic)
   - Data type mismatch → **HIGH** (runtime bugs)
   - Legitimate decomposition (1 upstream → N SRS) documented in SRS → **LOW**
   - Phase assignment difference → **MEDIUM** (planning confusion)
   - Actor name variant for same role → **MEDIUM**

#### What NOT to flag

- SRS naturally has more detail than BRD/PRD — more fields, more states, more transitions is expected
- Only flag when SRS CONTRADICTS, DROPS, or RENAMES without documentation
- PRD is user-facing; SRS has internal states — SRS having states not in PRD is normal

**Scoring:**
- All upstream artifacts traceable in SRS, no contradictions → 1.0
- Minor: 1-2 naming variants, documented decompositions → 0.75
- Significant: undocumented additions/renames, or type mismatches → 0.5
- Major: silently dropped upstream items or transition order conflicts → 0.25
- Fundamental contradictions (SRS says X, BRD says not-X) → 0.0

Item ID: `upstream_artifact_alignment`

---

## 7. Ghi findings

```markdown
| # | Severity | Dimension | File | Item ID | Score | Evidence | Suggestion | Business Impact | Source |
```

Each finding MUST include `business_impact` with three sub-fields:
- **WHO**: Primary stakeholder affected (Dev, QA, PO, Ops, Customer)
- **WHAT**: Impact type (Blocked, Rework risk, UX degradation, Compliance risk)
- **WHEN**: When impact materializes (Before Sprint, During Sprint, After Release)

Scoring scale: 1.0 / 0.75 / 0.5 / 0.25 / 0.0

---

## 8. Tính Business Alignment dimension score

```
business_alignment_score = round(sum(item_scores.values()) / 11 × 100, 1)
```

Canonical item IDs (N = 11, fixed):
`problem_statement_clear`, `business_goal_kpi_defined`, `scope_aligned_with_goal`, `out_of_scope_defined`, `stakeholder_context_defined`, `br_assumptions_confirmed`, `prd_business_alignment`, `brd_business_rule_coverage`, `scope_invention_check`, `process_alignment_current_future`, `upstream_artifact_alignment`

⚠️ MANDATORY: N = 11 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

Weight: **1.2**

---

## 9. Append findings vào report

Append CRITICAL/HIGH → section "4. Critical & High Findings".
Append MEDIUM/LOW → section "5. Medium & Low Findings".

Update frontmatter: thêm `step-v-02-business-alignment` vào `stepsCompleted`.

---

## [NEW] Write Structured Findings
Write `{findingsOutput}`:
```yaml
dimension: business_alignment
weight: 1.2
dimension_score: 0   # = round(sum(item_scores.values()) / 11 × 100, 1)
status: OK
findings: []
summary: {total: 0, critical: 0, high: 0, medium: 0, low: 0}
item_scores:
  problem_statement_clear: 0.0
  business_goal_kpi_defined: 0.0
  scope_aligned_with_goal: 0.0
  out_of_scope_defined: 0.0
  stakeholder_context_defined: 0.0
  br_assumptions_confirmed: 0.0
  prd_business_alignment: 0.0
  brd_business_rule_coverage: 0.0
  scope_invention_check: 0.0
  process_alignment_current_future: 0.0
  upstream_artifact_alignment: 0.0
```

## 10. Menu

```
Business Alignment Score: {X}% ({status}) [weight 1.2]
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

[C] Continue — Sang Completeness (Step V-03)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-03-completeness.md`
