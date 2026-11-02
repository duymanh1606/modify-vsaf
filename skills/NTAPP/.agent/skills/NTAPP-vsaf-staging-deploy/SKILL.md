---
name: NTAPP-vsaf-staging-deploy
description: 'Chạy workflow NTAPP/staging-deploy qua VSAF engine. Usage: /NTAPP-vsaf-staging-deploy <release_id>. Ví dụ: /NTAPP-vsaf-staging-deploy v1.2. Deploy toàn bộ release lên staging sau khi tất cả slice demo_status: passed; có HITL QA gate; tạo PR sau khi QA approve. Tiền điều kiện: tất cả slice đã passed + build ledger tồn tại.'
---

# VSAF Staging Deploy

Chạy `NTAPP/staging-deploy` qua VSAF engine.

## Instructions

1. **workflow** = `NTAPP/staging-deploy`
2. **args** = `release_id` lấy từ user input (ví dụ `v1.2`)
3. **projectPath** = thư mục gốc project hiện tại

Kiểm tra nhanh tiền điều kiện trước khi start:
- Tất cả file trong `NTAPP-output/Stage_2_Architecture/slices/*.md` có `demo_status: passed`
- Build ledger tồn tại trong `NTAPP-output/Stage_5_Build_Verify/build-ledger/`

Nếu tiền điều kiện chưa đủ → thông báo cho user và dừng.

Nếu đủ → thực hiện đúng theo protocol trong
[`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 2 trở đi.
