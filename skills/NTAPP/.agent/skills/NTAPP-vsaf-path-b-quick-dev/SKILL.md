---
name: NTAPP-vsaf-path-b-quick-dev
description: 'Chạy workflow NTAPP/path-b-quick-dev qua VSAF engine. Lane 2: bug fix / refactor / chore trên unit cũ — skip Stage 3-4c, không enforce test-first. Usage: /NTAPP-vsaf-path-b-quick-dev <unit_id> | <intent>. Ví dụ: /NTAPP-vsaf-path-b-quick-dev SCR-COMPOSE | fix lỗi gửi ảnh. Tiền điều kiện: unit_id có trong WBS + DD tồn tại. Dùng khi feature-triage recommend lane-2-quick-dev.'
---

# VSAF Path B Quick Dev

Chạy `NTAPP/path-b-quick-dev` qua VSAF engine (Lane 2 — bug fix / refactor / chore).

## Instructions

1. **workflow** = `NTAPP/path-b-quick-dev`
2. **args** = `"<unit_id> | <intent>"` lấy từ user input (ví dụ `"SCR-COMPOSE | fix lỗi gửi ảnh"`)
3. **projectPath** = thư mục gốc project hiện tại

Thực hiện đúng theo protocol trong [`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 2.

## Sau khi hoàn tất

Output là local commit. Deploy staging sau khi tất cả work ready → `/NTAPP-vsaf-staging-deploy <release_id>`.
