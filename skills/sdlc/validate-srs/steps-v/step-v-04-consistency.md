---
# model: sonnet
# findingsOutput: '{output_folder}/_validation_temp/findings-consistency.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
# grepPatterns: '../data/grep-patterns-srs.yaml'
---

# Step V-04: Consistency — Kiểm tra tính nhất quán

---

## 1. Intra-file consistency (trong cùng 1 file)

Với mỗi SRS file, kiểm tra:

### 1.1 ID patterns

**Load context:** Read `{contextFile}` and `{grepPatterns}` → `id_patterns` group.

Run Grep using `id_patterns` patterns against `srs_path`:
- `uc_id_valid` pattern → find all UC IDs, check format UC-[A-Z]{2,4}-\d{2}
- `screen_id_valid` pattern → find all SCR IDs, check format SCR-[A-Z]{2,4}-\d{2}  
- `br_id_valid` pattern → find all BR IDs
- `id_lowercase_violation` pattern → any lowercase ID violations?

Cross-check BR IDs: every BR referenced in flow tables must appear in Section 5 summary (C-4 check):
1. Grep `BR-[A-Z]{2,4}-\d{2,3}-\d{2,3}|BR-[A-Z]{2,4}-\d{3}` in flow sections → extract all referenced BR IDs
2. Grep same pattern in Section 5 → extract all defined BR IDs
3. Referenced but not defined → MEDIUM finding
4. Defined but not referenced anywhere → LOW finding

Item IDs: `uc_id_pattern`, `screen_id_pattern`, `error_code_consistency`, `br_code_consistency`

### 1.2 Naming

> **Template note (2026-04):** ERD section đã bị xóa — không còn ERD để đối chiếu entity naming. Check entity naming INTRA-FILE: đối chiếu cột "Bảng/Thực thể liên quan" trong các flow tables với nhau và với Section 5 BRs.

- Actor names nhất quán giữa UC table và flow table (cột Đối tượng)? Đối chiếu với Section 1 row "Đối tượng sử dụng" (actor_naming)
- Entity names nhất quán GIỮA CÁC UC flow tables (cột "Bảng/Thực thể liên quan")? (entity_naming) — không cần ERD nữa
- State names nhất quán giữa State Diagram Section 8 và bảng mô tả? (state_naming)
- Screen control names dùng đúng prefix convention: `txt`, `btn`, `lbl`, `chk`, `lnk`, `ddl`, `dt`, `img`? (screen_control_naming)
- Steps trong Activity Diagram có đánh số `:(1)`, `:(2)` nhất quán không? (activity_diagram_step_numbering)

### 1.3 References

> **Template note (2026-04):** Error code format mới: `REC-NNN`, `PAY-NNN` hoặc HTTP status (401, 403...) — không còn dùng `ERR-XX-NNN`. Check format nhất quán TRONG file.

- Error codes trong Section 3 khớp với bước trong flow (cột "Bước" trong bảng mã lỗi trỏ đến step trong activity diagram)? (error_code_consistency)
- Error code format nhất quán trong cùng file? (VD: không trộn lẫn `REC-NNN` với `ERR-XX-NNN`) (error_code_consistency)
- BR codes trong Section 5 khớp với nội dung UC? (br_code_consistency)
- FR IDs trong Mini-RTM Section 9 khớp? (rtm_fr_match)

---

## 2. Cross-file consistency (so sánh giữa các files)

**Cross-file consistency checks LUÔN LUÔN thực hiện** — KG cung cấp references tự động, không cần batch/full scope.

### 2.1 Entity naming across files
- Cùng entity (VD: Policy) có cùng field names không? (data_model_fields)
  - Ví dụ: `policyId` vs `policy_id`, `userId` vs `customer_id`
- Naming convention nhất quán? camelCase vs snake_case? (entity_naming)

### 2.2 Entity naming across files (updated)

> **Template note (2026-04):** ERD và DB schema không còn trong SRS → không thể check field-level data model. Thay bằng entity name consistency ACROSS FILES: cùng entity phải dùng cùng tên table/collection.

- Cùng entity (VD: Policy, CustomerProfile) có cùng tên trong flow tables (cột "Bảng/Thực thể liên quan") giữa các SRS files không? (entity_naming)
  - VD: FR4 dùng "CustomerProfile", FR2 dùng "customer_profile" → naming inconsistency
- ~~canonical_model_match~~ — REMOVED (no ERD/data model in SRS)
- ~~pk_fk_type_consistent~~ — REMOVED (no field-level schema in SRS)
- ~~currency_type_convention~~ — REMOVED (no field-level schema in SRS)

