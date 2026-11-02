---
cases_count: 6
range_cases_count: 8
---

# DatePicker Rule

## Mục đích

Sinh testcase kiểm tra trường nhập liệu dạng Ngày tháng (Date/Datetime).

## Điều kiện kích hoạt

Kích hoạt khi field có định dạng Date, Datetime, MonthYear hoặc là control DatePicker.

## Danh sách Testcase Bắt Buộc — 1 ô ngày đơn (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Nhập ngày không hợp lệ (ví dụ: `31/02/2026`, `99/99/9999`).
2. Nhập sai định dạng (ví dụ yêu cầu `dd/MM/yyyy` nhưng nhập `MM/dd/yyyy` hoặc chuỗi ký tự chữ).
3. Nhập ngày quá khứ (nếu business cấm).
4. Nhập ngày tương lai (nếu business cấm).
5. Chọn ngày từ Calendar widget.
6. Xóa ngày đã chọn (nếu trường không bắt buộc).

## Danh sách Testcase Bắt Buộc — CẶP KHOẢNG NGÀY (`fromDate` / `toDate`)

> Kích hoạt khi control là **cặp 2 ô ngày tạo thành 1 khoảng** (từ ngày / đến ngày, startDate/endDate…). Đây là case liên trường (cross-field) — cộng thêm vào cụm date-range.

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

7. Nhập `fromDate` lớn hơn `toDate` (nghịch đảo khoảng).
8. Nhập `fromDate` bằng `toDate` (cùng một ngày).
9. Nhập `fromDate` nhỏ hơn `toDate` (khoảng hợp lệ).
10. Chỉ nhập `fromDate`, bỏ trống `toDate`.
11. Chỉ nhập `toDate`, bỏ trống `fromDate`.
12. Bỏ trống cả `fromDate` và `toDate`.
13. Nhập khoảng vượt độ rộng tối đa cho phép (nếu business giới hạn max-span).
14. Chọn `fromDate` trên Calendar rồi kiểm tra `toDate` có bị chặn ngày trước `fromDate`.

## Expected chuẩn

- Hệ thống báo lỗi tương ứng khi nhập ngày sai định dạng hoặc không hợp lệ.
- Hiển thị đúng giá trị khi chọn từ Calendar.
- Trả về đúng format ngày yêu cầu khi lưu.
- Khoảng nghịch đảo (`fromDate > toDate`) → báo 1 lỗi liên trường nguyên văn theo spec, hoặc `[TBD]` + Q&A nếu spec im lặng (cấm tự chế message).

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ:
- Định dạng ngày tháng là gì (`dd/MM/yyyy` hay `yyyy/MM/dd`)?
- Có cho phép chọn ngày quá khứ/tương lai không?
- Cặp khoảng ngày: `fromDate == toDate` có hợp lệ không? Bắt buộc nhập đủ 2 ô hay cho mở 1 đầu? Có giới hạn max-span không? Message lỗi nghịch đảo nguyên văn là gì?
