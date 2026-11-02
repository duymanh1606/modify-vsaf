# STEP 03: TACTICAL — AGGREGATE + ENTITY/VO + INVARIANT + DOMAIN EVENT + UBIQUITOUS LANGUAGE

> **Acting as:** [Agent D2 — Tactical Domain Modeler](../agents/agent_d2_tactical_modeler.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R3, R4 (traceability), R5 (language), R10 (As-is ≠ To-be).

**Input:** `CONTEXT-MAP.md` + Scope (BC in-scope).
**Output:** per-BC `contexts/<bc>/CONTEXT.md` + `AGGREGATES.md`, và `EVENTS.md` catalog.
**Template:** [aggregates_template.md](../templates/aggregates_template.md), [context_bc_template.md](../templates/context_bc_template.md), [events_template.md](../templates/events_template.md).

> **Lặp theo từng BC in-scope.** REFRESH mode: chỉ chạy cho `<bc_id>` được chỉ định.

---

## 3.1 Ubiquitous Language per BC (chốt ngôn ngữ trước)

Với mỗi BC, viết `contexts/<bc>/CONTEXT.md` (format grill-with-docs): mỗi **term** + định nghĩa 1-2 câu (định nghĩa nó **LÀ gì**, không phải làm gì) + `_Avoid:` alias. Term phải khớp tên class/API/event trong code (đối chiếu system-overview). Mâu thuẫn term ↔ code → finding cho D3 (trục Language).

## 3.2 Mô hình Aggregate (as-is)

Với mỗi BC, từ ERD (HLD §3.1.3 / Module 0) + code + interview, xác định:

| Hạng mục | Cách xác định |
| :--- | :--- |
| **Aggregate + root** | Cụm entity thay đổi cùng nhau dưới một transaction; root = entry point mọi truy cập. Không xác định được root → **R7 stopping error**. |
| **Entity vs Value Object** | Entity = có identity + lifecycle; VO = immutable, định nghĩa bởi giá trị (Money, Address). |
| **Invariant** | Quy tắc luôn đúng trong aggregate (vd "tổng line item = order total"). Liệt kê **nơi thực thi thực tế** (trong aggregate? hay rải ở service?). |
| **Command → Event** | Hành động (PlaceOrder) → kết quả miền (OrderPlaced). |

> **As-is fidelity (R10):** Mô tả aggregate **như code đang là**. Nếu `Order` ôm 40 field gồm cả shipping, **ghi đúng** (aggregate khổng lồ) + finding. Nếu invariant kiểm ở `OrderService` thay vì trong `Order`, **ghi đúng** (anemic). Đề xuất tách/làm rich = to-be (Step 05). KHÔNG vẽ aggregate lý tưởng ở đây.

## 3.3 Domain Event Catalog

Tổng hợp mọi domain event vào `EVENTS.md`:

| Event | Producer BC | Aggregate | Consumer BC(s) | Cơ chế (sync RPC / async bus) | Pattern |
| :--- | :--- | :--- | :--- | :--- | :--- |

- Event đặt tên nghiệp vụ, thì quá khứ (`OrderPlaced`, không `OrderUpdated`). Tên kỹ thuật/CRUD → ghi đúng thực tại + finding (D3 trục Events).
- Event không có consumer **hoặc** không có producer → đánh `[orphan-event]` (R4) — finding, không xoá.
- Nếu BC tích hợp **không** qua event mà bằng RPC đồng bộ chuỗi → ghi `(no domain event — sync RPC)` + finding.

## 3.4 Interview SA per BC (qua D0)

1. "Quy tắc nào của <aggregate> phải LUÔN đúng?" (invariant)
2. "Khi <command>, hệ thống coi như 'chuyện gì đã xảy ra' trong nghiệp vụ?" (event discovery)
3. "<field> bất biến sau khi tạo, hay đổi được?" (entity vs VO)
4. "Sửa <aggregate> có cần khoá/giao dịch cùng entity nào khác?" (consistency boundary)

Không có SA → suy luận từ code/ERD + đánh `[TBD — SA verify]`.

## 3.5 Ghi part + bơm artifacts

Ghi `part_03_tactical.md`; bơm nguyên văn (R1) vào per-BC `CONTEXT.md` + `AGGREGATES.md` + `EVENTS.md`. Dual-write archive.

---

## ⛔ [GATE — G2: TACTICAL COMPLETENESS] (D0 self-check)

- [ ] Mỗi BC in-scope có ≥1 aggregate; mỗi aggregate có **root** xác định (R7).
- [ ] Mỗi aggregate có ≥1 invariant ghi rõ **nơi thực thi** (kể cả "rải ở service" — finding).
- [ ] Mỗi domain event có producer + consumer (hoặc `[orphan-event]` đánh dấu).
- [ ] Mỗi aggregate map ≥1 WBS unit (R4); term khớp/ lệch code đã ghi nhận.

FAIL → ở lại Step 03. PASS → Next.

**Next:** Read fully and follow `./step-04-maturity.md`
