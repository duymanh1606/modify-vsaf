# No Hallucination Rule (Gap Resolver)

## Mục đích
Chặn agent tự suy diễn giá trị canonical, hành vi, field, message lỗi, API hoặc business rule khi phân tích/đề xuất phương án cho một gap. Skill này quyết định "giá trị nào nên chốt" — nên rủi ro bịa còn cao hơn lúc audit.

## Nguyên tắc bắt buộc
Mọi đề xuất phương án cho một gap **phải trích dẫn bằng chứng** từ một trong các nguồn sau (ghi rõ file + §/dòng):

1. Dữ liệu thực tế được **report cite** (staging sample trong `f2`, giá trị thật). KHÔNG tự query DB nếu report không có.
2. TechSpec / Contract canonical (`{module}_techspec.md`, Module 0) — SSoT.
3. DD parts (`f0`–`f3`) của unit liên quan.
4. Code thực tế trong repo code (đã đọc + trích path:line + git blame).
5. Quyết định PO/Lead đã ghi trong report (cột Trả lời).

## Khi thiếu bằng chứng
Nếu KHÔNG có nguồn nào đủ để chốt giá trị/hành vi đúng → **KHÔNG tự đoán**. Phân loại gap = `mơ-hồ-nghiệp-vụ`, đề xuất ghi rõ `[Cần PO chốt]` + nêu các phương án và trade-off, KHÔNG chọn thay PO.

## Điều kiện reject (một đề xuất bị loại nếu)
- Chốt một giá trị/enum/regex mà không trích được nguồn.
- "Hợp thức hoá" hiện trạng: chốt theo code chỉ vì code đang làm vậy, dù code lệch contract (xem [priority-resolution-rule.md](./priority-resolution-rule.md)).
- Bịa message lỗi / mã lỗi / field / status không có trong nguồn.
- Suy ra "chiều lệch" (docs cũ hay code cũ) mà không dựa trên dấu vết thời gian (git log/blame, ngày CR, ngày DD).
- Đọc trực tiếp `.env` hoặc làm lộ credentials.
