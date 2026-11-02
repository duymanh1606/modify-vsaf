# Step 04.1b: WBS Audit & Coverage Quality Gate

> **Acting as:** [Agent E — Master Orchestrator](../agents/agent_e_orchestrator.md) (vai trò QA Gatekeeper)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R4 (Traceability), R6 (Gate), R7 (Stopping Errors).

## MỤC TIÊU (Goal)
Đảm bảo bản danh sách đơn vị work (WBS) do Agent C tạo ra đạt độ bao phủ 100% so với yêu cầu kinh doanh (PRD/Epics), phân loại module đúng 4-type taxonomy, và sở hữu cấu trúc dữ liệu High-Fidelity trước khi tiến hành thiết kế chi tiết.

## VAI TRÒ (Role)
- **Agent thực hiện**: **Agent E (Orchestrator/QA)**.
- **Agent nhận feedback**: **Agent C (Architect)**.

## ĐIỀU KIỆN KÍCH HOẠT (Trigger)
- Sau khi Agent C hoàn tất việc tạo/cập nhật file `project_wbs.md` tại Step 04.1.

---

## QUY TRÌNH KIỂM TOÁN (Audit Workflow)

### 1. Kiểm toán định lượng (Coverage Check)
- **Hành động**: Agent E đối soát danh sách `Epic ID / Story ID` trong WBS (Cột 4) với tài liệu PRD/Epics (Level 0).
- **Check-item**:
    - [ ] Mọi Epic quan trọng đều có ít nhất một đơn vị work tương ứng.
    - [ ] Không có Story nào bị bỏ sót (Missing Coverage).
    - [ ] Story chưa được cover → Agent E ghi nhận vào `Audit Report`.

### 2. Kiểm toán định tính (Data Lineage Check)
- **Hành động**: Kiểm tra tính logic của chuỗi Input/Output.
- **Check-item**:
    - [ ] Cấu trúc 3 dòng thẻ `<br>` (Input/Output) được thực thi 100%.
    - [ ] **Data Chain Integrity**: Mọi Output của ID phía trước phải được sử dụng làm Input cho ID phía sau (tránh dữ liệu "chết" hoặc "mồ côi").

