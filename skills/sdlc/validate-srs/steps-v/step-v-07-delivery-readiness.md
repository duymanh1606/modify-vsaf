---
# model: sonnet
# findingsOutput: '{output_folder}/_validation_temp/findings-delivery-readiness.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
---

# Step V-07: Delivery Readiness — Đánh giá mức độ sẵn sàng triển khai

Weight: **1.0**

---

## 0. Load Context
Read `{contextFile}` → get `srs_path`, `kg.prd_key_sections`, `kg.brd_key_sections`. Use KG line ranges for all upstream document reads — do NOT read full PRD/BRD.

> **Template note (2026-04):** API endpoint specs, DB schema, và Kafka event payload schemas đã bị **xóa khỏi SRS** — những artifact này thuộc về TSD (Technical Specification Document). Không check `api_contracts_defined`, `db_schema_specified`, `event_payload_schema` nữa. Thay bằng các check mới phù hợp template.

## 1. TSD Delegation & Screen Validation

### 1.1 TSD Delegation noted

- SRS có ghi rõ "API design → TSD" / "DB schema → TSD" thay vì cố inline API/DB spec không?
- Nếu SRS có inline API endpoint table với full request/response schema → flag MEDIUM (wrong artifact level)

**Scoring:**
- Không có inline API/DB spec (clean) OR có note "see TSD" → 1.0
- Có mention API path nhưng không có full schema (ví dụ: trong flow step) → 0.75 (acceptable)
- Có inline API spec table với full schema → 0.5 (MEDIUM — belongs in TSD)

Item ID: `tsd_delegation_noted`

### 1.2 Screen Control Validation Complete

Áp dụng cho mỗi UC có màn hình B2C/Admin.

Kiểm tra bảng screen control (Section 2.X.1):
- Cột `Require` điền đầy đủ (Bắt buộc / Tùy chọn) cho mỗi control?
- Cột `Maxlength` điền cho Text Input controls?
- Cột `Mô tả` có `**Validate:**` với error messages cho các input controls quan trọng?
- Error messages trỏ đến mã lỗi trong Section 3 không?

**Scoring:**
- Đầy đủ Require + Maxlength + Validate messages + error code ref → 1.0
- Có Require/Maxlength nhưng thiếu Validate messages → 0.75
- Bảng control có cấu trúc nhưng nhiều ô trống / thiếu thông tin → 0.5
- Không có bảng control (cho UC có màn hình) → 0.0 (MEDIUM)
- UC không có màn hình (backend-only) → skip

Item ID: `screen_control_validation_complete`

---

## 3. Error Handling

### 3.1 Error code registry
- Có danh sách error codes trong Section 3 "Danh sách mã lỗi đối tác trả về"?
- Format nhất quán: STT, Bước, Trường hợp, Mã lỗi, Mã thông báo lỗi?
- Mapping rõ ràng với bước trong flow (cột "Bước" trỏ đến bước trong activity diagram)?

### 3.2 Central registry (cross-file)
- Có central error code registry trong System SRS?
- Format nhất quán giữa modules?

Item ID: `error_handling_defined`

---

## 4. State Machine Completeness

Kiểm tra state diagrams (Section 8):

- Tất cả states được define?
- Tất cả transitions có trigger/guard/action?
- Initial state → final state path exists?
- Orphan states (no transition in/out)?
- Missing transitions (VD: error recovery)?

Item ID: `state_machine_complete`

---

## 5. Integration Specs

Kiểm tra external integrations:

- External API: format, auth method, timeout, retry policy?
- Third-party services: contract defined?

Item ID: `integration_specs`

---

## 6. Validation Rules

Kiểm tra input field validation trong screen control tables (Section 2.X.1):

> **Template note (2026-04):** Validation rules được định nghĩa INLINE trong cột Mô tả của screen control table, không phải separate section.

- Mỗi input control quan trọng trong bảng màn hình có keyword `**Validate:**`?
- Các validation conditions: bỏ trống, sai định dạng, ngoài range, duplicate?
- Error messages rõ ràng và tham chiếu mã lỗi trong Section 3?
- Dropdown/Checkbox có ghi giá trị hợp lệ?

Item ID: `validation_rules`

---

## 7. Business Rules Implementability

- Mỗi BR có thể code trực tiếp mà không cần interpret?
- BR có đầy đủ: condition, action, exception?
- BR có tham chiếu nguồn (PRD, nghị định)?

Item ID: `br_implementable`

---

## 8. Test Readiness

Kiểm tra khả năng test:

- AC có trực tiếp map được sang test cases không?
- Có test data examples hoặc test scenarios?
- Edge cases đã được đặc tả đủ để viết tests?

**Scoring:**
- AC → test case mapping rõ ràng + test data → 1.0
- AC testable nhưng thiếu test data → 0.75
- AC khó map sang test cases (too vague) → 0.5
- Không có AC → 0.0

Item ID: `test_readiness`

---

## 8b. Async SLA & Escalation

Kiểm tra mỗi async operation (insurer callback, UW async, endorsement, webhook):

- Có SLA timeout rõ ràng? (VD: insurer phải trả kết quả trong 24h)
- Có hành vi khi timeout: tự huỷ, escalate, hay retry?
- Có escalation path khi quá SLA? Ai nhận alert? Ai xử lý?
- **HIGH**: async flow không có SLA → system không biết khi nào nên dừng chờ, KH/partner bị treo vô thời hạn
- VD: endorsement treo ở `INSURER_PROCESSING` mãi vì không có timeout → pattern lỗi phổ biến

