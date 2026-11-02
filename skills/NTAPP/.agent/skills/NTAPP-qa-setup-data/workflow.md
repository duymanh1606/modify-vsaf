# WORKFLOW: NTAPP QA SETUP TEST DATA

Luồng công việc này điều phối quá trình **chuẩn bị môi trường & dữ liệu kiểm thử** (Test Data Setup): đọc kịch bản manual testcase chuẩn 10 cột đã chốt → bóc tách dữ liệu mồi (test data seed) → sinh cơ chế Setup (pre-condition) + Teardown (post-condition) đảm bảo môi trường độc lập và sạch sẽ (Clean State) trước khi đưa vào chạy Automation.

## Goal

Đảm bảo môi trường kiểm thử ở trạng thái độc lập, có dữ liệu mồi sẵn sàng và có cơ chế dọn dẹp tự động. Dữ liệu mồi phải đảm bảo **tính duy nhất** (dùng timestamp/UUID) để tránh Duplicate Entry khi chạy nhiều lần; Teardown phải xóa toàn bộ rác data sau mỗi đợt test.

**Reuse-first (Get-Or-Create):** TRƯỚC khi sinh dữ liệu mới, PHẢI kiểm tra dữ liệu automation đã tồn tại — truy vấn **5 bản ghi gần nhất mang hậu tố `auto`** (marker automation-owned) và đối chiếu **trạng thái + thuộc tính** với điều kiện đầu vào (precondition). Nếu có bản ghi thỏa mãn → **tái sử dụng** (không tạo mới); nếu không có bản nào trong 5 bản thỏa mãn → **tạo mới ngay** (không hỏi thêm, cho đỡ mất thời gian). Cơ chế này giúp Setup idempotent và tiết kiệm thời gian mỗi lần chạy.

## Your Role

Bạn đóng vai [Agent Robot Generator](./agents/agent_robot_generator.md) — Senior Automation Engineer. Trong skill này, persona chỉ thực thi phần **Test Data lifecycle**: trích xuất chính xác dữ liệu từ cột "Data Test" / "Precondition" của manual testcase, tuyệt đối không tự ý giả định (fabricate) dữ liệu.

## Compliance

Skill này SIMPLE (không có `principles/iron_rules.md`). Khi sinh script Setup/Teardown PHẢI tuân thủ các reference đã bundle trong `./references/`:

- **Zero-Fabrication:** Chỉ dùng dữ liệu kế thừa từ manual testcase / phần Dữ liệu trong `_detailed_design`; thiếu thì để rỗng hoặc đánh `[TBD]` — KHÔNG tự chế mock data (xem `./references/auto_robot_rules.md` §4 Anti-Patterns, §2 Test Data Management).
- **Isolation:** Dữ liệu định danh duy nhất (email/username/ID) bắt buộc sinh kèm timestamp/UUID (xem `./references/auto_robot_rules.md` §2).
- **Tiền tố `auto_`:** Mọi định danh kiểu chuỗi do automation sinh phải **BẮT ĐẦU** bằng `auto_` (dạng `auto_<nhãn>_{timestamp}`), override qua `AUTO_DATA_PREFIX`. Tiền tố cho phép dọn môi trường bằng đúng một mệnh đề `LIKE 'auto\_%'`. Trường chỉ nhận số (SĐT, mã số thuế) miễn trừ — giữ định dạng số, unique bằng phần số ngẫu nhiên.
- **Reuse-Gate (Get-Or-Create):** Trước khi CREATE, phải sinh bước kiểm tra tái sử dụng — query **5 bản ghi gần nhất có tiền tố `auto_`**, chấm trạng thái/thuộc tính so với precondition. Có bản thỏa → reuse (skip create, KHÔNG teardown bản kế thừa); không có bản thỏa → create ngay + đặt tiền tố `auto_` cho bản mới. Tiền tố chỉ dùng để **khoanh vùng dữ liệu automation-owned** — KHÔNG bao giờ đụng vào dữ liệu thật/manual.
- **Marker-not-fabrication:** Đối chiếu reuse chỉ dựa trên dữ liệu **thực sự query được** lúc runtime — KHÔNG tự giả định bản ghi tồn tại. Nếu không query được → mặc định rẽ nhánh CREATE.
- **Standards facade:** Tổng quan tiêu chuẩn Automation tại `./references/automation_standards.md`.
- **Missing-input handling:** Manual testcase không tồn tại / không readable → DỪNG, hỏi user, KHÔNG sinh mock thay thế.

