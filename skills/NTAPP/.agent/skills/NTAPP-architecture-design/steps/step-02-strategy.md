# STEP 02: CONTEXT & STRATEGY ANALYSIS

> **Acting as:** [Agent A — Context Strategist](../agents/agent_a_context_strategist.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication), R4 (Traceability), R7 (Stopping Errors — 3+ TBD NFR).

**Input:** Context Summary từ Step 01 + PRD + Epics
**Output:** `part_02_context_strategy.md`

---

## MỤC TIÊU BƯỚC NÀY

Phân tích hệ thống ở 3 tầng sâu (Event → Pattern → Structure) và lượng hóa toàn bộ yêu cầu phi chức năng (NFR). Đây là nền tảng dữ kiện cho tất cả các Agent tiếp theo.

---

## QUY TRÌNH THỰC THI

### 1. Thiết lập Phần 1: GIỚI THIỆU

Đọc PRD/Epics và trích xuất thông tin cho các mục sau. **TUYỆT ĐỐI KHÔNG bịa thông tin — chỉ trích xuất từ tài liệu hoặc từ Context Summary đã được người dùng xác nhận.**

**Mục 1.1 — Mục đích:**
- Xác định: Tài liệu phục vụ ai? (Developer, Tester, SA, PM, SOC...)
- Xác định: Tài liệu này làm căn cứ cho việc gì? (Coding, Integration testing, Infrastructure setup...)

**Mục 1.2 — Phạm vi:**
- Liệt kê các hệ thống/module nằm TRONG phạm vi thiết kế.
- Liệt kê các hệ thống bên ngoài (External Systems) mà BMS sẽ giao tiếp.
- Nêu rõ Tech Stack được đề xuất (dựa trên PRD hoặc ràng buộc đã xác nhận).

**Mục 1.3 — Thuật ngữ:**
- Quét toàn bộ PRD/Epics để lập bảng thuật ngữ. Mỗi từ viết tắt/thuật ngữ chuyên ngành PHẢI có dòng riêng trong bảng.

**Mục 1.4 — Tài liệu tham khảo:**
- Liệt kê tất cả tài liệu đầu vào với đường dẫn file thực tế (không dùng placeholder).

**Mục 1.5 — Mô tả tài liệu:**
- Tóm tắt cấu trúc của HLD sẽ được tạo ra (căn cứ vào Final Template).

### 2.1 Trích xuất Động lực Kiến trúc (Architecture Drivers & Root Causes)

Phân tích PRD/Epics để tìm ra các "Bài toán cốt lõi" mà Kiến trúc (HLD) này BẮT BUỘC phải giải quyết.
*Quy tắc: KHÔNG viết văn xuôi dài dòng. KHÔNG bịa thông tin. Trình bày dạng Bullet points ngắn gọn.*

**1. Vấn đề hiện tại (Nghiệp vụ & Kỹ thuật):**
> (Chỉ ghi nếu có) Các điểm nghẽn, lỗi lặp lại, hoặc giới hạn của hệ thống cũ. (Ví dụ: "Hệ thống A không thể xử lý hơn 100 TPS do lock DB"). Nếu là dự án mới tinh, ghi: "Dự án mới, không có nợ kỹ thuật".

**2. Rủi ro Kiến trúc cốt lõi (Architectural Risks / Root Causes):**
> (Bắt buộc) Suy luận góc độ Kiến trúc:
> - Nếu có Vấn đề hiện tại (Mục 1): Cấu trúc lõi nào là nguyên nhân gốc rễ? (Ví dụ: "Single Point of Failure tại Gateway", "Thiếu cơ chế xử lý bất đồng bộ").
> - Nếu là dự án greenfield: Dựa vào NFR (TPS, Concurrent Users, Availability) để suy luận rủi ro kiến trúc lớn nhất nếu chọn sai pattern. (Ví dụ: "Yêu cầu 10k concurrent users → rủi ro nếu chọn monolith stateful").

**3. Các ràng buộc Kiến trúc (Architecture Constraints):**
> Phân loại theo 3 nhóm. Mỗi nhóm liệt kê bullet points (bỏ qua nhóm nếu không có):
> - **Tech-stack bắt buộc:** (Ví dụ: Oracle DB, Spring Boot, Kafka)
> - **Legacy/Integration bắt buộc:** (Ví dụ: Core Banking qua SOAP, SAP qua IDoc)
> - **Compliance/Policy bắt buộc:** (Ví dụ: dữ liệu PII không ra khỏi DC nội bộ, tuân thủ ISO 27001)


### 2.2 Các yêu cầu phi chức năng (NFR)

Điền vào bảng sau. Mọi ô **bắt buộc** phải có giá trị — nếu PRD không đề cập, ghi `"Chưa xác định — cần làm rõ"` và **CẢnh báo Agent E**.

