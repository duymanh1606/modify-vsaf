---
# model: haiku
# findingsOutput: '{output_folder}/_validation_temp/findings-user-impact.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
---

# Step V-09: User Impact — Đánh giá tác động người dùng

Weight: **0.7**

---

## 0. Load Context
Read `{contextFile}` → get `srs_path`, `kg.prd_key_sections`, `kg.brd_key_sections`. Use KG line ranges for all upstream document reads — do NOT read full PRD/BRD.

## 1. Persona coverage

- Tất cả actors/personas trong PRD đã có UC tương ứng?
  - Khách hàng (end user)
  - Business Manager / Admin
  - Insurer Partner
  - System (background jobs)
- Không có persona nào bị thiếu UC coverage?

Item ID: `persona_coverage`

---

## 2. User journey completeness

- Entry point → completion journey rõ ràng?
- Happy path + unhappy path đều có?
- Post-action: KH biết bước tiếp theo?
  - VD: Đăng ký xong → rồi sao? Welcome screen? CTA?
- Multi-session journey: user có thể resume không?

Item ID: `journey_complete`

---

## 3. Error UX

- Error messages user-friendly (không raw technical)?
- Có hướng dẫn xử lý khi lỗi?
- Retry guidance?
- Gateway error → user-friendly mapping?
- Timeout → user thấy gì?

Item ID: `error_ux`

---

## 4. Loading & Empty states

- Loading states đã mô tả?
- Empty states (danh sách trống) đã mô tả?
- Skeleton/placeholder UI?

Item ID: `loading_empty_states`

---

## 5. Navigation & Recovery

- Back/Cancel/Undo đã xử lý?
- Confirmation dialogs cho destructive actions (hủy HĐ, xóa)?
- Session recovery (browser refresh, app crash)?
- Deep link / direct URL handling?

Item IDs: `back_cancel_undo`, `destructive_confirmation`

---

## 6. Edge-case UX

- What if user submits form twice?
- What if user leaves mid-checkout?
- What if payment succeeds but network drops before confirmation?
- What if user has multiple tabs open?

Item ID: `edge_case_ux`

---

## 6b. Pre-payment benefit disclosure

Kiểm tra mỗi flow có KH thanh toán cho quyền lợi chưa có hiệu lực ngay:

- Waiting period: nếu KH trả tiền hôm nay nhưng coverage chỉ có hiệu lực từ ngày X:
  - Có màn hình/step yêu cầu KH acknowledge (đọc và đồng ý) trước khi confirm payment không?
  - Ngày bắt đầu có hiệu lực có hiển thị rõ không?
- Late renewal coverage gap: KH gia hạn trễ → N ngày không được bảo vệ:
  - Có hiển thị gap period rõ ràng trước khi KH confirm không?
  - Có nói rõ hậu quả (không được claim trong gap) không?
- **HIGH**: KH trả tiền mà không biết quyền lợi bị delay/gap → khiếu nại sau này

Item ID: `pre_payment_benefit_disclosure`

---

## 6c. Auto financial action advance notice

Kiểm tra mọi hành động tài chính tự động (không cần KH click confirm):

- Auto-renewal: KH bật auto-renewal → khi gia hạn, KH có nhận thông báo trước không?
  - VD: "HĐ sẽ tự động gia hạn vào ngày X, phí Y sẽ trừ từ PTTT Z"
  - Không chấp nhận: auto-trừ tiền mà KH không nhận được bất kỳ thông báo advance nào
- Auto-charge delta endorsement: KH eSign endorsement → hệ thống tự trừ delta premium:
  - eSign là đồng ý thay đổi điều khoản, không phải đồng ý bị trừ tiền
  - Cần bước riêng: notify KH số tiền cần trả + KH xác nhận payment
- Kiểm tra cross-reference với PRD/AC: nếu PRD có AC yêu cầu gửi thông báo nhưng UC không thực hiện → CRITICAL

Item ID: `auto_financial_action_advance_notice`

---

## 6d. Async wait UX

Kiểm tra mỗi flow KH phải chờ async processing (UW decision, insurer sync, endorsement approval):

- KH thấy gì khi đang chờ? Loading screen? Status screen?
- KH có thể làm gì trong lúc chờ? Có nút Huỷ không?
- Nếu timeout: KH nhận thông báo gì? Có thể retry không?
- Có thể chọn option khác (insurer khác, sản phẩm khác) không?
- **HIGH**: KH bị kẹt ở màn hình "đang xử lý" không biết bao lâu, không có escape

