---
outputDir: '.vsaf/docs/features/{feature-name}'
featureTemplate: './srs-feature-template.md'
# System-level SRS (1 lần/hệ thống, cross-module) — dùng khi user yêu cầu "system SRS" hoặc scope=system.
systemTemplate: './srs-system-template.md'
systemOutput: '.vsaf/docs/{system-srs-file}.md'
# domain/glossary best-effort — dùng chung nguồn với cặp skill sdlc-validate-srs (nếu cài cùng).
domainChecklistGlob: '../sdlc-validate-srs/data/domain-checklists/{domain}.yaml'
selfCheckDimensions: 8   # Bước 5 tự kiểm rút gọn theo 8 dimension của sdlc-validate-srs
# Project memory: quét SRS các feature đã có để tái dùng thuật ngữ/entity/API/event (best-effort).
projectMemoryGlob: '.vsaf/docs/features/*/05-srs.md'
examplesFile: './examples/srs-good-bad.md'   # few-shot Good/Bad — chỉ nạp ở mode standard|full
mode: standard   # draft | standard | full — xem "## MODE" bên dưới. Đổi ở CONTEXT.md/.vsaf/config.yaml field `mode`.
---

# BA Write SRS Workflow

**Goal:** Phân tích yêu cầu và viết tài liệu SRS (Software Requirements Specification) feature-level theo template chuẩn Confluence — đúng **12 sections (0–11)** của template v6 (domain-neutral, multi-archetype, có Decision Log / Impact Matrix / Observability / Open Questions / AI Metadata), chuẩn diagram **PlantUML** (khớp template), có truy vết và self-check trước bàn giao.

**Your Role:** Business Analyst chuyên nghiệp — viết SRS theo quy trình chuẩn, đảm bảo truy xuất được từ PRD/BRD → Use Cases → Màn hình → Epic/Story.

> **Cặp skill:** `sdlc-write-srs` (generator) ↔ `sdlc-validate-srs` (quality gate). Skill này viết SRS đúng 12 section mà validate chấm điểm, dùng chung `domain-checklists/` để "viết đúng ngay từ đầu".

> **Hai cấp SRS:**
> - **Feature-level** *(mặc định)* — 1 flow/feature → `srs-feature-template.md` (12 sections 0–11) → lưu `05-srs.md`. Toàn bộ workflow dưới đây áp cho cấp này.
> - **System-level** *(khi user yêu cầu "system SRS" / scope=system)* — 1 lần/hệ thống, cross-module → `srs-system-template.md` (System v2) → lưu `{systemOutput}`. Cùng nguyên tắc (guardrails chống bịa, PlantUML-only, domain-aware, mode, self-check) nhưng theo cấu trúc system template (System Profile §0, Module Map, Integration Architecture, RTM cấp module). Feature SRS sau đó tham chiếu ngược System SRS ở §1.4 References; block `ai_metadata` §I của System SRS seed cho Reuse Index (Bước 1.7).

## ⛔ NGUYÊN TẮC CHỐNG BỊA (AI Guardrails — áp dụng xuyên suốt mọi bước)

Bạn là BA ghi lại yêu cầu, **KHÔNG phải người thiết kế nghiệp vụ mới**. TUYỆT ĐỐI không tự phát minh:

- **KHÔNG** thêm business rule / validation rule không truy được về PRD/BRD/ADR/domain-checklist.
- **KHÔNG** thêm trạng thái (state) hay chuyển trạng thái không có trong PRD/ADR/`knowledge_model`.
- **KHÔNG** thêm API endpoint / Kafka event / entity / field không có nguồn.
- **KHÔNG** "đoán" con số NFR (timeout, TPS, SLA…) — nếu PRD/ADR không nêu thì để `{{Cần bổ sung}}`.

Thiếu thông tin → **luôn** ghi `{{Cần bổ sung: <mô tả cần gì, hỏi ai>}}` và đưa vào Gap Analysis (Appendix 11). Mọi mục trong SRS phải **truy vết được về một nguồn**; mục không truy được nguồn = phải đánh dấu, không được viết như thể là sự thật. (Điều này giúp vượt "invention detection" của `sdlc-validate-srs`.)

