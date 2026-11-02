# Step 7: Emit (TERMINAL)

## GOAL

Chốt `figma-manifest.yaml` với **checksum per unit**, sinh `figma_ingest_report.md`, dọn intermediate, in lệnh kế tiếp.

Checksum là cơ chế duy nhất giúp Hook 3 phát hiện "Figma đã đổi sau khi DD được ký" — làm sai bước này thì drift gate vô hiệu.

## 1. Persona

Procedural. Tuân thủ **U1 (atomic)**, **U4 (deterministic)**, **U6 (scrub secret trước khi ghi)**.

## 2. Inputs

- `figma-manifest.yaml` (step-03, `checksum` còn trống).
- `specs/{unit_id}.json` (step-04), `frames/*.png` (step-06).
- `figma-ds-map.md` + `token-gap-report.md` (step-05).
- `report_sections[]` tích luỹ từ step-01 → step-06.

## 3. Pipeline

### Stage 7.1: Tính checksum per unit

```
checksum = sha256(
    specs/{unit_id}.json (bytes)
  + mọi frames/{unit_id}*.png (bytes, sort tên file alphabetical)
  + node_id + states[] đã sort
)
```

Ghi dạng `sha256:<16 hex đầu>` (đủ phân biệt, gọn cho manifest và log hook).

Bất biến khiến checksum có nghĩa: mọi fetch từ step-02 trở đi **pin cùng `version`** (U4). Không pin thì 2 lần chạy trên file đang được sửa ra 2 checksum khác nhau mà không ai đổi gì có ý nghĩa.

Chỉ tính cho unit **in-scope** (step-03 Stage 3.3b). Unit out-of-scope **giữ checksum cũ** — không đọc lại file, không tính lại.

**Re-ingest, unit in-scope:** so với manifest cũ:
- Checksum **không đổi** → giữ nguyên entry, `drift: false`.
- Checksum **đổi** → cập nhật entry + `drift: true` + `drift_detected_at`. Cờ này để người biết unit nào cần xem lại DD; Hook 3 so trực tiếp checksum với `figma_ref` trong DD nên không phụ thuộc cờ này.

### Stage 7.2: Finalize manifest (MERGE — không replace)

Step-03 Stage 3.6 đã dựng manifest merged (in-scope thay mới, out-of-scope giữ verbatim, `last_scope` đã ghi). Step này **chỉ điền phần phụ thuộc specs/frames**, đúng cho các unit in-scope: `checksum`, `frame_exported`, `states[].frame`, `ingested_at`, `figma_version`, `ds_id`.

⛔ **Không được** rebuild `units[]` từ đầu ở đây. Rebuild = xoá entry out-of-scope = đúng cái bug mà Stage 3.3b tồn tại để chặn.

Validate trước khi ghi theo [references/figma-manifest-schema.md](../references/figma-manifest-schema.md) — thiếu field bắt buộc → STOP (§4). Thêm 2 assert riêng cho merge:

| Assert | Fail → |
|---|---|
| Mọi `unit_id` có entry trong manifest **cũ** phải còn entry trong manifest **mới** (không mất unit nào) | STOP: *"Merge làm mất {N} unit: {list}. Đây là bug ghi đè — không ghi manifest."* |
| Unit out-of-scope phải có `figma_status` + `checksum` + `last_evaluated_at` **giống hệt** bản cũ | STOP liệt kê unit bị sửa ngoài ý muốn |

Ghi atomic vào **từng DS root** (multi-DS: N file, mỗi file chỉ chứa unit của DS đó).

### Stage 7.3: Sinh `figma_ingest_report.md`

Compose từ `report_sections[]` theo thứ tự: `[SOURCE]` → `[HARVEST]` → `[MAPPING]` → `[SPEC EXTRACT]` → `[DS RECONCILE]` → `[FRAME EXPORT]`, cộng 2 phần thêm:

**§ Layout Groups hint (dán được)** — với mỗi unit, render bảng 4 cột đúng format Stage 4a §2.2:

```markdown
### SCR-LIST — state `default`
| Group ID | Type | Members | Props |
| :--- | :--- | :--- | :--- |
| R1 | Stack | G1, G2 | direction=column, gap=lg, sizing=fill×hug |
| G1 | Stack | Left(fill), text_title, Right(fill) | direction=row, gap=sm, justify=start, align=center, sizing=fill×fixed, effective_align=center-full-width |
| G2 | Box | text_amount, button_submit | direction=row, justify=between, align=center, radius=none · geometry MEDIUM |
| G3 | Stack | G3a, G3b | direction=column, gap=md, radius=lg, border=none, elevation=card |
```

F3 verify rồi dán, không tự phát minh lại. Ghi rõ dòng nào `confidence: LOW` / `MEDIUM` (vd `Grid` suy luận, hoặc `Box` suy từ `geometry[]` vì frame không có Auto Layout — hậu tố `· geometry MEDIUM` như dòng G2 ở trên).

**3 assert format trước khi ghi report (fail-loud):**

1. Không `Props` cell nào chứa cùng một khoá hai lần. `align=center, align=stretch` là **lỗi**, không phải dữ liệu — nó nghĩa là step-04 Stage 4.3 đang gộp hai trục vào một tên khoá.
2. Mọi `Props` cell **không rỗng**.
3. Row có hậu tố `(fill)` ở member đầu **và** cuối, member giữa không `(fill)` → phải có `effective_align=center-full-width`. Thiếu → thông tin canh giữa bị mất ở khâu render, dù step-04 đã tính đúng.

