# OUTPUT WRITING RULES — An toàn Markdown + Ngôn ngữ hiển thị UI

> File này quy định cách **ghi đúng** testcase: (§1–3) bảo vệ định dạng Markdown Table khỏi vỡ/mất dữ liệu, và (§4) dùng ngôn ngữ End-User (UI Label) thay vì mã hệ thống trong mô tả kịch bản.

---

## 1. Bảo vệ phần cuối file (Placeholder Protection)
*   **[BÀN TAY SẮT - BẢO VỆ PHẦN CUỐI FILE]**: Khi chỉnh sửa bảng ở mục 5.2, BẠN TUYỆT ĐỐI NGHIÊM CẤM việc vô tình xóa, làm mất hoặc ghi đè các mục `5.3. Hướng dẫn Data & Environment Setup (E2E)` và `5.4. Defect Management` (các phần placeholder) ở cuối file.
*   Khi dùng công cụ edit file (`replace_file_content` hoặc `multi_replace_file_content`), chỉ khoanh vùng thay đổi trong phạm vi bảng của mục 5.2, giữ nguyên toàn vẹn nội dung từ mục 5.3 trở đi.

## 2. Bảo vệ cấu trúc bảng Markdown (Markdown Table Integrity)
*   **[BÀN TAY SẮT - AN TOÀN CẤU TRÚC MARKDOWN TABLE]**: Khi thực hiện ghi đè hoặc bổ sung (append/edit) bảng 11 cột, bạn BẮT BUỘC phải kiểm tra tính toàn vẹn của Markdown Table. 
*   Số lượng ký tự phân tách cột `|` của dòng vừa sinh/cập nhật PHẢI KHỚP hoàn toàn với dòng tiêu đề (header) của bảng (đủ 12 ký tự `|` để tạo ra đúng 11 cột — đã thêm cột `Exec`). Tuyệt đối không để xảy ra tình trạng thiếu `|` làm vỡ cấu trúc hiển thị hoặc mất cột của bảng.

### 2.1. Bọc backtick token phá bảng (HTML tag / ký tự đặc biệt) — BẮT BUỘC
*   **[BÀN TAY SẮT - BỌC BACKTICK TOKEN PHÁ BẢNG]**: Mọi ô bảng chứa **token phá cấu trúc markdown** BẮT BUỘC bọc trong backtick (inline code `` `...` ``) để render literal. Nếu để trần, trình render diễn giải chúng và **vỡ bảng từ dòng đó trở đi** (bug kinh điển: payload `<script>` trong cột "Các bước"/"Kết quả" nuốt hết phần còn lại của bảng).
*   Token nguy hiểm cần bọc backtick:
    *   **Thẻ HTML thô `<tag>`** (vd `<script>`, `<b>`, `<img src=x onerror=...>`, `<script>alert(1)</script>`) — điển hình là payload XSS/HTML của case `security-input`/`textbox-base`. Xuất hiện ở **mọi cột** (Data Test, Các bước, Kết quả mong muốn). CẤM để `"<script>"` trần trong dấu nháy kép ở cột prose — dù cột Data Test đã bọc backtick, khi NHẮC LẠI payload ở Bước/Kết quả PHẢI bọc backtick lại.
    *   Ký tự `|` literal trong nội dung ô (khác dấu phân cột) → escape `\|` hoặc bọc backtick.
*   ⚠️ Đây KHÔNG phải vi phạm §4.2 (cấm mã hệ thống): payload test là dữ liệu hợp lệ, chỉ cần bọc backtick để an toàn hiển thị.
*   **Quét cơ học bắt buộc TRƯỚC khi ghi file** (grep-able, đưa vào enforcement ở [testcase_generation_gates.md §1.2 mục 9](testcase_generation_gates.md)): chạy `grep -nE '"<[a-zA-Z/]' <file_markdown>` — **phải RỖNG**. Còn kết quả (chuỗi mở nháy kép + thẻ HTML thô) → bọc backtick hết rồi mới ghi. Cách sửa nhanh khi đã lỡ ghi: `perl -i -pe 's/"(<[^"]*>[^"]*)"/` + "`" + `$1` + "`" + `/g' <file>`.

