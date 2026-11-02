---
name: ntapp-figma-ingest
description: 'Biên dịch một Figma file thành artifact tĩnh deterministic trong spec repo (frame PNG + layout spec JSON + mapping unit↔frame + Figma↔DS map + token gap report) để Stage 4a/4b đọc từ FILE LOCAL, không node nào của slice-loop phải gọi Figma. Chạy NGOÀI slice-loop, ở batch phase sau khi WBS lock. Hai mode: `--tokens-only` (pass 0 — chỉ export Figma Variables/Styles ra W3C JSON làm input cho /ntapp-ds-bootstrap --external-tokens) và full (pass 2 — harvest frame + HITL mapping + spec extract + DS reconcile). Sử dụng khi người dùng nói "ingest figma", "lấy design từ figma", "figma đã vẽ trước", "map figma vào WBS", "đồng bộ figma", "figma ingest", "re-ingest figma".'
---

# NTAPP Figma Ingest Skill (Stage 0.8 — batch, ngoài slice-loop)

Compiler một chiều: **Figma → artifact spec repo**. Mọi consumer downstream (Stage 4a wireframe transcribe, Stage 4b reuse audit, Stage 5 visual reference) đọc file local đã ingest, KHÔNG gọi Figma.

Không sinh wireframe, không sinh `ui_schema`, không quyết reuse, không ghi `master_token.json` — chỉ **harvest → map → normalize → report gap**.

## Workflow

Follow the instructions in [workflow.md](./workflow.md).
