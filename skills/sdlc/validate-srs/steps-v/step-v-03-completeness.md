---
# model: opus
# findingsOutput: '{output_folder}/_validation_temp/findings-completeness.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
# grepPatterns: '../data/grep-patterns-srs.yaml'
---

# Step V-03: Completeness — Kiểm tra tính đầy đủ

---

## 1. Section Existence Check (Grep-only)

**Load context:** Read `{contextFile}` → get `srs_path`, `section_index`, `uc_cache`.
**Load patterns:** Read `{grepPatterns}` → get `srs_structure` pattern group.

**Use `section_index` from context.yaml first** (already built — no SRS read needed):
- Check each required section against the section_index titles
- If section_index is unavailable, run Grep using `srs_structure` patterns against `srs_path`

> **Template note (2026-04):** ERD section và Sequence Diagrams đã bị xóa khỏi template. API/DB/Kafka specs chuyển sang TSD. Template mới focus vào screen control tables + Activity Diagrams + Figma mapping + Gap Analysis. Không check `has_erd` và `has_uc_sequence` nữa.

Check presence of each item and record score:

| Item ID | Check | Pattern/Section | Score |
|---|---|---|---|
| has_overview | Section 1 "Mô tả chung" | section_overview | |
| has_use_case_summary | Bảng 1.1 UC Summary | section_uc_summary | |
| has_glossary | Section 1.2 Glossary | section_glossary | |
| has_references | Section 1.3 References | section_references | |
| has_uc_screens | Each UC có mục Màn hình (2.X.1) | section_uc_screens OR uc_cache | |
| has_screen_control_table | Each UC có bảng control (cột STT / Tên control / Loại control) | grep "Tên control\|Loại control" | |
| has_activity_diagram_per_uc | Each UC có Activity Diagram (@startuml block trong 2.X.2) | grep "@startuml UC-\|@startuml.*Activity" | |
| has_uc_flow_table | Each UC có bảng luồng (cột Bước / Đối tượng / Mô tả) | section_uc_flow_table OR uc_cache | |
| has_figma_mapping | Section 2 có bảng Figma mapping HOẶC explicit "chưa có Figma" / "Không có Figma" note | grep "Figma.*node\|chưa có Figma\|Không có Figma" | |
| has_error_codes | Section 3 "Danh sách mã lỗi đối tác trả về" | section_error_codes | |
| has_impact | Section 4 "Chức năng ảnh hưởng" | section_impact | |
| has_dependency_map | Section 4 có Dependency Map (@startuml component diagram) | grep "@startuml" within section 4 range | |
| has_business_rules | Section 5 Business Rules | section_business_rules | |
| has_nfrs | Section 6 Yêu cầu phi chức năng | section_nfr | |
| has_dependencies | Section 7 Ràng buộc / Giả định / Phụ thuộc | section_dependencies | |
| has_gap_analysis | Section 7.4 hoặc Section 9 có Gap Analysis table (cột Gap ID) | grep "Gap ID\|GA-[A-Z]" | |
| has_state_diagrams | Section 8 State Diagrams hoặc "Không áp dụng" note | section_state_diagrams | |
| has_traceability | Section 9 Mini-RTM | section_traceability | |
| has_edge_cases | "Luồng ngoại lệ" hoặc "EX" flows có mặt trong các UC | exception_flow pattern | |
| has_acceptance_criteria | Acceptance Criteria section | acceptance_criteria pattern | |
| has_open_questions_footer | Doc có "Các điểm cần Business confirm" footer | grep "cần Business confirm\|cần confirm" | |

Score: 1.0=present, 0.0=missing. Items "not applicable" (e.g., state diagrams cho FR không có entity lifecycle, Figma mapping cho backend-only FR) = skip from denominator.

Severity defaults khi thiếu:
- `has_screen_control_table`, `has_activity_diagram_per_uc` → MEDIUM
- `has_figma_mapping`, `has_dependency_map`, `has_gap_analysis` → MEDIUM
- `has_open_questions_footer` → LOW

---

## 2. Semantic completeness checks (LLM analysis)

Ngoài section existence, kiểm tra **nội dung** có đầy đủ:

### 2.1 UC coverage
- Đếm số UC trong bảng tóm tắt (1.1)
- Đếm số UC có section đặc tả chi tiết (2.X)
- Nếu thiếu UC spec → finding CRITICAL

### 2.2 Flow completeness
- Mỗi UC có: Precondition, Main flow, Alternative flow, Exception flow, Postcondition?
- Nếu chỉ có Main flow → CRITICAL
- Nếu thiếu Exception flow → HIGH

