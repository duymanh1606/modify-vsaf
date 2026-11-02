# KBKT Format Rule

> **Mục đích:** Quy chuẩn định dạng kịch bản kiểm thử manual bảng 11 cột (đã thêm cột `Exec` cho automation routing — xem [automation_contract_rules.md](../../../principles/automation_contract_rules.md)).

---

## 1. Phân chia 3 Khối kiểm thử (Multi-Block Rule)
Cấm gộp chung toàn bộ testcase vào 1 bảng. Bắt buộc chia làm 3 Khối/Bảng riêng biệt:
1. **Khối 1: Giao diện (UI):** Hiển thị mặc định, focus, tab-navigation, zoom/responsive, validate input (bắt buộc, maxlength, format, ký tự cấm), hành vi control (lọc combobox, checkbox đệ quy, popup).
2. **Khối 2: Chức năng (Functional):** Ràng buộc cơ sở dữ liệu, lỗi logic API/DB từ backend (mã PCS-), luồng nghiệp vụ E2E (lưu nháp, duyệt, Kafka).
3. **Khối 3: An toàn thông tin (ATTT):** Tấn công bypass client-side (API tampering, SQL Injection, IDOR, upload file shell). *Lưu ý:* Ký tự đặc biệt XSS trên UI thuộc Khối 1.

---

## 2. Định dạng cột và quy chuẩn viết

### Định danh ID liên tục
- Format: `KB-{id}-{RunningNumber}` (Ví dụ: `KB-SLICE-06-01`, `KB-SLICE-06-02`).
- Quy tắc liên tục: ID chạy liên tục xuyên suốt các Khối (Cấm chèn chữ phân loại như `KB-SLICE-06-UI-01` hay `KB-SLICE-06-FUNC-02`).

### Cách viết Mục đích kiểm thử
- Bắt buộc bắt đầu bằng từ khóa **"Kiểm tra"** hoặc **"Verify"**.
- *Đúng:* `Kiểm tra validate định dạng email.`
- Bắt buộc **cụ thể**: nêu rõ **đối tượng** (control/màn/API) + **khía cạnh** được kiểm; CẤM chung chung.
- *Đúng (cụ thể):* `Kiểm tra trường "Tên hồ sơ" nhận và hiển thị đúng ký tự tiếng Việt có dấu, không lỗi font/encode.`
- *Sai (generic):* `Kiểm tra nhập tiếng Việt có dấu.`

### Cách viết Các bước thực hiện
- Mô tả rõ hành động vật lý của Tester, không viết chung chung.
- *Ví dụ đúng:* 
  1. Mở màn hình Thêm mới template.
  2. Bỏ trống trường "Mã nhóm thuộc tính".
  3. Nhấn button "Lưu".
- Bắt buộc là **chuỗi thao tác vật lý đầy đủ** theo trình tự: **mở màn → định vị/focus control → nhập/tương tác → blur/quan sát/submit**. CẤM 1 bước cụt kiểu `(1) Nhập X`.
- CẤM bước **trống nghĩa** không nêu đối tượng/điểm quan sát: `(1) Quan sát.`, `(1) Nhập.`, `(1) Click ô.`, `(1) Mở trang.`, `(1) Đối chiếu thiết kế.` — phải chỉ rõ *control/vùng nào + nhìn cái gì* (vd `(1) Quan sát vùng header bảng: đếm số cột và đọc nhãn từng cột`). (Enforce: HARD CHECK "Chất lượng cột Các bước" — [testcase_generation_gates.md](../../../principles/testcase_generation_gates.md).)
- Mỗi bước **một dòng** — trong ô bảng markdown tách dòng bằng `<br>` (vd `(1) ... <br> (2) ... <br> (3) ...`).

