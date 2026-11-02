<!-- srs_level: system -->
# Software Requirements Specification (SRS)
## {{TÊN HỆ THỐNG}}

> **Template:** SRS System-Level v2 | **Cặp với:** `srs-feature-template.md` (feature-level v6)
> **Domain-neutral + multi-archetype** — dùng cho lending / insurance / payment / commerce / backend / integration. Ví dụ trong template là *placeholder*.
> **Chuẩn diagram DUY NHẤT = PlantUML** (`@startuml`) — khớp feature-template + skill. KHÔNG dùng Mermaid.
>
> **Thay đổi so với v1:**
> - [v2.1] **Diagram Mermaid → PlantUML** (System Context §2.2, Module Map §2.5, State Diagram §G) — hết trộn engine với feature-template.
> - [v2.2] **System Applicability Profile** (§0): greenfield/brownfield, có-UI?, deployment model, domains phủ, mode → chi phối section N/A.
> - [v2.3] **Decision Log** (§0): quyết định cấp hệ thống/kiến trúc + lý do (tách khỏi Lịch sử phiên bản; trỏ ADR).
> - [v2.4] **§2.7 Assumptions** có Status/Owner/Deadline (chống assumption bị quên).
> - [v2.5] **§4.9 Observability** cấu trúc Log/Metric/Trace/Dashboard/Alert (thay NFR-MON rời).
> - [v2.6] **Domain-neutral hoá** ví dụ insurance (Data Dictionary §E, State §G).
> - [v2.7] Sửa numbering NFR (4.6). **§I AI Metadata** `[full]` máy-đọc (modules/entities/external systems/glossary) cho agent downstream + seed Reuse Index feature-level.
>
> **Legend depth:** `[core]` = luôn có · `[std]` = từ mode standard · `[full]` = chỉ mode full.

| Thông tin | Chi tiết |
|---|---|
| **Dự án** | {{Tên dự án đầy đủ}} |
| **Phiên bản** | {{X.Y}} |
| **Trạng thái** | Draft |
| **Ngày tạo** | {{YYYY-MM-DD}} |
| **Người soạn** | {{Tên / Team}} |
| **Nguồn** | {{Danh sách tài liệu nguồn: PRD, Architecture, BRD, Epics,...}} |

### Lịch sử phiên bản

| Phiên bản | Ngày | Người thực hiện | Nội dung thay đổi |
|---|---|---|---|
| {{X.Y}} | {{YYYY-MM-DD}} | {{Tên}} | {{Mô tả thay đổi}} |

### Decision Log

> **Khác Lịch sử phiên bản:** đây ghi *quyết định cấp hệ thống/kiến trúc đã chốt và tại sao* (chọn stack, mô hình tích hợp, ranh giới module, chiến lược migrate…). Quyết định kiến trúc chi tiết → trỏ ADR.

| Ngày | Quyết định | Người chốt | Lý do / Đánh đổi | ADR / Nguồn |
|---|---|---|---|---|
| {{YYYY-MM-DD}} | {{vd: "tách module X thành service riêng"}} | {{CTO/Tech Lead}} | {{Lý do + phương án bị loại}} | {{ADR-XX / MoM}} |

### Bảng phê duyệt

| Vai trò | Họ tên | Chữ ký | Ngày |
|---|---|---|---|
| BA Lead | | | |
| Product Owner | | | |
| CTO / Tech Lead | | | |
| Legal / Compliance *(nếu domain bị quản lý)* | | | |
| UX Lead *(nếu có UI)* | | | |

### 0. System Applicability Profile

> **Khai báo 1 lần — quyết định section nào áp dụng.** Section không áp dụng → ghi **"N/A — {lý do}"**, KHÔNG để bảng rỗng.

| Thuộc tính | Lựa chọn | Ảnh hưởng |
|---|---|---|
| **Loại hệ thống** | ☐ Có UI (B2C/B2B) ☐ Backend/API platform ☐ Integration hub ☐ Batch/Data | §2.4 personas, §7.A Screen Inventory (N/A nếu không UI) |
| **Greenfield / Brownfield** | ☐ Mới hoàn toàn ☐ Thay thế/migrate hệ thống cũ | §5.3 Transition Requirements (bắt buộc nếu brownfield) |
| **Deployment model** | {{Cloud / On-prem / Hybrid; Container/K8s?}} | §2.3 Môi trường, §4.11 Portability |
| **Domains phủ** | {{lending / insurance / payment / … — có thể nhiều}} | Thay placeholder ví dụ; nạp domain-checklist |
| **Mode soạn** | ☐ draft ☐ standard ☐ full | Cắt mục `[std]`/`[full]` |

