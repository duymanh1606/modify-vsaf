# STEP 0/5 — JTBD Competitor Scouting
> 🎭 Hoá thân **scout_agent**. Đọc persona đầy đủ: `../agents/scout_agent.md` trước khi thực thi.
> ⛔ Chỉ đọc step kế SAU KHI qua [GATE 2] ở cuối file này.

**Input:** `{Research_Topic}` (từ người dùng).
**Action:**
- Phân tích Core Job theo framework JTBD (Jobs-to-be-Done).
- Đề xuất 20 đối thủ chia 3 Buckets: Direct, Indirect, Substitutes (mỗi tên kèm 1 câu < 15 chữ lý do).
**Output:** Ghi toàn bộ kết quả vào `{scout_data}` và in ra cho người dùng xem để lựa chọn.

---
## [GATE 2: CHỌN TARGET] — ⛔ DỪNG TẠI ĐÂY
In ra:
> "Dựa trên bản đồ cạnh tranh JTBD trên, để tối ưu nguồn lực phân tích sâu, hãy gõ tên 3 đến 5
> đối thủ/giải pháp mà bạn muốn hệ thống mổ xẻ nhất."
> 👉 **[PAUSE & WAIT FOR USER INPUT LẦN 2]** — KHÔNG đọc step-01 trước khi user trả lời.

Sau khi user trả lời → gán vào `{Target_Competitors}`.
**Next:** Read fully and follow `./step-01-market-research.md`