## 3. Sinh phân mảnh (Chunked / Iterative Writing)
*   Đối với các bảng testcase dài, tuyệt đối không cố ghi toàn bộ file trong một lượt chạy duy nhất nếu số lượng token quá lớn.
*   Hãy chia nhỏ quá trình ghi thành nhiều lần xuất (ví dụ: tối đa 15-20 cases/lần) và sử dụng công cụ chỉnh sửa trực tiếp vào file đó để cập nhật tiếp.
*   Tuyệt đối cấm viết tắt, tóm tắt, sử dụng dấu `...` hoặc "tương tự" để trốn tránh việc ghi đủ chi tiết.

## 4. Ngôn ngữ hiển thị UI (UI Label & End-User Language)

> Mô tả kịch bản dưới góc nhìn End-User / Manual Tester, không lộ mã hệ thống.
> **Phạm vi bề mặt:** §4.1 (Navigation Anchor) chỉ áp cho bề mặt **`ui`**. Bề mặt **`service`** (no-UI) áp §4.3. §4.2 (cấm mã hệ thống nội bộ) áp cho MỌI bề mặt.

### 4.1 Navigation Anchor chuẩn *(bề mặt `ui`)*
*   **[BÀN TAY SẮT - Navigation Anchor Rule]**: Bước đầu tiên của mỗi testcase phải dùng đúng tên màn hình truy về phần Giao diện (Kiến trúc thông tin / IA) trong `_detailed_design`.
    *   Tên màn hình = trường "Tên màn hình" / "Sidebar menu item" (VD: "Menu Quản lý yêu cầu").
    *   Tên nút CTA = tên control trong phần Giao diện của `_detailed_design` (VD: "Nút [+ Tạo yêu cầu]"). Route = trường "Route".
    *   **NGHIÊM CẤM TỰ ĐẶT TÊN MÀN HÌNH THEO CẢM TÍNH.**

### 4.2 Cấm mã hệ thống nội bộ trong mô tả
*   Trong cột "Các bước thực hiện" và "Kết quả mong muốn", TUYỆT ĐỐI KHÔNG viết mã Component/WBS nội bộ như `WGT-MODULE-TABBAR`, `SCR-COMPOSE`, `HUB-01`.
*   *(ui)* PHẢI viết dưới góc nhìn End-User (SAI: "Truy cập WGT-MODULE-TABBAR" → ĐÚNG: "Truy cập menu điều hướng chính, chọn mục 'Yêu cầu của tôi'").
*   Mã hệ thống nội bộ CHỈ ĐƯỢC xuất hiện ở cột Logic Ref / phần tham chiếu `rule:`.

### 4.3 Contract Anchor chuẩn *(bề mặt `service` — no-UI)*
*   Bước đầu tiên của mỗi testcase mô tả **gọi operation/endpoint** theo Contract Map (từ `_detailed_design`), KHÔNG dùng tên màn hình.
    *   Định danh operation = `METHOD /path` hợp đồng (VD: `POST /api/v1/transfers`) hoặc tên operation nghiệp vụ — đây là **contract detail**, KHÔNG phải "mã WBS nội bộ" nên được phép ghi. Field request/response dùng tên trong hợp đồng.
    *   **NGHIÊM CẤM TỰ ĐẶT endpoint/tên field THEO CẢM TÍNH** — phải truy về Contract Map (R1).
*   Vẫn cấm lộ mã WBS nội bộ (`HUB-01`, `MPF-02`…) trong mô tả case (§4.2); mã đó chỉ ở phần `@svc:`/`rule:`/Logic Ref.
