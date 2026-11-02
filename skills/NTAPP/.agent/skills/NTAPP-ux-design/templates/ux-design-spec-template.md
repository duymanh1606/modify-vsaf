---
stepsCompleted: []
inputDocuments: []
workflowType: 'ux-design-spec'
---

# UX JOURNEY SPECIFICATION — {{project_name}}

<!-- QUY ƯỚC OKF: dòng bắt đầu bằng "okf-id:" ngay dưới mỗi heading H2/H3 là ĐỊNH DANH
     ỔN ĐỊNH của mục đó trong đồ thị OKF. Đổi tiêu đề thì GIỮ NGUYÊN marker. Xoá marker
     thì danh tính tụt về slug của tiêu đề, và mọi cạnh trỏ tới mục này sẽ đứt lặng lẽ
     ngay lần đầu ai đó sửa câu chữ của tiêu đề.

     Tài liệu này đặc biệt cần nó hơn DD/techspec: SỐ MỤC NẰM TRONG TIÊU ĐỀ, nên id hôm
     nay là `3-1-mo-hinh-phan-lop`. Chèn thêm một §2.5 là mọi mục phía dưới bị đánh số
     lại và tái sinh dưới id mới. Marker cắt số ra khỏi danh tính.

     Marker phải là DÒNG KHÔNG RỖNG ĐẦU TIÊN dưới heading — bộ đọc dừng ở dòng đó. Đặt
     sau một comment hướng dẫn là marker không được đọc. -->

**Project:** {{project_name}}
**Anchor System:** {{anchor_system}}
**Integrated Systems:** {{integrated_systems}}
**Version:** 1.0
**Date:** {{date}}
**Author:** {{user_name}}
**Conventions:** xem [ux_conventions.md](./ux_conventions.md) — mọi pattern tương tác / notification / error / responsive / content áp cho spec này định nghĩa Ở ĐÓ (singleton project-wide), KHÔNG lặp lại ở đây.

---

## CHANGE LOG

| Date | Section | A/M/D | Description | Version |
|:-----|:--------|:------|:------------|:--------|
| {{date}} | All | A | Initial UX journey specification | 1.0 |

---

<!--
TEMPLATE v4.0 — SLIM JOURNEY SPEC
Tài liệu này chỉ giữ phần KHÔNG stage nào khác own được: thiết kế CROSS-SCREEN
(archetype, IA/navigation, journey flows) + PRD traceability.

KHÔNG chứa (đã tách/loại từ v4.0):
- Per-screen Screen Spec chi tiết → owner DUY NHẤT là feature-design Stage 4a §2 (DD wireframe).
  Journey node ở đây chỉ 1 dòng purpose + key states (đủ để 4a kế thừa intent, không đủ để drift).
- §17 Screen & Widget Inventory → SSoT là project_wbs.md (gate feature-design check WBS trực tiếp).
- Personas chi tiết → `ux_sketch.md` §Personas nếu có (Stage 1, optional) / PRD §User Stories nếu không; ở đây chỉ reference + actor lock từ HLD §3.1.1.
- Conventions (§3/§5/§11-15 cũ) → ux_conventions.md (project singleton, delta-update).

Mỗi section dưới có generation comment trỏ step file. Agent PHẢI đọc step file trước khi fill.
-->

## 1. EXECUTIVE SUMMARY
<!-- okf-id: executive-summary -->

### 1.1. Context & Vision
<!-- okf-id: context-vision -->
<!-- Step 02 — Agent UX2. Output: ≤2 đoạn — bối cảnh feature (hệ thống/quy trình hiện tại + pain chính, quantified nếu PRD có số) + 1 câu UX vision. KHÔNG bảng hiện trạng dài — chi tiết đã có trong PRD, cite thay vì chép. -->

### 1.2. Design Goals
<!-- okf-id: design-goals -->
<!-- Step 02 — Agent UX2. Output: table {Goal | Measurement} — min 3 goals, measurement quantified, trace PRD success criteria. -->

### 1.3. Personas (reference)
<!-- okf-id: personas -->
<!-- Step 02 — Agent UX2. Output: 1 dòng/role: {Persona name — role} → pointer `ux_sketch.md §Personas` (nếu có sketch) hoặc PRD user stories. Actor list LOCK theo HLD §3.1.1 (R8.1/R10) — chỉ liệt kê actor có trong HLD. KHÔNG viết lại persona table chi tiết. -->

---

## 2. WORKFLOW ARCHETYPE & INFORMATION MODEL
<!-- okf-id: workflow-archetype-info-model -->

### 2.1. Workflow Archetype
<!-- okf-id: workflow-archetype -->
<!-- Step 08 — Agent UX3 + UX0. Output: chọn 1 archetype (MAKER_CHECKER / WIZARD / DASHBOARD / TRANSACTIONAL / CONTENT_MGMT / OTHER) + 1-2 câu justification cite PRD primary user story. Hybrid (2 archetype song song) → split 2 spec, KHÔNG mix. OTHER → mô tả pattern inline ≤5 dòng. -->

