---
cases_count: 7
---

# Dependent Combobox Rule

## Mục đích

Sinh testcase cho combobox phụ thuộc combobox khác.

## Điều kiện kích hoạt

Kích hoạt khi có quan hệ cha-con giữa các field, ví dụ:

- Thuộc tính cha -> Giá trị cha.
- Giá trị cha -> Giá trị con cho phép.
- Mã đối tác -> Mã hợp đồng.
- Nhóm thuộc tính -> Thuộc tính.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Chưa chọn field cha, kiểm tra field con.
2. Chọn field cha hợp lệ, kiểm tra danh sách field con.
3. Đổi field cha sau khi đã chọn field con.
4. Clear field cha sau khi đã chọn field con.
5. Field cha không có dữ liệu con.
6. Field cha có nhiều dữ liệu con.
7. Dữ liệu con đang chọn không còn hợp lệ sau khi đổi cha.

## Expected chuẩn

- Khi chưa chọn cha: field con disable hoặc empty theo spec.
- Khi chọn cha: field con load danh sách tương ứng.
- Khi đổi cha: field con phải reset nếu giá trị cũ không còn hợp lệ.
- Không giữ dữ liệu con sai quan hệ.

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ:

- Field con reset hay giữ nguyên khi đổi field cha.
- Field con disable hay enable rỗng khi chưa chọn cha.
- Message khi không có dữ liệu con.
