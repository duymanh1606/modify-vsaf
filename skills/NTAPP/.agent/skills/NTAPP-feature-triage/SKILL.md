---
name: ntapp-feature-triage
description: 'Triage một feature mới TẠI INTAKE — trước Stage 1 Discovery, trước khi viết code/spec — để recommend chính xác MỘT lane workflow + slash command kế tiếp + reasoning. Đọc state hiện tại của project (WBS, Module 0, slice plan, Master DS) + hỏi dev một loạt câu cheap-to-expensive để gather signals, rồi áp decision algorithm 4 lane (Express hotfix / Path B quick-dev / Full per-slice / Ad-hoc per-unit). Lane Ad-hoc có 2 trigger: project PoC scale (≤3 unit toàn bộ) hoặc per-feature contained (1 unit, module cũ, no contract change). Refuse và escalate khi: WBS missing, Module 0 contract change, intent quá mơ hồ, multi-feature batch, new unit/module chưa trong WBS. Optional ghi manifest `.fasttrack/{id}.yaml` làm scope-creep tripwire khi config `scope_creep_guardrail` bật. Sử dụng khi người dùng nói "feature mới", "triage feature", "đi lane nào", "bắt đầu feature", "route feature", "feature intake", "đánh giá workflow cho feature".'
---

# NTAPP Feature Triage (Stage 0.5 — Intake Gate)

Triage feature mới **tại intake** — trước Stage 1 Discovery, trước khi viết code/spec. Output: 1 lane workflow + slash command kế tiếp + reasoning audit.

## Instructions

Read fully and follow: [`./workflow.md`](./workflow.md).
