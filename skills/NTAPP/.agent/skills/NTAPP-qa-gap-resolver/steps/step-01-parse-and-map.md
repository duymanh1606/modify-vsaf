# STEP 01: PARSE & MAP (Phase 1 — Analyze)

> **Acting as:** Senior Engineer / Tech Lead
> **Tuân thủ:** [priority-resolution-rule.md](../references/priority-resolution-rule.md), [no-hallucination-rule.md](../references/no-hallucination-rule.md)

## 1. Mục tiêu
Đọc report, biến bảng GAP thành **danh sách gap có cấu trúc**, và map mỗi gap → tính năng/API/màn ảnh hưởng. Đây là nền cho việc rà 4 nguồn ở Step 02.

## 2. Input
- `report_path` = `{qa_artifacts}/reviews/{id}_qa_report.md` (resolve ở INITIALIZATION). Thiếu/không đọc được → DỪNG, hỏi user.

## 3. Chỉ thị thực thi

1. **Đọc TOÀN BỘ report.** Đọc kỹ phần đầu: "Cách dùng báo cáo", **"Ký hiệu file"** (legend), và mục "ĐÃ ĐỌC GÌ / Pre-flight". Legend là chìa khoá để giải mã đường dẫn file thật từ ký hiệu rút gọn.

2. **Xây bảng giải mã ký hiệu → đường dẫn thật.** Report dùng ký hiệu rút gọn, ví dụ:
   - `HUB-ts` → `Stage_3_Specs/techspec/HUB_techspec.md`
   - `HUB-01/f2` → `Stage_4_Design/detailed_design/feature_design_parts/HUB-01/f2_..._part.md`
   - `COMPOSE/f3` → `.../SCR-COMPOSE/f3_ui_part.md`
   - `Module0` → `Stage_2_Architecture/00_system_connectivity_integration.md`
   - `wbs` → `Stage_2_Architecture/project_wbs.md`
   - `(d.X)` → dòng X trong file đó
   > Lấy quy ước từ chính legend của report đang xử lý — KHÔNG hardcode; report khác có thể dùng ký hiệu khác.

3. **Parse mỗi dòng GAP** (check TOÀN BỘ — cả 🔴/🟡/⚪) thành bản ghi:
   | Trường | Nội dung |
   |---|---|
   | `gap_id` | GAP-NN |
   | `severity` | 🔴 Cao / 🟡 Trung bình / ⚪ Thấp |
   | `status` | Todo / Resolved / Pending (đọc từ cột Trạng thái) |
   | `problem` | mô tả "Vấn đề" |
   | `cited_sources` | danh sách (ký hiệu file, §, d.X) trích trong ô Vấn đề + ô Phương án |
   | `proposed_options` | các phương án A/B/C report gợi sẵn (kèm dấu ✓) |
   | `po_answer` | nội dung cột Trả lời hiện có (nếu PO đã điền) |

   > Gap đã có `po_answer` (PO chốt rồi) hoặc `status=Resolved` → vẫn phân tích để xác nhận, nhưng đánh dấu "đã có chốt PO" và **ưu tiên tôn trọng quyết định PO** ở Step 02/03 (không đè lên).

4. **Map gap → tính năng ảnh hưởng.** Với mỗi gap, từ các unit trong `cited_sources` (HUB-01, HUB-02, SCR-COMPOSE, PMT-EXT-01…) và mục Pre-flight, xác định:
   - **Unit/loại**: BE service / FE screen / widget / external endpoint.
   - **Bề mặt ảnh hưởng**: API nào (path/verb nếu report nêu), màn nào, luồng demo nào.
   - **Repo code dự kiến**: unit này thuộc repo code nào trong `code_repo_roots` (để Step 02 rà code). Chưa chắc → để Step 02 xác minh.

5. **Nhóm sơ bộ gap cùng gốc.** Nhiều gap thường chung một nguyên nhân (vd "TechSpec CR mới vs DD part stale"). Ghi nhận nhóm để Step 02 rà nguồn 1 lần dùng cho cả nhóm (tiết kiệm) và Step 04 gom theo file đích.

## 4. Output (in-memory, chuyển sang Step 02)
- Danh sách gap có cấu trúc (bảng ở mục 3.3) + bảng giải mã ký hiệu → đường dẫn thật + map tính năng ảnh hưởng + nhóm gap cùng gốc.

## 5. Gate độ phủ
Parse **hết** gap trong report (đếm khớp con số tổng ở cuối report, vd "Tổng: 20 điểm"). Thiếu gap = parse chưa xong.