## ROSTER & ROLES

| Step | Agent | Vai trò | Output |
|---|---|---|---|
| 01 | [Agent Robot Generator](./agents/agent_robot_generator.md) | Test Data & Environment Setup | `{qa_artifacts}/data/{id}_test_data_setup.md` (+ optional `.sql`) |

## KIẾN TRÚC WORKFLOW

```
USER (manual testcase đã chốt + id)
   │
   ▼
[Step 01] Setup Test Data ──► {qa_artifacts}/data/
   • Data Extraction (cột Data Test / Precondition)
   • Reuse-Gate: query 5 bản ghi tiền tố `auto_` gần nhất → khớp precondition?
       ├─ Có  → REUSE (skip create)
       └─ Không → CREATE mới + đặt tiền tố `auto_`
   • Setup script (pre-condition) — Get-Or-Create, isolation timestamp/UUID
   • Teardown script (post-condition) — clean state (chỉ xóa bản do run tạo)
   │
   ▼
USER (script Setup/Teardown sẵn sàng cho Automation)
```

## INITIALIZATION (Configuration Resolution)

Trước khi chạy bất kỳ step nào, resolve config theo cascade 3 layer (cao → thấp).

### Bước 0 — Resolve `{project-root}`
Walk up từ `cwd` tìm marker: thấy `_bmad/` → project-root; else thấy `.git/` → project-root; else fallback `cwd` + log warning.

### Layer 1 — BMad project config
Đọc `{project-root}/_bmad/bmm/config.yaml` nếu có. Lookup: `project_name`, `stage_5_build_verify`. Thay placeholder `{project-root}` bằng absolute path đã resolve.

### Layer 2 — Skill family config (override)
Đọc `{project-root}/.bmm-config.yaml`, tìm section `ntapp-qa-setup-data:`. Override Layer 1 nếu có.
```yaml
ntapp-qa-setup-data:
  qa_artifacts: <path>     # optional, override default
```

### Layer 3 — Default + Interactive (fallback)
Nếu `qa_artifacts` chưa resolve được: default = `{stage_5_build_verify}/test`
(tức `{project-root}/NTAPP-output/Stage_5_Build_Verify/test`). Nếu cả `stage_5_build_verify` cũng miss → DỪNG, hỏi user path, rồi ghi vào `.bmm-config.yaml` section `ntapp-qa-setup-data:`.

### Biến runtime
| Biến | Nguồn | Ghi chú |
|---|---|---|
| `project_name` | Layer 1/2/3 | Header tài liệu |
| `qa_artifacts` | Layer 1/2/3 | Root output QA (= `{stage_5_build_verify}/test`) |
| `id` / `slice_id` | User input | Đơn vị/slice cần xử lý |
| `template_path` | Hardcode | `./templates/...` — relative to **skill root** |
| `agent_personas_path` | Hardcode | `./agents/` — relative skill root |
| `date` | System | ISO 8601 |

## Output Naming

Canonical-only — ghi đè mỗi run, KHÔNG dual-write, KHÔNG archive, KHÔNG `_v{N}`.

| Output | Path |
|---|---|
| Test data setup doc | `{qa_artifacts}/data/{id}_test_data_setup.md` |
| Test data SQL (optional) | `{qa_artifacts}/data/{id}_test_data.sql` |

## EXECUTION

Thực hiện tuần tự:

1. **[Step 01: Setup Test Data](./steps/step-01-setup-test-data.md)** → `{qa_artifacts}/data/{id}_test_data_setup.md`.
