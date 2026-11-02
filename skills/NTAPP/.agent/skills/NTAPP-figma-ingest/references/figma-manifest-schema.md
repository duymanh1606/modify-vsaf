# Figma Manifest Schema — `figma-manifest.yaml`

> **Version:** v1.0. Đây là **CONTRACT** giữa `ntapp-figma-ingest` (producer) và 4 consumer: Stage 4a `ntapp-feature-design`, Stage 4b `ntapp-ui-generation`, Stage 5 `dev`, và Hook 3 `stage3_input_gate.sh`.
> Đổi schema = đổi contract → phải patch cả 4 consumer. Thêm field optional thì không.

## Vị trí

`{ds_root}/_reference/figma/figma-manifest.yaml` — **per DS root**, mỗi file chỉ chứa unit thuộc DS đó.

Single-DS (không có `registry.yaml`) → đúng 1 file tại family root. Multi-DS → N file; consumer resolve DS root của unit theo `_shared/ds-resolution.md` (nhánh B cho skill, nhánh D cho hook) rồi mới đọc manifest tương ứng.

## Schema

```yaml
schema_version: "1.1"
ds_id: web-admin                  # null nếu single-DS
file_key: AbC123XyZ
figma_version: "1234567890"       # version PINNED của cả run (U4)
figma_last_modified: 2026-08-01T09:12:00Z
ingested_at: 2026-08-05T14:03:11Z
source_mode: api                  # api | manual | mcp

# Scope của LẦN INGEST GẦN NHẤT — quyết định unit nào được re-evaluate, unit nào
# giữ nguyên (xem §Merge semantics). Thiếu block này = manifest v1.0 cũ → coi như
# scope toàn file (mọi unit in-scope).
last_scope:
  pages: ["Thanh toán"]           # [] = toàn file
  node_ids: []
  feature: "Thanh toán"           # null nếu không truyền --feature
  units_in_scope: [SCR-PAY-01, SCR-PAY-02, SCR-PAY-03]

units:
  - unit_id: SCR-LOGIN            # BẮT BUỘC — phải tồn tại trong project_wbs.md
    figma_status: mapped          # mapped | missing | not_in_scope | stale | ignored
    node_id: "12:340"             # null khi figma_status != mapped
    base_name: "SCR-LOGIN v3"     # tên frame nguyên văn trong Figma
    page: Product
    matched_by: exact-id          # exact-id | name-similarity | journey-order | previous-manifest | manual
    confidence: HIGH              # HIGH | MEDIUM | LOW
    approved_by: ngoanh           # ai ký ở HITL step-03
    approved_at: 2026-08-05T13:58:02Z
    checksum: "sha256:9f2a1c0b4e7d8a35"
    drift: false                  # true khi checksum đổi so với lần ingest trước
    states:
      - state: default            # default | empty | loading | error | success | <chuỗi tự do>
        node_id: "12:340"
        state_recognized: true
        frame_exported: true
        frame: _reference/figma/frames/SCR-LOGIN.png        # relative tới DS root (U2)
      - state: error
        node_id: "12:411"
        state_recognized: true
        frame_exported: true
        frame: _reference/figma/frames/SCR-LOGIN__error.png
    spec: _reference/figma/specs/SCR-LOGIN.json
    contains: []                  # case D — widget nhúng trong frame này

  - unit_id: WGT-FILTER
    figma_status: mapped
    node_id: "12:355"             # node con bên trong frame của SCR-LIST
    parent_unit: SCR-LIST         # chỉ có ở unit đến từ contains[]
    # ... phần còn lại như trên

  - unit_id: SCR-EXPORT
    figma_status: missing         # ĐÃ XÉT, Figma thật sự không có frame → 4a author mode
    node_id: null
    reason: "Không frame nào match ở lần ingest 2026-08-05"
    last_evaluated_at: 2026-08-05T13:58:02Z

  - unit_id: SCR-LOGIN-OLD
    figma_status: not_in_scope    # CHƯA XÉT lần này (ngoài scope harvest) — KHÁC missing
    node_id: null
    reason: "Ngoài scope ingest 2026-08-05 (pages=[Thanh toán])"
    last_evaluated_at: 2026-07-20T10:00:00Z   # lần cuối THỰC SỰ được xét

ignored_frames:
  - base_name: Sandbox
    node_id: "44:12"
    page: Product
    ignore_reason: "designer xác nhận là nháp (HITL step-03)"

summary:
  mapped: 12
  missing: 2
  ignored: 4
  frames_exported: 18
  token_gaps: 7
  contrast_fails: 1
```

## Field bắt buộc (step-07 validate; thiếu → STOP)

Cấp file: `schema_version`, `file_key`, `figma_version`, `ingested_at`, `source_mode`, `last_scope`, `units`, `summary`.
Cấp unit: `unit_id`, `figma_status`. Khi `figma_status: mapped` thêm: `node_id`, `base_name`, `matched_by`, `confidence`, `approved_by`, `checksum`, `states` (≥1), `spec`.

## Merge semantics — manifest được MERGE, KHÔNG replace (v1.1)

