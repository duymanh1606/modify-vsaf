# Step 3: Unit Mapping ⛔ HITL GATE

> **Acting as:** [frame-mapper](../agents/frame-mapper.md) — đọc persona đầy đủ trước khi thực thi.

## GOAL

Chốt bảng **`WBS unit ↔ Figma frame`** và emit `figma-manifest.yaml`. Đây là **trái tim skill** và là input người thật duy nhất không automate được: không có tín hiệu nào trong hệ thống nói frame *"Đăng nhập v3 (final)"* là `SCR-LOGIN`.

## 1. Persona

Adopt [frame-mapper](../agents/frame-mapper.md). Persona declare: role + tín hiệu mapping + thang confidence + 4 case lệch + constraints. Thủ tục orchestration ở file này.

## 2. Inputs

- `frames_raw.json` (step-02).
- `project_wbs.md` — **SSoT của danh sách unit**. Lấy mọi ID prefix `SCR-*` / `WGT-*` (cột đầu markdown table). BE (`MPF-*`, `HUB-*`, ...) **không** tham gia mapping.
- (Optional) `ux_design.md` §4 Journey Screen Table — thứ tự màn trong journey, làm tín hiệu 2.
- `{family_root}/registry.yaml` (nếu multi-DS) — resolve DS root per unit.
- Manifest cũ `figma-manifest.yaml` (nếu re-ingest) — giữ mapping đã ký, không hỏi lại.

## 3. Pipeline

### Stage 3.1: Load universe 2 chiều

- **Chiều Figma:** `candidates[]` đã gom theo `variant_group` (step-02) — map ở mức **base**, không map từng state. Scope phía này **chỉ** do `scope_pages`/`node_ids` quyết (đã lọc ở step-02).
- **Chiều WBS:** mọi `SCR-*`/`WGT-*` trong `project_wbs.md`, kèm cột mô tả để làm tín hiệu semantic. **Đây là chiều bị `--feature` cắt ngắn** (Stage 3.1b).

### Stage 3.1b: Xác định feature scope (cắt ngắn CHIỀU WBS)

| Trường hợp | Xử lý |
|---|---|
| `scope.feature` có giá trị (step-01) | Lọc chiều WBS còn unit của feature đó. Nguồn danh sách unit, theo thứ tự: slice manifest `NTAPP-output/Stage_2_Architecture/slices/*.md` (units[] của slice thuộc feature) → cluster/epic tương ứng trong `project_wbs.md` → `ux_design.md` §4 journey screen table. Không nguồn nào khớp tên feature → **WARN + coi như không truyền** (đi nhánh dưới), KHÔNG STOP |
| `scope.feature` = null | **Tự suy:** chạy Stage 3.2 trước trên full WBS → lấy các unit match `confidence: HIGH`/`MEDIUM` → tra ngược feature/cluster chứa chúng trong WBS/slice manifest → nếu ≥2 unit cùng 1 feature thì đó là feature suy đoán. Đưa vào bảng HITL để xác nhận (Stage 3.5), **KHÔNG hỏi thành vòng riêng** |
| Suy không ra (0-1 unit match, hoặc match rải rác nhiều feature) | Giữ full WBS. Bảng dài hơn nhưng **không sai** — luật merge (Stage 3.3b) đã chặn việc ghi đè nhầm unit ngoài scope |

⛔ **Bất biến:** `--feature` (dù truyền tay hay suy đoán) **KHÔNG bao giờ** lọc bớt `candidates[]` phía Figma. Frame nằm ngoài feature nhưng trong scope Figma vẫn phải hiện ở danh sách "Frame chưa dùng" để người thấy — biết đâu designer để lẫn màn của feature này ở page khác.

### Stage 3.2: Propose mapping (per persona §3 tín hiệu)

Áp tín hiệu theo thứ tự, dừng ở tín hiệu đầu cho kết quả DUY NHẤT — ghi `matched_by` + `confidence`:

| # | Tín hiệu | Confidence khi khớp |
|---|---|---|
| 1 | `base_name` **chứa đúng ID unit** (`SCR-LOGIN`, case-insensitive, bỏ dấu phân cách) | **HIGH** |
| 2 | Normalized name similarity ≥ 0.85 với mô tả unit trong WBS (bỏ dấu tiếng Việt, lowercase, bỏ số version `v2`/`final`/`copy`) | **MEDIUM** |
| 3 | Thứ tự frame trong page khớp thứ tự màn trong `ux_design.md` §4 journey **và** similarity ≥ 0.6 | **MEDIUM** |
| 4 | Không tín hiệu nào | **LOW** → bắt buộc người map tay |

**Re-ingest:** unit đã có mapping đã ký trong manifest cũ **và** `base_name` không đổi → carry over, `matched_by: previous-manifest`, `confidence: HIGH`, KHÔNG hỏi lại.

