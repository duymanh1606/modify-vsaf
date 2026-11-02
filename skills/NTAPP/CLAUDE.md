# Project: NTAPP (VSAF Blended)

## Output structure

NTAPP (VSAF Blended) vận hành quy trình **per-slice có WBS**. Skill `ntapp-*` + `bmad-*`, enforce bằng 16 hook (`hooks/`) + git pre-commit. Output root `NTAPP-output/` theo cấu trúc trong [docs/Process/Manual_phase_1.md](docs/Process/Manual_phase_1.md) §3.3:

```
.
├── NTAPP-output/               (artifact workflow — output root)
│   ├── .okf/                   (bundle OKF — MÁY SINH; chỉ /NTAPP-okf-refresh ghi, KHÔNG sửa tay)
│   ├── Stage_1_Discovery/      (PRD, epics, brainstorms, ux_sketch/, triage/, Bugs_Issues/ + assets/)
│   ├── Stage_2_Architecture/   (HLD, Module 0, project_wbs, slices/ — slice plan Stage 2b)
│   ├── Stage_3_Specs/          (techspec/, ux/ — on-demand per slice)
│   ├── Stage_4_Design/         (detailed_design/, ui_schema/ — on-demand per slice)
│   ├── Stage_5_Build_Verify/   (story, plans, reviews, atdd/, test-framework/, test-artifacts/, bug-batches/)
│   ├── design-system/          (Master DS; multi-FE-repo → registry.yaml + {ds_id}/ — xem _shared/ds-registry-schema.md)
│   └── ledgers/                (slice-ledger.md + knowledge/ per slice; bug-fix-ledger.md per bug batch)
├── .vsaf/workflows/NTAPP/      (VSAF workflow YAML — chạy qua /NTAPP-vsaf-<name>)
├── hooks/                      (16 event hook Claude Code + lib/ — wire qua .claude/hooks/)
├── _bmad/                      (BMM core config — Layer 1 path defaults)
├── .agent/skills/              (Skill canonical — NTAPP + BMAD + Superpowers + SDLC)
├── .bmm-config.yaml            (Per-skill output overrides — Layer 2)
├── scripts/                    (Bootstrap script + engine-patches/ + templates/)
└── docs/Process/               (Manual + process docs)
```

**Output root hợp lệ:** `NTAPP-output/`. Ngoài root này KHÔNG ghi artifact nơi khác.

## Process shape

**2 phase:**

- **Batch** (1 lần per project/feature): Stage 1 → 2 → 2b → 3b — PRD + Epics → HLD + Module 0 + WBS lock → slice plan → UX Journey Spec.
- **Per-slice loop** (lặp theo từng SLICE-N trong slice plan): Stage 3a → 4 → 5 — mỗi slice spec-build-demo on-demand, học xong điều chỉnh slice sau. **KHÔNG** batch spec Stage 3a-4 cho toàn WBS upfront.

**Stage 3b (`/ntapp-ux-design`)** là batch run-once cho toàn bộ feature cần build, **KHÔNG per-slice** (journey trải rải rác nhiều slice → phải design holistic). Chỉ chạy khi feature multi-screen MỚI (≥2 `SCR-*` nối journey / actor mới); reuse-journey / single-screen / BE-only / mọi lane khác → **skip**, `feature-design` 4a kế thừa Journey Spec đã có / HLD §6 + `ux_conventions.md`. Gate SSoT: `ntapp-ux-design` step-01 §2.0. Sinh 2 artifact tách vai:

- `ux_design.md` — journey spec slim per-feature (archetype, IA delta, journey flows + journey screen tables với Key states). KHÔNG per-screen spec (4a là single wireframe owner), KHÔNG §17 inventory (WBS là SSoT).
- `ux_conventions.md` — **project singleton** living doc (principles / content / status labels / interaction / notification / error / responsive / a11y), delta-update per feature.

**DS grounding cho UI** (chống UI generic + không reuse): Stage 0 sinh `component_catalog.md` + `_reference/` (screenshots) làm nguồn vocabulary cho 4a/4b. Luật: **reuse-first** — 4b audit toàn inventory theo reuse ladder rồi mới cho phép NEW; contrast fail (`WCAG_CONTRAST_FAIL`) là blocker. Thủ tục chi tiết trong `ntapp-feature-design` (F3) + `ntapp-ui-generation`.

**Per-feature intake (Stage 0.5):** feature mới (project đã có PRD + WBS + HLD) → `/ntapp-feature-triage` recommend 1 trong 4 lane, emit decision file + (opt-in) manifest cho scope-creep guardrail. Triage là forcing function for clarity, không phải correctness oracle.

