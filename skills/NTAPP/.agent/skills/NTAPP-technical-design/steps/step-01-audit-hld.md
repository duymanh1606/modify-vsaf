# STEP 01: AUDIT ARCHITECTURE DESIGN (L1) & WBS SSOT

> **Acting as:** [Agent 0 — Orchestrator](../agents/agent_0_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication), R7 (Stopping Errors), R8 (Contract Lock), R9 (Missing Input Handling), R10 (Inheritance Compliance).

## 1. Mục tiêu
Đảm bảo tài liệu Layer 2 được xây dựng dựa trên một nền tảng kiến trúc Layer 1 vững chắc và thống nhất.

## 2. Pre-flight Check (BẮT BUỘC, theo R9)

Trước khi đọc input, Agent 0 PHẢI verify 3 file dependency tồn tại trong `{planning_artifacts}/`:

- [ ] **HLD canonical:** `architecture_design.md` (file flat — latest từ Stage 2 dual-write).
- [ ] **WBS SSoT:** `project_wbs.md`
- [ ] **Module 0 canonical:** `00_system_connectivity_integration.md` (file flat — latest, đã sync với HLD).

**Nếu BẤT KỲ file nào missing/unreadable** → DỪNG ngay (theo R9), KHÔNG generate placeholder. Hỏi user explicit:

```markdown
❌ Pre-flight FAILED — thiếu input cần cho Layer 2 TechSpec:
  - [ ] {liệt kê file thiếu}

Trước khi tiếp tục, vui lòng:
  (a) Cung cấp đường dẫn đến các file thiếu, HOẶC
  (b) Chạy `/ntapp-architecture-design` trước để tạo HLD + Module 0 + WBS,
      sau đó quay lại Step 01.

Tôi sẽ KHÔNG generate content thay thế (R3 + R9).
```

## 3. Chỉ thị thực thi

1. **Đọc Architecture Design (L1):** Load `{planning_artifacts}/architecture_design.md` (canonical latest). Trích xuất Section 3.1.2 Container Diagram + Section 3.2.x cho module đang thiết kế (`module_name`).

2. **Kiểm tra WBS SSoT:** Đọc `{planning_artifacts}/project_wbs.md`. Lọc danh sách đơn vị work thuộc module đang thiết kế.

2.1. **Scope Audit per `module_type` (theo Manual §3a scope rule):**
    - Classify ID prefix của các đơn vị thuộc module:
      - `BE-*` hoặc `{MODULE_PREFIX}-NN` → expect `module_type` = `backend-service` hoặc `infrastructure`
      - `SCR-*` + `WGT-*` → expect `module_type` = `frontend-app`
      - `INT-*` → expect `module_type` = `integration-contract`
    - Verify TẤT CẢ đơn vị work của module match cùng 1 module_type với giá trị đã resolve ở [workflow Bước 2](../workflow.md). Nếu mixed prefix (vd module BE có lẫn `SCR-*`) → DỪNG (theo R7 Stopping Error), báo cho user theo format:

      ```markdown
      ❌ Module `{module_name}` vi phạm scope rule (Manual §3a):
        - module_type khai báo: `{module_type}`
        - Nhưng có đơn vị work prefix lạc: `{list ID lạc}`

      Cách fix: quay lại Stage 2 (`/ntapp-architecture-design`) re-audit WBS,
      tách đơn vị work lạc sang module đúng type.
      ```

3. **Đọc Module 0 (Integration Map):** Load `{planning_artifacts}/00_system_connectivity_integration.md` (canonical latest, đã sync với HLD). Trích xuất Connectivity Matrix + Sequence Diagram liên quan module này. **LƯU Ý (R8):** Module 0 là Contract Lock — read-only trong skill này.

4. **Audit Architecture & Connectivity:**
    - Kiểm tra sơ đồ C4 trong L1 để xác định ranh giới Container của module.
    - Đối soát các điểm chạm trong L1 với các Contract ID tương ứng trong Module 0.

4.1. **Stateful Entity Determination (input cho Section 7):** Từ ERD/entity trong Module 0 + PRD, xác định module có entity nào persist một field status/lifecycle thật không.
    - **Có** → liệt kê entity + tập state hợp lệ trích từ source (vd `Order: DRAFT/SUBMITTED/APPROVED`) để Agent 2 dùng làm nguồn duy nhất cho Section 7.
    - **Không** (proxy/transform/query-only/dispatcher) → đánh dấu `module stateless` để Agent 2 khai báo stateless thay vì vẽ diagram.
    - **Cấm suy state từ WBS action** (action ≠ state). Source không định nghĩa lifecycle → ghi `state_source: [TBD]`, KHÔNG bịa (R3).

5. **Inheritance Compliance Audit (theo R10):** So sánh ranh giới module trong HLD và Module 0 với WBS / danh mục tính năng. Đảm bảo:
    - Tác nhân (Participants) xung quanh module phải khớp 100% giữa L1 và Module 0.
    - Protocols và Master Data Schema trong WBS/Tính năng phải tuân thủ tuyệt đối Module 0.

6. **Quyết định:**
    - **Nếu đủ thông tin & Khớp L1 + Module 0** → Chuyển sang Step 02.
    - **Nếu phát hiện Drift L1↔L2 hoặc thiếu Module 0** → DỪNG (theo R7 Stopping Error #2/#3), báo cáo điểm sai lệch + escalate user quay lại Layer 1 fix.

## 4. Đầu ra yêu cầu

- **Bảng Coverage Matrix (WBS ↔ HLD readiness):**
    - Cột: `[WBS ID] | [Feature Name] | [HLD Section Reference] | [HLD Readiness (Yes/No)]`.
    - **BẮT BUỘC:** Nếu bất kỳ ID nào có Readiness = "No" → DỪNG (theo R6 — Coverage Gate FAIL), báo lỗi.
- **Bảng Contract Matching Table:** Trích xuất ranh giới Input/Output từ HLD (L1) và Module 0 để bàn giao Agent 2.
- **Stateful Entity Verdict (cho Section 7):** `stateful` (kèm danh sách entity + tập state hợp lệ từ source) HOẶC `stateless` HOẶC `state_source: [TBD]`. Bàn giao Agent 2 làm input điều kiện cho Section 7.
- Danh sách các tài liệu Layer 1 + Module 0 đã được Agent 0 đọc và đối soát.

---

## [GATE — COVERAGE & DRIFT] ⛔

- **Coverage Gate (R6):** nếu BẤT KỲ WBS ID nào có HLD Readiness = "No" trong Coverage Matrix → DỪNG, báo lỗi, KHÔNG sang step kế.
- **Drift Gate (R7 Stopping #2/#3):** nếu phát hiện Drift L1↔L2 hoặc thiếu Module 0 → DỪNG, escalate user quay lại Layer 1 fix.
- Chỉ khi audit PASS (đủ thông tin + khớp L1 + Module 0) mới được tiếp tục.

**Next:** Read fully and follow `./step-02-strategy-rules.md`
