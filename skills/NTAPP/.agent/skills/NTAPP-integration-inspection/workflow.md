# WORKFLOW: NTAPP INTEGRATION INSPECTION

**Version:** 1.0.0
**Author:** M2MBA
**Last Updated:** 2026-06-09

Quy trình đầy đủ để sinh **bộ tài liệu phân tích & đặc tả tích hợp end-to-end** với đối tác. Điều khiển qua 2 tham số: **`direction`** (chiều tích hợp) + **`mode`** (cách làm việc). Entry point + overview: xem `SKILL.md`.


---

## 1. Đầu vào bắt buộc

Khi user khởi động skill, **BẮT BUỘC hỏi** trước khi phân tích:

1. **Tên hệ thống đối tác** — quyết định thư mục lưu file.
2. **Bối cảnh dự án & mục tiêu tích hợp** — domain, mục tiêu nghiệp vụ: tạo gì, tra cứu gì, đồng bộ gì.
3. **Tài liệu tích hợp** — OpenAPI/Swagger, Postman, WSDL, file spec, schema message, hoặc mô tả text.
4. **Bối cảnh hệ thống nội bộ** — các hệ thống tham gia (Core, OMS, CRM…), ERD/bảng hiện hữu, có tích hợp nhiều đối tác không.
5. **`direction` — chiều tích hợp** (nếu user chưa nói rõ, hỏi):

   | Giá trị | Ý nghĩa | Ảnh hưởng phân tích |
   |---|---|---|
   | `outbound` | **Mình gọi đối tác** — consume API/file/message của đối tác, map về model nội bộ | Source [IN] = UI nhập / DB cấu hình / BE tự sinh; đặc tả = đọc hiểu API đối tác; mapping = response đối tác → model nội bộ |
   | `inbound` | **Đối tác gọi mình** — mình expose API/data cho đối tác dùng | Source = field đối tác cần; đặc tả = API **mình** cung cấp ("hành động đề xuất cho đối tác"); nhấn data scoping + PII masking + rate limit |
   | `bidirectional` | **Hai chiều** | Phân tích cả hai góc nhìn, tách rõ luồng inbound/outbound |

6. **`mode` — cách làm việc** (default `batch` nếu user không nói):

   | Giá trị | Hành vi |
   |---|---|
   | `batch` | Xuất **toàn bộ 14 mục trong 1 lần**, đánh dấu **[Giả định]** rõ ràng chỗ thiếu thông tin. Không hứa "làm sau". |
   | `interactive` | Đi **từng mục**: sinh nội dung → hỏi câu hỏi khơi gợi (nhóm Nghiệp vụ/Dữ liệu/Bảo mật/Vận hành) → confirm 1 lần → mới sang mục tiếp. Ghi nhận câu hỏi **chưa có câu trả lời** để tổng hợp vào Mục 12. |

**Nhận diện loại tích hợp** — sau khi nhận tài liệu, tự động nhận diện rồi confirm **1 lần** trước khi phân tích. Bảng dấu hiệu + cách điều chỉnh section theo loại: [`references/integration-types.md`](references/integration-types.md).

Nếu không đủ dấu hiệu → hỏi thẳng: *"Đối tác tích hợp theo kiểu nào: REST API / File / Message Queue / SOAP / Hybrid?"*

---

## 2. Cấu trúc output — 14 mục

Bộ tài liệu hợp nhất gồm 14 mục dưới đây. Ở `mode: batch` xuất hết một lần; ở `mode: interactive` đi tuần tự theo thứ tự này. Mọi thông tin chưa confirm đánh dấu **[Giả định]** in đậm.

| # | Mục | Ghi chú điều chỉnh theo `direction` / loại tích hợp |
|---|-----|---|
| 1 | **Tổng quan & mục đích tích hợp** + bảng tóm tắt nhanh | Ghi rõ `direction`, loại tích hợp, môi trường, độ phức tạp |
| 2 | **Dữ liệu & mapping nội bộ** (trạng thái ✅ có sẵn / ⚠️ cần transform / ❌ chưa có) | Source [IN] đổi theo `direction` + loại — xem [`references/erd-and-mapping.md`](references/erd-and-mapping.md) |
| 3 | **Use Case & màn hình/chức năng cần xây** | `outbound`: màn cấu hình + gọi API; `inbound`: API mình expose + màn quản lý đối tác |
| 4 | **Danh sách thay đổi thực thể dữ liệu** (Phần A thêm mới / B bổ sung trường / C dataset chi tiết) — **BẮT BUỘC** | Tên field DB `snake_case`; tên field API theo loại — xem [`references/erd-and-mapping.md`](references/erd-and-mapping.md) |
| 5 | **Luồng tích hợp tổng thể** (mô tả 4 phần + pseudo flow) | **PHẢI** đủ 3 giai đoạn E2E (xem §3) |
| 6 | **Sequence Diagram** (Mermaid, `autonumber`, `Note over` phân nhóm) | Participant theo loại; KHÔNG đưa Database vào diagram — xem [`references/sequence-diagram-examples.md`](references/sequence-diagram-examples.md) |
| 7 | **Bảng mapping API ↔ Sequence** (cầu nối sang Mục 8) | Liệt kê theo thứ tự step trong sequence |
| 8 | **Đặc tả kỹ thuật chi tiết** (API / File / Message / WSDL) | Tên section + nội dung đổi theo loại. REST API dùng template đầy đủ — xem [`references/api-spec-template.md`](references/api-spec-template.md) |
| 9 | **ERD tích hợp đa đối tác** (Mermaid `erDiagram`) — **BẮT BUỘC** | Phản ánh đúng Mục 4; annotation nghiệp vụ; tư duy đa đối tác — xem [`references/erd-and-mapping.md`](references/erd-and-mapping.md) |
| 10 | **Non-Functional Requirements** (response time, availability, rate limit, timeout, retry, retention) | |
| 11 | **Rủi ro & Phụ thuộc** | |
| 12 | **Điểm cần làm rõ với đối tác** (bộ câu hỏi elicitation nhóm A/B/C) | Tự đối chiếu [Giả định] để đánh dấu 🔴/🟡 — xem [`references/elicitation-questions.md`](references/elicitation-questions.md) |
| 13 | **HTML Prototype** *(tùy chọn — hỏi user)* | Field bám bảng Mục 2 + Mục 4-C |
| 14 | **Checklist go-live** — **BẮT BUỘC** | Sandbox / Security / NFR / Documentation / Operations |

