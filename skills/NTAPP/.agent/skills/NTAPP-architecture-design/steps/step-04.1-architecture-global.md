# STEP 04.1: GLOBAL ARCHITECTURE DESIGN

> **Acting as:** [Agent C — System Architect](../agents/agent_c_system_architect.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication — Derivation Rule cho ERD), R4 (Traceability), R5 (Consistency L1↔L2), R6 (Gate G3 self-check).

**Input:** `part_02_context_strategy.md` + `part_03_tech_research.md` (nếu có) + PRD/Epics
**Output:** `part_04.1_global_architecture.md` — (Bao gồm: C4 Context L1, Container Diagram L2 & Bảng đặc tả Container)


## MỤC TIÊU BƯỚC NÀY

Chuyển hóa NFR và Tech Stack thành Mô hình Kiến trúc Ứng dụng hoàn chỉnh theo chuẩn C4 Model. Mọi thành phần phải được đặc tả ở mức "Traceability" — truy vết được từng giao thức, từng Topic, từng Database.

---

## QUY TRÌNH THỰC THI (Execution Steps)

### 3.1 Mô hình phân lớp tổng thể
**Trích xuất WBS & Layer 1 (SSoT Sync):** Agent C BẮT BUỘC khởi tạo hoặc cập nhật file `project_wbs.md` theo template `../templates/coverage_matrix_wbs.md` (template spec đầy đủ 2 thành phần: Function Decomposition Tree + Coverage Matrix + 4-type module classification). Quy tắc bổ sung chỉ áp dụng cho step này:

- **Module classification trước, đơn vị work sau:** Với mỗi cluster, Agent C quyết định `module_type` (1 trong 4 — xem template mục 0) **trước**, sau đó mới đặt ID theo convention prefix tương ứng (`BE-{MOD}-NN` / `SCR-{NAME}` / `WGT-{NAME}` / `INT-{SRC}-NN`).
- **Source ID:** ID phải chia đến mức Actionable, gán mã Story/Epic từ PRD/Epics.
- **Relations bắt buộc:** Screen ghi `consumes:`, widget cross-screen ghi `used_by:`, contract ghi `provider:` + `consumers:` (chi tiết format ở template mục 0).
- **Repo binding (CHỈ project multi-repo):** project có ≥2 FE code repo → mỗi Cluster Header `frontend-app` khai thẻ `<br>- repo: <code-repo-folder>` ở cột 3 (format ở template mục 0; unit KHÔNG khai — kế thừa theo module). Danh sách code repo lấy từ system_overview baseline / workspace; không chắc module thuộc repo nào → HỎI user (R3), KHÔNG đoán. Project 1 code repo → bỏ qua.
- `project_wbs.md` là SSoT cho §3.2.0 của HLD final — Step 07 sẽ inject **cả Tree + Bảng** verbatim. KHÔNG tự inject WBS content tại Step 04.2.

**📋 WBS File Management Rule (BẮT BUỘC, để bảo vệ work của user):**
- **File KHÔNG tồn tại** → tạo mới đúng cấu trúc theo template (Tree + Bảng).
- **File ĐÃ tồn tại + valid format** (đủ 2 thành phần theo template):
  → MERGE: giữ nguyên row cũ, **append** row mới vào cả Tree và Bảng. **TUYỆT ĐỐI KHÔNG overwrite** toàn file.
- **File ĐÃ tồn tại + invalid format** (thiếu thành phần hoặc sai cấu trúc theo template):
  → DỪNG, escalate Agent E. Agent E hỏi user: "WBS file hiện không đúng format chuẩn template (thiếu Tree hoặc Bảng). Anh/chị muốn (a) em backup `.bak` và tạo lại từ template, hay (b) anh/chị tự sửa rồi quay lại?". KHÔNG đụng vào file user trước khi confirm.

⚠️ **HANDSHAKE RULE (BẮT BUỘC):** 
Ngay sau khi sinh xong bảng WBS, Agent C phải DỪNG LẠI và kích hoạt **Step 04.1b: WBS Audit & Coverage Gate**. Tuyệt đối KHÔNG thực hiện các sơ đồ L1/L2 (3.1.1, 3.1.2) và Phase 2 (Modular Design) nếu chưa nhận được xác nhận `PASS` từ Agent E.

#### 3.1.1 System Context Diagram (Level 1)
**Sử dụng Mermaid C4Context.** Agent C phải tuân thủ nguyên tắc **Un-bundling** (Tách biệt các thực thể legacy).

#### 3.1.2 Container Diagram (Level 2) & Đặc tả Container
**Sử dụng Mermaid C4Container.** Phải thể hiện rõ **Security Zoning** (DMZ và Internal Network).

**⚠️ QUY TẮC BỐ CỤC BẮT BUỘC (Layout Convention):**
Agent C áp các rule sau **ngay khi sinh diagram** (không post-process). Hướng layer: **Actor đỉnh → Internal → DMZ → External đáy**.