## MODE — tiết kiệm token theo quy mô thay đổi

Đọc `mode` từ `CONTEXT.md`/`.vsaf/config.yaml` (mặc định `standard`). Mode **chỉ đổi độ sâu/độ giàu**, KHÔNG đổi 12-section structure, guardrails hay chuẩn PlantUML.

| Mode | Dùng khi | Bước 1.5 pre-write | Few-shot examples | Ma trận optional (CRUD/Risk) | Security/Privacy checklist |
|------|----------|--------------------|--------------------|------------------------------|----------------------------|
| `draft` | Thay đổi nhỏ, dựng khung nhanh | Rút gọn — chỉ FLAG 1.5a; bỏ 1.5b/1.5c | **Bỏ qua** (tiết kiệm token) | Bỏ | Chỉ nếu bắt buộc |
| `standard` *(default)* | Feature bình thường | Đủ 1.5a/1.5b/1.5c | **Nạp** `examplesFile` | Khi feature cần | Có điều kiện |
| `full` | Feature lớn / nhạy cảm / audit | Đủ + đối chiếu project memory kỹ | **Nạp** + bám sát mẫu | Luôn có | Luôn rà (nếu liên quan) |

> `draft` vẫn giữ nguyên: input-gate, guardrails chống bịa, 12 section, PlantUML, `{{Cần bổ sung}}`. Nó chỉ **bỏ phần phân tích/ví dụ tốn token**, không hạ chuẩn tính đúng.

## WORKFLOW

### Bước 0 — Kiểm tra đầu vào

**0.0 — Xác định cấp SRS:** mặc định **feature-level**. Nếu user yêu cầu "system SRS" / "SRS hệ thống" hoặc `scope=system` → chuyển sang **system-level**: dùng `{systemTemplate}`, lưu `{systemOutput}`, theo cấu trúc system template (System Profile §0 → §1 Giới thiệu → §2 Tổng quan (Module Map/Integration) → §3 FR theo module → §4 NFR → §5 Constraints → §6 RTM → §7 Phụ lục A–I). Các bước 1/1.5/2/3/4/5 dưới đây vẫn áp dụng về **nguyên tắc** (guardrails, PlantUML, mode, self-check) nhưng map vào section của system template. Phần còn lại của mô tả dưới đây theo feature-level.

Tự động đọc input artifacts từ VSAF pipeline:

**Input bắt buộc:**
- [ ] `.vsaf/docs/features/{feature-name}/02-prd.md` — PRD từ Phase 2
- [ ] `.vsaf/docs/features/{feature-name}/03-adr.md` — Architecture từ Phase 3

**Input tùy chọn:**
- [ ] `.vsaf/docs/features/{feature-name}/04-epics.md` — Epic breakdown
- [ ] Figma link — lấy từ `CONTEXT.md` field `figma_url` nếu có
- [ ] BRD file — nếu project có BRD trong `.vsaf/docs/`
- [ ] `domain` — field trong `CONTEXT.md`/`.vsaf/config.yaml` (vd `lending`, `insurance`). Nếu có → nạp domain profile ở Bước 1.
- [ ] GLOSSARY / ubiquitous language — nếu project có (vd `GLOSSARY.md`, `00_PLATFORM/GLOSSARY.md`) → nạp để đặt tên nhất quán.
- [ ] `mode` — `draft` | `standard` | `full` (mặc định `standard`). Xác định độ sâu Bước 1.5, việc nạp few-shot và ma trận optional. Xem "## MODE".

Nếu thiếu 02-prd.md hoặc 03-adr.md, **dừng lại ngay**:

```
Thiếu input artifacts cho Phase 4 SRS:

❌ [liệt kê file thiếu]

Vui lòng chạy Phase 2 (PRD) và Phase 3 (Architecture) trước.
```

Chỉ tiếp tục khi đã có đủ PRD + ADR.

