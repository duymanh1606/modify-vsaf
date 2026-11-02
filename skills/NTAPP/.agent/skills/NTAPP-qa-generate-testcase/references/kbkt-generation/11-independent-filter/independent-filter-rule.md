---
cases_count: 18
---

# Independent Filter Rule

> [!NOTE]
> **Số lượng động:** `cases_count: 18` là phần cố định. Số case thực tế = 18 **+ N** (search per-field, mỗi trường lọc 1 case) **+ M** (tổ hợp combination). Planner cộng thêm N+M theo số trường lọc trong `_detailed_design`.

## Mục đích

Sinh testcase kiểm tra tìm kiếm & bộ lọc độc lập trên màn danh sách / form tìm kiếm (vd: lọc theo merchantCode, productCode đơn lẻ hoặc kết hợp).

## Điều kiện kích hoạt

Kích hoạt khi màn có ô nhập tìm kiếm / bộ lọc độc lập và nút Tìm kiếm/Reset.

## Thành phần cần kiểm tra

- Các trường lọc (Textbox, Dropdown, Datepicker...).
- Nút Tìm kiếm, nút Hủy lọc/Reset.
- Danh sách kết quả trả về và trạng thái rỗng (Empty State).

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

### Trạng thái mặc định

1. Trạng thái các trường lọc khi vừa mở form.
2. Dữ liệu hiển thị khi chưa áp dụng lọc.

### Thực thi tìm kiếm

1. Lọc chỉ bằng 1 trường (các trường khác trống), lặp cho từng trường (per-field): thực thi tìm kiếm và **đối soát danh sách trả về khớp điều kiện trường đó** — KHÔNG dừng ở validate giá trị nhập.
2. Lọc kết hợp ≥2 trường theo toán tử spec (AND/OR): tổ hợp có kết quả, tổ hợp giao rỗng (Empty State), tổ hợp full-field.
3. Lọc với giá trị không tồn tại (Empty State).
4. Nhấn Enter tại ô lọc để tìm kiếm.
5. Thực thi tìm kiếm qua nút của màn (tên nút theo `_detailed_design`).
6. Tìm kiếm khớp một phần (Like) — chỉ trường nhập.
7. Tìm kiếm khớp chính xác (Equal) — chỉ trường nhập.
8. Tìm kiếm phân biệt/không phân biệt chữ hoa thường (Case Sensitivity).

### Reset bộ lọc

1. Xóa toàn bộ điều kiện tìm kiếm, đưa danh sách về mặc định (qua nút reset của màn — tên nút theo `_detailed_design`).

### Duy trì trạng thái

1. Giữ trạng thái bộ lọc khi quay lại từ màn hình khác.
2. Tải lại trang (F5/reload) khi đang áp lọc — khôi phục hoặc reset theo spec (im lặng → Q&A).
3. Mở deep-link URL có sẵn tham số lọc — áp đúng tham số; tham số không hợp lệ xử lý theo spec.

### Nhất quán trạng thái danh sách

1. Xóa tay hết giá trị mọi ô lọc (không qua Reset) — danh sách về mặc định, không giữ kết quả cũ (stale).
2. Đổi giá trị ô lọc nhưng chưa tìm lại — danh sách vẫn theo lần lọc hợp lệ gần nhất.
3. Áp lọc mới khi đang ở trang phân trang khác trang đầu — hành vi theo spec (im lặng → `[TBD-spec]` + Q&A); luôn assert không lộ trang trống.

### Xử lý dữ liệu nhập đặc biệt

1. Lọc với từ khóa chứa khoảng trắng hoặc ký tự đặc biệt.

## Nguyên tắc bắt buộc

> [!IMPORTANT]
> - **Validate ≠ Search:** mỗi trường phải có CẢ case validate giá trị nhập LẪN case thực thi search + đối soát danh sách.
> - **Per-field:** N trường lọc → tối thiểu N case search độc lập; cấm gộp thành 1 case đại diện.
> - **Cơ chế so khớp** (Like/Equal/case-sensitivity) lấy từ `_detailed_design` — cấm suy đoán.
> - **Oracle nguồn sự thật:** data chuẩn bị gồm CẢ bản ghi khớp và KHÔNG khớp; assert **UI + ≥1 lớp (API và/hoặc DB)** theo thứ tự `kbkt-format-rule` UI → DB → API: mọi bản ghi trả về khớp `<filter_value>`, bản ghi không khớp vắng mặt, count parity. Cấm oracle dừng ở "list hiển thị / không rỗng". Thiếu tên API/param/bảng-cột để đối soát → `[TBD-spec]` + Q&A (không bịa endpoint/tên cột).

## Expected chuẩn

```text
Hệ thống lọc dữ liệu theo điều kiện <filter_value>; danh sách hiển thị đúng các bản ghi khớp, bản ghi không khớp bị ẩn (UI). Đối soát nguồn sự thật: DB (WHERE <cột> theo cơ chế spec) và/hoặc API response trả đúng và đủ bản ghi khớp + total khớp — các lớp phải nhất quán.
```

```text
Hệ thống hiển thị màn hình danh sách rỗng kèm hình ảnh minh họa (nếu có) và thông điệp: "Không tìm thấy kết quả phù hợp".
```

```text
Hệ thống reset tất cả các ô lọc về trống (hoặc giá trị mặc định), tự động tải lại và hiển thị danh sách dữ liệu đầy đủ ban đầu.
```

## Điều kiện reject

- Bỏ qua kịch bản reset/hủy lọc.
- Thiếu expected mô tả trạng thái danh sách sau khi lọc (khớp kết quả hay Empty State).
- Tự suy đoán cơ chế so khớp (Like/Equal) mà không đối soát `_detailed_design`.
- Oracle chỉ kiểm list hiển thị/không rỗng, không đối soát TỪNG bản ghi khớp filter.
- Chỉ validate giá trị nhập mà thiếu case thực thi search + đối soát danh sách cho trường đó.
- Per-field: N trường lọc nhưng chỉ có 1 case đại diện (thiếu case cho ≥1 trường).
- Thiếu case search kết hợp trường khi màn có ≥2 trường lọc, hoặc thiếu tổ hợp giao rỗng (Empty State).
- Oracle chỉ dừng ở lớp UI, không đối soát API/DB (trừ khi spec chỉ có UI — phải ghi rõ lý do).
- Empty state chỉ assert message, thiếu CTA/nút theo wireframe — xem [screen-default-display-rule §Độ đầy đủ theo STATE](../01-ui/screen-default-display-rule.md).
- Danh sách stale: hiển thị kết quả không khớp filter hiện tại khi đã xóa/đổi filter (spec im lặng → Q&A, cấm suy đoán).
- Thiếu case áp lọc mới khi ở trang khác trang đầu, hoặc expected tự suy đoán về-trang-đầu/giữ-trang mà không đối soát spec; bất biến "không lộ trang trống" luôn phải assert. Parity count xem [grid-base-rule §Volume](../09-data-grid/grid-base-rule.md).
- Thiếu case duy trì trạng thái khi F5/reload hoặc deep-link tham số lọc (khi spec hỗ trợ khôi phục qua URL); expected phải theo spec, cấm mặc định một chiều.
