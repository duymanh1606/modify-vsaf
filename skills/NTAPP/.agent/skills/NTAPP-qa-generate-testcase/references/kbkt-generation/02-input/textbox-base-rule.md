---
cases_count: 21
---

# Textbox Base Rule

## Mục đích

Sinh bộ testcase nền cho các trường textbox/searchbox.

## Điều kiện kích hoạt

Kích hoạt khi field có loại:

- Textbox
- Searchbox
- Textarea
- Input text
- Mã code dạng text

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

### Nhóm hiển thị và trạng thái

1. Kiểm tra hiển thị field.
2. Kiểm tra placeholder.
3. Kiểm tra default value.
4. Kiểm tra enable/disable/readonly.
5. Kiểm tra focus vào field.

### Nhóm dữ liệu nhập

1. Nhập ký tự số.
2. Nhập chữ in hoa.
3. Nhập chữ in thường.
4. Nhập tiếng Việt có dấu.
5. Nhập ký tự đặc biệt.
6. Nhập HTML tag.
7. Nhập JavaScript snippet.
8. Nhập khoảng trắng.
9. Nhập dữ liệu hợp lệ.
10. Nhập dữ liệu không hợp lệ theo business rule.

### Nhóm thao tác

1. Copy/paste dữ liệu hợp lệ.
2. Copy/paste khoảng trắng.
3. Copy/paste ký tự đặc biệt.
4. Xóa giá trị.
5. Focus out.
6. Nhấn Enter khi đang focus.

## Expected chuẩn

Expected phải phụ thuộc rule field:

- Nếu field cho nhập tự do: hệ thống cho nhập và hiển thị đúng dữ liệu.
- Nếu field chặn khoảng trắng: khoảng trắng không được hiển thị trong field.
- Nếu field trim space khi paste: dữ liệu được tự động loại bỏ khoảng trắng đầu/cuối.
- Nếu field readonly/disable: không cho nhập, không focus hoặc focus theo spec.

## Điều kiện reject

- Không được mặc định mọi textbox đều cho nhập HTML/JS thành công nếu spec yêu cầu chặn.
- Không được mặc định field trim space nếu tài liệu không nói rõ.
- Không được bỏ qua placeholder với searchbox.
