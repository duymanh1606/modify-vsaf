# SRS Review — Glossary & Mô tả

---

## 1. REVIEW DIMENSIONS — Các chiều đánh giá

| Dimension | Mô tả | Weight |
|---|---|---|
| Completeness | Kiểm tra tính đầy đủ: có Overview, Use Cases, AC, NFRs, ERD, Business Rules, Error Codes, Dependencies, Traceability không? | 1.0 |
| Consistency | Kiểm tra tính nhất quán giữa các file: entity naming, UC ID prefix, state machine, data model, API patterns, terminology. | 1.0 |
| Quality | Kiểm tra chất lượng viết: ngôn ngữ mơ hồ (TBD, có thể), testability, AC format, duplicate requirements, scope clarity. | 1.0 |
| Readiness | Đánh giá mức độ sẵn sàng implement: API contracts, DB schema, error codes, state machines, integration specs, tech stack. | 1.0 |
| Risk | Đánh giá rủi ro kinh doanh: flow completeness (create→delete), external dependencies, integration gaps, scope creep, assumptions. | 0.8 |
| User Impact | Đánh giá tác động người dùng: persona coverage, journey completeness, error UX, onboarding, accessibility. | 0.7 |

---

## 2. SEVERITY LEVELS — Mức độ nghiêm trọng

| Severity | Mô tả | Hành động |
|---|---|---|
| CRITICAL | Block implementation — dev không thể implement mà không có câu trả lời hoặc spec bổ sung. | Phải sửa TRƯỚC khi bắt đầu Sprint |
| HIGH | Nên clarify sớm — có thể implement nhưng risk rework hoặc bugs. | Nên sửa trong Sprint 1 |
| MEDIUM | Nice to fix — không block nhưng improve quality, UX, maintainability. | Phân bổ vào Sprint 2 |
| LOW | Minor — pass hoặc cải thiện nhỏ. | Fix khi có thời gian |

---

## 3. QUESTION CATEGORIES — Phân loại câu hỏi

| Category | Mô tả | Ví dụ |
|---|---|---|
| flow-gap | Thiếu luồng xử lý đối xứng/bổ sung (có create nhưng thiếu delete/cancel/refund). | Payment có create nhưng thiếu refund. Policy có cancel nhưng thiếu reinstate. |
| ambiguity | Requirement mơ hồ, cần PO/stakeholder quyết định. | Figma cho skip CCCD, SRS yêu cầu bắt buộc — chọn cái nào? |
| cross-doc-conflict | Mâu thuẫn giữa PRD/System spec/SRS feature files. | System spec dùng UC-IP cho FR-8, SRS FR-8 dùng UC-PU. |
| domain-inference | Từ domain knowledge, thiếu flow thường gặp trong ngành bảo hiểm. | Grace period: claims allowed hay không? Endorsement reject: resubmit được không? |
| missing-spec | Flow/entity đề cập nhưng thiếu spec chi tiết để implement. | Kafka events mention xuyên suốt nhưng không có payload schema. |

---

## 4. ITEM IDs — Mã định danh findings