**Scoring:**
- Tất cả async flows có SLA + escalation → 1.0
- Có SLA nhưng không có escalation/behavior → 0.5
- Không có SLA cho bất kỳ async flow nào → 0.0 (HIGH)

Item ID: `async_sla_defined`

---

## 8c. Auth Method Mapping

Áp dụng khi SRS là API gateway hoặc có nhiều loại integration partner (FR13 API Factory, FR8 Purchase Flow, FR10 Policy Lifecycle...).

> **Template note (2026-04):** Auth method mapping là TSD concern với feature SRS thông thường. Chỉ check ở SRS level khi FR có nhiều channels với auth khác nhau. Severity downgrade LOW (không còn MEDIUM) cho feature SRS.

- Có bảng mapping rõ ràng: channel/actor nào dùng auth method nào?
  - VD: Channel Partner → API Key, KH B2C → JWT, Insurer callback → HMAC, Internal service → mTLS
- **LOW**: thiếu mapping ở SRS level → acceptable nếu TSD sẽ define. Flag chỉ nếu FR có explicit multi-auth requirement

**Scoring:**
- Có mapping table đầy đủ → 1.0
- Có mention nhưng không có mapping → 0.5
- Không đề cập → 0.75 (skip nếu single-channel feature)

Item ID: `auth_method_mapping`

---

## 8d. Configurable Thresholds

Kiểm tra các thresholds/config values trong SRS:

- Hardcoded values có nên là configurable không?
  - VD: OCR confidence threshold 0.85 (có thể khác nhau per insurer/product)
  - VD: retry count, grace period duration, rate limit values
- Nếu value có thể hợp lệ ở mức khác nhau per product/insurer/context → phải đánh dấu configurable
- **MEDIUM**: threshold hardcode có thể tạo ra nhiều PRs/deploys khi business muốn thay đổi

Item ID: `configurable_thresholds_flagged`

---

## 8e. Error Code Edge-State Coverage

Kiểm tra section 4 (error codes) có cover các tình huống "cross-state edges":

- Có mã lỗi cho: cố thực hiện action X trên entity ở trạng thái Y không tương thích?
  - VD: gia hạn HĐ đã quá grace period → cần mã lỗi riêng, không dùng generic 400
  - VD: huỷ HĐ đang LAPSED, endorsement khi HĐ còn < N ngày
  - VD: quote expired rồi mới gọi purchase, purchase khi có session pending
- Đếm số state × action combinations quan trọng, kiểm tra coverage
- **MEDIUM**: thiếu mã lỗi cross-state → partner/KH nhận HTTP 400 chung chung, không xây được UX

Item ID: `error_code_edge_states`

---

## 9. Rollout & Migration

Kiểm tra deployment considerations từ Section 7.4 "Yêu cầu chuyển đổi":

- **Rollout strategy**: big bang, phased, feature flag?
- **Migration plan**: data migration scripts, backward compatibility?
- **Transition requirements table**: có TR-001, TR-002... hoặc ghi rõ "Không áp dụng — flow mới hoàn toàn"?
- **Feature flags**: toggle strategy cho new features?
- **Rollback plan**: nếu rollout thất bại?

**Scoring:**
- Có rollout strategy + migration plan + rollback → 1.0
- Có rollout strategy nhưng thiếu migration/rollback → 0.75
- Chỉ mention "cần migration" chung chung → 0.5
- Không đề cập → 0.0

Item ID: `rollout_migration_plan`

---

## 10. Tính Delivery Readiness dimension score

```
delivery_readiness_score = round(sum(item_scores.values()) / 13 × 100, 1)
```

Canonical item IDs (N = 13, fixed):
`tsd_delegation_noted`, `screen_control_validation_complete`, `error_handling_defined`, `state_machine_complete`, `integration_specs`, `validation_rules`, `br_implementable`, `test_readiness`, `async_sla_defined`, `auth_method_mapping`, `configurable_thresholds_flagged`, `error_code_edge_states`, `rollout_migration_plan`

⚠️ MANDATORY: N = 13 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

Weight: **1.0**

---

## 11. Append findings vào report

Append CRITICAL/HIGH → section "4. Critical & High Findings".
Append MEDIUM/LOW → section "5. Medium & Low Findings".

Update frontmatter: thêm `step-v-07-delivery-readiness` vào `stepsCompleted`.

---

## [NEW] Write Structured Findings
Write `{findingsOutput}`:
```yaml
dimension: delivery_readiness
weight: 1.0
dimension_score: 0   # = round(sum(item_scores.values()) / 13 × 100, 1)
status: OK
findings: []
summary: {total: 0, critical: 0, high: 0, medium: 0, low: 0}
item_scores:
  tsd_delegation_noted: 0.0
  screen_control_validation_complete: 0.0
  error_handling_defined: 0.0
  state_machine_complete: 0.0
  integration_specs: 0.0
  validation_rules: 0.0
  br_implementable: 0.0
  test_readiness: 0.0
  async_sla_defined: 0.0
  auth_method_mapping: 0.0
  configurable_thresholds_flagged: 0.0
  error_code_edge_states: 0.0
  rollout_migration_plan: 0.0
```

## 12. Menu

```
Delivery Readiness Score: {X}% ({status}) [weight 1.0]
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

[C] Continue — Sang Risk Analysis (Step V-08)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-08-risk-analysis.md`