| NFR Category | Chỉ số yêu cầu | Nguồn (Section PRD) |
| :--- | :--- | :--- |
| **Throughput** | {TPS hoặc số request/phút} | {Mục X.X} |
| **Latency** | {API response max Xms} | {Mục X.X} |
| **Concurrent Users** | {Số lượng người dùng đồng thời} | {Mục X.X} |
| **Data Volume** | {GB/TB hiện tại, tăng trưởng X%/tháng} | {Mục X.X} |
| **Processing Mode** | {Realtime / Batch / Hybrid} | {Mục X.X} |
| **Availability** | {Uptime %; RTO; RPO} | {Mục X.X} |
| **Scalability** | {Horizontal / Vertical; Max scale target} | {Mục X.X} |
| **Security** | {Compliance: ISO/SOC2/HIPAA, Encryption level, **PII Masking required**, **Zoning requirement: DMZ**} | {Mục X.X} |


**Quy tắc cảnh báo:** Nếu có 3+ NFR ở trạng thái "Chưa xác định", DỪNG lại và báo cáo cho Agent E để quyết định:
- Option A: Kích hoạt Step 03 (Agent B research benchmark để ước tính).
- Option B: Quay lại người dùng để hỏi thêm.


### 2.3 Phân vùng Mạng (Security Zoning)

Xác định ranh giới mạng cho từng thành phần kiến trúc dự kiến. Đây là input bắt buộc cho Agent C (component placement), Agent D (security), Agent F (deployment diagram).

| Component (dự kiến) | Zone | Lý do | Cổng exposed |
| :--- | :--- | :--- | :--- |
| {API Gateway / Reverse Proxy} | DMZ | Tiếp xúc Internet hoặc đối tác bên ngoài | 443 |
| {App Service / Business Logic} | Trust Zone | Logic nội bộ, chỉ được gọi từ DMZ | — (nội bộ) |
| {Database / Cache / MQ} | Restricted Zone | Dữ liệu nhạy cảm, chỉ App Service truy cập | — (nội bộ) |

**Quy tắc:**
- Mỗi thành phần PHẢI thuộc đúng 1 zone (DMZ / Trust / Restricted).
- Nếu chưa biết chính xác component ở Step 02, ghi `"TBD ở Step 04, ràng buộc zone = X"` để Agent C có thể bám theo.
- Mọi luồng cross-zone PHẢI đi qua Gateway/Proxy — không cho phép kết nối trực tiếp từ DMZ xuống Restricted.

---

## Ghi output ra file

Ghi nội dung đã hoàn thành vào một file duy nhất:
- `{intermediate_folder}/part_02_context_strategy.md` — (Bao gồm: Mục 1.1 → 1.5 + Mục 2.1, 2.2 & Bảng NFR + Mục 2.3 Security Zoning)

---

## ĐIỀU KIỆN TIẾP TỤC (Exit Criteria)

- [ ] `part_02_context_strategy.md` được tạo, bao gồm Intro (1.1–1.5), Architecture Drivers (2.1), NFR (2.2), Security Zoning (2.3).
- [ ] Mục 2.1 có đủ 3 sub-section (Vấn đề hiện tại, Rủi ro Kiến trúc, Constraints) — Mục 2 và 3 bắt buộc có nội dung.
- [ ] Bảng NFR đã điền đủ 8 hàng (dù có thể một số ô là "Chưa xác định").
- [ ] Bảng Security Zoning đã liệt kê tối thiểu các thành phần dự kiến với zone tương ứng.
- [ ] Agent E đã nhận được báo cáo cảnh báo (nếu có NFR thiếu).

---

## 🚦 EXIT GATE — NFR Completeness (G1)

**Owner:** Agent E. Thực hiện ngay sau khi Agent A submit `part_02_context_strategy.md`.

**Check:**
- [ ] ≥ 5/8 NFR rows có giá trị định lượng (không phải "Chưa xác định").
- [ ] Security Zoning có ≥ 1 component cho mỗi zone (DMZ / Trust / Restricted) hoặc có lý do rõ ràng tại sao zone đó trống.
- [ ] Architecture Drivers (2.1) có ≥ 1 Root Cause được suy luận (greenfield → suy luận từ NFR; brownfield → từ Vấn đề hiện tại).
- [ ] Bảng Thuật ngữ (1.3) không rỗng nếu PRD có ≥ 5 từ viết tắt.

**Hành động khi FAIL:**
- Nếu thiếu NFR có thể bù bằng research → quyết định kích hoạt **Step 03**.
- Nếu thiếu thông tin chỉ user biết → quay lại **Step 01** clarify.
- Nếu Architecture Driver thiếu Root Cause → trả về Agent A phân tích lại.

**Hành động khi PASS:** ghi log "G1 PASS" rồi chuyển bước tiếp theo.

---

## Định tuyến research (Step 03 là CONDITIONAL — giữ nguyên nghiệp vụ branch cũ)

- **Cần Research** (G1 FAIL bù được bằng research / 3+ NFR "Chưa xác định" / tech-stack chưa chốt) → Step 03 thực thi research rồi mới sang Step 04.1.
- **Đủ thông tin** → Step 03 tự **pass-through** (không research, không ghi `part_03`) và đi thẳng Step 04.1 — tương đương nhánh "Bỏ qua Step 03" cũ.

Cả hai nhánh đều đi qua Step 03 (Step 03 tự quyết theo điều kiện kích hoạt ở đầu file của nó) → chuỗi liền mạch.

**Next:** Read fully and follow `./step-03-research.md`
