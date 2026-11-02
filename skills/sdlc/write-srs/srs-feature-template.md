<!-- srs_level: feature -->
# Flow {XX} — {Tên chức năng}

> **Template:** SRS Feature-Level v6 | **Cấu trúc:** SRS_Template standard (12 sections: 0–11)
> **Domain-neutral + multi-archetype** — dùng được cho lending / insurance / payment / commerce / backend-only / integration-only. Ví dụ minh hoạ trong template là *placeholder* — thay bằng domain của bạn.
>
> **Thay đổi so với v5:**
> - [v6.1] **§0 Decision Log** — lịch sử quyết định (tại sao chốt), tách khỏi Change Log (cái gì đổi). Truy vết "tại sao BR/scope thay đổi".
> - [v6.2] **§2.5 Assumption Validation** — mỗi ASM có Status / Owner / Deadline, tránh assumption bị quên.
> - [v6.3] **§11.4 Impact Matrix** kỹ thuật — API / DB / Cache / Kafka / Batch / Scheduler / Permission / Notification (impact analysis đầy đủ cho microservices).
> - [v6.4] **§8.2 Observability table** — Log / Metric / Trace / Dashboard / Alert (gộp NFR-OBS rời rạc, phục vụ SRE).
> - [v6.5] **§11.7 Open Questions** — câu hỏi nghiệp vụ chưa chốt (Owner/Due/Status), tách khỏi Gap Analysis (thiếu design).
> - [v6.6] **§11.8 AI Metadata** `[full]` — block máy-đọc (entities/events/commands/queries/aggregates/external APIs/glossary/confidence) cho agent downstream tái dùng; cộng hưởng Reuse Index.
> - [v6.7] `[full]` optional: **Priority Matrix** (§1.2), **Version Compatibility** (§4.5/§9), **Feature Toggle** (§9). §7.2 buộc **boundary values tường minh** (test data enumeration thuộc test-design).
> - [v6.8] §0 Applicability Profile thêm dòng **SRS level = `feature`** (tường minh, khớp marker `<!-- srs_level: feature -->` đầu file) — để validate-srs detect deterministic + không nhầm khung system.
>
> **Thay đổi so với v4:**
> - [v5.1] **Applicability Profile** (§0): khai báo loại feature (`UI / backend-process / integration-only / batch`) → section không áp dụng được đánh dấu **N/A có lý do** thay vì để rỗng.
> - [v5.2] **Depth legend theo mode** (`draft / standard / full`): mỗi section/bảng optional gắn nhãn `[std]` / `[full]` để cắt gọt theo mode mà không đổi cấu trúc.
> - [v5.3] **Domain-neutral hoá**: bỏ mặc định nghiêng bảo hiểm (Policyholder/NTBH…) → token trung lập `{PrimaryActor}` / `{DomainEntity}`; ví dụ cũ chuyển thành ghi chú "ví dụ".
> - [v5.4] §9 thêm **9.3 Data Migration & Backfill** cho archetype cắt-chuyển legacy (brownfield / legacy→new).
> - [v5.5] §1.3 vs §11.6 và §3.3 vs §11.3: ghi rõ **quan hệ canonical vs mở rộng** để tránh trùng lệch.
>
> **Thay đổi so với v3 (giữ nguyên từ v4):**
> - [v4.1] Cấu trúc 12 sections (0–11): 0 Preamble, 1 Introduction, 2 Business Context, 3 System Overview, 4 Data Model, 5 Functional Requirements, 6 State & Behavioral Models, 7 Business Rules & Validation, 8 NFR, 9 Constraints, 10 RTM, 11 Appendix
> - [v4.2] Section 3 System Overview tách riêng — High-Level Activity Diagram + Architecture (dời từ cuối tài liệu lên)
> - [v4.3] Section 4 Data Model gộp Entity tables + ER diagram + Kafka Events + API Endpoints
> - [v4.4] Section 7 Business Rules & Validation gộp BR table + Validation Rules + Error Codes (section 4 cũ)
> - [v4.5] Section 11 Appendix chứa Figma Mapping tables + Screen List + Chức năng ảnh hưởng + Gap Analysis
> - [v4.6] Section 10 RTM bổ sung cột BR + AC + Test Case (từ RTM chuẩn)
> - [v4.7] Figma Mapping tables dời về Appendix 11.1, UC detail chỉ giữ inline blockquote tham chiếu
>
> **Legend depth:** `[core]` = luôn có (mọi mode) · `[std]` = từ mode `standard` · `[full]` = chỉ mode `full`. Section không gắn nhãn = `[core]`.

**Dự án:** {Tên dự án}
**Trang Confluence gốc:** `{confluence-url}`
**Người soạn:** BA Team
**Ngày:** {YYYY-MM-DD}

---

## 0. Preamble

### Thông tin tài liệu

| | |
|---|---|
| **Tên tài liệu** | SRS Feature-Level — {FR-XX}: {Tên chức năng} |
| **Phiên bản** | {X.Y} |
| **Ngày** | {YYYY-MM-DD} |
| **Tác giả** | BA Team |
| **Trạng thái** | Draft / In Review / Approved |

### Bảng ghi nhận thay đổi

A – Tạo mới, M – Sửa đổi, D – Xóa bỏ

| Ngày | Vị trí | A/M/D | Nguồn gốc | Link CR | Mô tả thay đổi | Phiên bản Confluence | Phiên bản mới |
|---|---|---|---|---|---|---|---|
| {YYYY-MM-DD} | Toàn bộ | A | {PRD vX / Architecture vX / ...} | — | Tạo mới — SRS Feature-Level cho {FR-XX}: {Tên chức năng}. Bao gồm {N} chức năng con ({FR-XX-01} → {FR-XX-0N}) của {service-name}. | — | 1.0 |

### Decision Log

> **Khác Change Log:** Change Log = *cái gì trong tài liệu đã đổi*; Decision Log = *quyết định nghiệp vụ/thiết kế đã chốt và tại sao*. Dùng để truy "vì sao BR/scope/state thế này". Quyết định cấp kiến trúc hệ thống → trỏ ADR; quyết định cấp feature ghi tại đây.