Đây là bất biến quan trọng nhất của schema. Ingest hầu như luôn chạy **hẹp scope** (feature mới → 1 page Figma), nên nếu step-07 ghi đè manifest thì mọi unit của feature cũ bị hạ xuống `missing` → Stage 4a im lặng rơi về author mode dù Figma vẫn còn frame, và Hook 3 **không bắt được** (nó chỉ so checksum khi status là `mapped`). Lỗi loại này không ai báo, chỉ là chất lượng DD tự dưng kém đi.

**Định nghĩa "in-scope" của một unit ở lần ingest hiện tại** (xét theo thứ tự, dừng ở điều kiện đầu tiên đúng):

| # | Điều kiện | Kết luận |
|---|---|---|
| 1 | Có `--feature` **và** unit ∈ danh sách unit của feature đó | in-scope |
| 2 | Có `--feature` **và** unit ∉ danh sách đó | **out-of-scope** |
| 3 | Không `--feature`, harvest scope là toàn file (`pages: []` + `node_ids: []`) | in-scope |
| 4 | Entry cũ của unit có `page` ∈ pages đã harvest lần này | in-scope |
| 5 | Unit chưa có entry nào trong manifest cũ | in-scope (ứng viên mới) |
| 6 | Còn lại | **out-of-scope** |

**Luật ghi:**

- Unit **in-scope** → re-evaluate đầy đủ; kết quả có thể là `mapped` / `missing` / `ignored`. Set `last_evaluated_at` = giờ hiện tại.
- Unit **out-of-scope** → **giữ nguyên entry cũ verbatim**. KHÔNG đổi `figma_status`, KHÔNG đổi `checksum`, KHÔNG chạm `last_evaluated_at`.
- Unit out-of-scope mà **chưa từng** có entry (mới xuất hiện trong WBS, chưa ingest lần nào) → ghi `figma_status: not_in_scope` + `reason` nêu scope đã loại nó.

**`missing` vs `not_in_scope` — hai thứ khác nhau, đừng trộn:**

| | Nghĩa | Stage 4a | Hook 3 |
|---|---|---|---|
| `missing` | Đã xét, Figma **thật sự không có** frame cho unit này | author mode (đúng ý) | pass |
| `not_in_scope` | **Chưa xét** lần này — không biết Figma có gì | dùng entry cũ nếu có; không có thì author mode | **WARN** nếu DD có `figma_ref` (chưa verify được drift) |

## Bất biến

1. **`unit_id` phải tồn tại trong `project_wbs.md`.** Manifest không bao giờ là nguồn khai sinh unit.
2. **`checksum` chỉ do step-07 ghi** — công thức ở step-07 Stage 7.1. Manifest có unit `mapped` mà `checksum` rỗng = manifest chưa finalize → consumer coi như chưa ingest.
3. **Không lưu URL Figma đầy đủ, không lưu signed URL S3** (U6). Chỉ `file_key` + `node_id`; ai cần mở thì dựng link từ 2 mảnh đó.
4. **Path trong manifest là relative tới DS root** (U2) — portability cross-machine.
5. **`figma_version` cấp file là version của lần ingest gần nhất.** Unit out-of-scope giữ dữ liệu từ version cũ hơn — hợp lệ và có chủ ý (`last_evaluated_at` cho biết dữ liệu của unit đó cũ tới đâu). Đừng suy ra "mọi unit đều ở version này".
6. **Manifest MERGE, không replace** (xem §Merge semantics). Step-07 ghi đè toàn file = bug.

## Consumer đọc gì

| Consumer | Field dùng | Hành vi |
|---|---|---|
| Stage 4a `feature-design` step-02 | `units[].figma_status`, `spec`, `states[].frame` | `mapped` → transcribe mode (đọc spec + frame). `missing`/`not_in_scope`/`stale` → author mode như cũ |
| Stage 4a (ghi ngược vào DD §1) | `file_key`, `node_id`, `figma_version`, `checksum` | Ghi thành `figma_ref` trong DD — nguồn so sánh của Hook 3 |
| Stage 4b `ui-generation` step-01 | (qua `figma-ds-map.md`, không đọc manifest trực tiếp) | Bậc C-1 reuse ladder |
| Stage 5 `dev` | `states[].frame` | Visual reference qua link trong story. CẤM copy CSS (Rule 4) |
| Hook 3 `stage3_input_gate.sh` | `units[].unit_id`, `figma_status`, `checksum` | `mapped` + checksum lệch → **block**. `not_in_scope` + DD có `figma_ref` → **warn** (chưa verify được). `missing` → pass |

## Quan hệ với `figma_ref` trong DD

DD (Stage 4a) ghi ở §1:

```markdown
- **figma_ref:** `AbC123XyZ` / node `12:340` / version `1234567890` / checksum `sha256:9f2a1c0b4e7d8a35`
```

Hook 3 so `checksum` trong dòng này với `units[].checksum` của manifest hiện tại. Lệch → Figma đã đổi sau khi DD ký → block kèm hint chạy lại `/ntapp-figma-ingest`. Đây là toàn bộ phần Figma nằm trong slice-loop: **read-only, 0 network**.
