---
cases_count: 15
---

# Combobox Base Rule

## Mục đích

Sinh testcase chuẩn cho combobox/dropdown/single-select/multi-select.

## Điều kiện kích hoạt

Khi DD/UI có control dạng combobox, dropdown, select, tree-select hoặc list option.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

### Hiển thị

1. Kiểm tra label combobox.
2. Kiểm tra placeholder.
3. Kiểm tra default value.
4. Kiểm tra icon mở danh sách.
5. Kiểm tra trạng thái enable/disable.

### Mở danh sách

1. Click vào combobox.
2. Kiểm tra danh sách option hiển thị.
3. Kiểm tra scroll nếu nhiều option.
4. Kiểm tra không có dữ liệu.
5. Kiểm tra loading nếu danh sách lấy từ API.

### Chọn dữ liệu

1. Chọn 1 giá trị.
2. Chọn lại giá trị khác.
3. Clear giá trị nếu có icon clear.
4. Chọn bằng keyboard.
5. Tìm kiếm nhanh nếu combobox có search.

## Expected chuẩn

- Danh sách option đúng nguồn dữ liệu.
- Giá trị được chọn hiển thị lên control.
- Nếu single select: chỉ có một giá trị được chọn.
- Nếu multi select: cho phép chọn nhiều giá trị và hiển thị đúng format.

## Điều kiện reject

- Không được sinh testcase chọn option nếu không biết nguồn option.
- Không được tự bịa danh sách option.
- Không được bỏ qua trạng thái empty/loading nếu dữ liệu lấy từ API.