| Ngày | Quyết định | Người chốt | Lý do / Đánh đổi | Nguồn (PRD/họp/ADR) |
|---|---|---|---|---|
| {YYYY-MM-DD} | {Nội dung quyết định — vd: "chọn định danh CCCD làm lookup key thay vì SĐT"} | {PO/BA/Tech Lead} | {Lý do + phương án bị loại} | {PRD §X / MoM / ADR-XX} |

### Bảng phê duyệt

> UX Designer chỉ bắt buộc ký khi **Applicability Profile** có `UI`. Feature backend/integration/batch → bỏ dòng UX, thêm reviewer phù hợp (SRE / Data / Security) nếu cần.

| Vai trò | Họ tên | Chữ ký | Ngày |
|---|---|---|---|
| BA Lead | | | |
| Product Owner | | | |
| Tech Lead | | | |
| UX Designer *(nếu có UI)* | | | |

### Applicability Profile

> **Khai báo 1 lần — quyết định section nào áp dụng.** Đánh dấu ☑ vào loại feature. Section không áp dụng → ghi **"N/A — {lý do}"** ngay dưới heading, KHÔNG để bảng rỗng.

| Thuộc tính | Lựa chọn | Ảnh hưởng section |
|---|---|---|
| **SRS level** | `feature` *(cố định — tài liệu này là feature-level; System SRS dùng `srs-system-template.md`)* | validate-srs chấm khung feature N=29 (khớp marker `<!-- srs_level: feature -->` đầu file) |
| **Loại feature** | ☐ UI (B2C/B2B có màn hình) ☐ Backend/Process ☐ Integration-only ☐ Batch/Job | Chi phối §5.2 (control table), §11.1–11.2 (Figma/Screen) |
| **Có UI?** | ☐ Có → §5.2 control table + §11 Figma bắt buộc ☐ Không → §5.2 dùng "Interface Contract" thay control table; §11.1–11.2 = N/A | §5.2, §11.1, §11.2 |
| **Có state machine?** | ☐ Có → §6 bắt buộc ☐ Không → §6 = N/A | §6 |
| **Có tích hợp hệ thống ngoài?** | ☐ Có → §4.4/§4.5 + §2.6 bắt buộc ☐ Không | §4.4, §4.5, §2.6 |
| **Brownfield / cắt chuyển legacy?** | ☐ Có → §9.3 Data Migration bắt buộc ☐ Không → §9.3 = N/A | §9.3 |
| **Domain** | `lending / insurance / payment / commerce / {khác}` | Nạp domain-checklist tương ứng; thay placeholder ví dụ |
| **Mode soạn** | ☐ draft ☐ standard ☐ full | Cắt các mục `[std]`/`[full]` theo mode |

---

## 1. Introduction

### 1.1 Purpose

{Mô tả mục đích tài liệu — đặc tả yêu cầu phần mềm chi tiết cho {FR-XX}: {Tên chức năng} thuộc {Tên dự án}. Phạm vi bao gồm {N} chức năng con ({FR-XX-01} → {FR-XX-0N}) của **{service-name}**.}

| | |
|---|---|
| **Vấn đề cần giải quyết** | {Mô tả vấn đề nghiệp vụ mà flow này giải quyết.} |
| **Business Goals & Metrics** | {Metric ID}: {Chỉ số mục tiêu}. Nguồn: {PRD Metrics MX}. |
| **Loại chức năng** | ☐ Mobile app &nbsp;&nbsp; ☐ Web app &nbsp;&nbsp; ☐ Tiến trình &nbsp;&nbsp; ☐ API |
| **Đường dẫn chức năng** | {Đường dẫn menu/navigation dẫn đến chức năng.} |
| **Precondition** | {UC-XX-01}: {Điều kiện tiên quyết}. {UC-XX-02}: {Điều kiện tiên quyết}. |
| **Post-condition** | {Trạng thái hệ thống sau khi UC hoàn thành thành công. Bao gồm: DB state, events published, session state.} |
| **Flow liên quan** | Flow {YY} ({Tên}) → **Flow {XX} (này)** → Flow {ZZ} ({Tên}) |

### 1.2 Scope

**Phạm vi (In-scope):**

| Sub-FR | Chức năng | Phân kỳ |
|--------|-----------|---------|
| FR-{XX}-01 | {Tên chức năng} | MVP Bắt buộc / MVP Nên có / Phase 2 |
| FR-{XX}-02 | {Tên chức năng} | MVP Bắt buộc |

**Ngoài phạm vi (Out-of-scope):**
- {Tính năng A} — {Lý do / Phase kế hoạch}
- {Tính năng B} — {Lý do}

**Priority Matrix `[full]`** *(tuỳ chọn — hỗ trợ release planning; bỏ ở mode draft/standard nếu không cần)*

> `Technical Complexity` là **ước lượng sơ bộ của dev** — BA điền tạm, đánh dấu *(tentative)*, chốt lại ở Sprint Planning. Business Value + Risk do PO/BA.

| Sub-FR | Business Value (H/M/L) | Technical Complexity *(dev-est)* | Risk (H/M/L) | Priority tổng hợp |
|---|---|---|---|---|
| FR-{XX}-01 | H | M *(tentative)* | M | Must / P0 |
| FR-{XX}-02 | M | L *(tentative)* | L | Should / P1 |

### 1.3 Definitions & Acronyms

> **Canonical:** §1.3 là **nguồn chính** cho thuật ngữ dùng trong tài liệu này. §11.6 Glossary chỉ mở rộng/tham chiếu — KHÔNG định nghĩa mâu thuẫn. Nếu project có ubiquitous language / glossary chung → đồng bộ tên với nguồn đó.

| Thuật ngữ / Viết tắt | Giải thích |
|---|---|
| {DomainPlatform} | {Tên nền tảng/middleware của domain — vd: "LEP — Lending Enablement Platform", "NTBH — Nền tảng Bảo hiểm 2.0". Điền theo domain thực tế.} |
| {Thuật ngữ domain} | {Giải thích} |
| {Trạng thái / State} | {Mô tả trạng thái, quyền hạn tương ứng}. **Ghi chú lịch sử (nếu có):** {Lý do đặt tên / đổi tên}. |
| JWT | JSON Web Token — Token xác thực phiên *(giữ nếu feature dùng auth token)* |
| OTP | One-Time Password — Mã xác thực dùng một lần *(giữ nếu có)* |
| TTL | Time To Live — Thời gian hiệu lực *(giữ nếu có)* |
| {Luật/Quy định} | {Khung pháp lý áp dụng cho domain — vd: PDPA (bảo vệ dữ liệu), PCI-DSS (thẻ), Thông tư NHNN (tín dụng). Chỉ liệt kê cái áp dụng.} |

