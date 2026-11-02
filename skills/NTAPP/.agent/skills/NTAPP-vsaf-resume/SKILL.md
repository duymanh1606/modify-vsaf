---
name: NTAPP-vsaf-resume
description: 'Resume một VSAF workflow bị gián đoạn (crash, HITL gate, hoặc interrupted). Usage: /NTAPP-vsaf-resume <runId>. Dùng sau khi HITL gate (human đã ký approved_by) hoặc sau khi workflow bị crash/kill. Engine replay lại từ checkpoint WAL.'
---

# VSAF Resume

Resume workflow bị gián đoạn từ WAL checkpoint.

## Instructions

1. **runId** = lấy từ user input (chuỗi dạng `run_xxxxxxxx` hoặc tương tự)
2. **projectPath** = thư mục gốc project hiện tại

Gọi `mcp__vsaf__vsaf_resume`:
```
runId:       <runId>
projectPath: <projectPath>
```

Sau khi resume thành công, tiếp tục xử lý các node được trả về theo đúng protocol trong
[`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 3 trở đi.

Thông báo cho user: `↩ Resume workflow [runId: <runId>]`
