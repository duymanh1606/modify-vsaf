# {SCOPE} — Adversarial Code Review — v{N}

<!-- QUY ƯỚC OKF: mỗi finding mang ĐÚNG MỘT dòng "okf-finding:" đặt NGAY DƯỚI heading của
     nó. Dòng đó — không phải tiêu đề, không phải hàng bảng — là thứ định nghĩa "một finding".
     Bộ trích ĐẾM MARKER, không đoán heading.

     Vì sao phải thế: một bản review điển hình liệt kê cùng một finding ở HAI nơi — bảng tóm
     tắt (chỉ mục) và mục chi tiết (nội dung). Nếu máy nhận diện finding bằng hình dạng văn
     bản thì nó phải chọn: đếm bảng, đếm heading, hay đếm cả hai. Đếm cả hai biến 6 finding
     thành 12. Đó là lỗi SỐ HỌC, không phải lỗi độ chặt, và không mẫu nhận dạng nào chữa được.
     Marker chữa được, vì nó xuất hiện đúng một lần cho mỗi finding.

     BẢNG TÓM TẮT KHÔNG BAO GIỜ MANG MARKER. Nó là chỉ mục, không phải nội dung.

     Đổi tiêu đề finding thì GIỮ NGUYÊN marker — id là danh tính, tiêu đề là văn xuôi. -->

| Trường | Giá trị |
| :--- | :--- |
| Scope | `{SCOPE}` — {mô tả phạm vi review: slice / unit / changeset} |
| Unit | `{UNIT-ID}` ({code repo}) |
| Changeset | {N file (x main + y test)}; {branch diff vs main \| working-tree chưa commit} |
| Review method | {3 lớp độc lập: Blind Hunter / Edge Case Hunter / Acceptance Auditor \| khác — ghi rõ} |
| Ngày review | {YYYY-MM-DD} |
| Test execution | {kết quả thật, có số. Không viết "đã chạy test" mà không có con số.} |
| **Verdict** | {🛑 BLOCKED \| 🟡 SHIP-WITH-DEBT \| ✅ CLEAN} — Blocker {n} · High {n} · Medium {n} · Low {n} |

---

## Tóm tắt

<!-- Bảng chỉ mục. KHÔNG đặt marker ở đây — xem QUY ƯỚC OKF ở đầu file. -->

| # | Finding | Mức | Trạng thái |
| :--- | :--- | :--- | :--- |
| B1 | {tiêu đề một dòng} | blocker | open |
| H1 | {tiêu đề một dòng} | high | fixed |

---

## Findings

<!-- Mỗi finding = một heading H3, kèm ĐÚNG MỘT dòng marker ngay dưới heading đó. Dòng
     marker là một comment HTML, nội dung bên trong theo dạng:

         okf-finding: {id} · severity: {mức} · status: {trạng thái} · location: {path}:{line}

     {id}      — {B|H|M|L}{số}. Chữ cái là mức, số đếm trong mức. Duy nhất trong file này.
                 KHÔNG lặp tên scope vào id: scope đã nằm ở tên file {SCOPE}_review.md.
     severity  — blocker | high | medium | low. Phải khớp chữ cái của {id}.
     status    — open | fixed | deferred | dismissed | decision-needed
     location  — path:line; bỏ trống nếu finding không neo vào một chỗ cụ thể.

     `dismissed` VẪN GHI LẠI, không xoá. Một finding bị bác là một quyết định đã ra; xoá
     đi thì lần review sau không biết nó từng được cân nhắc.

     Khối hướng dẫn này xoá đi khi viết báo cáo thật (xem các template DD/techspec — tài
     liệu thật không giữ lại phần chỉ dẫn). Để lại cũng không sai số: nó cố tình KHÔNG
     chứa dòng nào khớp mẫu marker, nên không bị đếm thành finding ma. -->

### B1 — {tiêu đề finding}
<!-- okf-finding: B1 · severity: blocker · status: open · location: {path}:{line} -->

**Vị trí** — {file:line, hàm/lớp}

**Nguyên nhân + ảnh hưởng** — {vì sao sai, và hỏng cái gì khi nó chạy. Nêu được kịch bản
đầu vào cụ thể → kết quả sai cụ thể, không nói chung chung.}

**Cách sửa đề xuất** — {sửa gì, ở đâu}

**Bằng chứng** — {test/log/diff chứng minh. Nếu chưa có bằng chứng, ghi "chưa có" — đừng
để trống như thể đã kiểm.}

---

## Nhật ký các vòng sửa

| Vòng | Ngày | Đã đóng | Còn mở | Bằng chứng |
| :--- | :--- | :--- | :--- | :--- |
| 1 | {YYYY-MM-DD} | {B1, B2} | {H1–H11} | {lệnh test + kết quả có số} |
