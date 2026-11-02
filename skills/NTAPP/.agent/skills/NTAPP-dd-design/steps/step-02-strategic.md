# STEP 02: STRATEGIC — BOUNDED CONTEXT + SUBDOMAIN + CONTEXT MAP

> **Acting as:** [Agent D1 — Strategic Domain Analyst](../agents/agent_d1_strategic_analyst.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R3, R4 (no-orphan), R5 (Consistency), R8 (Model Alignment), R10 (As-is ≠ To-be).

**Input:** Evidence Inventory + Scope (từ Step 01).
**Output:** `{intermediate_folder}/part_02_strategic.md` → bơm vào `CONTEXT-MAP.md`.
**Template:** [context_map_template.md](../templates/context_map_template.md).

---

## 2.1 Phân định Bounded Context (as-is)

Với mỗi BC candidate, xác định bằng evidence + interview:
- **Ranh giới**: module/service nào thuộc BC; dữ liệu nào BC sở hữu (ai là authoritative writer).
- **Ngôn ngữ riêng**: term nào chỉ có nghĩa trong BC này (cùng từ khác nghĩa ở BC khác = tín hiệu ranh giới — giữ nguyên, không ép một nghĩa, R5).
- **Chủ sở hữu**: team nào sở hữu lõi BC.

> **As-is fidelity (R10):** Nếu một "BC" thực chất trộn 2 subdomain (vd Ordering + Inventory ghi chung), **vẽ đúng thực tại** (1 BC bị trộn) + đánh dấu finding. Đề xuất tách = to-be (Step 05), KHÔNG vẽ 2 BC sạch ở đây.

## 2.2 Phân loại Subdomain

Mỗi BC gắn một class (ưu tiên đầu tư chiến lược):
- **core** — lợi thế cạnh tranh, logic độc nhất → đầu tư mạnh, DDD chặt.
- **supporting** — cần cho nghiệp vụ nhưng không khác biệt → đủ tốt.
- **generic** — bài toán đã giải sẵn (auth, notification, payment rails) → nên mua/dùng off-the-shelf.

Phân loại từ PRD (đâu là giá trị cốt lõi) + xác nhận SA. Đây là input ưu tiên cho roadmap (Step 05).

## 2.3 Vẽ Context Map + Integration Pattern

Với mỗi cặp BC có tương tác, xác định (neo về Module 0 contract — R8):

| Quan hệ | Upstream→Downstream | Integration pattern (as-is) | Module 0 ref |
| :--- | :--- | :--- | :--- |

**Integration pattern** — chọn theo thực tại, không theo lý tưởng (legend đầy đủ ở [template §2](../templates/context_map_template.md)): `Anti-Corruption Layer` · `Published Language` · `Open Host Service` · `Conformist` · `Customer/Supplier` · `Shared Kernel` (⚠️ thường là finding nếu vô tình) · `Separate Ways`.

> Nếu as-is **thiếu ACL nơi đáng có** (downstream gọi thẳng DB upstream) → ghi pattern thực tế (`Shared Kernel` / shared-DB) + đánh dấu để D3 chấm ❌ trục Integration. KHÔNG "vẽ thêm" ACL chưa tồn tại (R10).

## 2.4 Ghi nhận mâu thuẫn nguồn (R5)

Mọi điểm HLD/code/SA mâu thuẫn về ranh giới hay ngữ nghĩa → bảng Open Conflicts (Context Map §5) + câu hỏi cho SA. KHÔNG tự quyết.

## 2.5 Interview SA (qua D0 — nếu scope có SA)

D1 soạn câu hỏi, D0 hỏi user (single touchpoint). Cheap → expensive:
1. "Term X ở module A và module B có cùng nghĩa không?" (dò ranh giới ngôn ngữ)
2. "Dữ liệu Y do BC nào sở hữu/ghi? BC khác chỉ đọc?"
3. "BC này là lợi thế cạnh tranh (core) hay chỉ cần đủ dùng?"
4. "Khi A gọi B, có lớp dịch (ACL) hay dùng thẳng model của nhau?"

Không có SA → đánh dấu mọi suy luận `[TBD — SA verify]`, KHÔNG nâng thành sự thật (R3).

## 2.6 Ghi part + bơm CONTEXT-MAP

Ghi `part_02_strategic.md`, rồi bơm nguyên văn (R1) vào `CONTEXT-MAP.md` canonical theo template (Inventory BC + Mermaid map + bảng quan hệ + Open Conflicts). Dual-write archive.

---

## ⛔ [GATE — G1: BOUNDARY COVERAGE] (D0 self-check)

- [ ] **Mọi** module/service trong WBS thuộc **≥1** BC (R4 — no orphan). Còn orphan → loop về 2.1.
- [ ] Mỗi BC có subdomain class (core/supporting/generic).
- [ ] Mỗi quan hệ Context Map có integration pattern + Module 0 ref (hoặc `[TBD]` có lý do).
- [ ] Ranh giới as-is không "vẽ đẹp" hơn thực tại (R10).

FAIL → ở lại Step 02 sửa. PASS → Next.

**Next:** Read fully and follow `./step-03-tactical.md`
