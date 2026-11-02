---
cases_count: 7
---

# Layout Visual Rule

## Mục đích

Sinh testcase kiểm tra chất lượng giao diện tổng thể: bố cục, font, chính tả, màu sắc, căn lề, khoảng cách.

## Điều kiện kích hoạt

Áp dụng cho mọi màn hình có UI.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

- Kiểm tra bố cục tổng thể.
- Kiểm tra độ dài/rộng của label, textbox, combobox, button.
- Kiểm tra font chữ, cỡ chữ, màu chữ.
- Kiểm tra căn lề trái/phải/trên/dưới.
- Kiểm tra chính tả, ngữ pháp, cấu trúc câu.
- Kiểm tra form không bị xô lệch.
- Kiểm tra form dễ sử dụng, đúng thứ tự đọc từ trên xuống dưới.

## Expected chuẩn

```text
Các label, textbox, combobox có độ dài, rộng và khoảng cách bằng nhau, không xô lệch.
Các label sử dụng cùng loại font, cỡ chữ, căn lề trái.
Không có lỗi chính tả, cấu trúc câu, ngữ pháp.
Form được bố trí hợp lý và dễ sử dụng.
```

## Điều kiện reject

Reject nếu testcase layout chỉ ghi `Kiểm tra giao diện` nhưng không có checklist cụ thể.