| Pattern | Mô tả | Ví dụ |
|---|---|---|
| has_* | Auto-check: kiểm tra section/content tồn tại trong document. | has_overview, has_nfrs, has_traceability, has_dependencies |
| no_ambiguous_language | Auto-check: tìm từ mơ hồ (TBD, should, có thể, etc.). | Tìm thấy 15 ambiguous terms trong prd.md |
| entity_naming | Auto-check: entity naming consistency across files. | entity_naming — kiểm tra cùng concept dùng cùng tên |
| deployment_requirements | Auto-check: có section Deployment/Infrastructure không. | Không tìm thấy section Deployment trong PRD |
| dependency_risk | Auto-check: external dependencies documented. | Không có section Dependencies/Third-party |
| acceptance_criteria_format | Auto-check: AC theo format Given/When/Then. | AC không có GWT format |
| clear_scope | Auto-check: có section phạm vi/ngoài phạm vi. | Không có section In-scope/Out-of-scope |
| no_duplicate_requirements | Auto-check: requirements trùng lặp giữa các file. | Consent spec overlap giữa FR-1 và FR-15 |
| api_contracts_defined | LLM-check: API contracts đầy đủ request/response schema. | Endpoints listed nhưng thiếu JSON schema |
| api_naming_pattern | LLM-check: API prefix nhất quán. | FR10 dùng /v1/ trong khi các FR khác dùng /api/v1/ |
| db_schema_specified | LLM-check: DB schema đầy đủ field types, PKs, FKs. | BIGINT PKs vs UUID v7 conflict |
| data_model_fields | LLM-check: entity fields nhất quán giữa các files. | Policy entity 13 fields vs 9 fields giữa FR10 và System |
| no_contradictions | LLM-check: không có mâu thuẫn nội dung giữa các files. | State machine 14 states vs 7 states |
| terminology_consistent | LLM-check: thuật ngữ dùng nhất quán. | Customer vs User vs Khách hàng cho cùng concept |
| error_handling_defined | LLM-check: error handling đầy đủ. | Không có central error code registry |
| uc-id-*-mismatch | LLM-check: UC ID prefix không khớp giữa System spec và SRS file. | uc-id-purchase-mismatch: UC-IP vs UC-PU |
| policy-* | LLM-check: Policy lifecycle/state machine issues. | policy-creation-flow-inconsistency |
| srs-completeness-* | LLM-check: SRS file completeness per module. | srs-completeness-fr9: FR-9 thiếu ERD |
| llm-* | LLM-check: semantic analysis results. | llm-missing-refund-spec, llm-testability-uw-timeout |
| risk-* | LLM-check: business risk assessment. | risk-refund-flow-missing |
| ui-* | LLM-check: user impact assessment. | ui-accessibility-missing |
| tech_stack_consistent | LLM-check: DB/broker/cache technology nhất quán giữa files. | MongoDB vs MariaDB vs PostgreSQL cho cùng entity |
| pk_fk_type_consistent | LLM-check: PK/FK type nhất quán theo canonical model. | BIGINT PKs vs UUID v7 conflict |
| canonical_model_match | LLM-check: feature SRS fields khớp System SRS canonical model. | Policy entity 13 fields (FR10) vs 9 fields (System) |
| currency_type_convention | LLM-check: currency fields thống nhất convention. | DECIMAL vs BIGINT (đơn vị nhỏ nhất) |
| cross_file_state_machine_match | LLM-check: state machine feature SRS khớp System SRS. | Claim 14 states (FR11) vs 7 states (System) |
| event_payload_schema | LLM-check: Kafka/event payload có schema đầy đủ. | Event mentioned nhưng không có payload fields/types |
| *-implementation-ready | LLM-check: module readiness to implement. | fr1-implementation-ready |
| br_assumptions_confirmed | LLM-check (V-02): BR không được viết dựa trên quyết định business chưa được confirm. Contradiction: luồng đã cứng hoá nhưng file ghi "câu hỏi cần confirm". | BR-PL-023 viết sẵn grace period behavior nhưng file ghi "cần business confirm" |
| downstream_event_consumers | LLM-check (V-03): mỗi event được publish phải có downstream consumers và side effects được mô tả. | PaymentCompletedEvent không có promotion-service consumer |
| cancellation_subflows_by_context | LLM-check (V-03): nếu có cooling-off concept, phải có nhánh huỷ riêng (trong/ngoài cooling-off) và ngày tính refund phải rõ ràng. | Chỉ có 1 luồng huỷ không phân biệt cooling-off |
| service_ownership_consistent | LLM-check (V-04): entity/resource phải được giao cho cùng service nhất quán cross-file. | Voucher validate: pricing-service (FR8) vs promotion-service (FR7, FR17) |
| api_contract_param_match | LLM-check (V-04): params trong SRS call phải match params required trong API contract. | FR7 gọi /vouchers/best?productId={id} nhưng contract yêu cầu userId+productId+premium |
| currency_unit_intra_section | LLM-check (V-04): không trộn đơn vị tiền trong cùng entity/breakdown section. | discount_amount=50000 đồng cạnh premium=5000000 cents trong cùng entity |
| state_name_uc_vs_diagram | LLM-check (V-04): state names trong UC flow steps phải khớp với nodes trong State Diagram. | UC dùng PENDING_ACTIVATION nhưng diagram chỉ có PENDING_ISSUANCE |
| referenced_fr_exists | LLM-check (V-04): FR được tham chiếu trong SRS phải tồn tại trong FR inventory. | "cross-insurer fallback (FR29)" — FR29 không tồn tại |
| upstream_artifact_alignment | LLM-check (V-02): Mọi structured artifact trong SRS (entity enums, fields, actors, phases, BR references) phải traceable về BRD/PRD. Diff: additions, removals, renames, type mismatches. Silent drops = CRITICAL, inventions = HIGH, naming divergence = HIGH. | BRD: 7 claim states (PAID); SRS: 11 states (thêm DISPUTED, tách PAID→DISBURSING+COMPLETED) — SRS refines nhưng phải documented |
| upstream_structural_consistency | LLM-check (V-04): SRS structural artifacts (state machines, transitions, field schemas, API paths, Kafka events) phải consistent với BRD state diagrams + Architecture event catalog + PRD AC state names. Transition order conflicts, field type mismatches, event coverage gaps = HIGH+. | BRD: UNDER_REVIEW→PROCESSING; SRS: PROCESSING→UNDER_REVIEW (reversed). PRD AC: DOCUMENTS_PENDING; SRS: DOCS_REQUIRED (name mismatch) |
| rules_self_explanatory | LLM-check (V-05): mỗi rule phải self-explanatory không cần PO interpret, tránh undefined terms. | "not exposed until acceptance" — acceptance không được định nghĩa |
| async_sla_defined | LLM-check (V-07): mỗi async flow phải có SLA timeout + escalation path + behavior khi quá SLA. | Endorsement treo ở INSURER_PROCESSING vô thời hạn vì không có timeout |
| auth_method_mapping | LLM-check (V-07): API spec phải có bảng mapping actor/channel → auth method. | "5 phương thức xác thực" nhưng không nói ai dùng cái nào |
| configurable_thresholds_flagged | LLM-check (V-07): threshold/config values phải đánh dấu configurable, không hardcode trong spec. | OCR threshold 0.85 hardcode thay vì configurable per insurer |
| error_code_edge_states | LLM-check (V-07): phải có error codes cho cross-state edge cases (action X trên entity ở state Y). | Không có mã lỗi cho: gia hạn HĐ đã quá grace, huỷ HĐ đang LAPSED, quote expired |
| insurer_rejection_rollback | LLM-check (V-08): mỗi flow gọi insurer phải có nhánh insurer từ chối + rollback. | Renewal assume insurer luôn accept — không có rejection path |
| platform_insurer_sync_gap_risk | LLM-check (V-08): khi platform confirm trước insurer sync, phải định nghĩa trách nhiệm trong gap. | KH nhận "kích hoạt thành công" nhưng insurer chưa ghi nhận — claim trong 15 phút đó? |
| concurrent_operation_conflict | LLM-check (V-08): nếu cho phép concurrent ops, phải có conflict resolution rule. | Nhiều endorsements đồng thời — delta premium tính thế nào? |
| dlq_alert_action_defined | LLM-check (V-08): DLQ/webhook failure phải có action plan, không chỉ "alert admin". | Webhook EXPIRED → alert admin → admin làm gì? bấm retry ở đâu? |
| pre_payment_benefit_disclosure | LLM-check (V-09): KH phải được acknowledge nếu thanh toán cho quyền lợi có waiting period / coverage gap. | Add-on waiting period: KH trả tiền hôm nay nhưng coverage từ ngày X — không có acknowledge step |
| auto_financial_action_advance_notice | LLM-check (V-09): mọi hành động tài chính tự động phải có thông báo advance cho KH. | Auto-renewal trừ tiền mà KH không nhận được thông báo trước (mâu thuẫn PRD AC39.4) |
| async_wait_ux | LLM-check (V-09): khi KH chờ async processing, phải mô tả UX: KH thấy gì, có thể huỷ không, nhận gì khi timeout. | Đang mua BH chờ UW: "đang xử lý" — KH làm gì? Có nút Huỷ không? |

