# Step 1: Source Resolve

## GOAL

Chuẩn hoá nguồn Figma thô (link người dán / config / inbox) thành `figma-source.json` — provenance **pinned version** mà mọi step sau bám vào.

## 1. Persona

Không có persona riêng — step procedural. Tuân thủ Universal Rules (U1-U7), đặc biệt **U6 (secret hygiene)** và **U7 (không đưa raw response vào context)**.

## 2. Inputs

- Arg người dùng: link Figma / `--file-key <key>` / `--tokens-only` / `--ds <ds_id>` / `--feature <name>`.
- Block `ntapp-figma-ingest` trong `.bmm-config.yaml` (`source_mode`, `file_key`, `scope_pages`).
- env `FIGMA_TOKEN` (mode `api`).

## 3. Pipeline

### Stage 3.1: Parse link → `file_key` + scope node

Nhận **2 format link** (Figma đổi `/file/` → `/design/`, link cũ vẫn lưu hành):

```
https://www.figma.com/design/{file_key}/{slug}?node-id=1234-567
https://www.figma.com/file/{file_key}/{slug}?node-id=1234-567
```

Thủ tục:
1. `file_key` = capture group của regex `figma\.com/(?:design|file)/([A-Za-z0-9]+)`.
2. `node-id` (nếu có) = query param `node-id`. **Chuyển `-` → `:`** — URL dùng `1234-567`, API cần `1234:567`. Bỏ bước này thì mọi call `nodes?ids=` trả rỗng và rất khó debug.
3. Không có link → dùng `config.file_key`. Cả hai thiếu → STOP (§4).
4. Có `node-id` → `scope.node_ids = [<id>]` (ingest 1 frame/section). Không có → `scope.pages = config.scope_pages` (rỗng = mọi page).

> Người dùng dán link kèm text khác (thường gặp) → extract bằng regex, KHÔNG yêu cầu dán lại.

### Stage 3.1b: `--feature <name>` (optional)

Ghi `scope.feature = <name>` nếu có. **Bất biến: `--feature` KHÔNG bao giờ lọc phía Figma** — scope Figma chỉ do `scope_pages`/`node_ids` quyết định. Nếu để nó lọc cả frame thì có 2 nguồn cùng quyết "đang làm màn nào", lệch nhau là mất frame im lặng.

Tác dụng duy nhất, tất cả nằm ở step-03: (a) cắt ngắn danh sách **phía WBS** trong bảng HITL, (b) sinh dòng **coverage** (*"feature có N unit → mapped M, thiếu K"*), (c) là tín hiệu #1 của luật in-scope (`references/figma-manifest-schema.md` §Merge semantics).

Không truyền → `scope.feature = null`; step-03 tự suy + xác nhận trong chính bảng HITL. **KHÔNG hỏi lại ở step này**, không block.

### Stage 3.2: Validate nguồn theo `source_mode`

**`api`:**
```bash
bash <skill_dir>/scripts/figma-fetch.sh whoami
```
- Exit 0 → tiếp. 401/403 → STOP (§4). Mọi network từ đây đi qua script này (U7).

**`manual`:** liệt kê `{output_root}/inbox/`. Rỗng → STOP kèm checklist §4.

**`mcp`:** session interactive → OK nhưng **chỉ cho phép scope 1 unit** (mode này dùng khi designer sửa 1 màn, re-ingest nhanh). Headless → set `source_mode: api` + WARN.

### Stage 3.3: Fetch file meta + PIN version (U4)

```bash
bash <skill_dir>/scripts/figma-fetch.sh file-meta --out "{output_root}/.work/file-meta.json"
```

Đọc **bằng `jq`** (không đọc raw file vào context):
```bash
jq -r '.name, .version, .lastModified, ([.document.children[].name] | join("|"))' "{output_root}/.work/file-meta.json"
```