Item ID: `async_wait_ux`

---

## 7. Onboarding & Accessibility

- First-time user experience?
- Tooltip / help text cho complex fields?
- Accessibility requirements (WCAG 2.1 AA)?
- Multi-language / locale handling?

Item IDs: `onboarding`, `accessibility`

---

## 8. Figma Platform Coverage (via figma-cache manifests)

1. Read ALL figma-cache manifests → filter screens for this FR
2. Group by platform: Mobile App vs Web Mobile
3. Check:
   - Customer-facing flows: both platforms have designs?
   - If SRS specifies dual-platform (Mobile + Web): both covered in Figma?
   - Admin flows: at least one platform has design?
4. Cross-reference with upstream PRD/ADR for platform coverage requirements

**Scoring:**
- Both platforms covered for all customer flows → 1.0
- One platform covered, other partial → 0.75
- Only one platform → 0.5
- No Figma designs for this FR → 0.25 (if customer-facing) or 1.0 (if backend-only)

Item ID: `figma_platform_coverage`

---

## 9. Ghi Unresolved Questions

Câu hỏi cần PO/stakeholder quyết định → ghi vào section "7. Unresolved Questions":

```markdown
| # | Severity | Dimension | Category | Question | Context | Related Files | Impact | Suggested Clarification |
```

---

## 10. Tính User Impact dimension score

```
user_impact_score = round(sum(item_scores.values()) / 13 × 100, 1)
```

Canonical item IDs (N = 13, fixed):
`persona_coverage`, `journey_complete`, `error_ux`, `loading_empty_states`, `back_cancel_undo`, `destructive_confirmation`, `edge_case_ux`, `pre_payment_benefit_disclosure`, `auto_financial_action_advance_notice`, `async_wait_ux`, `onboarding`, `accessibility`, `figma_platform_coverage`

⚠️ MANDATORY: N = 13 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

Weight: **0.7**

---

## 11. Append findings vào report

Append CRITICAL/HIGH → section "4. Critical & High Findings".
Append MEDIUM/LOW → section "5. Medium & Low Findings".
Append unresolved questions → section "7. Unresolved Questions".

Update frontmatter: thêm `step-v-09-user-impact` vào `stepsCompleted`.

---

## 8b. Deep Figma Cross-Validation (if page images available)

If `kg.figma_screens` in context.yaml has entries with `file` paths:

For each screen where `maps_to_uc` is not empty:
1. Check if the page image file exists on disk (Read tool — multimodal, ~1,500 tokens per image)
2. If image exists:
   - Extract visible UI elements: input fields, buttons, labels, error states
   - Compare with SRS UC spec for the mapped UC (use `uc_cache` line ranges for targeted read)
   - Check: do SRS screen controls match visible UI elements in Figma?
   - Check: are button labels consistent (SRS text vs Figma text)?
   - Check: are there Figma elements not specified in SRS (or vice versa)?
3. If mismatch found → create finding:
   - item_id: `figma_ux_mismatch`
   - severity: HIGH if functional difference (missing field/button), MEDIUM if label/text difference
   - evidence: "SRS UC-CA-01 lists 5 fields but Figma shows 7 fields (extra: avatar, address)"
   - business_impact: "WHO: Dev. WHAT: Must decide which spec to follow — Figma or SRS. WHEN: During Sprint."

If page images not on disk (gitignored or not yet generated):
- Skip deep check, log: "Figma deep check skipped — page images not available. Run /bmad-index-figma to generate."

---

## [NEW] Write Structured Findings
Write `{findingsOutput}`:
```yaml
dimension: user_impact
weight: 0.7
dimension_score: 0   # = round(sum(item_scores.values()) / 13 × 100, 1)
status: OK
findings: []
summary: {total: 0, critical: 0, high: 0, medium: 0, low: 0}
item_scores:
  persona_coverage: 0.0
  journey_complete: 0.0
  error_ux: 0.0
  loading_empty_states: 0.0
  back_cancel_undo: 0.0
  destructive_confirmation: 0.0
  edge_case_ux: 0.0
  pre_payment_benefit_disclosure: 0.0
  auto_financial_action_advance_notice: 0.0
  async_wait_ux: 0.0
  onboarding: 0.0
  accessibility: 0.0
  figma_platform_coverage: 0.0
```

## 12. Menu

```
User Impact Score: {X}% ({status}) [weight 0.7]
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}
Unresolved Questions: {count}

[C] Continue — Sang Tổng hợp Report (Step V-10)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-10-report.md`
