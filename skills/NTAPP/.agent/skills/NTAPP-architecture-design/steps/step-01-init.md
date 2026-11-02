# STEP 01: INITIALIZATION & CLARIFICATION

> **Acting as:** [Agent E — Master Orchestrator](../agents/agent_e_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication), R9 (Missing Input Handling).

**Input:** Tài liệu PRD, Epics, Project Brief (do người dùng cung cấp)
**Output:** Danh sách câu hỏi làm rõ (nếu thiếu) hoặc xác nhận đủ context để tiến hành

---

Đảm bảo Agent E có đủ thông tin chi tiết (High-Fidelity Context) để khởi động pipeline. Không được phép gom nhóm (bundle) các hệ thống legacy. Phải xác định rõ ranh giới hệ thống ngay từ đầu.


---

## QUY TRÌNH THỰC THI

### 1.1 Tìm kiếm & Đọc tài liệu đầu vào

Agent E phải tự động tìm kiếm trong project folder theo thứ tự ưu tiên (path placeholders resolved từ workflow.md INITIALIZATION cascade):

```
Ưu tiên 1: Tài liệu người dùng khai báo trực tiếp
Ưu tiên 2: {stage_1_discovery}/prd*.md (lấy file có version cao nhất nếu có)
Ưu tiên 3: {stage_1_discovery}/project_brief.md
Ưu tiên 4: {stage_1_discovery}/epics*.md (lấy file có version cao nhất nếu có)
Ưu tiên 5: {stage_1_discovery}/epics/epic-*.md (dạng sharded — output của bmad-shard-doc)
Ưu tiên 6: {stage_1_discovery}/system_overview/_overview.md
           + {stage_1_discovery}/system_overview/{sub_system}.md
           (output mode baseline của /ntapp-system-overview — brownfield / multi-repo)
```

> **Note:** `{stage_1_discovery}` resolved từ `_bmad/bmm/config.yaml` Layer 1. Default = `{project-root}/NTAPP-output/Stage_1_Discovery`. Nếu repo dùng cấu trúc khác, override trong `.bmm-config.yaml` Layer 2.

> **System Overview baseline (Ưu tiên 6) — input brownfield:** Khi `/ntapp-system-overview --mode baseline` đã chạy (vd qua workflow `reproduce_architecture`), output là **evidence as-built** của hệ thống hiện hữu — phải đối xử như **discovered facts**, ưu tiên cao hơn suy luận:
> - `{sub_system}.md` **Section 0 (Service Identity & Auth Profile)** → pre-fill **External Systems** + **Tech Stack** + auth/security zoning (Completeness Check item "External Systems", "Tech Stack", "Compliance").
> - `{sub_system}.md` **Section 6 (Integration — Inbound/Outbound)** → pre-fill ranh giới Container + protocol cho C4 L1/L2 (Step 04.1 §3.1.1–3.1.2).
> - `_overview.md` **Cross-System Contract Match Matrix** → seed contract surface giữa sub-systems cho Module 0 (Step 06). Contract đã evidence-driven → giảm `[TBD]` ở Module 0.
> - **Mọi `<TODO: SA verify — ...>` marker còn sót** trong baseline → KHÔNG tự điền; nâng thành Clarification Question ở 1.2 (R3 Zero-Fabrication, R9 Missing Input). Baseline giảm số câu hỏi nhưng không thay quyền quyết định của user.

**Hành động:** Đọc tất cả tài liệu tìm được và lập **Context Inventory** (Bảng kiểm kê thông tin). Đánh dấu rõ nguồn mỗi mục: `from PRD/Epics` (as-designed intent) vs `from system_overview baseline` (as-built evidence) — khi 2 nguồn mâu thuẫn, **flag cho user reconcile**, KHÔNG tự chọn.

**⚠️ Pre-flight Check (BẮT BUỘC, trước khi sang 1.2):**

Context Inventory **hoàn toàn rỗng** nghĩa là KHÔNG đọc được bất kỳ nguồn nào trong **cả 6 ưu tiên** trên — kể cả Ưu tiên 6 (system_overview baseline). Chỉ khi đó mới DỪNG ngay, **KHÔNG đi tiếp 1.2** (vì sẽ hỏi 10 câu vô nghĩa khi user còn chưa có gì).

