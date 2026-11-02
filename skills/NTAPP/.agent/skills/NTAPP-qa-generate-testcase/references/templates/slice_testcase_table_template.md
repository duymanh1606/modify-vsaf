# KỊCH BẢN KIỂM THỬ CHI TIẾT (E2E SYSTEM TEST PROTOCOL) — {id}

> **Chế độ:** Mode 3: GENERATE SLICE / UNIT  
> **Thời gian tạo:** {timestamp}  
> **Mã SLICE/Unit:** {id}  
> **Độ bao phủ cam kết (Coverage Gate):** 100% End-to-End luồng thao tác người dùng qua các units FE và BE.
>
> **Artifact đồng hành (Triple-Emit — xem [automation_contract_rules.md](../../principles/automation_contract_rules.md)):**
> - `{id}_testspec.feature` — bản canonical Gherkin + tags (nguồn automation).
> - `{id}_fixtures.yaml` — dữ liệu mồi + môi trường máy-đọc.
> - File markdown này là **VIEW** để QA ký + để `/ntapp-qa-robot` parse.
>
> **Cột `Exec`** (cổng automation): `automate` (qa-robot sinh code) · `manual` (tester chạy tay) · `exploratory` (hiếm — chỉ visual thẩm mỹ thuần trong KHỐI 1, KHÔNG charter). Rủi ro timing/đồng thời/phiên/[TBD] → viết scripted trong KHỐI 2/3. Quy tắc gán: [risk_based_allocation_rules.md](../../principles/risk_based_allocation_rules.md).

---

## 5. ĐẢM BẢO CHẤT LƯỢNG (QUALITY ASSURANCE & E2E TEST PROTOCOL)

### 5.0. Bối cảnh & Điều kiện tiên quyết (Test Preconditions)
1. **Người dùng đăng nhập:** Được cấp quyền theo đúng luồng E2E.
2. **Trạng thái hệ thống:** Mạng ổn định hoặc được cấu hình mock theo ca kiểm thử.

---

### 5.1.A. Impact Analysis (Phân tích ảnh hưởng luồng SLICE)
Bảng phân tích các đơn vị (Units), FE screens, BE modules bị ảnh hưởng khi triển khai `{id}`:

| Chức năng / phân hệ ảnh hưởng (Units) | Mức độ | Lý do / Nội dung chi tiết |
|:---|:---:|:---|
| **{Tên phân hệ FE: SCR/WGT}** | **H** | {Lý do} |
| **{Tên phân hệ BE: HUB/API}** | **H** | {Lý do} |

*Mức độ: H (High - Cao), M (Medium - Trung bình), L (Low - Thấp)*

---

### 5.2. Kịch bản kiểm thử E2E chi tiết (11-Column Manual Testcase — +Exec)

> **Biến thể theo `surface_type`:**
> - **`ui`** (dưới đây) — 3 khối **GIAO DIỆN / CHỨC NĂNG / PHÂN QUYỀN**; đầu mỗi màn có "Danh sách UI Controls"; cột Công cụ `Chrome`; Kết quả mong muốn phân lớp **UI:/API:/DB:/Log:**.
> - **`service`** (no-UI: HUB/MPF/INT — xem [service_surface_rules.md](../../principles/service_surface_rules.md)) — thay tiêu đề "MÀN HÌNH ACTION" bằng **"OPERATION {STT}: {METHOD /path hoặc tên operation}"**; đổi "Danh sách UI Controls" thành **"Danh sách Endpoint/Operation & Hợp đồng"** (request field · response · error catalog · side-effect); 3 khối = **HỢP ĐỒNG & REQUEST VALIDATION / NGHIỆP VỤ & E2E / PHÂN QUYỀN & ATTT**; cột Công cụ `Postman`/`RequestsLibrary`; Kết quả mong muốn phân lớp **API:/DB:/MSG:/Log:** (KHÔNG có UI:). Giữ nguyên 11 cột, chỉ đổi nội dung.

*(Lặp lại cấu trúc dưới đây cho từng Màn hình Action (ui) / Operation (service) tham gia vào luồng E2E)*

