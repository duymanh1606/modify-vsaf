# IRON RULES — Quy tắc bất biến của workflow NTAPP UX Design (Stage 3b — Journey Spec + Conventions)

> File này là **nguồn sự thật duy nhất** cho các nguyên tắc bất biến của toàn workflow.
> Mọi step file và persona PHẢI tham chiếu file này thay vì tự lặp lại nội dung.
> Khi cần emphasize 1 rule cụ thể trong step, **cite ID** (vd "theo R3") thay vì paraphrase nội dung.
>
> **v4.0 (2 artifact):** `ux_design.md` (journey spec — per feature-batch) + `ux_conventions.md` (project singleton). Per-screen Screen Spec / §17 inventory / personas chi tiết KHÔNG còn thuộc Stage 3b (owner lần lượt: feature-design 4a / project_wbs.md / ux-sketch-nếu-có → PRD §User Stories fallback; actor identity luôn lock theo HLD §3.1.1).

---

## R1. VERBATIM INJECTION (Bơm dữ liệu nguyên văn)

Khi hợp nhất các file `ux*_part.md` trong `ux_design_parts/` thành `ux_design.md` (Step 14 Final Assembly), **TUYỆT ĐỐI KHÔNG** thực hiện thao tác "Merge" truyền thống bằng cách đọc toàn bộ và viết lại bản tóm tắt. Bơm dữ liệu thô từ các Part vào placeholder trong template `ux-design-spec-template.md`.

**Ngoại lệ khai báo — `ux_conventions.md`:** conventions KHÔNG assemble từ parts. Steps 04/06/11/12/13 ghi TRỰC TIẾP vào `ux_conventions.md` (atomic write; bootstrap mode fill đủ section, delta mode chỉ patch section thay đổi + CHANGE LOG row). R1 không áp cho file này.

**Vi phạm điển hình:** "Tóm tắt §4 Journeys: có 2 journey chính..." → SAI. Phải copy nguyên văn Mermaid + journey screen table.

---

## R2. ZERO-SUMMARIZATION (Cấm tóm tắt)

Mọi Mermaid Diagram (journey flow), **Journey Screen Table**, bảng (Goals, PRD→UX Mapping) và spec field từ part file **PHẢI được giữ nguyên 100%** dung lượng và chi tiết khi đi vào artifact final.

**Journey Screen Table fidelity (thay Screen Spec Fidelity từ v4.0):** Stage 3b KHÔNG spec per-screen chi tiết (regions/components/states đầy đủ) — đó là fidelity của feature-design Stage 4a (single wireframe owner, chống dual-maintenance drift). Mỗi screen trong journey xuất hiện ĐÚNG 1 hàng trong Journey Screen Table, format canonical **đủ 5 cột, không thêm không bớt**:

```text
| Screen (SCR-* từ WBS) | Purpose (1 dòng) | Key states (bắt buộc UI phải có) | Entry ← / Exit → | Conventions refs (§C-x) |
```

- `Key states` = ràng buộc intent tối thiểu Stage 4a PHẢI cover (vd `Empty / Loading / Error / Locked-sau-approve`) — lấy từ state taxonomy §2.3, KHÔNG mô tả layout.
- **CẤM** thêm cột Regions/Components/wireframe vào table này (leo thang ngược về per-screen spec = tái tạo drift đã cắt).
- Zero-Summarization vẫn áp: không gộp 2 screen 1 hàng, không bỏ cột.

Giữ nguyên (diagram): Mermaid flow §4.x; ASCII composition diagram §2.2; ASCII nav tree §3.1 (delta).

**Vi phạm điển hình:** Cắt journey 8 bước còn 4; bỏ cột `Key states`; thêm cột `Components` vào Journey Screen Table; gộp secondary journey vào primary.

---

## R3. ZERO-FABRICATION / ZERO-HALLUCINATION (Cấm bịa)

Chỉ sử dụng thông tin từ các nguồn input đã được xác nhận. Mỗi nguồn có vai trò xác định:

| Nguồn | Path | UX dùng cho |
|:--|:--|:--|
| **PRD/Epics** (primary) | user-confirmed | FR/BR/NFR (§5 mapping), user journeys (§4), success criteria (§1) |
| **HLD canonical** (primary) | `{stage_2_architecture}/architecture_design.md` | System boundary + actors (§1.3), module list / WBS (§3), sequence flows per module (§4 tham chiếu) |
| **`project_wbs.md`** (primary — SSoT unit ID) | `{stage_2_architecture}/project_wbs.md` | `SCR-*` / `WGT-*` ID cho §3 nav leaf + §4 journey screen table — UX KHÔNG tự đặt ID |
| **Module 0 §7 Global State Registry** (narrow source) | `{stage_2_architecture}/00_system_connectivity_integration.md` §7 only | State enum cho status labels (`ux_conventions.md` §C2) — 1-1 mapping |
| **Master Design System** | `{design_system_path}/component_catalog.md` (digest — KHÔNG load full metadata) | Component vocabulary + recipes khi journey/conventions cần gọi tên component; token path verify qua `master_token.json` chỉ khi cần |
| **UX Sketch** (optional upstream) | `{stage_1_discovery}/ux_sketch/ux_sketch.md` | Nguồn chi tiết personas KHI CÓ (§1.3 chỉ reference; thiếu sketch → pointer PRD §User Stories — actor lock luôn theo HLD §3.1.1) + seed §3 IA + §4.1 Primary Journey |

