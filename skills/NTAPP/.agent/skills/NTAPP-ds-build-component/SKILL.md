---
name: ntapp-ds-build-component
description: 'Apply một delta proposal (NEW/MODIFIED tokens & components) vào codebase: scaffold component mới (bao gồm layout-primitive adapters theo stack-profile.layout_library), patch component cũ, update master_token canonical (spec repo) + export runtime token file (code repo, theo stack-profile), dual-write archive. Hard gate TRONG Stage 4b — chạy SAU /ntapp-ui-generation khi proposed_ds_updates.md (cho `screen_id` / `widget_id`) có [NEW] non-empty, trước khi merge feature code.'
---

# NTAPP DS Build Component Skill

Consumer của contract `_shared/proposal-schema.md`. Producer thường là Stage 4b Agent 1 (`/ntapp-ui-generation`), hoặc dev viết tay (manual mode).

**Scope:** FE-only — chỉ xử lý delta từ `screen_id` / `widget_id`. BE `feature_id` không có Master DS delta, skill skip.

6-step pipeline: validate proposal → warning gate → apply tokens (master_token.json, spec repo) → **export runtime tokens (code repo, theo stack-profile format)** → apply components (NEW trước, MODIFIED sau; layout-primitive components dispatch qua adapter theo `stack-profile.layout_library.strategy` — native/utility/generated/raw) → archive + report.

## Workflow

Theo instructions trong [workflow.md](./workflow.md).
