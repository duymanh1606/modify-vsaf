# Nguyên Tắc Traceability E2E Xuyên Lớp (UI -> API -> DB -> UI)

> **Mục đích:** Quy định bắt buộc E2E Traceability cho mọi kịch bản kiểm thử Happy Path thay đổi dữ liệu (Create, Update, Delete, Approve, Reject).
>
> **Phạm vi bề mặt:** §1–§2 dưới đây là chuỗi cho bề mặt **`ui`** (có màn hình). Bề mặt **`service`** (no-UI: API/service/job/consumer) áp §3.

---

## 1. Quy tắc Kiểm tra E2E Xuyên Lớp (Full Traceability)

Mỗi testcase Happy Path E2E bắt buộc phải mô tả rõ các bước đi qua 4 tầng trong cột **Các bước thực hiện** và **Kết quả mong muốn**:

1. **UI Điểm Nhập (Entry UI):** Thao tác điền dữ liệu và nhấn nút CTA trên màn hình hiện tại.
2. **API (Tùy chọn):** Nêu network call (endpoint, HTTP Code) nếu specs có đặc tả.
3. **DB:** Xác định câu lệnh truy vấn SQL kiểm tra Bảng (Table) nào, trạng thái bản ghi thế nào sau khi lưu. Với kịch bản **tạo mới**, áp thêm §1.1 (kiểm đủ trường).
4. **UI Phản ánh (Destination UI):** Kiểm tra sự thay đổi dữ liệu trên màn hình đích (đọc từ phần Giao diện của màn đích).
   - *Ràng buộc:* Cấm ghi chung chung kiểu "Kiểm tra bản ghi hiển thị đúng". Bắt buộc chỉ rõ:
     - **Vị trí hiển thị:** (ví dụ: dòng đầu tiên của bảng do sort DESC, hay hiển thị ở tab nào).
     - **Định dạng & Trạng thái:** (ví dụ: badge màu xanh chữ "Chờ duyệt", icon sub-link, marker ★).

## 1.1. Tạo mới — kiểm LƯU ĐỦ TRƯỜNG trong DB (bắt buộc)

Áp cho **mọi thao tác tạo mới bất kỳ thực thể nào**, cả `ui` lẫn `service`. Bước DB không được dừng ở "có 1 bản ghi" / "trạng thái = X":

1. **Liệt kê đủ trường** theo Dữ liệu / ERD / Data Dictionary của `_detailed_design` — gồm trường nhập tay, trường hệ thống sinh và trường mặc định không hiện trên form.
2. **Mức kiểm = có dữ liệu** (khác NULL/rỗng). KHÔNG so nguyên văn với giá trị nhập vì trường có thể mã hóa/hash — chỉ kiểm có giá trị, đúng kiểu/độ dài.
3. **Chỉ so giá trị** khi đặc tả nói rõ trường lưu nguyên bản.
4. **Bảng phụ thuộc** (bản ghi con, liên kết, nhật ký) kiểm cùng nguyên tắc + đúng số dòng.
5. Viết **liệt kê từng trường**, không gộp một câu. Đặc tả không nêu lưu dạng gì → Q&A, cấm tự suy.

> Lỗi hay lọt: bản ghi vào DB nhưng vài trường bị rơi/để rỗng — kiểm "tồn tại bản ghi" không thấy.

## 2. Điều kiện Reject (bề mặt `ui`)
Bất kỳ kịch bản Functional/E2E nào thiếu bước check DB hoặc thiếu verify hiển thị chi tiết tại màn hình đích đều bị coi là không đạt tiêu chuẩn (shallow testcase) và sẽ bị Reject.
Kịch bản **tạo mới** mà bước DB chỉ kiểm sự tồn tại / trạng thái, không liệt kê kiểm đủ trường đã lưu theo §1.1, cũng bị Reject.

## 3. Traceability cho bề mặt `service` (no-UI)
Không có "màn hình đích". Chuỗi xuyên lớp cho Happy Path thay đổi dữ liệu là **Request → API → DB → MSG → Log**:

1. **Request (Điểm nhập):** payload + header (auth, `Idempotency-Key`…) gửi tới operation/endpoint.
2. **API:** HTTP status + **assert body/schema** trả về (không chỉ "trả 200").
3. **DB (side-effect):** truy vấn bảng/cột bị tác động — trạng thái bản ghi sau xử lý (hoặc 0 row / bút toán đảo khi là nhánh lỗi). Cấm ghi chung chung; chỉ rõ bảng + điều kiện + trạng thái kỳ vọng. Operation **tạo mới** phải kiểm đủ trường đã lưu theo §1.1.
4. **MSG (nếu có):** event/message phát ra outbox/topic — tên event + số lượng đúng (vd idempotency: đúng 1 event).
5. **Log:** audit trail append-only (ai/làm gì/khi nào), nếu spec đặc tả.

**Điều kiện Reject (service):** kịch bản Functional/E2E thay đổi dữ liệu mà **thiếu assert side-effect** (DB, và MSG nếu operation phát event) — chỉ dựa vào HTTP status — bị coi là shallow và sẽ bị Reject. "Verify màn hình đích" ở §2 được **thay bằng** assert side-effect này.