Khi thiếu thông tin, PHẢI đánh dấu `[TBD]` — tuyệt đối không tự bịa. **Zero Placeholder runtime:** không để lại `[Data]`, `{placeholder}`, `{{variable}}` trong output cuối (trừ `[TBD]` có lý do).

---

## R4. TRACEABILITY (Xương sống truy vết Stage 3b)

Chuỗi truy vết bắt buộc:

```
PRD/Epic FR/BR/NFR → §5 PRD→UX Mapping row → { §N journey spec | ux_conventions.md §C-x | DD Stage 4a (per-screen) }
                  → §3 IA placement (nav node mới)
                  → §4 Journey Screen Table row (SCR-* từ WBS)
```

- **Mọi UX decision** truy ngược được đến ≥1 PRD requirement qua §5.
- **Mọi `SCR-*`/`WGT-*`** nhắc trong §3/§4 phải tồn tại trong `project_wbs.md` (WBS là SSoT — KHÔNG duy trì inventory riêng trong spec này).
- **Mọi screen trong journey** (§4 table) phải map ≥1 nav node §3.1 (node mới hoặc existing).
- **§5 không có hàng nào trống** — closure check là quality gate cuối.

---

## R5. CONSISTENCY (Đồng nhất xuyên artifact)

- Tên component nhắc trong journey spec / conventions PHẢI khớp `component_catalog.md` (vocabulary canonical từ Master DS). Component chưa có → ghi `[gap — propose Stage 4b]`, KHÔNG bịa selector.
- Token path (vd `semantic.color.status.approved`) PHẢI khớp `master_token.json` canonical.
- Status label (`ux_conventions.md` §C2) PHẢI 1-1 mapping với enum Module 0 §7 — 1 enum ↔ đúng 1 label, không nhập nhằng xuyên §C4/§C5.
- Persona/actor name (§1.3, §4) PHẢI khớp actor list HLD §3.1.1.
- Notification event (§C4) ↔ error type (§C5) nhất quán khi cùng trigger.

---

## R6. QUALITY GATES (Trạm kiểm soát bắt buộc dừng)

| Gate | Sau step | Owner | Hành động khi FAIL |
|---|---|---|---|
| Pre-flight Input Audit | 01 | UX0 | DỪNG, escalate user xác nhận PRD/Epics tồn tại + có cấu trúc FR/BR/NFR |
| Inheritance Audit (HLD + Module 0 + WBS) | 01 | UX0 | Warn nếu HLD/Module 0 thiếu; FAIL nếu WBS thiếu (Stage 3b chạy sau 2b — WBS phải có) |
| WBS ↔ Journey Sync | sau 09-10 | UX0 | Mọi SCR-* trong journey table tồn tại trong WBS; lệch → sửa journey hoặc escalate WBS amend (KHÔNG tự thêm ID) |
| Layout Best-Practice Compliance | sau 09-10 | UX0 | Audit journey theo **L5/L6/L9** (`_shared/layout-best-practices.md`, journey/IA-level — soi Mermaid + journey table + nav tree). Warn-only vĩnh viễn. L1/L2/L7 composition-level enforce tại `feature-design` |
| Conventions Coverage | sau 13 | UX0 | Journey table cột `Conventions refs` trỏ §C-x nào chưa tồn tại trong `ux_conventions.md` → quay lại step tương ứng bổ sung |
| Quantitative Audit | 14 | UX0 | Bảng đối soát step-14 §4.4 — mục FAIL → quay lại step tương ứng |
| PRD→UX Closure | 14 | UX2 | DỪNG, không release nếu §5 còn hàng "UX Solution" trống |

---

## R7. STOPPING ERRORS (Lỗi dừng khẩn cấp)

Dừng pipeline ngay và báo cáo nếu phát hiện:

1. PRD hoặc Epics **không tồn tại** hoặc rỗng → broken inheritance.
2. PRD không có cấu trúc FR/BR/NFR rõ ràng → §5 closure check không thể thực thi.
3. Status label (`ux_conventions.md` §C2) không 1-1 mapping với Module 0 §7 enum → vi phạm R8.
4. §1.3/§4 chứa actor không có trong HLD §3.1.1, hoặc HLD có actor mà journey bỏ qua → vi phạm R10.
5. Journey spec / conventions tham chiếu component **không có** trong `component_catalog.md` mà không đánh dấu `[gap — propose Stage 4b]` → vi phạm R5.
6. §5 PRD→UX mapping còn ≥1 hàng "UX Solution" trống ở Step 14 (closure fail).
7. `SCR-*` / `WGT-*` trong §3/§4 không tồn tại trong `project_wbs.md` → vi phạm R10 (WBS inheritance). KHÔNG tự thêm — escalate WBS amend (`/ntapp-architecture-design --append`).
8. `ux_conventions.md` bị journey spec ghi đè section trái owner (journey spec chỉ REFERENCE §C-x, không định nghĩa lại pattern).