> **Hướng dẫn:** Chỉ giữ acronym thực sự xuất hiện trong tài liệu — xoá dòng không dùng để tránh nhiễu. Mỗi trạng thái entity (nếu flow có state machine) phải có entry riêng: mô tả, quyền hạn, ghi chú lịch sử nếu tên từng thay đổi.

### 1.4 References

| Tài liệu | Phiên bản | Vị trí |
|---|---|---|
| BRD | {vX} | `.vsaf/docs/{brd-file}.md` (nếu có) |
| PRD | {vX} | `.vsaf/docs/features/{feature-name}/02-prd.md` |
| Architecture | {vX} | `.vsaf/docs/features/{feature-name}/03-adr.md` |
| Epic Breakdown | {vX} | `.vsaf/docs/features/{feature-name}/04-epics.md` |
| System SRS | {vX} | `.vsaf/docs/{system-srs-file}.md` (nếu có) |
| Figma — {Tên màn hình} | {UC-XX-0N} | [{Node ID}]({figma-link}) — {Mô tả ngắn} |
| Figma — Mobile App {Tên} | {UC-XX-0N} | Export PDF `{file.pdf}` — {Mô tả} |

---

## 2. Business Context

### 2.1 Business Goals

| Metric ID | Chỉ số | Mục tiêu | Nguồn |
|---|---|---|---|
| {MX} | {Tên chỉ số} | {Giá trị mục tiêu} | PRD vX |

- {Mục tiêu nghiệp vụ 1}
- {Mục tiêu nghiệp vụ 2}

### 2.2 Stakeholders

| Stakeholder | Vai trò | Quyền lợi |
|---|---|---|
| BA Team | Business Analyst | Đảm bảo yêu cầu nghiệp vụ đầy đủ |
| Product Owner | Product Owner | Phê duyệt scope |
| Tech Lead | Technical Lead | Đánh giá khả thi kỹ thuật |
| UX Designer | UX Designer | Thiết kế trải nghiệm người dùng |

### 2.3 Actors / User Roles

> Actor trung lập domain. Ví dụ theo domain: lending → *Người vay / Nhân viên thẩm định*; insurance → *Policyholder / Underwriter*; payment → *Payer / Merchant*.

| Actor | Mô tả | Quyền hạn |
|---|---|---|
| {PrimaryActor} | {Người dùng cuối chính của feature} | {Thực hiện luồng nghiệp vụ chính, xem thông tin} |
| {AdminActor} | {Nhân viên nội bộ / vận hành} | {Quản trị, hỗ trợ, phê duyệt} |
| {service-name} | Internal service tự động | {Xử lý logic backend} |
| ES: {ExternalSystem} | Hệ thống ngoài tích hợp API | Refer: TBD |

### 2.4 Channels

- Web Mobile (Website / Webview tích hợp lên các Ứng dụng)
- {Mobile App / API / Admin Portal — điền kênh áp dụng}

### 2.5 Assumptions

> Mỗi giả định phải có **Status + Owner + Deadline** — assumption không được xác nhận là rủi ro tiềm ẩn. `Chưa xác nhận` quá deadline → nâng thành rủi ro (§9) hoặc Open Question (§11.7).

| ID | Giả định | Status | Owner | Deadline xác nhận |
|---|---|---|---|---|
| ASM-01 | {Giả định nghiệp vụ/kỹ thuật} | ☐ Đã xác nhận ☐ Chưa xác nhận ☐ Bác bỏ | {Ai đảm bảo} | {YYYY-MM-DD} |
| ASM-02 | {Giả định — phụ thuộc bên ngoài} | ☐ Chưa xác nhận | {Bên phụ thuộc} | {YYYY-MM-DD} |

### 2.6 Dependencies

- **Phụ thuộc service:** {service-name} phụ thuộc {external-service-1}, {external-service-2}
- **Phụ thuộc API:** {Mô tả contract API cần finalize với bên nào}
- **Phụ thuộc flow:** {FR-XX} phụ thuộc {FR-YY} kích hoạt tại bước {N}

---

## 3. System Overview

### 3.1 System Description

{Mô tả tổng quan hệ thống — {service-name} đảm nhận vai trò gì trong luồng này. Liệt kê service chính, integration points, data flow tổng quan.}

| | |
|---|---|
| **Module thuộc về** | {service-name} — {Tên module} |
| **Bối cảnh pháp lý** | {Các quy định pháp luật liên quan: PDPA, Luật An ninh mạng, PCI-DSS.} |

### 3.2 High-Level Flow

> Diagram phải phân nhánh đầy đủ — không dùng nút tổng hợp đơn giản khi thực tế có nhiều kết quả khác nhau.

```plantuml
@startuml {FR-XX} Lifecycle Activity
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Arial
skinparam defaultFontSize 12
skinparam ActivityBorderColor #0A2956
skinparam ActivityBackgroundColor #D5DBE6
skinparam ActivityDiamondBorderColor #EE0033
skinparam ActivityDiamondBackgroundColor #FFD8D8
skinparam ArrowColor #333333
skinparam startColor #EE0033
skinparam endColor #EE0033

start
:{Bước khởi đầu};

if ({Điều kiện phân nhánh chính}?) then ({Nhánh A})
    :{UC-{XX}-01}: {Mô tả};
else ({Nhánh B})
    if ({Điều kiện phụ}?) then ({Kết quả 1})
        :{Trạng thái kết quả 1};
    else ({Kết quả 2})
        :{Trạng thái kết quả 2};
    endif
endif

stop
@enduml
```

### 3.3 Architecture Overview

