# STEP 2/6 — Customer Segmentation
> 🎭 Hoá thân **user_researcher**. Đọc persona đầy đủ: `../agents/user_researcher.md` trước khi thực thi.
> ⛔ Chỉ đọc step kế SAU KHI qua [GATE: CHỜ LỆNH] ở cuối file này.

**Context:** User đã chọn trọng tâm nghiên cứu. Cần phân rã chân dung khách hàng B2B.
**Role:** `user_researcher`

## 🛑 MANDATORY EXECUTION RULES (READ FIRST):
- KHÔNG BAO GIỜ tự bịa dữ liệu (Hallucination). Bắt buộc phải Verify bằng Web Search.
- ĐỌC TOÀN BỘ YÊU CẦU TRƯỚC KHI HÀNH ĐỘNG. Hiểu một nửa sẽ dẫn đến sai lầm chiến lược.
- Ghi ngay kết quả vào file đích.

## Nhiệm vụ Bắt buộc (Execution Rules):
1. Dựa trên dữ liệu thị trường và định hướng của User, **BẮT BUỘC** thực hiện Web Search để tìm hiểu sâu về tệp đối tượng mục tiêu.
2. Vẽ Bảng Phân khúc Khách hàng B2B theo Framework Firmographics. **TUYỆT ĐỐI KHÔNG** dùng các chức danh chung chung (như SME, CTO). Bảng phải chia rõ các cột:
   - Ngành nghề & Quy mô (VD: Chuỗi F&B 10-50 CH).
   - Chân dung người ra quyết định (Decision Maker).
   - Độ trưởng thành công nghệ hiện tại.
   - Kênh tiếp cận GTM tốt nhất.
   - Xếp hạng Ưu tiên Target (Tier 1/2/3) & Lý do chiến lược.
3. Ghi toàn bộ bảng kết quả phân tích này vào file `{raw_personas}`.

---
## [GATE: CHỜ LỆNH] — ⛔ DỪNG TẠI ĐÂY
Sau đó Dừng lại và chờ lệnh đi tiếp.
> 👉 KHÔNG đọc step-03 trước khi User ra lệnh đi tiếp.

**Next:** Read fully and follow `./step-03-journey.md`
