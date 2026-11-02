# WORKFLOW: NTAPP TECHNICAL DESIGN (LAYER 2)

Luồng công việc này điều phối đội ngũ **NTAPP Technical Design Squad** để xây dựng tài liệu thiết kế kỹ thuật phân hệ (TechSpec - Layer 2), đảm bảo tính kế thừa từ kiến trúc tổng thể (Architecture Design Layer 1) và thiết lập các tiêu chuẩn thực thi cho toàn bộ Module.

**Iron Rules:** Toàn workflow tuân thủ [principles/iron_rules.md](./principles/iron_rules.md). Agent 0 PHẢI đọc file này trước khi thực thi bất kỳ step nào.

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này CHỈ giữ KHUNG điều phối (sơ đồ + INITIALIZATION + global rules + pipeline map + LAUNCH). Chi tiết thực thi của mỗi step nằm TRONG chính step file đó (`./steps/step-0N-*.md`).
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi cổng `[GATE]`/PAUSE) RỒI mới đọc step kế theo con trỏ `**Next:**` ở cuối step. KHÔNG đọc trước nhiều step. State chuyển tiếp qua `.ts_parts` files + biến runtime, KHÔNG qua việc giữ instruction nhiều step trong context.

## 1. ROSTER & ROLES (Đội hình & vai trò)

| Agent | Role | Steps Owned | Output (Mục → part) |
|---|---|---|---|
| **0** | Orchestrator + QA Gatekeeper | 01, 05 | Audit scope vs Module 0 (01) → Sequential Assembly canonical + archive `v{N}` (05) |
| **1** | Business Strategist | 02 | part_1_strategy.md (Mục 1, 2, 3, 6.1 Swimlane) |
| **2** | System Architect | 03 | part_2_modeling.md (Mục 4, 5 WBS, 6.2 Sequence, 6.3 Logic, 7 State Machine) |
| **3** | Implementation Lead | 04 | part_3_implementation.md (Mục 8, 9, 10, 11, 12) |

Luồng: User cấp PRD/Epic + Architecture Design (L1) → **A0** load HLD + Module 0 (đã pre-created ở L1) và audit local scope vs Master Contracts (Step 01) → **A1/A2/A3** lần lượt ghi part vào `.ts_parts` (Step 02-04) → **A0** Sequential Assembly Pass 1-6 + Quantitative Audit (Stop if mismatch) → Final High-Fidelity TechSpec canonical + archive `v{N}` (Step 05). Chi tiết section↔part: §4; protocol lắp ráp Pass 1-6: step-05.

## 2. INITIALIZATION (Configuration Resolution)

Trước khi chạy bất kỳ step nào, Agent 0 PHẢI resolve config theo cascade 3 layer (ưu tiên cao → thấp).

### Bước 0 — Resolve `{project-root}`

Walk up từ `cwd` tìm marker folder:
1. Nếu thấy `_bmad/` → đó là `{project-root}`.
2. Nếu thấy `.git/` → đó là `{project-root}`.
3. Nếu lên đến `/` không thấy gì → fallback `cwd` + log warning: "⚠️ Không tìm thấy marker (`_bmad/` hoặc `.git/`), dùng cwd làm project-root".

### Layer 1 — BMad project config

Đọc `{project-root}/_bmad/bmm/config.yaml` nếu tồn tại. Lookup keys:
- `project_name`
- `planning_artifacts`

BMad dùng placeholder `{project-root}` trong values → Agent 0 thay bằng absolute path đã resolve ở Bước 0.

### Layer 2 — Skill family config (override)

Đọc `{project-root}/.bmm-config.yaml` nếu tồn tại. Tìm section `ntapp-technical-design:`. Override giá trị từ Layer 1 nếu có.

Schema mong đợi:
```yaml
ntapp-technical-design:
  project_name: <string>          # optional, override Layer 1
  planning_artifacts: <path>      # optional, override Layer 1
```

### Layer 3 — Default + Interactive (fallback)

Khi cả Layer 1 và Layer 2 đều miss biến cần → DỪNG, hỏi user (Pause & Wait):

```markdown
## ⚙️ SKILL CONFIG MISSING — Setup lần đầu

Tôi không tìm thấy config (`_bmad/bmm/config.yaml` hoặc `.bmm-config.yaml`).
Cần xác định 2 thông tin sau (ENTER để chấp nhận default):

[Q1] **project_name** (default: `{tên folder của project-root}`)?
[Q2] **planning_artifacts** path nơi đặt HLD + Module 0 + WBS
     (default: `{project-root}/output/architecture/`)?

→ Sau khi anh trả lời, tôi sẽ ghi vào `{project-root}/.bmm-config.yaml`
   để lần sau không hỏi lại.
```