### 2.2. Primary Entity & Composition Model
<!-- okf-id: primary-entity-composition -->
<!-- Step 08 — Agent UX3. Output: entity theo BUSINESS term + composition model (SINGLE / SECTIONED / LINEAR_STEPS / REFERENCE) + ASCII diagram sub-section/step + data-flow direction (nếu ≠ SINGLE). Mark Required/Optional + điều kiện kích hoạt. -->

### 2.3. Section Status & Data Propagation
<!-- okf-id: section-status-propagation -->
<!-- Step 08 — Agent UX3. Applicable: composition ≠ SINGLE. Output: (a) state taxonomy (universal Empty/In-progress/Complete/Error + archetype-conditional Locked/Rejected/Blocked/Draft/Published) — mỗi state: icon + color token path + 1 dòng business meaning; (b) bảng cross-section propagation {Source | Field | → Target | Field | Type | Timing | Conflict Policy} nếu có data dependency. Indicator pattern chi tiết + transition behavior → ux_conventions.md §C3. -->

---

## 3. INFORMATION ARCHITECTURE & NAVIGATION
<!-- okf-id: ia-navigation -->

### 3.1. Navigation Principle & Tree
<!-- okf-id: navigation-principle-tree -->
<!-- Step 07 — Agent UX3. Output: nav model (Action/System/Entity-Based/Hybrid) + ASCII navigation tree. BROWNFIELD (đã có ux_design trước / app đang chạy): chỉ vẽ DELTA — node mới + node neo (cha/anh em) đánh dấu (existing), KHÔNG vẽ lại toàn tree. Mỗi leaf node mới ↔ 1 SCR-* trong project_wbs.md (frontend-app module) — WBS là SSoT ID, UX không tự đặt. Annotate role-restricted. -->

### 3.2. Shell Placement
<!-- okf-id: shell-placement -->
<!-- Step 07 — Agent UX3. Output: screens mới đặt vào shell layout NÀO (reference shell đã có trong ux_conventions.md §C6-shell hoặc mô tả 1 khung ASCII nếu project chưa có shell doc). Region checklist per archetype giữ ở step file — chỉ emit kết luận. -->

---

## 4. USER JOURNEYS
<!-- okf-id: user-journeys -->

<!-- QUY TẮC CHUNG §4 (Step 09 + 10): mỗi journey = (a) Mermaid flowchart TD + (b) JOURNEY SCREEN TABLE.
KHÔNG Screen Spec block per screen (đã bỏ từ v4.0 — chi tiết regions/components/states per screen là việc
của feature-design Stage 4a; nguồn ở đây chỉ khoá INTENT + STATE bắt buộc để 4a kế thừa).

Journey Screen Table format (R2 fidelity — đủ 5 cột, không thêm không bớt):
| Screen (SCR-* từ WBS) | Purpose (1 dòng) | Key states (bắt buộc UI phải có) | Entry ← / Exit → | Conventions refs (§C-x áp dụng) |

L5/L6/L9 self-audit (journey/IA level, warn-only) ghi 1 dòng cuối mỗi journey. -->

### 4.1. Primary Journey — {{primary_role_name}}
<!-- okf-id: primary-journey -->
<!-- Step 09 — Agent UX0. Mermaid: verb sequence + end states theo archetype §2.1 (mapping table ở step-09). Cover happy path + major branches; không vẽ branch ngoài archetype. + Journey Screen Table. -->

### 4.2. Secondary Journey — {{secondary_role_name}}
<!-- okf-id: secondary-journey -->
<!-- Step 10 — Agent UX0. Applicable: ≥2 role non-overlapping trên cùng entity (single-role → SKIP, không placeholder). Mermaid + Journey Screen Table. Decision feedback loop về primary thể hiện bằng node trong Mermaid + hàng trong table (KHÔNG spec màn chi tiết). -->

### 4.3. Additional Role Journeys
<!-- okf-id: additional-role-journeys -->
<!-- Step 10 — Agent UX0. Applicable: ≥3 role. 1 sub-section per role: Role Context (1-2 dòng vì sao tách) + Mermaid + Journey Screen Table. Skip role không có user story trong PRD. -->

---

## 5. PRD → UX MAPPING
<!-- okf-id: prd-ux-mapping -->

<!-- Step 14 — Agent UX2. Output: bảng closure {PRD Requirement | UX Solution | Section (§ ở đây / §C-x conventions / DD Stage 4a)}. 100% FR+BR+NFR xuất hiện, 0 hàng trống, solution cụ thể. NFR/BR thuộc pattern chung → map sang ux_conventions.md §C-x. Requirement chưa có solution → 🔴 GAP + báo cáo. -->

---

*Template version: 4.0 (slim journey spec — per-screen Screen Specs → feature-design Stage 4a; §17 inventory → project_wbs.md; personas → ux-sketch nếu có / PRD fallback, actor lock HLD; conventions → ux_conventions.md) | Framework: NTAPP Method*