> 📎 Template file output đầy đủ (đủ Lịch sử thay đổi + 14 mục): [`references/output-template.md`](references/output-template.md).

---

## 3. Quy tắc E2E bắt buộc — 3 giai đoạn

Mọi **pseudo flow** (Mục 5), **mô tả quy trình** và **sequence diagram** (Mục 6) **PHẢI** đi theo 3 giai đoạn, đúng thứ tự:

1. **[AUTH]** — Xác thực đối tác/người dùng. Xác định cơ chế (API Key, OAuth2 Client Credentials / Authorization Code, Basic Auth, JWT, mTLS), nơi lưu credential, cách attach vào request (header / token / certificate).
2. **[DATA MAPPING]** — Thiết lập dữ liệu phục vụ tích hợp: bước tiền đề tạo/đồng bộ master data (KH, kho, sản phẩm…), mapping mã nội bộ ↔ mã đối tác **trước** khi gọi luồng chính.
3. **[INTEGRATION FLOWS]** — Luồng nghiệp vụ chính: gọi API / truyền file / gửi message theo từng use case.

Ví dụ minh họa (`outbound`):
- **[AUTH]** `POST /oauth/token` → nhận `access_token` (TTL 1h) → cache, tự refresh khi hết hạn.
- **[DATA MAPPING]** Tạo KH nội bộ → `CreateCustomer` → lưu `partnerCustomerId`; cấu hình kho → `RegisterWarehouse` → lưu `partnerWarehouseCode`.
- **[INTEGRATION FLOWS]** Tạo đơn → dùng 2 mã trên gọi `CreateShipment`.

Khi **phân tích tài liệu đối tác**, cũng phải đọc hiểu và trình bày luồng theo đúng 3 giai đoạn — không được tóm tắt chỉ phần API calls mà bỏ qua AUTH và DATA MAPPING.

---

## 4. Lưu file & xuất tài liệu

> **Output root resolve lúc runtime, KHÔNG hardcode** — xem §5 Config resolution. Mọi path dưới đây tương đối theo `{planning_artifacts}/` (mặc định trỏ `NTAPP-output/Stage_1_Discovery/integration/`).

- File chính: `{planning_artifacts}/<Tên đối tác>/Integration_<Tên đối tác>_YYYYMMDD.md` (đủ 14 mục + Lịch sử thay đổi).
- File QA elicitation (nếu user muốn tách riêng cho buổi họp): `{planning_artifacts}/<Tên đối tác>/elicitation/ListQA_<Tên đối tác>.md` — template [`references/qa-file-template.md`](references/qa-file-template.md).
- HTML prototype (Mục 13, nếu user đồng ý): `{planning_artifacts}/<Tên đối tác>/prototype/screens.html`.

> **Quy ước:** dùng tên đối tác không dấu cho phần tên file. `mode: batch` → **lưu ngay** sau khi sinh xong 14 mục, không đợi confirm. `mode: interactive` → lưu sau khi đi hết các mục.

---

## 5. Config resolution (paths)

Skill này tuân theo cùng **cascade 3-layer** như mọi NTAPP skill — đọc key chuẩn `planning_artifacts`, **KHÔNG hardcode path repo cụ thể** (Portability principle):

- **Layer 1** — `{project-root}/_bmad/bmm/config.yaml`: default `planning_artifacts`, `stage_1_discovery`, `project_knowledge`, `document_output_language`.
- **Layer 2** — `{project-root}/.bmm-config.yaml` section `ntapp-integration-inspection:`: override `planning_artifacts` cho skill này (mặc định `{project-root}/NTAPP-output/Stage_1_Discovery/integration`).
- **Layer 3** — Interactive fallback: nếu cả 2 layer đều miss biến cần, hỏi user nơi lưu.

