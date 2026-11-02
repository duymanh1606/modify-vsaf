---
cases_count: 6
---
# Duplicate Data Rule

## Mục đích

Sinh testcase kiểm tra dữ liệu trùng lặp.

## Điều kiện kích hoạt

Kích hoạt khi field có vai trò định danh hoặc mã duy nhất, ví dụ:

- Mã nhóm thuộc tính.
- Mã template.
- Tên template nếu business yêu cầu unique.
- Cặp quan hệ cha-con nếu không cho trùng.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Nhập giá trị chưa tồn tại.
2. Nhập giá trị đã tồn tại trong cùng màn hình.
3. Nhập giá trị đã tồn tại trong DB/hệ thống.
4. Nhập trùng khác hoa/thường nếu business không phân biệt case.
5. Nhập trùng sau trim space.
6. Nhập trùng trong nhiều dòng/cụm động.

## Expected chuẩn

- Với dữ liệu không trùng: cho phép lưu.
- Với dữ liệu trùng: hiển thị lỗi rõ vị trí và message.
- Không được lưu bản ghi trùng.

## Điều kiện cần Q&A

Tạo Q&A nếu chưa rõ:

- Có bắt unique không.
- Unique theo field đơn hay tổ hợp field.
- Có phân biệt hoa/thường không.
- Có trim trước khi check duplicate không.