```plantuml
@startuml
!pragma layout smetana
top to bottom direction
skinparam backgroundColor #2D2D3F
skinparam defaultFontColor #EEEEEE
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam ArrowColor #7EAAF0
skinparam componentBackgroundColor #3A3A50
skinparam componentBorderColor #555577
skinparam packageBackgroundColor #2D2D3F
skinparam packageBorderColor #555577

package "Presentation Layer" as PL #333348 {
  component [{Channel 1}] as CH1 #D4A843
  component [{Channel 2}] as CH2 #D4A843
}

package "{service-name}" as SVC #333348 {
  component [{Component 1}] as C1
  component [{Component 2}] as C2
}

package "External Systems" as EXT #333348 {
  component [{External 1}] as E1
  component [{External 2}] as E2
}

CH1 --> C1
CH2 --> C1
C1 --> C2
C1 --> E1
C2 --> E2

@enduml
```

**Nguyên tắc nền tảng:**
- {Nguyên tắc kiến trúc 1}
- {Nguyên tắc kiến trúc 2}

---

## 4. Data Model (Tham khảo — TSD chốt)

> Mô hình dữ liệu ở đây là tham khảo nghiệp vụ. TSD của {service-name} là nguồn chính xác cho schema DB.

### 4.1 Entity List

| Entity | Bảng DB | Mô tả | Service owner |
|--------|---------|-------|---------------|
| {EntityA} | `{table_a}` | {Mô tả} | {service-name} |
| {EntityB} | `{table_b}` | {Mô tả} | {service-name} |

### 4.2 Entity Details (Tham khảo - TSD chốt)

#### Bảng `{table_a}`

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `id` | UUID | ✅ | Primary Key |
| `{field}` | {type} | ✅ / ☐ | {Mô tả} |
| `status` | ENUM | ✅ | Trạng thái: `{StateA}` / `{StateB}` / `{StateC}` |
| `created_at` | TIMESTAMP | ✅ | Thời điểm tạo |
| `updated_at` | TIMESTAMP | ✅ | Thời điểm cập nhật cuối |

> **Ghi chú:** {Index, constraint đặc biệt nếu có.}

### 4.3 Relationships

```plantuml
@startuml {FR-XX} ER
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Arial
skinparam defaultFontSize 11

entity "{EntityA}" as A {
  * **id** : UUID <<PK>> #2255AA
  --
  * {field1} : {type}
  * {foreign_key_id} : UUID <<FK>> #55BB77
}

entity "{EntityB}" as B {
  * **id** : UUID <<PK>> #2255AA
  --
  * {field1} : {type}
  * {ref_field} : VARCHAR <<Ref>> #D4A843
}

A ||--o{ B : "{Quan hệ 1-N}"
@enduml
```

- {EntityA} — {EntityB}: {Mô tả quan hệ}

### 4.4 Kafka Events

| Event | Topic | Producer | Consumers | Mô tả |
|-------|-------|----------|-----------|-------|
| `{event.name}` | `{topic-name}` | {service-name} | {consumer-1, consumer-2} | {Khi nào publish} |

### 4.5 API Endpoints

| Method | Endpoint | Service | Mô tả | Auth |
|--------|----------|---------|-------|------|
| `POST` | `/api/v1/{resource}` | {service-name} | {Mô tả} | JWT |
| `GET` | `/api/v1/{resource}/{id}` | {service-name} | {Mô tả} | JWT |

**Version Compatibility `[full]`** *(chỉ khi Applicability Profile có API/integration & phải chạy đồng thời nhiều version)*

| API / Contract | Version | Trạng thái | Ai còn dùng | Kế hoạch deprecate |
|---|---|---|---|---|
| `/api/v{N}/{resource}` | v1 | Deprecated / Active | {client cũ} | {mốc gỡ} |
| `/api/v{N}/{resource}` | v2 | Active (feature này) | {client mới} | — |

> Nếu feature **không** đụng versioning → ghi "N/A — không thay đổi API contract".

---

## 5. Functional Requirements

### 5.1 Use Case List

| UC ID | Tên | Actor | Priority | FRs | Phương pháp kiểm thử |
|---|---|---|---|---|---|
| UC-{XX}-01 | {Tên UC} | {Actor} | Must Have / Should Have / Nice to Have | FR-{XX}-01 | Manual / API / E2E |
| UC-{XX}-02 | {Tên UC} | {Actor} | Must Have | FR-{XX}-02 | API / E2E |

### 5.2 Use Case Detail

> **Theo Applicability Profile (§0):**
> - **Feature có UI** → dùng bảng **control** (SCR-{XX}-01) + Figma mapping bên dưới.
> - **Backend/Process/Integration/Batch (không UI)** → BỎ bảng control, thay bằng **Interface Contract** (mẫu 5.2-B) mô tả input/output/trigger. Đánh dấu §11.1–11.2 = "N/A — feature không có UI".

> **Figma Web Mobile:** {Mô tả trạng thái Figma Web — màn hình nào đã có, áp dụng kênh nào. | N/A nếu không UI}
>
> **Figma Mobile App:** {Mô tả trạng thái Figma Mobile App — luồng nào đã có. | N/A nếu không UI}
>
> **Còn thiếu Figma:** {Liệt kê màn hình chưa có design. Xem Gap Analysis mục 11.4.}
>
> *(Figma Mapping tables chi tiết xem Appendix 11.1)*

> **Mẫu 5.2-B — Interface Contract (dùng thay bảng control khi KHÔNG có UI):**
>
> | Thuộc tính | Giá trị |
> |---|---|
> | **Kích hoạt bởi** | {API call `POST /...` / Kafka event `X` / Cron `0 2 * * *` / message queue} |
> | **Input** | {Schema/payload chính; ref §4.5 API hoặc §4.4 Event} |
> | **Xử lý** | {Tóm tắt logic; chi tiết ở Activity diagram + bảng mô tả luồng bên dưới} |
> | **Output / Side-effect** | {Response schema / event publish / DB write / file xuất} |
> | **Idempotency** | {Key idempotent + hành vi khi trùng — ref BR-{XX}-00-xx} |
> | **SLA/Throughput** | {ref §8.1 — vd p95 ≤ 800ms @ 200 TPS} |

---

> **⚠️ {Ghi chú ưu tiên MVP hoặc quyết định kiến trúc quan trọng nếu có}**

#### UC-{XX}-01: {Tên Use Case}

##### Màn hình SCR-{XX}-01 — {Tên màn hình} (Website)