### Stage 3.3: Phân loại 4 case lệch (persona §4)

| Case | Điều kiện | Xử lý |
|---|---|---|
| **A. Frame không map unit nào** | Frame còn lại sau khi mọi unit đã có frame | Hỏi người: nháp/bỏ (`ignore: true`) **hay** màn thật? Trả lời "màn thật" → **STOP**: *"Frame `{name}` là màn thật nhưng không có unit tương ứng trong WBS. WBS là SSoT — thêm unit bằng `/ntapp-architecture-design --append` rồi chạy lại. KHÔNG để Figma thành inventory thứ hai."* |
| **B. Unit không có frame** | Unit **in-scope** (Stage 3.3b) không match frame nào | `figma_status: missing` → unit đó **fallback author mode** ở Stage 4a. **KHÔNG block** (feature có thể ingest từng phần). ⚠️ Chỉ áp cho unit in-scope — unit out-of-scope đi luật merge, KHÔNG được gán `missing` |
| **C. 1 unit ↔ nhiều frame** | Nhiều `variant_group` cùng trỏ 1 unit, hoặc 1 group có nhiều state | State đã nhận diện → `states[]`. Nhiều group khác nhau cùng unit → hỏi người chọn group nào là canonical, còn lại `ignore: true` |
| **D. 1 frame ↔ nhiều unit** | Frame chứa cả screen và widget nhúng | `contains[]`: mỗi widget khai `unit_id` + `node_id` con. Người chỉ định node con (hoặc để trống → widget đó `figma_status: missing`) |

### Stage 3.3b: Phân loại in-scope / out-of-scope (BẮT BUỘC — chống ghi đè)

Ingest hầu như luôn hẹp scope (feature mới → 1 page Figma). Không có bước này, unit của feature cũ sẽ bị hạ xuống `missing` và Stage 4a im lặng rơi về author mode dù Figma vẫn còn frame — Hook 3 **không bắt được** vì nó chỉ so checksum khi status là `mapped`.

Áp **luật in-scope** ở `references/figma-manifest-schema.md` §Merge semantics (6 điều kiện, xét theo thứ tự) cho **mọi** unit `SCR-*`/`WGT-*` trong WBS — kể cả unit đã bị Stage 3.1b cắt khỏi bảng HITL.

Kết quả 3 nhóm:

| Nhóm | Xử lý ở step này | Ghi vào manifest (step-07) |
|---|---|---|
| **in-scope** | Chạy Stage 3.2 + 3.3 đầy đủ, đưa vào bảng HITL | `mapped` / `missing` / `ignored` + `last_evaluated_at` = giờ hiện tại |
| **out-of-scope, CÓ entry cũ** | KHÔNG xét, KHÔNG đưa vào bảng HITL | **giữ nguyên entry cũ verbatim** — không đổi status/checksum/`last_evaluated_at` |
| **out-of-scope, KHÔNG có entry cũ** | KHÔNG xét | `figma_status: not_in_scope` + `reason` nêu scope đã loại nó |

`missing` = "đã xét, Figma thật sự không có frame". `not_in_scope` = "chưa xét, không biết". Trộn hai cái này là gốc của bug ghi đè.

### Stage 3.4: Resolve DS root per unit (multi-DS)

Theo `_shared/ds-resolution.md` **nhánh B.4** cho từng unit đã map: thẻ `repo:` ở Cluster Header WBS (primary) → `id_prefixes` → `modules` → `default_ds`. Conflict giữa thẻ WBS và registry hints → **STOP báo mismatch** (không chọn im lặng theo bên nào). Không tín hiệu nào khớp → đưa vào bảng HITL cùng Stage 3.5 (hỏi 1 lần, không hỏi 2 vòng).

Single-DS (không có `registry.yaml`) → mọi unit dùng family root, bỏ qua stage này.

### Stage 3.5: ⛔ HITL — trình bảng, chờ người ký

Trình **một** bảng duy nhất (gộp cả state chưa nhận diện ở step-02 Stage 3.3 và DS chưa resolve ở 3.4 — người trả lời 1 lượt):

