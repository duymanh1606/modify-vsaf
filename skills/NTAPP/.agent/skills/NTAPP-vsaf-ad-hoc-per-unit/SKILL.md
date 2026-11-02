---
name: NTAPP-vsaf-ad-hoc-per-unit
description: 'Chạy workflow NTAPP/ad-hoc-per-unit qua VSAF engine. Lane 4: per-unit loop bỏ qua Stage 2b (không cần slice plan) — dùng cho PoC ≤ 3 unit hoặc unit độc lập. Usage: /NTAPP-vsaf-ad-hoc-per-unit <intent | file-path | unit_id>. Nhận thẳng intent từ feature-triage (KHÔNG bắt buộc unit_id sẵn trong WBS — node architecture-design append-mode tự tạo). Dùng khi feature-triage recommend lane-4-ad-hoc.'
---

# VSAF Ad-hoc Per Unit

Chạy `NTAPP/ad-hoc-per-unit` qua VSAF engine (Lane 4 — per-unit, skip Stage 2b).

12 node: `architecture-design → dd → ui-schema → ds-delta-decision → ds-build → story-bridge → atdd-classify → framework-setup → atdd-tests → dev → code-review → demo-unit`.

## Instructions

1. **workflow** = `NTAPP/ad-hoc-per-unit`
2. **args** = input từ user, 1 trong 3 dạng (node `architecture-design` tự phân loại + resolve):
   - **intent free-text** — mô tả yêu cầu trực tiếp từ feature-triage lane-4 (chưa có unit_id)
   - **đường dẫn file** — path tới decision file / triage output / PRD snippet (`*.md/.yaml/.json`)
   - **unit_id có sẵn** — vd `WGT-AVATAR` (đã biết từ WBS cũ)
3. **projectPath** = thư mục gốc project hiện tại

Không bắt buộc unit_id có sẵn trong WBS: `architecture-design` append-mode resolve intent → tạo entry WBS mới (append-only, giữ nguyên HLD / Module 0 / unit cũ).

Thực hiện đúng theo protocol trong [`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 2.

## Sau khi hoàn tất

- **Close point** = node `demo-unit` (HITL demo với SeniorDev/PM/PO; flip `demo_status: passed` trong story file). Output: local commit.
- **Single-unit / lần chạy.** Nếu intent resolve ra nhiều unit → unit phụ ghi vào `NTAPP-output/.pending-units`; `demo-unit` nhắc chạy lại `/NTAPP-vsaf-ad-hoc-per-unit <unit_id>` cho từng unit còn lại (tuần tự).
- `code-review` ghi knowledge per-unit (`NTAPP-output/ledgers/knowledge/<unit_id>.md`) — audit/retro snapshot, write-only (không feed sang unit kế).
- Deploy staging sau khi mọi unit xong → `/NTAPP-vsaf-staging-deploy <release_id>`.
