# IRON RULES — Quy tắc bất biến của workflow NTAPP Feature Design (Layer 3)

> File này là **nguồn sự thật duy nhất** cho các nguyên tắc bất biến của toàn workflow.
> Mọi step file và persona PHẢI tham chiếu file này thay vì tự lặp lại nội dung.
> Khi cần emphasize 1 rule cụ thể trong step, **cite ID** (vd "theo R3") thay vì paraphrase nội dung.

---

## R1. VERBATIM INJECTION (Bơm dữ liệu nguyên văn)

Khi hợp nhất các file `f*_part.md` trong `feature_design_parts/{id}/` thành tài liệu Master Detailed Design (Pass 2-4 của Step 07), **TUYỆT ĐỐI KHÔNG** thực hiện thao tác "Merge" truyền thống bằng cách đọc toàn bộ và viết lại bản tóm tắt.

**Tuân thủ:** Bơm dữ liệu thô từ các Part đơn lẻ vào các vị trí giữ chỗ trong Template `master_detailed_design_v4_template.md` (placeholder injection).

**Vi phạm điển hình:** "Tóm tắt phần Logic: feature có 3 quy tắc validation chính..." → SAI. Phải copy nguyên văn Logic Matrix + KBKT.

---

## R2. ZERO-SUMMARIZATION (Cấm tóm tắt)

Mọi Bảng biểu (Logic Matrix, Test Data Matrix, KBKT, UI Component Spec), Mermaid Diagram (Sequence, State Machine, Wireframe), và spec field từ file thô **PHẢI được giữ nguyên 100%** số scenario/row/diagram và nội dung khi đi vào DD final.

**Phạm vi R2:** R2 chống TÓM TẮT khi assembly (Step 07) — cấm lược bớt scenario/row/diagram hoặc viết lại thành bản rút gọn. Schema cột của mỗi bảng do template `master_detailed_design_v4_template.md` định nghĩa; sinh bảng đúng schema template, giữ nguyên schema đó khi assembly KHÔNG phải vi phạm R2.

**Vi phạm điển hình:** Cắt ngắn KBKT từ 50 scenario xuống 20; rút gọn Logic Matrix bỏ cột "Edge Case" (cột nội dung thiết kế); gộp 2 wireframe thành 1.

---

## R3. ZERO-FABRICATION / ZERO-HALLUCINATION (Cấm bịa)

Chỉ sử dụng thông tin từ các nguồn input đã được xác nhận. Source primary thay đổi theo `id_type`:

| `id_type` | Source primary | Source secondary |
|---|---|---|
| `feature_id` (BE) | L2 TechSpec — `{module}_techspec.md` canonical (cho module chứa feature) | PRD/Epics; UX Journey Spec (chỉ nếu cần ref) |
| `screen_id` (FE) | UX Journey Spec — `ux_design.md` (journey + **Key states** của screen trong Journey Screen Table + IA delta) **+ `ux_conventions.md`** (patterns C1-C7) **+ `component_catalog.md`** (DS vocabulary + recipes). *Gate-SKIP:* `project_wbs.md` (identity) + HLD §3.1.1/§3.2 (actor/IA) + conventions/catalog nếu có — ghi `ux_source: HLD-fallback` | PRD/Epics; L2 TechSpec của BE module mà screen consume |
| `widget_id` (FE) | UX Journey Spec — `ux_design.md` (journey nào dùng widget + Key states) **+ `ux_conventions.md` + `component_catalog.md`**. *Gate-SKIP:* `project_wbs.md` (identity) + HLD §3.1.1/§3.2 (actor/IA) + conventions/catalog nếu có — `ux_source: HLD-fallback` | PRD/Epics; ≥1 L2 TechSpec mà widget consume |

Mọi case PHẢI verify `id` tồn tại trong WBS SSoT — `project_wbs.md` unit list tương ứng (`features` / `screens` / `widgets`).

Khi thiếu thông tin (vd: validation rule cụ thể), PHẢI đánh dấu `[TBD]` — tuyệt đối không tự bịa.

**Zero Placeholder runtime:** TUYỆT ĐỐI KHÔNG để lại `[Data]`, `[VD: ...]`, `{placeholder}` trong output cuối cùng (trừ `[TBD]` có lý do rõ ràng).

---

## R4. TRACEABILITY (Xương sống truy vết Layer 3)

Chuỗi truy vết bắt buộc xuyên Detailed Design, phân nhánh theo `id_type`:

```
PRD/Epic → WBS unit list (features|screens|widgets) → DD F0 Overview
  ├─ feature_id (BE) → L2 TechSpec → DD F1 Logic → DD F2 Data → DD F4 QA
  ├─ screen_id (FE) → Journey Spec (journey + Key states) + Conventions + Catalog → DD F3 UI → DD F4 QA
  └─ widget_id (FE) → Journey Spec (journey usage + Key states) + Conventions + Catalog → DD F3 UI → [DD F2 Data nếu own state] → DD F4 QA
```

