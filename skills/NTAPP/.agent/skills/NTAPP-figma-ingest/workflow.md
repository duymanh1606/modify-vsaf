# Workflow: NTAPP Figma Ingest

**Goal:** Biên dịch 1 Figma file thành artifact **tĩnh, deterministic, git-diffable** trong spec repo, để Stage 4a/4b đọc **file local**. Sau khi ingest xong, toàn bộ slice-loop chạy **offline** — không network, không secret, replay được.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (bản đồ + rule + cổng). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi HITL/PAUSE) RỒI mới đọc step kế qua pointer `**Next:**` ở cuối step. KHÔNG đọc trước nhiều step. State chuyển tiếp qua artifact file + `report_sections[]`, không qua việc giữ instruction trong context.

---

## SCOPE — skill này KHÔNG làm gì

| Không làm | Owner thật |
|---|---|
| Vẽ/sinh wireframe §2.2, Layout Groups table, control matrix §2.3 | Stage 4a `ntapp-feature-design` F3 (transcribe TỪ output của skill này) |
| Sinh `ui_schema_{id}.json` | Stage 4b `ntapp-ui-generation` step-03 |
| Quyết định reuse / propose `[NEW]`/`[MODIFIED]` component | Stage 4b `ntapp-ui-generation` step-01 (reuse ladder C0→C3) |
| Ghi `master_token.json` / `components_metadata.json` | `ntapp-ds-bootstrap` step-07, `ntapp-ds-build-component` |
| Thêm unit vào WBS | `ntapp-architecture-design --append` |
| Sinh code | Stage 5 `dev` |

Ranh giới cứng: skill này **report gap**, KHÔNG **apply gap**. Mọi thay đổi Master DS đi qua `ds-bootstrap` / `ds-build-component`.

---

## MODES

| Mode | Lệnh | Tiền điều kiện | Chuỗi step |
|---|---|---|---|
| **tokens-only** (pass 0) | `/ntapp-figma-ingest --tokens-only` | Không cần WBS, không cần Master DS | 1 → 1t → TERMINAL |
| **full** (pass 2, DEFAULT) | `/ntapp-figma-ingest` | WBS locked **+** `master_token.json` tồn tại | 1 → 2 → 3 → 4 → 5 → 6 → 7 |
| **re-ingest** | `/ntapp-figma-ingest` (chạy lại) | như full | như full; unit checksum không đổi → skip export, giữ file; mapping đã ký carry over (`matched_by: previous-manifest`) nên HITL **chỉ hỏi về frame mới/bị rename** |

**Trigger re-ingest là _Figma đổi_, không phải _feature mới_:**

| Tình huống | Chạy lại? |
|---|---|
| Feature mới, designer vẽ màn mới | ✅ |
| Designer sửa màn cũ | ✅ **bắt buộc** — Hook 3 block `feature-design` cho unit đó tới khi re-ingest |
| Feature mới nhưng BE-only / reuse màn cũ | ❌ manifest hiện tại vẫn đúng |
| Feature mới mà designer chưa vẽ | ❌ unit sẽ là `missing` → 4a author mode |

Thứ tự batch phase (2 pass là bắt buộc — `ds-bootstrap` cần token file từ Figma, còn full ingest cần `master_token.json` để snap; chạy 1 lượt là deadlock):

```
/ntapp-figma-ingest --tokens-only          → exports/figma-tokens.w3c.json
/ntapp-ds-bootstrap --external-tokens <path>   (chạy từ CODE repo)
Stage 1 → Stage 2 (WBS lock) → Stage 2b
/ntapp-figma-ingest                        ← full ingest (HITL mapping ở đây)
Stage 3b /ntapp-ux-design
/NTAPP-vsaf-slice-loop SLICE-01            ← offline hoàn toàn
```

---

## STAGE PLACEMENT — NGOÀI slice-loop (bất biến, KHÔNG được vi phạm)

Skill này là **skill trực tiếp**, KHÔNG phải node VSAF (cùng tiền lệ `/ntapp-ds-bootstrap`). Lý do bất biến:

1. **PAT không bao giờ vào môi trường fanout subagent.** `dd-per-unit` + `ui-schema-per-fe-unit` chạy `max_concurrency: 5` × `claude -p`; không có lý do để N subagent giữ secret.
2. **slice-loop giữ tính offline + replayable.** Không network trong loop = không flaky, không rate-limit, không "chạy lại tuần sau ra kết quả khác vì designer vừa sửa".
3. **HITL mapping không chen vào giữa loop.** Loop chỉ có 1 gate người thật (`slice-demo`); thêm gate mapping vào giữa sẽ phá tính AFK.