### Bước 1 — Hỏi `module_name`

Technical-design là per-module skill. Agent 0 PHẢI hỏi user:

```markdown
**[Q]** Anh muốn thiết kế TechSpec cho module nào?
(`module_name` slug-style, lấy từ WBS — vd: `auth`, `payment`, `notification` ...)
```

`module_name` sẽ dùng để:
- Tạo `intermediate_folder` riêng cho module này.
- Đặt tên output file final.

### Bước 2 — Resolve `module_type` từ WBS

Module type quyết định section nào trong template được fill, section nào skip (theo [Manual §3a scope rule](../../../docs/Process/Manual_phase_1.md) — BE liệt kê features, FE liệt kê screens+widgets, INT liệt kê contracts).

1. Đọc `{planning_artifacts}/project_wbs.md`. Tìm dòng level 1 trong Function Decomposition Tree match pattern `[{PREFIX}] ... ({module_type})` cho module được chọn.
2. Trích xuất `module_type` ∈ {`backend-service`, `frontend-app`, `integration-contract`, `infrastructure`}.
3. **Fallback** — nếu WBS chưa có Mục 0 / Decomposition Tree (WBS legacy) hoặc module không match → DỪNG, hỏi user:

   ```markdown
   ⚠️ Không xác định được `module_type` cho `{module_name}` từ WBS.
   Vui lòng chọn:
     (a) `backend-service` — code server-side, không UI
     (b) `frontend-app` — code UI người dùng (screens + widgets)
     (c) `integration-contract` — schema/protocol giữa 2 module
     (d) `infrastructure` — observability/ops/platform
   ```

`module_type` sẽ dùng để gate các section trong template (§5.2 UI Control / §11 ERD / §12 Interface Contracts).

### Biến runtime cuối cùng

Sau cascade, các biến phải có giá trị:

| Biến | Nguồn | Ghi chú |
|---|---|---|
| `project_name` | Layer 1/2/3 | Tên dự án — hiển thị trong header TechSpec |
| `planning_artifacts` | Layer 1/2/3 | Absolute path nơi đặt HLD/Module 0/WBS làm input |
| `module_name` | User input | Tên module đang thiết kế — slug-style (vd `auth`, `payment`...) |
| `module_type` | WBS lookup hoặc user (fallback) | 1 trong 4: `backend-service` / `frontend-app` / `integration-contract` / `infrastructure` — gate section template |
| `intermediate_folder` | Auto-derive | = `{planning_artifacts}/{module_name}.ts_parts/` |
| `template_path` | Hardcode | `./templates/techspec_v3_ultimate_template.md` — resolve relative to **skill root**, không phải cwd |
| `agent_personas_path` | Hardcode | `./agents/` — relative to skill root |
| `iron_rules_path` | Hardcode | `./principles/iron_rules.md` — relative to skill root |
| `date` | System | Format ISO 8601 `YYYY-MM-DD` (consistent với Module 0 versioning) |

## 3. Quy tắc tuân thủ — Iron Rules

NTAPP Technical Design Squad tuân thủ toàn bộ rule trong [./principles/iron_rules.md](./principles/iron_rules.md). Đặc biệt quan trọng cho Layer 2:

- **R3 — Zero-Fabrication:** Không bịa Container/Contract không có trong L1/Module 0/WBS.
- **R8 — Contract Lock:** Module 0 frozen — không sửa Schema/Protocol từ L2.
- **R9 — Missing Input Handling:** Thiếu HLD/Module 0/WBS thì hỏi user, không hallucinate.
- **R10 — Inheritance Compliance:** Không sửa boundary/container name đã chốt ở L1. Internal decomposition allowed, external touchpoint frozen.

## 4. Quy tắc Lưu trữ Trung gian (.ts_parts folder)

Mọi output của Agent chuyên môn BẮT BUỘC phải được ghi nhận thành từng file riêng biệt trong thư mục trung gian trước khi hợp nhất:
- **Tên thư mục:** `{intermediate_folder}` (= `{planning_artifacts}/{module_name}.ts_parts/`).
- **Cấu trúc file bên trong:**
    - `part_1_strategy.md` (Agent 1): Mục 1, 2, 3, 6.1
    - `part_2_modeling.md` (Agent 2): Mục 4, 5, 6.2, 6.3, 7
    - `part_3_implementation.md` (Agent 3): Mục 8, 9, 10, 11, 12
