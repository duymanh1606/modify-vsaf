# STEP 08: WORKFLOW ARCHETYPE & INFORMATION MODEL (§2)

> **Thực hiện bởi:** Agent UX3 (IA & System Architect — Winston)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R3, R5, R8, R10**.

## 1. Mục tiêu

Chốt workflow archetype của feature, mô tả primary entity + composition model, state taxonomy + cross-section data propagation. Journey Spec §2 — nền cho §4 journeys.

## 2. Đầu vào cần đọc

- §3 part (IA — nav tree, shell placement) + §1 part (context, personas)
- PRD: primary user story (entity + archetype), business rules (composition + lifecycle), data dependency
- Module 0 §7 Global State Registry (nếu có) — state enum
- `master_token.json` — verify `semantic.color.status.*` paths

## 3. Chỉ thị thực thi

### 3.1. §2.1 Workflow Archetype

Chọn 1 archetype:

| Archetype | Pattern | Khi nào dùng |
|:---|:---|:---|
| MAKER_CHECKER | Creator submit → Reviewer approve/reject | Compliance form, approval workflow |
| WIZARD | Linear single-actor multi-step | Onboarding, form chia bước |
| DASHBOARD | Read-heavy + embedded action | Analytics, monitoring, ops console |
| TRANSACTIONAL | Single-actor single-submission | Simple form, search, lookup, config |
| CONTENT_MGMT | Create/edit/publish với draft state | CMS, docs, knowledge base |
| OTHER | Custom — mô tả entry signal → action sequence → terminal state (≤5 dòng) | — |

**Output:** 1 archetype + 1-2 dòng justification cite PRD primary user story.

**Hybrid check:** PRD chứa 2 archetype song song → split 2 spec riêng, KHÔNG mix. Báo user xác nhận scope split (GATE cuối step).

### 3.2. §2.2 Primary Entity & Composition Model

1. Entity theo BUSINESS term (không "record"/"row").
2. Composition model: SINGLE / SECTIONED / LINEAR_STEPS / REFERENCE.
3. ASCII diagram sub-section/step + data-flow direction (shape theo composition thực — SINGLE rõ ràng thì skip diagram). Mark Required/Optional + điều kiện kích hoạt.

### 3.3. §2.3 Section Status & Data Propagation

**Skip nếu composition = SINGLE.**

1. **State taxonomy** — universal: Empty / In-progress / Complete / Error; archetype-conditional: Locked + Rejected [MAKER_CHECKER], Blocked [WIZARD], Draft + Published [CONTENT_MGMT]. Mỗi state: icon + color token path + 1 dòng business meaning. KHÔNG bịa state ngoài archetype. *(Indicator pattern hiển thị + transition behavior chi tiết thuộc `ux_conventions.md` §C3 — step-11; ở đây chỉ khoá taxonomy.)*
2. **Cross-section propagation** (skip nếu sections độc lập data): bảng `| Source | Field | → Target | Field | Type (AUTO_READONLY/AUTO_EDITABLE/DERIVED/REFERENCE_LOOKUP) | Timing | Conflict Policy |` — liệt kê EVERY field cross-section; auto-populated field → journey table Key states ghi badge nguồn.

## 4. Đầu ra yêu cầu

- **Lưu trữ:** `{intermediate_folder}/ux3_modular_part.md`
- Nội dung: §2.1 + §2.2 + §2.3 (nếu applicable).
- Báo cáo: "§2 hoàn tất. Archetype: {X}, composition: {Y}, {Z} states, {W} propagation mappings."
- Preliminary archetype ở §3.2 (step-07) lệch với archetype chốt → quay lại sửa §3.2 shell placement TRƯỚC khi sang step-09.

## [GATE] — ⛔ KIỂM TRA TRƯỚC KHI SANG STEP KẾ
- **Hybrid archetype (§3.1):** PRD chứa 2 archetype song song → split 2 spec + **báo user xác nhận scope split** TRƯỚC khi đọc step-09. KHÔNG mix.

**Next:** Read fully and follow `./step-09-primary-journey.md`
