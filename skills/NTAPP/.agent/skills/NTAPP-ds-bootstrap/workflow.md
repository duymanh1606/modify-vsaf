# Workflow: NTAPP DS Bootstrap

**Goal:** Khởi tạo Master Design System cho FE repo từ code reality + best-practices baseline + (optional) external tokens.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (bản đồ + rule + cổng). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi HITL/PAUSE) RỒI mới đọc step kế qua pointer `**Next:**` ở cuối step. KHÔNG đọc trước nhiều step. State chuyển tiếp qua artifact file + `report_sections[]`, không qua việc giữ instruction trong context.

---

## INITIALIZATION

> **⚠️ Cross-repo direction:** Skill chạy **trong code repo** (cwd có `package.json`); READ source từ code repo, WRITE Master DS metadata về spec repo. Yêu cầu **multi-root workspace** mở cả 2 repo. Xem [Manual_phase_1.md mục 8](../../docs/Process/Manual_phase_1.md) — Multi-repo setup. Direction guard chi tiết: §U3.

### Inputs (DSO cung cấp khi gõ `/ntapp-ds-bootstrap`)
- (Optional) **External tokens path** — file NTAPP v1 hoặc W3C JSON nếu DSO muốn 3-way diff với code reality. Không nhắc → skip Step 5.
- (Optional) **Mode override** — `overhaul` / `regenerate full DS` → discard latest, snapshot vào `archive/` trước rồi rebuild. Default: incremental (reuse `stack-profile.json` nếu có).
- (Optional) **Target format** — `ntapp` (default) hoặc `w3c` để export thêm `master_token.w3c.json` ở Step 7.
- (Optional) **Re-parse flag** — `--refresh-library-api` để rerun parser bỏ qua cache (xem Step 1b).

Input còn lại được hỏi tại HITL gates (Step 1 reuse stack-profile, Step 1b parse-fail HITL, Step 6 auto-approve HIGH).

### Context Loading
Load `.bmm-config.yaml` ở **code repo root** — extract:
- `bmad.spec_repo_root` — relative/absolute path tới spec repo.
- `bmad.design_system_root` — resolved path tới **DS root của repo này** (default `{spec_repo_root}/NTAPP-output/design-system`). Project multi-DS (nhiều FE repo → nhiều DS): giá trị trỏ `{family_root}/{ds_id}` — thủ tục chuẩn `_shared/ds-resolution.md` **nhánh A** + `_shared/ds-registry-schema.md`.
- `bmad.code_repo_root` — root của code repo. Default = cwd (auto-detect nếu cwd có `package.json`).
- Block `stack` (manual override) + `ds-bootstrap` (rules config).

Load shared schemas (READ từ spec repo):
- `{design_system_root}/_shared/best-practices.md`, `stack-profile-schema.md`, `token-format-schema.md`, `component-metadata-schema.md`, `library-api-schema.md`, `pattern-matcher.md`, `w3c-converter.md`.
- **Multi-DS:** `_shared/` LUÔN ở family root — `{design_system_root}/_shared/` không tồn tại (DS namespaced `{family}/{ds_id}`) → đọc `{design_system_root}/../_shared/` (quy tắc fallback cơ học, áp cho mọi ref `_shared/*` trong skill).

### Pre-conditions (pre-flight)

**Pre-flight 1 — Cwd phải là code repo:** verify `{code_repo_root}/package.json` tồn tại. Nếu cwd = spec repo (vd: thấy `NTAPP-output/design-system/` ngay tại cwd, không có `package.json`) → STOP: *"Skill scan code stack từ code repo, phải chạy trong code repo. Mở multi-root workspace, switch sang code repo, chạy lại."*

**Pre-flight 2 — Spec repo accessible:** verify `{spec_repo_root}` exist + writable.