> **Brownfield reproduce — TUYỆT ĐỐI KHÔNG HALT vì "thiếu PRD":** đọc được Ưu tiên 6 (system_overview baseline) thì Inventory **KHÔNG rỗng**, dù `prd.md` / `epics.md` / `project_brief.md` đều không tồn tại. Đây là đường chạy chuẩn của workflow `NTAPP/reproduce_architecture` (Stage 2 as-is từ code): baseline as-built là **input chính**, PRD/Epics **không phải tiền điều kiện** (Hook 1 approval-gate cũng đã relax đúng nhánh này). Xử lý: đi tiếp 1.2 bình thường; ghi rõ trong Context Inventory nguồn duy nhất là `from system_overview baseline`; mọi hạng mục Completeness Check còn thiếu → nâng thành clarification question ở 1.3, KHÔNG bịa (R3). WBS sinh ra ở Step 04.1 gán cột Epic dạng `BL:<sub_system>` cho unit as-built thay vì mã `EPIC-xx` không tồn tại.

Hỏi user 1 câu duy nhất theo Iron Rule R9 (Missing Input Handling):

```markdown
❌ Không tìm thấy PRD/Epics/Project Brief, cũng không có system_overview baseline trong project.

Bạn có nguồn nào chưa?
  (a) Đã có tài liệu — vui lòng cung cấp đường dẫn (tuyệt đối hoặc tương đối từ project-root).
  (b) Brownfield (hệ thống đã có code, chưa có tài liệu) — chạy `/ntapp-system-overview` (mode baseline)
      để sinh evidence as-built trước, hoặc chạy cả Stage 2 qua `NTAPP/reproduce_architecture`.
  (c) Greenfield chưa có gì — đề xuất chạy `/bmad-create-prd` trước, sau đó quay lại Step 01.

Tôi sẽ KHÔNG generate content thay thế (bảo vệ Iron Rule R3 + R9).
```

- Option (a) → Agent E đọc file user cung cấp → quay lại Context Inventory → tiếp tục 1.2.
- Option (b) → Agent E DỪNG, ghi log "Cần sinh system_overview baseline trước (brownfield)". Sau khi baseline có, re-trigger Step 01 → Inventory không rỗng → chạy tiếp bình thường, KHÔNG cần PRD.
- Option (c) → Agent E DỪNG, ghi log "User cần tạo PRD trước". Workflow chấm dứt cho đến khi user re-trigger.

### 1.2 Kiểm tra tính đầy đủ (Completeness Check)

Sau khi đọc tài liệu, Agent E kiểm tra các hạng mục sau. Mỗi hạng mục thiếu sẽ tạo ra 1 câu hỏi làm rõ (Clarification Question):

| Hạng mục kiểm tra | Tìm thấy? | Câu hỏi nếu thiếu |
| :--- | :--- | :--- |
| Tên dự án & mục tiêu tổng quát | ✓/✗ | "Dự án này giải quyết vấn đề gì cho ai?" |
| Danh sách Actor chi tiết (High-Fidelity) | ✓/✗ | "Ai là người dùng chính? Vui lòng liệt kê từng role cụ thể (không ghi chung là 'User')." |
| Danh sách External Systems (Un-bundled) | ✓/✗ | "Vui lòng liệt kê tường minh từng hệ thống ngoài (vd: Payment Gateway, Auth Provider, ERP, Notification Service), không ghi chung là 'Core Systems'." |
| Phân vùng mạng dự kiến (DMZ/Internal) | ✓/✗ | "Hệ thống có yêu cầu phân vùng mạng DMZ cho Gateway không?" |
| Số lượng người dùng đồng thời (Concurrent) | ✓/✗ | "Hệ thống cần hỗ trợ bao nhiêu người dùng đồng thời?" |
| Yêu cầu về Latency / Response time | ✓/✗ | "Thời gian phản hồi tối đa là bao nhiêu (ms/s)?" |
| Khối lượng dữ liệu (Data volume & growth) | ✓/✗ | "Ước tính lượng dữ liệu ban đầu và tốc độ tăng trưởng?" |
| Tính chất xử lý (Realtime/Batch) | ✓/✗ | "Luồng xử lý chính là Realtime hay Batch?" |
| Ràng buộc công nghệ (Tech Stack) | ✓/✗ | "Tech stack dự kiến của bạn là gì? (Luôn xác nhận Tech Stack: Backend, Frontend, Database, AI)." |
| Ràng buộc bảo mật / Compliance | ✓/✗ | "Có yêu cầu đặc biệt về bảo mật hoặc compliance (vd: PII Masking) nào không?" |

