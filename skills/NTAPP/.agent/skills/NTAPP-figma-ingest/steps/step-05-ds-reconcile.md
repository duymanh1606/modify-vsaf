# Step 5: DS Reconcile

## GOAL

Nối Figma với Master DS ở hai trục và **chỉ report, không apply**:
1. `figma-ds-map.md` — Figma component instance → DS `component_id`; Figma style/variable → token path.
2. `token-gap-report.md` — giá trị ngoài tolerance + cặp contrast fail → input cho DSO chạy `ds-bootstrap --external-tokens`.

## 1. Persona

Procedural. **Không** adopt persona của Stage 4b — skill này không quyết reuse. Tuân thủ **U5 (no fabrication)** và **U3 (không ghi `master_token.json`)** nghiêm ngặt.

## 2. Inputs

- `specs/{unit_id}.json` (step-04) — `control_hint[].figma_component`, `raw` values.
- `{ds_root}/components_metadata.json` — inventory thật (`usage`, `recipes[]`).
- `{ds_root}/master_token.json` — token canonical.
- `{family_root}/_shared/pattern-matcher.md` — **SSoT thuật toán matching**. KHÔNG restate công thức ở đây.
- `{family_root}/_shared/best-practices.md` — **SSoT công thức WCAG contrast**. KHÔNG restate.
- Config `snap_tolerance`, `token_gap_warn_threshold`.

> **Multi-DS:** chỉ đối chiếu với `components_metadata.json` / `master_token.json` của **DS đã resolve cho unit** (step-03 Stage 3.4). Match chéo sang DS khác là sai — component DS khác không import được (`ds-resolution.md` nhánh B).

## 3. Pipeline

### Stage 5.1: Figma component → DS `component_id`

Với mỗi `figma_component` distinct (dedupe trước — 1 file Figma thường dùng 1 component ở 30 chỗ):

1. Chạy matching **theo thủ tục** `_shared/pattern-matcher.md` §5 trên **toàn bộ** `components_metadata.json` (trừ category `layout-primitive` — đã xử lý qua `layout_groups_hint` ở step-04).
2. Nguồn cho 4 signal của pattern-matcher, ánh xạ từ dữ liệu Figma:

   | Signal | Lấy từ |
   |---|---|
   | intent (0.40) | Tên component Figma + `role` của text con + `intent` ở `control_hint` |
   | structural (0.25) | Hình dạng child (có icon? có label? có input? mấy slot?) |
   | tags (0.20) | `componentProperties` (variant prop names/values) |
   | a11y (0.15) | **Figma không cung cấp** → signal này để trống; ghi rõ trong map là score bị giảm trần. KHÔNG bịa giá trị a11y (U5) |

3. Ghi **top-3 candidate + score** cho mỗi Figma component.

### Stage 5.2: Ngưỡng ghi map (hint — non-binding)

| Top-1 score | Ghi vào `figma-ds-map.md` | Ý nghĩa cho Stage 4b |
|---|---|---|
| **≥ 0.95** | `mapped` | Bậc **C-1 Figma-mapped** — 4b reuse trực tiếp, không cần score lại |
| **0.70 – 0.94** | `likely` | 4b ưu tiên vào shortlist, vẫn score đủ |
| **< 0.70** | `unmapped` | 4b chạy reuse ladder C0→C3 bình thường như không có Figma |

> **Bất biến:** map này là **hint, non-binding** — hoàn toàn cùng bản chất với cột `DS candidate` ở §2.3. Stage 4b step-01 vẫn là chủ sở hữu duy nhất của quyết định reuse/`[NEW]`. Skill này KHÔNG được ghi `proposed_ds_updates.md`.

### Stage 5.3: Snap raw value → token path

Với mỗi giá trị trong khoá `raw` của specs (`gap`, `padding`, `font_size`, `radius`, `fill`, `stroke`):

1. Tìm token cùng tier trong `master_token.json` có giá trị gần nhất.
2. |Δ| ≤ `snap_tolerance` (default spacing 2px, radius 2px, font_size 1px; màu: **exact hex** hoặc ΔE ≤ 2) → **snap**: ghi `token_path` vào `figma-ds-map.md` §Token, thêm dòng vào `snap_log` (raw → token → Δ).
3. |Δ| > tolerance → **gap entry** trong `token-gap-report.md`: raw value, token gần nhất, Δ, số lần xuất hiện, unit nào dùng.
4. Không có token nào cùng tier → gap entry với `nearest: none`.

`snap_tolerance` là nút xoay quan trọng: chặt quá → report dài vô ích (designer lệch 1px là chuyện thường); lỏng quá → mất ý đồ thật của designer.

**Ngoại lệ BẮT BUỘC — `radius` snap theo VAI TRÒ trước, theo px sau.** Node có `surface[].radius_role` (step-04 Stage 4.2b) thì tra bảng vai trò trước; chỉ khi vai trò không có token tương ứng mới rơi về snap px:

| `radius_role` | Token đích | Nếu DS không có |
|---|---|---|
| `pill` | token có value `9999px` (thường `radius.full`) | **gap entry `RADIUS_PILL_MISSING`** — xem dưới |
| `circle` | token có value `50%` (thường `radius.circle`) | gap entry |
| `rounded-lg` / `-md` / `-sm` | snap px trong nhóm radius | — |

Snap `pill` bằng px là sai theo thiết kế: cùng vai trò pill là `r=24` trên nút cao 48 và `r=28` trên nút cao 56 — snap px cho ra hai token khác nhau cho một ý định, và nút cao hơn thang token thì luôn thiếu. Bo hết hai đầu là **quan hệ với chiều cao**, không phải một con số.

