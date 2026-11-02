# {Bounded Context Name} — Ubiquitous Language

*Ngôn ngữ chung của bounded context này. Term ở đây phải khớp tên class/API/event trong code (as-is).*

> **BC ID:** BC-{SLUG} · **Subdomain:** core / supporting / generic · **Owner:** [team] · **Version:** v{N}
> Một term = một nghĩa **trong BC này**. Cùng từ ở BC khác có thể khác nghĩa — đó là ranh giới, không phải xung đột.

---

## Mô tả
{1-2 câu: BC này tồn tại để làm gì, chịu trách nhiệm gì.}

## Language

**{Term}**:
{Định nghĩa 1-2 câu — nó LÀ gì, không phải làm gì.}
_Avoid_: {alias nên loại bỏ}
_Code ref_: {class/API/event khớp term — hoặc `[mismatch: code gọi là X]` nếu lệch (finding cho D3 trục Language)}

**{Term 2}**:
...
_Avoid_: ...

## Quan hệ giữa các term (trong BC)
- Một **{Order}** chứa nhiều **{LineItem}**; mỗi **{LineItem}** trỏ tới một **{Product}** (chỉ bằng id — Product thuộc BC khác).

## Đối thoại mẫu (minh hoạ term tương tác)
> "Khi khách **đặt** một **{Order}**, ta khoá **{Price}** tại thời điểm đó, kể cả **{Product}** đổi giá sau."

## Mâu thuẫn / cần SA xác nhận
| Term | Vấn đề | Câu hỏi SA |
| :--- | :--- | :--- |
| {term} | code dùng 2 tên lẫn lộn | [TBD — SA verify] |
