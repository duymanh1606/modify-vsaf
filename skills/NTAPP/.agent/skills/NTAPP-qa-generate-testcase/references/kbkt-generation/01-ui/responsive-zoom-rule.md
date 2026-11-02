---
cases_count: 5
---

# Responsive Zoom Rule

## Mục đích

Kiểm tra màn hình khi thu nhỏ/phóng to trình duyệt hoặc zoom giao diện.

## Điều kiện kích hoạt

Áp dụng cho màn hình web.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

- Zoom out bằng `Ctrl -`.
- Zoom in bằng `Ctrl +` hoặc `Ctrl =`.
- Kiểm tra không vỡ layout.
- Kiểm tra không mất button chính.
- Kiểm tra không che khuất error message.

## Expected chuẩn

```text
Màn hình thu nhỏ/phóng to tương ứng và không bị vỡ giao diện. Các control chính vẫn hiển thị, không bị chồng lấn, không mất khả năng thao tác.
```