Phần duy nhất của Figma nằm TRONG loop là **gate read-only, 0 network**: so `figma_ref.checksum` trong DD với `figma-manifest.yaml` (Hook 3 `stage3_input_gate.sh`). Lệch → hook block, người chạy lại skill này ngoài loop rồi `/NTAPP-vsaf-resume <runId>`.

---

## INITIALIZATION

> **⚠️ Cross-repo direction:** Skill chạy **trong SPEC repo** (cwd có `NTAPP-output/`) — ngược với `ds-bootstrap` (chạy từ code repo). READ: Figma REST API + spec repo. WRITE: **chỉ** spec repo, **chỉ** trong `{ds_root}/_reference/figma/`. Xem §U3.

### Inputs (user cung cấp khi gõ `/ntapp-figma-ingest`)

| # | Input | Bắt buộc | Nguồn |
|---|---|---|---|
| 1 | **`FIGMA_TOKEN`** — Personal Access Token, scope `file_content:read` (+ `file_variables:read` cho `--tokens-only` trên Enterprise) | ✅ với `source_mode: api` | **env var duy nhất**. TUYỆT ĐỐI không đặt trong `.bmm-config.yaml` (file này committed) |
| 2 | **Figma link** (hoặc `file_key`) + **scope** (page nào / `?node-id=` nào) | ✅ | Paste khi gõ command; step-01 parse. Bền vững hơn: `file_key` + `scope_pages` trong config |
| 3 | **Ký bảng mapping `WBS unit ↔ frame`** | ✅ (full mode) | HITL gate ở step-03 — input người thật duy nhất không automate được |
| 4 | `--ds <ds_id>` | Chỉ khi multi-DS + `--tokens-only` | Pass 0 chưa có unit để resolve DS → phải chỉ định |
| 5 | `--feature <name>` | ❌ Optional | Cắt ngắn **phía WBS** của bảng HITL + sinh dòng coverage. KHÔNG lọc phía Figma. Quên nhập → step-03 tự suy + xác nhận trong chính bảng HITL; suy không ra thì dùng full WBS (dài hơn, không sai) |

> **Đòn bẩy giảm chi phí #3:** yêu cầu designer đặt **tên frame = ID unit trong WBS** (`SCR-LOGIN`, `WGT-SIDEBAR`). Lúc đó step-03 chỉ còn confirm 1 lần cho cả feature thay vì map tay từng dòng mỗi lần re-ingest.

### Context Loading

Load `.bmm-config.yaml` ở **spec repo root** — extract:
- Block `ntapp-figma-ingest` (`source_mode`, `file_key`, `scope_pages`, `frame_filter`, `export_scale`, `snap_tolerance`, `output_root`, `ignore_name_patterns`). Thiếu block → dùng default ghi ở §CONFIG.
- `bmad.design_system_root` → **family root**. Resolve DS root theo `_shared/ds-resolution.md`:
  - **nhánh B** (per-unit) cho full mode — mỗi unit mapped resolve DS root riêng.
  - **nhánh C** (per-feature đa DS) khi 1 Figma file phủ nhiều FE repo → N manifest, mỗi manifest snap theo `master_token.json` của DS mình. KHÔNG snap chéo.
- `bmad.code_repo_root` — chỉ để **in hint** ở step-01t (`ds-bootstrap` phải chạy từ code repo). KHÔNG đọc/ghi code repo.

Load (READ-only, spec repo):
- `NTAPP-output/Stage_2_Architecture/project_wbs.md` — **SSoT của danh sách unit** (full mode).
- `{ds_root}/master_token.json`, `{ds_root}/components_metadata.json` — đối chiếu ở step-05.
- `{family_root}/_shared/pattern-matcher.md` — thuật toán matching (cùng SSoT với Stage 4b).
- `{family_root}/_shared/w3c-converter.md` — convert token (step-01t).
- `{family_root}/_shared/best-practices.md` — công thức WCAG contrast (step-05).
- (Optional) `NTAPP-output/Stage_3_Specs/ux/ux_design.md` §4 — journey order làm tín hiệu mapping.

