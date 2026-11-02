# Step 6: Frame Export

## GOAL

Export PNG mỗi unit (+ mỗi state) vào `frames/` — đây là thứ Agent F3 ở Stage 4a **thực sự xem** khi transcribe wireframe.

Step này **graceful**: export fail không STOP run (specs từ step-04 vẫn dùng được).

## 1. Persona

Procedural. Tuân thủ **U6 (URL hygiene)** — signed URL S3 tuyệt đối không được lưu vào artifact.

## 2. Inputs

- `figma-manifest.yaml` — unit mapped + `states[]` + `node_id`.
- Config `export_scale` (default 2).
- (`manual` mode) file PNG trong `inbox/frames/`.

## 3. Pipeline

### Stage 6.1: Gom danh sách node cần export

Một entry/`(unit_id, state)`. Unit có `figma_status: missing` hoặc `stale`, frame `ignore: true` → không export.

Tên file đích:
- `frames/{unit_id}.png` cho state `default`.
- `frames/{unit_id}__{state}.png` cho state khác (`SCR-LIST__empty.png`).

Dùng `__` (2 gạch dưới) làm separator để phân biệt với dấu `-` trong chính unit id (`SCR-LOGIN`).

### Stage 6.2: Request render + download

Ghi trước file **`name-map.json`** — INPUT của script, map `node_id` → basename đích (không đuôi):

```json
{ "12:340": "SCR-LOGIN", "12:411": "SCR-LOGIN__error" }
```

```bash
bash <skill_dir>/scripts/figma-fetch.sh images \
  --ids "12:340,12:411" --scale 2 --format png \
  --dest "{output_root}/frames" \
  --name-map "{output_root}/.work/name-map.json"
```

Script ghi thẳng tên file đích (không cần pass rename) và in **TSV** ra stdout — `ok<TAB>node<TAB>path` / `fail<TAB>node<TAB>reason`. Đọc TSV này để điền `frame_exported`. Entry thiếu trong name-map → fallback `node_{id}.png` (không mong muốn — kiểm lại name-map nếu thấy tên này).

Cơ chế 2 pha của Figma (script lo, ghi lại ở đây để hiểu khi debug):
1. `GET /v1/images/:key?ids=...` → JSON `{"images": {"12:340": "https://s3..."}}` — **signed URL, hết hạn sau ít phút**.
2. Download từng URL → ghi `.part` → rename (U1).

Script **không** in URL ra stdout và **không** lưu vào bất kỳ artifact nào (U6) — URL rot thì manifest trỏ vào rác.

Kích thước: `scale 2` cho desktop 1440px ra ~2880px. File > 4MB → tự hạ scale về 1 cho node đó + ghi WARN (PNG chỉ để người xem, không cần pixel-perfect).

### Stage 6.3: `manual` mode

Copy từ `inbox/frames/` sang `frames/` theo mapping đã ký ở step-03 (tên file trong inbox thường là tên frame, không phải unit id → rename theo mapping). File thiếu → unit đó ghi WARN, không STOP.

### Stage 6.4: Verify

Mỗi file: tồn tại + kích thước > 0 + magic bytes PNG (`89 50 4E 47`). Fail → xoá file lỗi, WARN, ghi `frame_exported: false` cho unit đó.

## 4. Decision Points

- **`/v1/images` trả `err` non-null** (thường: node quá lớn để render) → WARN, `frame_exported: false`, tiếp tục unit khác. Hint trong report: *"Frame `{name}` quá lớn để Figma render — nhờ designer tách frame nhỏ hơn, hoặc F3 dùng specs JSON thay ảnh."*
- **429 rate-limit** → script tự backoff (exponential, ≤3 lần). Hết retry → WARN, `frame_exported: false` cho phần còn lại + hint chạy lại step này sau ít phút (re-ingest sẽ skip unit đã export nhờ checksum).
- **Download timeout / URL hết hạn** → request lại `/v1/images` cho đúng node đó (≤1 lần), rồi WARN nếu vẫn fail.
- **Toàn bộ export fail** → **KHÔNG STOP**, nhưng WARN nặng: *"0 PNG export được. Stage 4a sẽ chỉ có specs JSON (đủ để dựng Layout Groups, thiếu cảm nhận thị giác). Kiểm quyền file / thử lại sau."*

## 5. Output

- `{ds_root}/_reference/figma/frames/{unit_id}[__{state}].png`.
- Cập nhật `frame_exported: true|false` per `(unit, state)` — step-07 ghi vào manifest.
- `report_sections[]` += `[FRAME EXPORT]` (số file, tổng dung lượng, danh sách fail + lý do).

**Next:** Read fully and follow `./step-07-emit.md`
