# Step 4: Spec Extract

## GOAL

Với mỗi unit đã mapped, sinh `specs/{unit_id}.json` — hierarchy **đã prune** + `layout_groups_hint[]` + `surface[]` + `geometry[]` + `copy[]` + `icon_candidates[]` + `control_hint[]`.

Đây là step tạo ra giá trị lớn nhất của cả skill: **Figma Auto Layout ↔ Layout Groups table gần như 1-1**, nên F3 ở Stage 4a không phải đoán bố cục.

**Nguyên tắc phạm vi extract:** thứ gì **không** được emit ra ngoài khoá `raw` thì Stage 4a không có cách hợp pháp nào để biết, và sẽ im lặng rơi về giá trị mặc định của DS.

| Lớp | Bỏ thì Stage 4a mất gì | Stage 4.x |
|---|---|---|
| Surface treatment (radius/border/elevation) | Vai trò bo góc; có/không viền | **4.2b** |
| Toạ độ tương đối của container không Auto Layout | Quan hệ trên–dưới vs cùng hàng | **4.2c** |
| `sizing` của member + tách 2 trục align | Canh giữa suy từ FILL hai bên | **4.3** |

## 1. Persona

Procedural. Tuân thủ **U7** (fetch → file → `jq` prune → chỉ đọc bản prune), **U5** (không suy diễn), **U4** (sorted, deterministic).

## 2. Inputs

- `figma-manifest.yaml` (step-03) — unit nào, `node_id` nào, `states[]` nào.
- `figma-source.json` — `version` pinned.
- Config `snap_tolerance` (dùng ở step-05; step này chỉ ghi raw + đánh dấu).
- (`manual` mode) `inbox/nodes.json`.

## 3. Pipeline

### Stage 4.1: Fetch sâu — chỉ node đã mapped

```bash
bash <skill_dir>/scripts/figma-fetch.sh nodes \
  --ids "12:340,12:411,18:22" --depth 12 \
  --out "{output_root}/.work/nodes-deep.json"
```

Chỉ truyền `node_id` của unit **mapped** (+ node của từng state). Frame `ignore: true` không fetch. Script tự chunk `ids` để không vượt giới hạn độ dài URL.

### Stage 4.2: Prune (bỏ node vô nghĩa với spec)

Bỏ node khi khớp bất kỳ điều kiện:

| Bỏ | Lý do |
|---|---|
| `visible: false` | Không thuộc màn đang đặc tả |
| `type: VECTOR` mà **không** phải icon candidate (Stage 4.5) | Đồ hoạ trang trí |
| `type: RECTANGLE` / `ELLIPSE` chỉ có `fills`, không có sibling text/child | Background/divider — sẽ tái tạo bằng token, không cần node |
| `isMask: true` và mọi descendant | Kỹ thuật render Figma, không có tương đương UI |
| `GROUP` có đúng 1 child | **Collapse** — nâng child lên thay vì giữ wrapper rỗng |
| Node ngoài `absoluteBoundingBox` của frame cha | Ghi chú designer để cạnh canvas |

Giữ: `FRAME`, `INSTANCE`, `COMPONENT`, `TEXT`, `VECTOR` (icon), `GROUP` (≥2 child).

### Stage 4.2b: Surface treatment → `surface[]` (NGOÀI `raw`)

`cornerRadius` / `strokes` / `effects` đã có sẵn trong response `/v1/files/{key}/nodes` — không cần fetch thêm. Nhưng **giá trị px thô phải ở trong `raw`** (Stage 4.7), nên tầng ngoài mang **vai trò (role)**, không mang số. Vai trò là thứ F3 được đọc và ghi vào DD; số là thứ step-05 snap sang tên token.

Với mỗi node giữ lại có `cornerRadius != 0` **hoặc** `strokes[] != []` **hoặc** `effects[]` có `DROP_SHADOW`/`INNER_SHADOW` visible → 1 entry:

```json
{
  "node_id": "12:340",
  "figma_name": "Button / Primary / Large / Default",
  "radius_role": "pill",
  "radius_source": "descendant",
  "border": { "style": "solid", "sides": "all" },
  "elevation": true,
  "confidence": "HIGH"
}
```

**`radius_role` — suy từ tỉ lệ radius / cạnh ngắn, KHÔNG từ giá trị tuyệt đối:**