> **Multi-DS:** `_shared/` LUÔN ở family root. `{ds_root}/_shared/` không tồn tại → đọc `{ds_root}/../_shared/` (quy tắc cơ học, áp cho mọi ref `_shared/*` trong skill).

### Pre-conditions (pre-flight)

**PF1 — Cwd phải là spec repo:** `NTAPP-output/` tồn tại tại cwd. Nếu cwd có `package.json` mà không có `NTAPP-output/` → STOP: *"Skill ghi artifact vào spec repo, phải chạy từ spec repo. Mở multi-root workspace, switch sang spec repo, chạy lại."*

**PF2 — Tooling:** `curl` + `jq` khả dụng. Thiếu → STOP (script `figma-fetch.sh` phụ thuộc cả hai).

**PF3 — Nguồn hợp lệ theo `source_mode`:**
- `api` → `FIGMA_TOKEN` set **và** `scripts/figma-fetch.sh whoami` trả 200. 401/403 → STOP với hint tạo lại PAT + kiểm quyền xem file. Không set → STOP, hint đổi `source_mode: manual`.
- `manual` → `{output_root}/inbox/` tồn tại + non-empty. Rỗng → STOP kèm checklist export (step-01 §4).
- `mcp` → session phải interactive. Headless → **tự fallback `api`** + WARN (không STOP). `api` cũng không khả dụng → STOP.

**PF4 — (full mode) Upstream artifact:** `project_wbs.md` tồn tại; **và** ≥1 DS root có `master_token.json`. Thiếu WBS → STOP hint Stage 2. Thiếu `master_token.json` → STOP: *"Chạy `/ntapp-figma-ingest --tokens-only` rồi `/ntapp-ds-bootstrap --external-tokens <path>` trước — không có Master DS thì mọi giá trị Figma thành gap, `token-gap-report.md` vô dụng."*

**PF5 — `file_key` resolve được:** từ link paste / config / `--file-key`. Không parse được → STOP hiển thị 2 format link được nhận (step-01 §3.1).

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

| # | Step file | Persona | Output | Skip / branch |
|---|---|---|---|---|
| 1 | steps/step-01-source-resolve.md | (procedural) | `figma-source.json` | branch: `--tokens-only` → 1t; else → 2 |
| 1t | steps/step-01t-token-export.md | (procedural) | `exports/figma-tokens.w3c.json` | gated: chỉ mode `--tokens-only`; **TERMINAL** |
| 2 | steps/step-02-frame-harvest.md | (procedural) | `frames_raw.json` | — |
| 3 | steps/step-03-unit-mapping.md | frame-mapper | `figma-manifest.yaml` | **[GATE] HITL** — user ký bảng mapping |
| 4 | steps/step-04-spec-extract.md | (procedural) | `specs/{unit_id}.json` | — |
| 5 | steps/step-05-ds-reconcile.md | (procedural, dùng pattern-matcher) | `figma-ds-map.md` + `token-gap-report.md` | — |
| 6 | steps/step-06-frame-export.md | (procedural) | `frames/{unit_id}[__{state}].png` | graceful: export fail → WARN, không STOP |
| 7 | steps/step-07-emit.md | (procedural) | checksum + `figma_ingest_report.md` | TERMINAL |

Chuỗi full: **1 → 2 → 3 → [GATE: HITL mapping] → 4 → 5 → 6 → 7**.
Một cổng người-dùng bắt buộc: **HITL mapping ở Step 3**.

---

## GLOBAL RULES — UNIVERSAL SUB-AGENT RULES (bất biến — áp dụng mọi step)

### U1. Atomic file write
Mọi write (`figma-source.json`, `frames_raw.json`, `figma-manifest.yaml`, `specs/*.json`, `figma-ds-map.md`, `token-gap-report.md`, `figma_ingest_report.md`, `exports/*.json`) PHẢI dùng **tempfile → fsync → rename**. PNG download ghi `.part` rồi rename. Không append-write, không partial write.

### U2. Path resolution
- Path trong artifact: **relative tới DS root** (vd `_reference/figma/frames/SCR-LOGIN.png`). KHÔNG absolute — portability cross-machine.
- Path Figma: luôn `{file_key}` + `{node_id}` dạng `1234:567` (dấu `:`), KHÔNG lưu URL đầy đủ.

