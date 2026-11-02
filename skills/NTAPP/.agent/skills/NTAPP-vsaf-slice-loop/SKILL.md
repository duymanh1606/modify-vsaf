---
name: NTAPP-vsaf-slice-loop
description: 'Chạy workflow NTAPP/slice-loop cho một slice cụ thể. Usage: /NTAPP-vsaf-slice-loop <slice_id>. Ví dụ: /NTAPP-vsaf-slice-loop SLICE-01. Build 1 slice end-to-end: techspec → UX → DD → ui-schema → DS-build → story → ATDD → dev → commit → demo. Dùng khi người dùng nói "build slice", "chạy slice-loop", "bắt đầu SLICE-NN". Tiền điều kiện: WBS + slice plan đã approved.'
---

# VSAF Slice Loop

Chạy `NTAPP/slice-loop` cho slice được chỉ định (Stage 3 → 4 → 5, workflow chính Lane B).

## Instructions

1. **workflow** = `NTAPP/slice-loop`
2. **args** = `slice_id` lấy từ user input (ví dụ `SLICE-01`)
3. **projectPath** = thư mục gốc project hiện tại

Thực hiện đúng theo protocol trong [`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 2.

## Sau khi hoàn tất

- Nếu dừng ở HITL demo gate: nhắc cập nhật `demo_status: passed` trong `NTAPP-output/Stage_2_Architecture/slices/<slice_id>.md`.
- Sau khi tất cả slice `demo_status: passed` → hướng dẫn `/NTAPP-vsaf-staging-deploy <release_id>`.