**Xác định Applicability Profile (§0 template v5) — làm ngay để biết section nào áp dụng:**
Từ PRD/ADR, suy ra và xác nhận với user:
- **Loại feature**: `UI` / `Backend-Process` / `Integration-only` / `Batch`.
- **Có UI?** Không → §5.2 dùng "Interface Contract" (mẫu 5.2-B) thay bảng control; §11.1–11.2 Figma = "N/A — không UI"; Bước 2 (Figma) bỏ qua.
- **Có state machine?** Không → §6 = "N/A".
- **Có tích hợp ngoài?** → chi phối §4.4/§4.5/§2.6.
- **Brownfield / cắt chuyển legacy?** Có → §9.3 Data Migration bắt buộc.
- **Domain** (`lending`/`insurance`/`payment`/…) → nạp domain-checklist ở Bước 1.6, thay placeholder ví dụ.

> Section không áp dụng → ghi **"N/A — {lý do}"** dưới heading, KHÔNG để bảng rỗng. Profile này điền vào bảng §0 của SRS.

---

### Bước 1 — Đọc & phân tích PRD/BRD

Đọc toàn bộ tài liệu PRD từ `02-prd.md` và Architecture từ `03-adr.md`. Nếu có `04-epics.md`, đọc thêm epic breakdown. Trích xuất và tổ chức thông tin theo cấu trúc:

**1.1 Mục tiêu dự án**
- Business objective
- Problem statement
- Success criteria

**1.2 Phạm vi (Scope)**
- In-scope features / Sub-FRs
- Out-of-scope
- Các module/màn hình chính

**1.3 Actors & Use Cases**
- Danh sách các actor (vai trò người dùng)
- User stories / use cases đã đề cập

**1.4 Business Rules**
- Quy tắc nghiệp vụ quan trọng
- Constraints & assumptions

**1.5 Non-functional Requirements**
- Performance, security, scalability, v.v. (nếu có)

**1.6 Nạp domain profile + glossary (best-effort — bỏ qua nếu không có)**
- Nếu `CONTEXT.md`/`.vsaf/config.yaml` có field `domain` → thử đọc `../sdlc-validate-srs/data/domain-checklists/{domain}.yaml` (dùng chung với skill validate; nếu không cài cùng thì bỏ qua, KHÔNG dừng).
  - Trích **`invariants:`** (bất biến nghiệp vụ) và **`knowledge_model:`** (entities/lifecycle/hazard_states/forbidden_transitions) nếu có → dùng làm ràng buộc khi viết Business Rules (section 7), State Diagrams (section 6) và Data Model (section 4). **KHÔNG viết SRS vi phạm invariant.**
- Nếu project có GLOSSARY / ubiquitous language → nạp danh sách thuật ngữ chuẩn để đặt tên entity/UC/trạng thái **nhất quán** với dự án (tránh rớt Consistency ở bước validate).

**1.7 Project memory & reuse index (best-effort — bỏ qua nếu là feature đầu tiên)**
Quét SRS của **các feature đã có** qua `{projectMemoryGlob}` (`.vsaf/docs/features/*/05-srs.md`, trừ feature hiện tại) + đọc `CONTEXT.md`/`KNOWLEDGE.md` nếu có. Để tiết kiệm token, **ưu tiên đọc block `ai_metadata` (§11.8)** của các SRS cũ nếu có (đã là bản tóm tắt máy-đọc: entities/events/commands/queries/aggregates/external_apis) — rẻ và chính xác hơn parse văn xuôi. Nếu SRS cũ không có §11.8 thì mới **trích** thủ công (không chép toàn văn):
- **Entities** (từ §4 Data Model của các SRS cũ) + tên trạng thái (§6).
- **API endpoints / Kafka events** đã đặt (§4).
- **Thuật ngữ / định nghĩa** (§1.3).

Dựng **"Reuse Index"** (bảng: Khái niệm | Tên đã dùng | Feature nguồn) rồi áp dụng:
- **Tái dùng** đúng tên đã có thay vì đặt tên mới cho cùng khái niệm (entity, API, event, term).
- **Cross-feature consistency — FLAG near-synonym**: nếu feature này định đặt một tên **gần nghĩa** với khái niệm đã tồn tại (vd `InsuranceStatus` trong khi feature khác đã có `PolicyStatus`) → **cảnh báo + đề xuất dùng lại tên cũ**, KHÔNG tự đổi. Việc kiểm near-synonym là heuristic → chỉ flag để user quyết.