- **Mục đích:** Lưu lại bản thô (Raw) để User có thể audit lại quy trình làm việc của từng Agent một cách trực quan.
- **Yêu cầu:** Giữ nguyên 100% mọi sơ đồ (Mermaid/ASCII) và mọi bảng biểu trong các file này (theo R2 — Zero-Summarization).

## 5. Output Naming Convention

| Output | Path | Versioning |
|---|---|---|
| Intermediate parts | `{intermediate_folder}/part_{1\|2\|3}_{name}.md` | Không version (overwrite mỗi run) |
| Final TechSpec — canonical | `{planning_artifacts}/{module_name}_techspec.md` | Flat, overwrite mỗi run (latest pointer) |
| Final TechSpec — archive | `{planning_artifacts}/archive/{module_name}_techspec_v{N}.md` | Bump `v1 → v2 → v3...` mỗi run (snapshot history) |

**Ví dụ:** module `auth` (run lần đầu):
- Canonical: `{planning_artifacts}/auth_techspec.md`
- Archive: `{planning_artifacts}/archive/auth_techspec_v1.md`

Re-design lần sau:
- Canonical: `{planning_artifacts}/auth_techspec.md` (overwrite)
- Archive thêm: `{planning_artifacts}/archive/auth_techspec_v2.md`

## 6. PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

Mỗi step là một file độc lập trong `./steps/`, mở đầu bằng `> **Acting as:** [Agent X]` trỏ persona, kết thúc bằng cổng `[GATE]` + pointer `**Next:**` tới step kế (step cuối là TERMINAL).

| # | Step file | Agent | Output chính | Gate |
|---|---|---|---|---|
| 01 | steps/step-01-audit-hld.md                | 0 | Coverage Matrix + Contract Matching Table + Stateful Entity Verdict (audit, chưa ghi part) | intake (§2) + **COVERAGE & DRIFT** (R6/R7) |
| 02 | steps/step-02-strategy-rules.md           | 1 | part_1_strategy.md (Mục 1, 2, 3, 6.1) | **STRATEGY HANDOFF** |
| 03 | steps/step-03-architectural-modeling.md   | 2 | part_2_modeling.md (Mục 4, 5, 6.2, 6.3, 7) | **MODELING HANDOFF** (R3 state grounding) |
| 04 | steps/step-04-implementation-contracts.md | 3 | part_3_implementation.md (Mục 8, 9, 10, 11, 12) | **IMPLEMENTATION HANDOFF** (Acceptance Criteria) |
| 05 | steps/step-05-orchestration-qa.md         | 0 | Canonical + Archive TechSpec (Sequential Assembly Pass 1-6) | **ASSEMBLY AUDIT** Pass 5/6 (TERMINAL) |

Chuỗi: **01 → 02 → 03 → 04 → 05**. step-05 là step **TERMINAL** (không có pointer `**Next:**`).
Cổng intake (config cascade + `module_name` + `module_type`) đã xử lý ở **§2 INITIALIZATION** TRƯỚC khi vào step-01. Mỗi cổng `[GATE]` nằm ngay trên con trỏ `**Next:**` của step nó canh; FAIL → DỪNG/loop về owner, KHÔNG phải pointer `**Next:**`.

## 7. GLOBAL RULES (bất biến — áp dụng mọi step)

- ⛔ Đọc đúng MỘT step file mỗi lần; chỉ đọc step kế khi cổng `[GATE]` của step hiện tại PASS. State chuyển qua `.ts_parts` + biến runtime, không qua việc giữ nhiều step trong context.
- ✅ **R2 — Zero-Summarization:** giữ nguyên 100% mọi sơ đồ (Mermaid/ASCII) và bảng biểu khi ghi part files.
- ✅ **R3 — Zero-Fabrication:** không bịa Container/Contract/state ngoài L1 / Module 0 / WBS.
- ✅ **R8 — Contract Lock:** Module 0 frozen — read-only trong toàn skill.
- ✅ **R10 — Inheritance Compliance:** không sửa boundary/container name đã chốt ở L1.
- Toàn bộ Iron Rules (§3 + [principles/iron_rules.md](./principles/iron_rules.md)) luôn áp dụng cho mọi step.

## 8. LAUNCH

Sau khi **§2 INITIALIZATION** resolve xong toàn bộ biến runtime (đã qua các cổng intake: config cascade, `module_name`, `module_type`) → khởi động pipeline tại step đầu tiên.

**Next:** Read fully and follow `./steps/step-01-audit-hld.md`
