# STEP 6/6 — Executive Synthesis (TERMINAL)
> 🎭 Hoá thân **pr_chief_editor**. Đọc persona đầy đủ: `../agents/pr_chief_editor.md`.
> ⛔ Đây là step cuối — KHÔNG còn step kế.

**Context:** Hoàn thiện báo cáo Product Director/CPO
**Role:** `pr_chief_editor`

## Nhiệm vụ:
1. Đọc và gộp dữ liệu từ 4 file raw: `{raw_personas}`, `{raw_journey}`, `{raw_pain_matrix}`, `{raw_prioritization}`.
2. Viết Báo cáo hoàn chỉnh.
3. BẮT BUỘC tuân thủ cấu trúc sau ở ngay đầu báo cáo:
   - **Tên báo cáo:** Tự động sinh tiêu đề tiếng Việt dựa trên dữ liệu phân tích, theo đúng format: `[{project_name}] Báo cáo Phân tích Chân dung & Nỗi đau Khách hàng - Phân khúc [Tên Phân Khúc Trọng Tâm] (Problem-Solution Fit)`. *(Lưu ý: Tự động thay thế [Tên Phân Khúc Trọng Tâm] bằng nhóm khách hàng thực tế, VD: E-commerce, F&B...)*
   - **Version Control:** Vẽ một bảng gồm [Phiên bản (V1, V2...)] | [Ngày cập nhật (dùng biến {date})] | [Tóm tắt thay đổi].
   - Phải có phần Executive Summary súc tích ở đầu báo cáo.
   - CHÉP Y NGUYÊN (Copy paste 100%) các Bảng Markdown từ file raw (Đặc biệt thêm mục Customer Behavior & Decision Process), không được tự ý tóm tắt Bảng.
4. KẾT XUẤT ĐA LUỒNG (Dual-Export): GHI TOÀN BỘ NỘI DUNG VÀO 2 FILE CÙNG LÚC:
   - Ghi đè vào `{final_report}` (Để làm Bản Master mới nhất cho các Agent khác đọc).
   - Ghi thêm một bản sao vào `{archive_report}` (Để lưu trữ lịch sử chống mất mát).
5. Hiển thị thông báo: *"Báo cáo phiên bản mới nhất của dự án `{project_name}` đã được lưu tại Master File và sao lưu vào thư mục Archive. Quy trình Product Research hoàn tất!"*
