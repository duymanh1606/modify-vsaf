# STEP 06: MODULE 0 — CONNECTIVITY MATRIX & INTEGRATION HARDENING

> **Acting as:** [Agent F — Integration Architect](../agents/agent_f_integration_architect.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R1 (Verbatim Injection), R3 (Zero-Fabrication), R4 (Traceability), R8 (Contract Lock).

**Input:** `part_04.1_global_architecture.md` (HLD L1/L2 + ERD), `part_04.2_modular_deepdive.md`, `part_05_implementation_security.md`, [module_0_template.md](../templates/module_0_template.md)
**Output trung gian:** `part_06_module0_draft.md`
**Output thành phẩm (dual-write):**
- Canonical: `{planning_artifacts}/00_system_connectivity_integration.md` (latest, overwrite)
- Archive: `{planning_artifacts}/archive/00_system_connectivity_integration_v{N}.md` (snapshot history)

---

## MỤC TIÊU

Xuất bản **Module 0** — bản đồ tích hợp hệ thống bất biến, gồm 2 phase nội bộ:
- **Phase A — Connectivity Skeleton**: trích xuất ma trận kết nối + sơ đồ trình tự gốc từ HLD L1.
- **Phase B — Integration Hardening**: tiêm Schema, Resilience, Security policies vào skeleton đã chốt.

---

## PHASE A — CONNECTIVITY MATRIX (Skeleton Extraction)

### A.1. Ingest Input Context
- **Biểu mẫu đích:** Đọc tệp [module_0_template.md](../templates/module_0_template.md) để nắm cấu trúc 7 phần bắt buộc.
- **Dữ liệu nguồn:** Đọc `part_04.1_global_architecture.md` (Container Diagram L2 + ERD) và `part_04.2_modular_deepdive.md` (Sequence Diagrams).
- Liệt kê toàn bộ các mũi tên giao tiếp giữa các Container.

### A.2. Xây dựng Sơ đồ trình tự gốc
- Vẽ sơ đồ Mermaid `sequenceDiagram` mô tả luồng Payload đi qua các module chính.
- Sử dụng đúng tên các phân hệ đã định nghĩa ở L1/L2 (R5 — Consistency).

### A.3. Lập Ma trận kết nối
- Điền dữ liệu vào bảng Ma trận tại Mục 1 của [module_0_template.md](../templates/module_0_template.md).
- **Payload Alignment**: Source/Target phải tương ứng với các thực thể trong ERD.
- Ghi rõ giao thức (Protocol) theo đúng L1 (vd: gRPC, REST, Kafka topic name).
- Nếu L1 chưa quy định Protocol → đánh dấu `[TBD]` (R3 — Zero-Fabrication).
- **A-U4 — Edge↔Contract mapping (BẮT BUỘC):** với **mỗi cạnh service-to-service NỘI BỘ** (một service gọi một service khác trong hệ), ghi vào cột `INT-*` đúng **một** unit contract sở hữu cạnh đó. Nếu cạnh chưa có contract:
    - Agent F **tạo mới** unit `INT-*` cho cạnh đó và ghi chú "cần bổ sung vào WBS" (contract này sẽ được khai ở `project_wbs.md` với `provider` + `consumers` tương ứng), **hoặc**
    - đánh dấu cạnh là `external` / `no-contract` kèm **lý do** rõ ràng (vd: gọi hệ đối tác bên thứ ba, không phải cạnh nội bộ).
    - **CẤM** để cạnh nội bộ không có contract mà không có lý do (đây là nguồn của "edge without owner" — cạnh không ai sở hữu).

### A.4. Phase A Checkpoint
- [ ] Số luồng kết nối khớp với số mũi tên (Rel) trong sơ đồ L2.
- [ ] Mọi Container trong L2 xuất hiện trong ma trận (no missing node).
- [ ] Không có entry "[Data]" hoặc placeholder runtime trong ma trận.
- [ ] **Mọi cạnh nội bộ (service→service) có một `INT-*` sở hữu, HOẶC được đánh dấu `external`/`no-contract` kèm lý do** — không còn cạnh nội bộ không hợp đồng và không lý do (A-U4).

---

## PHASE B — INTEGRATION HARDENING (Policy Injection)

### B.1. Lock & Ingest
- Đọc lại Phase A output làm Metadata bất biến.
- **Nghiêm cấm:** Không thay đổi Ma trận kết nối (Mục 1) và Sơ đồ trình tự (Mục 2). Nhiệm vụ duy nhất là tiêm dữ liệu vào các mục còn lại.

### B.2. Master Data Modeling (ERD Consolidation)
- Trích xuất và chi tiết hoá **Master Data Schema** từ ERD ở `part_04.1_global_architecture.md`.
- ERD trong Module 0 phải là bản chi tiết hơn (Level 3) của ERD ở Step 4.1, đảm bảo tính nhất quán 100% về định danh thực thể (R5).
- Thêm các Metadata trường bắt buộc: `trace_id`, `timestamp`.
- Nếu không tìm thấy cấu trúc dữ liệu thô trong L1 → đánh dấu `[TBD]` (R3).

### B.3. Apply Global Mesh Policies
- Đặc tả: cơ chế xác thực (Auth), kháng lỗi (Resilience: retry/circuit breaker/timeout), bảng trạng thái toàn cục (States).
- Đối chiếu với từng dòng trong Ma trận kết nối ở Phase A để thiết lập chính sách tương ứng (1-1 mapping).

### B.4. Final Assembly & Dual-Write

#### B.4.1. R8 Sync Check (BẮT BUỘC trước khi write)

Agent F kiểm tra context invocation:
- **Case 1 — Cascade từ HLD update (Step 07 trigger):** Cho phép write (Module 0 phải sync theo HLD mới).
- **Case 2 — Reconcile drift (Module 0 hiện tại không khớp HLD canonical):** Cho phép write để đồng nhất.
- **Case 3 — Edit độc lập (HLD không đổi, Module 0 vẫn khớp):** **REJECT** theo R8. Báo user: "Module 0 đã khớp HLD và HLD chưa update — không có lý do để bump version. Nếu cần thay đổi Schema/Protocol, hãy update HLD ở Stage 2 trước, Module 0 sẽ cascade theo."

#### B.4.2. Merge content
- Kết hợp dữ liệu mới vào các Mục 3, 4, 5, 6, 7 của bản mẫu [module_0_template.md](../templates/module_0_template.md).
- **Ghi vết draft:** Lưu bản thảo gộp tại `{intermediate_folder}/part_06_module0_draft.md`.

#### B.4.3. Dual-Write (chỉ thực hiện khi B.4.1 PASS)

1. `mkdir -p {planning_artifacts}/archive/` (idempotent).
2. Detect `N_next`: list `{planning_artifacts}/archive/00_system_connectivity_integration_v*.md` → `max(N) + 1`.
3. Ghi 2 file:
    - Canonical: `{planning_artifacts}/00_system_connectivity_integration.md` (overwrite).
    - Archive: `{planning_artifacts}/archive/00_system_connectivity_integration_v{N_next}.md` (new snapshot).

---

## EXIT CRITERIA (Done = đủ tất cả)

- [ ] `part_06_module0_draft.md` chứa cả Phase A + Phase B.
- [ ] **R8 Sync Check** (B.4.1) đã PASS — write được phép vì cascade từ HLD update HOẶC reconcile drift.
- [ ] Canonical `{planning_artifacts}/00_system_connectivity_integration.md` đã ghi (overwrite latest).
- [ ] Archive `{planning_artifacts}/archive/00_system_connectivity_integration_v{N_next}.md` đã tạo.
- [ ] **Sanity Check**: ERD trong tệp này khớp hoàn toàn với danh mục thực thể đã dùng trong HLD L2 (R5).
- [ ] Báo cáo xác nhận: "Đã trích xuất chính xác X luồng kết nối từ HLD L1".
- [ ] Không còn placeholder Template, ngoại trừ `[TBD]` có lý do rõ ràng.

---

## ⛔ [GATE — R8 Sync Check] (đặt TRƯỚC Next)

Dual-write Module 0 chỉ thực hiện khi **R8 Sync Check (B.4.1) PASS** (cascade từ HLD update HOẶC reconcile drift). Case 3 (edit độc lập, HLD chưa đổi) → **REJECT**, KHÔNG đi tiếp. PASS → đã ghi canonical + archive → sang Step 07 assembly.

**Next:** Read fully and follow `./step-07-assembly.md`