| Điều kiện (`r` = cornerRadius, `s` = min(w, h)) | `radius_role` | Ghi chú |
|---|---|---|
| `r >= s/2 - 1` **và** `w/h` ngoài khoảng 0.9–1.1 | `pill` | Bo hết hai đầu — hộp chữ nhật |
| `r >= s/2 - 1` **và** `w/h` trong khoảng 0.9–1.1 | `circle` | Avatar / icon tròn |
| `s/4 <= r < s/2 - 1` | `rounded-lg` | — |
| `s/8 <= r < s/4` | `rounded-md` | — |
| `0 < r < s/8` | `rounded-sm` | — |
| `r == 0` | *(không emit entry vì radius)* | — |

Ngưỡng theo tỉ lệ chứ không theo px: cùng một `r = 24` là **pill** trên nút cao 48 và **rounded-sm** trên thẻ cao 400.

**`radius_source` — bắt buộc, vì INSTANCE thường không mang radius ở node gốc:** `cornerRadius` của component instance nằm ở frame **bên trong** instance (hoặc ở component master), không ở node instance. Thứ tự tra:

1. `cornerRadius` / `rectangleCornerRadii` trên chính node → `radius_source: "self"`.
2. Không có → **descend** vào con: `FRAME`/`RECTANGLE` đầu tiên có `cornerRadius != 0` **và** kích thước ≥ 90% node cha (tức là nền của instance, không phải chi tiết nhỏ bên trong) → `radius_source: "descendant"`.
3. Vẫn không có → **không emit** `radius_role` và ghi vào `warnings[]`: *"`{figma_name}` là INSTANCE không tra được radius (node gốc và con đều không có `cornerRadius`) — F3 phải đọc từ ảnh, ghi vào §2.5"*. U5: không bịa.

`rectangleCornerRadii` (4 góc khác nhau) → `radius_role` lấy theo góc **lớn nhất**, thêm `radius_asymmetric: true`; F3 đọc ảnh để biết góc nào.

**`border` — phân biệt viền với đổ bóng:**

| Tín hiệu Figma | `border` |
|---|---|
| `strokes[]` có ≥1 paint visible, `strokeDashes` rỗng | `{ style: "solid", sides: <xem dưới> }` |
| `strokes[]` visible + `strokeDashes[]` không rỗng | `{ style: "dashed", sides: ... }` |
| `strokes[]` rỗng / toàn `visible: false` | `null` — **không có viền** |

`sides`: `individualStrokeWeights` có ≥1 cạnh = 0 → liệt kê cạnh khác 0 (`"top"`, `"top+bottom"`); đều nhau → `"all"`. Đây là nguồn duy nhất để DD nói được "kẻ ngăn chỉ ở trên" thay vì "khung viền quanh".

`elevation: true` khi có `DROP_SHADOW` visible. **Bắt buộc emit cả khi `border: null`** — vì thẻ trắng bo góc + bóng mềm và thẻ trắng có viền 1px trông rất khác nhau, mà ASCII `┌──┐` biểu diễn cả hai giống nhau. Không có entry surface thì F3 mặc định vẽ viền.

Màu stroke / độ dày px / blur bóng đi vào `raw` như mọi giá trị khác (Stage 4.7); step-05 snap sang token.

### Stage 4.2c: Container không Auto Layout → `geometry[]`

`layoutMode: NONE` (hoặc `GROUP`) mà có ≥2 child → **không có thông tin nào** về quan hệ không gian của các con nếu chỉ nhìn cây. Emit toạ độ **tương đối, đã chuẩn hoá** để F3 suy lại bố cục mà không phải mở ảnh đo bằng mắt:

```json
{
  "node_id": "12:411",
  "figma_name": "Group 42",
  "inferred_direction": "row",
  "inferred_align": "center",
  "confidence": "MEDIUM",
  "children": [
    { "node_id": "…:1", "name": "text_amount",   "box": [0.00, 0.42, 0.38, 0.16] },
    { "node_id": "…:2", "name": "button_submit", "box": [0.44, 0.40, 0.56, 0.20] }
  ]
}
```

`box` = `[x, y, w, h]` **tỉ lệ 0–1 so với `absoluteBoundingBox` của node cha**, làm tròn 2 chữ số. Dùng tỉ lệ chứ không px vì (a) không vướng luật `raw` — đây là quan hệ bố cục, không phải giá trị design token nào để hardcode, (b) so sánh được giữa mobile 375 và desktop 1440.

**Suy `inferred_direction`** (thủ tục cố định, không phán đoán tự do):

