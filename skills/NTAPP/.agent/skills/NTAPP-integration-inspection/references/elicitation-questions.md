---
Version: 1.0.0
Author: M2MBA
Last Updated: 2026-06-09
Description: Bộ câu hỏi elicitation (khơi gợi per-mục + nhóm A/B/C) — cho Mục 12 của NTAPP-integration-inspection
---

# Bộ câu hỏi Elicitation — Tham chiếu cho Mục 12

Hai tầng câu hỏi:
- **Tầng 1 — Câu hỏi khơi gợi per-mục:** ở `mode: interactive`, hỏi sau mỗi mục để confirm. Ghi nhận câu chưa có câu trả lời.
- **Tầng 2 — Bộ câu hỏi nhóm A/B/C:** tổng hợp ở Mục 12, dùng cho buổi elicitation chính thức với Biz / Đối tác / 3-way.

---

## Tầng 1 — Câu hỏi khơi gợi theo mục

**Mục 2 (Dữ liệu & mapping)**
- *Nghiệp vụ:* Trường "Có sẵn" có được cập nhật đầy đủ & nhất quán không? Trường "Chưa có" có thể derive từ dữ liệu sẵn có? Đối tác đặt tên trường khác nội bộ (cần alias mapping)?
- *Dữ liệu:* Format ngày/tiền tệ/mã vùng có khớp? Trường null/optional đối tác xử lý sao? Enum/lookup đối tác dùng mã nào?
- *Bảo mật:* Trường PII nào (SĐT/CCCD/địa chỉ/tài chính) cần mask? Đối tác lấy tất cả bản ghi hay chỉ data thuộc scope (data scoping)?

**Mục 3 / 4 (Chức năng & thay đổi thực thể)**
- *Nghiệp vụ:* Chức năng thay đổi — bên nội bộ nào khác đang dùng (impact)? Ảnh hưởng màn hình/report/export nào? Cần phối hợp team nào?
- *Dữ liệu:* Dữ liệu lịch sử sau khi thêm trường xử lý sao (null/backfill/default)? Trường mới bắt buộc nhập? Validation? Cần migration script?
- *Bảo mật:* Cần thêm role/permission nội bộ? Cần audit log (ai sửa, lúc nào, giá trị cũ/mới)?

**Mục 5 / 6 (Luồng & sequence)**
- Có bước thứ tự thay đổi tùy điều kiện (branching)? Còn luồng ngoài happy path (hủy, token hết hạn, trùng, timeout)?
- Tích hợp sync (real-time) hay async (webhook/polling)? Token refresh xảy ra ở bước nào?
- Đối tác cần lưu dữ liệu trung gian (session_id…) để dùng bước tiếp?

**Mục 8 (Đặc tả API)**
- Response nhiều bản ghi — cần pagination flow? Log/audit ghi ở tầng nào (Gateway/Backend)? Nếu async — webhook hay polling, timeout bao lâu báo lỗi?

---

## Tầng 2 — Nhóm A: Hỏi Stakeholder Biz (Product Owner)
*Tập trung: tại sao, cái gì, kỳ vọng nghiệp vụ.*

**Mục tiêu & phạm vi:** Tích hợp giải quyết vấn đề gì? KPI kỳ vọng? Phạm vi giai đoạn 1 gồm luồng nào, luồng nào roadmap sau? Nếu thất bại/chậm, nghiệp vụ bị ảnh hưởng thế nào?

**Quy tắc & ngoại lệ:** Có trường hợp xử lý khác luồng thường (VIP, đơn đặc biệt, vùng không phục vụ)? Khi dữ liệu hai bên mâu thuẫn, bên nào là source of truth? Có thứ tự xử lý/điều kiện tiên quyết nào tài liệu API chưa đề cập?

**Hiệu năng & SLA:** Real-time / near-real-time / batch? Tần suất nếu batch? Nếu đối tác downtime, fallback thủ công là gì, ai làm? Delay tối đa chấp nhận được?

**Bảo mật & tuân thủ:** Có PII / dữ liệu tài chính / nhạy cảm? Compliance nào (GDPR, PCI-DSS, Thông tư NH…)? Ai được xem/sửa dữ liệu tích hợp phía nghiệp vụ?

**Vận hành sau go-live:** Ai xử lý incident phía nội bộ? Cần dashboard theo dõi? Quy trình phê duyệt thay đổi cấu hình tích hợp?

---

## Tầng 2 — Nhóm B: Hỏi Đối tác (Technical Team)
*Câu hỏi đổi theo loại tích hợp đã nhận diện.*

**Chung mọi loại:** Sandbox có không, ai cấp credential, đủ edge case? Breaking change báo trước bao lâu, qua kênh nào? Đầu mối kỹ thuật & SLA hỗ trợ? Encoding/timezone/định dạng ngày chuẩn gì?

