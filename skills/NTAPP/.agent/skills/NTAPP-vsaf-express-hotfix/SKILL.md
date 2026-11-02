---
name: NTAPP-vsaf-express-hotfix
description: 'Chạy workflow NTAPP/express-hotfix qua VSAF engine. Usage: /NTAPP-vsaf-express-hotfix <preset> | <intent>. Preset hợp lệ: typo, config, log-level, lint, test-fix. Ví dụ: /NTAPP-vsaf-express-hotfix typo | sửa label nút Submit. Express lane bypass DD — phải compensate trong 48h (full DD + WBS entry + ripple audit), verify thủ công khi review PR. Dùng khi cần hotfix nhanh thuộc 5 preset.'
---

# VSAF Express Hotfix

Chạy `NTAPP/express-hotfix` qua VSAF engine.

## Instructions

1. **workflow** = `NTAPP/express-hotfix`
2. **args** = `"<preset> | <intent>"` lấy từ user input (ví dụ `"typo | sửa label nút Submit"`)
   - Preset hợp lệ: `typo`, `config`, `log-level`, `lint`, `test-fix`
   - Nếu preset không hợp lệ → nhắc user chạy skill `/ntapp-feature-triage "<intent>"` thay thế (skill trực tiếp, không qua VSAF engine)
3. **projectPath** = thư mục gốc project hiện tại

Sau khi xác định 3 giá trị trên, thực hiện đúng theo protocol trong
[`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 2 trở đi.

**Lưu ý sau khi hoàn tất:** nhắc user món nợ 48h — bổ sung **full DD + WBS entry + ripple audit** cho unit vừa hotfix.
Không còn workflow tracker tự động: người review PR phải tự kiểm đủ 3 mục đó trước khi merge.