---

## 5. SCORING — Cách tính điểm

| Metric | Mô tả | Giá trị |
|---|---|---|
| Score per finding | 1.0 = pass, 0.5 = partial, 0.0 = fail | |
| Dimension score | Trung bình weighted của tất cả findings trong dimension | OK >= 80%, WARN 60-79%, FAIL < 60% |
| Overall score | Weighted average: completeness/consistency/quality/readiness x 1.0, risk x 0.8, user-impact x 0.7 | |
| Source: auto | Kiểm tra tự động — structure, keyword, section check | |
| Source: llm | LLM agent phân tích semantic — cross-reference, testability, flow gaps, contradictions | |

---

## 6. AUTO-CHECK ITEMS — Kiểm tra tự động theo SRS template

### 6.1 Completeness — Section existence checks

| Item ID | Check | Section trong template | Severity |
|---|---|---|---|
| has_overview | Section "1. Mô tả chung" tồn tại với đầy đủ fields | Section 1 | CRITICAL |
| has_use_case_summary | Bảng "1.1 Tóm tắt Use Cases" có data | Section 1.1 | CRITICAL |
| has_glossary | Section "1.2 Định nghĩa & Từ viết tắt" | Section 1.2 | MEDIUM |
| has_references | Section "1.3 Tài liệu tham chiếu" | Section 1.3 | MEDIUM |
| has_uc_screens | Mỗi UC có subsection "Màn hình" với bảng controls | Section 2.X.1 | CRITICAL |
| has_uc_sequence | Mỗi UC có Sequence Diagram (PlantUML) | Section 2.X.2 | CRITICAL |
| has_uc_flow_table | Mỗi UC có Bảng mô tả luồng nghiệp vụ | Section 2.X.2 | CRITICAL |
| has_erd | Section "3. Bảng/Thực thể liên quan" có ER diagram | Section 3 | HIGH |
| has_error_codes | Section "4. Danh sách mã lỗi" | Section 4 | HIGH |
| has_impact | Section "5. Chức năng ảnh hưởng" | Section 5 | MEDIUM |
| has_business_rules | Section "6. Business Rules tổng hợp" | Section 6 | HIGH |
| has_nfrs | Section "7. Yêu cầu phi chức năng" | Section 7 | MEDIUM |
| has_dependencies | Section "8. Ràng buộc, Giả định & Phụ thuộc" | Section 8 | HIGH |
| has_state_diagrams | Section "9. State Diagrams" hoặc ghi "Không áp dụng" | Section 9 | MEDIUM |
| has_traceability | Section "10. Ma trận truy xuất (Mini-RTM)" | Section 10 | HIGH |
| has_edge_cases | Luồng ngoại lệ/exception flows rõ ràng | Trong UC flows | MEDIUM |
| has_acceptance_criteria | Acceptance Criteria đo lường được | Per UC | HIGH |