---

## 1. Giới thiệu

### 1.1 Mục đích tài liệu

{{Mô tả mục đích SRS — tài liệu này phục vụ ai, dùng để làm gì}}

Tài liệu phục vụ:
- Làm cơ sở cho thiết kế kỹ thuật (Architecture, SDD)
- Cơ sở viết test plan và test cases
- Xác nhận scope và chức năng với stakeholders
- {{Thêm mục đích khác nếu cần}}

### 1.2 Đối tượng đọc

| Đối tượng | Mục đích sử dụng |
|---|---|
| BA Team | Tài liệu gốc để phát triển và kiểm soát thay đổi |
| Dev Team | Hiểu yêu cầu để thiết kế và lập trình |
| Test Lead | Cơ sở viết test plan và test case |
| Product Owner | Xác nhận scope, phân kỳ |
| {{Thêm đối tượng khác}} | {{Mục đích}} |

### 1.3 Phạm vi hệ thống

**In-scope (MVP — Phase 1):**
- {{Module/Feature 1}} (FR range)
- {{Module/Feature 2}} (FR range)
- ...

**Out-of-scope (Phase 2/3):**
- {{Feature}} — Phase X
- ...

### 1.4 Định nghĩa & Từ viết tắt

| Thuật ngữ / Viết tắt | Giải thích |
|---|---|
| SRS | Software Requirements Specification |
| UC | Use Case |
| FR | Functional Requirement |
| NFR | Non-Functional Requirement |
| BR | Business Rule |
| RTM | Requirements Traceability Matrix |
| {{Thêm thuật ngữ domain}} | {{Giải thích}} |

### 1.5 Tài liệu tham chiếu

| Tài liệu | Phiên bản | Vị trí |
|---|---|---|
| {{Tên tài liệu}} | {{vX.Y}} | {{Đường dẫn}} |
| ... | | |

---

## 2. Tổng quan hệ thống

### 2.1 Mô tả sản phẩm

{{Mô tả tổng quan hệ thống: giải quyết vấn đề gì, mô hình hoạt động, MVP scope}}

### 2.2 Sơ đồ ngữ cảnh hệ thống (System Context Diagram)

```plantuml
@startuml System Context
!pragma layout smetana
left to right direction
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Arial
skinparam defaultFontSize 12
skinparam ArrowColor #333333

actor "{{Actor 1}}" as A1
actor "{{Actor 2}}" as A2
rectangle "**{{TÊN HỆ THỐNG}}**" as SYS #D5DBE6
rectangle "{{External System 1}}" as E1 #FFD8D8
rectangle "{{External System 2}}" as E2 #FFD8D8

A1 --> SYS
A2 --> SYS
SYS --> E1
SYS --> E2
@enduml
```

### 2.3 Môi trường vận hành

| Hạng mục | Chi tiết |
|---|---|
| Nền tảng | {{Web / Mobile / WebView / API}} |
| Trình duyệt hỗ trợ | {{Chrome X+, Safari X+,...}} |
| Hạ tầng | {{Cloud provider, deployment model}} |
| Backend | {{Tech stack}} |
| Database | {{DB technologies}} |
| Message Broker | {{Nếu có}} |
| API Gateway | {{Nếu có}} |
| Auth | {{Auth solution}} |

### 2.4 Actors và đặc điểm người dùng

| Actor | Mô tả | Tần suất | Kênh | Mức kỹ thuật |
|---|---|---|---|---|
| **{{Persona 1}}** | {{Mô tả}} | {{Tần suất}} | {{Kênh}} | {{Mức}} |
| **{{Persona 2}}** | {{Mô tả}} | {{Tần suất}} | {{Kênh}} | {{Mức}} |

### 2.5 Module Map

