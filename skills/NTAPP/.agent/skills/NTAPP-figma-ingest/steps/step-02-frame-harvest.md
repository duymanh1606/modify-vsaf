# Step 2: Frame Harvest

## GOAL

Lọc ra **candidate frame** (những frame trông như màn hình thật) từ document tree, bỏ nháp/cover/archive/component page. Output `frames_raw.json` — danh sách gọn để step-03 mapping.

## 1. Persona

Procedural. Tuân thủ **U7 (context hygiene)** nghiêm ngặt: document tree KHÔNG vào context, mọi lọc bằng `jq` trên file.

## 2. Inputs

- `figma-source.json` (step-01) — `file_key`, `version` pinned, `scope`.
- Config: `scope_pages`, `frame_filter`, `ignore_name_patterns`, `max_frames`.
- (`manual` mode) `inbox/nodes.json` + danh sách file trong `inbox/frames/`.

## 3. Pipeline

### Stage 3.1: Fetch tree ở độ sâu tối thiểu

```bash
# Có scope.node_ids → fetch đúng node đó
bash <skill_dir>/scripts/figma-fetch.sh nodes --ids "1234:567" --depth 3 \
  --out "{output_root}/.work/tree.json"

# Không có → fetch document shallow để liệt kê page + frame top-level
bash <skill_dir>/scripts/figma-fetch.sh file-tree --depth 3 \
  --out "{output_root}/.work/tree.json"
```

`--depth 3` là đủ để thấy page → frame → child cấp 1 (nhận diện frame rỗng). **KHÔNG** fetch full depth ở đây — step-04 mới fetch sâu, và chỉ cho frame đã mapped. Đây là điểm chặn chi phí chính: file 200 frame × full depth có thể ra hàng chục MB.

`manual` mode: dùng `inbox/nodes.json` làm `tree.json` (schema plugin khác nhau → chỉ cần lấy được `id`, `name`, `type`, `children`; không đủ field → coi như chỉ có PNG, mỗi file trong `inbox/frames/` thành 1 candidate với `node_id: null`).

### Stage 3.2: Lọc candidate (thứ tự áp dụng)

Chạy trên `tree.json` bằng `jq`, theo đúng thứ tự:

1. **Page scope** — `scope.pages` non-empty → chỉ giữ page có `name` trong list. Có `scope.node_ids` → bỏ qua bước này.
2. **Node type** — giữ `FRAME`, `SECTION`, `COMPONENT_SET`; bỏ `COMPONENT` đơn lẻ (đó là DS component, không phải màn — trừ khi unit là `WGT-*`, xem 5).
3. **Depth** — chỉ frame **top-level trong page** (hoặc con trực tiếp của `SECTION`). Frame lồng trong frame là thành phần của màn, không phải màn.
4. **Blacklist tên** — bỏ nếu khớp bất kỳ regex trong `ignore_name_patterns` (default: `^_`, `^Cover`, `^Archive`, `^Draft`, `^Copy of `, `^Untitled`).
5. **Whitelist tên** — `frame_filter` set → chỉ giữ frame khớp.
6. **Frame rỗng** — `children` rỗng hoặc chỉ chứa `TEXT` đơn (thường là note của designer) → bỏ.
7. **Dedupe** — cùng `name` + cùng size → giữ frame có `children` nhiều nhất, ghi các bản còn lại vào `duplicates[]` (để step-03 hỏi nếu cần).

### Stage 3.3: Nhận diện state variant

Frame thể hiện **state khác nhau của cùng một màn** là pattern rất phổ biến (designer vẽ `Danh sách`, `Danh sách / empty`, `Danh sách - loading`). Tách bằng suffix separator `/`, `-`, `—`, `()`:

| Tên frame | base | state |
|---|---|---|
| `SCR-LIST` | `SCR-LIST` | `default` |
| `SCR-LIST / empty` | `SCR-LIST` | `empty` |
| `SCR-LIST - loading` | `SCR-LIST` | `loading` |
| `SCR-LIST (error)` | `SCR-LIST` | `error` |

Chuẩn hoá state về vocabulary Layout Best-Practices L2: `default` / `empty` / `loading` / `error` / `success`. Từ khác (`hover`, `mobile`, `v2`) → giữ nguyên chuỗi + `state_recognized: false` (step-03 hỏi người).

Ghi thành `variant_group` — step-03 map **base** với unit, các state thành `states[]`.

### Stage 3.4: Emit `frames_raw.json` (atomic, U1; sorted, U4)

```json
{
  "candidates": [
    {
      "base_name": "SCR-LIST",
      "child_count": 34,
      "duplicates": [],
      "node_id": "12:340",
      "page": "Product",
      "size": { "h": 1024, "w": 1440 },
      "state": "default",
      "state_recognized": true,
      "variant_group": "SCR-LIST"
    }
  ],
  "excluded_count": { "blacklist": 11, "empty": 3, "nested": 47, "page_scope": 62 },
  "total_candidates": 18
}
```

`excluded_count` không phải trang trí — người dùng cần thấy "62 frame bị loại vì page scope" để biết mình có set scope sai không.

## 4. Decision Points

- **0 candidate** → STOP: *"Không frame nào qua filter. Loại vì: {excluded_count}. Kiểm `scope_pages` (page khả dụng: {pages_available từ figma-source.json}) hoặc nới `ignore_name_patterns`."*
- **> `max_frames` (default 80)** → **WARN + PAUSE hỏi người**: *"{N} candidate — nhiều hơn ngưỡng {max_frames}. Ingest hết sẽ tốn thời gian export và bảng mapping sẽ rất dài. Thu hẹp `scope_pages` / `frame_filter`, hay tiếp tục toàn bộ?"* Người chọn tiếp tục → tiếp, không STOP.
- **`manual` mode chỉ có PNG, không có `nodes.json`** → WARN rõ: *"Chỉ có PNG, không có structure → step-04 KHÔNG sinh được `layout_groups_hint`. F3 sẽ phải đoán bố cục từ ảnh. Muốn giữ phần này thì cần plugin export JSON hoặc `source_mode: api`."* Tiếp tục, không STOP.
- **`state_recognized: false` cho ≥1 frame** → không xử lý ở đây, chuyển sang step-03 hỏi kèm bảng mapping (gộp 1 lần hỏi, không hỏi 2 lần).

## 5. Output

- `{output_root}/.work/tree.json` (intermediate).
- `{output_root}/.work/frames_raw.json`.
- `report_sections[]` += `[HARVEST]` (số candidate, số loại theo lý do, số variant group).

**Next:** Read fully and follow `./step-03-unit-mapping.md`
