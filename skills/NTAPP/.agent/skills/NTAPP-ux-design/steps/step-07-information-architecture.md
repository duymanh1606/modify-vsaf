# STEP 07: INFORMATION ARCHITECTURE & NAVIGATION (§3 — delta-aware)

> **Thực hiện bởi:** Agent UX3 (IA & System Architect — Winston)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R3, R5, R8.4 (WBS lock), R10**.

## 1. Mục tiêu

Đặt screens MỚI của feature vào kiến trúc điều hướng: nav model + nav tree (DELTA cho brownfield) + shell placement. Journey Spec §3.

## 2. Đầu vào cần đọc

- §1 part: anchor system, personas references (mental model)
- `project_wbs.md` — **SSoT** `SCR-*`/`WGT-*` list của feature (R8.4)
- `ux_design.md` cũ §3 (nếu brownfield-per-feature) — nav tree hiện có
- `ux_conventions.md` §C6 shell blueprint (nếu đã có từ trước)
- `component_catalog.md` — nav components có sẵn (sidebar/tabs/breadcrumb)
- PRD FR navigation; HLD §3.2.0 module list
- PRD primary user story → **preliminary archetype hint** (confirm chính thức ở step-08)

## 3. Chỉ thị thực thi

### 3.1. §3.1 Navigation Principle & Tree

**Bước 1 — nav model** (giữ model đã có nếu brownfield — đổi model là quyết định lớn, escalate):

| Model | Khi nào dùng |
|:---|:---|
| **Action-Based** — menu theo business goal | Persona nghĩ theo công việc; anchor tích hợp ≥2 backend |
| **System-Based** — menu theo module | Persona tech-savvy; mỗi hệ thống một domain |
| **Entity-Based** — menu theo entity chính | Single primary entity; CONTENT_MGMT / DASHBOARD |
| **Hybrid** | Mix |

**Bước 2 — ASCII nav tree, chế độ DELTA:**
- **Brownfield** (`ux_design.md` cũ tồn tại): CHỈ vẽ node mới + node neo (cha/anh em trực tiếp, đánh dấu `(existing)`). KHÔNG vẽ lại toàn tree.
- **Lần đầu:** vẽ tree đầy đủ.

```
{{anchor}} Shell
├── (existing) Quản lý đối tác
│   ├── (existing) Danh sách merchant
│   └── [NEW] Đối soát giao dịch          ← SCR-RECON-LIST
│       └── [NEW] Chi tiết đối soát       ← SCR-RECON-DETAIL
```

**Quality:**
- Mỗi leaf node MỚI ↔ đúng 1 `SCR-*` trong WBS (R8.4 — thiếu screen trong WBS → escalate `/ntapp-architecture-design --append`, KHÔNG tự đặt ID).
- Annotate role-restricted. Label nhất quán nav model.

### 3.2. §3.2 Shell Placement

- Screens mới dùng shell NÀO: reference `ux_conventions.md` §C6 shell blueprint nếu đã có (1 dòng: "đặt trong content area của shell chuẩn, breadcrumb cấp 2"). Chưa có shell doc → chọn region set theo preliminary archetype (decision matrix để step file cũ — emit kết luận + ASCII 1 khung đơn giản, chi tiết shell về §C6 ở step-13).
- Optional region → kèm justification. Action bar: secondary trái, primary phải (§C1 Consistency).
- Preliminary archetype đổi ở step-08 → quay lại sửa §3.2.

## 4. Đầu ra yêu cầu

- **Lưu trữ:** `{intermediate_folder}/ux3_ia_part.md`
- Nội dung: §3.1 (delta tree) + §3.2.
- Báo cáo: "§3 hoàn tất. Nav model: {giữ nguyên/chọn mới}, {X} node mới ↔ WBS OK, shell: {ref §C6 / mô tả mới}."

**Next:** Read fully and follow `./step-08-information-hierarchy.md`
