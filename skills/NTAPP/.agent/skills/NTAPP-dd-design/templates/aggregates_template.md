# {Bounded Context Name} — Aggregates (AS-IS)

*Mô hình tactical của BC **như code đang là** — kể cả khuyết tật (Iron Rule R10). Đề xuất cải thiện ở `TARGET.md`.*

> **BC ID:** BC-{SLUG} · **Version:** v{N} · **Nguồn:** ERD (HLD §3.1.3 / Module 0) + code + SA interview.

---

## 1. Danh mục Aggregate

| Aggregate | Root entity | WBS unit(s) | Quy mô (as-is) | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **Order** | `Order` | BE-ORD-01 | ⚠️ ôm 40+ field gồm shipping | aggregate to — finding T3 |
| ... | ... | ... | ... | ... |

## 2. Chi tiết mỗi Aggregate

### Aggregate: Order  (root: `Order`)

**Entities & Value Objects:**
| Tên | Loại | Identity / Immutable | Ghi chú |
| :--- | :--- | :--- | :--- |
| `Order` | Entity (root) | id | — |
| `LineItem` | Entity | id (trong order) | — |
| `Money` | Value Object | immutable | định nghĩa bởi giá trị |
| `ShippingAddress` | Value Object | immutable | — |

**Invariants (quy tắc luôn đúng):**
| # | Invariant | Nơi thực thi **thực tế** (as-is) | Finding |
| :-: | :--- | :--- | :--- |
| 1 | Tổng `LineItem.amount` = `Order.total` | ⚠️ kiểm trong `OrderService`, không trong aggregate | T4 anemic |
| 2 | Order `CONFIRMED` không sửa được line item | ✅ trong `Order.addLineItem()` | — |

**Command → Domain Event:**
| Command | Điều kiện | Domain Event phát ra | Cơ chế |
| :--- | :--- | :--- | :--- |
| `PlaceOrder` | giỏ không rỗng | `OrderPlaced` | ⚠️ as-is: gọi RPC, chưa có event — finding T6 |
| `CancelOrder` | chưa shipped | `OrderCancelled` | — |

**Consistency boundary:** {transaction ôm những entity nào — có vượt aggregate không?}
**Persistence (as-is):** {bảng nào; domain có lệ thuộc ORM/SQL trực tiếp không — finding T7?}

---

### Aggregate: {Next}  (root: `...`)
*(lặp block trên)*