**Lưu ý:** Nếu người dùng chưa quyết định Tech Stack, Agent E **PHẢI** đề xuất thực hiện `step-03-research.md` để hỗ trợ ra quyết định về lựa chọn kiến trúc & techstack.

**Lưu ý (brownfield — có system_overview baseline):** Các hạng mục **External Systems**, **Tech Stack**, **Compliance/Security** có thể được đánh `✓` nếu đã pre-fill từ baseline (xem §1.1 mapping). KHÔNG hỏi lại câu đã có evidence as-built. Vẫn hỏi nếu baseline để `<TODO: SA verify>` hoặc nếu hạng mục đó là **intent tương lai** (greenfield extension) mà baseline chưa cover.


### 1.3 Xử lý kết quả kiểm tra

**Trường hợp A — Thiếu 1+ hạng mục:**
- Tổng hợp TẤT CẢ câu hỏi còn thiếu vào một danh sách duy nhất.
- Hiển thị cho người dùng theo định dạng:

```markdown
## 🔍 CLARIFICATION REQUIRED - Trước khi thiết kế kiến trúc

Tôi đã đọc tài liệu PRD và Epics. Để đảm bảo thiết kế kiến trúc chính xác, tôi cần làm rõ {N} điểm sau:

**[Q1]** {Câu hỏi 1}
**[Q2]** {Câu hỏi 2}
...

Vui lòng trả lời tất cả câu hỏi trên để tôi có thể bắt đầu thiết kế.

**💡 Tip:** Nếu bạn chưa chắc chắn về Tech Stack, hãy cho tôi biết. Tôi có thể thực hiện **Research (Step 03)** để so sánh các lựa chọn và đưa ra đề xuất tối ưu dựa trên NFR của bạn.
```

- **DỪNG HOÀN TOÀN** và chờ người dùng phản hồi. KHÔNG tự suy đoán.

**Trường hợp B — Đủ thông tin:**
- Lập **Context Summary** (Bảng tóm tắt context đã thu thập) và hiển thị cho người dùng xác nhận.
- **BẮT BUỘC:** Highlight phần **Tech Stack** thành một mục riêng biệt và yêu cầu người dùng xác nhận lại một lần nữa trước khi đi tiếp.
- Sau khi người dùng confirm, chuyển sang **Step 02**.

## Tạo thư mục intermediate

Sử dụng biến `intermediate_folder` đã resolve từ workflow.md INITIALIZATION (cascade resolver) — tự động `= {planning_artifacts}/architecture_design_parts/`.

- Agent E: `mkdir -p {intermediate_folder}` (idempotent — đã tồn tại thì skip).
- Nếu `intermediate_folder` chưa được resolve (cascade Layer 1+2 đều miss) → Layer 3 đã trigger Pause & Wait ở workflow.md. Agent E **KHÔNG tự đoán path** ở step này.

---

## ĐIỀU KIỆN TIẾP TỤC (Exit Criteria)

- [ ] Tất cả hạng mục trong Completeness Check đều có thông tin.
- [ ] Người dùng đã xác nhận Context Summary.
- [ ] Người dùng đã **PHÊ DUYỆT** Tech Stack cụ thể (hoặc đã đồng ý chuyển sang Step 03 để research).
- [ ] Thư mục `architecture_design_parts/` đã được tạo.

---

## ⛔ [GATE — INTAKE] (cổng người dùng, đặt TRƯỚC Next)

Chỉ đọc step kế SAU KHI Exit Criteria trên thỏa: người dùng đã xác nhận **Context Summary** và đã **PHÊ DUYỆT Tech Stack** cụ thể (hoặc đồng ý sang Step 03 để research) — §1.3 Trường hợp B. Nếu còn thiếu hạng mục (Trường hợp A) → **DỪNG HOÀN TOÀN**, chờ người dùng, KHÔNG tự suy đoán và KHÔNG đọc step-02.

**Next:** Read fully and follow `./step-02-strategy.md`