- Chiếu các `box` lên trục X và trục Y. Cặp con nào chồng lấn ≥ 60% trên trục Y **và** không chồng lấn trên trục X → cùng hàng.
- Mọi cặp cùng hàng → `row`. Mọi cặp rời nhau theo Y → `column`. Lẫn cả hai → `mixed` + `confidence: LOW`.
- `inferred_align`: theo trục vuông góc — tâm các con lệch < 5% bề rộng cha → `center`; sát mép đầu → `start`; sát mép cuối → `end`.

`confidence` ở đây **cao nhất là MEDIUM** — suy từ toạ độ tĩnh không biết được ý định responsive của designer. F3 phải đối chiếu ảnh trước khi dán.

> Không có khối này thì node loại đó chỉ ra `Box` với `props: ""` — F3 không có gì để đọc nên phải đoán, và mặc định sẽ đoán theo thứ tự `children` (tức xếp dọc).

### Stage 4.3: Auto Layout → `layout_groups_hint[]` (giá trị cốt lõi)

Với mỗi node còn lại có `layoutMode != NONE`, map sang **10 canonical primitive** của `_shared/component-metadata-schema.md` §12:

| Tín hiệu Figma | `Type` | Ghi chú |
|---|---|---|
| `layoutMode: VERTICAL` | `Stack` + `direction=column` | — |
| `layoutMode: HORIZONTAL` | `Stack` + `direction=row` | — |
| `layoutWrap: WRAP` | `Cluster` | Cluster là primitive cho nhóm wrap được |
| `layoutMode: HORIZONTAL` + `primaryAxisAlignItems: SPACE_BETWEEN` | `Cluster` | Thường là action bar / header |
| 1 child + `counterAxisAlignItems: CENTER` + `primaryAxisAlignItems: CENTER` | `Center` | — |
| `VERTICAL` chứa đúng 1 `TEXT` (label) + 1 `INSTANCE` input | `FormField` | `Props: label="<text nguyên văn>"` |
| ≥2 `FormField` trong `VERTICAL` đều cùng width | `FieldGrid` | `confidence: MEDIUM` |
| ≥2 hàng con cùng số cột, cột cùng width | `Grid` | `confidence: LOW` — Figma không có Grid thật, đây là suy luận |
| `layoutMode: NONE` nhưng có ≥2 child | `Box` | Kèm entry `geometry[]` (Stage 4.2c) — `props` mang `inferred_direction`/`inferred_align`, KHÔNG để rỗng |

**Props map — mỗi trục một khoá riêng (BẮT BUỘC):**

| Figma | Props | Trục |
|---|---|---|
| `itemSpacing` | `gap=<raw>px` (step-05 snap → tên token) | — |
| `paddingTop/Right/Bottom/Left` | `padding=<raw>` (gộp nếu đối xứng) | — |
| `primaryAxisAlignItems: MIN/CENTER/MAX/SPACE_BETWEEN` | `justify=start/center/end/between` | **trục chính** |
| `counterAxisAlignItems: MIN/CENTER/MAX/BASELINE` | `align=start/center/end/baseline` | **trục vuông góc** |
| `layoutSizingHorizontal` / `Vertical` | `sizing=<h>×<v>` với `fill`/`hug`/`fixed` | — |

⛔ **CẤM dùng khoá `align=` cho cả hai trục.** Format cũ sinh ra `align=center, align=stretch` — hai giá trị cùng tên khoá, người đọc không thể biết cái nào là trục nào, và `stretch` thật ra là thông tin `sizing` bị gán nhầm nhãn. Đây là nguyên nhân trực tiếp của lớp bug canh lề. Một khoá xuất hiện hai lần trong một `props` string là **lỗi format**, step-07 phải bắt (§Stage 7.3).

**`sizing` của từng member — bắt buộc ghi vào cột `Members`:**

Member nào có `layoutSizingHorizontal: FILL` (trong row) hoặc `Vertical: FILL` (trong column) → hậu tố `(fill)`. `HUG` → `(hug)`. `FIXED` → không hậu tố.

```
Members: Left(fill), text_title, Right(fill)
```

**Quy tắc canh giữa suy diễn — `effective_align` (chốt lớp bug nặng nhất):**

Row `HORIZONTAL` có ≥3 member, member **đầu và cuối** `sizing=fill`, member giữa `hug`/`fixed` → phần tử giữa **canh giữa theo toàn bề ngang của hàng**, bất kể `justify=start`. Ghi thêm vào Props:

```
direction=row, gap=10px, justify=start, align=center, sizing=fill×fixed, effective_align=center-full-width
```