> **Figma Web Mobile:** [{Tên frame} `{node-id}`]({figma-link})
> - **{Bước / State}** (`{node-id}`, {WxH}px): {Mô tả layout và các control chính}
> - **Error state** (`{node-id}`): {Mô tả}
> - **Lưu ý:** {Điểm khác biệt Figma vs SRS — cần confirm PO}

| STT | Tên control | Loại control | Require | Maxlength | Giá trị mặc định | Mô tả |
|---|---|---|---|---|---|---|
| 1 | {controlId} | Text Input / Button / Checkbox / Dropdown / DatePicker / ImageUpload | Bắt buộc / Tùy chọn / — | {N} | — | {Mô tả mục đích}. **Validate:** • {Trường hợp lỗi 1} → "{Thông báo lỗi}" • {Trường hợp lỗi 2} → "{Thông báo lỗi}" |

> **Prefix control:** `txt` TextInput · `btn` Button · `lbl` Label · `chk` Checkbox · `lnk` Link/Hyperlink · `ddl` Dropdown · `dt` DatePicker · `img` ImageUpload

##### Màn hình SCR-{XX}-01-MOB — {Tên màn hình} (Mobile App)

> **Figma Mobile App:** Export PDF `{file.pdf}`
> - **{Thành phần}:** {Mô tả}
>
> **Khác biệt Mobile App vs Web Mobile:**
> | Tiêu chí | Web Mobile | Mobile App |
> |---|---|---|
> | {Tiêu chí 1} | {Web} | {Mobile} |
> | Input định danh | Radio SĐT / CCCD | Single input tự nhận dạng format (10 số = SĐT; 9–12 ký tự = CCCD) |

| STT | Tên control (Mobile App) | Loại control | Require | Maxlength | Giá trị mặc định | Mô tả |
|---|---|---|---|---|---|---|
| 1 | {controlId_MOB} | Text Input | Bắt buộc | 12 | — | {Mô tả}. **Lưu ý:** {Single input / format detection}. **Validate:** • {Lỗi} → "{Thông báo}" |

> **Prefix Mobile:** thêm `_MOB` suffix (VD: `txtHoTen_MOB`)

##### Activity Diagram — UC-{XX}-01

```plantuml
@startuml UC-{XX}-01 Activity
skinparam backgroundColor #FAFAFA
skinparam defaultFontName Arial
skinparam defaultFontSize 12
skinparam ActivityBorderColor #0A2956
skinparam ActivityBackgroundColor #D5DBE6
skinparam ActivityDiamondBorderColor #EE0033
skinparam ActivityDiamondBackgroundColor #FFD8D8
skinparam ArrowColor #333333
skinparam startColor #EE0033
skinparam endColor #EE0033

start
:(1) {Bước 1};
:(2) {Bước 2};

if ({Điều kiện}?) then (Không)
    :(3a) {Bước nhánh lỗi};
    stop
else (Có)
endif

:(N) {Bước cuối};
stop
@enduml
```

##### Mô tả luồng nghiệp vụ

| Bước | Đối tượng | Mô tả | Ghi chú | Bảng/Thực thể liên quan |
|---|---|---|---|---|
| 1 | {Actor / Frontend / service-name} | {Mô tả hành động} | {BR liên quan. EF: Exception Flow. AF: Alternative Flow.} | {table_a} |
| 2 | ES: {ExternalSystem} | {Mô tả} | Refer: TBD | — |

> **Phân nhánh DRAFT/ACTIVE edge-case (nếu có):**
>
> | Bước | Đối tượng | Mô tả | Ghi chú | Bảng/Thực thể liên quan |
> |---|---|---|---|---|
> | {N}a | {service-name} | **[Phân nhánh {StateA}]** {Mô tả xử lý} | BR-{XX}-00-01. | {entity} |
> | {N}b | {service-name} | **[Phân nhánh {StateB}]** {Mô tả xử lý} | BR-{XX}-{N}-01. | {entity} |

**Luồng thay thế:** ALT1: {Mô tả}

**Luồng ngoại lệ:** EX1: {Mô tả} ({ERR-{XX}-001}) → {Xử lý}. EX2: {Mô tả} → {Xử lý}.

**Mapping Epic:** Story {X.Y} (Epic {Z}) — {Tên Story}

---

#### UC-{XX}-0N: {Tên Use Case tiếp theo}

> *(Lặp lại cấu trúc UC-{XX}-01 cho từng UC)*

---

### 5.3 Acceptance Criteria

> Trích từ {PRD vX.X}. Format: Given/When/Then. Mapping UC trong SRS này.

| AC ID | UC liên quan | Mô tả |
|---|---|---|
| AC-{FR-XX}-01 | UC-{XX}-01 | Given {điều kiện}, When {hành động}, Then {kết quả mong đợi + event published nếu có} |
| AC-{FR-XX}-02 | UC-{XX}-01 | Given {điều kiện lỗi}, When {hành động}, Then {error response + UI feedback} |
| AC-{FR-XX}-03 | UC-{XX}-02 | Given {điều kiện entity ở StateB}, When {hành động nâng cấp thành công}, Then {entity upgraded to StateA} + {event published} |

---

## 6. State & Behavioral Models

> Bắt buộc khi flow quản lý entity có nhiều trạng thái. Nếu không có state machine → bỏ section này.

### 6.1 State Definitions

```plantuml
@startuml
!pragma layout smetana
skinparam backgroundColor #2D2D3F
skinparam defaultFontColor #EEEEEE
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam ArrowColor #7EAAF0
skinparam ArrowFontColor #CCCCCC
skinparam stateBackgroundColor #3A3A50
skinparam stateBorderColor #555577
skinparam stateFontColor #EEEEEE

[*] --> {StateA} : {UC tạo entity — điều kiện đầy đủ}
[*] --> {StateB} : {UC tạo entity — điều kiện thiếu / shell}
{StateB} --> {StateA} : {UC nâng cấp — điều kiện hoàn chỉnh}
{StateA} --> {StateC} : {Admin deactivate / business event}
{StateC} --> {StateA} : {Admin reactivate}

state {StateA} #55BB77
state {StateB} #7777DD
state {StateC} #E06070
@enduml
```