### 2.3 API patterns

> **Template note (2026-04):** API endpoint specs không còn trong SRS. Check API path nhất quán chỉ khi API paths xuất hiện trong flow tables (cột Ghi chú hoặc ES: External System calls).

- API paths trong flow tables (nếu có) dùng prefix nhất quán `/api/v1/`? (api_naming_pattern)
- ~~api_contract_param_match~~ — REMOVED (API contracts in TSD, not SRS)

### 2.4 State machine alignment (cross_file_state_machine_match)

**Structured extraction approach (C-5) — more reliable than pure semantic comparison.**

#### Step 1: Extract state lists via Grep (Haiku-tier work)

From `{grepPatterns}` → `state_machine` pattern group:
1. Run `plantuml_state` pattern against SRS file → extract all state names from state diagrams
2. Run `state_transition` pattern → extract transition triggers
3. Build `srs_states` list from extracted names

From System SRS (use line range from `context.yaml` `kg.arch_key_sections` or targeted read of state section):
4. Extract `system_states` list the same way

#### Step 2: Compare YAML lists (Sonnet judgment)

Compare `srs_states` vs `system_states`:
- States in SRS but not in System SRS → document in finding (may be legitimate decomposition)
- States in System SRS but not in feature SRS → check if applicable to this FR
- Transition triggers inconsistent → HIGH finding
- State count discrepancy > 2× → CRITICAL

This replaces full semantic comparison with structured list comparison.

Item IDs: `state_naming`, `cross_file_state_machine_match`

### 2.5 Service ownership alignment (service_ownership_consistent)
- Với mỗi entity/resource quan trọng (voucher, promotion, claim, policy):
  - Tìm tất cả files đề cập entity này và xem service nào được giao ownership
  - **CRITICAL** nếu: File A giao voucher validate/reserve cho pricing-service, nhưng File B+C giao cho promotion-service
  - Đây là lỗi boundary thực sự, không phải naming — có thể dẫn đến implement sai service
- Cách check: search tên entity + action (validate, reserve, apply) → xem subject service

### 2.8 State name uc-vs-diagram alignment (state_name_uc_vs_diagram)
- So sánh tên states được dùng trong UC flow steps với tên states trong State Diagram (section 9):
  - Mỗi status/state xuất hiện trong flow steps phải có node tương ứng trong diagram
  - **CRITICAL**: flow steps dùng `PENDING_ACTIVATION` nhưng diagram chỉ có `PENDING_ISSUANCE` → dev không biết map vào đâu
  - Xây danh sách states từ flow steps → đối chiếu với diagram nodes
- Chú ý: đây khác với state_naming check (mục 1.2) vốn chỉ check naming pattern

### 2.9 Referenced FR existence check (referenced_fr_exists)
- Nếu SRS tham chiếu FR khác (VD: "cross-insurer fallback (FR29)", "see FR-15 for details"):
  - FR được tham chiếu phải tồn tại trong danh sách FR đã định nghĩa trong project
  - **HIGH**: tham chiếu FR không tồn tại → feature đó là out-of-scope thực chất, cần ghi rõ
  - Cách check: extract tất cả FR references → đối chiếu với FR inventory (FR1–FR17 hoặc bất kỳ range nào project đang dùng)

### 2.10 Technology stack alignment (tech_stack_consistent)
- Database technology nhất quán cho cùng entity/module? (tech_stack_consistent)
  - VD: MongoDB vs MariaDB vs PostgreSQL cho cùng entity → CRITICAL
  - Message broker: Kafka vs RabbitMQ → phải nhất quán
  - Cache: Redis vs Memcached → phải nhất quán
- Thuật ngữ thống nhất, không dùng lẫn lộn? (terminology_consistent)
  - VD: "Khách hàng" vs "Customer" vs "User" cho cùng concept

### 2.11 Architecture alignment (MANDATORY via KG)

**Token-efficient:** Read Architecture entity → find service catalog section → targeted read.

1. From KG: read architecture entity `key_sections` to find "Service Catalog" or "Technology Stack" sections
2. From upstream context: check service/component definitions in `.vsaf/docs/features/{feature-name}/03-adr.md` or `graphify-out/graph.json`
3. Targeted read of architecture sections
4. Compare:
   - SRS tech stack (DB, framework, broker) matches architecture decisions?
   - SRS API patterns match architecture API conventions?
   - SRS service boundaries align with architecture service mapping?

Item ID: `architecture_alignment`
Scoring: 1.0 (aligned) / 0.75 (minor deviation) / 0.5 (significant mismatch) / 0.0 (contradicts)

