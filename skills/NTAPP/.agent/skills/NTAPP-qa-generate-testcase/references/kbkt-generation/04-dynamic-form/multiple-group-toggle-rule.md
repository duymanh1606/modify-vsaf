---
cases_count: 12
---
# Multiple Group Toggle Rule

## Mục đích

Sinh testcase cho checkbox/toggle `Nhập nhiều nhóm` và field động `Mã nhóm thuộc tính`.

## Điều kiện kích hoạt

Kích hoạt khi màn hình có toggle/checkbox làm xuất hiện hoặc ẩn field khác.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Kiểm tra hiển thị mặc định của toggle.
2. Khi chưa tích chọn, field phụ thuộc phải không hiển thị hoặc disable theo spec.
3. Tích chọn toggle.
4. Kiểm tra màu/trạng thái toggle sau khi tích chọn.
5. Kiểm tra field phụ thuộc xuất hiện.
6. Kiểm tra field phụ thuộc enable.
7. Kiểm tra placeholder field phụ thuộc.
8. Bỏ tích chọn toggle.
9. Kiểm tra field phụ thuộc bị ẩn.
10. Kiểm tra dữ liệu field phụ thuộc có bị clear không khi ẩn.
11. Tích chọn lại sau khi đã nhập dữ liệu trước đó.
12. Kiểm tra validate required chỉ chạy khi field đang hiển thị/enable.

## Expected chuẩn

```text
Mặc định button Nhập nhiều nhóm hiển thị màu xám và chưa được tích chọn.
```

```text
Khi tích chọn, button Nhập nhiều nhóm chuyển sang trạng thái đã tích chọn, đổi màu theo thiết kế và hiển thị trường Textbox Mã nhóm thuộc tính*: enable bên dưới trường Nhóm thuộc tính.
```

```text
Khi bỏ tích chọn, button Nhập nhiều nhóm quay về màu xám và không còn hiển thị trường Textbox Mã nhóm thuộc tính*.
```

## Rule validate đi kèm

Nếu field động có dấu `*`, required validation chỉ áp dụng khi field đang active.

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ dữ liệu field phụ thuộc sau khi ẩn:

- Clear luôn?
- Giữ tạm trong state?
- Clear khi lưu?