**🌐 REST API:** OAuth2/API Key/mTLS? Token expiry & refresh? Rate limit (req/giây hoặc /ngày), quota theo account? Idempotency — gọi trùng xử lý sao? Timeout mặc định, retry do ai? Có webhook/callback? Giá trị null/field thiếu xử lý sao?

**📁 File-based:** Giao thức (SFTP/FTPS/S3/API upload), credential dạng gì? Naming convention cố định, nhiều file cùng ngày? Header row? Encoding (UTF-8/BOM/Windows-1252)? Delimiter & escape char? File lỗi cấu trúc — reject toàn bộ hay partial? Có file acknowledgement? Dọn dẹp thư mục processed/error? Cơ chế báo khi file trễ giờ?

**📨 Message Queue:** Broker gì + version? Delivery guarantee (at-most/at-least/exactly-once)? Ordering đảm bảo (per partition/queue)? Schema format (JSON/Avro/Protobuf), có Schema Registry? Consumer fail — DLQ/retry/thủ công? Retention bao lâu? Tự quản offset? Replay từ offset cụ thể? Throughput dự kiến?

**🔧 SOAP / Web Service:** WSDL endpoint ổn định hay đổi theo môi trường? WS-Security UsernameToken hay Certificate? Giới hạn kích thước SOAP envelope? Fault code/FaultString chuẩn hoá thế nào? Có MTOM/XOP cho attachment?

---

## Tầng 2 — Nhóm C: Confirm cả hai bên (buổi 3-way)

| Chủ đề | Câu hỏi cần confirm |
|--------|---------------------|
| **Field mapping** | Tên field biz vs đối tác? Kiểu dữ liệu có khớp? |
| **Status mapping** | Trạng thái đối tác trả về có map 1-1 với nội bộ? Có trạng thái nào chưa mapping? |
| **Rollout plan** | Go-live khi nào? Cutover data cũ thế nào? Kế hoạch rollback? |
| **Data reconciliation** | Nếu dữ liệu hai bên lệch, quy trình đối chiếu & xử lý? Tần suất? |
| **Ownership incident** | Đầu mối khi có sự cố? Alert gửi đâu? Escalation path? |
| **Môi trường chuyển đổi** | Khi nào sandbox → production? Điều kiện kiểm tra gì? |

> 💡 **Tip:** Tổ chức ít nhất 2 buổi riêng (Biz, Đối tác) trước buổi 3-way. Buổi 3-way chưa align trước thường tốn thời gian giải thích khái niệm cơ bản thay vì ra quyết định.

---

## Cách sinh câu hỏi ưu tiên (Mục 12)

Sau khi hoàn thành 14 mục, tự động:
1. **Rà [Giả định]** trong tài liệu → đánh dấu 🔴 (chưa có thông tin) vào câu hỏi liên quan.
2. **Rà field chưa rõ Source** (Mục 2) → đánh dấu 🟡 (cần confirm) vào nhóm A/B.
3. **Rà field Persist=Yes nhưng Purpose chưa rõ** → thêm câu hỏi đối soát/tracking vào nhóm C.
4. In danh sách theo ưu tiên (🔴 trước, 🟡 sau), gom theo nhóm A/B/C.

Bảng tổng hợp Mục 12:

| # | Câu hỏi cần làm rõ | Nhóm | Mục liên quan | Ảnh hưởng nếu không rõ | Ưu tiên |
|---|-------------------|------|---------------|----------------------|---------|
| 1 | *(câu hỏi)* | Nghiệp vụ / Dữ liệu / Bảo mật / Vận hành | Mục X | *(rủi ro)* | Cao / TB / Thấp |

*Phân loại ưu tiên:* **Cao** = không rõ thì không thiết kế đúng (block); **Trung bình** = ảnh hưởng chất lượng/độ chính xác; **Thấp** = làm rõ được sau khi bắt đầu triển khai.

**Ví dụ output:**
```
📋 BỘ CÂU HỎI ELICITATION — [Tên đối tác]

=== NHÓM A — Stakeholder Biz ===
🔴 [Mục tiêu] Nếu CreateShipment thất bại, fallback thủ công là gì?
🟡 [SLA] Thời gian đồng bộ trạng thái đơn tối đa bao lâu?

=== NHÓM B — Đối tác ===
🔴 [Reliability] API CreateCustomer có idempotency không?
🟡 [Data] Trường `status` có thể thêm giá trị mới không báo trước không?

=== NHÓM C — Confirm hai bên ===
🔴 [Status mapping] "RETURNED" của đối tác map sang trạng thái nội bộ nào?
```
