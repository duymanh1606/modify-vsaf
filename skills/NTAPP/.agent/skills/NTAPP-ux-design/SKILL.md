---
name: ntapp-ux-design
description: 'Execute the multi-agent UX Design workflow to produce TWO separated artifacts: (1) ux_design.md — slim UX Journey Specification per feature-batch (workflow archetype + information model, IA/navigation DELTA, journey flows as Mermaid + journey screen tables, PRD traceability — NO per-screen Screen Specs, those are owned by feature-design Stage 4a; NO §17 inventory, WBS is SSoT; personas referenced only — actor lock HLD §3.1.1, detail from ux-sketch if present else PRD); (2) ux_conventions.md — PROJECT-SINGLETON living conventions doc (UX principles, content strategy + status labels 1-1 Module 0 §7, interaction patterns, notification matrix, error handling, responsive & a11y, audit-log rules) written once then delta-updated. APPLICABILITY: chạy MỘT lần (batch, sau slice-planning, trước vòng per-slice) cho TOÀN BỘ feature — union mọi SCR/WGT trải qua nhiều slice — KHÔNG per-slice. Chỉ áp dụng ở Lane 3 cho feature multi-screen MỚI (≥2 màn SCR-* nối journey, hoặc actor/flow mới). SKIP cho feature reuse-journey / single-screen / BE-only và mọi lane khác — feature-design Stage 4a kế thừa Journey Spec + Conventions đã có / HLD §3.2. Entry gate ở step-01 §2.0 là SSoT.'
---

# NTAPP UX Design Skill (Stage 3b — Journey Spec + Project Conventions)

This skill runs a multi-agent orchestrated process (UX0/UX2/UX3/UX4) producing **two separated artifacts**:

| Artifact | Scope | Content |
|:---------|:------|:--------|
| **`ux_design.md`** — UX Journey Specification | Per feature-batch (slim, ~2 pages) | §1 Executive summary + persona references · §2 Workflow archetype & information model · §3 IA & navigation **delta** · §4 User journeys (Mermaid + journey screen table — 1 line/screen) · §5 PRD→UX mapping |
| **`ux_conventions.md`** — Project UX Conventions | PROJECT SINGLETON (living doc, delta-updated) | C1 principles · C2 content strategy + status labels · C3 interaction patterns · C4 notifications · C5 error handling · C6 responsive & a11y · C7 audit-log rules |

**What this skill deliberately does NOT produce** (v4.0 separation of ownership):
- Per-screen Screen Specs → owner: `feature-design` Stage 4a §2 (single wireframe owner — no drift).
- Screen & Widget inventory (§17 cũ) → SSoT: `project_wbs.md` (gates check WBS directly).
- Detailed personas → §1.3 chỉ reference theo fallback chain: actor identity lock theo **HLD §3.1.1** (bắt buộc — luôn tồn tại); chi tiết từ `ux_sketch.md` (Stage 1, **optional**) nếu có, không có → pointer `PRD §User Stories`. KHÔNG hard-depend vào sketch.

## Agent Squad

| Agent | Role | BMAD Persona |
|:------|:-----|:-------------|
| **UX0** | UX Lead & Orchestrator | Sally (bmad-agent-ux-designer) |
| **UX2** | PM Liaison | John (bmad-agent-pm) |
| **UX3** | IA & System Architect | Winston (bmad-agent-architect) |
| **UX4** | Content Strategist | Paige (bmad-agent-tech-writer) |

## Instructions

Read fully and follow: `./workflow.md`