### 2b. Kiểm toán cấu trúc file (Structural Check)
- **Hành động**: Kiểm tra `project_wbs.md` đúng cấu trúc 2 thành phần theo template.
- **Check-item**:
    - [ ] Có **Function Decomposition Tree** (fenced block ` ```text `, ASCII với `├──` `│` `└──`) đặt **trước** Coverage Matrix.
    - [ ] Có **Coverage Matrix** bảng 4 cột.
    - [ ] **Tree ↔ Bảng integrity**: Mọi ID xuất hiện trong Tree phải xuất hiện trong Bảng và ngược lại — không thiếu, không thừa.
    - [ ] **ID uniqueness (global toàn project)**: Mỗi WBS ID xuất hiện đúng 1 row trong Bảng — KHÔNG trùng cross-module/cross-repo (2 FE app cùng chức năng phải phân biệt bằng segment app, vd `SCR-ADM-LOGIN` vs `SCR-APP-LOGIN`). Trùng → FAIL, list ID.

### 2c. Kiểm toán phân loại module (Module Type Classification Check)
- **Hành động**: Kiểm tra mỗi cluster trong WBS đã declare đúng `module_type` (1 trong 4 type) và đơn vị work dưới cluster khớp convention.
- **Check-item**:
    - [ ] Mọi cluster header đều có hậu tố `_(module_type)_` với giá trị ∈ {`backend-service`, `frontend-app`, `integration-contract`, `infrastructure`} (xem template mục 0).
    - [ ] **Naming convention khớp module_type:**
        - `backend-service` / `infrastructure` → ID dạng `{MOD}-NN` hoặc `BE-{MOD}-NN` (feature_id).
        - `frontend-app` → ID dạng `SCR-{NAME}` (screen) hoặc `WGT-{NAME}` (widget). KHÔNG cho phép feature_id pattern trong cluster FE.
        - `integration-contract` → ID dạng `INT-{SRC}-NN`.
    - [ ] **Cross-mismatch check**: ID prefix `SCR-` / `WGT-` xuất hiện trong cluster KHÔNG phải `frontend-app` → FAIL (vd: `SCR-LOGIN` lạc vào cluster `backend-service`).
    - [ ] **Frontend-app coverage:** Cluster `frontend-app` phải có ≥ 1 screen. Cluster chỉ có widgets (không screen) → cho phép nhưng warn (component library reusable).
    - [ ] **Repo binding (CHỈ audit khi project multi-repo):** project có ≥2 FE code repo (signal: `design-system/registry.yaml` khai ≥2 systems, hoặc baseline/user đã xác nhận multi-repo) → mọi Cluster Header `frontend-app` PHẢI có thẻ `- repo: <code-repo-folder>` ở cột 3, giá trị ∈ danh sách code repo đã biết (workspace folder / registry `code_repo`). Thiếu thẻ hoặc giá trị lạ → FAIL, list cluster. Thẻ `repo` xuất hiện ở row đơn vị work (không phải header) → FAIL (sai vị trí). Project 1 code repo → thẻ optional, bỏ qua check.

### 2d. Kiểm toán quan hệ (Relations Cross-Reference Check)
- **Hành động**: Verify relations field (`consumes` / `used_by` / `provider` / `consumers`) trỏ tới ID thực sự tồn tại trong WBS.
- **Check-item**:
    - [ ] Mọi `screen` row có field `consumes: <feature_id>` → mỗi `<feature_id>` phải tồn tại trong cùng WBS (cluster `backend-service` hoặc `integration-contract`).
    - [ ] Mọi `widget` row có field `used_by: <screen_id>` → mỗi `<screen_id>` phải tồn tại trong cùng WBS (cluster `frontend-app`).
    - [ ] Mọi `contract` row có `provider: <module_id>` + `consumers: <module_id>...` → mỗi `<module_id>` phải khớp prefix cluster header tồn tại trong WBS.
    - [ ] Dangling reference (relations trỏ tới ID không tồn tại) → FAIL, list ra ID lạc.

### 2e. Kiểm toán tính đầy đủ đồ thị (Graph-Completeness Presence Check)

> **Bản chất (A-U3):** đây là **presence check** — Agent E chỉ kiểm *có khai hay không*, rồi trả về **gap-list có địa chỉ** để Agent C sửa trong **MỘT lượt follow-up bounded**. Completeness là việc của Agent E (audit), KHÔNG dồn lên Agent C phải hoàn hảo trong 1 pass. Đây là checklist đóng, không phải bài toán mở.

- **Phạm vi:** CHỈ xét **feature-unit**. **BỎ QUA** mọi unit có cột Epic (Cột 4) bắt đầu bằng `BL:` — đó là baseline brownfield as-built, ngoài phạm vi (không ép khai lại cạnh cho hệ đã chạy).
- **Phân loại role:** role đọc từ thẻ `<br>- role: <role>` ở cột 3; nếu trống thì suy từ prefix (`SCR-`/`WGT-` → consumer; `INT-` → contract).
- **Check-item (mỗi mục miss → ghi ID cụ thể vào gap-list):**
    - [ ] Mọi **consumer** (screen / widget, hoặc `role: consumer`) khai **≥ 1** `consumes` → nếu 0 thì list ID.
    - [ ] Mọi **contract** (`INT-*`) khai **cả** `provider` **và** `consumers` → nếu thiếu thì list ID + nêu rõ thiếu cái nào (`provider` hay `consumers`).
    - [ ] Mọi unit có `role ∈ {proxy, gateway, aggregation, bff}` **bị ít nhất một consumer tiêu thụ** mà **không** khai downstream `consumes` → list ID (proxy fronting service khác phải khai nó forward xuống đâu).
- **Output format (gap-list có địa chỉ, cụ thể, đếm được):**
    > `[graph-completeness] N unit consumer thiếu consumes: <id>, <id>; M contract thiếu provider: <id>; K contract thiếu consumers: <id>; P proxy thiếu downstream consumes: <id>`
    Nếu 0 gap → ghi "Graph-completeness: PASS".
- Agent C nhận gap-list và sửa trong **một lượt follow-up bounded** (chỉ điền cạnh thiếu, không re-author toàn bảng), rồi Agent E re-check mục 2e.

### 3. Feedback Loop (Cơ chế phản hồi)
- **Hành động**: Agent E xuất một bản `WBS Audit Report` ngắn gọn.
- **Nếu FAIL**:
    - Agent E cung cấp danh sách cụ thể các ID hoặc Story bị lỗi/thiếu, phân loại theo gate (Coverage / Lineage / Structural / Module Type / Relations / **Graph-completeness**). Riêng Graph-completeness → trả gap-list có địa chỉ (mục 2e) để Agent C điền cạnh thiếu trong 1 lượt follow-up bounded.
    - Agent C **PHẢI** quay lại Step 04.1 để cập nhật lại `project_wbs.md` cho đến khi đạt Pass.
- **Nếu PASS**:
    - Agent E "Khóa" WBS và cho phép workflow chuyển sang Step 04.2 (Modular Design).

---

## KẾT QUẢ ĐẦU RA (Exit Criteria)
1. File `project_wbs.md` đạt trạng thái "Audited & Locked".
2. Báo cáo `WBS_Audit_Report.md` (nếu có lỗi cần fix), phân loại theo 6 gate (Coverage / Lineage / Structural / Module Type / Relations / Graph-completeness).

---

## ⛔ [GATE G2 — WBS Lock] (đặt TRƯỚC Next)

- **FAIL** (bất kỳ 1 trong 6 category: Coverage / Lineage / Structural / Module Type / Relations / **Graph-completeness**) → Agent C **PHẢI** quay lại [`./step-04.1-architecture-global.md`](./step-04.1-architecture-global.md) cập nhật `project_wbs.md` rồi re-audit. KHÔNG đi tiếp (đây là recovery loop của gate, KHÔNG phải `**Next:**`).
- **PASS** → Agent E "Khoá" WBS ("Audited & Locked"). Agent C quay lại Step 04.1 hoàn tất L1/L2 + ERD (nếu chưa) và đạt G3, rồi pipeline chuyển sang Step 04.2.

**Next:** Read fully and follow `./step-04.2-architecture-modules.md`