| Trạng thái | Mô tả | Quyền hạn | Trigger vào | Trigger ra | Ai thực hiện |
|---|---|---|---|---|---|
| {StateA} | {Mô tả}. **Có {external auth account}.** | ✅ {Quyền đầy đủ} | {UC / event tạo ra} | {UC / event chuyển ra} | System / Admin |
| {StateB} | {Mô tả — incomplete / shell}. **Không có {external auth account}.** | ✅ Xem ❌ Thực hiện | {UC / điều kiện} | {UC nâng cấp} | System (tự động) |
| {StateC} | {Mô tả — deactivated / blocked} | ❌ Mọi quyền | {Admin action / policy} | {Admin reactivate} | {Admin role} |
| *({LOCK_TEMP})* | **Không phải DB status** — cờ tạm thời trong {external system} khi {điều kiện}. `status` DB vẫn là `{StateA}`. Tự giải phóng sau {N} phút. | ❌ {Quyền bị giới hạn} | {Trigger} | {Recovery / timeout} | {External system} (tự động) |

### 6.2 Transitions

| From | To | Điều kiện | UC trigger | Event publish |
|------|----|-----------|-----------|---------------|
| `[*]` | {StateA} | {Điều kiện đầy đủ} | UC-{XX}-01 | `{event.created}` |
| `[*]` | {StateB} | {Điều kiện thiếu} | UC-{XX}-01 | `{event.draft}` |
| {StateB} | {StateA} | {Điều kiện hoàn chỉnh} | UC-{XX}-0N | `{event.activated}` |
| {StateA} | {StateC} | Admin deactivate | UC-admin | `{event.deactivated}` |

### 6.3 Decision Matrix — Kết quả theo điều kiện đầu vào `[std]`

> Bắt buộc khi flow có ≥2 UC tạo cùng entity với kết quả trạng thái khác nhau tùy điều kiện. Giúp dev/QA tra cứu nhanh. Mode `draft` có thể bỏ.

| UC | {Điều kiện 1} | {Điều kiện 2} | {Điều kiện 3} | Kết quả `status` | Event | {Auto-xxx}? |
|---|---|---|---|---|---|---|
| UC-{XX}-01 | {Giá trị} | {Giá trị} | {Giá trị} | **{StateA}** | `{event.name}` | ✅ |
| UC-{XX}-01 | {Giá trị khác} | {Giá trị} | — | **{StateB}** | `{event.draft}` | ❌ → UC-{XX}-0N |
| UC-{XX}-0N | Bất kỳ ({StateB} nâng cấp) | ✅ | — | **{StateA}** | `{event.activated}` | ✅ |

> **Lưu ý:**
> - `{LOCK_TEMP}` **không phải** DB status — không xuất hiện trong bảng trên.
> - {Global rule BR-{XX}-00-01} áp dụng trước mọi dòng "{External} Không".

---

## 7. Business Rules & Validation

### 7.1 Business Rules

> Bắt đầu bằng nhóm **BR-{XX}-00-xx** cho global rules áp dụng toàn flow (cross-cutting: idempotency, state machine, integration pattern, identifier policy).

| Mã | Nội dung | Tham chiếu | UC liên quan |
|---|---|---|---|
| BR-{XX}-00-01 | **{Tên global rule — VD: Pre-check + State-before-external-call}:** {Mô tả đầy đủ pattern. (1) Điều kiện trigger. (2) Hành động bắt buộc trước khi gọi hệ thống ngoài. (3) Hành động sau khi hệ thống ngoài thành công.} | {Nghiệp vụ / Architecture / PRD} | UC-{XX}-01, UC-{XX}-02, ... |
| BR-{XX}-00-02 | **Quy tắc định danh toàn flow:** {Mô tả định danh nào được dùng làm lookup key.} | {Quyết định nghiệp vụ} | Tất cả UC |
| BR-{XX}-01-01 | {Nội dung BR cụ thể cho UC-{XX}-01} | PRD vX — FR-{XX}-01 | UC-{XX}-01 |
| BR-{XX}-01-02 | {Nội dung BR} | {Nguồn} | UC-{XX}-01 |

### 7.2 Validation Rules

> **Bắt buộc ghi boundary tường minh** (min/max/độ dài/định dạng cụ thể) — để QA có sẵn ranh giới sinh test. *Enumeration test data đầy đủ (positive/boundary/negative/invalid/performance) là việc của `sdlc-test-design` (Phase 5) — SRS không liệt kê data cụ thể, chỉ cung cấp ranh giới + AC (§5.3).*

| Field | Rule | Boundary tường minh | Thông báo lỗi |
|-------|------|---------------------|---------------|
| {fieldName} | Required — không được để trống | — | "{Tên field} không được để trống" |
| {fieldName} | Format — {regex / pattern} | {vd: `^0\d{9}$` — 10 chữ số} | "{Thông báo lỗi format}" |
| {fieldName} | Range | min={N}, max={M} *(inclusive?)* | "{Thông báo lỗi range}" |

### 7.3 Error Handling

> Bước tương ứng với bước trong Activity Diagram mục 5.2

| STT | Bước | Trường hợp | Mã lỗi | Thông báo lỗi |
|---|---|---|---|---|
| 1 | UC-{XX}-01 Bước {N} | {Mô tả trường hợp lỗi} | ERR-{XX}-001 (HTTP {4xx/5xx}) | "{Thông báo lỗi hiển thị cho user}" |
| 2 | General | Rate limit exceeded | ERR-{XX}-{N} (HTTP 429) | "Quá nhiều yêu cầu. Vui lòng thử lại sau." |
| 3 | General | Server error | ERR-{XX}-{N} (HTTP 500) | "Hệ thống đang bận, vui lòng thử lại sau" |

---

## 8. Non-Functional Requirements

> Chỉ liệt kê NFR **đặc thù cho flow này**. NFR chung toàn hệ thống xem System SRS.

### 8.1 Performance

| ID | Nhóm | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|---|
| NFR-PERF-01 | Performance | {Yêu cầu — p95 latency, throughput} | {≤ N giây / N ms} |
| NFR-SCALE-01 | CCU | Concurrent users | MVP: {N}K CCU; Year 1: {N}K CCU |
| NFR-SCALE-02 | Stateless | Service stateless | Session lưu Redis, không lưu in-memory |

### 8.2 Security (Tham khảo)

| ID | Nhóm | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|---|
| NFR-SEC-01 | Security | {Yêu cầu bảo mật} | {Tiêu chí đo lường} |