**Pre-flight 2b — DS identity (multi-DS guard):** nếu `{design_system_root}/registry.yaml` tồn tại → config đang trỏ **family root** của project multi-DS, KHÔNG phải DS root của repo. *Ngoại lệ hợp lệ duy nhất:* registry có system `root: "."` mà `code_repo` khớp repo hiện tại (DS legacy in-place) → tiếp tục. Ngược lại → STOP: *"`bmad.design_system_root` đang trỏ family root (có `registry.yaml`). Sửa `.bmm-config.yaml` code repo trỏ vào DS root của repo: {liệt kê `{ds_id} → {family}/{root}` từ registry}. Repo chưa có DS trong registry → chạy lại và chọn nhánh 'Tạo DS mới' ở Step 1."*

**Pre-flight 3 — Shared schemas tồn tại:** mỗi file trong Context Loading list phải resolve. Thiếu → STOP: *"Spec repo thiếu shared schema `{path}`. Verify spec repo state hoặc clone lại."*

**Pre-flight 4 — External tokens path (nếu DSO cung cấp):** file tồn tại + parse-able JSON. Fail → báo DSO sửa path/format trước khi tiếp tục.

**Pre-flight 5 — `node_modules` (nếu Step 1b sẽ chạy):** `ui_library.name ∉ {none, shadcn}` và `node_modules/{lib}` không tồn tại → STOP: *"Lib `{name}` cần parse nhưng `node_modules/{lib}` không có. Chạy `npm install` (hoặc tương đương) trước."* (Library-api-parser cũng có cùng check; pre-flight chỉ fail-fast.)

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

