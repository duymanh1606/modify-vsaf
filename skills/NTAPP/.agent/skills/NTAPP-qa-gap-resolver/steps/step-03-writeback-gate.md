# STEP 03: WRITE-BACK & GATE 1 (Phase 1 — Analyze)

> **Acting as:** Senior Engineer / Tech Lead
> **Tuân thủ:** [priority-resolution-rule.md](../references/priority-resolution-rule.md), [no-hallucination-rule.md](../references/no-hallucination-rule.md)

## 1. Mục tiêu
Ghi kết quả phân tích Step 02 trở lại **report gốc**: điền đề xuất ngắn vào cột Trả lời + append section phân tích chi tiết. Rồi DỪNG chờ người dùng chọn gap xử lý.

## 2. Chỉ thị thực thi

### 2.1. Điền cột "Trả lời" của từng dòng GAP (đề xuất NGẮN)
Với mỗi gap CHƯA có `po_answer`:
- Ghi vào ô "Trả lời": `[AI đề xuất] <X> — <lý do 1 dòng + nguồn>`
  - Ví dụ: `[AI đề xuất] A — chốt theo HUB-ts §11.2.1 (d.1478); DD stale hơn CR-COMPOSE-1`
  - Nếu là `mơ-hồ-nghiệp-vụ`: ghi `[Cần PO chốt] — <câu hỏi nghiệp vụ>` (KHÔNG chọn A/B/C).
- Đổi cột **Trạng thái**: `Todo → Pending` (đã có đề xuất nhưng cần user xác nhận). Render đúng checkbox stack sẵn có của report: `☐&nbsp;Todo<br>☐&nbsp;Resolved<br>☑&nbsp;Pending`.

Gap **đã có `po_answer`** → KHÔNG đè cột Trả lời; giữ nguyên Trạng thái do PO đặt.

### 2.2. Append section phân tích chi tiết vào CUỐI report gốc
Thêm 1 section (không phá bố cục bảng phía trên):

```markdown
---
## PHÂN TÍCH & ĐỀ XUẤT (AI) — {date}

> Do `ntapp-qa-gap-resolver` sinh. Đây là **đề xuất có bằng chứng**, KHÔNG phải quyết định cuối — chờ PO/Lead chốt ở cột "Trả lời".

### GAP-NN — <tiêu đề ngắn>  ·  Phân loại: <nhãn>
1. **Tính năng ảnh hưởng:** …
2. **Bằng chứng 4 nguồn:** <bảng Nguồn | Giá trị | Trích dẫn | Ngày>
3. **Phân loại + chiều lệch:** <nhãn> — <lý do theo mốc thời gian>
4. **Đề xuất chốt:** …
5. **Hiện trạng code:** <đang làm gì · khớp/lệch · path:line>
6. **Việc cần làm nếu chốt:** <regen DD / sửa §techspec / diff code> — file đích: …
```
Lặp cho mọi gap, theo thứ tự 🔴 → 🟡 → ⚪.

### 2.3. Bảng tổng hợp đầu section (để quét nhanh)
Ngay dưới tiêu đề section, thêm bảng: `GAP | Mức | Phân loại | Đề xuất tóm tắt | File đích | Cần PO?`.

## 3. Ghi file
Ghi đè in-place `{qa_artifacts}/reviews/{id}_qa_report.md`. **KHÔNG** tạo archive/`_v{N}`. Giữ nguyên toàn bộ nội dung PO đã điền trước đó.

## 4. GATE 1 (bắt buộc — DỪNG)
Sau khi ghi file, trình bày trong hội thoại:
- Bảng tổng hợp (mục 2.3) + đếm theo phân loại.
- **Nhóm gap cùng gốc** (chốt 1 lần cho cả nhóm) để user quyết theo cụm.
- Chỉ rõ gap `mơ-hồ-nghiệp-vụ` **bắt buộc PO chốt trước**, skill không execute được.

Rồi HỎI: **"Chọn gap (hoặc nhóm) nào để tôi xử lý ở Phase 2?"**. KHÔNG tự sang Step 04. Chờ người dùng chọn.