### 2.12 Architecture Service Boundary Check (C-2 — new check)

**Zero extra token cost — pure Grep + KG lookup.**

1. Load `arch_services` from `context.yaml` → list of valid service names (e.g., `ntbh-payment-service`, `ntbh-policy-service`)
2. Run Grep `service_references` patterns from `{grepPatterns}` against `srs_path`:
   - `service_name` pattern → find all service references in SRS flows/diagrams
   - `infra_component` pattern → find Kafka, Redis, Keycloak, Kong references
3. For each service name found in SRS:
   - Is it in `arch_services` list? → OK
   - Not in list → **CRITICAL: "SRS references non-existent service {name} — not in Architecture service catalog"**
4. For each infra component found in SRS:
   - Is it in the approved tech stack (from Architecture entity)? → OK
   - Not approved → **HIGH: "Unapproved infrastructure component {name}"**

Item ID: `architecture_alignment` (extends existing check in 2.11)

### 2.13 Error Code Completeness Cross-check (C-3 — new check)

**Zero extra token cost — pure Grep.**

1. Grep Section 3 (error codes section, use `section_error_codes` line range from `section_index`):
   - Extract all error code IDs defined in section 4
2. For each error code ID, Grep full `srs_path` for that ID:
   - Appears in at least one flow step → OK
   - Never referenced in flows → MEDIUM: "Error code {ID} defined in Section 4 but never referenced in flow steps"
3. Reverse check: Grep flow tables for any error code pattern not in Section 4:
   - Referenced in flows but not defined → HIGH: "Error code {code} referenced in flows but not defined in Section 4"

Item ID: `error_code_consistency` (enhances existing check)

### 2.14 Upstream structural consistency (upstream_structural_consistency)

**Complements all other cross-file checks in Section 2.**
Those checks validate SRS ↔ System SRS and SRS ↔ Architecture for tech stack/service boundaries.
This check validates SRS ↔ BRD/PRD for structural artifact consistency (state machines, entity schemas, events, API paths).

**Zero extra reads:** Reuses BRD/PRD/Architecture sections already loaded by V-02 context or V-04's architecture checks. If context.yaml contains `kg.brd_key_sections` and `kg.prd_key_sections`, use those line ranges. Otherwise, this check is skipped (KG not available).

#### Artifact Extraction

> **Template note (2026-04):** S3 (Kafka event coverage), S4 (Entity field schema), S5 (API endpoint paths) đã bị xóa — những artifact này không còn trong SRS. Chỉ giữ S1, S2, S6 (state machine + AC state names).

From upstream docs already in context, extract and compare against SRS:

| # | Check | Upstream Source | SRS Source | Diff Type |
|---|-------|----------------|------------|-----------|
| S1 | State machine states | BRD PlantUML `state` declarations | SRS Section 8 PlantUML states | Set diff: additions, removals |
| S2 | State transitions + order | BRD PlantUML `-->` arrows | SRS PlantUML `-->` arrows | Order comparison |
| ~~S3~~ | ~~Kafka event coverage~~ | ~~REMOVED~~ | ~~REMOVED~~ | ~~REMOVED~~ |
| ~~S4~~ | ~~Entity field schema~~ | ~~REMOVED~~ | ~~REMOVED~~ | ~~REMOVED~~ |
| ~~S5~~ | ~~API endpoint paths~~ | ~~REMOVED~~ | ~~REMOVED~~ | ~~REMOVED~~ |
| S6 | PRD AC state names | PRD AC text (`state_chain` pattern) | SRS canonical state names | Name alignment |

#### Diff Logic (same for all artifact types)

For each artifact type where both upstream and SRS have data:

1. Extract `upstream_list` and `srs_list`
2. Report:
   - **In upstream, NOT in SRS** → severity depends on type:
     - State/field dropped → CRITICAL
     - Event not covered → HIGH
     - API path missing → HIGH
   - **In SRS, NOT in upstream** → typically OK (SRS refines), but flag if:
     - Entirely new entity/state with no upstream trace → HIGH (possible invention)
     - New API endpoint not in Architecture → MEDIUM
   - **Same item, different name** → HIGH (naming inconsistency)
   - **Same items, different order** → HIGH for transitions (logic change); LOW for fields (cosmetic)
   - **Same field, different type** → HIGH (e.g., DECIMAL vs BIGINT)