```plantuml
@startuml Module Map
!pragma layout smetana
left to right direction
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Arial
skinparam defaultFontSize 12
skinparam ArrowColor #333333
skinparam rectangleBackgroundColor #D5DBE6
skinparam rectangleBorderColor #0A2956

actor "{{Actor 1}}" as A1
actor "{{Actor 2}}" as A2
rectangle "{{Module 1}}" as M1
rectangle "{{Module 2}}" as M2
rectangle "{{Module 3}}" as M3

A1 --> M1
A1 --> M2
A2 --> M3
@enduml
```

| Module | Flows | FRs | Priority |
|---|---|---|---|
| **{{M1: Tên module}}** | Flow XX | FR range | Must Have / Should Have |
| **{{M2: Tên module}}** | Flow XX | FR range | Must Have / Should Have |

### 2.6 Kiến trúc tích hợp

| Hệ thống bên ngoài | Loại | Mục đích | Giao thức | Chiều | SLA |
|---|---|---|---|---|---|
| {{Tên hệ thống}} | Partner / Third-party | {{Mục đích}} | {{REST/SOAP/File}} | Inbound / Outbound / Bidirectional | {{SLA}} |

### 2.7 Giả định và phụ thuộc cấp hệ thống

**Giả định (mỗi giả định phải có Status/Owner/Deadline — chống bị quên):**

| ID | Giả định | Status | Owner | Deadline xác nhận |
|---|---|---|---|---|
| A1 | {{Giả định 1}} | ☐ Đã xác nhận ☐ Chưa xác nhận ☐ Bác bỏ | {{Ai}} | {{YYYY-MM-DD}} |
| A2 | {{Giả định 2}} | ☐ Chưa xác nhận | {{Ai}} | {{YYYY-MM-DD}} |

> Giả định "Chưa xác nhận" quá deadline → nâng thành rủi ro (§5.4) hoặc Open Issue (§7.C).

**Phụ thuộc:**
- D1: {{Phụ thuộc 1 — hậu quả nếu không có}}
- D2: {{Phụ thuộc 2 — hậu quả nếu không có}}

---

## 3. Yêu cầu chức năng (Functional Requirements)

> **ID scheme:** `UC-[MODULE]-[NNN]` | **Business Rule:** `BR-[NNN]` | **Thông báo:** `MSG-[NNN]`

### 3.X Module X — {{Tên Module}} (Flow XX)

> **Tài liệu chi tiết:** Xem `srs/SRS-{{code}}-FlowXX-vX.Y.md` (nếu có SRS feature-level riêng)

**Tóm tắt UCs:**

| UC ID | Tên | Actor | Priority | FRs |
|---|---|---|---|---|
| UC-MX-001 | {{Tên UC}} | {{Actor}} | Must Have | {{FR range}} |

---

#### UC-MX-001: {{Tên Use Case}}

| Thông tin | Chi tiết |
|---|---|
| **ID** | UC-MX-001 |
| **Tên** | {{Tên UC}} |
| **Mô tả** | {{Mô tả ngắn gọn}} |
| **Ưu tiên** | Must Have / Should Have / Could Have |
| **Trạng thái** | Draft |
| **Nguồn** | {{PRD vX FR range}} |
| **Actor** | {{Actor chính}} |
| **Kênh** | {{Kênh sử dụng}} |
| **Đường dẫn chức năng** | {{Navigation path}} |
| **Trigger** | {{Sự kiện kích hoạt}} |
| **Tần suất sử dụng** | {{Tần suất}} |
| **Điều kiện tiên quyết** | {{Preconditions}} |

**Luồng chính (Main Flow):**
1. {{Bước 1}}
2. {{Bước 2}}
3. ...

> Khi UC ≥5 bước hoặc ≥2 lần rẽ nhánh, **bắt buộc** kèm sequence diagram và/hoặc activity diagram (PlantUML). Xem mẫu trong `srs-feature-template.md` §3.1, §3.2.

**Luồng thay thế:**
- **Alt-1 — {{Tên}}:** {{Mô tả}}
- **Alt-2 — {{Tên}}:** {{Mô tả}}

**Luồng ngoại lệ:**
- **Exc-1 — {{Tên}}:** {{Mô tả}}

**Hậu điều kiện:**
- Thành công: {{Kết quả khi thành công}}
- Thất bại: {{Kết quả khi thất bại}}

