---
# model: sonnet
# findingsOutput: '{output_folder}/_validation_temp/findings-risk-analysis.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
---

# Step V-08: Risk Analysis — Phân tích rủi ro

Weight: **0.8**

---

## 0. Load Context
Read `{contextFile}` → get `srs_path`, `kg.prd_key_sections`, `kg.brd_key_sections`. Use KG line ranges for all upstream document reads — do NOT read full PRD/BRD.

## 1. Flow completeness (flow-gap)

Kiểm tra mỗi SRS file có đủ luồng đối xứng:

| Create flow | Cần có | Check |
|---|---|---|
| Create order/policy | Cancel/Refund | |
| Payment initiate | Payment failure/timeout/refund | |
| Submit claim | Withdraw claim / Appeal rejected | |
| Grant permission | Revoke permission | |
| Subscribe | Unsubscribe | |
| Reserve (voucher) | Release/Expire | |

**Nếu thiếu luồng đối xứng → finding flow-gap**

Item ID: `exception_flows_handled`

---

## 2. External dependencies

- External APIs/services đã liệt kê?
- Có fallback strategy nếu external service down?
- Circuit breaker / retry logic defined?
- Timeout SLA defined?

Item ID: `external_deps_fallback`

---

## 3. Integration gaps

- Flow A → Flow B transition rõ ràng?
  - VD: FR-8 Purchase → FR-9 Payment trigger mechanism?
  - VD: FR-9 Payment → FR-10 Policy creation trigger?
- Event vs API call: architecture decision documented?

Item ID: `integration_gaps`

---

## 4. Data inconsistency risks

- Distributed transaction risks: nếu step A thành công nhưng step B thất bại?
- Eventual consistency windows: khi nào data nhất quán?
- Orphan records: payment success nhưng order không được tạo?
- Duplicate processing: nếu message consumed twice?

Item ID: `data_consistency_risks`

---

## 5. Scope creep

- Requirements trong SRS có vượt PRD scope không?
- Features mention nhưng không trong MVP?
  - VD: FR-5 precondition yêu cầu Viettel data nhưng MVP không dùng

Item ID: `scope_creep`

---

## 6. Assumptions & Concurrency

- Assumptions rõ ràng, đánh dấu cần confirm?
- Race condition scenarios:
  - Concurrent payment for same order?
  - Concurrent policy update?
  - Session TTL vs async processing time?

Item IDs: `assumptions_listed`, `concurrency_considered`

---

## 6b. Insurer rejection rollback

Kiểm tra mỗi flow có call external insurer (issue policy, renew, cancel, endorse):

- Có nhánh xử lý khi insurer từ chối không?
  - Issue: insurer từ chối phát hành → tiền KH đâu? hoàn tự động hay manual?
  - Renewal: insurer từ chối gia hạn → tiền đã trừ → rollback?
  - Cancel: insurer từ chối huỷ (VD: CTPL có quy trình riêng) → platform handle thế nào?
  - Endorse: insurer không phản hồi → endorsement treo mãi?
- **CRITICAL**: flow assume insurer luôn accept mà không có rejection/timeout path

Item ID: `insurer_rejection_rollback`

---

## 6c. Platform-Insurer sync gap risk

Kiểm tra nguyên tắc "async sync với insurer — failure không chặn KH":

- Nếu platform confirm thành công với KH trước khi insurer sync, phải định nghĩa:
  - Trong khoảng thời gian chờ sync, platform có đảm bảo quyền lợi cho KH không?
  - Nếu KH cần claim trong khoảng đó và insurer nói "không thấy HĐ" → ai chịu trách nhiệm?
  - Khi sync thất bại (insurer reject sau khi KH đã nhận confirm) → rollback strategy?
- **HIGH**: thiếu định nghĩa trách nhiệm trong sync gap → legal/claim dispute risk

Item ID: `platform_insurer_sync_gap_risk`

---

## 6d. Concurrent operation conflict

Kiểm tra các scenarios cho phép concurrent operations:

- Nếu nhiều endorsements được submit đồng thời cho cùng 1 HĐ:
  - Cho phép hay block? Rule rõ ràng?
  - Nếu đều approved, delta premium tính thế nào?
- Nếu endorsement đang pending mà HĐ sắp hết hạn:
  - Endorsement có bị auto-reject? Hay treo?
- KH có thể withdraw endorsement đang pending không? Endpoint nào?
- **MEDIUM**: thiếu conflict resolution rules → dev tự quyết định behavior → inconsistent

Item ID: `concurrent_operation_conflict`

---

## 6e. DLQ and alert action plan

Kiểm tra các DLQ và alert scenarios:

- Nếu message vào DLQ (data format sai, processing failed): có notify sender không? Cách nào?
  - Không notify → sender nghĩ thành công nhưng data bị lost
- Nếu webhook gửi thất bại N lần → EXPIRED → "alert Admin":
  - Admin nhận alert bằng cách nào? Bấm retry ở đâu? Quy trình xử lý cụ thể?
  - Nếu event bị mất là `policy.issued` → partner không biết → KH thắc mắc
- **HIGH**: alert không đi kèm action plan → incident kéo dài không cần thiết

Item ID: `dlq_alert_action_defined`

