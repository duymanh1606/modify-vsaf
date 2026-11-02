# STEP 5/6 — Prioritization & Scoring
> 🎭 Hoá thân **product_manager**. Đọc persona đầy đủ: `../agents/product_manager.md` trước khi thực thi.
> Không có cổng user ở step này — chạy xong trỏ thẳng step kế.

**Context:** Cần sàng lọc, chấm điểm Nỗi đau dựa trên độ khốc liệt của thị trường và ROI.
**Role:** `product_manager`

## Nhiệm vụ:
1. Đọc kỹ `{raw_pain_matrix}` và `{market_data_input}` (Đặc biệt phần định vị của đối thủ).
2. Lọc bỏ các Nỗi đau "ảo" hoặc độ ưu tiên quá thấp. Chú trọng vào Nỗi đau nào đối thủ đang làm rất tệ.
3. BẮT BUỘC vẽ BẢNG MARKDOWN Chấm điểm Ưu tiên chia làm 3 mức độ:
   - `[Nỗi đau]`
   - `[Phân loại P0/P1/P2]` (P0: Sống còn, P1: Quan trọng, P2: Nice-to-have)
   - `[Lý do ưu tiên]` (Rationale: Chấm dựa trên Mức độ nghiêm trọng + Điểm yếu đối thủ)
4. Ghi toàn bộ phân tích và Bảng vào file `{raw_prioritization}`.

**Next:** Read fully and follow `./step-06-synthesis.md`