**Yêu cầu dữ liệu:**

| Trường | Kiểu | Bắt buộc | Validation | Ghi chú |
|---|---|---|---|---|
| {{field_name}} | {{String/Integer/Enum/Date/...}} | Có/Không | {{Rule}} | {{Ghi chú}} |

**Business Rules:**

| Mã | Nội dung | Tham chiếu |
|---|---|---|
| BR-XXX | {{Nội dung rule}} | {{PRD/FR/NFR reference}} |

**Các thông báo hệ thống:**

| Mã | Loại | Nội dung | Điều kiện |
|---|---|---|---|
| MSG-XXX | Success/Error/Info/Push | {{Nội dung thông báo}} | {{Điều kiện hiển thị}} |

**Phương pháp kiểm thử:** {{Manual / API test / E2E automation / Integration test / Load test}}

---

> **Lặp lại section 3.X cho mỗi Module. Lặp lại UC block cho mỗi Use Case trong module.**

---

## 4. Yêu cầu phi chức năng (Non-Functional Requirements)

### 4.1 Hiệu năng (Performance)

| ID | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| NFR-PERF-001 | {{Yêu cầu}} | {{p95 / p99 / SLA}} |

### 4.2 Bảo mật (Security)

| ID | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| NFR-SEC-001 | {{Yêu cầu}} | {{Tiêu chí}} |

### 4.3 Khả dụng & Độ tin cậy (Availability)

| ID | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| NFR-AVAIL-001 | {{Yêu cầu}} | {{% uptime}} |
| NFR-REL-001 | RPO | {{< X minutes}} |
| NFR-REL-002 | RTO | {{< X hours}} |

### 4.4 Khả dụng với người dùng (Usability)

| ID | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| NFR-USAB-001 | {{Accessibility — WCAG level}} | {{VD: WCAG 2.1 Level AA cho contrast, font size}} |
| NFR-USAB-002 | {{Learnability — thời gian onboarding}} | {{VD: User hoàn thành task chính trong ≤X phút lần đầu}} |
| NFR-USAB-003 | {{Error recovery — khả năng phục hồi}} | {{VD: Mọi lỗi có hướng dẫn sửa, undo trong ≤X bước}} |
| NFR-USAB-004 | {{Đa ngôn ngữ / Localization}} | {{VD: Hỗ trợ vi-VN, en-US}} |

### 4.5 Khả năng mở rộng (Scalability)

| ID | Yêu cầu | MVP | Year 1 |
|---|---|---|---|
| NFR-SCALE-001 | {{Yêu cầu}} | {{MVP target}} | {{Year 1 target}} |

### 4.6 Khả năng tương tác (Interoperability)

| ID | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| NFR-INTEROP-001 | {{Contract/format trao đổi với hệ thống ngoài}} | {{VD: REST/JSON theo OpenAPI 3.x; versioning backward-compatible}} |

### 4.7 Tuân thủ quy định (Compliance)

> Điền theo domain trong System Applicability Profile: lending → Thông tư NHNN; payment/thẻ → PCI-DSS; mọi domain có PII → PDPA.

| ID | Yêu cầu | Quy định | Tiêu chí |
|---|---|---|---|
| NFR-COMP-001 | {{Yêu cầu}} | {{Tên quy định áp dụng cho domain}} | {{Tiêu chí}} |

### 4.8 Audit & Ghi log

| ID | Yêu cầu | Tiêu chí |
|---|---|---|
| NFR-AUDIT-001 | {{Scope}} | {{Chi tiết}} |
| NFR-AUDIT-002 | Retention | {{>= X years}} |

### 4.9 Observability (Monitoring & Alerting)

> Bảng có cấu trúc cho DevOps/SRE. Log KHÔNG chứa mật khẩu/token/PII thô (mask). Correlation ID propagate xuyên service/Kafka/HTTP.

| Luồng/sự kiện cần quan sát | Log (mức) | Metric (tên + loại) | Trace | Dashboard | Alert (điều kiện) |
|---|---|---|---|---|---|
| {{giao dịch chính}} | INFO | `{{metric}}` counter | correlationId | {{dashboard}} | {{error rate > X%/5m}} |
| {{gọi hệ thống ngoài}} | ERROR | `{{metric}}` counter/gauge | span | {{dashboard}} | {{latency/timeout > ngưỡng}} |

