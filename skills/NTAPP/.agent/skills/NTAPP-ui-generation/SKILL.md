---
name: ntapp-ui-generation
description: 'Sinh UI Semantic Schema từ L3 Detailed Design cho FE unit (screen hoặc widget). Audit Design System delta theo thủ tục reuse-first (pattern-matcher scoring toàn inventory + reuse ladder recipe→atom→primitive), đề xuất NEW/MODIFIED token + component kèm [REUSE AUDIT] + contrast pre-check (WCAG_CONTRAST_FAIL producer), kiểm L3↔L2 contract drift, capture visual_intent, aesthetic self-critique mặc định ON (visual-lint 7 trục deterministic, opt-out), output `ui_schema_{id}.json`. Chỉ chạy với `screen_id` / `widget_id` — BE `feature_id` skip Stage 4b hoàn toàn.'
---

# UI Generation Skill

Skill tự động hóa transition từ L3 Detailed Design sang actionable UI Schema, đảm bảo consistency với Master Design System và technical contracts. Tùy chọn thêm tầng **aesthetic self-critique** (Step 4) — đưa ra + kiểm chứng quyết định thẩm mỹ deterministic (visual-lint 7 trục trên token đã resolve) TRƯỚC khi bàn giao Stage 5, cắt vòng lặp "render xấu → sửa tay".

**Scope:** FE-only (Stage 4b). Đầu vào nhận `screen_id` hoặc `widget_id`. Nếu nhận `feature_id` (BE) → skill dừng và hướng dẫn đi thẳng Stage 4c.

**Aesthetic critique (default ON, opt-out):** Step 4 gated bởi feature-flag `aesthetic_critique` (default **ON** — A5 contrast là a11y hard floor). Tắt per-run (`aesthetic_critique=off`) hoặc qua `.bmm-config.yaml` (không khuyến nghị). Spec-repo-pure, deterministic (rule-based lint, loop cap N=3, no pixel render), mọi quyết định resolve về token reference. Rubric SSoT: `{design_system_root}/_shared/aesthetic-rubric.md` (resolve qua `.bmm-config.yaml`; default `{spec_repo_root}/NTAPP-output/design-system`).

## Workflow

Theo instructions trong [workflow.md](./workflow.md).
