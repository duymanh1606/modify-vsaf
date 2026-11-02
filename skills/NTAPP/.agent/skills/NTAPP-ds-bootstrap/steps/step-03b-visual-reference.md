# Step 3b: Visual Reference Capture (optional, skippable)

## GOAL

Capture **bằng chứng thị giác** của product hiện tại (brownfield) làm grounding cho mọi stage downstream: screenshot các trang đại diện + visual notes (ngôn ngữ style của product). Token JSON mô tả *giá trị*; visual reference mô tả *cách product nhìn* — density, elevation, table/card treatment, header pattern, icon weight. Thiếu tầng này, UI sinh ở Stage 4-5 đúng token nhưng "generic" — không giống product.

> **Skip conditions (graceful — KHÔNG fail run):**
> - Greenfield (Step 3 discover 0 component) → skip, log info.
> - Config `ds-bootstrap.visual_reference: off` trong `.bmm-config.yaml` → skip.
> - Không có cách render app (không dev server, DSO không cung cấp URL/screenshot) → skip với WARN + hướng dẫn bổ sung sau bằng re-run step này.

## 1. Persona

Không có persona riêng — step procedural, DSO tương tác trực tiếp. Tuân thủ Universal Rules (U1-U5), đặc biệt **U3: KHÔNG modify code repo** (chạy dev server = execute read-only, KHÔNG sửa file).

## 2. Inputs

- `components_metadata_parts/01_discovered.json` (Step 3) — `usage.screens` cho danh sách trang đại diện.
- `stack-profile.json` — dev server command hint (nếu detect được từ `package.json` scripts).
- DSO cung cấp (hỏi 1 lần, chọn 1 trong 3):
  1. **Dev server URL** đang chạy (vd `http://localhost:4200`) + danh sách route đại diện.
  2. **Staging URL** + routes (nếu app public/nội bộ truy cập được).
  3. **Screenshot có sẵn** — DSO copy tay vào `{design_system_root}/_reference/pages/`.

## 3. Pipeline

### Stage 3b.1: Chọn trang đại diện (≤8)

Ưu tiên đa dạng pattern thay vì đủ mọi trang: 1 list/table page, 1 form page, 1 detail/dashboard page, 1 modal/overlay flow, + trang DSO chỉ định. Nguồn gợi ý: `usage.screens` có count cao nhất (Step 3).

### Stage 3b.2: Capture

Với URL mode:

```bash
npx -y playwright screenshot --full-page "{url}{route}" "{design_system_root}/_reference/pages/{route-slug}.png"
```

- Viewport mặc định 1440×900 (desktop). Capture thêm 390×844 (mobile) cho ≤2 trang chính nếu app responsive.
- Playwright không cài được / URL không reachable → fallback hỏi DSO screenshot tay (mode 3).

### Stage 3b.3: Visual notes

Ghi `{design_system_root}/_reference/visual-notes.md` (atomic U1) — quan sát từ screenshots, mỗi mục ≤3 dòng, **cite screenshot file** làm evidence:

```markdown
# Visual Notes — {project}

## Style character (tổng thể)
- Density: {compact/comfortable} — vd bảng 40px row height (pages/merchant-list.png)
- Elevation: {flat/subtle shadow/heavy} — card dùng border 1px thay shadow
- Corner language: {sharp/4px/8px/pill}
- Icon weight: {outline/filled}, size chuẩn {16/20/24}px

## Per-pattern
### Table/List pages ({file})
- Header treatment, row hover, pagination style, filter bar composition
### Form pages ({file})
- Label position, field grouping, action bar placement
### Overlay/Modal ({file})
- Backdrop, width convention, footer button order
```

### Stage 3b.4: Consumer note

Append `[VISUAL REFERENCE]` vào `report_sections[]`: số trang captured + đường dẫn. Consumers đọc `_reference/` (spec repo — mọi stage đọc được không vi phạm direction guard):
- **Stage 4a** `feature-design` F3 — grounding composition/proportion khi vẽ wireframe.
- **Stage 4b** `ui-generation` Step 1/3/4 — đối chiếu visual_intent với style character thật.
- **Stage 4b** `ds-build-component` scaffolder — đối chiếu style idiom khi scaffold NEW.
- **Stage 5** dev agent — reference khi implement (link qua DD).

## 4. Decision Points

- **Mọi capture mode fail** → skip với WARN: *"Visual reference trống — UI sinh ra sẽ chỉ ground trên token, style match yếu hơn. Bổ sung sau: chạy lại `/ntapp-ds-bootstrap` (step 3b tự detect `_reference/` đã có và chỉ capture bổ sung)."*
- **Re-run (incremental):** `_reference/pages/` đã có → chỉ capture route mới DSO chỉ định, giữ ảnh cũ (không xoá — DSO tự dọn khi UI đổi lớn).

## 5. Output

- `{design_system_root}/_reference/pages/*.png` (≤8 trang, +mobile variants nếu có).
- `{design_system_root}/_reference/visual-notes.md`.
- `report_sections[]` += `[VISUAL REFERENCE]`.

**Next:** Read fully and follow `./step-04-normalize.md`