- **Mọi `id`** phải tồn tại trong WBS unit list tương ứng (verify ở Step 01 pre-flight).
- **Mọi UI component** trong F3 reference vocabulary từ `component_catalog.md` (cột `DS candidate` §2.3 khi match; cluster khớp recipe → compose theo recipe). Component chưa có trong catalog → wireframe vẫn được mô tả control mới nhưng KHÔNG bịa tên component canonical — Stage 4b audit sẽ quyết reuse/NEW.
- **Mọi Key states** của screen trong Journey Screen Table (`ux_design.md` §4) phải được cover trong F3 §2.3 state declarations — thiếu = vi phạm inheritance (R10).
- **Mọi Logic Matrix row** trong F1 phải có ít nhất 1 KBKT scenario tương ứng trong F4.
- **Mọi data field** trong F2 phải có entity origin từ L2 TechSpec §11 (Logical Data Model) hoặc Module 0 ERD (cho BE feature); hoặc widget local state schema (cho widget own state).
- **Mọi sequence step** trong F1 phải khớp với external touchpoint trong L2 Module 0 (nếu có).

---

## R5. CONSISTENCY (Đồng nhất xuyên các Parts đã tạo)

- Tên UI control trong F3 (UI Part) PHẢI khớp 100% với tên field trong F1 (Logic Part) khi cùng reference 1 element. (Áp dụng khi cả 2 part tồn tại.)
- Tên entity/field trong F2 (Data Part) PHẢI khớp với schema từ L2 TechSpec — không tự đổi tên.
- KBKT scenario ID (F4) PHẢI cite trực tiếp Logic Matrix row ID (F1) làm origin. (Khi F1 tồn tại.)
- Wireframe (F3) phải khớp journey / IA / Key states đã chốt trong UX Journey Spec + patterns trong `ux_conventions.md` (§C1-C7 áp cho unit — cột Conventions refs của journey table).

---

## R6. QUALITY GATES (Trạm kiểm soát bắt buộc dừng)

Workflow có các quality gate **bắt buộc dừng** chờ pass trước khi đi tiếp:

| Gate | Sau step | Owner | Hành động khi FAIL |
|---|---|---|---|
| Inheritance Audit | 01 | Agent F0 | DỪNG, escalate user fix L2 hoặc UX Spec trước |
| Wireframe Composition Audit | 02 (sau F3) | Agent F0 | Audit wireframe theo **L1-L4/L7/L8/L10/L11** (`{design_system_root}/_shared/layout-best-practices.md`). Mặc định **warn-only** (đề xuất fix). Khi `layout_rules.enforce_hard: true`: HIGH-confidence **L1/L2/L7** fail → **bắt buộc fix** trước Next. Vi phạm bắt nguồn từ UX Spec (L5/L6/L9) → escalate ngược UX Spec (R10), KHÔNG tự sửa lệch |
| UI ↔ Logic Sync | 06 | Agent F0 | Loop back F3 hoặc F1 sửa naming |
| Logic ↔ KBKT Coverage | 06 | Agent F0 | Loop back F4 bổ sung scenario |
| Quantitative Audit | 07 (Pass 5) | Agent F0 | Bơm lại đoạn bị thiếu, không release DD |

---

## R7. STOPPING ERRORS (Lỗi dừng khẩn cấp)

Dừng pipeline ngay và báo cáo nếu phát hiện:

1. `id` không tồn tại trong WBS unit list tương ứng theo `id_type` (`features` / `screens` / `widgets`) → broken traceability.
2. (Áp dụng cho `feature_id`) L2 TechSpec module chứa feature **chưa được approve** (file không tồn tại hoặc thiếu signoff).
3. (Áp dụng cho `screen_id` / `widget_id`) **Identity gate = WBS (SSoT):** `id` phải có trong `project_wbs.md` screens/widgets list — vắng mặt = orphan thật → DỪNG (mọi trường hợp). **Journey gate (chỉ multi-screen-new):** feature thuộc nhánh chạy Stage 3b mà `ux_design.md` (Journey Spec) không tồn tại/chưa approve → DỪNG, chạy `/ntapp-ux-design` trước; screen có trong WBS nhưng KHÔNG xuất hiện trong Journey Screen Table nào → **WARN** (advisory — screen ngoài journey chính, F3 tự chịu trách nhiệm IA placement) + ghi note vào DD Section 1, KHÔNG dừng. **Gate-SKIP / HLD-fallback:** feature thuộc nhánh gate-SKIP (single-screen/reuse — `ntapp-ux-design` step-01 §2.0) → không yêu cầu Journey Spec; source primary = `project_wbs.md` (identity) + HLD §3.1.1/§3.2 (actor/IA) + `ux_conventions.md`/`component_catalog.md` nếu có; ghi `ux_source: HLD-fallback`.
4. Drift giữa F1 Logic Matrix và F4 KBKT: row F1 không có KBKT scenario, hoặc KBKT scenario không cite F1 row. (Chỉ áp dụng khi F1 đã chạy.)
5. F3 §2.3 bỏ sót **Key states** mà Journey Screen Table khai cho screen này, HOẶC F3 điền cột `DS candidate` bằng tên component **không có** trong `component_catalog.md` (bịa vocabulary — vi phạm R10). (Chỉ áp dụng khi F3 đã chạy.) **Ngoại lệ HLD-fallback:** khi `ux_source: HLD-fallback`, không có Journey Screen Table để khớp — F3 tự author per-unit wireframe từ WBS + HLD §3.2 + conventions/catalog (nếu có); vẫn cấm bịa tên component ngoài catalog.