---

## 6f. Timeline & Effort Feasibility

Kiểm tra các yếu tố khiến SRS không khả thi về mặt timeline/effort:

- **Scope quá lớn cho 1 sprint**: UC nào có > 5 sub-flows hoặc > 10 business rules mà không được phân rã thành stories nhỏ hơn?
- **External dependency chưa confirmed**: Feature phụ thuộc API / contract bên ngoài (insurer, payment gateway, 3rd party) mà contract chưa ký hoặc API chưa stable → nếu SRS assume sẵn sàng → rủi ro
- **Dependency giữa FRs chưa chốt**: FR-X phụ thuộc FR-Y nhưng FR-Y không có SRS hoặc đang TBD → FR-X không thể implement đúng hạn
- **Assumption kỹ thuật quá rủi ro**: SRS assume sẵn có infrastructure (VD: Kafka cluster, 3rd party OAuth) mà thực tế chưa provision

**Không đánh giá absolute effort** (BA không phải PM). Chỉ flag khi:
- Có explicit blocker (dependency chưa sẵn sàng, contract chưa ký)
- Scope của 1 UC vượt quá giới hạn "có thể done in 1 sprint" rõ ràng

**Scoring:**
- Không có blocker dependency, scope hợp lý → 1.0
- 1 external dependency chưa confirmed nhưng low risk → 0.75
- Dependency quan trọng chưa chốt hoặc scope quá lớn → 0.5
- Blockers rõ ràng: contract chưa ký, FR phụ thuộc chưa có SRS → 0.25 (HIGH)

Item ID: `timeline_effort_feasible`

---

## 7. Edge-case failure risks

- Network timeout mid-transaction?
- Partial payment scenarios?
- User abandons flow mid-step — cleanup?
- System restart mid-processing?

Item ID: `edge_case_failure_risks`

---

## 8. Ghi Unresolved Questions

Trong quá trình review Risk, các câu hỏi cần PO/stakeholder quyết định → ghi vào section "7. Unresolved Questions" với format:

```markdown
| # | Severity | Dimension | Category | Question | Context | Related Files | Impact | Suggested Clarification |
```

Categories: flow-gap, ambiguity, cross-doc-conflict, domain-inference, missing-spec

---

## 9. Tính Risk dimension score

```
risk_score = round(sum(item_scores.values()) / 13 × 100, 1)
```

Canonical item IDs (N = 13, fixed):
`exception_flows_handled`, `external_deps_fallback`, `integration_gaps`, `data_consistency_risks`, `scope_creep`, `assumptions_listed`, `concurrency_considered`, `insurer_rejection_rollback`, `platform_insurer_sync_gap_risk`, `concurrent_operation_conflict`, `dlq_alert_action_defined`, `timeline_effort_feasible`, `edge_case_failure_risks`

⚠️ MANDATORY: N = 13 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

Weight: **0.8**

---

## 10. Append findings vào report

Append CRITICAL/HIGH → section "4. Critical & High Findings".
Append MEDIUM/LOW → section "5. Medium & Low Findings".
Append unresolved questions → section "7. Unresolved Questions".

Update frontmatter: thêm `step-v-08-risk-analysis` vào `stepsCompleted`.

---

## 9b. Domain Pattern Check

Read domain checklist if configured:
1. Check `CONTEXT.md` or `.vsaf/config.yaml` for `domain` field
2. If `domain` is set (e.g., `insurance`): read `../data/domain-checklists/{domain}.yaml`
3. If no `domain` field or file not found: skip domain-specific checks entirely

For each checklist item where `applies_to` includes any FR in scope:
1. Grep the SRS file(s) for keywords related to the check
2. If NOT found or insufficiently specified → create finding with:
   - item_id: checklist item `id` (e.g., `INS-CL-02`)
   - severity: from checklist
   - category: `domain-inference`
   - evidence: what was searched and not found
   - suggestion: what needs to be added
   - business_impact: derive from `regulation` field if present (WHO: Compliance/Legal, WHAT: Compliance risk, WHEN: Before Release)
3. Skip items where `applies_to` FRs are not in validation scope

---

## [NEW] Write Structured Findings
Write `{findingsOutput}`:
```yaml
dimension: risk_analysis
weight: 0.8
dimension_score: 0   # = round(sum(item_scores.values()) / 13 × 100, 1)
status: OK
findings: []
summary: {total: 0, critical: 0, high: 0, medium: 0, low: 0}
item_scores:
  exception_flows_handled: 0.0
  external_deps_fallback: 0.0
  integration_gaps: 0.0
  data_consistency_risks: 0.0
  scope_creep: 0.0
  assumptions_listed: 0.0
  concurrency_considered: 0.0
  insurer_rejection_rollback: 0.0
  platform_insurer_sync_gap_risk: 0.0
  concurrent_operation_conflict: 0.0
  dlq_alert_action_defined: 0.0
  timeline_effort_feasible: 0.0
  edge_case_failure_risks: 0.0
```

## 11. Menu

```
Risk Analysis Score: {X}% ({status}) [weight 0.8]
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}
Unresolved Questions: {count}

[C] Continue — Sang User Impact (Step V-09)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-09-user-impact.md`
