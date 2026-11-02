---
name: ntapp-ux-sketch
description: 'Tạo bản phác thảo UX nhẹ (Personas + Rough IA + Primary Journey + Screen Intent Table) sau khi có PRD/Epics nhưng trước khi triển khai HLD, kèm preview HTML HI-FI review được trực tiếp trong lavish (click element → comment → agent sửa). Dùng để forcing function chi tiết hóa business intent, inform HLD design, và giảm rework downstream cho Master UX Spec. Sử dụng khi người dùng nói "phác thảo UX", "ux sketch", "early UX exploration", "draft UX trước HLD".'
---

# NTAPP UX Sketch Skill (Stage 1 sub-step)

This skill provides a **lightweight UX sketch workflow** to produce a rough UX document — Personas + Rough IA + Primary User Journey — **after PRD/Epics but BEFORE HLD design**, plus a **hi-fi HTML preview** of the journey that PM/BA/PO review by annotating elements directly in lavish.

## Purpose

3 outcomes:

- **Forcing function:** PM/BA + UX Designer phải chi tiết hóa user interaction (gõ gì, thấy gì, click gì) — không né bằng prose tổng quát.
- **Inform HLD design:** Tech Lead xem sketch trước khi design module / container / state machine → sát flow user thực.
- **Reduce downstream rework:** Journey Spec (`/ntapp-ux-design`) Stage 3b inherit sketch làm seed cho §1.3 Persona references + §3 IA delta + §4.1 Primary Journey — chỉ expand, không rewrite. (Sketch optional — thiếu sketch thì 3b fallback PRD, không block.)

## Output

**1 sketch document** `ux_sketch.md` với 5 sections + **1 preview hi-fi retained** (`previews/{feature_slug}_ux_sketch_preview.html`):

| § | Section | Mô tả |
|:--|:--|:--|
| §1 | Executive Brief | Anchor system + primary user goals (1 đoạn) |
| §2 | Rough Personas | 2-3 personas — name, role, top 3 pain points + top 3 goals |
| §3 | Rough IA | Top-level navigation tree + integration points với existing systems (đặc biệt cần cho brownfield) |
| §4 | Primary Journey | 1-2 luồng chính: Mermaid sequence + Screen Intent Table (Screen / Role / Content blocks / CTA / Branch / Trace) + Preview Index |
| §5 | Open Questions for HLD | Câu hỏi technical cho Tech Lead trả lời ở Stage 2 |

Preview mặc định **hi-fi** — render bằng component thật (Tailwind/DaisyUI) skin bằng `master_token.json` của Master DS nếu project đã bootstrap Stage 0; mỗi frame mang `id` + `data-*` để annotation của reviewer map thẳng về ô tương ứng trong Screen Intent Table. Hạ về wireframe grayscale bằng `sketch_preview: lofi`, tắt bằng `off`.

## Squad

| Agent | Vai trò | BMAD Persona |
|:--|:--|:--|
| **UXS0** | UX Sketch Lead & Orchestrator | Sally (`bmad-agent-ux-designer`) |
| **UXS1** | Research Analyst | Mary (`bmad-agent-analyst`) |

## Stage placement

Sub-step cuối Stage 1 — sau khi PRD + Epics approve, trước khi trigger Stage 2 Architecture.

## Relationship với `/ntapp-ux-design`

```
PRD/Epics → ux_sketch.md (Stage 1) → HLD/Module 0 (Stage 2) → ux_design.md (Stage 3b)
                ↓                                                    ↑
                └──── inherited as seed cho §1.3 + §3 + §4.1 ────────┘
```

Sketch là **optional upstream**. Nếu không chạy sketch, ux-design vẫn generate from scratch.

## Instructions

Read fully and follow: `./workflow.md`