> Ở `full` mode: đối chiếu kỹ toàn bộ Reuse Index. Ở `draft`/`standard`: đối chiếu tên entity/API/event chính. Feature đầu tiên (không có SRS cũ) → bỏ qua, ghi "Chưa có project memory".

Sau bước này, xuất ra **"Tóm tắt PRD/BRD"** (kèm dòng ghi domain profile + glossary + project memory đã nạp hay chưa) để user xác nhận trước khi sang bước 2.

---

### Bước 1.5 — Chuẩn hoá & phân loại yêu cầu (pre-write analysis)

Trước khi viết SRS, chuẩn hoá tập yêu cầu từ PRD để **không truyền lỗi PRD xuống SRS**. Đây là bước phân tích, output là bảng để user xác nhận — **KHÔNG tự sửa/gộp yêu cầu**.

> **Mode gating:** `draft` → chỉ chạy 1.5a (FLAG lỗi đầu vào), bỏ 1.5b/1.5c để tiết kiệm token. `standard`/`full` → chạy đủ 1.5a/1.5b/1.5c.

**1.5a — Rà chất lượng đầu vào (FLAG, không tự sửa):**
Quét các FR trong PRD và **đánh dấu** (không âm thầm gộp/xoá):
- FR **trùng lặp** (duplicate) → đề xuất hợp nhất, chờ user xác nhận.
- FR **mâu thuẫn** (conflict) nhau hoặc với ADR/invariants → nêu cặp mâu thuẫn.
- **Actor thiếu**: hành động không rõ ai thực hiện.
- **Orphan requirement**: FR không gắn được với UC/actor/mục tiêu nào.
- **Phụ thuộc vòng** (circular) giữa các FR/UC.

> ⚠️ Việc **tự động** hợp nhất/loại bỏ yêu cầu là CẤM (đổi phạm vi ngầm). Chỉ FLAG + đề xuất; quyết định thuộc về user. Chồng lấn với `sdlc-validate-srs` là có chủ đích — ở đây là chặn sớm, không phải chấm điểm.

**1.5b — Phân loại & định tuyến từng yêu cầu về section đích:**
Gán mỗi item PRD vào đúng 1 loại → 1 section của template (chống đặt sai chỗ / bỏ sót):

| Loại | Section đích |
|------|-------------|
| Functional (hành vi hệ thống) | §5 Functional Requirements (UC) |
| Business Rule | §7 Business Rules & Validation |
| Validation | §7 |
| Constraint / Assumption / Dependency | §9 Constraints |
| NFR (performance/reliability/security/…) | §8 NFR |
| UX / persona / journey | §5 (UC) + §11 Appendix (Figma) |
| Integration (API/event/service ngoài) | §4 Data Model |
| Security / Privacy | §8 NFR (+ checklist Bước 3) |

**1.5c — Trích Business Objects & đối chiếu knowledge_model:**
Liệt kê nhanh các entity nghiệp vụ (tên, vòng đời sơ bộ, owner) rồi **đối chiếu với `knowledge_model`** đã nạp (Bước 1.6) nếu có: entity/lifecycle/forbidden_transition nào lệch → FLAG. Bảng này là nháp cho §4/§6, không thay §4/§6.

Xuất **"Requirement Analysis"** (3 bảng 1.5a/1.5b/1.5c) để user xác nhận/clarify trước khi sang Bước 2. Các mục chưa rõ → chuyển thành `{{Cần bổ sung}}`.

---

### Bước 2 — So sánh PRD/BRD với Figma (nếu có Figma)

Nếu có Figma link, dùng Figma MCP tools để đọc design:
1. Gọi `get_figma_data` để lấy danh sách pages/frames
2. Download screenshots cho từng màn hình chính

So sánh và ghi nhận:

| Hạng mục | PRD/BRD nói | Figma thiết kế | Trạng thái |
|---|---|---|---|
| [Feature/Screen] | ... | ... | ✅ Khớp / ⚠️ Khác biệt / ❓ Chưa rõ |

**Phân tích gap:**
- **Gap 1 — Thiếu trong Figma:** Features có trong PRD nhưng không thấy trong design
- **Gap 2 — Thêm trong Figma:** UI elements trong Figma nhưng không đề cập trong PRD
- **Gap 3 — Mâu thuẫn:** Thông tin không nhất quán giữa hai nguồn

**Fallback khi không dùng được Figma MCP:**
- Không có `figma_url` → ghi rõ "Chưa có Figma design — cần UX team cung cấp" tại Appendix 11.1 của SRS.
- Có `figma_url` nhưng **Figma MCP không khả dụng** (không cài / offline) → KHÔNG bỏ qua đối chiếu: hỏi user cung cấp screenshot/PDF export, hoặc đánh dấu từng màn hình là `❓ Chưa đối chiếu (thiếu MCP)` trong bảng gap và liệt kê ở Gap Analysis để không âm thầm mất bước so khớp.

Sau bước này, xuất ra **"Báo cáo Gap Analysis"** và hỏi user có muốn clarify gap nào trước khi viết SRS không.

---

### Bước 3 — Viết tài liệu SRS theo Feature Template

Đọc template tại `./srs-feature-template.md` và viết SRS **đúng theo cấu trúc template v6 — 12 sections (0–11)**. KHÔNG đổi thứ tự / tên section. Áp **Applicability Profile** (Bước 0): section không áp dụng → "N/A — {lý do}", section `[std]`/`[full]` → cắt theo `mode`. Feature không UI → §5.2 dùng Interface Contract (mẫu 5.2-B) thay bảng control:

| # | Section | Nội dung chính |
|---|---------|----------------|
| 0 | **Preamble** | Thông tin tài liệu, Change Log (A/M/D), **Decision Log** (quyết định đã chốt + lý do — tách khỏi Change Log; trỏ ADR nếu là quyết định cấp hệ thống), Applicability Profile, bảng phê duyệt |
| 1 | **Introduction** | Purpose, Scope (in/out-of-scope, Sub-FR + phân kỳ), Definitions & Acronyms |
| 2 | **Business Context** | Business goals/metrics, actors, precondition/postcondition tổng, flow liên quan; **Assumptions có Status/Owner/Deadline** (assumption chưa xác nhận quá hạn → rủi ro §9 hoặc Open Question §11.7) |
| 3 | **System Overview** | High-Level Activity Diagram + Architecture (dời lên đầu, không để cuối) |
| 4 | **Data Model** | Entity tables + ER diagram + **Kafka Events** (mỗi event ghi rõ trigger → event → consumer) + **API Endpoints** (API gọi service ngoài ghi thêm Provider / Consumer / Timeout / Retry / Fallback — feed dimension Risk của validate) |
| 5 | **Functional Requirements** | Đặc tả từng UC: Màn hình (bảng controls) + Luồng nghiệp vụ (diagram + bảng mô tả); mỗi UC đủ Precondition / Main / Alternative / Exception / Postcondition |
| 6 | **State & Behavioral Models** | State diagram vòng đời entity |
| 7 | **Business Rules & Validation** | Bảng BR (mã duy nhất) + Validation Rules + **Error Codes** |
| 8 | **NFR** | Yêu cầu phi chức năng đặc thù flow + **Observability** (Log/Metric/Trace/Dashboard/Alert — log KHÔNG chứa PII/secret) |
| 9 | **Constraints** | Ràng buộc, giả định, phụ thuộc, transition requirements |
| 10 | **RTM (Mini-RTM)** | PRD FR → UC → Màn hình → Epic/Story → **BR → AC → Test Case** + cột **Depends-on** (FR-này phụ thuộc FR nào — phục vụ roadmap/release/impact). Đảm bảo không có phụ thuộc vòng (đã FLAG ở Bước 1.5a). |
| 11 | **Appendix** | Figma Mapping + Screen List + **Impact Matrix** (§11.4: business + technical API/DB/Cache/Kafka/Batch/Scheduler/Permission/Notification) + Gap Analysis (thiếu artifact) + **Open Questions** (§11.7: câu hỏi nghiệp vụ chưa chốt — Owner/Due/Status) + **(tuỳ chọn `[full]`)** AI Metadata (§11.8, block `ai_metadata` máy-đọc phái sinh từ §4/§5/§6 — cho agent downstream + Reuse Index), CRUD Matrix, Risk Register |