### 6.2 Quality — Content quality checks

| Item ID | Check | Severity |
|---|---|---|
| no_ambiguous_language | Không có "có thể", "nên", "thường", "tùy trường hợp", TBD | HIGH |
| acceptance_criteria_format | AC theo Given/When/Then hoặc checklist measurable | HIGH |
| no_duplicate_requirements | Không trùng lặp requirements giữa các UC/files | MEDIUM |
| clear_scope | Có section phạm vi + ngoài phạm vi rõ ràng | HIGH |
| no_placeholder | Không còn {{...}}, TODO, TBD chưa xử lý | HIGH |
| consistent_language | Ngôn ngữ nhất quán (toàn VN hoặc toàn EN) | LOW |
| flow_step_numbering | Bảng mô tả luồng có đánh số bước liên tục | HIGH |
| diagram_syntax_valid | PlantUML/Mermaid syntax hợp lệ | CRITICAL |

### 6.3 Consistency — Cross-file checks (cần so sánh nhiều files)

| Item ID | Check | Severity |
|---|---|---|
| entity_naming | Entity names nhất quán giữa ER, bảng mô tả, luồng | CRITICAL |
| uc_id_pattern | UC ID tuân theo UC-FX-NN pattern | HIGH |
| screen_id_pattern | Screen ID tuân theo SCR-FX-NN pattern | HIGH |
| actor_naming | Actor names nhất quán | HIGH |
| api_naming_pattern | API endpoint prefix nhất quán (/api/v1/) | HIGH |
| state_naming | State names nhất quán giữa diagrams và bảng | HIGH |
| error_code_consistency | Error codes nhất quán giữa section 4 và flow steps | HIGH |
| br_code_consistency | Business Rule mã BR-XXX nhất quán | HIGH |
| terminology_consistent | Thuật ngữ thống nhất, không dùng lẫn lộn | MEDIUM |
| rtm_fr_match | FR IDs trong Mini-RTM khớp PRD source | HIGH |
| data_model_fields | Entity fields nhất quán giữa các files | CRITICAL |
| no_contradictions | Không mâu thuẫn nội dung giữa các files | CRITICAL |
| tech_stack_consistent | DB technology, message broker, cache nhất quán giữa các files cho cùng entity/module | CRITICAL |
| pk_fk_type_consistent | PK type (UUID v7 vs BIGINT vs SERIAL) và FK references nhất quán theo canonical model | HIGH |
| canonical_model_match | Entity fields trong feature SRS khớp System SRS canonical model (field count, field names, data types) | CRITICAL |
| currency_type_convention | Currency fields thống nhất convention: BIGINT (đơn vị nhỏ nhất) hoặc DECIMAL — không trộn lẫn | HIGH |
| cross_file_state_machine_match | State machine trong feature SRS khớp System SRS (state count, state names, transitions) | CRITICAL |