**Bước 1 — Directive NGAY SAU dòng `title`:**
```
UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```
- `$c4BoundaryInRow="1"`: mỗi `System_Boundary` chiếm 1 hàng (xếp dọc).
- `$c4ShapeInRow="3"`: container trong Boundary xếp 3/hàng.

**Bước 2 — Thứ tự khai báo (Top → Bottom):**
1. `Person(...)` — Actor/User dàn ngang trên cùng.
2. `System_Boundary(internal, ...)` — Internal Network/Trust Zone:
   - Tầng 1: `Presentation` (Web/UI/App) + `API`.
   - Tầng 2: `Core` (orchestrator/business) + `Data` (DB/Cache/Storage).
   - **Auto-split rule:** Boundary nào > 4 container → BẮT BUỘC chẻ đôi thành 2 Boundary con cạnh nhau (vd `Core - Business Logic` + `Core - Platform Services`) để tránh kéo dọc.
3. `System_Boundary(dmz, ...)` — Edge/DMZ chốt dưới Internal.
4. `System_Ext(...)` — External Systems dưới đáy (đi qua DMZ). Enterprise APIs nội bộ tách cạnh DMZ.

**Bước 3 — Nhóm `Rel(...)` theo tầng:** (1) Actor ↔ Internal, (2) nội bộ Internal, (3) Internal ↔ DMZ, (4) DMZ ↔ External.

**Bước 4 — Nesting & content cleanup:**
- Boundary nesting ≤ 2 cấp; group theo layer, không group theo block nhỏ vụn.
- Mô tả container ≤ 2 dòng, dùng keywords. **Không gắn Requirement IDs** (vd `[BE-MOD-01]`, `[REQ-02]`) vào diagram — giữ trong WBS table.

**Bước 5 — Mermaid syntax compatibility:**
- KHÔNG dùng ký tự `→`, `{`, `}`, hoặc Unicode đặc biệt khác trong mã Mermaid.
- Comment chỉ dùng `%%` (không dùng `'`).
- Đảm bảo render thành công trong C4Container extension.

**Sau khi vẽ xong sơ đồ**, BẮT BUỘC điền đầy đủ Bảng Đặc tả Container & Database:

| Tên Container | Công nghệ (Tech Stack) | Giao tiếp Inbound | Giao tiếp Outbound | Vai trò & Logic xử lý chi tiết (Data Domain, Fallback) |
| :--- | :--- | :--- | :--- | :--- |
| `{Container Name}` | `{Framework v.X, DB Type}` | `{HTTP REST từ Web UI}` | `{gRPC đến Vector DB}` | `{Nhiệm vụ chính. Logic mapping. Fallback nếu timeout}` |

**Quy tắc bảng Container:**
- `TUYỆT ĐỐI KHÔNG` ghi chung chung ("Xử lý request"). Lỗ hổng thường gặp là mô tả quá sơ sài. **Yêu cầu BẮT BUỘC: Cột "Vai trò & Cơ chế xử lý chi tiết" phải được viết cực kỳ chi tiết, diễn giải cụ thể và hoàn toàn bằng tiếng Việt.** Phải nêu rõ loại luồng dữ liệu hoặc bước thuật toán sẽ xử lý.
- Phải ghi chính xác tên Kafka Topic (nếu dùng), tên DB (MariaDB/Postgres/Mongo), tên Cache Key pattern.
- Cột "Fallback" phải mô tả cụ thể hành vi khi dependency bị lỗi.
- Liệt kê & mô tả đầy đủ tất cả các container trong diagram.

#### 3.1.3 Global Data Model (ERD)
**Sử dụng Mermaid `erDiagram`.** Đây là tài liệu SSoT kỹ thuật cho các thực thể dữ liệu.

**⚠️ SAFETY GUARDRAILS (Chống ảo giác & Trôi thông tin):**
- **Derivation Rule**: Agent C **TUYỆT ĐỐI KHÔNG** tự bịa ra thực thể hay dựa vào PRD & Epics một cách cảm tính. Danh mục thực thể phải trích xuất 100% từ bộ 3 nguồn kỹ thuật:
    1. **Tech Research (Step 3)**: Định hướng công nghệ và cấu trúc dữ liệu đặc thù (vd: Vector Store schemas).
    2. **Context Diagram (L1)**: Các thực thể dữ liệu trao đổi giữa các hệ thống lớn.
    3. **Container Diagram (L2)**: Các ranh giới dữ liệu vật lý và Database/Cache/Queue nodes.
- **Traceability Rule**: Mỗi thực thể chính trong ERD phải có ghi chú (giải thích) về việc nó được lưu trữ tại Container nào trong sơ đồ L2.
- **Relationship Rule (No Orphans)**: Mọi thực thể trong ERD **BẮT BUỘC** phải có ít nhất một mối quan hệ (Rel) với thực thể khác. Không chấp nhận thực thể "mồ côi" (orphan entity) vì nó cho thấy sự thiếu sót trong logic nghiệp vụ hoặc dư thừa thiết kế.
- **Granularity Rule**: Giới hạn ở mức **Level 2 ERD** (Các thực thể chính và quan hệ lõi). KHÔNG sa đà vào liệt kê hàng chục trường dữ liệu chi tiết ở bước này (dành cho Step 06.2).