**Bug từ test/demo/UAT** đi đường riêng, KHÔNG qua triage → xem [§Bug lane](#bug-lane).

### Intake yêu cầu mới — grill → triage → architecture

Yêu cầu mới đến dạng **BRD / PRD / user story** (tài liệu khách gửi, epic mới, story lẻ) đi qua 3 chặng, **đúng thứ tự**, TRƯỚC khi chạm workflow build:

1. **Làm rõ — `/grill-with-docs`.** KHÔNG đem BRD thô đi triage/spec: grill tới khi mọi nhánh quyết định được chốt, thuật ngữ khớp glossary hiện có, lựa chọn kiến trúc ghi thành ADR. **Yêu cầu lớn gồm nhiều chức năng mới (đặc biệt greenfield) → grill TỪNG user story / TỪNG functional requirement một**, KHÔNG gộp cả BRD vào 1 session — session ôm nhiều story cho ra CONTEXT nông, quyết định story sau đè story trước, không đủ độ chi tiết cho Stage 1-2. Output vào spec repo `Stage_1_Discovery/` (xem §Override path).
2. **Chọn lane — `/ntapp-feature-triage "<intent>"`.** Chạy *sau* grill để intent đã sạch (triage là forcing function for clarity, không phải nơi làm rõ yêu cầu). Triage đọc state project (WBS / Module 0 / slice plan / DS) rồi ghi `lane` vào decision file → dispatch theo §Chọn lane. Project chưa có WBS thì triage **refuse** — đó là tín hiệu đi Track B (Stage 1 → Stage 2), không phải lỗi.
3. **Update kiến trúc rồi mới chạy lane.** WBS/HLD phải phản ánh yêu cầu đã grill trước khi build, vì Rule 2/3 pre-commit chặn code không có unit trong WBS + không có DD:
   - **lane-3 / lane-4, unit chưa có trong WBS** → `/ntapp-architecture-design --append` (thêm vài unit, không chạm contract Module 0; chạm contract / đổi module boundary → escalate FULL). Lane 3: unit mới chưa nằm trong slice nào → chạy lại `/NTAPP-vsaf-run NTAPP/slice-planning` để gom vào slice.
   - **lane-1 / lane-2** (unit cũ, DD đã có) → KHÔNG đụng WBS, đi thẳng lệnh lane.
   - **Greenfield** → không có gì để "append": Stage 1 `create_prd_epics` (lấy CONTEXT.md + ADR từ grill làm nguồn input) → Stage 2 `/ntapp-architecture-design` dựng fresh.

### Figma vẽ trước (Stage 0.8 — `/ntapp-figma-ingest`, NGOÀI slice-loop)

Chạy khi SCR/WGT đã có giao diện Figma. Thủ tục ingest nằm trong skill; ở đây chỉ 4 điều quyết định *khi nào gọi* và *ai thắng khi lệch*:

- **Thứ tự SSoT:** Figma own **layout/visual intent** — KHÔNG own contract (DD §3 + Module 0 thắng), token (Master DS thắng; lệch đi qua `[NEW]`/`[MODIFIED]`), conventions (`ux_conventions.md` thắng), inventory (**WBS thắng** — frame không có unit → `/ntapp-architecture-design --append`, KHÔNG tự sinh unit).
- **Hai pass, đúng thứ tự:** `--tokens-only` → `ds-bootstrap --external-tokens` → Stage 1-2 (WBS lock) → full ingest. Ingest compile Figma thành artifact tĩnh để 4a/4b đọc **file local** → slice-loop offline, không PAT trong fanout subagent.
- **Re-ingest khi _Figma đổi_, KHÔNG phải khi _có feature mới_** (BE-only / reuse màn cũ → khỏi chạy lại). Ingest hẹp scope an toàn: manifest MERGE, không replace.
- **`FIGMA_TOKEN` chỉ ở env** — KHÔNG đặt vào `.bmm-config.yaml` (file committed). Trong slice-loop phần Figma duy nhất là drift gate read-only ở Hook 3 (`DISABLE_FIGMA_DRIFT_GATE=1` để bỏ qua).

## VSAF Workflows

Tất cả workflow NTAPP nằm tại `.vsaf/workflows/NTAPP/`. **Chạy qua slash command `/NTAPP-vsaf-<name>`** — ưu tiên trước mọi phương án chạy tay từng stage. Workflow chưa có wrapper riêng (`create_prd_epics`, `slice-planning`) → dùng generic `/NTAPP-vsaf-run NTAPP/<name>`.

### Happy path

**2 track chỉ khác nhau ở khối onboard (Stage 0-2); từ Stage 2b trở đi giống hệt.** Chọn sai track thì `reproduce_architecture` fail ngay ở `input-gate` (đòi ≥1 code repo).

**Track A — Brownfield** (hệ đã có code chạy). Khối onboard = *Phase A reconstruct baseline*, chạy **1 lần / hệ thống**:

```
Stage 0    ./scripts/bootstrap.sh                               # workspace + pre-commit hook + skill symlink (TRƯỚC mọi skill)
Stage 0    /ntapp-figma-ingest --tokens-only                    # (chỉ khi có Figma) Figma Variables/Styles → W3C JSON
Stage 0    /ntapp-ds-bootstrap       ┐ chạy song song           # Master DS extract TỪ CODE FE đang chạy — 1 lần / FE-repo (BE-only → skip)
Stage 0    /ntapp-system-overview    ┘ (xem note dưới)          # baseline as-is + Contract Matrix — idempotent, reproduce_architecture chạy lại được
Stage 2    /NTAPP-vsaf-reproduce-architecture                   # system-overview + HLD + Module 0 + WBS lock AS-IS TỪ CODE
Stage 1    /NTAPP-vsaf-run NTAPP/create_prd_epics               # chỉ khi bắt đầu phát triển mới — KHÔNG phải tiền điều kiện của Stage 2
```

> **`ds-bootstrap` ∥ `system-overview` chạy song song được** (2 tab / 2 agent): write set rời nhau — ds-bootstrap chỉ ghi `design-system/`, system-overview chỉ ghi `Stage_1_Discovery/system_overview/`; cả hai chỉ **đọc** code repo và không đọc output của nhau.
> **Nhưng đừng song song `ds-bootstrap` với cả `/NTAPP-vsaf-reproduce-architecture`** — workflow đó còn node `architecture`, mà WBS audit dùng `design-system/registry.yaml` làm tín hiệu "project có ≥2 FE repo" để bắt thẻ `repo:` ở cluster header. Registry chưa kịp sinh thì check tụt xuống fallback (baseline / hỏi người) và binding `unit → repo → DS` có thể trống. **Multi-FE-repo → để `ds-bootstrap` xong trước Stage 2**; 1 FE repo → không ảnh hưởng.

**Track B — Greenfield** (từ con số 0, chưa có code). **KHÔNG dùng `reproduce_architecture`, KHÔNG chạy `/ntapp-system-overview`** — không có gì để scan:

```
Stage 0    ./scripts/bootstrap.sh
Stage 1    /NTAPP-vsaf-run NTAPP/create_prd_epics               # PRD + Epics (+ UX sketch) — tiền điều kiện THẬT của Stage 2
Stage 2    /ntapp-architecture-design                           # HLD + Module 0 + WBS lock dựng FRESH từ PRD/Epics (skill trực tiếp)
Stage 0    /ntapp-ds-bootstrap                                  # có Figma → chạy sớm với --external-tokens; không → hoãn tới SAU khi xong toàn bộ slice (extract từ code đã build)
```

**Chung cả 2 track:**

```
Stage 2b   /NTAPP-vsaf-run NTAPP/slice-planning                 # Slice manifest
Stage 0.8  /ntapp-figma-ingest                                  # (chỉ khi có Figma) full ingest — HITL mapping unit↔frame
Stage 3b   /ntapp-ux-design                                     # (chỉ khi feature multi-screen mới) UX Journey Spec — batch 1 lần
Intake     /grill-with-docs                                     # (yêu cầu mới BRD/PRD/user story) làm rõ trước — nhiều chức năng/greenfield: grill TỪNG story
Stage 0.5  /ntapp-feature-triage "<intent>"                     # (khi chưa biết đi lane nào) triage feature về 1 trong 4 lane
Stage 3-5  /NTAPP-vsaf-slice-loop <slice_id>                    # Build 1 slice end-to-end (lặp per slice)
Bug        /ntapp-log-bug                                       # (khi test/demo ra lỗi) ghi bug — xem §Bug lane
Bug        /NTAPP-vsaf-fix-bug --all                            # Vá batch bug song song trên branch riêng (nhận cả mã Jira)
Release    /NTAPP-vsaf-staging-deploy <release_id>              # Verify slice đã code + fix chỗ đứt mạch + tạo PR lên nhánh staging (KHÔNG deploy)
```

> **Brownfield — thứ tự Stage 1 ↔ Stage 2 KHÔNG bắt buộc:** `reproduce_architecture` dựng kiến trúc **as-is từ code đang chạy** → **không cần PRD/Epics**; `input-gate` chỉ đòi ≥1 code repo + `project_wbs.md` chưa lock. PRD/Epics chạy sau chỉ là nguồn phụ — lệch với baseline thì **as-built thắng** + flag cho SA reconcile. Hook 1 `approval_gate.sh` tự relax khi PRD+Epics **cùng vắng mặt** và có bằng chứng brownfield (`NTAPP-output/.reproduce-mode` hoặc baseline `system_overview/`); file tồn tại mà chưa ký → **vẫn BLOCK**. Escape tay: `BROWNFIELD_REPRODUCE=1`.

### Bảng tất cả workflows

> **Skill trực tiếp, KHÔNG phải VSAF node:** `/ntapp-ds-bootstrap` · `/ntapp-architecture-design` (Stage 2 greenfield — không có workflow tương ứng) · `/ntapp-feature-triage` · `/ntapp-figma-ingest` · `/ntapp-ux-design` · `/ntapp-log-bug` · `/ntapp-fix-bug` · `/ntapp-qa-*`. Riêng figma **cố ý** để ngoài node — PAT không vào fanout subagent, loop giữ được offline/replayable. Trong bug lane chỉ `bug-fix-batch` là workflow.

| Workflow | Mục tiêu | Lệnh chạy | Tiền điều kiện |
|---|---|---|---|
| `create_prd_epics` | Stage 1 — PRD + Epics + UX sketch v0; 1 HITL gate (PM + BA ký) | `/NTAPP-vsaf-run NTAPP/create_prd_epics` | — |
| `reproduce_architecture` | Stage 2 **brownfield-only** — system-overview + HLD + Module 0 + WBS lock **as-is từ code**; 1 HITL gate (SA ký). *Greenfield dùng `/ntapp-architecture-design`* | `/NTAPP-vsaf-reproduce-architecture` | ≥1 code repo trong workspace + `project_wbs.md` chưa lock (`--args "--force"` để ghi đè). **KHÔNG cần PRD/Epics** |
| `slice-planning` | Stage 2b — sinh slice manifest cho phát triển mới; 1 HITL gate (SeniorDev + SA ký) | `/NTAPP-vsaf-run NTAPP/slice-planning` | `project_wbs.md` đã lock (`approved_by:`) — từ track nào cũng được |
| `slice-loop` | Stage 3→4→5 per slice (workflow chính): techspec → UX → DD → ui-schema → DS-build → story → ATDD → dev → commit → demo | `/NTAPP-vsaf-slice-loop <slice_id>` | `slice-planning` approved; slice_id trong WBS |
| `ad-hoc-per-unit` | Lane 4 — per-unit loop, skip Stage 2b; PoC ≤ 3 unit | `/NTAPP-vsaf-ad-hoc-per-unit <unit_id>` | WBS locked; unit_id trong WBS |
| `path-b-quick-dev` | Lane 2 — bug fix / refactor / chore trên unit cũ; skip Stage 3 + 4b-4c | `/NTAPP-vsaf-path-b-quick-dev <unit_id> \| <intent>` | unit_id trong WBS + DD tồn tại |
| `express-hotfix` | Lane 1 — express hotfix 5 preset (typo/config/log-level/lint/test-fix); bypass DD, compensate 48h | `/NTAPP-vsaf-express-hotfix <preset> \| <intent>` | Preset phải khớp list 5 |
| `bug-fix-batch` | Bug lane — 1..N bug từ `BUGS-*.md` **hoặc từ mã Jira**: localize + gom nhóm parallel-safe → **HITL gate 1** duyệt plan → fix trên branch/worktree riêng theo 3 đợt (foundation tuần tự → group độc lập song song → chuỗi phụ thuộc tuần tự) → verify + đề xuất merge order → **HITL gate 2** duyệt nội dung Jira → resolve Jira | `/NTAPP-vsaf-fix-bug <--all \| SLICE-01,SLICE-02 \| path/BUGS-*.md \| TTCNSPQT-5205>` | WBS locked + (≥1 `BUGS-*.md` **hoặc** Jira credential `env.md`) |
| `staging-deploy` | Kiểm chứng feature lắp ráp chạy thông (reachability + ATDD suite slice-loop đã sinh) → remediate chỗ đứt mạch → gate deterministic → commit/push/**PR vào nhánh staging**. **KHÔNG auto-deploy, KHÔNG build** | `/NTAPP-vsaf-staging-deploy <release_id>` | Tất cả slice `demo_status: passed` |

> **Phạm vi hiện tại của `staging-deploy`:** tên "deploy" là *nói quá* — workflow dừng ở **tạo PR**. Nó chỉ kiểm tra lại tính sẵn sàng của các slice đã code, vá chỗ đứt mạch (AUTO khi có cạnh đã khai báo; contract/plan-gap → **ESCALATE**, không tự bịa provider), rồi commit/push/PR mọi repo vào nhánh staging — merge PR mới là thứ kích CI/CD. Không có HITL approve gate: chặn cuối là `feature-integration-gate` (bash deterministic, còn marker `.staging_blocked_*` → exit 1); người chỉ được hỏi khi repo **chưa có nhánh staging** để chọn nhánh đích. Bước **build tự động sẽ bổ sung khi có MCP** — hiện chưa nằm trong workflow.

### Chọn lane (cũng là bảng dispatch của `feature-triage`)

`feature-triage` ghi field `lane` vào decision file; map sang lệnh kế tiếp:

```
lane-1-express    lỗi nhỏ khớp 1 trong 5 preset     → /NTAPP-vsaf-express-hotfix <preset> | <intent>   (compensate 48h)
lane-2-quick-dev  unit cũ có DD, chỉ fix/refactor   → /NTAPP-vsaf-path-b-quick-dev <unit_id> | <intent>
lane-3-full-slice feature mới theo WBS + slice plan → /NTAPP-vsaf-slice-loop <slice_id>                (mặc định)
lane-4-ad-hoc     unit mới độc lập, chưa có DD      → /NTAPP-vsaf-ad-hoc-per-unit <unit_id>
refused                                             → dừng lại, xem lý do trong decision file
                  bug từ test/demo/UAT              → §Bug lane (KHÔNG qua triage)
```

### So sánh 4 workflow build

Ceremony khác nhau ở đâu (input + tiền điều kiện xem bảng workflow ở trên):

| | `express-hotfix` (L1) | `path-b-quick-dev` (L2) | `ad-hoc-per-unit` (L4) | `slice-loop` (L3, main) |
|---|---|---|---|---|
| **Tech spec / UX** | ❌ | ❌ | ❌ | ✅ |
| **Sinh DD** | mini-DD | conditional — `dd-sync` refresh khi intent đổi contract; fix/chore/refactor-giữ-contract → skip | ✅ full | ✅ full |
| **UI schema / DS delta / DS build** | ❌ | ❌ | ✅ | ✅ |
| **Story + ATDD** | ❌ | ❌ | ✅ | ✅ |
| **Code review** | ❌ | ✅ | ✅ | ✅ |
| **Rule 2/3 (WBS + DD)** | ❌ bypass `EXPRESS_LANE=1` | ✅ | ✅ | ✅ |
| **HITL demo** | ❌ | ❌ | ❌ | ✅ flip `demo_status` |
| **Output cuối** | **PR remote** — staging fast track | local commit | local commit | local commit → chờ `staging-deploy` sau khi mọi slice `passed` |
| **Nợ phải trả** | ✅ compensate đủ DD + WBS trong 48h — verify **thủ công** khi review PR | ❌ | ❌ | ❌ |

### Bug lane

Bug phát hiện lúc test/demo/UAT **không** qua `/ntapp-feature-triage` (triage là intake cho *feature*, không phải defect). 2 chặng: **log** (ghi nhận, không đụng code) → **fix** (tuần tự hoặc batch song song).

| | `/ntapp-log-bug` | `/ntapp-fix-bug` *(skill trực tiếp)* | `/NTAPP-vsaf-fix-bug` *(workflow `bug-fix-batch`)* |
|---|---|---|---|
| **Vai trò** | Ghi nhận 1 bug | Vá **tuần tự** | Vá **batch song song** |
| **Input** | mô tả bug (+ màn hình/ảnh, + API) | 1 file `BUGS-<SLICE>-<account>.md` **hoặc** mã Jira / URL `/browse/<KEY>` | `--all` \| `SLICE-01,SLICE-02` \| path `BUGS-*.md` (1..N file, nhiều account) **hoặc** 1..N mã Jira / URL `/browse/<KEY>`. Trộn file + Jira trong 1 lần → DỪNG, chạy 2 batch riêng |
| **Tiền điều kiện** | WBS (để suy unit) | file bug tồn tại / Jira credential (`env.md`) | WBS locked + ≥1 `BUGS-*.md` / Jira credential (`env.md`) |
| **Git** | không đụng code | **KHÔNG commit, KHÔNG push** (sửa tại chỗ) | branch + `git worktree` riêng per group; **KHÔNG merge, KHÔNG push** |
| **Flip trạng thái bug** | tạo entry `Open` | ✅ → `Fixed` | ❌ user tự flip **sau khi merge** |
| **Jira** | opt-in tạo `Bug`/`Issue` | opt-in transition `Resolved` + assign lại Reporter | opt-in — nhận bug từ mã Jira; cuối batch transition `Resolved` + assign lại Reporter, qua **HITL gate 2** riêng |
| **Để lại gì** | entry + ảnh trong `assets/` | code đã sửa + doc synced, dừng chờ review | `bug-batches/<date>-<slug>/` (+ `reviews/<gid>.md`, `jira-resolve-plan.md`, `jira-resolve-result.md`) + branch chưa merge + **MERGE ORDER** |

**Guardrail** (thủ tục chi tiết nằm trong skill — file bug, đánh số, ảnh, Jira: `NTAPP-log-bug`; gom nhóm, batch dir, merge order: `bug-fix-batch.yaml`):

- File `BUGS-*.md` là **append-only + read-mostly**: chỉ sửa dòng trạng thái (+ ghi chú fix) của đúng bug đang xử lý, KHÔNG đụng mô tả hay bug khác. Áp cả khi sửa tay ngoài skill.
- **`bug-fix-batch` không merge/push/flip status.** User merge theo MERGE ORDER (foundation trước) rồi mới flip trạng thái — flip trước khi merge làm spec lệch code chưa land. Batch dir cố định ⇒ **1 batch / lần / repo**.
- **2 HITL gate của `bug-fix-batch` ký bằng checksum, không phải `touch`.** Gate 1 `APPROVED` = checksum `bug-groups.yaml`; gate 2 `APPROVED-JIRA` = checksum `jira-resolve-plan.md`. Sửa file sau khi ký → cổng đóng lại, phải ký lại. Lý do: batch dir tên `<ngày>-<slug>` nên chạy lại cùng ngày trùng thư mục cũ — chữ ký chỉ-kiểm-tồn-tại sẽ cho bản plan chưa ai đọc đi thẳng vào node sửa code thật (gate 2 còn nặng hơn: `Resolved → To Do` KHÔNG revert được).
- **Resolve Jira ≠ flip trạng thái file.** `bug-fix-batch` được ghi Jira (sau gate 2, chỉ bug fix thành công) nhưng **KHÔNG** flip `BUGS-*.md` — Jira `Resolved` nghĩa là "dev xong, chờ verify", branch vẫn chưa merge. User merge xong mới flip file thủ công.
- Policy fix sống ở engine dùng chung **`NTAPP-bug-fix-engine`** (không gõ trực tiếp) — `ntapp-fix-bug` và `bug-fix-batch` đều ủy quyền cho nó. **Sửa cách fix thì sửa engine**, đừng sửa rải ở 2 nơi gọi.

### Resume sau HITL gate

Workflow dừng ở HITL bash-gate (exit 1 chờ human ký `approved_by:` vào file). Sau khi ký xong:

```
/NTAPP-vsaf-resume <runId>
```

## Workflow guardrails (pre-commit hook)

Pre-commit hook ở `.git/hooks/pre-commit` (cài qua `./scripts/bootstrap.sh`) enforce 9 rules từ [Manual_phase_1.md](docs/Process/Manual_phase_1.md) §7.

> **Phạm vi:** Rule 2 (WBS) + Rule 3 (DD) + Rule 6 (ui_schema) áp cho artifact theo WBS (`NTAPP-output/` + code theo WBS). Rule 4/8/9 (token / infra / emoji) là luật chung, áp cho mọi file.

| Rule | Check | Skip nếu |
|---|---|---|
| 1 | File code có header `id: <ID>` + `dd_version: vN` trong 10 dòng đầu. ID prefix phải khớp loại file: UI extension → `SCR-*` hoặc `WGT-*`; non-UI extension → prefix khác (vd `MPF-*`, `HUB-*`, `INT-*`) | (luôn enforce) |
| 2 | `<id>` tồn tại trong `project_wbs.md` (markdown table cột đầu — mọi loại ID: features / screens / widgets / contracts) | WBS chưa có (Stage 2 chưa chạy) |
| 3 | `{id}_detailed_design.md` tồn tại | Stage 4a chưa chạy |
| 4 | UI code (`.tsx/.jsx/.css/.scss`) không hardcode color hex / px / font-family | (luôn enforce trên UI files) |
| 5 | (skip — semantic check, không automate) | — |
| 6 | UI file → `ui_schema_{id}.json` tồn tại (id lấy từ header) | Stage 4b chưa chạy |
| 7 | Nếu `proposed_ds_updates.md` có `[NEW]` → `build_report.md` tồn tại | UI artifact không có delta |
| 8 | Repo `repo_type: service-only` trong CLAUDE.md → KHÔNG commit infra paths (Dockerfile / CI / helm / k8s / terraform / ansible / devcontainer) | Repo declare `fullstack` / `unknown` / không có scope block. Test framework configs (Playwright / Cypress / Vitest / Pytest / ...) KHÔNG block — đó là test code |
| 9 | UI files KHÔNG chứa unicode emoji (U+2600-U+27BF + U+1F300-U+1FAFF) — Stage 4b đã translate emoji wireframe sang `icon_bindings`, code phải import icon từ `stack-profile.icon_library` | File có pragma `// allow-emoji` / `# allow-emoji` / `<!-- allow-emoji -->` trong 10 dòng đầu — legit case: chat content, emoji picker, emoji reaction |

**Header bắt buộc trong 10 dòng đầu của mọi file code.** Key `id:` là canonical; loại unit encoded qua **ID prefix**, không qua tên key. Hook chấp nhận legacy key `screen_id:` / `widget_id:` / `feature_id:` như alias (value vẫn quyết prefix check) — file mới dùng `id:`.

```
// id: MPF-01 | dd_version: v1               BE / non-UI extension
// id: SCR-COMPOSE | dd_version: v1          FE screen
// id: WGT-SIDEBAR | dd_version: v1          FE widget
#  id: HUB-01 | dd_version: v1               Python / Shell
<!-- id: SCR-EMBED-PMT | dd_version: v1 -->  HTML
```

UI extension (`.tsx/.jsx/.vue/.html/.css/.scss/.sass/.less`) bắt buộc prefix `SCR-*` / `WGT-*`; đổi convention thì override env `UI_ID_PREFIX_PATTERN="^(SCR|WGT|<custom>)-"`.

**UI component trong `.ts` thuần (Angular `*.component.ts`):** `.ts` không nằm trong UI extension list → hook coi là non-UI → header `SCR-*` fail Rule 1. Khai `ui_file_pattern` (regex theo path) để hook nhận đúng là UI cho cả rule 1/4/6/9 — env `UI_FILE_PATTERN`, hoặc bền hơn là key trong `.bmm-config.yaml` của **code repo**:

```yaml
# code repo .bmm-config.yaml
ui_file_pattern: "\\.(component|page)\\.ts$"
```

Sửa template hook xong → chạy lại `./scripts/bootstrap.sh --refresh` (từ code repo) để cài lại hook mới.

**Bypass khẩn cấp** (hotfix only — phải compensate đủ header `id:` + WBS entry + DD file trong 48h):

```bash
SKIP_PRECOMMIT=1 git commit -m "hotfix: ..."
```

## QA skills — Stage 5

**Chuỗi 4 bước, chạy đúng thứ tự** (artifact vào biến `qa_artifacts`, default `{stage_5_build_verify}/test`, override ở `.bmm-config.yaml`):

```
1  /ntapp-qa-audit             soát Specs L2 + {id}_detailed_design.md → {id}_qa_report.md (Gap + Q&A). DỪNG chờ user trả lời
2  /ntapp-qa-gap-resolver      xử lý từng gap trong qa_report — đối chiếu 4 nguồn (dữ liệu thực → TechSpec/Contract → DD → code),
                               đề xuất phương án, user chốt rồi thực thi
3  /ntapp-qa-generate-testcase sinh testcase E2E cho 1 SLICE (có file slice) hoặc 1 unit đứng riêng (HUB/WGT/SCR/MPF);
                               triple-emit .feature + markdown + fixtures.yaml
4  /ntapp-qa-robot             sinh Robot Framework POM từ testcase đã chốt + chạy + self-heal (cấm Sleep, retry ≤3)
```

`/ntapp-qa-setup-data` — tuỳ chọn, chen giữa 3 và 4: bóc dữ liệu mồi từ testcase → script Setup/Teardown isolation bằng timestamp/UUID, có reuse-gate (query bản ghi `auto` gần nhất trước khi tạo mới).

Bước 1 là gate thật: **không viết testcase khi `qa_report` còn gap chưa chốt** — đó là lý do bước 2 tồn tại.

## Nơi ghi artifact

### Dual-repo cho Stage 5

Nếu project tách **spec repo** (design + audit artifact) và **code repo** (runtime + test code):

| Loại artifact | Lifecycle | Repo |
|:---|:---|:---|
| Test code (`*.spec.*`, fixtures, configs) | Live | **Code repo** `tests/` |
| Framework setup log (`framework-setup-progress.md`) | Live | **Code repo** `NTAPP-output/test-artifacts/` |
| ATDD live checklist (`atdd-checklist-{story_key}.md`) | Live | **Code repo** `NTAPP-output/test-artifacts/` |
| Framework decision record per module | Snapshot (1 lần khi setup) | **Spec repo** `Stage_5_Build_Verify/test-framework/{module}/decision-record.md` |
| ATDD audit reference per story (pointer + timestamps) | Snapshot (1 lần khi sign-off) | **Spec repo** `Stage_5_Build_Verify/atdd/{id}/README.md` |
| Test design plan (`/bmad-testarch-test-design`) | Snapshot | **Spec repo** `Stage_5_Build_Verify/test-artifacts/test-design/` |
| Traceability matrix (`/bmad-testarch-trace`) | Snapshot per release | **Spec repo** `Stage_5_Build_Verify/test-artifacts/traceability/` |
| NFR assessment (`/bmad-testarch-nfr`) | Snapshot per release | **Spec repo** `Stage_5_Build_Verify/test-artifacts/` |
| Cross-iteration ledger + per-slice knowledge | Snapshot (committed per slice) | **Spec repo** `NTAPP-output/ledgers/` |

**KHÔNG sync live artifacts giữa 2 repo** — manual sync = drift risk. Audit trail dựa vào reference + git history code repo.

### Cách mỗi stack resolve output path

| Stack | Cơ chế | Config file |
|:---|:---|:---|
| **NTAPP** skills (Stage 1-5) | 3-layer cascade (Layer 1 BMM → Layer 2 per-skill → Layer 3 interactive) | `_bmad/bmm/config.yaml` + `.bmm-config.yaml` |
| **NTAPP DS** skills (`ntapp-ds-bootstrap`, `ntapp-ds-build-component`) | Đọc `bmad.design_system_root` (block-level). Default `{spec_repo_root}/NTAPP-output/design-system`. **Multi-DS**: code repo trỏ `{family}/{ds_id}` theo `design-system/registry.yaml`; resolve per unit theo `design-system/_shared/ds-resolution.md` | `_bmad/bmm/config.yaml` hoặc `.bmm-config.yaml` |
| **BMAD** official skills (prd, epics, code-review, dev) | Đọc `planning_artifacts` / `implementation_artifacts` từ BMM | `_bmad/bmm/config.yaml` |
| **Superpowers** (third-party MIT) | Honors "User preferences override default" | THIS FILE |
| **Testarch** (`/bmad-testarch-*`) | Đọc `test_artifacts` từ TEA config; chỉ ghi vào cwd `{project-root}` — chạy từ repo nào ghi repo đó | `_bmad/tea/config.yaml` |
| **Grilling** (`grill-with-docs`) | Portable, không đọc config → chỉ honor override lúc runtime từ file này | THIS FILE |

### Override path cho skill portable / third-party

**Superpowers** (default `docs/superpowers/...` → ghi cùng root NTAPP): `writing-plans` → `Stage_5_Build_Verify/plans/YYYY-MM-DD-<id>.md` · `brainstorming` → `Stage_1_Discovery/brainstorms/YYYY-MM-DD-<topic>-design.md` · `requesting-code-review` → `Stage_5_Build_Verify/reviews/`.

> `writing-plans`, `executing-plans`, `subagent-driven-development`, `requesting-code-review` đã bị **BLOCK** trong workflow chuẩn (Manual §5 "Skill xung đột") — override chỉ dùng khi chạy standalone, để artifact không lạc chỗ.

**`grill-with-docs`** (chặng 1 của §Intake yêu cầu mới) → ghi hết vào **spec repo** `NTAPP-output/Stage_1_Discovery/`, KHÔNG ghi repo root / code repo: `CONTEXT.md` · `CONTEXT-MAP.md` + `contexts/<name>/CONTEXT.md` (multi-context) · ADR → `adr/NNNN-slug.md` (scan thư mục này để lấy số kế tiếp).

**Testarch** — `_bmad/tea/config.yaml` đã sync: `test_artifacts` → `Stage_5_Build_Verify/test-artifacts/`, kèm `test-design/` · `test-reviews/` · `traceability/`.

### Báo cáo code review

Là output của **`/bmad-code-review`** (KHÔNG phải Superpowers): ghi `NTAPP-output/Stage_5_Build_Verify/reviews/<id>_review.md` theo template chốt `.agent/skills/bmad-code-review/templates/review_report_template.md`. Mỗi finding = 1 heading + **đúng một** dòng `okf-finding:` ngay dưới heading đó; bảng tóm tắt KHÔNG mang marker (đặt cả 2 nơi sẽ đếm 1 finding thành 2). Marker được `hooks/verification_gate.sh` và node review của `slice-loop` / `ad-hoc-per-unit` đọc. Finding bị bác **vẫn giữ lại** với `status: dismissed`, không xoá.

## Visual review loop — lavish (third-party AXI)

Preview gate render-evidence cho HITL UI (thay review markdown chay): mở HTML artifact trong browser local, human annotate element/text → agent nhận feedback qua `npx -y lavish-axi poll`. Skill vendored `.agent/skills/lavish` (MIT), phân phối qua bootstrap (xem §Bootstrap); update upstream bằng `npx skills add kunchenguid/lavish-axi --skill lavish` rồi copy đè. Thiếu skill thì integration point vẫn chạy (steps gọi `npx -y lavish-axi` trực tiếp).

**Bật ở 3 điểm qua `.bmm-config.yaml`** — `ntapp-ui-generation` (`hitl_surface`, opt-in) · `ntapp-feature-design` (`wireframe_preview`, opt-in) · `ntapp-ux-sketch` (`sketch_preview`, **default ON**, hi-fi). Cách render + vòng đời session của từng điểm nằm trong step file tương ứng.

**Guardrails (bắt buộc, áp cho mọi điểm tích hợp):**

- **Agent là người chạy lệnh mở và đưa URL cho user** — annotate chỉ sống trên session URL do local server phục vụ; bàn giao đường dẫn `.html` là bàn giao bản chỉ-đọc. Chỉ `end` session sau khi human xong việc với artifact đó.
- Preview **không phải SSoT, không phải visual đã DS-approve** — canonical vẫn là schema / proposal / `ux_sketch.md`; feedback sửa vào part file rồi re-render, KHÔNG sửa tay HTML. Preview 4b/4a **disposable** (không commit); riêng ux-sketch **RETAINED** (commit làm render-evidence + visual seed cho 4a).
- Style bằng **CSS vars từ `master_token.json` của DS tương ứng unit** (multi-DS: theo `ds-resolution.md`). Preview 4b/4a **TUYỆT ĐỐI không** dùng fallback Tailwind/DaisyUI CDN của lavish — đúng failure mode "library-default look" cần chặn. *Ngoại lệ:* ux-sketch hi-fi được dùng CDN làm engine layout, nhưng theme vars **phải** override bằng token Master DS.
- **CẤM `lavish-axi share`** (publish spec nội bộ lên host bên thứ 3, public by default). `export` chỉ ra bản tĩnh → không dùng làm đường vào tương tác.
- Session URL **machine-local, không phải link chia sẻ** và `/session/{key}` **không có auth** → KHÔNG commit URL vào artifact; **CẤM** `LAVISH_AXI_HOST=0.0.0.0`. Reviewer máy khác thì pull repo rồi tự chạy `npx -y lavish-axi "<path>"`.
- Tắt telemetry: `export LAVISH_AXI_TELEMETRY=0`. Dev-loop only — không đưa vào CI path / VSAF headless run.

## Bootstrap & onboarding

Setup project mới hoặc onboard dev mới qua `./scripts/bootstrap.sh`. Chi tiết đầy đủ: [README.md](README.md).

| Use case | Command |
|---|---|
| Lần đầu setup (project lead) | `./scripts/bootstrap.sh` |
| Upgrade single → multi-repo (clone thêm code repo) | `./scripts/bootstrap.sh --upgrade` |
| Dev mới join (machine-local) | `./scripts/bootstrap.sh --refresh` |
| Preview plan, không apply | `./scripts/bootstrap.sh --dry-run` |
| Non-interactive (CI) | `PROJECT_NAME="..." AUTO_CONFIRM=1 ./scripts/bootstrap.sh` |

**⚠️ Đừng dùng `--refresh` để upgrade single → multi-repo** — nó skip workspace + gitignore block, IDE không mở được multi-folder. Case này dùng `--upgrade`.

| Loại | Artifact | Tạo bởi mode |
|---|---|---|
| Committed | `<project>.code-workspace`, spec repo `.bmm-config.yaml` (sinh khi thiếu/stale, xem dưới), `.gitignore` block (cả 2 repo) | Full / Upgrade |
| Machine-local (gitignored) | Code repo `.bmm-config.yaml`, skill symlink `.agent/skills/`, IDE caches | Full / Upgrade / Refresh |
| Machine-local (git design) | Pre-commit hook (`.git/hooks/`) | Full / Upgrade / Refresh |

Script tự làm (mọi mode): cài VSAF engine nếu thiếu → scaffold SDLC structure → **apply engine patch** → detect repo + sinh workspace/config → **rsync `.agent/skills/` sang `.claude/skills/` + `.cursor/skills/`** (Antigravity qua `scripts/antigravity/install-agy-skills.sh` — agy chỉ đọc `~/.gemini/config/skills/`) → cài pre-commit hook mọi repo → ghi marker `repo_type` (`service-only` / `fullstack`) vào code repo `CLAUDE.md` cho Rule 8 ([Manual §7.5](docs/Process/Manual_phase_1.md#75-repo-scope-service-only-vs-fullstack)).

**Spec repo `.bmm-config.yaml` (Full / Upgrade).** Layer 2, và là **nơi duy nhất** `okf.families` được đọc — khai ở Layer 1 `_bmad/bmm/config.yaml` thì engine bỏ qua trong im lặng. Bootstrap sinh từ `scripts/templates/bmm-config-specrepo.template.yaml` (15 OKF family + override per-skill) khi file **chưa có** hoặc **lộ dấu hiệu chép từ project khác** (header `CODE REPO config` · `project_name` placeholder · `spec_repo_root` trỏ ra ngoài repo); file đã tinh chỉnh tay — có `families:` hoặc block `ntapp-*:` — thì giữ nguyên. Ghi đè luôn backup `.bak.<timestamp>` trước.

> Repo template **không** mang file này. Bootstrap chạy ở đây sẽ sinh lại (repo có `package.json` nên bị xếp là code repo) — artifact machine-local, **đừng commit về**.

Hai thứ đáng nhớ vì ảnh hưởng cách viết workflow YAML — engine patch (`engine-patches/vsaf-4.2.7/apply.sh`, idempotent) thêm 2 node key:

- `fanout:` — glob fan-out.
- `ledger: <path>` — engine đọc file rồi chèn vào **đầu prompt** làm context cross-iteration (cap 16KB, áp cả cho fanout sub-task). **Reader-only** — việc ghi ledger vẫn do prompt điều khiển.

## Portability principle

Skill canonical (`.agent/skills/`) **KHÔNG được** chứa path cụ thể của repo này — mọi output path phải đến từ config file ở project root mà skill đọc lúc runtime. Skill portable không đọc config (`grill-with-docs`, `lavish`) thì giữ nguyên default trong file skill; path riêng của project chỉ khai báo ở CLAUDE.md.