Fail → STOP với tên unit + group id. Ba assert này chặn lớp lỗi không quan sát được ở tầng dưới: canh giữa thành canh trái, cùng hàng thành xếp dọc.

**§ Surface hint (dán được)** — bảng ánh xạ vai trò → token, F3 copy vào cột `Props`:

```markdown
| Unit | Node / group | radius_role | Props ghi vào §2.2 |
| :--- | :--- | :--- | :--- |
| SCR-LIST | `button_submit` | pill | `radius=full` |
| SCR-LIST | `G3` content card | rounded-lg | `radius=lg, border=none, elevation=card` |
```

Node có `radius_role` mà `figma-ds-map.md` §[SURFACE] **không** gắn được token (vd `RADIUS_PILL_MISSING`) → vẫn liệt kê, cột Props ghi `radius=<TODO: DS thiếu token pill>` + dòng trong §Việc cần làm tiếp. Bỏ trống ô đó thì 4a rơi về mặc định `radius-base` mà không ai biết.

**§ Việc cần làm tiếp** — checklist người đọc:
- Unit `figma_status: missing` → sẽ author mode ở 4a (liệt kê).
- Unit `figma_status: not_in_scope` **mà DD đã có `figma_ref`** → chưa verify được drift lần này; muốn chắc thì chạy ingest với scope phủ chúng (liệt kê).
- Gap token > threshold → khuyến nghị `ds-bootstrap --external-tokens`.
- `FIGMA_CONTRAST_FAIL` → gửi designer sửa Figma.
- Frame export fail → liệt kê.
- **`RADIUS_PILL_MISSING` / `BORDER_WIDTH_TOKENS_MISSING`** → sửa `master_token.json` (lỗi mô hình token phía mình, không phải phía designer). Ghi rõ giá trị hiện tại của `radius.full` nếu nó không phải `9999px`.
- **Node INSTANCE không tra được radius** (step-04 Stage 4.2b bậc 3) → liệt kê; F3 phải đọc từ ảnh và ghi vào §2.5, nên chúng cần có tên trong report thay vì im lặng.
- **Group `Box` suy từ `geometry[]`** (`confidence: MEDIUM`) → liệt kê; đề nghị designer bật Auto Layout cho những frame này để lần ingest sau lên `HIGH`.

**§ Merge summary** — bảng 1 dòng/nhóm để người kiểm ngay là không mất gì:

| Nhóm | Số unit | Ghi chú |
|---|---|---|
| in-scope, mapped | 5 | checksum mới |
| in-scope, missing | 1 | `SCR-PAY-06` |
| out-of-scope, giữ verbatim | 34 | không chạm |
| out-of-scope, mới (`not_in_scope`) | 0 | — |

### Stage 7.4: Dọn + gitignore

- Xoá `{output_root}/.work/` (intermediate: `tree.json`, `nodes-deep.json`, `file-meta.json`, `name-map.json`).
- Verify spec repo `.gitignore` có dòng `_reference/figma/.work/` (thêm nếu thiếu — đây là ngoại lệ hợp lệ duy nhất của U3 write-scope, vì `.gitignore` nằm ngoài `_reference/figma/`; ghi rõ trong report là đã thêm).

### Stage 7.5: Scrub + in lệnh kế tiếp

Scrub theo U6 (`figd_*`, `?X-Amz-`) trên mọi file vừa ghi. Còn khớp → STOP (§4).

In:
```
Ingest xong: {mapped} unit mapped, {missing} missing, {frames} PNG, {gaps} token gap.

Tiếp theo:
  1. (nếu gap > 0)  /ntapp-ds-bootstrap --external-tokens {path}     ← chạy từ CODE repo
  2. Stage 3b        /ntapp-ux-design
  3. Slice loop      /NTAPP-vsaf-slice-loop SLICE-01                 ← offline, không gọi Figma
  4. Commit spec repo: manifest + specs + frames + report
```

## 4. Decision Points

- **Manifest thiếu field bắt buộc** (schema validate fail) → STOP liệt kê field thiếu + unit nào. KHÔNG ghi manifest nửa vời (manifest là contract của 3 consumer + 1 hook).
- **0 unit có checksum** (mọi unit missing/stale) → STOP: *"Không unit nào ingest được. Không ghi manifest rỗng — nó sẽ khiến Hook 3 báo drift sai cho mọi unit."* Ngoại lệ: manifest cũ đã có unit `mapped` out-of-scope → **không STOP** (merge vẫn bảo toàn chúng), chỉ WARN là lần này không ingest thêm được gì.
- **Assert merge fail** (mất unit, hoặc entry out-of-scope bị sửa) → STOP như bảng Stage 7.2. Đây là loại lỗi phải fail-loud: hậu quả của nó (4a âm thầm rơi về author mode) không có gate nào khác bắt được.
- **Scrub còn khớp pattern secret** → STOP: *"Phát hiện chuỗi giống PAT/signed-URL trong `{file}`. KHÔNG commit. Kiểm lại step vừa ghi file này."*
- **`.gitignore` không ghi được** (read-only) → WARN, hướng dẫn thêm tay. Không STOP.

## 5. Output

- `{ds_root}/_reference/figma/figma-manifest.yaml` (final, có checksum).
- `{ds_root}/_reference/figma/figma_ingest_report.md`.
- `.work/` đã xoá.

**TERMINAL.** Không đọc step tiếp. Người dùng commit spec repo rồi đi tiếp theo checklist Stage 7.5.