### U3. Direction guard (write scope)
Skill là uni-directional: **READ Figma + spec repo, WRITE spec repo trong `{ds_root}/_reference/figma/` mà thôi.**
- Write path không bắt đầu bằng `{ds_root}/_reference/figma/` → STOP: *"figma-ingest chỉ ghi trong `_reference/figma/`. Target `{path}` sai scope."*
- KHÔNG chạm `master_token.json`, `components_metadata.json`, `component_catalog.md`, `feature_deltas/`, `project_wbs.md`, DD, `ui_schema_*`.
- KHÔNG chạm code repo (kể cả đọc để "đối chiếu" — đối chiếu đi qua `components_metadata.json` ở spec repo).

### U4. Deterministic output
Same `(file_key, version, config, mapping)` → same output.
- Mọi fetch downstream step-01 **pin `version`** lấy ở step-01. Designer sửa giữa run không tạo ingest split-brain.
- JSON: 2-space indent, **sorted keys** (`jq -S`), array sort theo key ổn định (`node_id` alphabetical, không theo thứ tự API trả).
- Timestamp chỉ ở field định trước (`ingested_at`, `figma_last_modified`), không scatter trong body.

### U4b. Manifest MERGE, không replace
Ingest hầu như luôn chạy **hẹp scope** (feature mới → 1 page Figma). Manifest phải được **merge**: unit ngoài scope harvest giữ entry cũ verbatim; chỉ unit in-scope được re-evaluate. Luật in-scope + phân biệt `missing` (đã xét, Figma không có) vs `not_in_scope` (chưa xét) là SSoT ở [references/figma-manifest-schema.md](./references/figma-manifest-schema.md) §Merge semantics.

Vì sao là rule cấp workflow chứ không phải chi tiết của 1 step: ghi đè manifest hạ unit của feature cũ xuống `missing` → Stage 4a **im lặng** rơi về author mode dù Figma vẫn còn frame, và Hook 3 **không bắt được** (chỉ so checksum khi status là `mapped`). Không ai báo gì, chỉ là chất lượng DD tự dưng kém đi. Step-07 có 2 assert fail-loud cho việc này.

### U5. No fabrication
- **KHÔNG đoán mapping** unit↔frame. Confidence < HIGH → đưa vào bảng HITL cho người quyết, không tự chọn.
- **KHÔNG bịa token/component**. Giá trị Figma không khớp token nào trong tolerance → ghi `token-gap-report.md`, KHÔNG tự tạo token, KHÔNG tự propose `[NEW]`.
- Text không đọc được / node lỗi → `<TODO: verify in Figma>` + `confidence: LOW`, không suy diễn.
- Dùng thang confidence chuẩn: **HIGH** (≥2 tín hiệu khớp) / **MEDIUM** (1 tín hiệu, còn lại ambiguous) / **LOW** (heuristic-only → bắt buộc HITL).

### U6. Secret & URL hygiene
- PAT **chỉ** từ env `FIGMA_TOKEN`. KHÔNG log, KHÔNG ghi vào artifact, KHÔNG in ra stdout (kể cả một phần).
- `/v1/images` trả **signed URL S3 hết hạn** → download rồi bỏ; TUYỆT ĐỐI không lưu vào manifest (sẽ rot).
- Trước khi ghi bất kỳ artifact: scrub chuỗi khớp `figd_[A-Za-z0-9_-]+` và query param `?X-Amz-`.

### U7. Context hygiene (bảo vệ context window)
- Raw response Figma API **KHÔNG được vào context**. Luôn: script fetch → ghi file → `jq` prune → đọc **bản đã prune**.
- Một frame vừa phải cũng ra vài trăm KB JSON (`absoluteBoundingBox`, `fills`, `effects`, vector path). Đọc raw = nổ context + mất determinism.
- Cấm `curl` thủ công trong hội thoại; mọi network đi qua `scripts/figma-fetch.sh`.

---

## CONFIG (block `ntapp-figma-ingest` trong `.bmm-config.yaml` spec repo)

| Key | Default | Ý nghĩa |
|---|---|---|
| `source_mode` | `api` | `api` \| `manual` \| `mcp` (mcp = dev-loop interactive, không dùng trong VSAF) |
| `file_key` | — | Lấy từ link nếu thiếu |
| `scope_pages` | `[]` (= mọi page) | Tên page chứa màn thật |
| `frame_filter` | `null` | Regex whitelist tên frame |
| `ignore_name_patterns` | `["^_", "^Cover", "^Archive", "^Draft", "^Copy of ", "^Untitled"]` | Blacklist tên frame |
| `export_scale` | `2` | Scale PNG |
| `snap_tolerance` | `{spacing: 2, radius: 2, font_size: 1}` (px) | Ngưỡng snap giá trị Figma → token |
| `token_gap_warn_threshold` | `20` | Vượt → step-05 khuyến nghị chạy lại `ds-bootstrap` trước slice |
| `max_frames` | `80` | Vượt → WARN yêu cầu thu hẹp scope |
| `output_root` | `{ds_root}/_reference/figma` | — |

