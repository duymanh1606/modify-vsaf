# STEP 4/5 — Executive Synthesis (TERMINAL)
> 🎭 Hoá thân **chief_editor**. Đọc persona đầy đủ: `../agents/chief_editor.md`.
> ⛔ Đây là step cuối — KHÔNG còn step kế.

**Input:** Đọc toàn bộ `{raw_market_data}`, `{raw_strategy_data}`, `{raw_feature_data}`.
**Action:**
- Hợp nhất thành 1 báo cáo duy nhất, giải quyết các đoạn trùng lặp (Redundancy).
- BẮT BUỘC ở đầu báo cáo:
  - **Tên báo cáo** theo format: `[{project_name}] Báo cáo Nghiên cứu thị trường {Research_Topic}`.
  - **Version Control:** bảng [Phiên bản (V1, V2...)] | [Ngày cập nhật (biến {date})] | [Tóm tắt thay đổi].
  - **Executive Summary** súc tích.
- CHÉP Y NGUYÊN (100%) các Bảng Markdown từ file raw — KHÔNG tự ý tóm tắt bảng.
- BẮT BUỘC mục **'Strategic Recommendations'** ở cuối: **TỐI THIỂU 3 KHUYẾN NGHỊ CHIẾN LƯỢC** dựa trên data.
- **Dual-Export** — ghi TOÀN BỘ nội dung vào 2 file cùng lúc:
  - Ghi đè `{final_output_file}` (Bản Master mới nhất).
  - Ghi thêm bản sao vào `{archive_output_file}` (lưu trữ lịch sử).
- Trình bày chuẩn C-Level (McKinsey style).
- Hiển thị: *"Báo cáo phiên bản mới nhất của dự án `{project_name}` đã được lưu tại Master File và sao lưu
  vào thư mục Archive. Quy trình Market Research hoàn tất!"*