### 4.10 Khả năng bảo trì (Maintainability)

| ID | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| NFR-MAINT-001 | {{Code quality / test coverage}} | {{VD: Unit test coverage ≥X%, SonarQube quality gate pass}} |
| NFR-MAINT-002 | {{Documentation}} | {{VD: API docs auto-generated (OpenAPI 3.x), architecture docs up-to-date}} |
| NFR-MAINT-003 | {{Modular design}} | {{VD: Microservices loosely coupled, thay thế 1 service không ảnh hưởng service khác}} |

### 4.11 Khả năng di chuyển (Portability)

| ID | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| NFR-PORT-001 | {{Platform independence}} | {{VD: Containerized (Docker/K8s), không vendor-locked}} |
| NFR-PORT-002 | {{Database portability}} | {{VD: Dùng standard SQL, tránh vendor-specific extensions}} |
| NFR-PORT-003 | {{Multi-channel support}} | {{VD: API-first, hỗ trợ embed vào host app khác ngoài channel hiện tại}} |

---

## 5. Ràng buộc, Giả định & Phụ thuộc

### 5.1 Ràng buộc kỹ thuật

- {{Ràng buộc tech stack}}
- {{Ràng buộc deployment}}
- {{Ràng buộc infra}}

### 5.2 Ràng buộc quy định pháp lý

- {{Ràng buộc pháp lý 1}}
- {{Ràng buộc pháp lý 2}}

### 5.3 Yêu cầu chuyển đổi (Transition Requirements)

> *(ISO 29148 §6.4 + BABOK v3 §7.4.3 — bắt buộc khi hệ thống thay thế/migrate từ hệ thống cũ)*

| # | Yêu cầu | Mô tả | Owner | Timeline |
|---|---|---|---|---|
| TR-001 | {{Data migration}} | {{VD: Migrate X records từ hệ thống cũ, mapping rules, validation}} | {{Team}} | {{Sprint/Phase}} |
| TR-002 | {{Parallel-run}} | {{VD: Chạy song song old/new system trong X tuần, so sánh output}} | {{Team}} | {{Period}} |
| TR-003 | {{Rollback plan}} | {{VD: Nếu migration fail, rollback trong ≤X giờ, data intact}} | {{Team}} | {{Trigger}} |
| TR-004 | {{User training / communication}} | {{VD: Training cho X users trước go-live, hướng dẫn sử dụng}} | {{Team}} | {{Before go-live}} |

> Nếu không có migration/chuyển đổi, ghi rõ: "Không áp dụng — hệ thống mới hoàn toàn."

### 5.4 Rủi ro ảnh hưởng đến yêu cầu

| Rủi ro | Mức độ | Ảnh hưởng | Biện pháp |
|---|---|---|---|
| {{Rủi ro}} | Cao/Trung bình/Thấp | {{Module/Feature bị ảnh hưởng}} | {{Mitigation}} |

---

## 6. Ma trận truy xuất yêu cầu (RTM)

| PRD FR | UC ID | Module | Màn hình | Epic/Story |
|---|---|---|---|---|
| {{FR ID}} | {{UC ID}} | {{Module}} | {{Screen name}} | {{Epic/Story ref}} |

---

## 7. Phụ lục

### A. Danh sách màn hình (Screen Inventory)

| Màn hình | Module | Figma/Screenshot | UC liên quan |
|---|---|---|---|
| {{Tên màn hình}} | {{Module}} | {{Đường dẫn}} | {{UC ID}} |

### B. Business Rules Index

| Mã | Nội dung | Module | UC |
|---|---|---|---|
| BR-XXX→YYY | {{Nhóm rule}} | {{Module}} | {{UC ID}} |

### C. Open Issues

| # | Vấn đề | Module | Người phụ trách | Hạn | Trạng thái |
|---|---|---|---|---|---|
| OI-X | {{Vấn đề}} | {{Module}} | {{Người}} | {{Deadline}} | Open |

### D. Danh sách thông báo hệ thống (Message Catalog)