`version` lấy được **phải được truyền vào mọi call sau** (`--version <v>`). Đây là điều kiện để checksum ở step-07 có nghĩa: designer sửa file giữa run sẽ không tạo ingest nửa cũ nửa mới.

### Stage 3.4: Resolve DS root đích

- **full mode:** chưa biết unit → chỉ resolve **family root** ở đây; DS root per-unit resolve tại step-03 sau khi có mapping (`_shared/ds-resolution.md` nhánh B/C).
- **`--tokens-only`:** không có unit để suy ra DS. Family root có `registry.yaml` **và** ≥2 systems **và** không có `--ds` → STOP: *"Multi-DS: chỉ định `--ds <ds_id>` để biết export token cho DS nào. Các `ds_id` khả dụng: {liệt kê từ registry}."* Single-DS → DS root = family root.

### Stage 3.5: Emit `figma-source.json` (atomic, U1)

```json
{
  "file_key": "AbC123",
  "file_name": "BMS — Product",
  "figma_last_modified": "2026-08-01T09:12:00Z",
  "mode": "api",
  "pages_available": ["Product", "Flows", "Archive"],
  "scope": { "feature": "Thanh toán", "node_ids": [], "pages": ["Product", "Flows"] },
  "version": "1234567890",
  "run_mode": "full"
}
```

Sorted keys, 2-space (U4). Ghi vào `{ds_root}/_reference/figma/figma-source.json` (`--tokens-only` multi-DS: DS đã chọn ở 3.4; full mode: ghi tạm ở family root `_reference/figma/`, step-03 copy sang từng DS root khi mapping đã chốt).

## 4. Decision Points

- **Không resolve được `file_key`** → STOP: *"Cần link Figma hoặc `file_key`. Format nhận được: `figma.com/design/{key}/...` hoặc `figma.com/file/{key}/...`. Hoặc khai `file_key` trong block `ntapp-figma-ingest` của `.bmm-config.yaml`."*
- **`FIGMA_TOKEN` không set** (mode `api`) → STOP: *"Set env `FIGMA_TOKEN` (Figma → Settings → Security → Personal access tokens, scope `file_content:read`). Đừng đặt vào `.bmm-config.yaml` — file đó committed. Không có PAT → đổi `source_mode: manual`."*
- **401/403 từ `whoami` hoặc `file-meta`** → STOP: *"PAT không hợp lệ hoặc account không có quyền xem file `{file_key}`. Kiểm: PAT còn hiệu lực? account đã được invite vào file/team? file thuộc org khác?"*
- **404 `file-meta`** → STOP: *"`file_key` không tồn tại — link có thể trỏ prototype/branch. Dán link từ thanh địa chỉ khi mở file ở chế độ Design."*
- **`manual` + inbox rỗng** → STOP kèm checklist export cho designer:
  1. PNG mỗi frame → `inbox/frames/{tên-frame}.png` (**bắt buộc** — thiếu thì ingest vô nghĩa).
  2. Structure JSON (plugin export JSON) → `inbox/nodes.json` (**khuyến nghị mạnh** — thiếu là **mất Auto Layout → Layout Groups**, giá trị lớn nhất của ingest; F3 phải đoán bố cục lại từ ảnh).
  3. Token W3C JSON (plugin Tokens Studio) → `inbox/tokens.json` (cho `--tokens-only`).
- **`mcp` + scope > 1 unit** → STOP: *"`source_mode: mcp` chỉ ingest 1 unit/lần (MCP phụ thuộc selection trên canvas). Dùng `api` cho batch."*

## 5. Output

- `{ds_root}/_reference/figma/figma-source.json`.
- `{output_root}/.work/file-meta.json` (intermediate, không commit — thêm `.work/` vào `.gitignore` nếu chưa có).
- `report_sections[]` += `[SOURCE]` (file name, version pinned, mode, scope, số page).

## 6. Branch

- `run_mode == "tokens-only"` → **Next:** `./step-01t-token-export.md`
- else → **Next:** `./step-02-frame-harvest.md`