### 2.3 Cross-reference coverage (nếu có PRD)
- Đối chiếu FRs trong PRD với UCs trong SRS
- FR nào trong PRD chưa có UC tương ứng? → HIGH

### 2.4 Entity coverage
- Entities mention trong flow tables có trong ERD section 3 không?
- Entities trong ERD có mô tả trong bảng 3.2 không?

### 2.5 Downstream event consumer coverage
- Với mỗi event được publish trong flow (VD: `PaymentCompletedEvent`, `PolicyIssuedEvent`):
  - Có mô tả service nào consume event này không?
  - Có mô tả side effects quan trọng của downstream consumer không?
  - VD: payment SRS publish `PaymentCompletedEvent` nhưng không mô tả promotion-service consume event này để redeem voucher → thiếu side effect quan trọng
- Nếu downstream consumer quan trọng bị thiếu → HIGH

Item ID: `downstream_event_consumers`

### 2.6 Cancellation sub-flow by context
- Nếu feature có cooling-off period: có nhánh huỷ riêng cho trong-cooling-off vs ngoài-cooling-off?
  - Trong cooling-off: hoàn 100%, không bắt buộc lý do
  - Ngoài cooling-off: pro-rata, bắt buộc lý do
- Nếu chỉ có 1 luồng huỷ duy nhất → HIGH
- Cũng kiểm tra: khi có refund, ngày tính pro-rata có được xác định rõ không?
  - VD: tính từ ngày KH yêu cầu hay ngày insurer confirm? → Nếu không rõ → MEDIUM

Item ID: `cancellation_subflows_by_context`

### 2.7 PRD Acceptance Criteria coverage (via KG)

**Token-efficient:** Read PRD entity → find AC section line range → targeted read.

1. From KG fr-to-docs index: find PRD sections for this FR
2. Targeted read of PRD acceptance criteria for this FR
3. For each PRD acceptance criterion:
   - Is there a corresponding SRS UC or AC that covers it?
   - Map: PRD AC → SRS UC/AC
4. Finding: any PRD AC not covered → HIGH severity

Item ID: `prd_ac_coverage`

### 2.8 Derived-from Traceability — Two-Pass Invention Detection (CRITICAL)

**This is an Opus-level check. Two passes prevent false negatives.**

#### Pass 1 — Haiku extraction (exhaustive ID listing)

Run Grep to extract ALL formally defined SRS artifacts:

1. Grep `UC-[A-Z]{2,4}-\d{2}` in `srs_path` → extract unique UC IDs (e.g., UC-FR8-01)
2. Grep `BR-[A-Z]{2,4}-\d{3}|BR-\d{3}` in `srs_path` → extract unique BR IDs
3. Grep `NFR-|constraint:|Ràng buộc:` in `srs_path` → extract unique NFR/constraint IDs
4. Result: `extracted_uc_ids`, `extracted_br_ids`, `extracted_constraint_ids`

#### Pass 2 — Opus semantic judgment (traceability per extracted item)

Using KG pre-loaded data from `context.yaml` (`kg.prd_key_sections`, `kg.brd_key_sections`, `kg.fr_to_docs`):

For EACH UC ID in `extracted_uc_ids`:
- Can this UC's PURPOSE trace to a PRD FR or BRD requirement? (decomposition is OK — 1 PRD FR → many UCs)
- If NOT traceable → **CRITICAL: "Invented requirement — {UC_ID} has no upstream source in PRD/BRD"**
- Use targeted PRD/BRD reads via line ranges from context.yaml `kg` section

For EACH BR ID in `extracted_br_ids`:
- Is this BR derivable from BRD business rules or PRD acceptance criteria?
- If NOT traceable → **HIGH: "Untraceable business rule — {BR_ID} not found in BRD/PRD"**

For EACH constraint in `extracted_constraint_ids`:
- Is this from Architecture decisions or PRD NFR section?
- If NOT traceable → **MEDIUM: "Added constraint — not in Architecture/PRD"**

**Zero-miss guarantee:** Pass 1 (Grep) ensures every UC/BR is captured before Pass 2 (Opus) judges traceability. No LLM scanning of raw SRS text.

Item ID: `derived_from_traceability`

### 2.9 Role & Permission per UC

Kiểm tra mỗi UC có định nghĩa rõ role/permission không — riêng biệt với RBAC NFR ở V-06:

- Mỗi UC table có cột Actor hoặc ghi rõ actor role trong precondition không?
- Nếu có nhiều role có thể trigger cùng UC (VD: Admin vs Customer), có sub-flow riêng hoặc note rõ sự khác biệt không?
- Các action nhạy cảm (approve, cancel, refund, config) có ghi rõ role nào được phép không?
- Nếu SRS có Section 6 Business Rules hoặc bảng actor riêng, danh sách role có đầy đủ với thực tế không?

**Không yêu cầu bảng RACI đầy đủ.** Chỉ cần: mỗi UC không bị "ambiguous actor" — người đọc biết ngay ai có quyền trigger/thực hiện.

**Scoring:**
- Tất cả UC có actor rõ, role nhạy cảm đều có permission note → 1.0
- Phần lớn UC rõ, 1-2 action nhạy cảm thiếu permission boundary → 0.75
- Nhiều UC chỉ ghi "User" hoặc "System" không phân biệt role → 0.5
- Không có role/actor định nghĩa trong UC nào → 0.0 (CRITICAL)

Item ID: `role_permission_per_uc`

---

### 2.10 Input / Output / Validation Coverage per UC

Kiểm tra mỗi UC có mô tả đầy đủ input, output, và validation rules không.

> **Template note (2026-04):** Template mới embed validation trực tiếp vào cột Mô tả của screen control table (`**Validate:** • ...` inline), không còn separate input spec table. API request/response specs chuyển sang TSD.

**Input (screen control tables — Section 2.X.1):**
- Mỗi UC có màn hình → có bảng control với các cột: STT, Tên control, Loại control, Require, Maxlength, Giá trị mặc định, Mô tả
- Mỗi input control quan trọng (Text Input, Checkbox, Dropdown) có ghi Require (Bắt buộc/Tùy chọn)?
- Maxlength có điền cho Text Input không?

**Validation (inline trong cột Mô tả):**
- Có `**Validate:**` keyword trong Mô tả của các input controls không?
- Validation messages có tham chiếu đến Error Code trong Section 3 không?

**Output (flow table — Section 2.X.2):**
- Bảng luồng nghiệp vụ có mô tả kết quả sau khi UC thành công không?
- Cột "Bảng/Thực thể liên quan" có ghi entity nào bị tạo/cập nhật không?

**Scoring:**
- Screen control table đầy đủ + `**Validate:**` inline + error code reference → 1.0
- Có screen control table nhưng thiếu validate messages → 0.75
- Chỉ có flow table, không có screen control table (cho UC có màn hình) → 0.5
- Không có screen control table lẫn validate messages → 0.25 (HIGH)
- UC không có màn hình (backend-only) → skip item

Item ID: `input_output_validation_coverage`

---

### 2.11 Loop / Backward Flow Coverage

Kiểm tra các luồng có thể lặp lại hoặc quay lui mà SRS chưa xử lý:

**Loop flows (lặp lại trong cùng session):**
- User re-submit sau khi sửa lỗi (VD: form validation fail → sửa → submit lại)?
- User reload / refresh giữa chừng — state có được preserve không?
- Retry action sau timeout — có idempotency concern không?

**Backward flows (quay lui bước trước):**
- User bấm "Quay lại" từ bước N về bước N-1 — data có bị mất không?
- Checkout wizard: quay lại step 2 từ step 3 → có ảnh hưởng gì đến đơn đang tạo không?
- Multi-step process: nếu step giữa fail, có cần rollback toàn bộ hay partial?

**Dấu hiệu cần flag:**
- Flow chỉ có "happy path thẳng" mà không có nhánh cho re-try / back-navigation
- Business rule áp dụng tại step N phụ thuộc data step N-1, nhưng không có guard khi backward

**Scoring:**
- Tất cả loop/backward scenarios có explicit handling → 1.0
- Có note "user có thể quay lại" nhưng không mô tả data impact → 0.75
- Flow chỉ one-way, không đề cập loop/backward dù UC có multi-step → 0.5
- Wizard / multi-step hoàn toàn thiếu backward handling → 0.25 (HIGH)
- Không applicable (UC single-step) → skip

Item ID: `loop_backward_flow_handled`

---

### 2.12 Figma screen coverage (via figma-cache manifests)

1. Read Figma design references for screens mapping to this FR:
   - Use Figma MCP tools if available → filter screens matching this feature's FR ID
2. Read SRS screen mapping section (Mapping Figma ↔ SRS Screens table)
3. Cross-check:
   - Every SRS screen (SCR-XX-XX) has a mapped Figma page/node? → check manifest
   - Every Figma manifest screen for this FR has a corresponding SRS screen? → orphan design check
4. Finding: SRS screen without Figma design → MEDIUM; Figma screen without SRS → LOW (informational)