**Observability Specification** *(cho DevOps/SRE — thay NFR-OBS rời rạc bằng bảng có cấu trúc)*

| Sự kiện/luồng cần quan sát | Log (mức + nội dung) | Metric (tên + loại) | Trace | Dashboard | Alert (điều kiện) |
|---|---|---|---|---|---|
| {vd: giải ngân thành công} | INFO — {fields, KHÔNG log PII/secret} | `{metric_name}` counter | correlationId qua Kafka/HTTP | {tên dashboard} | {vd: error rate > 1%/5m} |
| {vd: gọi service ngoài lỗi} | ERROR — {mã lỗi, không lộ token} | `{metric}` counter | span tới ES | {dashboard} | {timeout > N/phút} |

> **Ràng buộc:** log KHÔNG chứa mật khẩu/token/PII thô (mask). Correlation ID propagate xuyên Kafka/HTTP cho mọi request.

### 8.3 Usability (Tham khảo)

> Chỉ áp dụng khi Applicability Profile có `UI`. Feature backend/integration/batch → "N/A — không có giao diện người dùng".

| ID | Nhóm | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|---|
| NFR-A11Y-01 | WCAG | Mức tuân thủ | WCAG 2.1 Level AA cho tất cả B2C screens |
| NFR-A11Y-02 | WCAG | Touch target | Minimum 44x44px cho mobile touch targets |

### 8.4 Reliability (Tham khảo)

| ID | Nhóm | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|---|
| NFR-AVAIL-01 | Availability | Uptime {service-name} | ≥ {X}% |
| NFR-COMP-01 | Compliance | {Yêu cầu tuân thủ pháp lý} | {Tiêu chí} |

**Recovery Objectives:**

| Service | RPO | RTO | Rationale |
|---|---|---|---|
| {service-name} | ≤ {N} phút | ≤ {N} phút | {Lý do — tác động nếu down} |

---

## 9. Constraints (Tham khảo)

### 9.1 Technical Constraints (Tham khảo)

- **CON-01 —** {Tên ràng buộc}: {Mô tả ràng buộc kỹ thuật}
- **CON-02 —** {Tên ràng buộc}: {Mô tả}

### 9.2 Legal Constraints (Tham khảo)

> Điền theo domain trong Applicability Profile: lending → Thông tư NHNN; insurance → Thông tư bảo hiểm; payment/thẻ → PCI-DSS; mọi domain có PII → PDPA/Luật BVNTD.

- **LEG-01:** {Ràng buộc pháp lý áp dụng cho domain}
- **LEG-02:** {Ràng buộc tuân thủ khác}

### 9.3 Data Migration & Backfill (Tham khảo)

> **Bắt buộc khi Applicability Profile = brownfield / cắt chuyển legacy.** Nếu greenfield → ghi "N/A — feature mới hoàn toàn, không có dữ liệu cũ".

| Hạng mục | Nội dung |
|---|---|
| **Nguồn dữ liệu cũ** | {Hệ thống/bảng legacy nguồn; ước lượng số bản ghi} |
| **Phạm vi migrate** | {Migrate toàn bộ / chỉ active / cut-off theo ngày} |
| **Mapping** | {Field cũ → field mới; ref §4; giá trị enum cũ → enum mới} |
| **Chiến lược** | ☐ Big-bang ☐ Song song (dual-write) ☐ Cuốn chiếu theo tập khách |
| **Backfill / dữ liệu thiếu** | {Trường mới không có ở nguồn cũ → default / suy diễn / {{Cần bổ sung}}} |
| **Reconciliation** | {Cách đối soát sau migrate — count match, checksum, sampling} |
| **Rollback** | {Điều kiện & cách hoàn tác nếu migrate lỗi} |
| **Downtime** | {Cần dừng dịch vụ không? Bao lâu? / Zero-downtime} |

**Yêu cầu chuyển đổi (Transition Requirements):**

> {Không áp dụng — flow mới hoàn toàn. / Hoặc: tóm tắt migration plan — chi tiết ở bảng 9.3.}

**Rủi ro liên quan:**

| STT | Rủi ro | Khả năng | Tác động | Giảm thiểu |
|---|---|---|---|---|
| 1 | {Mô tả rủi ro} | Cao / Trung bình / Thấp | Cao / Trung bình / Thấp | {Biện pháp giảm thiểu} |

### 9.4 Feature Toggle / Rollout `[full]`

> *(Tuỳ chọn — chỉ khi feature phát hành sau feature flag / rollout theo tỷ lệ.)* Không dùng flag → "N/A — release trực tiếp".

| Toggle | Default | Chiến lược rollout | Owner | Điều kiện tắt/dọn flag |
|---|---|---|---|---|
| `{feature.toggle.key}` | OFF | {% canary → 100% / theo tập KH} | {team} | {khi ổn định N ngày → gỡ flag} |

---

## 10. RTM

> Truy xuất từ PRD/BRD → UC → Màn hình → BR → AC → Test Case → Epic/Story

| PRD FR | UC ID | Màn hình | BR | AC | Test Case | Epic/Story | Ghi chú |
|--------|-------|----------|----|----|-----------|------------|---------|
| FR-{XX}-01 | UC-{XX}-01 | SCR-{XX}-01, SCR-{XX}-01-MOB | BR-{XX}-01-01 | AC-{FR-XX}-01 | TC-{XX}-01 | Story {X.Y} (Epic {Z}) | {☑/☐} Web Figma {☑/☐} Mobile App Figma |
| FR-{XX}-02 | UC-{XX}-02 | SCR-{XX}-03 | BR-{XX}-02-01 | AC-{FR-XX}-03 | TC-{XX}-03 | Story {X.Y} (Epic {Z}) | Cần Figma cho SCR-{XX}-03 |

---

## 11. Appendix

### 11.1 Figma Mapping

#### Mapping Figma Web Mobile ↔ SRS Screens

| SRS Screen | Figma Web Mobile | Figma Node ID | Figma Node IDs chi tiết | Ghi chú |
|---|---|---|---|---|
| SCR-{XX}-01 {Tên màn hình} | **{Tên Figma frame}** | `{node-id}` | {node IDs chi tiết} | {Ghi chú khác biệt / trạng thái} |
| SCR-{XX}-02 {Tên màn hình} | *Chưa có Figma* | — | — | Cần bổ sung |