#### 🖥 MÀN HÌNH ACTION {STT}: {Tên Màn Hình Action}

##### 📌 Danh sách UI Controls (Tra cứu nhanh từ đặc tả)
| Mã Control | Tên Control | Loại thành phần UI | Vai trò & Vị trí hiển thị trên giao diện |
|:---:|:---|:---|:---|
| **Control 1** | ... | ... | ... |

##### KHỐI 1: GIAO DIỆN (UI)

| ID | Mục đích kiểm thử | Trường hợp kiểm thử | Data Test | Các bước thực hiện | Môi trường | Công cụ test | Kết quả mong muốn (UI, DB, Log) | Độ ưu tiên | Exec | Luồng ref |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|:---:|:---|
| **KB-{id}-01** | Kiểm tra Xử lý lỗi validation Email (BVA) | Nhập Email thiếu ký tự @ | `Email: testdomain.com` | (1) Nhập "testdomain.com" vào trường Email. <br> (2) Bấm submit. | Stag | Chrome | **UI:** Trường Email viền đỏ, hiển thị lỗi "Email không đúng định dạng". | P1 | manual | Ref UI: Control-05 |

##### KHỐI 2: CHỨC NĂNG (FUNCTIONAL & E2E LUỒNG NGHIỆP VỤ)

| ID | Mục đích kiểm thử | Trường hợp kiểm thử | Data Test | Các bước thực hiện | Môi trường | Công cụ test | Kết quả mong muốn (UI, DB, Log) | Độ ưu tiên | Exec | Luồng ref |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|:---:|:---|
| **KB-{id}-02** | Kiểm tra hiển thị thành công toàn luồng tạo mới | User tạo mới thành công từ UI xuống BE | `fixture: valid_compose_payload` | (1) Mở màn hình {Tên màn hình}. <br> (2) Nhập dữ liệu hợp lệ. <br> (3) Bấm Lưu. | Stag | Chrome | **UI:** Chuyển hướng sang màn hình Danh sách, bản ghi mới hiển thị ở dòng đầu tiên. <br> **DB:** Bảng `composite_requests` insert thành công bản ghi mới với status `PENDING`. <br> **API:** POST `{endpoint}` trả HTTP 200. | P0 | automate | Luồng chính |

##### KHỐI 3: PHÂN QUYỀN & ATTT (SECURITY)

| ID | Mục đích kiểm thử | Trường hợp kiểm thử | Data Test | Các bước thực hiện | Môi trường | Công cụ test | Kết quả mong muốn (UI, DB, Log) | Độ ưu tiên | Exec | Luồng ref |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|:---:|:---|
| **KB-{id}-03** | Kiểm tra bảo mật IDOR | Thao tác trên tài nguyên của user khác | `ID User khác` | (1) Lấy token User A. <br> (2) Gửi API request xem chi tiết ID User B. | Stag | Postman | **API:** HTTP 403 Forbidden. | P0 | automate | ATTT |

*Độ ưu tiên (= @risk): P0 (Blocker/Sanity/Luồng chính), P1 (Luồng nhánh/Biên/Lỗi HUB), P2 (Lỗi hiển thị/Visual)*
*Exec (= @exec): `automate` (sang qa-robot) · `manual` (tester chạy tay) · `exploratory` (hiếm — visual thuần KHỐI 1). Mỗi dòng `automate` phải có `@id` khớp 1-1 trong file `.feature` và một dataset trong `fixtures.yaml`.*

---

#### ⚙️ VÍ DỤ BIẾN THỂ SERVICE (no-UI) — OPERATION {STT}: `POST /api/v1/transfers`

##### 📌 Danh sách Endpoint/Operation & Hợp đồng (Tra cứu nhanh từ đặc tả)
| Endpoint/Operation | Request field (ràng buộc) | Response / HTTP | Error catalog | Side-effect (DB/MSG/Log) |
|:---|:---|:---|:---|:---|
| `POST /api/v1/transfers` | `amount` (BigDecimal>0), `currency` (enum), `Idempotency-Key` (header) | 201 + `{transferId,status}` | `INSUFFICIENT_FUNDS`→422, `DUP_KEY`→200(idempotent), `INVALID_CCY`→400 | insert `transfers` status PENDING · phát event `transfer.created` · audit log |

