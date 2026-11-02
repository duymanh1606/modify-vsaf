---
cases_count: dynamic
---
# Error Response Behavior Rule

## Mục đích

Sinh testcase cho danh mục mã lỗi (error-code catalog) mà spec đặc tả hành vi hệ thống per-code, phủ ĐỦ và ĐÚNG mọi phản hồi + side-effect — không rút gọn về "hiện lỗi".

## Điều kiện kích hoạt

Kích hoạt khi tài liệu (`_detailed_design`/API spec — phần Logic/Dữ liệu) có bảng/danh mục mã lỗi kèm hành vi phản hồi per-code (message, side-effect UI, HTTP status). Bao trùm mọi tầng: validation nghiệp vụ, conflict, phân quyền, tích hợp downstream.

> **Ranh giới (MECE):** provoke lỗi hạ tầng (timeout/circuit-breaker/cache/session) thuộc [backend-resilience-rule](../10-be/backend-resilience-rule.md); cơ chế lỗi inline theo field thuộc [inline-error-rule](./inline-error-rule.md). Rule này chỉ sở hữu việc phủ ĐỦ hành vi phản hồi per-code (đặc biệt side-effect UI).

## Nguyên tắc phủ (mỗi mã lỗi `<code>` trong catalog)

1. Tái lập đúng điều kiện kích hoạt `<code>` theo spec.
2. Assert HTTP status / `error_code` trả về (nếu spec nêu).
3. Assert nội dung message verbatim (cấm paraphrase).
4. Assert TỪNG side-effect đặc tả là 1 dòng độc lập: đổi trạng thái control (uncheck/disable/lock), badge/marker, focus, điều hướng, KHÔNG-tự-retry, giữ/dọn input…
5. Assert exclusivity: chỉ phản hồi của `<code>` xuất hiện (xem [kbkt-format-rule §Chất lượng Expected](../00-core/kbkt-format-rule.md)).

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** mỗi cặp (mã lỗi × side-effect) là 1 testcase độc lập. Cấm gộp nhiều side-effect vào 1 Expected "hiện lỗi phù hợp".

## Expected chuẩn

Phân tầng UI → DB → API → Log; liệt kê từng side-effect rời:

```text
**UI:** hiển thị đúng 1 <thông báo verbatim>; <control liên quan> chuyển <trạng thái đặc tả>; không xuất hiện thông báo khác.
**API:** HTTP <status> (`<error_code>`).
**DB:** <trạng thái dữ liệu — không tạo bản ghi rác / rollback>.
```

## Điều kiện reject

- Gộp nhiều mã lỗi hoặc nhiều side-effect vào 1 case.
- Bỏ side-effect đặc tả (badge, uncheck, no-retry, focus, navigation).
- Expected chung chung "báo lỗi phù hợp" / thiếu exclusivity.
- Tự suy hành vi per-code không có trong catalog → Q&A.
