---
name: ntapp-slice-planning
description: 'Gom các work unit trong project_wbs.md thành các vertical slice (tracer bullet) demoable, chạy ở Stage 2b — NGAY SAU khi WBS lock ở Stage 2 và TRƯỚC vòng lặp per-slice Stage 3-4-5. Mỗi slice là một lát cắt mỏng end-to-end tự demo được, group nhiều unit (BE feature + FE screen + contract) mà KHÔNG merge chúng thành một story. Cắt slice theo seam test (ownership / auth-foundation / resilience / in-house-vs-external) để giữ phần in-house AFK và không để một unit external kéo cả slice thành HITL. Slice plan drive on-demand spec (Stage 3-4 chỉ chạy cho unit thuộc slice đang active), thay vì batch toàn WBS upfront. Sử dụng khi người dùng nói "lập slice plan", "chia vertical slice", "slice planning", "gom unit thành lát demoable", "plan demoable increment sau WBS lock".'
---

# NTAPP Slice Planning (Stage 2b)

Lập kế hoạch vertical slice từ `project_wbs.md` — gom work unit thành các lát cắt mỏng demoable, chạy **NGAY SAU Stage 2 (WBS lock)** và **TRƯỚC vòng lặp per-slice Stage 3-4-5**. Output: `SLICE-*.md` manifest ở spec repo `Stage_2_Architecture/slices/` (cùng folder với `project_wbs.md`, vì slice là extension của WBS) — drive on-demand spec cho từng slice, không batch toàn WBS.

## Instructions

Read fully and follow: [`./workflow.md`](./workflow.md).