`RADIUS_PILL_MISSING` là gap entry đặc biệt: ghi rõ *"DS không có token radius nào bằng `9999px`. Token `radius.full` hiện là `{value}` — nếu là `50%` thì nó cho ra hình bầu dục trên hộp chữ nhật, KHÔNG phải pill. Sửa `master_token.json` theo `_shared/best-practices.md` §4.8."* Đây là lỗi mô hình token, không phải lỗi designer — nên nó phải nêu tên nguyên nhân thật thay vì báo lệch px.

**`border` snap 2 vế riêng:** `stroke_weight` → token `border.width.*` (thiếu nhóm này → gap entry `BORDER_WIDTH_TOKENS_MISSING`, ghi 1 lần cho cả DS chứ không mỗi node một dòng); `stroke_color` → token color như mọi màu khác. `surface[].border.style` (`solid`/`dashed`) và `.sides` **không snap** — chúng là vai trò, đi thẳng vào `figma-ds-map.md` §[SURFACE] để 4a đọc.

### Stage 5.4: Contrast pre-scan

Với mọi cặp (text fill, background fill của node cha gần nhất có fill) trong specs:

1. Resolve 2 vế sang hex (raw Figma, hoặc token đã snap ở 5.3).
2. Tính ratio theo công thức **owned bởi** `_shared/best-practices.md` (accessibility section).
3. < 4.5:1 (normal text) / < 3:1 (large text + UI component) → entry `FIGMA_CONTRAST_FAIL` trong `token-gap-report.md`: unit, node, cặp màu, ratio đo được, ngưỡng cần, gợi ý token đạt chuẩn gần nhất.

> **Tên warning khác có chủ ý.** `WCAG_CONTRAST_FAIL` do Stage 4b step-01 Stage 3.4 **sở hữu độc quyền** (producer duy nhất ở proposal-time). Ở đây là `FIGMA_CONTRAST_FAIL` — tầng sớm hơn, mục đích khác: bắt designer sửa Figma **trước** khi vào slice, chứ không phải chặn build. Không block gì cả.

### Stage 5.5: Emit

`figma-ds-map.md` — 4 section:

```markdown
# Figma ↔ DS Map — {ds_id}
> Nguồn: figma-source.json (file {file_key} @ version {version}). HINT, non-binding.

## [COMPONENT]
| Figma component | Variant props | DS component_id | Score | Status | Top-3 khác |
|---|---|---|---|---|---|
| `Button/Primary` | size, state | `app-button` | 0.97 | mapped | app-icon-button (0.62), app-link (0.41) |

## [TOKEN]
| Figma value | Token path | Δ | Occurrences | Units |
|---|---|---|---|---|
| `gap: 16` | `spacing.md` | 0 | 41 | SCR-LIST, SCR-LOGIN |
| `gap: 14` | `spacing.md` | 2 (snapped) | 6 | SCR-LIST |

## [SURFACE]
| Unit | Node / group | radius_role | Token radius | border | elevation |
|---|---|---|---|---|---|
| SCR-LIST | `button_submit` | pill | `radius.full` | none | — |
| SCR-LIST | `G4` content card | rounded-lg | `radius.lg` | none | card |

## [UNMAPPED]
| Figma component | Top-1 score | Ghi chú cho Stage 4b |
|---|---|---|
| `SegmentedTabs` | 0.48 | Chưa có tương đương — 4b sẽ chạy reuse ladder C0→C3 |
```

§[SURFACE] là section 4a đọc để điền `radius=` / `border=` / `elevation=` vào Props của Layout Groups §2.2 — **tên token, không phải px**. Thiếu section này thì 4a chỉ có `radius_role` dạng chữ và phải tự đoán token tương ứng.

`token-gap-report.md` — 2 section: `[TOKEN GAP]` (từ 5.3) + `[CONTRAST]` (từ 5.4), mỗi entry kèm `occurrences` để DSO ưu tiên.

## 4. Decision Points

- **Số gap > `token_gap_warn_threshold` (default 20)** → **WARN + khuyến nghị mạnh**: *"{N} token gap. Nên chạy `/ntapp-figma-ingest --tokens-only` rồi `/ntapp-ds-bootstrap --external-tokens` để hoà giải token TRƯỚC khi vào slice-loop — nếu không mỗi slice sẽ tự propose `[NEW]` rời rạc và Master DS phân mảnh sau vài slice."* Không STOP (người có thể chấp nhận nợ có chủ ý).
- **`components_metadata.json` rỗng / 0 component** → bỏ Stage 5.1-5.2, `figma-ds-map.md` chỉ có section `[TOKEN]` + WARN: *"DS chưa có component nào — chạy `/ntapp-ds-bootstrap` trước để map có nghĩa."*
- **Màu resolve fail** (gradient, image fill, blend mode) → ghi `UNRESOLVED` trong gap report, bỏ khỏi contrast scan. KHÔNG đoán màu đại diện (U5).
- **Cùng Figma component map 2 DS khác nhau** (multi-DS, 1 Figma file phủ nhiều FE repo) → hợp lệ, không phải lỗi. Ghi riêng ở map của từng DS.

## 5. Output

- `{ds_root}/_reference/figma/figma-ds-map.md`.
- `{ds_root}/_reference/figma/token-gap-report.md`.
- `report_sections[]` += `[DS RECONCILE]` (mapped/likely/unmapped count, snap count, gap count, contrast fail count, **số surface entry đã gắn token + `RADIUS_PILL_MISSING`/`BORDER_WIDTH_TOKENS_MISSING` nếu có**).

**Next:** Read fully and follow `./step-06-frame-export.md`
