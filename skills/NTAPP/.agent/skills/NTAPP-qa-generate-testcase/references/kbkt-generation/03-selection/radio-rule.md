---
cases_count: 4
---

# Radio Rule

## Mục đích

Sinh testcase cho các lựa chọn Radio Button (Single choice).

## Điều kiện kích hoạt

Khi form có nhóm Radio button.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Kiểm tra trạng thái mặc định (có option nào được check sẵn không).
2. Click chọn 1 option.
3. Click chọn option khác (Kiểm tra option cũ bị uncheck tự động).
4. Click lại vào option đang chọn (với Radio, thường không cho phép uncheck bằng cách click lại).

## Expected chuẩn

- Radio: Chỉ cho phép chọn duy nhất 1 giá trị tại một thời điểm.

## Điều kiện cần Q&A

Tạo Q&A nếu:
- Cần làm rõ có giá trị Default nào không.
- Có logic phụ thuộc (chọn Radio A thì hiện thêm field B không).
