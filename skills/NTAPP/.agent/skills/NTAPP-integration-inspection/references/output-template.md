# Template: Tài liệu Đặc tả Tích hợp (14 mục)

> **Version:** 1.0 | **Author:** M2MBA | **Last Updated:** 2026-06-09
> Lưu tại: `{planning_artifacts}/<Tên đối tác>/Integration_<Tên đối tác>_YYYYMMDD.md` — `{planning_artifacts}` resolve runtime (default `NTAPP-output/Stage_1_Discovery/integration`), xem SKILL.md §Config resolution.

---

# Tài liệu Đặc tả Tích hợp: [Tên đối tác]

> **Phiên bản:** 1.0 | **Ngày:** DD/MM/YYYY | **Người tạo:** [Tên BA]
> **Chiều tích hợp:** outbound (mình gọi đối tác) / inbound (đối tác gọi mình) / bidirectional
> **Trạng thái:** Draft / Review / Approved

---

## Lịch sử thay đổi

| Phiên bản | Ngày | Người thực hiện | Nội dung thay đổi |
|----------|------|----------------|------------------|
| 1.0 | DD/MM/YYYY | [Tên BA] | Tạo mới |

---

## 1. Tổng quan & mục đích tích hợp

> *(3–5 dòng: tên đối tác, mục đích, phạm vi dữ liệu, chiều tích hợp, loại tích hợp, môi trường, timeline)*

**Bảng tóm tắt nhanh:**

| Thuộc tính | Giá trị |
|-----------|--------|
| Đối tác | [Tên] |
| Mục đích | [Mục đích nghiệp vụ] |
| Chiều tích hợp | outbound / inbound / bidirectional |
| Loại tích hợp | REST API / Message Queue / File / SOAP / Hybrid |
| Môi trường hiện tại | Sandbox / Production |
| Số API/file/message | [N] |
| Thực thể thay đổi | [N thêm mới, M bổ sung trường] |
| Mức độ phức tạp | Thấp / Trung bình / Cao |

---

## 2. Dữ liệu & mapping nội bộ

*[Bảng trạng thái ✅/⚠️/❌ + bảng mapping IN/OUT field-level — từ `erd-and-mapping.md` §A]*

---

## 3. Use Case & màn hình/chức năng cần xây

| Tên chức năng | Loại (Gọi API / Tạo dữ liệu đầu vào / Cấu hình / Process nội bộ) | API/file/message liên quan | Dữ liệu liên quan |
|---|---|---|---|

---

## 4. Danh sách thay đổi thực thể dữ liệu *(bắt buộc)*

*[Phần A thêm mới + Phần B bổ sung trường + Phần C dataset chi tiết — từ `erd-and-mapping.md` §B]*

---

## 5. Quy trình tích hợp đề xuất (4 phần)

*[Mô tả 4 phần + pseudo flow — đủ 3 giai đoạn [AUTH] → [DATA MAPPING] → [INTEGRATION FLOWS]]*

---

## 6. Sequence Diagram

*[Mermaid — autonumber, Note over phân nhóm 3 giai đoạn, KHÔNG có Database — xem `sequence-diagram-examples.md`]*

---

## 7. Bảng Mapping API ↔ Sequence

| # | Step trong sequence | Kiểu | Tên API/Topic/File | Method | Endpoint/Path | Mô tả ngắn | Phần/Bước (Mục 5) |
|---|-------------------|------|--------------------|--------|---------------|------------|-------------------|

---

## 8. Đặc tả Chi tiết API / Message / File

*[Đặc tả từng item theo thứ tự Mục 7 — REST API dùng template đầy đủ `api-spec-template.md`; File/MQ/SOAP dùng bảng tương ứng `integration-types.md` §2]*

---

## 9. ERD tích hợp đa đối tác *(bắt buộc)*

*[Mermaid erDiagram — phản ánh đúng Mục 4, annotation nghiệp vụ trên quan hệ, tư duy đa đối tác — xem `erd-and-mapping.md` §C]*

---

## 10. Non-Functional Requirements

| Thuộc tính | Yêu cầu | Ghi chú |
|-----------|--------|--------|
| Response time | ≤ [X]ms (p95) | |
| Availability | [X]% uptime | |
| Rate limit | [X] req/phút per API Key | |
| Timeout | [X] giây | |
| Retry policy | [X] lần, backoff [Y]s | |
| Data retention | Log lưu [X] ngày | |

---

## 11. Rủi ro & Phụ thuộc

| # | Rủi ro | Khả năng | Tác động | Biện pháp giảm thiểu |
|---|--------|---------|---------|---------------------|
| 1 | *(mô tả)* | Cao/TB/Thấp | Cao/TB/Thấp | *(biện pháp)* |

**Phụ thuộc kỹ thuật:**
- [ ] [Team/hệ thống cần phối hợp]
- [ ] [API/service bên thứ ba cần sẵn sàng]

---

## 12. Điểm cần làm rõ với đối tác

*[Bảng tổng hợp câu hỏi nhóm A/B/C + ưu tiên 🔴/🟡 — từ `elicitation-questions.md`]*

---

## 13. HTML Prototype / Giao diện mẫu *(tùy chọn)*

> Tạo nếu luồng phát sinh chức năng nội bộ cần UI (form cấu hình partner, quản lý API Key, dashboard log tích hợp, màn cấu hình mapping).

**File HTML:** `{planning_artifacts}/<Tên đối tác>/prototype/screens.html` — 1 file, tab navigation, mỗi tab = 1 chức năng từ Mục 3.

Yêu cầu: field bám bảng Mục 2 + Mục 4-C; có trạng thái UI (active/inactive, enabled/disabled, loading, error); trường nhạy cảm (API Key/secret/PII) có placeholder + tooltip cảnh báo; màu phân biệt section header (`#f0f0f0`), action button (primary), error/warning (đỏ/vàng).

---

## 14. Checklist go-live *(bắt buộc)*

**Sandbox & Testing**
- [ ] Sandbox test toàn bộ luồng (happy path + error path)
- [ ] Kiểm tra retry logic và idempotency
- [ ] Test pagination nếu có

**Security & Compliance**
- [ ] Security review (PII masking, auth mechanism đúng thiết kế)
- [ ] Rate limit test — client xử lý 429 đúng
- [ ] Data scoping (đối tác không lấy được dữ liệu ngoài phạm vi)

**Non-Functional**
- [ ] NFR validate: response time (p95 ≤ threshold), availability, timeout
- [ ] Load test nếu volume cao

**Documentation & Handoff**
- [ ] Documentation sign-off (BA + Tech Lead + đại diện đối tác)
- [ ] Onboarding guide gửi đối tác (endpoint, auth, error codes)

**Operations**
- [ ] Monitoring alert (5xx spike, latency cao, queue lag)
- [ ] Rollback plan — cơ chế tắt tích hợp, xử lý dữ liệu đang dở
- [ ] Log retention policy đúng môi trường production
