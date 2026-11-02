---
cases_count: 6
---

# Checkbox Rule

## Mục đích

Sinh testcase cho các lựa chọn Checkbox (Multiple choice).

## Điều kiện kích hoạt

Khi form có nhóm Checkbox hoặc nút Checkbox.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Kiểm tra trạng thái mặc định.
2. Tick chọn 1 option.
3. Tick chọn nhiều option.
4. Tick chọn tất cả option (Select All - nếu có).
5. Bỏ tick 1 option đang chọn.
6. Bỏ tick tất cả (Clear All - nếu có).

## Expected chuẩn

- Checkbox: Cho phép chọn nhiều giá trị, trạng thái tick/untick lưu đúng.

## Điều kiện cần Q&A

Tạo Q&A nếu:
- Cần làm rõ có giá trị Default nào không.
- Có logic phụ thuộc (chọn Checkbox A thì hiện thêm field B không).
