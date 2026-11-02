# PROMPT: Sinh `project_wbs.md` chuẩn High-Fidelity (BMAD-METHOD)

## Mục tiêu
Sử dụng prompt này để ép hệ thống AI/LLM phải sinh file `project_wbs.md` đạt chuẩn kiến trúc cấp cao (High-Fidelity). File gồm **2 thành phần bắt buộc theo thứ tự**:

1. **Function Decomposition Tree** (cây ASCII) — bản đồ tổng quan dạng tree, giúp người đọc nắm cấu trúc phân hệ trong 1 lần liếc mắt.
2. **Coverage Matrix (WBS Table)** — bảng 4 cột chi tiết với data flow lineage.

Đây là SSoT (Single Source of Truth) cho phạm vi chức năng; Step 07 sẽ inject **cả 2 thành phần** verbatim xuống `architecture_design.md` §3.2.0.

---

## 0. Phân loại Module (Module Type Classification — BẮT BUỘC)

Mỗi cluster trong WBS PHẢI được phân loại 1 trong **4 module type** dưới đây. Đây là input quyết định downstream:
- Stage 3a TechSpec scope (BE liệt kê features, FE liệt kê screens + widgets, INT liệt kê contracts).
- Stage 4b UI generation (chỉ chạy cho `frontend-app`).
- Pre-commit hook V6 lookup `<id>` theo unit list tương ứng (`features` / `screens` / `widgets`).

### Decision Matrix

| Module type | Khi nào dùng | Đơn vị work | ID prefix convention |
|---|---|---|---|
| `backend-service` | Code chạy server-side, không có UI người dùng. Bao gồm: API endpoint, consumer/worker, job scheduler, internal logic service. | `features` | `BE-{MOD}-NN` (vd `BE-MPF-01`) hoặc legacy `{MOD}-NN` |
| `frontend-app` | Code chạy trong browser / mobile shell — có UI người dùng tương tác trực tiếp. | `screens` + `widgets` (optional) | `SCR-{NAME}` cho screen (vd `SCR-LOGIN`); `WGT-{NAME}` cho widget cross-screen (vd `WGT-AVATAR`) |
| `integration-contract` | API/event contract đặc tả giao thức giữa 2 module — KHÔNG có implementation runtime. Sống để khoá schema cross-team. | `contracts` | `INT-{SRC}-NN` (vd `INT-PMT-01`) |
| `infrastructure` | Observability (logging/metrics/tracing), ops tooling, platform service không phục vụ business user trực tiếp. | `features` | `{MOD}-NN` (vd `OBS-01`) |

### Quyết định khi mơ hồ

| Tình huống | Pick |
|---|---|
| Service có cả API endpoint VÀ admin UI nội bộ → tách 2 cluster? | **Tách** thành 2 module: 1 `backend-service` (API) + 1 `frontend-app` (admin UI). Lý do: scope khác, owner thường khác, Stage 3 spec khác. |
| API gateway / BFF (Backend-for-Frontend) | `backend-service` — vẫn là server-side code. |
| Event contract Kafka topic share giữa 3 microservice | `integration-contract` — declare provider + consumers. |
| Reusable UI component library (npm package nội bộ) | `frontend-app` — declare widgets không có screens. |
| CI/CD pipeline / Terraform infra | `infrastructure`. |
| Provider (BE / BFF / gateway) bị **nhiều consumer ĐỘC LẬP** tiêu thụ, các consumer đến ở **slice khác nhau** | **KHÔNG** mô hình hoá thành 1 atom "build một lần" (anti-mega-hub). Hai lựa chọn: (a) **tách per-capability** thành nhiều atom nhỏ — mỗi khả năng/endpoint-nhóm 1 unit, hoặc (b) đánh dấu `<br>- growable: yes` (unit cố ý lớn dần qua nhiều slice — xem mục Relations). Lý do: một mega-hub gánh nhiều khả năng cho consumer đến ở thời điểm khác nhau → slice sau không có atom nào build endpoint mới → seam vô hình. **Ví dụ:** 1 BFF phục vụ 6 màn trải 6 slice mà chỉ build ở slice đầu → 5 slice sau thiếu endpoint. Ưu tiên (a); dùng (b) khi bản chất unit đúng là 1 hub hợp lệ. |