Biến runtime sau cascade:

| Biến | Nguồn | Dùng cho |
|:---|:---|:---|
| `planning_artifacts` | Layer 1/2/3 | OUTPUT — chứa `<Tên đối tác>/` (doc chính + `elicitation/` + `prototype/`) |
| `stage_1_discovery` | Layer 1 | INPUT optional — đọc PRD/Epics nếu cần bối cảnh |
| `project_knowledge` | Layer 1 | INPUT optional — domain docs nếu brownfield |
| `document_output_language` | Layer 1 | Ngôn ngữ output (default Vietnamese) |

---

## 6. Quy tắc Do / Don't

| # | Do ✅ | Don't ❌ |
|---|-------|---------|
| 1 | Hỏi tên đối tác + `direction` + `mode` ngay đầu; lưu vào `{planning_artifacts}/<Tên đối tác>/` (resolve runtime, xem §5) | Hardcode path repo cụ thể, hoặc lưu sai root (KHÔNG ghi vào `docs-BA/` hay nơi khác) |
| 2 | Nhận diện loại tích hợp từ tài liệu → **confirm 1 lần** trước khi phân tích | Giả định luôn là REST API khi chưa xác nhận |
| 3 | `batch`: sinh đủ 14 mục 1 lần, đánh dấu **[Giả định]** rõ ràng | Chỉ trả sequence mà thiếu các mục khác |
| 4 | Điều chỉnh Source, tên section đặc tả, participant, câu hỏi theo `direction` + loại tích hợp | Dùng ngôn ngữ REST API cho tích hợp File/Queue; bỏ qua góc nhìn `direction` |
| 5 | Mọi pseudo flow & sequence PHẢI đủ 3 giai đoạn **[AUTH] → [DATA MAPPING] → [INTEGRATION FLOWS]** | Bắt đầu thẳng vào luồng nghiệp vụ, bỏ qua xác thực & mapping tiền đề |
| 6 | Mục 4 (thay đổi thực thể) đủ 3 phần A/B/C; Mục 9 (ERD) phản ánh đúng Mục 4 | Bỏ Mục 4 hoặc thiết kế ERD hardcode 1 đối tác, không có bảng mapping/config đa đối tác |
| 7 | Sequence có `autonumber` + `Note over` phân nhóm 3 giai đoạn + KHÔNG có Database object + có bảng mapping API↔Sequence (Mục 7) | Đưa Database vào sequence; đặc tả API mà không có bảng mapping Mục 7 |
| 8 | Mục 8: đặc tả theo thứ tự bảng Mục 7; REST API dùng template đầy đủ (request/response/status/rate-limit/security) + ví dụ JSON | Đặc tả thiếu ví dụ JSON hoặc không map với dữ liệu đối tác cần (Mục 2) |
| 9 | Đủ 14 mục gồm NFR, Rủi ro, Checklist go-live, Lịch sử thay đổi | Bỏ bất kỳ mục bắt buộc nào (4, 9, 14) |
| 10 | Mục 12: gom câu hỏi chưa rõ, phân nhóm A/B/C + ưu tiên Cao/TB/Thấp | Bỏ qua bước elicitation sau khi hoàn thành tài liệu |
| 11 | `interactive`: confirm **1 lần** ở cuối mỗi mục | Confirm nhiều lần trong cùng một mục |
| 12 | Sau Mục 14: chủ động hỏi HTML Prototype (Mục 13); field bám bảng Mục 2 + Mục 4-C | Sinh prototype tự do không bám bảng mapping |
| 13 | Toàn bộ output tiếng Việt (trừ tên kỹ thuật: field, endpoint, HTTP method) | Viết output bằng tiếng Anh |

---

## 7. Reference files

| File | Nội dung |
|---|---|
| [`references/integration-types.md`](references/integration-types.md) | Bảng nhận diện loại; điều chỉnh section/đặc tả/participant/câu hỏi theo loại |
| [`references/sequence-diagram-examples.md`](references/sequence-diagram-examples.md) | Sequence Mermaid mẫu đủ 4 loại (REST/File/MQ/SOAP) |
| [`references/erd-and-mapping.md`](references/erd-and-mapping.md) | Bảng mapping dữ liệu (D'/E), quy tắc Source theo loại, ERD đa đối tác mẫu, danh sách thay đổi thực thể |
| [`references/api-spec-template.md`](references/api-spec-template.md) | Template đặc tả API chi tiết (request/response/status/rate-limit/security) + ví dụ |
| [`references/elicitation-questions.md`](references/elicitation-questions.md) | Bộ câu hỏi nhóm A (Biz) / B (Đối tác, theo loại) / C (3-way) + cách sinh ưu tiên |
| [`references/output-template.md`](references/output-template.md) | Template file output đầy đủ 14 mục |
| [`references/qa-file-template.md`](references/qa-file-template.md) | Template file QA elicitation (checkbox cho buổi họp đối tác) |