#### Mapping Figma Mobile App ↔ SRS Screens

| SRS Screen | Figma Mobile App | Nguồn PDF | Mô tả chi tiết | Khác biệt so với Web Mobile |
|---|---|---|---|---|
| SCR-{XX}-01-MOB {Tên} (Mobile App) | **{Tên Figma frame}** | `{file.pdf}` | {Mô tả đầy đủ: control, CTA, navigation} | **(1)** {Khác biệt 1}. **(2)** {Khác biệt 2}. |

### 11.2 Screen List

| Screen | Kênh | Figma | UC liên quan | Mô tả |
|--------|------|-------|-------------|-------|
| SCR-{XX}-01 | Web Mobile | ✅ `{node-id}` | UC-{XX}-01 | {Mô tả} |
| SCR-{XX}-01-MOB | Mobile App | ✅ PDF `{file.pdf}` | UC-{XX}-01 | {Mô tả} |
| SCR-{XX}-02 | Web Mobile | ❌ Chưa có | UC-{XX}-02 | {Mô tả} |

### 11.3 Architecture Detail `[full]`

> **Canonical:** §3.3 là Architecture Overview chính. §11.3 chỉ chứa sơ đồ **bổ sung** (sequence/deployment/…) — KHÔNG lặp lại §3.3. Mode `draft`/`standard` có thể bỏ.

### 11.4 Chức năng ảnh hưởng & Impact Matrix

**Chức năng ảnh hưởng (business/flow):**

| STT | Kênh | Chức năng | Nội dung ảnh hưởng |
|---|---|---|---|
| 1 | {Kênh} | {FR-YY}: {Tên chức năng} | {Mô tả ảnh hưởng — flow dependency, event consumer, data shared.} |
| 2 | {Kênh} | {service-name} | Nhận events: `{event.name}` ({Mô tả hành động}). |

**Technical Impact Matrix** — đánh dấu tầng bị chạm để impact analysis đầy đủ (đặc biệt cho microservices):

| Tầng | Bị ảnh hưởng? | Chi tiết (cái gì / vì sao) |
|---|---|---|
| **API** | ☐ Có ☐ Không | {Endpoint mới/đổi; breaking change? ref §4.5} |
| **DB / Schema** | ☐ Có ☐ Không | {Bảng/cột mới, migration; ref §4 + §9.3} |
| **Cache** | ☐ Có ☐ Không | {Key mới, invalidation, TTL} |
| **Kafka / Event** | ☐ Có ☐ Không | {Event mới, đổi consumer; ref §4.4} |
| **Batch / Job** | ☐ Có ☐ Không | {Job bị chạm / cần thêm} |
| **Scheduler / Cron** | ☐ Có ☐ Không | {Lịch mới/đổi} |
| **Permission / Role** | ☐ Có ☐ Không | {Role/quyền mới; ref §2.3} |
| **Notification** | ☐ Có ☐ Không | {Template/kênh thông báo mới} |
| **Config / Feature flag** | ☐ Có ☐ Không | {Config mới; ref §9 Feature Toggle nếu có} |

### 11.5 Gap Analysis

> Gap đã giải quyết: strikethrough `~~GA-{XX}-01~~`. Loại: `Thiếu Figma` / `Khác biệt` / `Mâu thuẫn` / `Thiếu UC`

| Gap ID | Loại | Mô tả | Ảnh hưởng | Đề xuất xử lý |
|---|---|---|---|---|
| GA-{XX}-01 | Thiếu Figma | {Màn hình chưa có design} | {Ảnh hưởng Dev/QA} | {Cần confirm PO / UX} |

### 11.6 Glossary

> **Mở rộng của §1.3** — không định nghĩa mâu thuẫn với §1.3. Dùng cho thuật ngữ domain phụ / nâng cao không cần ở phần Introduction.

| Thuật ngữ | Định nghĩa |
|-----------|-----------|
| {Term} | {Definition} |

### 11.7 Open Questions

> **Khác Gap Analysis (§11.5):** Gap = thiếu design/UC/mâu thuẫn artifact; Open Question = **câu hỏi nghiệp vụ chưa chốt** cần Business/PO trả lời. Câu hỏi còn `Open` = chặn hoặc rủi ro cho implement. Đóng → strikethrough.

| ID | Câu hỏi | Owner | Due | Status |
|---|---|---|---|---|
| OQ-{XX}-01 | {Câu hỏi nghiệp vụ chưa có đáp án — vd "hạn mức trần khi KH có 2 hồ sơ?"} | {PO / Business} | {YYYY-MM-DD} | ☐ Open ☐ Answered |

### 11.8 AI Metadata `[full]`

> **Block máy-đọc cho agent downstream (Dev/QA/Architect) & Reuse Index của feature sau.** Là *bản tóm tắt phái sinh* từ nội dung SRS ở trên — KHÔNG thêm khái niệm mới ở đây; mọi mục phải xuất hiện trong section tương ứng. Mode `draft`/`standard` có thể bỏ.

```yaml
ai_metadata:
  feature: "{FR-XX} {Tên}"
  entities:            # từ §4
    - name: "{EntityA}"
      states: ["{StateA}", "{StateB}"]   # từ §6 nếu có
  business_events:     # từ §4.4
    - "{event.name}"
  commands:            # hành động ghi/biến đổi state — từ §5 UC
    - "{CreateX}"
  queries:             # hành động đọc — từ §5 UC
    - "{GetX}"
  aggregates:          # nhóm entity + invariant — từ §6/§7
    - "{AggregateRoot}"
  external_apis:       # từ §4.5 / §2.6
    - "{ExternalSystem}"
  glossary_source: "{link §1.3 / GLOSSARY dự án}"
  confidence:          # từ Self-check Bước 5 của skill
    overall: "High | Medium | Low"
    low_sections: ["{§ nào còn {{Cần bổ sung}}}"]
```

---

*Tài liệu cần review bởi: Product Owner, UX Designer *(nếu có UI)*, Tech Lead trước khi chuyển sang Sprint Planning.*

*Các điểm cần Business confirm: xem §11.7 Open Questions (câu hỏi nghiệp vụ) và §11.5 Gap Analysis (thiếu artifact).*

*-- Hết tài liệu SRS Flow {XX} --*