---

## R8. CONTRACT LOCK (Khoá hợp đồng tích hợp)

4 nguồn upstream là **read-only** trong Stage 3b — UX không được tự sửa:

### R8.1. HLD lock — `{stage_2_architecture}/architecture_design.md`
- System boundary, actor list (§3.1.1), module list / WBS breakdown (§3.2.0), sequence diagram per module (§3.2.2).

### R8.2. Module 0 §7 Global State Registry lock
- State enum cho mọi entity. `ux_conventions.md` §C2 chỉ được dịch enum sang user-facing label (1-1), KHÔNG thêm/bớt state.

### R8.3. Master Design System lock — `component_catalog.md` + `master_token.json` + `components_metadata.json`
- Chỉ **reference** vocabulary; audit gap = informational note `[gap — propose Stage 4b]`. KHÔNG sửa token, không tạo component canonical mới ở Stage 3b.

### R8.4. WBS lock — `project_wbs.md`
- `SCR-*` / `WGT-*` ID là của WBS. UX không đặt ID mới, không list unit ngoài WBS. Thiếu screen cần thiết → escalate WBS amend, KHÔNG tự chế.

### Khi phát hiện sai/thiếu
Không tự fix tại Stage 3b. Escalate qua R7 — quay lại Stage 1 (PRD), Stage 2 (HLD/Module 0/WBS), hoặc DSO update Master DS trước.

---

## R9. MISSING INPUT HANDLING (Xử lý input thiếu)

Nếu input file không tồn tại hoặc không readable: DỪNG ngay, KHÔNG generate placeholder content thay thế. Báo user explicit. Chỉ tiếp tục sau khi user confirm.

**Phân loại:**
- **PRD + Epics:** Required. Thiếu → DỪNG.
- **`project_wbs.md`:** Required (Stage 3b chạy sau slice-planning — WBS phải lock rồi). Thiếu → DỪNG, hint chạy Stage 2.
- **HLD:** Recommended. Thiếu → WARN, đánh dấu "derived from PRD only".
- **Module 0 §7:** Recommended. Thiếu → WARN, status labels derive từ PRD BR + đánh dấu "pending Tech Lead reconcile".
- **`component_catalog.md`:** Recommended. Thiếu → WARN, hint chạy `/ntapp-ds-bootstrap`; conventions/journey tránh gọi tên component cụ thể (dùng `[gap]`).
- **UX Sketch:** Optional. Có → seed personas/IA/primary journey + audit drift sketch ↔ HLD (HLD thắng). Không có → §1.3 reference PRD §User Stories, §3/§4 generate from scratch — KHÔNG STOP/WARN vì thiếu sketch.
- **`ux_conventions.md` đã tồn tại:** không phải input thiếu — đó là DELTA MODE (steps conventions chỉ patch thay đổi).

---

## R10. INHERITANCE COMPLIANCE (Tuân thủ kế thừa từ Layer trên)

Stage 3b PHẢI kế thừa — không tự ý đổi:

- **PRD inheritance:** Mọi FR/BR/NFR có ≥1 row trong §5 (map sang journey spec section, conventions §C-x, hoặc DD Stage 4a).
- **HLD inheritance:** System boundary, actor list, module/WBS breakdown khớp 100% HLD §3.1.1/§3.2.0.
- **WBS inheritance:** Mọi `SCR-*`/`WGT-*` trong §3/§4 khớp 1-1 với `project_wbs.md`. UX không đặt ID.
- **Module 0 §7 inheritance:** Status enum ↔ label 1-1 trong `ux_conventions.md` §C2.
- **Master DS inheritance:** Component vocabulary từ `component_catalog.md` (read-only); gap → `[gap — propose Stage 4b]`.
- **UX Sketch inheritance** (optional — KHÔNG phải hard dependency): actor identity luôn lock theo HLD §3.1.1. Có sketch → §1.3 reference tên personas từ sketch, §3/§4.1 seed từ sketch rồi expand; không có → §1.3 reference PRD §User Stories, KHÔNG block. Drift sketch ↔ HLD/Module 0 → escalate R7 (HLD/Module 0 thắng).

**Vi phạm điển hình:**
- §4 journey dùng actor "Approver" trong khi HLD §3.1.1 dùng "Operator / NV VDS" → SAI.
- §C2 dùng label "Đang xử lý" cho 2 enum khác nhau → SAI (1 label map nhiều enum).
- Journey table screen `SCR-QUICKVIEW` không có trong WBS → SAI (R8.4 — escalate WBS amend).
- Journey spec tự viết lại persona table chi tiết thay vì reference (sketch nếu có / PRD nếu không) → SAI (dual-maintenance).

**Khi cần đổi:** escalate qua R7 → quay lại Stage 1/2 hoặc DSO, không tự fix trong Stage 3b.
