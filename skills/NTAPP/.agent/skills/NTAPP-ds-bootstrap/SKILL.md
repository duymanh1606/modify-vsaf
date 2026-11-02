---
name: ntapp-ds-bootstrap
description: 'Bootstrap Master Design System từ FE repo code. Detect stack, extract raw style, discover components, normalize theo best-practices, optional reconcile với external tokens (Figma/AI). Chạy 1 lần khi onboard project hoặc khi overhaul DS. Stage 0 trong NTAPP Phase 1.'
---

# NTAPP DS Bootstrap Skill

Khởi tạo Master Design System cho repo: scan code, extract token + component, normalize, propose. Output `master_token.json`, `components_metadata.json`, `stack-profile.json`, `bootstrap_report.md`.

Hỗ trợ optional 3-way diff với external tokens (NTAPP v1 hoặc W3C format) — DSO cung cấp path khi gõ slash command.

## Workflow

Follow the instructions in [workflow.md](./workflow.md).