Lý do phải suy tường minh: đây là idiom "3 cột cân bằng" (phần tử phụ neo hai biên, phần tử chính ở giữa). Figma **không có thuộc tính nào ghi "canh giữa"** — nó là *hệ quả* của việc hai cột biên cùng `FILL`. Bỏ `sizing` đi thì thông tin canh giữa biến mất không dấu vết, và `justify=start` còn lại sẽ được đọc thành canh trái.

Biến thể 2 member (`[hug, fill]` hoặc `[fill, hug]`) → `effective_align=push-end` / `push-start` (một phần tử bị đẩy về cuối/đầu hàng).

Gán `Group ID` theo convention của F3: `R1` = root, `G*` = generic, `F*` = FormField. Sinh **theo thứ tự render** (thứ tự `children` trong Figma = thứ tự Members).

**Surface vào Props, KHÔNG thêm cột:** node có entry `surface[]` (Stage 4.2b) → thêm vào cùng `props` string 3 khoá phẳng, giữ đúng dạng `key=value` mà Stage 4b đang parse:

```
radius=pill, border=solid-all, elevation=card
```

`border=none` cũng **phải ghi tường minh** khi node có `elevation: true` — "bóng, không viền" là một quyết định thiết kế, còn khoá vắng mặt là "không biết", và hai thứ đó dẫn tới hai đoạn code khác nhau.

> Output là **hint dán-được**: step-07 render sẵn bảng markdown 4 cột (`Group ID | Type | Members | Props`) trong `figma_ingest_report.md` — vẫn 4 cột như hợp đồng §2.2 của Stage 4a, thông tin mới nằm trong `Members` (hậu tố sizing) và `Props` (khoá mới). F3 verify + điền vào §2.2, KHÔNG tự phát minh lại.

### Stage 4.4: `control_hint[]` — gợi ý §2.3

Mỗi `INSTANCE` + `TEXT` là input/button → 1 dòng:
- `control_id`: snake_case suy từ (a) tên node nếu đã semantic (`input-merchant-code` → `input_merchant_code`), (b) else `<loại>_<slug(text)>` (`button_tim_kiem`). Tên vô nghĩa (`Frame 427`) → `<TODO: F3 đặt tên>` (U5 — không bịa).
- `figma_component`: tên component instance nguyên văn (step-05 map sang DS).
- `variant_props`: `componentProperties` của instance (vd `{size: md, state: default}`).
- `intent` (button/action only): suy từ variant prop (`Primary` → `primary`, `Danger`/`Destructive` → `destructive`) — không suy được → để trống.

### Stage 4.5: `icon_candidates[]` — gợi ý Icon Legend

Node `VECTOR`/`INSTANCE` là icon khi: tên chứa `icon`/`ic-`/`ic_`, **hoặc** component name bắt đầu bằng `Icon`, **hoặc** kích thước vuông ≤ 32px và không có text con.

Mỗi candidate → `{ node_id, figma_name, icon_name_kebab, size, near_control }`. `icon_name_kebab` là **semantic intent** (`search`, `chevron-down`), không phải tên file Figma. Không suy được intent → `<TODO: F3 đặt tên>`.

Đây là input cho bảng **Icon Legend** bắt buộc ở Stage 4a §2.2 — và là lý do code KHÔNG bao giờ chứa emoji (pre-commit Rule 9).

### Stage 4.6: `copy[]` — text nguyên văn

Mọi `TEXT` còn lại → `{ node_id, text, role, near_control }`. `role` phân loại heuristic:

| role | Tín hiệu |
|---|---|
| `label` | Ngay trên/trái input trong cùng FormField |
| `placeholder` | Nằm trong INSTANCE input, opacity thấp / màu muted |
| `button` | Nằm trong INSTANCE có variant giống button |
| `error` | Màu resolve về nhóm danger/error, hoặc mở đầu bằng cụm cảnh báo |
| `heading` | font-size lớn nhất trong nhánh |
| `body` | còn lại |

**Text nguyên văn là bắt buộc giữ đúng từng ký tự** — đây là nguồn cho bảng Validation §2.3 (Action → Trường hợp lỗi → Thông báo lỗi nguyên văn) và cho `ux_conventions.md`. Không dịch, không sửa chính tả, không rút gọn.

### Stage 4.7: Raw value — đánh dấu, KHÔNG đưa vào chỗ code đọc

Mọi giá trị px/hex/font đi kèm dưới khoá `raw` **và** cờ `raw_only: true`:

```json
"raw": { "raw_only": true, "gap": 14, "padding": [16, 24, 16, 24], "fill": "#1F6FEB",
         "font_size": 13, "radius": 24, "stroke_weight": 1, "stroke_color": "#E5E5E5" }
```

