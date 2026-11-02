# RÀ SOÁT ĐIỂM CHƯA RÕ (AMBIGUITY AUDIT) — {id}

**Đối tượng:** {id} · **Ngày:** {timestamp}
**Mục tiêu / phạm vi demo (nếu là slice):** {mô tả 1 dòng điều cần build/demo}

### 📚 Tài liệu tham chiếu (đọc trước)

> Bảng này đặt **NGAY ĐẦU** báo cáo (không để cuối). Cột đầu là **tên file ĐẦY ĐỦ** (KHÔNG viết tắt `DD`/`L2`/`M0`), bọc link tương đối từ root workspace để bấm mở được.

| Tên file (bấm để mở) | Vai trò | Phiên bản |
|:---|:---|:---|
| [{ĐV}_detailed_design.md]({detailed_design_root}/{ĐV}_detailed_design.md) | Thiết kế chi tiết (DD) của {ĐV} | {vN} |
| [{module}_techspec.md]({techspec_root}/{module}_techspec.md) | TechSpec Layer 2 — source-of-truth hiện hành | {vN} |
| [00_system_connectivity_integration.md]({architecture_root}/00_system_connectivity_integration.md) | Module 0 — contract kết nối | {vN} |
| [prd.md / ux_design.md / project_wbs.md]({...}) | Nguồn đối chiếu bổ sung (khi có) | {vN} |

**Cách dùng báo cáo:** mỗi dòng là 1 điểm đang **mâu thuẫn** hoặc **chưa rõ**. Trong cột *Vấn đề*, **mỗi trích dẫn đặt ở ĐẦU dòng làm nhãn in đậm** — ghi **tên file ĐẦY ĐỦ · §mục · (dòng N)** và **bấm được** (click nhảy thẳng tới đúng dòng). PO/Lead điền **A/B/C** vào cột *Trả lời*, rồi tick cột *Trạng thái*. Chỉ bắt đầu viết testcase khi **mọi dòng 🔴 Cao** = Resolved.
**Cột Trạng thái:** **Todo** (mới, chưa ai phản hồi — mặc định) · **Resolved** (đã có câu trả lời ở cột Trả lời) · **Pending** (đã trả lời nhưng cần làm rõ thêm).

> [!IMPORTANT]
> **Quy ước viết cột "Vấn đề" (bắt buộc — để ai đọc cũng hiểu):** KHÔNG viết cụt kiểu điện tín, KHÔNG nhồi nhiều nguồn vào 1 câu dài. Mỗi ô gồm 1 **tiêu đề đậm** + các dòng có **NHÃN CỐ ĐỊNH**, mỗi nguồn 1 dòng, **trích dẫn clickable đặt ở ĐẦU dòng**:
> - `**{tiêu đề ngắn}.**`
> - `**[{tên file đầy đủ} §{mục} · dòng {N}]({link}#L{N}):** {file này nói gì}` — lặp 1 dòng cho MỖI nguồn mâu thuẫn (DD, techspec, Module 0…).
> - `**⇒ Hậu quả:** {chặn demo / expected mơ hồ / lọc sai…}`.
>
> Link = đường dẫn tương đối từ root workspace + anchor `#L{N}` (dùng dòng đầu nếu là range). Cột "Phương án" liệt kê sẵn A/B/C, dấu **✓** = khuyến nghị; PO điền lựa chọn vào cột "Trả lời" rồi tick "Trạng thái".

---

## 1. ĐÃ ĐỌC GÌ (Pre-flight — kiểm tra độ phủ đầu vào)

| Unit | Loại | DD đọc? | Ghi chú |
|:---|:---|:---:|:---|
| {unit} | BE/FE | {OK/MISSING/N/A} | |

> **Coverage verdict:** {đã đọc file DD của mọi unit? PASS / ghi ngoại lệ}. **Phần Đảm bảo chất lượng / Kiểm thử KHÔNG đọc** (chứa KBKT nhúng sẵn — không dùng để audit).
> **Tài liệu nguồn đã đối chiếu:** Module 0, {module}_techspec, ux_design, prd, project_wbs.

---

## 🔴 MỨC CAO — bắt buộc chốt trước khi viết testcase

> Blocker luồng chính / khiến fixture fail / khiến cột "Kết quả mong muốn" mơ hồ. Gate GENERATE chỉ mở khi **mọi dòng 🔴 = Resolved**.