| Mã | Loại | Nội dung | UC |
|---|---|---|---|
| MSG-XXX | Success/Error/Info/Push | {{Nội dung}} | {{UC ID}} |

### E. Data Dictionary

> *(ISO 29148 §6.4.3.8 Logical database requirements + BABOK v3 §7.1 Data Models)*

| Thực thể | Thuộc tính | Kiểu dữ liệu | Ràng buộc | Bắt buộc | Mô tả | Hệ thống nguồn |
|---|---|---|---|---|---|---|
| {{Entity}} | {{field_name}} | {{String/Integer/Date/Enum/UUID}} | {{FK, Unique, Check,...}} | Có/Không | {{Mô tả nghiệp vụ}} | {{Hệ thống/service sở hữu dữ liệu — theo domain}} |

### F. CRUD Matrix

| Use Case | {{Entity 1}} | {{Entity 2}} | {{Entity 3}} | {{Entity 4}} |
|---|---|---|---|---|
| UC-MX-001 | C | R | — | — |
| UC-MX-002 | R | U | C | — |
| UC-MX-003 | — | R | R | D |

> C=Create, R=Read, U=Update, D=Delete, —=Không tác động

### G. State Diagrams — Entity Lifecycle

> *(BABOK v3 §7.1 State Diagrams — bắt buộc cho entities có ≥3 trạng thái)*

**{{Entity name}} Lifecycle:**

```plantuml
@startuml {{Entity}} Lifecycle
!pragma layout smetana
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Arial
skinparam defaultFontSize 11

[*] --> {{State1}} : {{Trigger}}
{{State1}} --> {{State2}} : {{Event/Action}}
{{State2}} --> {{State3}} : {{Event/Action}}
{{State2}} --> {{State4}} : {{Event/Action}}
{{State3}} --> [*]
{{State4}} --> [*]
@enduml
```

| Trạng thái | Mô tả | Trigger chuyển trạng thái | Ai thực hiện |
|---|---|---|---|
| {{State1}} | {{Mô tả}} | {{Event}} | {{Actor/System}} |
| {{State2}} | {{Mô tả}} | {{Event}} | {{Actor/System}} |

> Lặp lại cho mỗi entity có lifecycle phức tạp (VD theo domain: lending → LoanApplication/Disbursement; payment → Transaction; commerce → Order; insurance → Policy/Claim).

### H. Verification Summary

> *(ISO 29148 §6.4.4 — cross-reference giữa requirements và phương pháp kiểm thử)*

| Module | UC ID | Phương pháp kiểm thử | Test Coverage | Ghi chú |
|---|---|---|---|---|
| {{Module}} | UC-MX-001 | {{Manual / API / E2E / Integration / Load / Security}} | {{Unit + Integration + E2E}} | {{Ghi chú đặc biệt}} |
| {{Module}} | UC-MX-002 | {{...}} | {{...}} | |

**Tổng hợp per module:**

| Module | Tổng UC | Manual | API Test | E2E | Integration | Load | Security |
|---|---|---|---|---|---|---|---|
| {{M1}} | {{X}} | {{X}} | {{X}} | {{X}} | {{X}} | {{X}} | {{X}} |

### I. AI Metadata `[full]`

> **Block máy-đọc cho agent downstream & seed Reuse Index của SRS feature-level.** Là *bản tóm tắt phái sinh* từ nội dung ở trên — KHÔNG khai báo khái niệm mới. Mode `draft`/`standard` có thể bỏ.

```yaml
ai_metadata:
  system: "{{TÊN HỆ THỐNG}}"
  domains: ["{{lending}}", "{{payment}}"]      # từ §0 Profile
  modules:                                       # từ §2.5 Module Map
    - name: "{{M1}}"
      flows: ["Flow XX"]
      priority: "Must"
  entities:                                      # từ §7.E Data Dictionary
    - name: "{{Entity}}"
      owner_system: "{{service}}"
  external_systems:                              # từ §2.6 Integration Architecture
    - name: "{{ExternalSystem}}"
      protocol: "{{REST/SOAP/File}}"
      direction: "{{Inbound/Outbound}}"
  glossary_source: "{{link §1.4 / GLOSSARY dự án}}"
```

---

*Tài liệu cần review bởi: {{Danh sách reviewer roles}} trước khi baseline.*