Ý nghĩa cờ: **step-05 snap sang token; Stage 4a/4b/5 KHÔNG được đọc khoá này**. Nếu để dev copy `#1F6FEB` vào code, pre-commit Rule 4 sẽ block — đây là chốt chặn ở tầng spec, trước khi tới đó.

**Phạm vi của lệnh cấm:**

| Loại thông tin | Ở đâu | 4a đọc được? |
|---|---|---|
| Giá trị đo được (px, hex, weight, blur) | `raw` | ❌ |
| **Vai trò / ý định** (`radius_role: pill`, `border.style: solid`, `elevation: true`) | `surface[]` — tầng ngoài | ✅ |
| **Quan hệ bố cục** (`sizing`, `justify`, `align`, `effective_align`, `geometry[].box`) | `layout_groups_hint[]` / `geometry[]` — tầng ngoài | ✅ |
| Tên token đã snap (`radius.lg`, `border.subtle`) | step-05 ghi vào `figma-ds-map.md` | ✅ |

Lệnh cấm nhằm chặn **giá trị hardcode**, không nhằm chặn **ý định thiết kế**. Áp lên cả ý định thì 4a mất luôn radius/border/canh lề — mỗi giá trị đo được phải có một vai trò tương ứng ở tầng ngoài.

### Stage 4.8: Emit `specs/{unit_id}.json` (atomic, sorted)

Một file/unit. State variant nằm trong cùng file, khoá `states.{state}.tree` (không tách file — F3 đọc 1 lần thấy đủ mọi state, khớp L2 mandatory-states audit).

## 4. Decision Points

- **Frame không có Auto Layout nào** (`layoutMode: NONE` toàn bộ) → vẫn emit spec, `layout_groups_hint` = 1 dòng `R1 | Box | ...` **kèm entry `geometry[]` đầy đủ** (Stage 4.2c) + WARN: *"Designer không dùng Auto Layout → composition tree suy từ toạ độ tương đối (`geometry[]`), `confidence` tối đa MEDIUM. F3 đối chiếu ảnh trước khi dán; đề nghị designer bật Auto Layout cho lần sau."* KHÔNG được emit `props: ""` — container rỗng props là thứ đẩy F3 sang đoán mò.
- **Node có `cornerRadius` nhưng thiếu `absoluteBoundingBox`** (không suy được `s = min(w,h)`) → không emit `radius_role`, ghi `warnings[]`. Suy role bằng px tuyệt đối là sai theo thiết kế (§Stage 4.2b).
- **Node fetch 404 / thiếu trong response** (frame bị xoá sau khi map) → unit đó `figma_status: stale`, WARN, tiếp tục unit khác. KHÔNG STOP.
- **Depth 12 vẫn bị cắt** (`children` cuối còn node chưa expand) → WARN liệt kê node bị cắt; tăng `--depth` và fetch lại **chỉ** node đó.
- **`manual` mode không có structure JSON** → bỏ Stage 4.3-4.7, emit spec tối thiểu `{ states: {...}, source: "png-only" }` + WARN đã nêu ở step-02.

## 5. Output

- `{ds_root}/_reference/figma/specs/{unit_id}.json` (mỗi unit mapped 1 file). Khoá per-state: `tree`, `layout_groups_hint[]`, **`surface[]`**, **`geometry[]`**, `control_hint[]`, `icon_candidates[]`, `copy[]`, `node_count_kept`.
- `report_sections[]` += `[SPEC EXTRACT]` (per unit: số node giữ/prune, số layout group, **số surface entry, số geometry entry, số node INSTANCE không tra được radius**, số control hint, số icon, số copy, WARN nếu có).

**Self-check trước khi emit (fail-loud — 3 assert):**

1. Mọi `layout_groups_hint[]` entry có `props` **không rỗng**. Rỗng → bug Stage 4.2c/4.3, không phải "frame không có gì".
2. Không `props` string nào chứa cùng một khoá hai lần (`align=…, align=…`). Có → bug format Stage 4.3.
3. Mọi node có `cornerRadius != 0` trong `raw` đều có entry `surface[]` tương ứng, **hoặc** có dòng trong `warnings[]` giải thích tại sao không. Lệch → radius đang rơi vào lỗ đen giữa `raw` và tầng ngoài.

Fail bất kỳ assert → STOP với tên node cụ thể. Ba lớp thông tin này mất đi thì **không gate nào phía sau bắt được**: DD vẫn đủ section, code vẫn compile, chỉ giao diện là sai.

**Next:** Read fully and follow `./step-05-ds-reconcile.md`
