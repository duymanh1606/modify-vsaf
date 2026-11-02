---
cases_count: 14
---
# Dynamic Row Add Remove Rule

## Mục đích

Sinh testcase cho các cụm dữ liệu có icon `+` và `-`, ví dụ thêm/xóa nhóm thuộc tính hoặc filter rule.

## Điều kiện kích hoạt

Khi UI có khả năng thêm/xóa dòng/cụm control động.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

### Thêm dòng/cụm

1. Đang có 1 cụm, nhấn icon `+`.
2. Đang có nhiều cụm, nhấn icon `+` ở cụm đầu.
3. Nhấn icon `+` ở cụm giữa.
4. Nhấn icon `+` ở cụm cuối.
5. Kiểm tra cụm mới có đủ field theo spec.
6. Kiểm tra icon `+`/`-` sau khi thêm.
7. Kiểm tra default value của cụm mới.

### Xóa dòng/cụm

1. Đang có 1 cụm, nhấn icon `-`.
2. Đang có nhiều cụm, xóa cụm đầu tiên.
3. Đang có nhiều cụm, xóa cụm ở giữa.
4. Đang có nhiều cụm, xóa cụm cuối.
5. Xóa cụm đã nhập dữ liệu.
6. Xóa cụm chưa nhập dữ liệu.
7. Kiểm tra re-index nếu UI có số thứ tự.

## Expected chuẩn

- Khi thêm: hiển thị thêm đúng một cụm mới với đủ field.
- Khi xóa: chỉ xóa đúng cụm được chọn, không ảnh hưởng cụm khác.
- Với cụm cuối: sau khi xóa, cụm liền trước phải hiển thị icon phù hợp.
- Nếu còn 0 cụm, hiển thị empty state theo spec.

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ:

- Có cho xóa cụm cuối cùng không.
- Có popup confirm khi xóa dữ liệu đã nhập không.
- Có giới hạn số cụm tối đa không.
