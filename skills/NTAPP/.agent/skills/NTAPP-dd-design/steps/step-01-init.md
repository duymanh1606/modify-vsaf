# STEP 01: INITIALIZATION — EVIDENCE INVENTORY & SCOPE

> **Acting as:** [Agent D0 — Domain Orchestrator](../agents/agent_d0_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication), R8 (Model Alignment), R9 (Missing Input), R10 (As-is ≠ To-be).

**Input:** Evidence của hệ thống hiện hữu (HLD, Module 0, WBS, system-overview, PRD/Epics, CONTEXT.md intent-level).
**Output:** Evidence Inventory + Scope (BC in-scope) đã user xác nhận.

---

## 1.1 Tìm & đọc evidence (theo thứ tự ưu tiên)

Đọc từ path đã resolve ở [workflow.md INITIALIZATION](../workflow.md#initialization). Mọi input nằm dưới `{planning_artifacts}` — nơi `/ntapp-architecture-design` + `/ntapp-system-overview` ghi ra (không hardcode output-root):

```
Ưu tiên 1: File user khai báo trực tiếp
Ưu tiên 2: {planning_artifacts}/architecture_design.md                 (HLD — ranh giới module, C4, ERD)
Ưu tiên 3: {planning_artifacts}/00_system_connectivity_integration.md  (Module 0 — contract, SSoT bất biến cho R8)
Ưu tiên 4: {planning_artifacts}/project_wbs.md                         (WBS — unit để map về BC, R4 no-orphan)
Ưu tiên 5: {planning_artifacts}/system_overview/_overview.md + {sub_system}.md   (as-built evidence brownfield)
Ưu tiên 6: {planning_artifacts}/prd*.md + epics*.md                    (intent nghiệp vụ)
Ưu tiên 7: {planning_artifacts}/CONTEXT.md / CONTEXT-MAP.md            (ubiquitous language từ grill-with-docs)
```

**Hành động:** Đọc tất cả file tìm được, lập **Evidence Inventory** — mỗi mục đánh dấu nguồn:
- `as-built` (system-overview, code reality) — ưu tiên cao nhất cho as-is.
- `as-designed` (HLD/PRD intent) — đối chiếu, flag nếu lệch as-built.
- `contract-locked` (Module 0) — bất biến cho R8; domain model không được mâu thuẫn.
- `sa-stated` (chờ interview ở Step 02/03).

> **Mâu thuẫn nguồn** (HLD nói A, system-overview nói B) → ghi vào Inventory cột "conflict", KHÔNG tự chọn (R5). Sẽ đưa vào Context Map §5 để SA reconcile.

## 1.2 Pre-flight Check (BẮT BUỘC)

Nếu Evidence Inventory **không có** HLD **lẫn** WBS (không đọc được kiến trúc nền) → **DỪNG** (R9):

```markdown
❌ Không tìm thấy HLD / WBS — chưa có kiến trúc nền để tái dựng domain model.

  (a) Đã có ở path khác — cung cấp đường dẫn.
  (b) Chưa có — chạy `/ntapp-architecture-design` (FULL) trước, rồi quay lại Step 01.

Tôi sẽ KHÔNG bịa bounded context thay thế (R3 + R9).
```

> **Vì sao:** Domain model là **downstream** của HLD + Module 0 (R8). Không có kiến trúc nền thì reproduce sẽ thành bịa, không phải tái dựng.

## 1.3 Đề xuất scope (Bounded Context candidate sơ bộ)

Từ WBS + HLD §3.2 (module list), D0 lập **bảng module → BC candidate sơ bộ** (chưa chốt — D1 sẽ tinh chỉnh):

| Module/Service (WBS) | BC candidate (gợi ý) | Subdomain (phỏng đoán) | Evidence |
| :--- | :--- | :--- | :--- |
| [BE-ORD-*] | BC-ORDERING | core? | HLD §3.2.1 |
| ... | ... | ... | ... |

Mọi module phải xuất hiện (R4 no-orphan). Module chưa rõ thuộc BC nào → để `[TBD — D1 interview]`.

## 1.4 Chốt scope với user (Pause & Wait)

Hiển thị Evidence Inventory + bảng BC candidate, hỏi user xác nhận scope:

```markdown
## 🔍 SCOPE — Trước khi tái dựng domain model

Đã đọc {N} file evidence. Đề xuất {M} bounded context candidate (bảng trên).

**[Q1]** Tái dựng TOÀN BỘ hệ thống, hay chỉ một cụm BC? (vd chỉ "Ordering + Billing")
**[Q2]** Có SA/Domain Expert tham gia interview (Step 02/03) không? (interview-driven cần người trả lời ngữ nghĩa miền)
**[Q3]** Mâu thuẫn nguồn đã phát hiện: {liệt kê}. Xác nhận để tôi đưa vào danh sách reconcile?

Trả lời xong tôi khởi động pipeline (D1 → D2 → D3 → D4).
```

**DỪNG HOÀN TOÀN** chờ user. KHÔNG tự suy đoán scope.

## 1.5 Tạo thư mục intermediate

Sau khi user confirm: `mkdir -p {intermediate_folder}` (= `{domain_artifacts}/_parts/`, idempotent).

---

## ĐIỀU KIỆN TIẾP TỤC (Exit Criteria)

- [ ] Evidence Inventory lập xong, đánh dấu nguồn + conflict.
- [ ] Pre-flight pass (có HLD/WBS) hoặc đã dừng đúng cách.
- [ ] User đã chốt **scope** (toàn bộ / cụm BC) + xác nhận có/không SA interview.
- [ ] `{intermediate_folder}` đã tạo.

## ⛔ [GATE — INTAKE] (cổng người dùng, đặt TRƯỚC Next)

Chỉ đọc step kế SAU KHI user chốt scope (§1.4). Thiếu HLD/WBS (§1.2) → DỪNG, không đọc step-02.

**Next:** Read fully and follow `./step-02-strategic.md`