### 6.4 Readiness — Implementation readiness checks

| Item ID | Check | Severity |
|---|---|---|
| api_contracts_defined | API contracts: method, endpoint, request/response schema | CRITICAL |
| db_schema_specified | DB schema đầy đủ: field types, PKs, FKs | HIGH |
| error_handling_defined | Error codes: mã, message, HTTP status, step trigger | HIGH |
| state_machine_complete | State machine: transitions, guards, actions | HIGH |
| integration_specs | External API: format, auth, timeout, retry | HIGH |
| event_payload_schema | Kafka/event payload schema defined: topic, fields, types, version — không chỉ mention event name | CRITICAL |
| validation_rules | Input field validation: regex, range, format | HIGH |
| navigation_flow | Screen navigation rõ ràng: A → action → B | MEDIUM |
| mockup_reference | Mockup/wireframe reference cho mỗi màn hình | MEDIUM |
| br_implementable | Business rules có thể code trực tiếp | HIGH |

### 6.5 Risk — Risk assessment checks

| Item ID | Check | Severity |
|---|---|---|
| exception_flows_handled | Tất cả exception flows: network error, timeout, invalid data | HIGH |
| external_deps_fallback | External dependencies có fallback | HIGH |
| integration_gaps | Integration gaps giữa flows đã document | HIGH |
| scope_creep | Không có requirements vượt PRD scope | MEDIUM |
| assumptions_listed | Assumptions đã liệt kê và đánh dấu cần confirm | MEDIUM |
| concurrency_considered | Race condition scenarios đã xem xét | HIGH |
| migration_risk | Data migration risks đã xử lý (nếu thay flow cũ) | HIGH |
| security_risks | Authentication, authorization, data exposure | CRITICAL |

### 6.6 User Impact — User experience checks

| Item ID | Check | Severity |
|---|---|---|
| persona_coverage | Tất cả personas/actors trong PRD đã cover | HIGH |
| journey_complete | User journey hoàn chỉnh entry → completion | HIGH |
| error_ux | Error messages rõ ràng, có hướng dẫn xử lý | HIGH |
| onboarding | First-time experience đã xem xét | MEDIUM |
| loading_empty_states | Loading states, empty states đã mô tả | MEDIUM |
| accessibility | Accessibility considerations (nếu yêu cầu) | LOW |
| back_cancel_undo | Navigation back/cancel/undo đã xử lý | MEDIUM |
| destructive_confirmation | Confirmation dialogs cho destructive actions | MEDIUM |

---

## 7. OUTPUT REPORT STRUCTURE

### Frontmatter

```yaml
---
type: srs-validation-report
date: {date}
validator: BA Validate SRS Skill
scope: {single | batch | full}
files_reviewed: [list of files]
overall_score: {number}%
overall_status: {OK | WARN | FAIL}
stepsCompleted: []
---
```

### Report Sections

1. **Executive Summary** — Overall score, status, findings count by severity
2. **Per-Dimension Scorecard** — Table: dimension, weight, score, status, findings count
3. **Critical & High Findings** — Must-fix: #, severity, dimension, file, item_id, score, evidence, suggestion
4. **Medium & Low Findings** — Nice-to-fix items
5. **Unresolved Questions** — Questions needing PO/stakeholder decision: #, severity, dimension, category, question, context, related_files, impact, suggested_clarification
6. **Recommendations** — Prioritized action plan
7. **Appendix: Full Scoring Matrix** — All items with scores