Item ID: `figma_screen_coverage`

---

## 3. Ghi findings

Với mỗi finding, ghi theo format:

```markdown
| # | Severity | Dimension | File | Item ID | Score | Evidence | Suggestion | Business Impact | Source |
```

Each finding MUST include `business_impact` with three sub-fields:
- **WHO**: Primary stakeholder affected (Dev, QA, PO, Ops, Customer)
- **WHAT**: Impact type (Blocked, Rework risk, UX degradation, Compliance risk)
- **WHEN**: When impact materializes (Before Sprint, During Sprint, After Release)
```

- Source = `auto` cho section checks, `llm` cho semantic analysis
- Score: 1.0 / 0.75 / 0.5 / 0.25 / 0.0

---

## 4. Tính Completeness dimension score

```
completeness_score = round(sum(item_scores.values()) / 29 × 100, 1)
```

Canonical item IDs (N = 29, fixed — excludes meta fields `uc_count`, `invented_requirements`):
`has_overview`, `has_use_case_summary`, `has_glossary`, `has_references`, `has_uc_screens`, `has_screen_control_table`, `has_activity_diagram_per_uc`, `has_uc_flow_table`, `has_figma_mapping`, `has_error_codes`, `has_impact`, `has_dependency_map`, `has_business_rules`, `has_nfrs`, `has_dependencies`, `has_gap_analysis`, `has_state_diagrams`, `has_traceability`, `has_edge_cases`, `has_acceptance_criteria`, `has_open_questions_footer`, `prd_ac_coverage`, `derived_from_traceability`, `role_permission_per_uc`, `input_output_validation_coverage`, `loop_backward_flow_handled`, `figma_screen_coverage`, `downstream_event_consumers`, `cancellation_subflows_by_context`

⚠️ MANDATORY: N = 29 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

Ghi nhận: `completeness_score = X%`, status = OK/WARN/FAIL

---

## 5. Append findings vào report

Append tất cả CRITICAL/HIGH findings vào section "4. Critical & High Findings" của report file.
Append MEDIUM/LOW findings vào section "5. Medium & Low Findings".

Update frontmatter: thêm `step-v-03-completeness` vào `stepsCompleted`.

---

## [NEW] Write Structured Findings

Write file `{findingsOutput}`:
```yaml
# findings-completeness.yaml — generated by step-v-03
# model: opus | weight: 1.0

dimension: completeness
weight: 1.0
dimension_score: 0   # = round(sum(item_scores.values()) / 29 × 100, 1)
status: OK  # OK | WARN | FAIL
findings: []
summary:
  total: 0
  critical: 0
  high: 0
  medium: 0
  low: 0
item_scores:
  has_overview: 0.0
  has_use_case_summary: 0.0
  has_glossary: 0.0
  has_references: 0.0
  has_uc_screens: 0.0
  has_screen_control_table: 0.0      # NEW — screen control table per UC
  has_activity_diagram_per_uc: 0.0   # NEW — Activity Diagram per UC (replaces has_uc_sequence)
  has_uc_flow_table: 0.0
  has_figma_mapping: 0.0             # NEW — Figma mapping or explicit N/A note
  has_error_codes: 0.0               # Section 3 (was Section 4)
  has_impact: 0.0                    # Section 4 (was Section 5)
  has_dependency_map: 0.0            # NEW — Dependency Map plantuml in Section 4
  has_business_rules: 0.0            # Section 5 (was Section 6)
  has_nfrs: 0.0                      # Section 6 (was Section 7)
  has_dependencies: 0.0              # Section 7 (was Section 8)
  has_gap_analysis: 0.0              # NEW — Gap Analysis table in Section 7.4 or Section 9
  has_state_diagrams: 0.0            # Section 8 (was Section 9)
  has_traceability: 0.0              # Section 9 (was Section 10)
  has_edge_cases: 0.0
  has_acceptance_criteria: 0.0
  has_open_questions_footer: 0.0     # NEW — "Các điểm cần Business confirm" footer
  prd_ac_coverage: 0.0
  derived_from_traceability: 0.0
  role_permission_per_uc: 0.0
  input_output_validation_coverage: 0.0
  loop_backward_flow_handled: 0.0
  figma_screen_coverage: 0.0
  downstream_event_consumers: 0.0
  cancellation_subflows_by_context: 0.0
  uc_count: 0
  invented_requirements: []    # list of UC/BR IDs flagged as invented
```

---

## 6. Menu

```
Completeness Score: {X}% ({status})
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

[C] Continue — Sang Consistency (Step V-04)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-04-consistency.md`