```markdown
## Mapping đề xuất — feature `Thanh toán` (suy đoán) — {N} unit in-scope / {M} frame

| WBS unit | Mô tả (WBS) | Frame đề xuất | States | DS | Tín hiệu | Confidence |
|---|---|---|---|---|---|---|
| SCR-PAY-01 | Chọn phương thức | `SCR-PAY-01` | default, error | web-admin | exact-id | HIGH |
| SCR-PAY-02 | Xác nhận GD | `Thanh toán B2 v3` | default, empty | web-admin | name-similarity 0.88 | MEDIUM |
| SCR-PAY-03 | Kết quả | — | — | — | — | LOW → cần map tay |

**Coverage:** feature `Thanh toán` có 6 unit → mapped 5, thiếu 1 (`SCR-PAY-03`)
**Frame chưa dùng:** `Sandbox`, `Note cho dev` → đề xuất `ignore: true`
**Unit in-scope chưa có frame:** `SCR-PAY-06` → `figma_status: missing` (Stage 4a author mode)
**Giữ nguyên, KHÔNG xét lần này (out-of-scope):** 34 unit — `SCR-LOGIN`, `SCR-DASH`, … *(entry cũ giữ verbatim)*
**Cần bạn xác nhận:**
  (1) Feature đang ingest là `Thanh toán` — đúng không? (suy từ 5 unit đã match; sai thì cho tôi tên đúng)
  (2) State `mobile` của `SCR-PAY-02` — giữ hay bỏ?
  (3) `SCR-PAY-03` thuộc frame nào?
```

Dòng **Coverage** chỉ in khi có feature (truyền tay hoặc suy đoán được) — nó trả lời *"designer vẽ đủ màn cho feature này chưa?"*, thứ bảng full-WBS không nói được.

Dòng **out-of-scope** chỉ liệt kê tên, **không** đưa vào bảng chính — mục đích là để người thấy chúng được **bảo toàn**, không phải để duyệt lại.

Chờ người trả lời `approved` (hoặc sửa từng dòng). **KHÔNG tự tiếp tục** khi còn dòng `confidence: LOW` chưa được người quyết (U5). Người bác feature suy đoán → dùng tên họ đưa, quay lại Stage 3.1b lọc lại (1 vòng, không lặp vô hạn).

### Stage 3.6: Emit `figma-manifest.yaml` (atomic, U1 — MERGE, không replace)

Schema đầy đủ: [references/figma-manifest-schema.md](../references/figma-manifest-schema.md). Ghi **per DS root** — mỗi manifest chỉ chứa unit thuộc DS đó (multi-DS: N file; single-DS: 1 file). Copy `figma-source.json` từ family root sang từng DS root kèm theo (mỗi bản self-contained, audit được độc lập).

Thủ tục ghi:
1. Load manifest cũ (nếu có). `schema_version: "1.0"` (không có `last_scope`) → coi như lần trước scope toàn file.
2. Với unit **in-scope** → thay entry bằng kết quả mới. Với unit **out-of-scope có entry cũ** → copy entry cũ **nguyên xi**. Với unit **out-of-scope không có entry** → tạo entry `not_in_scope`.
3. Ghi `last_scope` = `{pages, node_ids, feature, units_in_scope[]}` của lần này.
4. `units[]` sort theo `unit_id` alphabetical (U4) — merge không được làm đảo thứ tự gây diff giả.

`checksum` để **trống** cho unit in-scope ở step này — step-07 tính sau khi có specs + frames. Unit out-of-scope giữ checksum cũ.

## 4. Decision Points

- **WBS không có `SCR-*`/`WGT-*` nào** → STOP: *"WBS chưa có unit FE. Chạy Stage 2 (`/NTAPP-vsaf-reproduce-architecture`) hoặc kiểm prefix ID — mapping chỉ nhận `SCR-*`/`WGT-*`."*
- **Case A + người xác nhận "màn thật"** → STOP như bảng §3.3.
- **DS resolve conflict** → STOP báo mismatch (nhánh B.4).
- **Người trả lời không rõ / chỉ nói "ok" khi còn dòng LOW** → hỏi lại đúng dòng còn thiếu, KHÔNG suy diễn (U5).
- **100% unit in-scope là `missing`** → STOP: *"Không unit nào map được frame. Ingest sẽ không tạo giá trị gì. Kiểm scope harvest hoặc naming convention frame."* (Chỉ tính unit **in-scope** — unit out-of-scope đang được bảo toàn, không phải bằng chứng ingest thất bại.)
- **`--feature` không khớp nguồn nào** (slice manifest / WBS cluster / journey) → WARN: *"Không tìm thấy feature `{name}` trong slice manifest hay WBS cluster. Bỏ lọc, dùng full WBS — bảng sẽ dài hơn nhưng không sai."* KHÔNG STOP.
- **Người bác feature suy đoán** → nhận tên họ đưa, lọc lại Stage 3.1b, trình lại bảng **một** lần. Vẫn không khớp → bỏ lọc, full WBS.

## 5. Output

- `{ds_root}/_reference/figma/figma-manifest.yaml` (per DS, `checksum` chưa điền).
- `{ds_root}/_reference/figma/figma-source.json` (copy từ family root).
- `report_sections[]` += `[MAPPING]` (bảng đã ký nguyên văn + feature scope đã chốt + coverage + số mapped/missing/not_in_scope/ignored/preserved + ai ký + thời điểm).

**Next:** Read fully and follow `./step-04-spec-extract.md`