---

## FAIL CONDITIONS

Mọi STOP condition document tại DECISION POINTS của step tương ứng. Generic categories:

- **Pre-flight fail** — cwd sai repo, thiếu `curl`/`jq`, PAT invalid, thiếu WBS / `master_token.json`, `file_key` không parse được.
- **Scope fail** — 0 frame sau filter; > `max_frames` frame (WARN + yêu cầu thu hẹp).
- **Mapping fail** — frame trông như màn thật nhưng không có unit tương ứng trong WBS → STOP hint `/ntapp-architecture-design --append` (WBS là SSoT, KHÔNG để Figma thành inventory thứ 2).
- **U3 guard violation** — attempt write ngoài `_reference/figma/`.
- **Auth/quota** — 401/403 (STOP), 429 (script tự backoff; hết retry → STOP).

- **Merge fail** — step-07 assert phát hiện mất unit hoặc entry out-of-scope bị sửa (§U4b).

**KHÔNG fail** (graceful, chỉ WARN): unit không có frame (`figma_status: missing` → unit đó fallback author mode ở 4a); unit ngoài scope (`not_in_scope` → giữ entry cũ); PNG export lỗi (specs vẫn dùng được); `/variables/local` 403 (fallback `/styles` → fallback manual); `--feature` không khớp nguồn nào (bỏ lọc, dùng full WBS).

---

## OUTPUTS

Tất cả ghi vào **spec repo**, trong `{ds_root}/_reference/figma/` (per DS — multi-DS thì N bản, mỗi bản chỉ chứa unit của DS đó):

```
{ds_root}/_reference/figma/
├── figma-source.json          # provenance: file_key, version (pinned), last_modified, mode, scope
├── figma-manifest.yaml        # unit_id → node_id, states[], checksum, figma_status   ← CONTRACT
├── figma-ds-map.md            # Figma component/style name → DS component_id / token path
├── token-gap-report.md        # gap ngoài tolerance → input cho ds-bootstrap --external-tokens
├── figma_ingest_report.md     # summary run + mapping đã ký + WARN
├── frames/{unit_id}[__{state}].png
├── specs/{unit_id}.json       # hierarchy pruned + layout_groups_hint + copy[] + icon_candidates[]
├── exports/figma-tokens.w3c.json   # chỉ mode --tokens-only
└── inbox/                     # chỉ mode manual — nơi designer drop file
```

Schema contract của manifest: [references/figma-manifest-schema.md](./references/figma-manifest-schema.md).

**Consumer:**

| Consumer | Đọc | Dùng để |
|---|---|---|
| Stage 4a `ntapp-feature-design` step-02 | `frames/*.png` + `specs/*.json` | Transcribe §2.2 wireframe + Layout Groups + §2.3 control matrix |
| Stage 4b `ntapp-ui-generation` step-01 | `figma-ds-map.md` | Bậc **C-1 Figma-mapped** đầu reuse ladder → cắt false-`[NEW]` |
| Stage 5 `dev` | `frames/*.png` (link qua DD) | Visual reference — CẤM copy CSS (Rule 4 pre-commit chặn hex/px) |
| Hook 3 `stage3_input_gate.sh` | `figma-manifest.yaml` | Drift gate: checksum vs `figma_ref` trong DD |
| DSO | `token-gap-report.md` | Quyết định chạy `ds-bootstrap --external-tokens` |

> **Commit:** sau khi chạy xong, commit spec repo (manifest + specs + PNG + report). PNG là **render-evidence RETAINED** — cùng loại với preview `ux_sketch` (committed nhưng KHÔNG phải SSoT: Figma là SSoT, sửa Figma rồi re-ingest, không sửa tay artifact).

---

## LAUNCH

Chạy pre-flight PF1-PF5 ở INITIALIZATION. Pass → vào pipeline bắt đầu Step 1.

**Next:** Read fully and follow `./steps/step-01-source-resolve.md`