3. For each flagged item, include in finding:
   - `upstream_source`: which doc and line
   - `srs_source`: which section and line
   - `diff_type`: addition | removal | rename | reorder | type_mismatch
   - `severity`: per rules above
   - `suggestion`: specific fix (e.g., "Align SRS state name to BRD: rename COMPLETED → PAID, or document the split in SRS changelog")

#### Interaction with V-02 6e

V-02 `upstream_artifact_alignment` checks business-level alignment (are the right things specified?).
V-04 `upstream_structural_consistency` checks structural-level consistency (are they specified the same way?).

Example: BRD says entity has field `claim_number` (VARCHAR 50). SRS has `claim_reference` (VARCHAR 50).
- V-02 asks: "Is this the same business concept or a new field?" → Business alignment question
- V-04 asks: "These are different field names for similar purpose — is naming consistent?" → Structural consistency question

Both checks may flag the same artifact from different angles. This is intentional — they serve different reviewers (BA vs Dev/Architect).

**Scoring:**
- All structural artifacts consistent across upstream and SRS → 1.0
- Minor: 1-2 naming variants with clear semantic equivalence → 0.75
- Significant: field type mismatches, missing events, or >3 naming divergences → 0.5
- Major: dropped upstream states/fields, reversed transitions → 0.25
- Fundamental: SRS structure contradicts upstream (different entity, different lifecycle) → 0.0

Item ID: `upstream_structural_consistency`

---

## 3. Ghi findings

Format:
```markdown
| # | Severity | Dimension | File | Item ID | Score | Evidence | Suggestion | Business Impact | Source |
```

Each finding MUST include `business_impact` with three sub-fields:
- **WHO**: Primary stakeholder affected (Dev, QA, PO, Ops, Customer)
- **WHAT**: Impact type (Blocked, Rework risk, UX degradation, Compliance risk)
- **WHEN**: When impact materializes (Before Sprint, During Sprint, After Release)
```

Ghi rõ file(s) liên quan khi cross-file: `file1 AND file2`

---

## 4. Tính Consistency dimension score

```
consistency_score = round(sum(item_scores.values()) / 19 × 100, 1)
```

Canonical item IDs (N = 19, fixed):
`uc_id_pattern`, `screen_id_pattern`, `error_code_consistency`, `br_code_consistency`, `actor_naming`, `entity_naming`, `state_naming`, `screen_control_naming`, `activity_diagram_step_numbering`, `rtm_fr_match`, `api_naming_pattern`, `cross_file_state_machine_match`, `service_ownership_consistent`, `state_name_uc_vs_diagram`, `referenced_fr_exists`, `tech_stack_consistent`, `terminology_consistent`, `architecture_alignment`, `upstream_structural_consistency`

⚠️ MANDATORY: N = 19 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

---

## 5. Append findings vào report

Append CRITICAL/HIGH → section "4. Critical & High Findings". Append MEDIUM/LOW → section "5. Medium & Low Findings".

Update frontmatter: thêm `step-v-04-consistency` vào `stepsCompleted`.

---

## [NEW] Write Structured Findings

Write file `{findingsOutput}`:
```yaml
# findings-consistency.yaml — generated by step-v-04
# model: sonnet | weight: 1.0

dimension: consistency
weight: 1.0
dimension_score: 0
status: OK
findings: []
summary:
  total: 0
  critical: 0
  high: 0
  medium: 0
  low: 0
item_scores:
  uc_id_pattern: 0.0
  screen_id_pattern: 0.0
  error_code_consistency: 0.0
  br_code_consistency: 0.0
  actor_naming: 0.0
  entity_naming: 0.0
  state_naming: 0.0
  screen_control_naming: 0.0
  activity_diagram_step_numbering: 0.0
  rtm_fr_match: 0.0
  api_naming_pattern: 0.0
  cross_file_state_machine_match: 0.0
  service_ownership_consistent: 0.0
  state_name_uc_vs_diagram: 0.0
  referenced_fr_exists: 0.0
  tech_stack_consistent: 0.0
  terminology_consistent: 0.0
  architecture_alignment: 0.0
  upstream_structural_consistency: 0.0
new_checks:
  service_boundary_violations: []   # list of unauthorized service references
  orphan_error_codes: []            # error codes defined but never referenced
  undefined_error_codes: []         # error codes referenced but not defined
  orphan_br_ids: []                 # BR IDs defined but not referenced in flows
  upstream_diffs: []   # list of {artifact_type, diff_type, upstream_source, upstream_value, srs_value, severity}
```

---

## 6. Menu

```
Consistency Score: {X}% ({status})
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

[C] Continue — Sang Quality (Step V-05)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-05-quality.md`
