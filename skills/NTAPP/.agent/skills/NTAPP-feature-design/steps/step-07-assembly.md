# STEP 07: SEQUENTIAL ASSEMBLY & FINAL AUDIT (TERMINAL)

> **Acting as:** [Agent F0 — Lead Orchestrator](../agents/agent_f0_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R1 (Verbatim Injection), R2 (Zero-Summarization), R6 (Quantitative Audit Gate).
> ⛔ Đây là step cuối — KHÔNG còn step kế.

**Input:** Các file `f*_part.md` thực tế trong `{intermediate_folder}` — số lượng tùy `id_type` (xem Execution Matrix workflow §3). Luôn có: `f0_overview_part.md`, `f4_qa_part.md`, `f0_sync_matrix_part.md`. Conditional: `f3_ui_part.md` / `f1_logic_part.md` / `f2_data_part.md`.

**Output (dual-write):**
- Canonical: `{planning_artifacts}/{id}_detailed_design.md` (latest, overwrite)
- Archive: `{planning_artifacts}/archive/{id}_detailed_design_v{N}.md` (snapshot history)

---

## 1. Mục tiêu
Hợp nhất các file part thực tế từ Step 01-06 thành Master Detailed Design bằng quy trình **5-Pass Assembly** — tuân thủ R1 (Verbatim) và R2 (Zero-Summarization). Pass 2-4 inject conditional theo part đã tồn tại.

## 2. QUY TRÌNH "FFT ASSEMBLY" (5-PASS)

### PASS 1: INITIALIZATION (Khởi tạo khung Master Detailed Design)
- Sử dụng `../templates/master_detailed_design_v4_template.md` làm phôi.
- Điền tên đơn vị work và `id` (WBS ID) + `id_type` rõ ràng trong header.
- Hoàn thiện bảng **Changelog** (Lịch sử thay đổi).
- Bơm nội dung từ `f0_overview_part.md` vào **Mục 1 (Overview & Scope)**.

### PASS 2: FRONTEND WORKSPACE INJECTION (Bơm UI/UX) — conditional
- **Áp dụng khi:** `f3_ui_part.md` tồn tại (`id_type ∈ {screen_id, widget_id}`).
- Bơm nội dung từ `f3_ui_part.md` vào **Mục 2 (Frontend Workspace)**.
- **TỐI QUAN TRỌNG (theo R1, R2):**
    - Bê nguyên xi ASCII Wireframe Blueprint.
    - Đảm bảo bảng **UI Controls** không bị mất Case/Validation nào.
- **Nếu f3 không tồn tại** (BE feature): mark Mục 2 = `_Không áp dụng (id_type = feature_id — không có UI)._` và bỏ trống.

### PASS 3: BACKEND & LOGIC INJECTION (Bơm Logic) — conditional
- **Áp dụng khi:** `f1_logic_part.md` tồn tại (`id_type == feature_id`).
- Bơm nội dung từ `f1_logic_part.md` vào **Mục 3 (Backend Workspace)**.
- **Yêu cầu (theo R2):**
    - Sơ đồ Mermaid Sequence Diagram phải nguyên vẹn.
    - Bảng **Logic Matrix** phải khớp 100% số lượng các bước logic.
- **Nếu f1 không tồn tại** (FE screen/widget): mark Mục 3 = `_Không áp dụng (id_type = {id_type} — FE consume BE logic, không own)._` và bỏ trống.

### PASS 4: DATA & QA INJECTION (Bơm Tích hợp & Kiểm thử)
- **Mục 4 — conditional:** Bơm `f2_data_part.md` vào **Mục 4 (Data & Integration)** nếu tồn tại. Nếu không (FE screen / widget không own state): mark `_Không áp dụng._`
- **Mục 5 — luôn áp dụng:** Bơm `f4_qa_part.md` vào **Mục 5 (Quality Assurance)** (luôn tồn tại).
- **Yêu cầu (theo R1, R2):** Bê nguyên xi các mẫu JSON Schema, bảng Error Codes, **bảng Persistence Write-Spec §4.3** và bảng KBKT.

### PASS 5: SYNC MATRIX & QUANTITATIVE AUDIT (R6 Quantitative Audit Gate)
- Bơm `f0_sync_matrix_part.md` vào **Mục 6 (Interaction Sync Matrix)**.
- **Audit Checklist (BẮT BUỘC pass trước khi release — áp dụng theo part đã inject):**
    - [ ] **Row Count Match:** Đếm số dòng bảng Logic (Mục 3, nếu có) + Write-Spec (Mục 4.3, nếu có) + QA (Mục 5) khớp với Parts thô.
    - [ ] **Diagram Count:** Số lượng Mermaid Diagram không đổi giữa parts và DD final.
    - [ ] **Traceability:** 100% Case ID trong Sync Matrix có KBKT-ID tham chiếu (R4).
    - [ ] **Section coverage:** Mỗi mục không applicable được mark rõ `_Không áp dụng (lý do)._` — không để trống ambiguous.
- **Xử lý FAIL:** Nếu hụt dòng/diagram → bơm lại đoạn bị thiếu (KHÔNG release DD nếu chưa pass — theo R6).

---

## 3. PASS 6: DUAL-WRITE OUTPUT (Canonical + Archive)

Sau khi Pass 5 PASS, Agent F0 PHẢI:

1. `mkdir -p {planning_artifacts}/archive/` (idempotent).
2. Detect `N_next`: list `{planning_artifacts}/archive/{id}_detailed_design_v*.md` → `max(N) + 1` (hoặc `1` nếu archive rỗng).
3. Ghi 2 file (cùng nội dung):
    - **Canonical:** `{planning_artifacts}/{id}_detailed_design.md` (overwrite — latest pointer).
    - **Archive:** `{planning_artifacts}/archive/{id}_detailed_design_v{N_next}.md` (new snapshot).
4. Báo user: "✅ Đã ghi canonical `{id}_detailed_design.md` + archive `_v{N_next}.md` (id_type={id_type})".

---

## 4. ĐIỀU KIỆN HOÀN THÀNH (Done Criteria)

- [ ] Canonical `{planning_artifacts}/{id}_detailed_design.md` đã ghi (overwrite latest).
- [ ] Archive `{planning_artifacts}/archive/{id}_detailed_design_v{N_next}.md` đã tạo.
- [ ] Tóm tắt kết quả (số lượng table rows, diagrams, mục applicable / N/A) được hiển thị cho User.
- [ ] Audit Matrix kết luận: `PASSED`.

## [GATE] — Release (⛔ chốt chặn cuối — KHÔNG có Next)

- Pass 5 Quantitative Audit (R6) PASS: Row Count Match + Diagram Count + Traceability + Section coverage. Nếu hụt dòng/diagram → bơm lại đoạn thiếu, **KHÔNG release DD** khi chưa pass.
- Dual-write Canonical + Archive (Pass 6) hoàn tất. Đây là step **TERMINAL** — không còn `**Next:**`; kết thúc workflow.

---
*Lưu ý: Tuân thủ R3 + R9 — không tự ý bịa đặt nội dung ngoài các file Parts đã được Specialist phê duyệt. Nếu thiếu Part → DỪNG, hỏi user.*