| # | Step file | Persona | Output | Skip / branch |
|---|---|---|---|---|
| 1 | steps/step-01-stack-detect.md | stack-detector | stack-profile.json | skip nếu `stack-profile.json` đã có VÀ DSO confirm reuse |
| 1b | steps/step-01b-library-api-parse.md | library-api-parser | library_apis/{lib}@{ver}/*.json | skip nếu `ui_library.name ∈ {none, shadcn}` |
| 2 | steps/step-02-extract.md | raw-style-extractor | master_token_parts/01_raw_extracted.json | — |
| 3 | steps/step-03-discover.md | component-discoverer | components_metadata_parts/01_discovered.json (+ usage, recipes, inferred intents) | — |
| 3b | steps/step-03b-visual-reference.md | (procedural, DSO tương tác) | _reference/pages/*.png + _reference/visual-notes.md | skip nếu greenfield / config off / không có nguồn render |
| 4 | steps/step-04-normalize.md | normalizer | master_token_parts/02_normalized.json | branch: external tokens → 5, else → 6 |
| 5 | steps/step-05-conflict-resolve.md | conflict-resolver | master_token_parts/03_conflict_resolved.json | gated: chỉ chạy nếu DSO cung cấp external tokens |
| 6 | steps/step-06-human-approval.md | (compose report + HITL) | bootstrap_report.md | [GATE] DSO `'approved'`; optional auto-approve HIGH qua config |
| 7 | steps/step-07-apply.md | bootstrap-applier | master_token.json + components_metadata.json + archive | TERMINAL; chỉ chạy sau khi DSO `'approved'` ở Step 6 |

Chuỗi: **1 → 1b → 2 → 3 → 3b → 4 → [branch: external tokens? → 5] → 6 → [GATE: DSO approval] → 7**.
Một cổng người-dùng bắt buộc: **HITL approval ở Step 6** (nằm trong step-06, trước khi sang step-07).

---

## GLOBAL RULES — UNIVERSAL SUB-AGENT RULES (bất biến — áp dụng mọi step)

Mọi persona/sub-agent của skill này tuân thủ các convention sau (declared **ONCE** ở đây, persona không lặp lại):

### U1. Atomic file write
Mọi write filesystem (master_token.json, components_metadata.json, stack-profile.json, library_apis/*, master_token_parts/*, components_metadata_parts/*, bootstrap_report.md, archive contents, optional W3C export) PHẢI dùng pattern **tempfile → fsync → rename**. Không append-write, không partial write.

### U2. Path resolution
- File trong **code repo**: path relative tới `{code_repo_root}` (vd: `src/app/lib/components/button/button.component.ts`). KHÔNG absolute, KHÔNG prefix.
- File trong **spec repo**: path relative tới `{design_system_root}` (vd: `master_token_parts/01_raw_extracted.json`).
- Lý do relative: portability cross-machine (dev clone code repo paths khác nhau).

### U3. Cross-repo direction guard
Bootstrap là uni-directional: **READ-only code repo, WRITE-only spec repo**.

- KHÔNG modify source trong `{code_repo_root}/...` (không edit `package.json`, không edit style/component files, không sửa `node_modules/`).
- Mọi resolve target path phải check: write path bắt đầu bằng `{code_repo_root}/...` → STOP *"Bootstrap không write code repo. Target `{path}` sai. Verify `bmad.design_system_root` config."* Read path bắt đầu bằng `{design_system_root}/...` cho source-of-truth files → OK (vd: shared schemas, previous run output).

### U4. Deterministic output
Same `(code state, config, external file)` → same output. Áp dụng:
- JSON pretty-print: 2-space indent, sorted keys alphabetical.
- Array stable ordering (sort tokens alphabetical TRONG tier, components alphabetical, raw values sort theo `occurrences` descending rồi alphabetical tie-break, dedup theo value).
- Timestamps chỉ trong metadata fields định trước (`generated_at`, `last_updated`), không scatter trong body.

### U5. Conservative inference (no fabrication)
Khi không đủ confidence, sub-agent KHÔNG đoán. Behaviors:
- Mark `<TODO: DSO fill>` placeholder cho field không infer được.
- Flag `confidence: LOW` + suggest DSO override qua `.bmm-config.yaml`.
- Library parser fail: mark `unknown` type + ghi note, KHÔNG fabricate prop.
- Edge cases handle theo persona §6, KHÔNG silent-skip.

### U6. Confidence levels (single canonical)
| Level | Định nghĩa |
|---|---|
| **HIGH** | ≥2 nguồn confirm (vd: manifest + sample file), hoặc deviation rõ ràng + fix tự nhiên |
| **MEDIUM** | 1 nguồn confirm, others ambiguous, hoặc pattern conflict cần DSO chọn |
| **LOW** | Heuristic-only, opinion-based, hoặc fabrication risk → bắt buộc DSO override |

Field confidence < HIGH → flag console + suggest override.

---

## FAIL CONDITIONS

Mọi STOP condition document tại DECISION POINTS của step tương ứng (step-01 đến step-07). workflow.md không liệt kê tránh drift. Generic categories:

- **Pre-flight fail** — missing manifest, multi-framework conflict, spec repo unreachable, schema missing, `node_modules` thiếu.
- **External file invalid** — parse fail hoặc format không support.
- **Validation fail không resolve** — hard validation fail (WCAG) còn sau Step 6 → bắt buộc DSO resolve.
- **U3 guard violation** — sub-agent attempt write code repo.

## OUTPUTS

Tất cả output ghi về **spec repo** (`{design_system_root}/...`). Code repo KHÔNG bị skill ghi vào (chỉ READ scan):

- `{design_system_root}/master_token.json` (latest)
- `{design_system_root}/components_metadata.json` (latest — kèm `usage` per component + top-level `recipes[]`)
- `{design_system_root}/component_catalog.md` (derived digest — consumer: Stage 3b/4a vocabulary)
- `{design_system_root}/_reference/` (visual reference — screenshots + visual-notes.md; optional, Step 3b)
- `{design_system_root}/stack-profile.json`
- `{design_system_root}/bootstrap_report.md`
- `{design_system_root}/master_token_parts/` (intermediate)
- `{design_system_root}/components_metadata_parts/` (intermediate)
- `{design_system_root}/library_apis/{lib}@{ver}/*.json` (Step 1b)
- `{design_system_root}/archive/_v{N}_{timestamp}/` (snapshot sau DSO `'approved'`)
- (Optional) `{design_system_root}/master_token.w3c.json` (target format `w3c`)

> **Commit:** sau khi skill chạy xong, DSO commit/push spec repo. Code repo không bị động chạm — không cần commit code repo cho bootstrap.

---

## LAUNCH

Chạy pre-flight ở INITIALIZATION. Pass → vào pipeline bắt đầu Step 1.

**Next:** Read fully and follow `./steps/step-01-stack-detect.md`