#### 3.1.4 Mô hình ứng dụng framework (Nếu có)
- Xác định Design Pattern chính (Hexagonal / Clean Architecture / MVC...).
- Mô tả sự phân tách giữa 3 lớp: Presentation, Application Core, Infrastructure.

## Ghi output (POST-PROCESSING)
1. Ghi kết quả vào file:
   - `{intermediate_folder}/part_04.1_global_architecture.md` (Bao gồm: C4 Context L1, Container Diagram L2 & Bảng đặc tả Container).
2. **Self-audit Layout Convention:** Agent C tự check cả L1 và L2 trên checklist Exit Gate G3 (mục dưới).
3. **Conditional remediation (with graceful fallback):**
   - **Khi G3 PASS** → bỏ qua bước này, không gọi optimizer.
   - **Khi G3 FAIL ở tiêu chí layout/syntax/content:**
     - **TRY:** kích hoạt skill `c4-diagram-optimizer` qua `@../../c4-diagram-optimizer/SKILL.md`.
     - **CATCH (skill không cài / không tìm thấy):** Agent C tự sửa diagram theo G3 checklist + warn user:
       ```
       ⚠️ c4-diagram-optimizer chưa cài tại `../../c4-diagram-optimizer/`.
       Tự sửa theo checklist G3. Khuyến nghị cài skill để remediation chất lượng hơn.
       ```
     - KHÔNG fail toàn bộ workflow chỉ vì optimizer missing.
---

## ĐIỀU KIỆN TIẾP TỤC (Exit Criteria)
- [ ] `project_wbs.md` đủ 2 thành phần theo template (Function Decomposition Tree ASCII + Coverage Matrix bảng 4 cột).
- [ ] **WBS đã được Agent E Audit và đạt trạng thái "PASS" (Step 04.1b).**
- [ ] Sơ đồ Context L1 có mũi tên với nhãn giao thức đầy đủ.
- [ ] Sơ đồ L2 đã phân ranh giới DMZ/Internal.
- [ ] Sơ đồ L2 tuân thủ Layout Convention.
- [ ] Bảng Container có đủ tất cả container, database từ sơ đồ L2, không bỏ sót.
- [ ] Sơ đồ ERD đã bao phủ 100% thực thể lõi (No Orphans).
- [ ] Sơ đồ ERD đã ánh xạ thực thể vào đúng Container (Database/Cache).
- [ ] Không còn placeholder `[Data]` hay `[VD: ...]` trong output.

---

## 🚦 EXIT GATE — L1/L2 Consistency (G3, self-check by Agent C)

Agent C **PHẢI tự audit** trước khi handoff sang Step 04.2. Mỗi tiêu chí FAIL → tự sửa (hoặc gọi `c4-diagram-optimizer` nếu là vấn đề layout/syntax/content) rồi audit lại.

**Architecture consistency:**
- [ ] Mọi `System_Ext` trong L1 đều xuất hiện trong L2 (hoặc có ghi chú lý do bỏ).
- [ ] ERD không có **orphan entity** (mọi thực thể có ≥ 1 quan hệ).
- [ ] Bảng Container đã liệt kê đủ TẤT CẢ node trong L2 — không bỏ sót.
- [ ] Không có protocol/topic/DB nào còn `[TBD]` ở mức Container Spec (chỉ chấp nhận `[TBD]` ở Module 0 nếu thực sự thiếu data).

**Layout convention & syntax:**
- [ ] Sơ đồ L2 tuân thủ Layout Convention §3.1.2 Bước 1-5 (directive, thứ tự khai báo, auto-split >4 container, nesting ≤2 cấp, Mermaid syntax compatibility).

**FAIL → Agent C tự sửa hoặc gọi optimizer remediation rồi audit lại. KHÔNG chuyển sang 04.2 nếu chưa pass G3.**

---

## ⛔ [GATE — Handshake WBS + G3] (đặt TRƯỚC Next)

- **Handshake (BẮT BUỘC):** ngay sau khi sinh xong bảng WBS, DỪNG và kích hoạt **Step 04.1b (Gate G2 — WBS Audit)**; KHÔNG vẽ L1/L2 (3.1.1, 3.1.2) cho tới khi nhận `PASS` từ Agent E.
- **G3 (self-check):** sau khi hoàn tất L1/L2/ERD, Agent C tự audit checklist trên; FAIL → tự sửa/optimizer rồi audit lại.
- Chỉ qua `**Next:**` (Step 04.1b để chốt khoá WBS / G2) khi WBS đã sinh xong; Step 04.1b sẽ trỏ tiếp Step 04.2 sau khi đạt Pass G2 (+ G3).

**Next:** Read fully and follow `./step-04.1b-wbs-audit.md`