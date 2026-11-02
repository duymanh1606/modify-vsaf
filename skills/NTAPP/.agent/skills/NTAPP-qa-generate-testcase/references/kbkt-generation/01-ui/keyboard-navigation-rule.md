---
cases_count: 4
---

# Keyboard Navigation Rule

## Mục đích

Sinh testcase kiểm tra khả năng thao tác bằng bàn phím.

## Điều kiện kích hoạt

Áp dụng cho màn hình có input, button, combobox, checkbox, grid action hoặc popup.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Nhấn `Tab` liên tục.
2. Nhấn `Shift + Tab` liên tục.
3. Nhấn `Enter`.
4. Với combobox/dropdown: kiểm tra `Arrow Up`, `Arrow Down`, `Enter`, `Tab`.
## Expected chuẩn

- `Tab`: focus di chuyển lần lượt từ trái sang phải, từ trên xuống dưới.
- `Shift + Tab`: focus di chuyển ngược lại từ dưới lên trên, từ phải sang trái.
- `Enter`: nếu focus vào button thì thực hiện action của button; nếu không focus button thì thực hiện action chính theo spec.
- Combobox: cho phép mở danh sách, di chuyển option và chọn option bằng bàn phím.

## Lỗi cần chặn

- Không được sinh testcase keyboard nếu màn hình chỉ là view tĩnh không có focusable control, trừ khi workflow yêu cầu accessibility.
- Không được viết expected `Không lỗi`.