---

## R8. CONTRACT LOCK (Khoá hợp đồng tích hợp)

Module 0 canonical (`{planning_artifacts}/00_system_connectivity_integration.md`) là **read-only trong Layer 3**. Tuyệt đối:
- Không sửa Schema/Protocol/Resilience của Module 0 từ skill này.
- Mọi thay đổi phải bump version Module 0 mới ở Layer 1 — không từ skill này.
- Nếu phát hiện Module 0 sai hoặc thiếu → escalate qua R7 (Stopping Error #2), không tự fix.

Tương tự cho Master Design System: read-only trong Layer 3 (chi tiết tại R10).

---

## R9. MISSING INPUT HANDLING (Xử lý input thiếu)

Nếu input file (PRD, Epics, L2 TechSpec, UX Spec, `project_wbs.md`, hoặc bất kỳ `f*_part.md` dependency nào) **không tồn tại** hoặc **không readable**:

- DỪNG ngay, **KHÔNG generate placeholder content** (`[Data]`, `<TBD>`, mock value, "feature có 3 màn hình tự bịa...") thay thế.
- Báo user explicit: "File `X` tại path `Y` không tìm thấy. Vui lòng cung cấp đường dẫn hoặc xác nhận file."
- Chỉ tiếp tục sau khi user confirm file tồn tại + readable.

**Vi phạm điển hình:** Agent đọc UX Spec không có rồi tự suy ra "feature có 5 màn hình A, B, C..." → SAI. Phải hỏi user trước.

**Liên quan:** R9 bổ sung cho R3 — R3 cấm bịa khi đã có context, R9 cấm bịa khi thiếu context.

---

## R10. INHERITANCE COMPLIANCE (Tuân thủ kế thừa từ Layer trên)

Layer 3 PHẢI kế thừa từ 2 nguồn cao hơn — không tự ý đổi:

- **L2 TechSpec inheritance:** Module boundary, Container name, sequence diagram, persistence schema phải khớp 100% với L2.
- **UX inheritance (2 artifact):**
  - **Journey Spec (`ux_design.md`):** journey flow, IA delta placement, **Key states per screen** (Journey Screen Table — F3 §2.3 phải cover đủ), **journey-level layout audit (L5/L6/L9 — đọc từ dòng self-audit cuối mỗi journey §4)**. Composition-level audit (L1-L4/L7/L8/L10/L11) feature-design **tự sở hữu** (§2.4); phát hiện Journey Spec vi phạm journey-level (L5/L6/L9) → escalate ngược, KHÔNG tự sửa lệch. *(Per-screen wireframe/regions KHÔNG còn trong UX Spec từ v4.0 — F3 là single wireframe owner.)*
  - **Conventions (`ux_conventions.md`):** interaction patterns (§C3), notification/error surfaces (§C4/C5), content rules + status labels (§C2), responsive/a11y (§C6), audit-log rules (§C7) — F3 áp theo cột `Conventions refs` của journey table + §C-x liên quan; không định nghĩa lại pattern trong DD.
  - **HLD-fallback (gate-SKIP):** khi feature thuộc nhánh gate-SKIP (single-screen/reuse), inheritance source = **`project_wbs.md` (identity) + HLD §3.1.1/§3.2 (actor + IA)** + `ux_conventions.md` (nếu đã có — conventions là project-wide, vẫn áp) + `component_catalog.md`. Ghi `ux_source: HLD-fallback` ở Section 1 DD. KHÔNG áp dụng cho feature multi-screen mới (phải có Journey Spec).

**Master Design System qua digest:** F3 đọc **`component_catalog.md`** (digest derived — tên + intent + variants + recipes + used-in, ~1-2k token) để author đúng vocabulary + composition; **KHÔNG load full** `master_token.json`/`components_metadata.json` (nặng, matcher authoritative là Stage 4b). Token-level styling vẫn KHÔNG thuộc DD (Stage 4b/DS layer).

**Vi phạm điển hình:**
- F3 §2.3 bỏ state `Rejected (editable + reason)` mà Journey Screen Table khai cho screen → SAI (vi phạm R10 Key states).
- F3 điền DS candidate `app-fancy-tag` không tồn tại trong `component_catalog.md` → SAI (bịa vocabulary).
- F1 Logic Part đặt tên field `userId` khác `user_id` của L2 TechSpec ERD → SAI (vi phạm R5 + R10).

**Khi cần đổi:** escalate qua R7 (Stopping Error #2/#3) → quay lại Layer 1/2 (TechSpec) hoặc Journey Spec/Conventions update trước, không tự fix trong L3.