##### KHỐI 2: NGHIỆP VỤ & E2E (API → DB → MSG → Log)
| ID | Mục đích kiểm thử | Trường hợp kiểm thử | Data Test | Các bước thực hiện | Môi trường | Công cụ test | Kết quả mong muốn (API, DB, MSG, Log) | Độ ưu tiên | Exec | Luồng ref |
|:---|:---|:---|:---|:---|:---|:---|:---|:---:|:---:|:---|
| **KB-{id}-10** | Idempotency: request trùng key chỉ tạo 1 giao dịch | Gửi cùng `Idempotency-Key` 2 lần | `fixture: valid_transfer` | (1) POST lần 1. <br> (2) POST lại cùng key. | Stag | RequestsLibrary | **API:** lần 2 trả HTTP 200 cùng `transferId` lần 1. <br> **DB:** bảng `transfers` chỉ 1 bản ghi. <br> **MSG:** chỉ 1 event `transfer.created`. | P0 | automate | Luồng chính |

*(Bề mặt service KHÔNG có KHỐI GIAO DIỆN; oracle không chứa `UI:`.)*

---

### 5.3. Hướng dẫn Data & Environment Setup (E2E)

> **Nguồn canonical:** dữ liệu mồi máy-đọc nằm ở `{id}_fixtures.yaml`. Mục này chỉ là bản tóm tắt người-đọc; khi lệch, `fixtures.yaml` thắng.

Đặc tả các dữ liệu mồi, script hoặc cấu hình Mock API để chạy được SLICE này từ đầu đến cuối trên môi trường Staging:
- {Biến 1} -> {Giá trị mẫu và pre-condition}  *(khớp `fixtures.yaml#fixtures[].key`)*

**Tiền điều kiện automation:** các dòng `Exec=automate` cần `ui_schema_{id}.json` tồn tại để `/ntapp-qa-robot` lấy selector. Liệt kê file còn thiếu (nếu có) tại `fixtures.yaml#automation_prereq`.

---

### 5.4. Defect Management (Quy trình quản lý và báo cáo lỗi)

#### 1. Quy chuẩn báo cáo lỗi E2E (Log bug lên Jira)
- **Tiêu đề (Summary):** `[BUG][{id}] - {Mô tả lỗi E2E}`
- **Các bước tái hiện (Steps to Reproduce):** Ghi rõ thao tác UI.
- **Kết quả thực tế (Actual Result):** Mô tả lỗi trên giao diện hoặc phản hồi sai từ Backend.
- **Kết quả kỳ vọng (Expected Result):** Hành vi E2E mong đợi.

#### 2. Báo cáo tiến độ E2E (Test Run Progress Report)
- **Tổng số kịch bản:** `{total_tcs}`
- **Pass:** `{pass_tcs}` (`{pass_rate}%`)
- **Fail:** `{fail_tcs}` (`{fail_rate}%`)
- **Skip:** `{skip_tcs}`

---

### 5.6. Coverage Debt Ledger (Nợ độ phủ do spec gap)

> Theo [explore_and_consistency_rules.md](../../principles/explore_and_consistency_rules.md) §3. Liệt kê mọi **bất biến bắt buộc đang nợ vì spec/contract còn `[TBD]`/gap** — case đã có dạng dòng `[BR]` scripted trong KHỐI 2/3 (không phải charter), expected neo theo contract canonical, hiện FAIL tới khi code đạt. Để không bị ru ngủ bởi "màu xanh automation". Khi gap/contract chốt (round-trip) → gỡ `[BR]`, xóa dòng nợ. Rỗng → ghi "Không có nợ coverage".

| Bề mặt × Bất biến | Gap ID | Case @id ([BR]) | Q&A blocking | Trạng thái |
|:---|:---|:---|:---|:---:|
| {vd: Search merchant × filter-correctness} | GAP-{NN} | KB-SLICE-{id}-{NNN} | {mục Q&A trong qa_report} | Đang nợ |
