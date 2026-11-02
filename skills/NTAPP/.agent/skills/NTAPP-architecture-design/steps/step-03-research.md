# STEP 03: TECH RESEARCH & INTELLIGENCE [CONDITIONAL]

> **Acting as:** [Agent B — Research Scout](../agents/agent_b_research_scout.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication — phải có URL nguồn), R4 (Traceability).

**Điều kiện kích hoạt:** Bước này CHỈ được thực thi khi có ÍT NHẤT MỘT trong các điều kiện sau:
  1. Agent A phát hiện 3+ NFR ở trạng thái "Chưa xác định"
  2. PRD đề cập đến công nghệ/giao thức KHÔNG QUEN THUỘC (ví dụ: một Message Queue mới, một API Third-party đặc thù)
  3. Agent E hoặc người dùng chủ động yêu cầu research
  4. Người dùng chưa chắc chắn về Tech Stack và cần AI đề xuất so sánh các lựa chọn kiến trúc (Trigger từ Step 01).

> **Pass-through (nếu KHÔNG điều kiện nào kích hoạt):** KHÔNG thực hiện research, KHÔNG ghi `part_03_tech_research.md`, KHÔNG hỏi xác nhận tech stack — đi thẳng tới `**Next:**` (Step 04.1). Đây chính là nhánh "đủ thông tin → bỏ qua Step 03" mà Step 02 (G1) định tuyến.

**Input:** Bảng NFR từ Step 02 + Danh sách External Systems + Tech constraints
**Output:** `part_03_tech_research.md`

---

## MỤC TIÊU BƯỚC NÀY

Lấp đầy các khoảng trống kiến thức bằng bằng chứng thực tế (Benchmark, API Docs, Best Practice). Cung cấp Tech Stack khuyến nghị có căn cứ cho Agent C và D.

---

## QUY TRÌNH THỰC THI

### 3.1 Xác định các khoảng trống cần Research

Lập danh sách Research Queries từ input của Agent E:

```
Ví dụ:
- [GAP-1] Chưa có số liệu TPS → Research benchmark cho Message Queue phù hợp
- [GAP-2] PRD đề cập "Kafka" nhưng chưa rõ Topic structure
- [GAP-3] External System "Jira Cloud API" — cần đọc API docs để hiểu Rate Limits
```

### 3.2 Thực thi Web Search (cho từng Research Query)

Với mỗi Research Query, Agent B sử dụng công cụ tìm kiếm web:

**Template truy vấn:**
```
Query: {Technology/Pattern} benchmark {relevant_metric} {year}
Query: {External System} API documentation rate limits authentication
Query: {Tech A} vs {Tech B} performance comparison {use_case}
```

**Quy tắc Research:**
- Phải trích dẫn nguồn (URL) cho mọi số liệu benchmark.
- Ưu tiên nguồn: Official Docs > CNCF Reports > Technology Blogs (2023+).
- KHÔNG sử dụng thông tin không có nguồn gốc rõ ràng.
- Mỗi công nghệ phải có bảng Trade-off (Ưu/Nhược) tối thiểu 3 điểm mỗi cột.

### 3.3 Đánh giá và Đề xuất Tech Stack

Sau khi research, lập bảng so sánh và đưa ra đề xuất:

**Bảng So sánh Công nghệ (Template):**

| Hạng mục | Lựa chọn A | Lựa chọn B | Lựa chọn đề xuất |
| :--- | :--- | :--- | :--- |
| Message Queue | Kafka | RabbitMQ | {Đề xuất + Lý do} |
| Caching | Redis Cluster | Memcached | {Đề xuất + Lý do} |
| Vector DB | PostgreSQL+PGVector | ChromaDB | {Đề xuất + Lý do} |
| Auth | Keycloak | Auth0 | {Đề xuất + Lý do} |

**Quy tắc đề xuất:**
- Mỗi đề xuất PHẢI có benchmark số liệu chứng minh đáp ứng NFR.
- Nếu có ràng buộc công nghệ từ người dùng → Ưu tiên giữ nguyên ràng buộc đó.

### 3.4 Phân tích giao thức External Systems

Với từng External System được liệt kê trong PRD:
- Đọc API Documentation (nếu có URL).
- Ghi lại: Authentication method, Rate Limits, Data format (JSON/XML), Webhook support.
- Chỉ ra các rủi ro tích hợp (Integration Risks).

---

## Ghi output ra file

Ghi vào: `{intermediate_folder}/part_03_tech_research.md`

Cấu trúc file:
```markdown
# Tech Proposal Report

## 1. Research Queries & Sources
## 2. Tech Stack Comparison Tables
## 3. Recommended Tech Stack
## 4. External System Integration Notes
## 5. Integration Risk Register
```

---

## ĐIỀU KIỆN TIẾP TỤC (Exit Criteria)

- [ ] Tất cả Research Queries đã được giải đáp bằng nguồn trích dẫn.
- [ ] Bảng Tech Stack Comparison đã được lập đầy đủ.
- [ ] `part_03_tech_research.md` đã được ghi.
- [ ] Người dùng đã xem báo cáo research và **XÁC NHẬN** lựa chọn tech stack cuối cùng.

---

## ⛔ [GATE — User confirm tech stack] (chỉ khi đã research; đặt TRƯỚC Next)

Nếu đã thực thi research → chỉ sang Step 04.1 SAU KHI người dùng **XÁC NHẬN** lựa chọn tech stack cuối cùng (Exit Criteria trên). Nếu pass-through (không research) → bỏ qua cổng này, đi thẳng Next.

**Next:** Read fully and follow `./step-04.1-architecture-global.md`
