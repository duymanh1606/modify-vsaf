# STEP 07: MERGE, QA & FINALIZE

> **Acting as:** [Agent E — Master Orchestrator](../agents/agent_e_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R1 (Verbatim Injection), R2 (Zero-Summarization), R4 (Traceability), R6 (Quantitative Audit Gate).
> ⛔ **Đây là step cuối (TERMINAL) — KHÔNG có `**Next:**`.** Cổng cuối = G4 Quantitative Audit + trình bày HLD cho người dùng. (Cascade Module 0 sync ở §7.5.4 là re-run R8, KHÔNG phải pointer pipeline.)

**Input:** Tất cả file `part*.md` trong thư mục `architecture_design_parts/`
**Output (dual-write):**
- Canonical: `{planning_artifacts}/architecture_design.md` (latest, overwrite mỗi run)
- Archive: `{planning_artifacts}/archive/architecture_design_v{N}.md` (snapshot history, version mới mỗi run)

---

Hợp nhất toàn bộ output từ các Agent A, B, C, D thành một tài liệu HLD duy nhất, nhất quán và đầy đủ.

---

## QUY TRÌNH THỰC THI "FFT ASSEMBLY" (5-PHASE — phase nội bộ của Step 07, không phải global pass)

### GIAI ĐOẠN 1: INITIALIZATION (Khởi tạo khung HLD)
- **Hành động:** Sử dụng `architecture_design_final_template.md` để tạo file HLD mới.
- **Nhiệm vụ:**
    - Thiết lập tiêu đề dự án.
    - Hoàn thiện bảng **Document History**.
    - Khởi tạo bảng **Architecture Audit Matrix** để đối soát WBS ID (SSoT).

### GIAI ĐOẠN 2: STRATEGY & NFR INJECTION (Bơm bối cảnh)
- **Hành động:** Bơm nội dung từ `part_02_context_strategy.md` vào Mục 1 và Mục 2 của HLD.
- **Yêu cầu:** Giữ nguyên bảng NFR và các bullet points của System Thinking.

### GIAI ĐOẠN 3: ARCHITECTURE DEEP-DIVE INJECTION (Bơm kiến trúc)
- **Hành động:** Bơm nội dung vào Mục 3 theo thứ tự sau:
    1. **§3.1.x** (Phân lớp, C4 L1/L2, ERD, Framework) ← từ `part_04.1_global_architecture.md` verbatim.
    2. **§3.2.0 (Function Decomposition Tree + Coverage Matrix)** ← từ `project_wbs.md` verbatim (bê nguyên cả Tree ASCII + Bảng 4 cột). Đây là single source — KHÔNG đọc từ part_04.2.
    3. **§3.2.1+ (Mô hình tổng thể, Sequence/Data Flow per module)** ← từ `part_04.2_modular_deepdive.md` verbatim, bắt đầu từ §3.2.1 (part_04.2 không được chứa §3.2.0 — xem step-04.2).
- **TỐI QUAN TRỌNG:**
    - Sơ đồ C4 Level 1 (Context).
    - Sơ đồ C4 Level 2 (Container with DMZ/Internal boundary).
    - Toàn bộ Sequence Diagrams cho từng Module trọng yếu.
    - Cấm tuyệt đối việc bỏ bớt Loop/Alt trong Sequence Diagram.

### GIAI ĐOẠN 4: IMPLEMENTATION & SOLUTIONS INJECTION (Bơm thực thi)
- **Hành động:** Bơm nội dung từ `part_05_implementation_security.md` vào Mục 4 và Mục 5.
- **Yêu cầu:** Bê nguyên xi ASCII Project Tree và các bảng ATTT (Zoning), Caching, Sharding.

### GIAI ĐOẠN 5: QUANTITATIVE AUDIT & ADR (Đối soát định lượng)
- **Hành động:** Thực hiện kiểm toán tài liệu cuối cùng.
- **Chỉ tiêu đối soát (Audit Checklist):**
    - [ ] **WBS Injection (verify)**: §3.2.0 của HLD đã chứa cả Function Decomposition Tree (ASCII) + Coverage Matrix bảng 4 cột, copy verbatim từ `project_wbs.md` (write action thực hiện ở Giai đoạn 3, mục này chỉ verify).
    - [ ] **Data Integrity**: Đối soát tất cả Object/Table trong Sequence và Data Flow (phần 3.2.2) với sơ đồ ERD (phần 3.1.3). Nếu phát hiện thực thể 'ngoài luồng' -> Agent E phải yêu cầu Agent C cập nhật lại ERD.
    - [ ] **No Orphan Entities**: Đảm bảo 100% thực thể trong ERD đều có quan hệ (arrow), không có thực thể đứng độc lập.
    - [ ] **Data Consistency**: Đảm bảo sơ đồ ERD trong tài liệu HLD chính (3.1.3) khớp 100% với ERD trong tài liệu Tích hợp hệ thống (Module 0).
    - [ ] **Code-to-Design Mapping:** Kiểm tra tính logic giữa Folder Path trong phần 4.1 và Modules đã khai báo.
    - [ ] **Diagram Count:** Tổng số sơ đồ Mermaid trong HLD phải khớp 100% với tổng số sơ đồ trong các file thô.
    - [ ] **ADR Integrity:** Có ít nhất 3 bản ghi ADR được tổng hợp tại Mục 6.
    - [ ] **WBS Traceability:** Mọi ID tính năng (vd: `RAG-01`) phải xuất hiện ít nhất một lần trong sơ đồ Sequence hoặc Data Flow kỹ thuật tại Mục 3.2.0.
- **Xử lý hụt:** Nếu số lượng sơ đồ/bảng không khớp -> Agent E PHẢI thực hiện `replace_file_content` để bơm lại đoạn bị thiếu.

---

### 7.3 Tổng hợp ADR (Architectural Decision Records)
Quét toàn bộ các file intermediate để thu thập các quyết định kiến trúc quan trọng. Mỗi quyết định lớn (chọn DB, chọn pattern, chọn giao thức) phải có 1 ADR entry:

```markdown
### ADR-{XXX}: {Tiêu đề quyết định}
- **Ngày:** {YYYY-MM-DD}
- **Bối cảnh:** {Vấn đề cần giải quyết — trích xuất từ NFR hoặc Tech Proposal}
- **Các phương án đã xem xét:** {A: ..., B: ..., C: ...}
- **Quyết định:** {Phương án được chọn}
- **Lý do:** {Lý do kỹ thuật, liên kết với NFR cụ thể}
- **Hệ quả (Consequences):** {Điều gì sẽ thay đổi khi áp dụng quyết định này}
```

**Số lượng ADR tối thiểu:** 3 entries (Tech Stack chính, DB chính, Pattern chính).

---

### 7.4 Merge Final HLD Document
Hợp nhất theo đúng cấu trúc của `architecture_design_final_template.md`:

```markdown
# TÀI LIỆU THIẾT KẾ KIẾN TRÚC TỔNG THỂ: {Tên dự án}

## BẢNG GHI NHẬN THAY ĐỔI
{Điền metadata: date, version, change description}

## 1. GIỚI THIỆU & PHÂN TÍCH CHIẾN LƯỢC
{Nội dung từ part_02_context_strategy.md - BẮT BUỘC COPY 1:1}

## 2. KIẾN TRÚC ỨNG DỤNG
{Nội dung từ part_04.1_global_architecture.md & part_04.2_modular_deepdive.md - BẮT BUỘC COPY 1:1}

## 3. CHIẾN LƯỢC TRIỂN KHAI VẬT LÝ & GIẢI PHÁP
{Nội dung từ part_05_implementation_security.md - BẮT BUỘC COPY 1:1}

## 4. NHẬT KÝ QUYẾT ĐỊNH KIẾN TRÚC (ADR)
{Các ADR entries được tổng hợp ở bước 6.3}

```

**Quy tắc merge:**
- KHÔNG lược bỏ bất kỳ nội dung nào từ các file intermediate.
- KHÔNG thay đổi số liệu hoặc thuật ngữ — chỉ ghép nối.
- Kiểm tra tính nhất quán: tên Container ở Section 3 phải khớp chính xác với tên Folder ở Section 4.
- Bảng BẢNG GHI NHẬN THAY ĐỔI phải điền: ngày hôm nay, version, "Khởi tạo HLD bởi Multi-Agent System".

---

### 7.5 Dual-Write Output (Canonical + Archive)

Agent E PHẢI thực hiện 4 bước sau:

1. **Tạo archive folder** (idempotent):
   ```
   mkdir -p {planning_artifacts}/archive/
   ```

2. **Detect next version number `N_next`:**
   - List existing archive: `ls {planning_artifacts}/archive/architecture_design_v*.md`
   - Parse `v{N}` từ tên file → `N_next = max(N) + 1` (hoặc `1` nếu archive rỗng).

3. **Ghi 2 file (cùng nội dung HLD đã merge):**
   - **Canonical:** `{planning_artifacts}/architecture_design.md` (overwrite — latest pointer).
   - **Archive:** `{planning_artifacts}/archive/architecture_design_v{N_next}.md` (new snapshot).

4. **Cascade Module 0 sync (R8 logic mới):**
   - Vì HLD vừa update, Module 0 BẮT BUỘC re-run Step 06 để cập nhật theo HLD mới.
   - Agent E auto-trigger Step 06 nếu phát hiện HLD changed (so sánh nội dung canonical với archive v{N_next - 1} nếu có).

---

### 7.6 Trình bày kết quả cho người dùng
Sau khi ghi file thành công, Agent E hiển thị tóm tắt:

```markdown
## ✅ HOÀN THÀNH — Thiết kế Kiến trúc Tổng thể (HLD)

**Canonical (latest):** `{planning_artifacts}/architecture_design.md`
**Archive (v{N_next}):** `{planning_artifacts}/archive/architecture_design_v{N_next}.md`

**Tóm tắt:**
- Section 1: {N} thuật ngữ, {N} tài liệu tham khảo
- Section 2: {N} NFR được xác định
- Section 3: {N} Containers, {N} nodes luồng Inbound, {N} nodes luồng Query
- Section 4: {N} Epics được mapping vào folder structure
- Section 5: {N} cơ chế ATTT, Caching TTL = {X}h
- Section 6 (ADR): {N} quyết định kiến trúc được ghi lại

**Cảnh báo (nếu có):**
- {Danh sách các NFR chưa xác định để người dùng theo dõi}

---
Bạn có muốn điều chỉnh phần nào hoặc bắt đầu tạo Tech Spec tiếp theo không?
```

---

## ĐIỀU KIỆN HOÀN THÀNH (Done Criteria)

- [ ] QA Checklist tất cả sections PASS.
- [ ] ADR có ít nhất 3 entries.
- [ ] Canonical `{planning_artifacts}/architecture_design.md` đã ghi (overwrite latest).
- [ ] Archive `{planning_artifacts}/archive/architecture_design_v{N_next}.md` đã tạo.
- [ ] Module 0 đã được cascade re-run (Step 06) nếu HLD content đã thay đổi.
- [ ] Tóm tắt kết quả đã được hiển thị cho người dùng.
- [ ] File `architecture_design_parts/` intermediate có thể được giữ lại để audit sau.

**🎉 KẾT THÚC WORKFLOW — Architecture Design hoàn thành.**
