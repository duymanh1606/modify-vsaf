---
name: NTAPP-vsaf-reproduce-architecture
description: 'Chạy workflow NTAPP/reproduce_architecture qua VSAF engine. Stage 2: dựng lại kiến trúc as-is từ CODE hiện tại (brownfield) — system-overview baseline + HLD + Module 0 + WBS lock; dừng ở HITL gate chờ SA ký approved_by. Usage: /NTAPP-vsaf-reproduce-architecture [--args "--skip-qa --force --repos a,b,c"]. Tiền điều kiện: ≥1 code repo trong workspace + project_wbs.md chưa lock — KHÔNG cần PRD/Epics (reproduce mô tả hệ thống đang chạy, không phải intent tương lai). Sau approved → /NTAPP-vsaf-slice-planning (phát triển mới).'
---

# VSAF Reproduce Architecture

Chạy `NTAPP/reproduce_architecture` qua VSAF engine (Stage 2 — tái dựng kiến trúc as-is từ code).

## Instructions

1. **workflow** = `NTAPP/reproduce_architecture`
2. **args** = chuỗi flag người dùng truyền sau lệnh, hoặc `""` (mặc định không cần args). Flag hợp lệ, forward nguyên xuống node:
   - `--skip-qa` — bỏ Q&A loop của `NTAPP-system-overview` (chạy headless; SA review gate bên trong skill vẫn cần người)
   - `--force` — regen baseline đã có **và** cho phép ghi đè `project_wbs.md` đã lock
   - `--repos a,b,c` / `--workspace-root <path>` — chỉ định code repo khi auto-detect không đúng
3. **projectPath** = thư mục gốc project hiện tại (spec repo)

**Tiền điều kiện — KHÔNG kiểm tra PRD/Epics.** Workflow này đọc **code**, không đọc yêu cầu: PRD/Epics nếu có chỉ là nguồn phụ, và Hook 1 `approval_gate.sh` đã relax đúng nhánh này. Điều kiện thật do node `input-gate` của workflow enforce (fail-fast, exit 1):

| # | Điều kiện | Không thoả → hướng xử lý |
|---|---|---|
| 1 | ≥1 code repo trong workspace root (marker `pom.xml` / `package.json` / `go.mod` / ...) | Mở multi-root workspace / clone code repo cạnh spec repo / `--args "--workspace-root <path>"`. Greenfield chưa có code → `/NTAPP-vsaf-run NTAPP/create_prd_epics` rồi `NTAPP/slice-planning` |
| 2 | `project_wbs.md` chưa có `approved_by:` | Thêm vài unit lẻ → `/ntapp-architecture-design --append`. Cố ý dựng lại toàn bộ → `--args "--force"` |

KHÔNG tự pre-check gì thêm trước khi gọi engine — cứ start workflow, `input-gate` sẽ báo lỗi kèm phương án; relay nguyên message đó cho người dùng nếu node này exit 1.

Thực hiện đúng theo protocol trong [`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 2.

## HITL gate

Khi workflow dừng chờ SA ký: nhắc ký `approved_by:` + `approved_at:` vào `architecture_design.md`, `00_system_connectivity_integration.md`, `project_wbs.md`, sau đó `/NTAPP-vsaf-resume <runId>`.

Khi approved → hướng dẫn bước tiếp:
- Chưa có PRD/Epics mà sắp phát triển mới → `/NTAPP-vsaf-run NTAPP/create_prd_epics` (độc lập, chạy sau được)
- Đã có slice plan → `/NTAPP-vsaf-slice-loop SLICE-01`; chưa có → `/NTAPP-vsaf-run NTAPP/slice-planning` trước