### Cách viết Kết quả mong muốn (Expected Result)
- Mô tả rõ trạng thái quan sát được trên UI/API/DB/MSG/Log.
- Bắt buộc phân tầng expected result bằng thẻ bôi đậm (chỉ ghi tầng nào thực sự có), **mỗi tầng trên MỘT DÒNG riêng** — trong ô bảng markdown dùng `<br>` để tách dòng:
  - *(bề mặt `ui`)* thứ tự ưu tiên **UI → DB → API → Log**: **UI:**, **DB:**, **API:**, **Log:**. Dòng có hệ quả UI bắt buộc mở đầu bằng **UI:**.
  - *(bề mặt `service` — no-UI)* thứ tự **API → DB → MSG → Log**: **API:**, **DB:**, **MSG:**, **Log:**. KHÔNG có **UI:**. `MSG:` = event/message phát ra outbox/topic.
- *Ví dụ đúng (ui):* **UI:** Trường "Mã nhóm thuộc tính" hiển thị viền đỏ và báo lỗi inline: "Mã nhóm là bắt buộc".
- *Ví dụ đúng (service):* **API:** HTTP 422, body `errorCode = INSUFFICIENT_FUNDS`. <br> **DB:** bảng `transfers` không phát sinh bản ghi (0 row).

#### Chất lượng Expected (SSoT)
- **Deterministic:** mỗi Expected mô tả đúng 1 hành vi/trạng thái theo spec. Cấm nhánh chưa resolve ("chặn hoặc báo lỗi", "cắt hoặc …", "A/B"); spec không xác định → Q&A, không tự chọn.
- **Exclusivity:** khi spec định nghĩa 1 phản hồi cho 1 điều kiện, Expected phải khẳng định (a) đúng phản hồi đó, (b) vắng phản hồi khác cùng loại (chỉ 1 toast, không lỗi generic thừa; lỗi validation không phải lỗi hệ thống).
- **Content-match cho tập kết quả:** Expected của thao tác trả về danh sách phải mô tả sự khớp nội dung của TỪNG bản ghi với điều kiện, không dừng ở "danh sách hiển thị".
- **Provenance TEXT hiển thị (cấm bịa microcopy):** khi Expected khẳng định một **chuỗi hiển thị cụ thể** (placeholder / nhãn / option / message / empty-state / tiêu đề / tooltip) → chuỗi đó phải **verbatim từ nguồn** (i18n key hoặc phần Giao diện DD) **kèm cite** `(i18n: <key>)` / `(DD §x)`; nguồn rỗng/chưa dịch → ghi `[TBD]` + Q&A. **CẤM tự đặt text theo "UI thường thấy"/prior** (vd placeholder `"Tất cả"`). Kiểm *tồn tại* control mà chưa biết nội dung → phát biểu bằng trạng thái quan sát ("placeholder hiển thị, nội dung [TBD]"), KHÔNG dùng "có placeholder" trống nghĩa.

### Không gộp dòng (No Row Grouping)
- Mỗi trường hợp kiểm thử (biên, rỗng, sai định dạng...) phải nằm ở một dòng (Row) độc lập. Cấm gộp nhiều điều kiện test vào chung một ô.

### Bảng tra cứu UI Controls
- Bắt buộc sinh bảng tra cứu nhanh (Quick Reference Mapping) cho tất cả UI Controls ngay phía trên bảng kịch bản.

### Cột `Exec` (Automation routing)
- Cột áp chót (trước "Luồng ref"): giá trị `automate` | `manual` | `exploratory`, gán ở [Step 02b](../../../steps/step-02b-risk-allocation.md).
- `automate` → `/ntapp-qa-robot` sinh code + chạy; `manual` → tester chạy tay; `exploratory` → theo charter (Mục 5.5).
- Mỗi dòng `automate` phải có `@id` khớp 1-1 với một `Scenario` trong `{id}_testspec.feature` và một dataset trong `{id}_fixtures.yaml`.

---

## 3. Điều kiện Reject
- Thiếu bước (steps) hoặc expected result mơ hồ.
- Control không tồn tại trong specs/mockup.
- Tự bịa message lỗi khi specs không quy định (khi thiếu phải tạo danh sách câu hỏi Q&A dạng bảng).
