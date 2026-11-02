---
cases_count: 9
---

# Cancel Button Rule

## Mục đích

Sinh testcase cho button Hủy/Đóng/Back.

## Điều kiện kích hoạt

Khi màn hình/form có button Hủy, Đóng, Back, icon X hoặc Cancel.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Kiểm tra hiển thị button.
2. Kiểm tra trạng thái enable/disable.
3. Click khi form chưa thay đổi dữ liệu.
4. Click khi form đã thay đổi dữ liệu.
5. Click khi đang có lỗi validate.
6. Click khi đang loading submit.
7. Kiểm tra điều hướng sau khi hủy.
8. Kiểm tra dữ liệu chưa lưu không bị ghi nhận.
9. Kiểm tra popup confirm nếu spec có.

## Expected chuẩn

- Nếu chưa sửa dữ liệu: đóng form/quay về màn trước theo spec.
- Nếu đã sửa dữ liệu: hiển thị confirm hoặc hủy không lưu theo spec.
- Dữ liệu đang chỉnh sửa không được lưu nếu user chọn hủy.

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ khi hủy form đã sửa dữ liệu:

- Có confirm không?
- Confirm message là gì?
- Điều hướng về đâu?
