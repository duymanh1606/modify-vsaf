---
cases_count: 15
---
# Filter Rule Block Rule

## Mục đích

Sinh testcase cho khối `Quy tắc Lọc giá trị (Filter Rules)` trong màn hình cấu hình phụ thuộc.

## Điều kiện kích hoạt

Kích hoạt khi chức năng cho phép cấu hình quan hệ lọc giá trị theo thuộc tính cha/con.

## Thành phần cần kiểm tra

- Icon bộ lọc.
- Nội dung empty state.
- Button Thêm filter.
- Cụm Thuộc tính cha.
- Cụm Giá trị cha.
- Cụm Giá trị con cho phép.
- Icon `+` thêm cụm.
- Icon `-` xóa cụm.
- Button Lưu.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

### Empty state

1. Khi chưa có filter nào.
2. Hiển thị icon bộ lọc.
3. Hiển thị content dòng 1: chưa có filter nào.
4. Hiển thị content dòng 2: hướng dẫn bấm nút để thêm rule.
5. Button Thêm filter enable.

### Thêm filter

1. Nhấn button Thêm filter.
2. Hiển thị cụm Thuộc tính cha - Giá trị cha - Giá trị con cho phép.
3. Kiểm tra từng combobox trong cụm.
4. Kiểm tra icon `+`/`-` của cụm.

### Xóa filter

1. Xóa khi chỉ có 1 cụm chưa nhập dữ liệu.
2. Xóa khi chỉ có 1 cụm đã nhập dữ liệu.
3. Xóa cụm đầu/giữa/cuối khi có nhiều cụm.
4. Sau khi xóa hết, quay về empty state.
5. Xóa một thuộc tính đang làm cha của một thuộc tính phụ thuộc khác (Bắt lỗi cảnh báo không cho xóa).

### Ràng buộc Cấu hình Nâng cao (Advanced Configuration Constraints)

1. **Circular Dependency (Ràng buộc vòng)**: Báo lỗi khi người dùng cố tình cấu hình Cấp 1 phụ thuộc Cấp 2, và Cấp 2 lại được cấu hình phụ thuộc ngược lại Cấp 1 (VD: A -> B -> A). Cảnh báo rõ ràng để ngăn chặn vòng lặp vô tận.

## Expected chuẩn

Expected phải mô tả rõ trạng thái sau thao tác, ví dụ:

```text
Xóa cụm Thuộc tính cha - Giá trị cha - Giá trị con cho phép và hiển thị lại Khối Quy tắc Lọc giá trị (Filter Rules) gồm icon Bộ lọc, content Chưa có filter nào, content hướng dẫn và button Thêm filter enable.
```

## Điều kiện reject

- Không được chỉ ghi `Xóa thành công`.
- Không được bỏ qua empty state sau khi xóa cụm cuối.
