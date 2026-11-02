# STEP 02: EVIDENCE & PROPOSE (Phase 1 — Analyze)

> **Acting as:** Senior Engineer / Tech Lead
> **Tuân thủ:** [priority-resolution-rule.md](../references/priority-resolution-rule.md) (lõi — đọc trước), [no-hallucination-rule.md](../references/no-hallucination-rule.md)

## 1. Mục tiêu
Với **MỖI gap**, thu thập bằng chứng từ 4 nguồn, xác định chiều lệch, phân loại, và ra **đề xuất phương án có trích dẫn**. Đây là bước nặng nhất → chạy song song.

## 2. Song song hoá (bắt buộc cho report nhiều gap)
- Dispatch **1 subagent cho mỗi NHÓM gap cùng gốc** (nhóm đã lập ở Step 01) — không phải mỗi gap, để tránh đọc lặp cùng file nguồn. Nhóm độc lập → chạy song song.
- Mỗi subagent nhận: danh sách gap của nhóm + bảng giải mã ký hiệu + `code_repo_roots` + [priority-resolution-rule.md](../references/priority-resolution-rule.md). Subagent trả về phân tích per-gap theo mục 4.
- Dùng `general-purpose` agent (cần đọc file + grep code + git). Gom kết quả về theo `gap_id`.

## 3. Thu 4 nguồn cho mỗi gap (theo thứ tự ưu tiên câu hỏi A)

Với mỗi gap, mở ĐÚNG file + §/dòng được cite (đừng đọc mò), thu:

1. **Dữ liệu thực tế** — CHỈ nếu report cite (staging sample trong `f2`, giá trị thật). Ghi giá trị + nguồn. Report không cite → bỏ qua tầng này, KHÔNG tự query DB.
2. **TechSpec / Contract (SSoT)** — đọc đúng §/dòng canonical. Ghi giá trị canonical + số hiệu CR nếu có.
3. **DD (L3)** — đọc part BE/FE liên quan. Ghi giá trị + ngày sinh part (frontmatter/git).
4. **Code thực tế (câu hỏi B — hiện trạng)** — grep trong `code_repo_roots` tìm chỗ xử lý (validator, enum, controller, query…). Ghi:
   - **Hành vi code đang làm** (path:line).
   - **`git blame`/`git log`** dòng đó → ngày sửa gần nhất (để xác định chiều lệch).

> Thiếu nguồn quan trọng mà report kỳ vọng có (vd cite một §techspec nhưng file không tồn tại) → ghi `[Không tìm thấy nguồn X]`, KHÔNG bịa.

## 4. Xác định chiều lệch + phân loại (theo priority-resolution-rule §2, §3)

So 3 mốc thời gian (ngày CR TechSpec · ngày DD · ngày commit code) → gán đúng 1 nhãn:
- **stale-docs** · **code-mới-docs-cũ** · **lệch-code-vs-contract** (bug) · **mơ-hồ-nghiệp-vụ**

Một gap nhiều mặt → ghi từng mặt + nhãn từng mặt.

## 5. Ra đề xuất (per-gap)

Mỗi gap xuất khối phân tích gồm ĐỦ 6 phần (thiếu phần nào = chưa đạt):

1. **Tính năng ảnh hưởng** — unit/API/màn/luồng demo (từ Step 01).
2. **Bằng chứng 4 nguồn** — bảng: Nguồn | Giá trị/Hành vi | Trích dẫn (file §d.X hoặc path:line) | Ngày. Nguồn không có → ghi "—".
3. **Phân loại + chiều lệch** — nhãn + 1 câu lý do dựa trên mốc thời gian.
4. **Đề xuất chốt** — giá trị/hành vi canonical nên chốt + nguồn hậu thuẫn (theo thứ tự ưu tiên). Nếu `mơ-hồ-nghiệp-vụ` → ghi `[Cần PO chốt]` + liệt kê phương án & trade-off, KHÔNG tự chọn.
5. **Hiện trạng code (câu hỏi B)** — code đang làm gì, **khớp hay lệch** đề xuất, mức độ lệch.
6. **Việc cần làm nếu chốt phương án này** — liệt kê cụ thể: regen DD part nào / sửa §techspec nào / sửa file code nào (đề xuất diff) — đây là input cho Step 04. Kèm **file đích** của mỗi việc (để Step 04 gom).

> Nếu gap đã có `po_answer` (PO chốt): tôn trọng quyết định PO; phần "Đề xuất chốt" = xác nhận/triển khai theo PO, chỉ cảnh báo nếu phát hiện quyết định PO xung đột bằng chứng thực tế.

## 6. Output (in-memory, chuyển sang Step 03)
Khối phân tích 6 phần cho mỗi gap + danh sách "việc cần làm" kèm file đích (gom sẵn theo file để Step 04 dùng).
