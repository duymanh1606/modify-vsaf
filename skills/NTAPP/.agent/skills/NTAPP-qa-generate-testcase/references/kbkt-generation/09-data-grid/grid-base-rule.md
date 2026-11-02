---
cases_count: 9
---
# Data Grid Base Rule

## Mục đích

Sinh testcase kiểm tra thao tác hiển thị và quản lý bảng dữ liệu (Gridview / Data Table).

## Điều kiện kích hoạt

Khi màn hình có danh sách dạng bảng hiển thị nhiều bản ghi (gồm cả panel danh sách trong modal và list virtual-scroll).

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Empty State: hiển thị bảng khi không có dữ liệu (vd text "Không có dữ liệu").
2. Hiển thị tên và thứ tự các cột theo `_detailed_design`.
3. Phân trang mặc định: số bản ghi trên 1 trang đúng giá trị đặc tả (không mặc định 10).
4. Chuyển trang: sang trang 2, trang cuối.
5. Sắp xếp (Sorting) tăng dần/giảm dần theo cột ID hoặc cột Ngày tạo.
6. Thao tác trên dòng: xem chi tiết / sửa / xóa từng dòng (nút theo `_detailed_design`).
7. Thao tác hàng loạt: tick chọn nhiều dòng và xóa hàng loạt (nếu hỗ trợ).
8. Volume / chống cắt ngầm: seed số bản ghi khớp filter > page size đặc tả và > 10 (default framework); xác nhận mọi bản ghi truy cập được qua phân trang/scroll, không bị cắt ngầm. Assert theo count, không dựa "có dòng hiện".
9. Boundary phân trang (BVA): seed các mốc biên quanh page size — đúng 1 bản ghi, đúng bằng page size, page size + 1 (tràn trang 2 đúng 1 bản ghi); mỗi mốc assert số dòng/trang và tổng số trang khớp page size đặc tả. Mốc 1 bản ghi: chỉ 1 trang, không hiện điều hướng trang thừa.

## Expected chuẩn

- Bảng không vỡ layout khi nội dung text quá dài.
- Phân trang đúng logic, không tải lại toàn trang nếu dùng ajax.
- Sắp xếp đồng bộ dữ liệu đúng chiều.
- Số dòng hiển thị + tổng số bản ghi/tổng trang khớp nguồn sự thật: DB (COUNT theo cùng điều kiện) và/hoặc API `total`/`totalElements` — UI không thừa/thiếu so với DB/API.

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ:
- Số bản ghi mặc định trên một trang là bao nhiêu?
- Số bản ghi tối đa panel/list hiển thị (cap virtual-scroll) là bao nhiêu?
- Có cột nào cho phép sorting, cột nào không?