| Mã | Trạng thái | Vấn đề là gì & vì sao quan trọng | Phương án (✓ = nên chọn) | Trả lời |
|:---|:---|:---|:---|:---:|
| GAP-01 | ☑&nbsp;Todo<br>☐&nbsp;Resolved<br>☐&nbsp;Pending | **{tiêu đề ngắn}.**<br>**[{FileA_đầy_đủ} §{mục} · dòng {X}]({linkA}#L{X}):** {FileA nói gì}.<br>**[{FileB_đầy_đủ} §{mục} · dòng {Y}]({linkB}#L{Y}):** {FileB nói gì}.<br>**⇒ Hậu quả:** {hậu quả cụ thể lên demo/test}. | **A✓** {hướng nên chọn}<br>**B** {hướng khác}<br>**C** {hướng khác} | |
| GAP-02 | ☑&nbsp;Todo<br>☐&nbsp;Resolved<br>☐&nbsp;Pending | **{tiêu đề}.**<br>**[{File} §{mục} · dòng {N}]({link}#L{N}):** {…}.<br>**⇒ Hậu quả:** {…}. | **A✓** …<br>**B** … | |

## 🟡 MỨC TRUNG BÌNH

> Sai logic nhánh / ranh giới (boundary) / mã lỗi.

| Mã | Trạng thái | Vấn đề là gì & vì sao quan trọng | Phương án (✓ = nên chọn) | Trả lời |
|:---|:---|:---|:---|:---:|
| GAP-… | ☑&nbsp;Todo<br>☐&nbsp;Resolved<br>☐&nbsp;Pending | **{tiêu đề}.**<br>**[{File} §{mục} · dòng {N}]({link}#L{N}):** {…}.<br>**⇒ Hậu quả:** {…}. | **A✓** …<br>**B** … | |

## ⚪ MỨC THẤP

> Hiển thị / định dạng / làm rõ nhỏ — không chặn viết testcase.

| Mã | Trạng thái | Vấn đề là gì & vì sao quan trọng | Phương án (✓ = nên chọn) | Trả lời |
|:---|:---|:---|:---|:---:|
| GAP-… | ☑&nbsp;Todo<br>☐&nbsp;Resolved<br>☐&nbsp;Pending | **{tiêu đề}.**<br>**[{File} §{mục} · dòng {N}]({link}#L{N}):** {…}.<br>**⇒ Hậu quả:** {…}. | **A✓** … | |

---

## GHI CHÚ

**Vệ sinh tài liệu (không chặn viết testcase — nên gửi người chủ tài liệu sửa để tránh lệch tiếp):**
- {vd: số phiên bản / số dòng techspec lệch giữa các unit — trích **tên file đầy đủ + link dòng**}.
- {vd: version Module 0 mỗi nơi ghi một kiểu — trích file}.

**Viết testcase được ngay (không phải đợi mức Cao):** {liệt kê phần contract đã rõ, an toàn viết ngay — vd validation input, mã lỗi 4xx đã tường minh, happy path đã đủ}.

**Tổng: {N} điểm — 🔴 Cao: {a} · 🟡 Trung bình: {b} · ⚪ Thấp: {c}.**

---
*Đây là bước bắt buộc trước khi viết testcase — DỪNG chờ PO/Lead điền cột "Trả lời". Chỉ chuyển sang Mode 2 GENERATE khi **mọi dòng 🔴 Cao** = Resolved.*

<!--
GHI CHÚ CHO AI (không render — hướng dẫn sinh báo cáo):
1. Bố cục cố định: (1) header + **bảng "📚 Tài liệu tham chiếu" đặt NGAY ĐẦU** (cột đầu = tên file ĐẦY ĐỦ bọc link tương đối từ root workspace, kèm phiên bản) + "Cách dùng" + Cột Trạng thái → (2) mục 1 pre-flight → (3) 3 bảng theo mức 🔴/🟡/⚪, mỗi mức 1 bảng, CÙNG 5 cột THEO THỨ TỰ (Mã · Trạng thái · Vấn đề · Phương án · Trả lời) → (4) GHI CHÚ. KHÔNG để bảng tài liệu tham chiếu xuống cuối.
2. KHÔNG tách bảng "§2b cross-document" riêng. Mâu thuẫn cấp tài liệu (Module 0 / techspec / ux / prd lệch nhau, hoặc 1 file tự mâu thuẫn) → đưa thành GAP trong 3 bảng theo mức (nếu ảnh hưởng testcase) HOẶC gộp vào mục "Vệ sinh tài liệu" ở GHI CHÚ (nếu chỉ là drift version/số dòng, không chặn test). Luôn trích tên file đầy đủ + §/dòng.
3. Cột "Vấn đề" = 1 tiêu đề đậm + các dòng có NHÃN CỐ ĐỊNH, MỖI nguồn 1 dòng, **trích dẫn clickable ĐẶT Ở ĐẦU DÒNG** dạng `**[tên file đầy đủ §mục · dòng N](link#LN):** nội dung`, kết thúc bằng dòng `**⇒ Hậu quả:** …`. TUYỆT ĐỐI KHÔNG viết tắt tên file (không `DD`/`L2`/`M0`), KHÔNG telegraphic, KHÔNG để trích dẫn trôi về cuối câu.
4. Link trích dẫn: đường dẫn tương đối từ root workspace + anchor `#L{N}` (VSCode/GitHub nhảy thẳng tới dòng). Range dòng → dùng dòng đầu cho anchor, ghi "dòng X–Y" ở nhãn.
5. Cột "Trạng thái" = cột 2 (ngay sau Mã), 3 checkbox stack mặc định "☑ Todo / ☐ Resolved / ☐ Pending" (dùng &nbsp; giữa ô và nhãn + <br> xuống dòng). PO đổi sang Resolved khi có Trả lời, hoặc Pending nếu cần làm rõ thêm.
6. Đánh số GAP liên tục xuyên suốt 3 bảng (GAP-01, 02, … không reset theo mức).
7. Gate: đánh dấu 🔴 cho mọi điểm chặn viết testcase; các điểm này phải = Resolved trước khi sang Mode 2 GENERATE.
-->
