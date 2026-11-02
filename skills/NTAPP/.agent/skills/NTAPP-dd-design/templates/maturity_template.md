# DDD MATURITY ASSESSMENT — [PROJECT_NAME]

*Đánh giá "cái gì tốt — giữ, cái gì sai — sửa" cho mô hình miền as-is. Chấm theo [maturity_rubric.md](../principles/maturity_rubric.md) (7 trục).*

> **Trạng thái:** AS-IS assessment · **Version:** v{N} · **Cập nhật:** {date}
> Mỗi mức phải có **evidence**. Không evidence → không được ✅ (Iron Rule R3). To-be & lộ trình sửa: xem `TARGET.md` + `MIGRATION.md`.

---

## 1. Bảng tổng hợp (Roll-up — toàn hệ thống)

| BC ID | Subdomain | T1 Boundary | T2 Language | T3 Aggregate | T4 Richness | T5 Integration | T6 Events | T7 Layering | Tổng | Level |
| :--- | :--- | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: |
| BC-ORDERING | core | ⚠️ | ✅ | ⚠️ | ❌ | ⚠️ | ❌ | ⚠️ | 6/14 | **L1** |
| ... | ... | | | | | | | | | |

*Ký hiệu: ✅=2 KEEP · ⚠️=1 TIGHTEN · ❌=0 VIOLATION. Level từ tổng điểm (rubric §"Composite"). Core subdomain có ❌ → trần L2.*

**Phân bố:** {x} BC ở L0–L1 (cần đầu tư), {y} ở L2, {z} ở L3–L4. **Core subdomain trung bình:** L{n}.

---

## 2. Chi tiết per-BC

### BC-ORDERING (core) — Level L1

| Trục | Mức | Điểm | Evidence | Finding (1 câu) |
| :--- | :--: | :--: | :--- | :--- |
| T1 Boundary Integrity | ⚠️ | 1 | HLD §3.2; `order/` gọi thẳng `inventory/` repo | Rò boundary: Ordering đọc trực tiếp bảng inventory |
| T2 Ubiquitous Language | ✅ | 2 | Glossary khớp `Order`/`LineItem` trong code | Ngôn ngữ nhất quán |
| T3 Aggregate Design | ⚠️ | 1 | `Order` ôm 40+ field, gồm cả shipping | Aggregate quá to — gợi ý tách |
| T4 Model Richness | ❌ | 0 | Toàn rule trong `OrderService` 2000 dòng | Anemic — transaction script |
| T5 Integration Hygiene | ⚠️ | 1 | Đọc inventory qua shared DB read | Shared read chưa qua contract |
| T6 Domain Events | ❌ | 0 | Không có event; gọi RPC chuỗi 5 service | Không truy được lịch sử miền |
| T7 Layer/Persistence | ⚠️ | 1 | Domain entity có annotation JPA | Lệ thuộc ORM nhẹ |
| **Tổng** | | **6/14** | | **Level L1 — Named** |

**Remediation seeds (→ Step 05 nâng thành migration item):**
- ❌ T4: Trích business rule khỏi `OrderService` về `Order` aggregate — *lane-3 (refactor có ADR)*.
- ❌ T6: Giới thiệu `OrderPlaced`/`OrderCancelled` domain event, decouple inventory — *lane-3 slice*.
- ⚠️ T3: Tách `Shipping` khỏi `Order` aggregate — *lane-2 quick-dev*.
- ⚠️ T1/T5: Thay shared DB read bằng API/event của Inventory BC — *lane-3*.

---

### BC-{NEXT} (...) — Level L{n}
*(lặp bảng trên cho mỗi BC)*

---

## 3. Phát hiện xuyên BC (Cross-cutting findings)

*Vấn đề không thuộc riêng BC nào (Iron Rule R7 stopping errors thường rơi vào đây).*

| # | Loại | Mô tả | BC liên quan | Mức độ |
| :--: | :--- | :--- | :--- | :--- |
| 1 | Shared mutable DB | 3 BC cùng ghi bảng `customer` không qua ACL | ORD, BIL, FUL | ❌ Critical |
| 2 | Orphan event | `LegacySync` không có consumer | — | ⚠️ |