**Quy tắc viết:**
- Viết bằng **tiếng Việt** trừ khi user yêu cầu tiếng Anh
- Giữ nguyên business rules từ PRD/BRD, không tự ý thay đổi logic nghiệp vụ; **không vi phạm `invariants` domain đã nạp ở Bước 1.6**
- Đặt tên entity/UC/trạng thái theo **glossary** + **Reuse Index** (Bước 1.7) — tái dùng tên đã có ở feature khác, không đặt tên mới cho cùng khái niệm
- **Few-shot (mode `standard`/`full`)**: đọc `{examplesFile}` và bám theo mẫu **Good** cho FR / BR / UC / Data Model, tránh các lỗi ở mẫu **Bad**. Mode `draft` → bỏ qua để tiết kiệm token.
- Mỗi Use Case (section 5) phải có: Precondition, Main flow, Alternative flow, Exception flow, Postcondition
- Màn hình dùng chung: đặt bảng đầy đủ tại UC đầu tiên, UC sau ghi tham chiếu
- **Chuẩn diagram DUY NHẤT = PlantUML** — KHỚP với `srs-feature-template.md` (dùng ```plantuml + `@startuml`): Activity, State/Lifecycle, ER, Sequence đều PlantUML. KHÔNG trộn Mermaid. (Bản gốc "Quy tắc viết" ghi Mermaid là SAI — template thực tế dùng PlantUML; xem REFACTOR-NOTES P0-b.)
- Figma Mapping tables đặt ở Appendix 11.1; trong UC chỉ giữ blockquote tham chiếu
- **Tránh ngôn ngữ mơ hồ**: KHÔNG dùng "nhanh / hợp lý / nếu cần / có thể / càng sớm càng tốt / linh hoạt / tối ưu / thân thiện" mà không kèm tiêu chí đo được. Nếu PRD dùng từ mơ hồ → viết lại thành tiêu chí cụ thể; nếu không suy ra được → `{{Cần bổ sung: định lượng "<từ mơ hồ>"}}`.
- Nếu thông tin chưa đủ → ghi `{{Cần bổ sung}}` và liệt kê ở Gap Analysis (Appendix 11)

**Checklist Security & Privacy (kích hoạt CÓ ĐIỀU KIỆN — chỉ khi feature liên quan):**
- Nếu feature có **auth / phân quyền / xử lý tiền / dữ liệu nhạy cảm** → trong §8 NFR (hoặc §9) nêu rõ: Authentication, Authorization (role/permission per UC), Audit log, Encryption (at-rest/in-transit), Data masking, Rate limit. Với mục nào PRD/ADR chưa nói → `{{Cần bổ sung}}` (KHÔNG tự chế chính sách security).
- Nếu feature xử lý **PII / dữ liệu cá nhân** (áp dụng PDPA/GDPR/PCI) → nêu: Retention (thời gian lưu), Consent, Delete/erasure policy, Audit truy cập, Masking. Không rõ mức tuân thủ → FLAG cho user, không tự quyết.
- Feature **không** liên quan → bỏ qua, không thêm section rỗng.

---

### Bước 4 — Lưu file SRS

Lưu tài liệu SRS vào: `.vsaf/docs/features/{feature-name}/05-srs.md`

Thông báo cho user:
- Đường dẫn file đã lưu
- Số lượng use cases đã viết
- Danh sách gaps quan trọng cần team confirm
- Các phần SRS còn `{{...}}` cần bổ sung thêm

---

### Bước 5 — Self-check trước khi bàn giao

Trước khi coi SRS là "xong", tự rà nhanh theo **8 dimension** của skill `sdlc-validate-srs` (đây là self-check nhẹ, KHÔNG thay thế việc chạy gate đầy đủ):

| # | Dimension | Câu hỏi tự kiểm |
|---|-----------|-----------------|
| 1 | Business Alignment | Có problem statement + metric truy về PRD? Scope/out-of-scope rõ? |
| 2 | Completeness | Đủ 12 section? Mỗi UC đủ Pre/Main/Alt/Exception/Post? Có Error Codes, ERD, BR, NFR, RTM? |
| 3 | Consistency | Tên entity/UC/state nhất quán + khớp glossary? UC ID cùng prefix? State machine không mâu thuẫn? |
| 4 | Quality | Không còn ngôn ngữ mơ hồ; AC testable; không requirement gộp/trùng |
| 5 | System & NFR | NFR đo được (con số); Architecture (section 3) khớp ADR |
| 6 | Delivery Readiness | Có API contract, DB schema, integration spec, rollout/migration nếu cần |
| 7 | Risk Analysis | Exception flow, external dependency, integration gap, assumption đã nêu |
| 8 | User Impact | Persona/journey phủ đủ; error UX; onboarding/accessibility nếu liên quan |
| — | **Invariant** | Nếu có domain profile: SRS **không vi phạm** `invariants` đã nạp (Bước 1.6) |

Xuất **"Self-check summary"**: liệt kê mục ✅ đạt / ⚠️ còn thiếu (kèm section) / `{{Cần bổ sung}}` còn lại.

**Confidence per section (tín hiệu bàn giao — KHÔNG phải điểm số):** gán mỗi section một mức **High / Medium / Low** dựa trên độ đầy đủ của nguồn (PRD/ADR/Figma). Section nào **Low** → nêu rõ lý do + việc cần clarify. Đây chỉ là tín hiệu cho downstream biết chỗ "mềm"; điểm GO/NO-GO chính thức vẫn do `sdlc-validate-srs` quyết. Ở mode `full`, ghi kết quả confidence này vào block `ai_metadata.confidence` (§11.8) để agent downstream đọc được.

> **Bàn giao khép kín:** khuyến nghị user chạy tiếp `validate srs` trên `05-srs.md` để có điểm GO/CONDITIONAL GO/NO-GO chính thức. Self-check này chỉ giúp giảm số vòng NO-GO, không phải quyết định gate.

---

## WORKFLOW — SYSTEM-LEVEL SRS (chỉ khi Bước 0.0 chọn scope=system)

> Áp dụng khi viết **1 SRS cho cả hệ thống** (cross-module), dùng `{systemTemplate}` (System-Level v2), lưu `{systemOutput}`. Giữ nguyên **mọi nguyên tắc** ở trên (guardrails chống bịa, PlantUML-only, domain-aware, mode, glossary/Reuse Index) — chỉ đổi cấu trúc output và đơn vị phân tích (module thay vì UC đơn lẻ). Các bước S dưới đây thay cho Bước 1–5 khi ở cấp system.

### S0 — Đầu vào (system)
- **Bắt buộc:** PRD tổng / tập PRD các module, ADR/Architecture hệ thống. **Tùy chọn:** BRD, danh sách feature SRS đã có (`05-srs.md`), CONTEXT/KNOWLEDGE, domain, mode.
- Thiếu PRD hệ thống hoặc ADR → dừng, yêu cầu bổ sung (như Bước 0).

### S1 — Đọc & tổng hợp cấp hệ thống
- Đọc PRD tổng + ADR. Nếu có **các feature SRS đã viết** → **ưu tiên đọc block `ai_metadata` (§11.8)** của chúng để gom nhanh module/entity/event/external-system (rẻ token, khớp gap #1↔project-memory). Feature SRS thiếu §11.8 mới trích thủ công.
- Nạp domain profile + glossary (như Bước 1.6). Dựng **Reuse Index cấp hệ thống** (entity/API/event/term dùng chung) để các module nhất quán tên.

### S1.5 — Phân rã module & phân tích chéo (pre-write)
- **Module decomposition:** liệt kê module (tên, flows/FR range, priority) → §2.5 Module Map. FLAG module trùng chức năng / ranh giới chồng lấn (KHÔNG tự gộp).
- **Integration surface:** liệt kê hệ thống ngoài + chiều + giao thức + SLA → §2.6.
- **Cross-module dependency & circular check** (như 1.5a nhưng ở cấp module) → feed §5.4 rủi ro + Decision Log nếu phải chốt ranh giới.

### S2 — Context/Module diagram (thay Figma gap)
- System-level thường **không đối chiếu Figma**. Thay vào đó vẽ **System Context §2.2** + **Module Map §2.5** (PlantUML). Nếu hệ thống có UI và có Figma tổng → ghi tham chiếu, không đi sâu control-level (đó là việc feature SRS).

### S3 — Viết System SRS theo `{systemTemplate}`
Theo đúng cấu trúc System-Level v2, **KHÔNG đổi tên/thứ tự section**:

| § | Nội dung | Ghi chú |
|---|----------|---------|
| 0 | System Applicability Profile + Decision Log | Khai báo loại hệ thống/greenfield-brownfield/deployment/domains → section N/A |
| 1 | Giới thiệu | Mục đích, đối tượng đọc, phạm vi hệ thống, định nghĩa, references |
| 2 | Tổng quan hệ thống | Mô tả, **Context diagram**, môi trường, actors, **Module Map**, **Integration Architecture**, Assumptions (Status/Owner/Deadline) |
| 3 | FR theo module | Mỗi module 1 mục 3.X; UC tóm tắt + chi tiết; **trỏ feature SRS** (`srs/…-FlowXX`) nếu có, KHÔNG chép lại toàn văn |
| 4 | NFR | Perf/Sec/Avail/Usability/Scale/**Interoperability §4.6**/Compliance/Audit/**Observability §4.9**/Maintainability/Portability |
| 5 | Constraints | Kỹ thuật, pháp lý, **Transition Requirements** (bắt buộc nếu brownfield), rủi ro |
| 6 | RTM cấp module | PRD FR → UC → Module → Màn hình → Epic/Story |
| 7 | Phụ lục | Screen Inventory (N/A nếu không UI), BR Index, **Open Issues**, Message Catalog, Data Dictionary, CRUD, State (PlantUML), Verification Summary, **§I AI Metadata** `[full]` |

- Guardrails chống bịa + PlantUML-only + tránh weasel-word: **giữ nguyên** như feature-level.
- Mode gating: `draft` bỏ Verification Summary/AI Metadata/CRUD chi tiết; `full` làm đủ.

### S4 — Lưu
- Lưu vào `{systemOutput}` (mặc định `.vsaf/docs/{system-srs-file}.md`). Thông báo: modules đã đặc tả, số feature SRS được tham chiếu, Open Issues/gap còn lại, các `{{Cần bổ sung}}`.

### S5 — Self-check (system)
- Dùng lại 8 dimension của Bước 5 nhưng map vào cấu trúc system: Completeness = đủ Module Map/Integration/RTM cấp module/Data Dictionary; Consistency = tên entity/module/event nhất quán xuyên module + khớp Reuse Index; User Impact **N/A** nếu hệ thống không có UI (ghi rõ lý do, không để trống).
- Confidence per section → ghi `ai_metadata` §I ở mode `full`.
- Khuyến nghị chạy `validate srs` với **chế độ system** (validate-srs tự nhận `srs_level=system`).

---

## Lưu ý quan trọng

- Luôn viết bằng **tiếng Việt** trừ khi user yêu cầu tiếng Anh
- Với mỗi gap phát hiện, đề xuất cách xử lý thay vì bỏ qua
- Nếu Figma có nhiều pages, hỏi user muốn focus vào page/flow nào trước
- Giữ nguyên business rules từ PRD/BRD, không tự ý thay đổi logic nghiệp vụ
- Template phải tuân thủ **đúng format** tại `./srs-feature-template.md` — không được thay đổi cấu trúc section