### Relations bắt buộc khai báo trong WBS

Để Stage 4c story bridge link đúng FE↔BE và pre-commit hook trace ripple:

| Đơn vị work | Field relation | Format |
|---|---|---|
| `screen` | `consumes` | Danh sách `feature_id` mà screen này gọi (vd: `consumes: BE-AUTH-01, BE-AUTH-02`) |
| `widget` | `used_by` | Danh sách `screen_id` consume widget này — chỉ ghi nếu widget cross-screen (vd: `used_by: SCR-LOGIN, SCR-DASHBOARD`) |
| `contract` | `provider` + `consumers` | `provider: <module_id>` + `consumers: <module_id1>, <module_id2>` |
| `feature` (BE, leaf) | (không có field bắt buộc) | Optional ghi `entity` chính nếu có. Leaf BE **KHÔNG** khai `consumes`. |
| **bất kỳ unit** | `role` (optional, rẻ — 1 dòng/row) | `<br>- role: <role>` chỉ khai khi unit là pass-through/aggregation **dùng chung**: `proxy` / `gateway` / `aggregation` / `bff`. Bỏ trống nếu là leaf BE / screen / widget / contract (role suy tự động từ prefix). |
| **unit có `role ∈ {proxy, gateway, aggregation, bff}`** | `consumes` (downstream) | `<br>- consumes: <service-or-contract ids>` — liệt kê các service/contract mà nó forward xuống. Đây là **trường hợp DUY NHẤT** một unit BE được khai `consumes` (đóng gap "cạnh tier-giữa khuyết"). Leaf BE vẫn không khai gì. |
| **unit hub hợp lệ** | `growable` (optional) | `<br>- growable: yes` đánh dấu unit **cố ý lớn dần qua nhiều slice** (hub hợp lệ), để tooling downstream phân biệt hub hợp lệ với mega-hub lỗi (xem "Quyết định khi mơ hồ"). |
| **Cluster Header row** | `repo` (điều kiện — BẮT BUỘC cho mọi cluster `frontend-app` khi project có **≥2 FE code repo**; optional cho cluster khác khi multi-repo) | `<br>- repo: <code-repo-folder>` ghi ở **Cluster Header row**, KHÔNG ghi per-unit — mọi unit kế thừa repo theo module của nó. Giá trị = tên folder code repo trong workspace (khớp field `code_repo` trong `design-system/registry.yaml` nếu registry đã tồn tại). Đây là mắt xích binding `unit → repo → design system` để skill Stage 3b/4a/4b resolve đúng DS khi project có nhiều FE repo (tín hiệu #1 — `_shared/ds-resolution.md` B.4.1; hooks KHÔNG đọc thẻ này — tự resolve qua path/glob nhánh D). Project 1 code repo → bỏ trống toàn bộ. |

Notation: ghi tất cả relations/attributes **trong cột 3 (Mô tả)** của Coverage Matrix dưới dạng thẻ `<br>- <key>: <value>` — đúng các key `consumes` / `used_by` / `provider` / `consumers` / `role` / `growable` / `repo`. Giá trị dạng danh sách (`consumes`, `used_by`, `consumers`) phân tách bằng dấu phẩy; `provider` / `role` / `growable` / `repo` là 1 giá trị (`repo` CHỈ hợp lệ ở Cluster Header row). Format thống nhất để Agent E audit và tooling parse được (không tự chế cú pháp khác).

### Threshold tách cluster

Cluster vượt threshold → BẮT BUỘC tách thành sub-cluster ở level-1 (không nested). ID đơn vị work giữ nguyên — chỉ restructure cluster header.

| module_type | Threshold | Đếm theo |
|---|---|---|
| `backend-service` | 15 features | features |
| `frontend-app` | 20 screens HOẶC 15 widgets | đếm tách |
| `integration-contract` | 20 contracts | contracts |
| `infrastructure` | 10 features | features |

**Naming sub-cluster:** `[{PARENT}-{SUFFIX}]` hyphen, suffix UPPERCASE.

**Tiêu chí tách (chọn 1, KHÔNG stack):**
- Sub-domain — use case / stakeholder khác nhau.
- Nhóm entity — set entity tách được.
- Lifecycle — giai đoạn không overlap thời điểm thực thi.

**KHÔNG tách theo:** layer technical, chia random theo count.

**Không quyết được** → DỪNG, escalate Agent E hỏi user.

---

## Mẫu Prompt đưa vào LLM

```markdown
Hãy đóng vai trò là một Technical Architect Master. Nhiệm vụ của bạn là sinh ra file `project_wbs.md` đạt chuẩn kiến trúc cấp cao (High-Fidelity).

File PHẢI có cấu trúc 2 phần theo thứ tự dưới đây, không được bỏ phần nào:

═══════════════════════════════════════════════════════════
## PHẦN 1 — Function Decomposition Tree (BẮT BUỘC, ASCII)
═══════════════════════════════════════════════════════════

### Quy tắc trình bày
- Định dạng: **ASCII tree** (dùng các ký tự `├──`, `│`, `└──`). Đây là exception cho Principle 4 ("không dùng ASCII art") của Final Template — chỉ áp cho WBS tree, không áp cho các diagram kiến trúc khác.
- Root node = tên hệ thống/dự án (UPPERCASE + viết tắt trong ngoặc).
- Level 1 = các Module/Cluster, định danh `[PREFIX] Tên Module (module_type)` — module_type là 1 trong 4 giá trị đã định nghĩa ở mục 0.
- Level 2 = từng đơn vị work + tên ngắn gọn:
  - `backend-service` / `infrastructure`: liệt kê features (`{MOD}-NN` hoặc `BE-{MOD}-NN`).
  - `frontend-app`: liệt kê screens (`SCR-{NAME}`) trước, sau đó widgets (`WGT-{NAME}`) — group dưới sub-node `Screens:` và `Widgets:` nếu có cả hai.
  - `integration-contract`: liệt kê contracts (`INT-{SRC}-NN`).
- Tree phải bọc trong fenced code block ` ```text ... ``` `.
- Mọi ID xuất hiện trong tree PHẢI xuất hiện ở bảng Coverage Matrix bên dưới và ngược lại (data integrity).

### Mẫu Tham Khảo
```text
<TÊN HỆ THỐNG VIẾT HOA> (<PREFIX>)
├── [MOD1] Tên Module BE (backend-service)
│   ├── BE-MOD1-01  Mô tả ngắn (ENTITY_CHÍNH)
│   ├── BE-MOD1-02  Mô tả ngắn (ENTITY_CHÍNH)
│   └── BE-MOD1-03  Mô tả ngắn
│
├── [SHELL] Tên Module FE (frontend-app)
│   ├── Screens:
│   │   ├── SCR-LOGIN     Màn hình đăng nhập
│   │   └── SCR-DASHBOARD Trang chính
│   └── Widgets:
│       ├── WGT-AVATAR    Avatar user (cross-screen)
│       └── WGT-SIDEBAR   Sidebar navigation
│
├── [INT-MOD1] MOD1 Integration Contract (integration-contract)
│   ├── INT-MOD1-01  Event: <Domain>Created
│   └── INT-MOD1-02  REST contract: /<resource>
│
└── [OBS] Observability (infrastructure)
    ├── OBS-01  Centralized logging
    └── OBS-02  Distributed tracing
```

═══════════════════════════════════════════════════════════
## PHẦN 2 — Coverage Matrix (Bảng 4 cột chi tiết)
═══════════════════════════════════════════════════════════

### 1. Cấu trúc Cột bắt buộc
Bảng phải có đủ 4 cột như sau:
`| WBS ID | Tên Feature | Mô tả ngắn gọn (BA) & Data Flow | Epic / Story |`

> **Lưu ý:** Cột 1 ("WBS ID") chứa ID của đơn vị work (feature_id / screen_id / widget_id / contract_id tuỳ module type). Pre-commit hook V6 lookup chính cột này.
>
> **WBS ID là global-unique toàn project:** mỗi ID xuất hiện đúng 1 row — KHÔNG trùng giữa các module/cluster, kể cả khi project có nhiều code repo. Hai FE app có chức năng tương tự (vd cùng có màn login) PHẢI phân biệt bằng segment app trong tên: `SCR-ADM-LOGIN` (admin portal) vs `SCR-APP-LOGIN` (end-user app). Lý do: toàn bộ tooling downstream (ui_schema, feature_deltas, hooks, DD lookup) key theo ID phẳng — ID trùng = artifact ghi đè nhau.

### 2. Nguyên tắc trình bày Dòng Tiêu Đề Cụm (Cluster Header)
- Các đơn vị work phải được gom nhóm theo Module/Cluster.
- Mỗi Cluster Header PHẢI bôi đậm `**[PREFIX] Tên Module**` kèm hậu tố italic ` _(module_type)_` (vd `**[MPF] Merchant Profile** _(backend-service)_`).
- Ở cột thứ 3, PHẢI có một câu mô tả ngắn gọn (chuẩn BA) về giá trị cốt lõi của toàn bộ cụm này (VD: "Hệ thống tiếp nhận, số hóa và làm sạch dữ liệu từ đa định dạng file...").
*(Format: `| **[Mã] Tên Cụm** _(module_type)_ | | [Câu mô tả] | |`)*
- **Multi-repo (project có ≥2 FE code repo):** Cluster Header `frontend-app` PHẢI khai thêm thẻ `repo` trong cột 3 (xem mục 0 — Relations): `| **[ADM] Admin Portal** _(frontend-app)_ | | Module FE quản trị merchant.<br>- repo: acme-admin-fe | |`. Project 1 code repo → bỏ qua thẻ này.

### 3. Nguyên tắc đặt tên đơn vị work (Cột 2)
- Phải có tiền tố phân tầng (Layering Tag): `[L{number}-{LayerName}]` (VD: `[L1-Entry]`, `[L2-Parser]`, `[L3-State]`).
- Tên theo chuẩn English-First, có thể nối thêm tiếng Việt giải thích nếu cần.
*(VD: `[L1-Entry] File Upload qua Drag & Drop` hoặc `[L3-AuthZ] Permission Check — Operator/Reviewer/Admin`)*
- **Riêng `frontend-app`:** widget cross-screen ghi prefix `[Shared]` thay vì `[L{n}-*]` (vd `[Shared] Avatar Widget`).

### 4. BẮT BUỘC: Kiến trúc luồng dữ liệu + Relations (Cột 3)
Cột mô tả KHÔNG được viết văn xuôi lê thê. Bắt buộc ép vào 3 dòng thẻ `<br>` với cấu trúc:
- **Dòng 1:** `[L{number} - Tên tầng tiếng Việt] [Mô tả mục đích kinh doanh của bước này].`
- **Dòng 2:** `<br>- Input: [Entity/Data] từ [Nguồn/Actor / (Mã-ID-trước-đó)]`
- **Dòng 3:** `<br>- Output: [Data đẩy ra] + [Trạng thái tương ứng]`

**Bổ sung relations (theo loại đơn vị work):**
- `screen` row → thêm `<br>- consumes: <feature_id1>, <feature_id2>` (BE feature mà screen call API).
- `widget` row (cross-screen) → thêm `<br>- used_by: <screen_id1>, <screen_id2>`.
- `contract` row → thêm `<br>- provider: <module_id>` + `<br>- consumers: <module_id1>, <module_id2>`.
- `feature` (BE leaf) → không bắt buộc relations field; ghi `entity` chính nếu có. Leaf BE **KHÔNG** khai `consumes`.
- **`role` (optional, mọi unit):** unit là pass-through/aggregation dùng chung → thêm `<br>- role: <role>` với role ∈ `proxy` / `gateway` / `aggregation` / `bff`. Leaf BE / screen / widget / contract bỏ trống (role suy từ prefix).
- **downstream cho proxy:** unit có `role ∈ {proxy, gateway, aggregation, bff}` → BẮT BUỘC thêm `<br>- consumes: <service-or-contract ids>` (các service/contract nó forward xuống). Đây là trường hợp DUY NHẤT unit BE khai `consumes`.
- **`growable` (optional):** unit là hub hợp lệ cố ý lớn dần qua nhiều slice → thêm `<br>- growable: yes` (phân biệt với mega-hub lỗi).

*Rule tối thượng:* Mọi Output của bước trước (VD: `NormalizedDocument` của `BE-ING-06`) phải được chỉ đích danh là Input của bước sau (VD: `- Input: NormalizedDocument (BE-ING-06)`).

### 5. Cột Epic (Cột 4)
- Epic: Xác định rõ nguồn Epic/Story (VD: `E2 (Story 2.4)`).

---

### Mẫu Tham Khảo (Bạn PHẢI bắt chước 100% cấu trúc này)

| WBS ID | Tên Feature | Mô tả ngắn gọn (BA) | Epic / Story |
| :--- | :--- | :--- | :--- |
| **[ING] Document Ingestion** _(backend-service)_ | | Hệ thống tiếp nhận, số hóa và làm sạch dữ liệu từ đa định dạng file (PDF, Word, Excel). | |
| BE-ING-01 | [L1-Entry] File Upload qua Drag & Drop | [L1 - Tiếp nhận] User kéo thả document vào upload zone; hệ thống khởi tạo job xử lý<br>- Input: File PDF/Word từ user<br>- Output: Job ID + trạng thái "Đang xử lý" | E2 (Story 2.4) |
| BE-ING-02 | [L2-Parser] OCR Pipeline — PDF Scan | [L2 - Số hóa] Nhận diện và số hóa nội dung từ file PDF scan không có text layer<br>- Input: File PDF scan (BE-ING-01)<br>- Output: AnalyzeResult (văn bản + bảng) | E2 (Story 2.4) |
| **[SHELL] Document Workspace UI** _(frontend-app)_ | | Module FE shell cho user upload + theo dõi document. | |
| SCR-UPLOAD | [L1-Entry] Upload Screen | [L1 - Giao diện] Màn hình upload với drag-drop zone + progress bar<br>- Input: User action drag/drop file<br>- Output: Job ID hiển thị + trạng thái realtime<br>- consumes: BE-ING-01, BE-ING-02 | E2 (Story 2.4) |
| WGT-PROGRESS | [Shared] Upload Progress Widget | [Shared] Widget hiển thị progress upload, sử dụng FSM (IDLE/UPLOADING/SUCCESS/ERROR)<br>- Input: Job ID từ SCR-UPLOAD<br>- Output: UI progress visual<br>- used_by: SCR-UPLOAD, SCR-BULK-IMPORT | E2 (Story 2.5) |
| **[INT-ING] ING Integration Contract** _(integration-contract)_ | | API contract ING expose cho consumer downstream. | |
| INT-ING-01 | [Event] DocumentNormalized | [Contract] Kafka event publish khi document đã normalize xong<br>- Input: NormalizedDocument (BE-ING-06)<br>- Output: Kafka topic `ing.document.normalized`<br>- provider: ING<br>- consumers: BIL, RPT | E2 (Story 2.6) |
| **[GW] API Gateway / BFF** _(backend-service)_ | | Lớp BFF tổng hợp: nhận request từ FE, forward xuống service nội bộ; phục vụ nhiều màn trải nhiều slice. | |
| BE-GW-01 | [L1-Proxy] Document BFF Aggregator | [L1 - Cổng vào] Nhận request từ các màn FE, tổng hợp rồi forward xuống service downstream<br>- Input: HTTP request từ SCR-UPLOAD<br>- Output: Response tổng hợp cho FE<br>- role: bff<br>- consumes: BE-ING-01, INT-ING-01<br>- growable: yes | E2 (Story 2.7) |

═══════════════════════════════════════════════════════════
## CẤU TRÚC FILE `project_wbs.md` MONG ĐỢI
═══════════════════════════════════════════════════════════

# PROJECT WBS — <Tên Dự Án>
<Mô tả 1-2 dòng>

---

## Function Decomposition Tree

```text
<ASCII tree theo PHẦN 1>
```

---

## Coverage Matrix (WBS) — High-Fidelity

<Bảng 4 cột theo PHẦN 2>
```
