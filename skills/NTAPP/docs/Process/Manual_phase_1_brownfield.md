# Manual Phase 1 — Track Brownfield (hệ thống đã tồn tại)

> **File này = workflow chi tiết cho dự án brownfield.** Đọc theo thứ tự: Phase A (dựng baseline 1 lần) → Phase B (mỗi yêu cầu mới).
>
> Set up onboard (bootstrap → skill check → repo), vai trò & approve, bảng slash command, pre-commit rules, multi-repo — đều là **cơ chế dùng chung**, nằm ở **[Manual_phase_1.md](Manual_phase_1.md)** (Hub). Làm xong PHẦN A của Hub (onboard) rồi quay lại đây.
>
> Bức tranh tổng 2-phase: Hub [mục 2](Manual_phase_1.md#2-bức-tranh-tổng-quan--5-stage). Vai trò ai approve stage nào: Hub [mục 4](Manual_phase_1.md#4-vai-trò-quyền-approve--handoff). Bảng slash command đầy đủ: Hub [mục 5](Manual_phase_1.md#5-bảng-slash-command--skill-xung-đột).

---

## 1. Brownfield là gì

Đã có **code + hệ thống đang chạy**. Foundation (Design System, kiến trúc) tồn tại **ngầm trong code** — phải **dựng lại (reconstruct) thành tài liệu** (Phase A) trước khi thêm tính năng mới, rồi mọi yêu cầu mới đi qua **Feature Triage** (Phase B) để chọn lane.

**Multi-repo:** spec repo riêng + (các) code repo hiện tại. Setup workspace: Hub [§3 Set up onboard](Manual_phase_1.md#3-set-up-onboard--bootstrap--skill-check--repo) + [§7 Multi-repo](Manual_phase_1.md#7-multi-repo-nếu-áp-dụng).

---

## 2. Phase A — Reconstruct baseline (1 lần khi onboard hệ thống)

> **Chạy `./scripts/bootstrap.sh` TRƯỚC mọi skill.** Bootstrap script auto-detect spec repo + các code repo, sinh `<project>.code-workspace` + `.bmm-config.yaml` per repo, symlink `.agent/skills/` cross-repo. Chưa chạy → skill (vd `/ntapp-system-overview`, `/ntapp-ds-bootstrap`) **không nhận diện đúng các repo** trong workspace. Lần đầu: `./scripts/bootstrap.sh`; dev mới join: `--refresh`; nâng single → multi-repo: `--upgrade`. Chi tiết: Hub [§3 Set up onboard](Manual_phase_1.md#3-set-up-onboard--bootstrap--skill-check--repo) + [README.md](../../README.md).

Mục tiêu: biến cái đang chạy thành tài liệu canonical (Master DS (design system) + HLD (architecture) + Module 0 (Connectivity specification) + WBS (function list)) để workflow Phase 1 có nền tham chiếu.

### Bước A1 — Design System Bootstrap từ code hiện tại

> **Chỉ chạy khi hệ thống có frontend (repo/code FE).** Backend-only → bỏ qua A1, sang thẳng A2. Đây là **Design System Bootstrap** (Stage 0, `/ntapp-ds-bootstrap` — sinh Master Design System), khác **Bootstrap script** (`./scripts/bootstrap.sh` — set up workspace, Hub [§3](Manual_phase_1.md#3-set-up-onboard--bootstrap--skill-check--repo)).

**Người làm:** Design System Owner. `/ntapp-ds-bootstrap` extract Master DS (`master_token.json`, `components_metadata.json`, `stack-profile.json`) **từ chính code repo đang chạy** — token + component thật đang dùng, không phải from scratch. **Nhiều FE repo → chạy 1 lần/repo, mỗi repo 1 DS riêng** (lần 2 skill tự hỏi tạo `ds_id` mới + sinh `design-system/registry.yaml`, không đè DS repo trước — xem [Hub §7.6](Manual_phase_1.md#76-multi-ds--nhiều-fe-repo-nhiều-design-system)).

**Lưu ý:** Skill hỏi từng quyết định (stack profile, duyệt HIGH/MEDIUM/LOW, xung đột external tokens, apply, format export) trực tiếp trong chat.

**Cách làm:**
1. Gõ `/ntapp-ds-bootstrap`. Skill chạy lần lượt: nhận diện stack (framework + UI library + **icon library** + **layout library** + styling), quét token thô từ style files, quét component, chuẩn hóa theo best-practices, đối chiếu external tokens (nếu có), đợi DSO duyệt, ghi kết quả.
2. **Câu hỏi DSO sẽ gặp:**
   - *Confirm runtime token path* — vd `runtime_token_path = src/styles/_design-tokens.scss` (file token runtime ghi vào code repo ở Stage 4b).
   - *Confirm icon library* — vd `lucide-react@0.290`. Repo nhiều icon library → chọn canonical. Không detect được → DSO nhập npm package hoặc `none`.
   - *Confirm layout library* — vd `chakra-ui-layout` (strategy `native-component`). Không match → fallback `css-vanilla` strategy `generated-component`.
   - Các câu duyệt HIGH/MEDIUM/LOW, conflict external token, format export.
3. Skill ghi `bootstrap_report.md` (spec repo `NTAPP-output/design-system/`) với 3 nhóm HIGH / MEDIUM / LOW. Lỗi cứng kiểu WCAG contrast fail phải xử lý xong mới apply.
4. DSO tick/untick checkbox, gõ "approved" để skill ghi `master_token.json` + `components_metadata.json` về spec repo.
5. (Tùy chọn) external tokens từ designer / Figma AI: nhắc skill khi gõ slash command (so sánh 3 chiều code vs external vs best-practice).
   - **Có Figma file thật** → đừng export tay. Chạy trước `/ntapp-figma-ingest --tokens-only` (từ **spec repo**) để lấy Figma Variables/Styles ra `figma-tokens.w3c.json`, rồi truyền path đó vào `--external-tokens`. Đây là **pass 0** của luồng Figma; full ingest phải chờ tới sau WBS lock ([§3.3b](#33b-stage-08--figma-ingest-chỉ-khi-feature-có-figma-vẽ-trước)).
   - Không có Figma Enterprise → endpoint variables trả 403, skill tự lùi sang `/styles` (chỉ có màu + typography, **không có spacing/radius**). Muốn đủ bộ thì nhờ designer export bằng plugin Tokens Studio.
6. Spec repo có 4 file canonical + `library_apis/{lib}@{ver}/`. DSO commit + push spec repo. Code repo không bị chạm.

**Output:** `master_token.json`, `components_metadata.json`, `stack-profile.json`, `bootstrap_report.md`, `library_apis/`, snapshot `archive/_v1_{timestamp}/`. **Approve:** Design System Owner.

> Mọi thay đổi Master DS sau đó đi qua Stage 4b (`/ntapp-ds-build-component`). Làm lại từ đầu → nhắc skill *"chạy ds-bootstrap chế độ overhaul"*.

### Bước A2 — Architecture baseline (tài liệu hóa hệ thống hiện tại)

**Brownfield chưa có tài liệu mô tả hệ thống hiện tại?** Chạy `/ntapp-system-overview` (default mode `baseline`) **trước khi gõ skill HLD** (Bước A3). Skill scan các code repo đang chạy (mọi cặp service-to-service: FE↔BE, mobile↔BE, BE↔BE, BFF), sinh tài liệu mô tả từng sub-system + bức tranh tích hợp giữa chúng.

**Cách làm:**

1. Mở multi-root workspace gồm spec repo + các code repo. Gõ `/ntapp-system-overview` — **mode `baseline` là default**, không cần kèm `--mode`. Skill liệt kê code repo phát hiện được, hỏi xác nhận scope, rồi scan từng sub-system song song. (Chỉ cần per-repo doc cho onboarding, KHÔNG cần Contract Matrix / Q&A → gõ tường minh `--mode overview`, hoặc chọn option (e) ở bảng scope confirm.)

2. Mỗi sub-system in scope có 1 file ở `NTAPP-output/Stage_1_Discovery/system_overview/` gồm 10 sections + **Section 0 Service Identity** (base URL expose / consume, IDL artifact, auth scheme — là **join key** cho Contract Matrix) + **Section E Open Questions for SA**. Body sections (Executive Summary, Business Features, Risks) cho phép `**Assumption:**` prose; bảng API / Integration / Data Model strict require `file:line` evidence.

3. **Interactive Q&A loop:** sau scan, skill chủ động hỏi tối đa 10 câu HIGH-IMPACT (target sub-system của URL chưa rõ, auth scheme chưa rõ, IDL source) ngay trong chat. SA trả lời inline (free text hoặc skip), skill patch trực tiếp vào file. Câu MEDIUM/LOW giữ inline TODO. Power user dùng `--skip-qa` để bỏ qua loop (CI / non-interactive).

4. File `_overview.md` chứa **Contract Match Matrix** (Tier 3 strict, no Assumption) — với mỗi cặp consumer↔provider trong scope, skill gắn 1 trong 5 trạng thái: `MATCHED` / `VERSION-MISMATCH` / `CONSUMER-ONLY` (provider out-of-scope hoặc dead) / `PROVIDER-ORPHAN` (endpoint không ai gọi) / `DTO-DRIFT` (shape khác giữa 2 bên — bug tiềm ẩn). Không đủ evidence → `UNKNOWN` + TODO chứ KHÔNG đoán. Drift cross-repo khó thấy khi đọc từng repo riêng — chạy skill ngay đầu Phase A để bắt drift trước khi dựng HLD.

5. SA review summary 3-choice (Approve / Refine / Cancel), approve → skill ghi canonical + snapshot archive (`archive/_v{N}_{date}/`). SA tự fill các `<TODO: SA verify>` còn lại cho business intent (skill không suy được từ code).

6. Khi gõ `/ntapp-architecture-design` ở Bước A3, nhắc agent: *"baseline hệ thống nằm ở `Stage_1_Discovery/system_overview/`"*. Sub-agent Context + Research của HLD sẽ load làm input.

### Bước A3 — HLD reconcile + WBS lock

**Người làm:** SA. `/ntapp-architecture-design` (mention baseline ở `system_overview/`). Agent C dựng `project_wbs.md` **từ hệ thống hiện có + yêu cầu mới**, Agent E audit coverage, lock WBS.

**Cách làm:**
1. Gõ `/ntapp-architecture-design`. Skill chạy 6 sub-agent (Context, Research, Architect, Security, Module-0, Orchestrator) — Context + Research load baseline `system_overview/`.
2. **2 gate quan trọng:**
   - **Gate WBS Audit:** Agent C tạo `project_wbs.md` từ template 4-cột (theo baseline + PRD/Epics yêu cầu mới + module boundary). Agent E audit 100% coverage. Phải PASS thì mới chạy tiếp.
   - **Gate handshake:** `project_wbs.md` đã tồn tại sai format → Agent E hỏi SA (backup `.bak` tạo lại / SA tự sửa).
3. SA review HLD + Module 0 + WBS. Đặc biệt Module 0 — **contract khoá**, đổi sau tốn nhiều. Module 0 đổi ảnh hưởng compliance → submit Compliance review.

**Output:** `architecture_design.md` + `00_system_connectivity_integration.md` + **`project_wbs.md`** (lock).

**Cấu trúc WBS:** Mỗi module khai báo 1 trong 4 type:

| Module type | Đơn vị work | Naming convention | Đặc tính |
|---|---|---|---|
| `backend-service` | `features` | `{MODULE_PREFIX}-NN` (vd `HUB-01`) | BE component: API endpoint, consumer, job |
| `frontend-app` | `screens` + `widgets` | `SCR-{NAME}` + `WGT-{NAME}` | Screen = top-level route. Widget = cross-cutting |
| `integration-contract` | `contracts` | `INT-{SRC}-NN` | API/event contract giữa 2 module |
| `infrastructure` | `features` | `{MODULE_PREFIX}-NN` | Observability, ops, platform |

Quan hệ tường minh: `screen` ghi `consumes`; `widget` ghi `used_by`; `contract` ghi `provider` + `consumers`. Source-of-truth cho Stage 4c story bridge + pre-commit hook ID lookup.

**Approve:** SA. Compliance co-approve nếu có Module 0 changes.

> Sau khi WBS lock, mọi ID ở Stage 3+ phải lấy từ `project_wbs.md`. Thêm/đổi đơn vị work → trigger lại Agent C + Agent E re-audit, **không sửa thủ công**.

> **Sau Phase A:** project có Master DS + HLD + Module 0 + WBS lock. Stage 2b Slice Planning chạy khi cần build feature lớn theo slice (xem Phase B, lane Full per-slice).

---

## 3. Phase B — Incremental (mỗi yêu cầu mới)

Hệ thống đã có WBS + HLD + Module 0 + DS → **mọi yêu cầu mới KHÔNG tự động đi full per-slice loop**. Đi qua Feature Triage trước.

### 3.0 Làm rõ ý tưởng — `/grill-with-docs` (optional, trước Triage)

**Khi nào dùng:** Mới chỉ có **ý tưởng** xây mới / nâng cấp nhưng **chưa làm rõ luồng, kịch bản và các edge case** có thể có. Chạy `/grill-with-docs` trước khi triage để biến ý tưởng mơ hồ thành mô tả đủ rõ — tránh `/ntapp-feature-triage` refuse early vì yêu cầu chưa rõ ràng.

**Người làm:** Bất kỳ ai khởi tạo feature (PM/BA/Dev).

**Cách làm:**
1. Gõ `/grill-with-docs`. Skill phỏng vấn liên tục từng câu một (one-at-a-time), đào từng nhánh decision tree: luồng chính, actor, kịch bản, edge case, ranh giới khái niệm — đối chiếu với `CONTEXT.md` (glossary domain) + code hiện có, bắt mâu thuẫn thuật ngữ tại chỗ.
2. Khi một khái niệm/quyết định chốt, skill cập nhật **`context.md`** (glossary domain) inline; quyết định khó đảo ngược + có trade-off thật → offer ghi ADR (`docs/adr/`).
3. Trả lời tới khi đạt shared understanding → có **`context.md`** mô tả rõ luồng + kịch bản + edge case.

**Output:** `context.md` (+ ADR nếu có). **Dùng làm đầu vào cho Triage:** `/ntapp-feature-triage --file=context.md` (thay cho mô tả 1 câu ở §3.1).

**Approve:** không cần — đây là bước làm rõ, không phải gate.

> Skip được khi ý tưởng đã có tài liệu mô tả chi tiết và rõ ràng (đi thẳng `/ntapp-feature-triage "1 câu mô tả/ file tài liệu"`). `/grill-with-docs` **không thay** Triage — nó chỉ sharpen input cho Triage.

### 3.1 Stage 0.5 — Feature Triage (intake gate)

**Mục tiêu:** Trước khi viết code/spec, recommend chính xác MỘT lane workflow + slash command kế tiếp + reasoning audit.

**Người làm:** Bất kỳ ai khởi tạo feature (PM/BA/Dev). Skill là **forcing function for clarity** — không thay thế PRD, chỉ định hướng workflow.

**Cách làm:**
1. Gõ `/ntapp-feature-triage "1 câu mô tả feature"` (hoặc `--file=draft.md`). Skill scan state hiện tại (WBS, Module 0, slice plan, Master DS) + hỏi dev 9 câu cheap-to-expensive (intent, module, scope, contract change, critical domain, audience, actor change). Skip câu suy được từ context.
2. Skill áp **HARD GATES** refuse early: WBS missing / intent vague / multi-feature batch / Module 0 contract change / module mới / unit mới chưa trong WBS. Mỗi refuse kèm unblock command cụ thể.
3. Pass gates → decision tree (first-match) chọn 1 trong 4 lane (bảng dưới).
4. Lane modifiers inject thêm step: `touches_critical_domain` (money/auth/RBAC/PII) → Mandatory ATDD trước first commit; `demo_audience=regulator` → `/bmad-testarch-nfr` + `/bmad-testarch-trace` trước sign-off; `introduces_new_actor` AND lane=3 → `/ntapp-ux-sketch` trước TechSpec; DS chưa bootstrap AND UI module → `/ntapp-ds-bootstrap` first.
5. Output decision file: `NTAPP-output/Stage_1_Discovery/triage/{YYYY-MM-DD}-{slug}.md` (recommended lane + reasoning + next slash command + refused paths + honest limits). Dev confirm bằng cách chạy command recommend. Re-run nếu attestation sai hoặc WBS đổi mid-build.
6. (Opt-in, default OFF) `.bmm-config.yaml` set `scope_creep_guardrail: true` AND lane=4 trigger-B → skill ghi manifest `triage/manifests/{id}.yaml` (attestation: module_0_unchanged, no_new_contract, max_units) — tripwire bằng mắt khi reviewer xem PR.

**Approve:** Skill output là **advisory** — không cần ai approve. Audit trail tự ghi trong decision file.

> **Honest limits — triage KHÔNG detect:** True scope, contract drift implicit, cross-slice ripple, DS token gaps tinh tế, test-first discipline trong Lane 2, stale slice plan. Ghi đầy đủ trong mỗi decision file.

### 3.2 Routing — 4 lane

| Tình huống | Lane | Đi tiếp |
|---|---|---|
| Lỗi nhỏ khớp 1/5 preset (typo/config/log/lint/test) | **Express hotfix** (L1) | `/NTAPP-vsaf-express-hotfix <preset> \| <intent>` (mini-DD + PR remote, compensate 48h — Hub [§6 Express lane](Manual_phase_1.md#6-quy-tắc-bắt-buộc--không-bypass)) |
| Unit cũ có DD sẵn, chỉ fix/refactor | **Path B quick-dev** (L2) | `/NTAPP-vsaf-path-b-quick-dev <unit_id> \| <intent>` (Stage 5 Path B, §3.4) |
| Unit mới độc lập, chưa có DD, no contract change | **Ad-hoc per-unit** (L4) | `/NTAPP-vsaf-ad-hoc-per-unit <unit_id>` (skip Stage 2b → Stage 4-5, §3.4) |
| Feature lớn theo WBS + slice plan | **Full per-slice loop** (L3) | `/NTAPP-vsaf-slice-loop <slice_id>` (Stage 2b → vòng lặp Stage 3-4-5, §3.3-3.4) |

**Bảng so sánh 4 workflow build:**

| | `express-hotfix` (L1) | `path-b-quick-dev` (L2) | `ad-hoc-per-unit` (L4) | `slice-loop` (L3) |
|---|---|---|---|---|
| **Input** | `preset_type + intent` | `unit_id + intent` | `unit_id` | `slice_id` |
| **Tiền điều kiện** | Preset khớp 5 loại | WBS + DD sẵn | WBS sẵn | WBS + slice plan + HLD + Master DS |
| **Sinh DD** | mini-DD ≤ 30 phút | ❌ (DD sẵn) | ✅ full | ✅ full per unit |
| **UI schema / DS / Story / ATDD** | ❌ | ❌ | ✅ | ✅ |
| **Code review** | ❌ | ✅ | ✅ | ✅ |
| **Output cuối** | **PR remote** | local commit | local commit | local commit |
| **HITL demo / close-out** | ❌ | ❌ | ❌ | ✅ flip `demo_status` + ghi ledger (`slice-ledger` + `knowledge/`) |
| **Technical debt** | ✅ compensate 48h | ❌ | ❌ | ❌ |

> **Lỗi phát hiện khi test / demo / UAT KHÔNG đi qua Triage** — triage là cổng vào của *yêu cầu mới*, không phải của *defect*. Bug có đường riêng: `/ntapp-log-bug` → `/ntapp-fix-bug` \| `/NTAPP-vsaf-fix-bug`, xem [§3.6](#36-bug-lane--log--fix-sau-demo). Ngược lại, yêu cầu diễn đạt dưới dạng "sửa hành vi cho đúng ý mới" (chưa từng là lỗi được log) vẫn đi Triage → thường ra Lane 2 `path-b-quick-dev`.

### 3.3 Stage 2b — Slice Planning (chỉ lane Full per-slice)

**Mục tiêu:** Gom các unit trong `project_wbs.md` thành **vertical slice** (tracer bullet) demoable end-to-end, sort theo dependency. Drive vòng lặp Stage 3-5.

**Khi nào chạy:** Lane Full per-slice, sau khi có WBS + Module 0. **Người làm:** Senior Dev (chính) + SA + BA co-review.

**Cách làm:**
1. Gõ `/ntapp-slice-planning`. Skill đọc `project_wbs.md` (bắt buộc) + Module 0 + Epics. KHÔNG cần DD.
2. Seam test: **Ownership**, **Auth-foundation** (slice auth build trước slice consume auth), **Resilience** (slice external dependency tách khỏi in-house-only), **In-house vs external**.
3. 2 gate: **Coverage** (mọi unit P0 trong ≥1 slice) + **DAG** (slice N depend 1..N-1, no cycle).
4. Output: `Stage_2_Architecture/slices/SLICE-{n}-{title}.md` — front-matter `slice_id`, `title`, `type` (AFK/HITL), `units`, `blocked_by`, `enhanced_by`, `parent_epics`, `demoable`, `seam_rationale`.
5. Review: Slice 1 đụng đủ layer (BE + FE + contract); không slice ≥8 unit; DAG hợp capacity.
6. Approve → commit slice manifests.

**Output:** `NTAPP-output/Stage_2_Architecture/slices/SLICE-*.md`. **Approve:** Senior Dev + SA.

> **Slice rule:** Group không merge (mỗi unit vẫn sinh story riêng ở 4c); cross-epic OK; AC sống trong story file; slice plan không lock cứng — học từ slice N → update N+1. Phát hiện cần thêm unit → update WBS (Bước A3) rồi re-run slice planning.
>
> **Khi skip 2b:** ≤ 3 unit hoặc PoC throwaway — mỗi unit chạy spec-build độc lập (đây cũng là lane Ad-hoc per-unit).

### 3.3b Stage 0.8 — Figma Ingest (chỉ khi feature có Figma vẽ trước)

**Bỏ qua mục này nếu feature không có Figma.** Không có Figma thì Stage 4a tự sáng tác wireframe như bình thường — không thiếu bước nào.

**Mục tiêu:** biên dịch Figma thành artifact tĩnh trong spec repo để Stage 4a/4b đọc **file local**, nhờ đó vòng lặp per-slice chạy **offline hoàn toàn**.

**Khi nào chạy:** sau Slice Planning (§3.3), **trước** vòng lặp §3.4. Bắt buộc sau WBS lock vì bảng mapping cần danh sách unit. Chạy lại mỗi lần designer sửa Figma. **Người làm:** Design System Owner hoặc UI Engineer (người ký mapping nên là người biết feature).

**Cách làm:**
1. Chạy **từ spec repo** (ngược `ds-bootstrap` — skill này không đọc code): `export FIGMA_TOKEN=...` rồi `/ntapp-figma-ingest` kèm link Figma.
2. Skill harvest frame (lọc nháp/cover/archive), gom frame cùng màn thành `states[]` (`default`/`empty`/`loading`/`error`), rồi **dừng ở cổng HITL**: trình bảng `WBS unit ↔ frame` kèm tín hiệu match + độ tin cậy. Bạn ký `approved` hoặc sửa từng dòng.
3. Sau khi ký, skill trích layout spec (Auto Layout → **Layout Groups** gần như 1-1), export PNG, đối chiếu Master DS, ghi checksum.
4. Đọc `figma_ingest_report.md` — mục *Việc cần làm tiếp* liệt kê: unit thiếu frame, token gap, cặp màu fail contrast, frame export lỗi.
5. Commit spec repo (manifest + specs + PNG + report).

**Bốn tình huống lệch, xử lý khác nhau:**

| Tình huống | Xử lý |
|---|---|
| Frame không map được unit nào, nhưng là **màn thật** | **Dừng** — thêm unit bằng `/ntapp-architecture-design --mode append` ([Bước A3](#bước-a3--hld-reconcile--wbs-lock)) rồi ingest lại. WBS là SSoT của inventory, không để Figma sinh unit |
| Frame là nháp của designer | Đánh `ignore` tại cổng HITL |
| Unit trong WBS **không có** frame | `figma_status: missing` → unit đó Stage 4a tự author mode. **Không chặn** — ingest từng phần là hợp lệ |
| 1 frame chứa cả screen và widget nhúng | Khai `contains[]`, chỉ node con cho từng `WGT-*` |

**Output:** `design-system/.../_reference/figma/` — `figma-manifest.yaml` (contract), `specs/{unit}.json`, `frames/{unit}[__state].png`, `figma-ds-map.md`, `token-gap-report.md`. **Approve:** người ký bảng mapping (ghi vào manifest làm audit trail).

> **Token gap nhiều (>20) thì xử lý trước khi vào slice.** Nghĩa là designer đang dùng giá trị Master DS không có. Để mỗi slice tự đề xuất `[NEW]` rời rạc thì sau vài slice Master DS phân mảnh — và cảnh báo `STYLE_FRAGMENTATION` ở Stage 4b chỉ bắt được khi 2 proposal còn đang dở cùng lúc. Đường đúng: `--tokens-only` → `/ntapp-ds-bootstrap --external-tokens` một lượt ([Bước A1](#bước-a1--design-system-bootstrap-từ-code-hiện-tại) mục 5).
>
> **Không có PAT / không Enterprise:** dùng `source_mode: manual` — designer drop file vào `_reference/figma/inbox/`. Chỉ có PNG thì **mất phần layout tree**, Stage 4a phải đoán bố cục lại từ ảnh; muốn giữ thì cần plugin export JSON.

### 3.4 Vòng lặp per-slice — Stage 3 → 4 → 5

**Mặc định: chạy engine `vsaf`.** Khi feature đã route vào lane Full per-slice (L3), build một SLICE-N = gõ MỘT lệnh:

```
/NTAPP-vsaf-slice-loop <slice_id>     # vd /NTAPP-vsaf-slice-loop SLICE-01
```

Engine chạy nguyên DAG Stage 3→4→5 (techspec → UX → DD → ui-schema → DS-build → story → ATDD → dev → commit), **dừng ở HITL demo gate**; resume bằng `/NTAPP-vsaf-resume <runId>`. Lặp cho từng SLICE-N theo `blocked_by` — slice trước demo PASS → mở slice tiếp. Spec **on-demand** (engine chỉ chạy unit thuộc slice đang build), không batch upfront.

> **Prerequisite:** WBS lock (Stage 2) + slice plan approve (Stage 2b). Chưa có → KHÔNG trigger.

> **Nếu feature có Figma (đã ingest ở §3.3b):** vòng lặp **không đổi lệnh, không đổi node** — engine vẫn chạy đúng DAG đó và **không gọi Figma**. Khác biệt nằm bên trong: unit có `figma_status: mapped` thì Stage 4a chạy **TRANSCRIBE mode** (chép trung thực từ `specs/` + `frames/`, ghi `figma_ref` vào DD §1 + Deviation log ở §2.5), Stage 4b thêm một bậc reuse "Figma-mapped" lên đầu thang nên bớt đề xuất `[NEW]` giả. Unit `missing` chạy author mode như thường. Nếu designer sửa Figma sau khi DD đã ký, Hook 3 **chặn** ở lần chạy 4a kế tiếp (so checksum) — lúc đó chạy lại `/ntapp-figma-ingest` **ngoài** vòng lặp rồi `/NTAPP-vsaf-resume <runId>`.

**Fallback khi engine lỗi / cần can thiệp từng bước:** chạy tay tuần tự chuỗi skill theo [§3.5 Fallback thủ công](#35-fallback-thủ-công--chạy-per-slice-tuần-tự-từng-stage) — cùng thứ tự, cùng gate, cùng approver, chỉ khác là gõ từng lệnh thay vì engine tự lái.

> Lane **Ad-hoc per-unit** chạy cùng các stage này nhưng cho 1 unit, skip Stage 2b — luôn chạy tay theo §3.5 (không qua engine).

### 3.5 Fallback thủ công — chạy per-slice tuần tự từng stage

> Dùng khi engine `vsaf` lỗi, hoặc khi cần dừng/can thiệp ở một stage cụ thể (debug, sửa tay). Đây là **đúng chuỗi stage mà engine tự động hoá** — gõ tuần tự từng lệnh, lặp cho từng SLICE-N. Spec **on-demand**, không batch upfront.

**Stage 3b — System UX Spec (batch toàn bộ feature cần build, TRƯỚC vòng lặp) → Stage 3a — TechSpec (per-slice, trong vòng)** — cả hai consume PRD + HLD. 3b chạy **1 lần** ngay sau slice plan approve; 3a chạy per-slice. **3b có điều kiện** — chỉ chạy khi feature multi-screen mới xét trên **union mọi SCR/WGT của TẤT CẢ slice** (≥2 `SCR-*` nối journey, hoặc actor/flow mới); reuse-journey / single-screen / BE-only **skip** — `feature-design` Stage 4a kế thừa UX Spec đã có / HLD §6 (gate SSoT: `ntapp-ux-design` step-01 §2.0). **Brownfield per-feature thường reuse journey sẵn → phần lớn feature skip 3b.**

> **Prerequisite:** WBS lock + slice plan approve. Chưa có → KHÔNG trigger Stage 3.

- **3b (batch, chạy trước):** `/ntapp-ux-design`. Thiết kế trải nghiệm **tổng thể cho toàn bộ feature cần build** (union SCR/WGT mọi slice — không per-slice). Đọc PRD + Epics + HLD + Module 0 (state enum) + Master DS. Inheritance Audit lock actor/module/state. 5 sub-agent qua 14 step → 5 layer (Foundation, Architecture, Core Journeys, Cross-cutting, Appendix). Output `ux_design.md`. **Approve:** UX Designer + PO + BA.
- **3a (per-slice, trong vòng):** `/ntapp-technical-design` + tên module. 4 sub-agent (Scope Audit check declare đủ đơn vị work, Strategy, Modeling, Implementation). Output `{module}_techspec.md`. **Approve:** Tech Lead. *Scope rule:* TechSpec chỉ đặc tả đơn vị work thuộc module sở hữu (BE→features, FE→screens+widgets, integration→contracts); UI control consume BE feature đặt trong techspec FE, KHÔNG copy sang BE.

**Stage 4a — Detailed Design (Senior Dev) ∥ Stage 4b — UI Schema (UI Engineer)** — 4a trước, 4b consume 4a + Master UX Spec + Master DS. Per slice: chỉ unit thuộc SLICE-N.

- **4a:** `/ntapp-feature-design` + ID đơn vị work. 5 sub-agent (Overview, Logic, Data, UI, QA) song song; UI skip khi BE feature, Data skip khi widget không state. **Wireframe convention** (chỉ FE — F3 emit §2.2): control annotation `[control_id]` khớp bảng UI Controls §2.3; emoji = visual hint kèm `🔍[icon-name]`; **Icon Legend** bắt buộc khi có ≥1 emoji; **Layout Groups** (10 canonical primitive Stack/Cluster/Grid/Spacer/Center/Box/FormField/FieldGrid/Sidebar/Switcher) bắt buộc khi ≥2 sibling control hoặc form multi-field — Stage 4b build `layout` tree từ bảng này. Output `{id}_detailed_design.md`. **Approve:** Senior Dev.
  - **Có Figma (unit `figma_status: mapped`) → TRANSCRIBE mode:** F3 không sáng tác bố cục nữa mà chép từ `_reference/figma/specs/{id}.json` + xem `frames/{id}[__state].png` (**tất cả** state, không chỉ default). Bảng Layout Groups đã được ingest render sẵn trong `figma_ingest_report.md` — F3 verify rồi dán, chú ý các dòng ghi `confidence: LOW` (`Grid` là suy luận; frame không bật Auto Layout thì bố cục suy từ toạ độ, độ tin cậy thấp). Thêm 2 nghĩa vụ: `figma_ref` ở §1 (nguồn của cổng chống lệch, Hub [§6 rule 11](Manual_phase_1.md#6-quy-tắc-bắt-buộc--không-bypass)) và **§2.5 Deviation log** ghi mọi chỗ DD khác Figma kèm lý do. Text hiển thị (label, thông báo lỗi) copy **nguyên văn từng ký tự** — đây là nguồn cho bảng Validation §2.3. **Cấm đọc khoá `raw`** trong specs (px/hex thô) — đó là input để ingest snap token, đọc rồi viết vào DD sẽ đẩy giá trị hardcode xuống Stage 5 và Rule 4 chặn.
  - Ở TRANSCRIBE mode, self-audit composition (L1-L11) chuyển **cảnh báo thuần**, kể cả khi cấu hình bật `enforce_hard`. Rule fail lúc này là phát hiện về **design của designer**, không phải lỗi của F3 → ghi vào Deviation log dạng `escalate designer`, KHÔNG tự sửa layout cho "đạt rule".
- **4b:** chỉ module `frontend-app`. `/ntapp_ui_generation` + `screen_id`/`widget_id`. 2 agent song song: **Design System Agent** (đối soát token + component, thiếu → `feature_deltas/{id}/proposed_ds_updates.md` [NEW]/[MODIFIED]/[WARNINGS]); **UI Semantic Schema Agent** (JSON: FSM + data binding + layout tree + icon bindings). Output `ui_schema_{id}.json` + `proposed_ds_updates.md`.
  - **Có Figma:** thang reuse thêm bậc **C-1 Figma-mapped** lên trên cùng — component designer đã dùng, tra qua `figma-ds-map.md`: `mapped` (≥0.95) → reuse thẳng, không đề xuất gì; `likely` (0.70-0.94) → đẩy lên đầu shortlist nhưng vẫn chấm đủ; `unmapped` → chạy C0→C3 như không có Figma. Bậc này chỉ dùng để **biện minh reuse**, KHÔNG dùng để biện minh `[NEW]` (điểm trong map thiếu tín hiệu a11y vì Figma không cung cấp, nên trần điểm thấp hơn). Nhờ bậc này mà "màn mới có filter nhưng đề xuất tạo lại filter bar" bớt xảy ra.
  - **Cổng kiểm tra Master DS:** `[NEW]` rỗng → bỏ qua. Có NEW → DSO gõ `/ntapp-ds-build-component`: cập nhật `master_token.json` + `components_metadata.json` ở spec repo, **export token runtime sang code repo** (path từ `stack-profile.runtime_token_path`), scaffold/patch component code repo, archive, viết `build_report.md`. Commit cross-repo: Hub [§7.2](Manual_phase_1.md#72-quy-trình-commit-khi-skill-chạy-xong). File token runtime auto-generated (overwrite mỗi run). Layout primitive generate theo `layout_library.strategy`, lazy materialization. **Đừng merge code UI** khi chưa có `build_report.md` — Rule 7 chặn.

  **Approve:** UI Engineer. DSO duyệt + apply nếu thay đổi Master DS.

**Stage 4c — Story Bridge (Senior Dev / BA)** — SAU 4a + 4b, TRƯỚC Stage 5. Bridge NTAPP layered design → BMAD story format.
1. Scope story (chỉ unit thuộc SLICE-N): BE story per `feature_id`; FE story per `screen_id` (cover screen + widget consume); Widget story riêng khi cross-screen đổi đáng kể hoặc build trước consumer.
2. `/bmad-create-story` per story, **tag `slice_id: SLICE-N`**. Bridge: Story foundation ← DD §1 + §5.2 (P0 → Given/When/Then); Tasks ← DD §3.2 + UI schema FSM; Dev Notes ← HLD + TechSpec; Testing ← KBKT P0/P1; Demo context ← `demoable`.
3. Output `NTAPP-output/Stage_5_Build_Verify/{epic}-{story}-{title}.md`. Senior Dev review (AC khớp KBKT P0, `slice_id` tồn tại, status `ready-for-dev`). **Approve:** Senior Dev.

> Skip 4c: Path B quick-dev / Express hotfix. Sprint tracking optional: `/bmad-sprint-planning` 1 lần per epic.

**Stage 5 — Build & Verify (Dev / QA)** — build theo thứ tự SLICE-N, chỉ story có `slice_id = SLICE-active`. Slice trước demo PASS → mở slice tiếp.
1. Branch `feature/{id}` code repo. Khuyến nghị `/superpowers-using-git-worktrees` cho parallel nội bộ slice.
2. **Phân loại ATDD** (canonical: Hub [§5.1](Manual_phase_1.md#51-phân-loại-mandatory-atdd-canonical); enforce Hook 8). **Mandatory** nếu khớp ≥1: A1 cross-system (≥2 service) · A2 multi-actor/stateful · A3 async/resilience · B1 critical-domain (money/auth/RBAC/PII-audit) · B2 destructive. **Fallback:** thiệt hại đo được / audit → Mandatory (QA ghi `atdd:` front-matter, override thắng). **Optional** cho còn lại. *Bugfix-regression → pipeline bugfix, không ở gate này.*
   - Khi Mandatory, trước code: (a) setup framework 1 lần per module — `/bmad-testarch-framework` (multi-root workspace, scaffold `<code-repo>/tests/`, log live KHÔNG sync); (b) `/bmad-testarch-atdd` per feature với story file → test code `<code-repo>/tests/{e2e,api}/{id}.spec.*` + live checklist; (c) chạy test verify FAIL vì assertion không vì syntax; (d) commit tests riêng trước implementation.
3. **Path code-gen:** Path A `/bmad-dev-story` (đọc story, enforce red-green-refactor + DoD gate); Path B `/bmad-quick-dev` (bug fix/refactor/chore, không 4c, KHÔNG enforce test-first → follow up `/superpowers-test-driven-development`).
4. Header mỗi file `// id: <ID> | dd_version: <vN>` (1 key, loại unit qua prefix). Hook reject nếu thiếu/sai. Chi tiết Hub [§6](Manual_phase_1.md#6-quy-tắc-bắt-buộc--không-bypass).
5. Trước PR, dev tự kiểm: `/superpowers-systematic-debugging`, `/superpowers-verification-before-completion` (chạy thật, lưu output), `/bmad-code-review` (3 lớp adversarial). Mandatory ATDD: kiểm tests FAIL → PASS.
6. **PR bằng `/superpowers-finishing-a-development-branch`** (Option 2) — skill chạy lại test suite (gate cuối), sinh PR template, giữ worktree.
7. **QA Lead review PR:** execute KBKT manual từ 4a (human exploratory). Mở rộng tuỳ ý (diff judgment, code-review lần 2, pair review).
8. Dev nhận feedback → `/superpowers-receiving-code-review`.
9. QA sign-off + merge. Audit trail trong git history.

**Approve:** Dev review (peer) + QA sign-off.

> **Demo SLICE-N** → flip `demo_status` + ghi ledger (`slice-ledger` + `knowledge/`) → học → quay lại Stage 2b update slice tiếp nếu cần.
>
> **Dual-repo Stage 5:** Code repo giữ live artifacts (test code, configs, framework log, atdd-checklist). Spec repo không lưu doc per-feature — audit dựa git history. KHÔNG sync live artifacts. Phân loại: CLAUDE.md §"Dual-repo cho Stage 5".

### 3.6 Bug lane — log & fix (sau demo)

**Mục tiêu:** Lỗi phát hiện khi test / demo / UAT được **ghi nhận có trace** (về WBS unit + slice) rồi vá có kỷ luật, không fix mò và không mất dấu.

**Không đi qua Triage.** Triage là cổng vào của *yêu cầu mới*; bug là *defect trên thứ đã build*. Bug lane có 2 chặng riêng: **log trước, fix sau**.

#### Chặng 1 — Ghi nhận: `/ntapp-log-bug`

**Người làm:** ai phát hiện lỗi (QA / Dev / BA / PO).

**Cách làm:**
1. Gõ `/ntapp-log-bug` kèm mô tả lỗi. Cung cấp thêm nếu có: **màn hình** (ảnh chụp **dán trực tiếp trong khung chat**) và/hoặc **API** phát sinh lỗi (path + method).
2. Skill tự xác định `account` người log (`git config user.name` → username Jira → hỏi), rồi map input → **WBS unit**: màn hình → tìm `SCR-*`/`WGT-*` trong `project_wbs.md`; API → grep path trong `Stage_3_Specs/techspec/`, `Stage_4_Design/detailed_design/` hoặc code để tìm unit sở hữu endpoint.
3. Từ unit → tra **SLICE** (`rg "<UNIT-ID>" NTAPP-output/Stage_2_Architecture/slices/*.md`). Nhiều slice khớp / không slice nào khớp → skill **hỏi**, không đoán.
4. Ảnh: helper `capture-bug-image.sh` liệt kê screenshot mới trong folder mặc định theo OS (macOS `~/Desktop` + nơi cấu hình qua `defaults`; Windows `Pictures\Screenshots`), agent đọc từng ảnh và so khớp với ảnh dán trong chat rồi copy vào `assets/{SLICE-ID}/{account}/`. **Dò folder là chính, clipboard chỉ fallback** (1 bug thường nhiều ảnh, clipboard giữ được 1). macOS báo `BLOCKED` = TCC chặn đọc folder → cấp Full Disk Access, hoặc đổi nơi lưu screenshot sang `~/Downloads`, hoặc dùng clipboard.
5. Skill append entry vào `NTAPP-output/Stage_1_Discovery/Bugs_Issues/BUGS-{SLICE-ID}-{account}.md`, trạng thái `Open`.
6. (Opt-in) Đẩy Jira — xem bảng phân loại `Bug` vs `Issue` bên dưới.

**Output:** entry `{SLICE}-{account}-BUG-NN` + ảnh trong `assets/{SLICE-ID}/{account}/` (+ dòng link Jira nếu có).

**Approve:** không cần — đây là bước ghi nhận, không phải gate.

**4 bất biến không được phá:**

| # | Bất biến | Vì sao |
|---|---|---|
| 1 | **1 file / 1 slice / 1 account** — `BUGS-{SLICE-ID}-{account}.md` | 2 người log cùng lúc không ghi chung 1 file → không conflict khi merge |
| 2 | **Append-only** — thêm bug mới KHÔNG sửa/xoá bug cũ (ngoại lệ duy nhất: chèn dòng `Jira:` vào entry vừa tạo) | File bug là chứng cứ, không phải scratchpad |
| 3 | **Đánh số theo từng file** — chỉ quét file của chính account đang log | `account` đã nằm trong mã bug nên mã vẫn duy nhất toàn project: `SLICE-20-dinhtq8-BUG-01` ≠ `SLICE-20-dinhtq9-BUG-01` |
| 4 | **Không bịa nội dung ảnh / steps / expected / actual** — thiếu thì để trống | Bug bịa còn tệ hơn bug không có mô tả |

**Phân loại khi đẩy Jira** — skill tự đề xuất kèm lý do, người dùng chốt (mơ hồ thì **phải** để người chốt, không tự quyết im lặng):

| Type | Dấu hiệu |
|---|---|
| `Bug` | Hành vi lệch spec / DD / techspec; exception / stacktrace; sai số liệu; UI vỡ layout; API sai status code / format; regression so với bản chạy được trước đó |
| `Issue` | Code chạy **đúng như đang thiết kế** nhưng nghiệp vụ chưa hợp lý; thiếu định nghĩa cho case biên chưa ai chốt; 2 tài liệu nói khác nhau; đề xuất cải tiến UX — tóm lại **cần người chốt trước khi làm được** |

> **Thứ tự cố định: ghi file TRƯỚC, tạo Jira SAU.** Jira lỗi (mạng / credential / field bắt buộc) thì bug vẫn đã được log — chỉ cần chạy lại **riêng bước Jira**, không log lại. Ngược lại là mất bug.
>
> Chuẩn bị 1 lần: `jira.project_key` trong `.bmm-config.yaml` (skill tự tạo block nếu chưa có) + credential `env.md` theo mẫu `env.example.md` trong skill dir — **KHÔNG commit `env.md` thật**. Skill luôn `probe` project để lấy đúng `required_fields` của từng issue type; ⚠️ **thang Severity của Jira thường khác thang trong file log** (`Critical/High/Medium/Low`) → phải map về `allowedValues` mà probe trả về và cho người dùng xác nhận, gửi thẳng sẽ nhận HTTP 400.
>
> Trạng thái trong file log và trạng thái trên Jira **không tự đồng bộ** ở chặng log.

#### Chặng 2 — Vá: `/ntapp-fix-bug` (tuần tự) hoặc `/NTAPP-vsaf-fix-bug` (batch)

**Người làm:** Dev sở hữu unit. **Bug "đang mở"** = trạng thái ∈ {`Open`, `In Progress`, `Reopened`} (nguồn Jira: mọi status ngoài `Resolved`/`Closed`/`Cancelled`/`Done`).

| | `/ntapp-fix-bug` | `/NTAPP-vsaf-fix-bug` |
|---|---|---|
| **Nguồn** | 1 file `BUGS-{SLICE}-{account}.md` **hoặc** 1 mã Jira / URL `/browse/<KEY>` (đọc mô tả + ảnh attachment thẳng từ Jira) | 1..N file: `--all` \| `SLICE-01,SLICE-02` \| path `BUGS-*.md` |
| **Cách fix** | tuần tự, `in-place-nocommit` — **KHÔNG commit, KHÔNG push** | song song trên `git worktree` riêng per group, `branch-commit` |
| **Gom nhóm** | ❌ | ✅ `foundation` (hot node / kernel dùng chung — land trước) · `parallel` (file-dir disjoint) · `serial` (`depends_on`) · `needs-investigation` (chưa localize được → KHÔNG auto-fix) |
| **HITL gate** | 2 — duyệt fix plan (step-01) + duyệt nội dung ghi lên Jira (step-03) | 1 — `approve-plan`: đọc 3 file trong batch dir, sửa gom nhóm nếu cần, rồi `touch <batch_dir>/APPROVED` + `/NTAPP-vsaf-resume <runId>` |
| **Doc-sync spec** | `inline` — ngay sau mỗi bug | `deferred` → node serial `integrate-verify` sync (fanout song song mà cùng ghi spec repo = tranh ghi) |
| **Trạng thái bug** | flip → `Fixed` + ghi chú fix | ❌ **read-mostly** — người dùng tự flip **sau khi merge** |
| **Jira** | opt-in resolve: `Nguyên nhân`/`Ảnh hưởng`/`Giải pháp` (bắt buộc với type `Bug`) → assign lại **Reporter** → transition `Resolved` | ❌ |
| **Output** | code đã vá + doc synced, dừng chờ review | `Stage_5_Build_Verify/bug-batches/{date}-{slug}/` (`bug-groups.yaml`, `bug-grouping-plan.md`, `conflict-matrix.md`, `bug_batch_integration.md`) + branch chưa merge + **MERGE ORDER**; append `ledgers/bug-fix-ledger.md` |

**Việc "fix đúng 1 bug trên 1 unit" nằm ở engine dùng chung `NTAPP-bug-fix-engine`** — cả 2 lệnh trên đều ủy quyền cho nó, không tự viết lại logic. Engine chạy: root-cause (`superpowers-systematic-debugging`) → DD gate (reconstruct v1→v2 khi thiếu DD mà bug chạm contract) → ATDD gate (test-first RED→GREEN khi mandatory) → fix tối thiểu → pre-commit 9 rule → verify bậc cao nhất có sẵn → code-review → doc-sync spec. **Ceremony thích ứng, không full-gate đồng đều:** bug critical-domain / đổi contract → nghiêm; bug vặt (express / style thuần) → nhẹ. `severity` trong file log **chỉ** để sắp thứ tự + suy `lane` khi thiếu, KHÔNG bật gate nào (canonical: Hub [§5.1](Manual_phase_1.md#51-phân-loại-mandatory-atdd-canonical)).

**Sau khi `/NTAPP-vsaf-fix-bug` xong (thứ tự bắt buộc):**
1. Review + merge theo **MERGE ORDER** trong `bug_batch_integration.md` (foundation trước).
2. Dọn worktree: `git -C <repo> worktree remove <wt>`.
3. **Rồi mới** flip trạng thái bug trong `BUGS-*.md` → `Fixed`. Flip trước khi merge = spec nói đã fix trong khi code chưa land.
4. Bug `needs-investigation` → bổ sung route / file / stack trace vào `BUGS-*.md` rồi chạy lại cho batch phụ.

**Approve:** Dev review + (nếu bug thuộc slice đã demo) QA xác nhận lại trước khi flip `Closed`.

> **1 batch / lần / repo.** Batch dir đọc từ `NTAPP-output/.current-bug-batch`, marker group ở `NTAPP-output/.work/bug-groups/` — path cố định nên chạy 2 batch song song trên cùng spec repo sẽ đè nhau.
>
> **Bug file là read-mostly ở mọi chặng fix:** chỉ được sửa dòng trạng thái (+ ghi chú fix) của đúng bug đang xử lý; KHÔNG sửa mô tả, KHÔNG đụng bug khác. Bug không tự fix được (mơ hồ / không tái hiện / phụ thuộc ngoài / cần quyết định sản phẩm) hoặc engine trả BLOCKER/ESCALATE → **giữ nguyên trạng thái**, ghi lý do vào report, đi tiếp bug khác — và **KHÔNG đụng Jira**.

---

## 4. Khác biệt so với greenfield

| | Brownfield (file này) | Greenfield |
|---|---|---|
| **Bước đầu** | Reconstruct baseline (DS + arch + WBS từ code) | Stage 1 Discovery (PRD from scratch) |
| **Design System Bootstrap** (chỉ khi có FE) | Extract từ codebase lớn sẵn có | From scratch / scaffold / hoãn |
| **Baseline discovery** | `/ntapp-system-overview --mode baseline` + Contract Matrix | Skip — không có hệ thống cũ |
| **WBS** | Derive từ hệ thống hiện có + yêu cầu mới | Build mới từ PRD/Epics |
| **Cửa ngõ việc mới** | Feature Triage ngay từ đầu (Phase B) | Per-slice loop; feature đến sau cũng triage |

→ Dự án mới từ con số 0? Dùng **[Manual_phase_1_greenfield.md](Manual_phase_1_greenfield.md)** thay vì file này.
