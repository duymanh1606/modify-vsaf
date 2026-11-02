# Manual Phase 1 — Set up lần đầu & điều hướng workflow

> **Đối tượng:** PM, BA, SA, Tech Lead, UX Designer, Senior Dev, UI Engineer, Dev, QA.
>
> **Phase 1 là gì?** Team làm trực tiếp trong IDE (Claude Code / Cursor). Tài liệu Markdown là nguồn chuẩn duy nhất. Agent gọi qua slash command; người điều phối giữa các bước, không có server tự động.
>
> **Skill stack:** ~26 skill — NTAPP (9) + BMAD (9) + Superpowers (7 core + 1 situational). Bảng đầy đủ: [mục 5](#5-bảng-slash-command--skill-xung-đột).
>
> **Áp dụng khi:** dự án ≤ 3 module pilot, ≤ 15 feature, ≤ 5 module. Vượt ngưỡng: xem [mục 8](#8-khi-nào-hết-phase-1).
>
> **File này:** Hub gồm set up + điều hướng + reference dùng chung cho cả 2 track. PHẦN A (mục 1-3) đọc theo thứ tự khi onboard; PHẦN B (mục 4-8) tra khi cần. Cách chạy từng stage (Stage 0→5) nằm trong 2 file track [Brownfield](Manual_phase_1_brownfield.md) / [Greenfield](Manual_phase_1_greenfield.md), không lặp ở đây.

---

<!-- ════════════ PHẦN A · BẮT ĐẦU Ở ĐÂY (đọc theo thứ tự) ════════════ -->

## 1. Điều hướng — chọn track theo loại dự án

Cả 2 track đều multi-repo và dùng chung phần set up + reference trong file này. Khác nhau ở đường khởi động. Đọc PHẦN A của Hub trước, rồi mở đúng file track để chạy workflow chi tiết:

| | **[Brownfield →](Manual_phase_1_brownfield.md)** | **[Greenfield →](Manual_phase_1_greenfield.md)** |
|---|---|---|
| **Tiền đề** | Hệ thống + code đã tồn tại | Bắt đầu từ con số 0 |
| **Bước đầu** | Dựng lại baseline: DS Bootstrap từ code hiện tại + `/ntapp-system-overview` (default mode `baseline`) → HLD reconcile | Stage 1 Discovery (PRD + Epics) |
| **Nền tảng** | Suy ra WBS / HLD / DS từ hệ thống đang chạy | Dựng mới Stage 1 → 2 → 2b |
| **Yêu cầu mới** | Qua Feature Triage chọn lane (Phase B) | Per-slice loop; feature đến sau cũng triage |

Tóm tắt: brownfield dựng lại DS + kiến trúc hiện có trước, rồi mọi việc mới đi qua triage. Greenfield đi thẳng từ Stage 1. Bức tranh vòng lặp chung: [mục 2](#2-bức-tranh-tổng-quan--5-stage).

---

## 2. Bức tranh tổng quan — 5 stage

Phase 1 gồm 2 phase: **nền tảng** (Stage 1→2→2b→3b — dựng PRD / kiến trúc / WBS / slice plan, rồi **UX Journey Spec** 1 lần ở Stage 3b nếu feature multi-screen mới + **UX Conventions** project singleton) rồi **per-slice loop** (Stage 3a→5, lặp theo từng SLICE-N). Mỗi slice đi 1 vòng spec → build → demo, học xong điều chỉnh slice kế tiếp. *Stage 3b là batch toàn feature — KHÔNG per-slice, vì SCR/WGT liên quan trải rải rác nhiều slice nên trải nghiệm phải design holistic 1 lần. Từ v4.0: 3b KHÔNG spec per-screen (feature-design 4a là single wireframe owner), KHÔNG duy trì §17 inventory (WBS là SSoT) — chỉ giữ archetype + IA delta + journey flows (Key states) + PRD mapping, và tách conventions (principles/content/status/interaction/notification/error/responsive) sang `ux_conventions.md` viết 1 lần, delta-update.*

> Khi bổ sung tính năng mới (thường ở brownfield), chạy lại Stage 1.1–2b ở **chế độ append**: `/ntapp-architecture-design --mode append` mở rộng HLD / Module 0 / WBS cho phần mới, không ghi đè baseline cũ và không re-lock toàn bộ WBS. Sau đó tính năng mới đi tiếp per-slice (brownfield: qua [Feature Triage](Manual_phase_1_brownfield.md#31-stage-05--feature-triage-intake-gate) trước).

Cột Track trong bảng: **BF** = chỉ brownfield · **GF** = chỉ greenfield · **Cả 2** = cả hai · **repo FE** = chỉ khi dự án có frontend · **▸ yêu cầu mới** = chỉ chạy khi có yêu cầu/tính năng mới.

| Phase | Stage | Track | Tên đầy đủ | Làm gì | Output chính |
|---|---|---|---|---|---|
| **Nền tảng** (lần đầu + re-run append khi thêm tính năng) | **Stage 1.0** | BF (baseline) · repo FE (DS) | Khởi tạo nền — onboard (System baseline + Design System bootstrap) | Dựng lại hiện trạng + tạo Master Design System ban đầu — xem ghi chú điều kiện bên dưới | `system-overview` baseline (BF) + Master Design System (repo FE) |
| **Nền tảng** | **Stage 1.1** | Cả 2 | Khám phá (Discovery) | Ghi lại yêu cầu → tài liệu + chia epic/story | Product Requirements (PRD) + Epics & Stories (+ UX Sketch — tuỳ chọn) |
| **Nền tảng** | **Stage 2** | Cả 2 (BF: reproduce/append · GF: fresh) | Kiến trúc (Architecture) | Thiết kế tổng thể + khoá phạm vi build; re-run `--mode append` để mở rộng cho tính năng mới. **BF dừng tại đây sau khi dựng lại hiện trạng.** | High-Level Design (HLD) + Module 0 + `project_wbs.md` (khoá / thêm entry khi append) |
| **Intake** (BF — mỗi yêu cầu mới) | **Stage 0.5** | BF ▸ yêu cầu mới | Phân loại yêu cầu (Feature Triage) | Cổng vào mỗi yêu cầu mới: áp hard gate + cây quyết định → chọn 1 trong 4 lane build | Decision file (lane đã chọn) — [chi tiết](Manual_phase_1_brownfield.md#31-stage-05--feature-triage-intake-gate) |
| **Batch** (1 lần per feature, sau 2b) | **Stage 2b** | Cả 2 · BF ▸ yêu cầu mới | Hoạch định slice (Slice Planning) | Gom WBS (phần yêu cầu mới) thành các lát cắt dọc | Slice manifest `SLICE-*` — dùng cho vòng lặp bên dưới |
| **Batch** (1 lần per feature, sau 2b · trước vòng lặp) | **Stage 0.8** | repo FE ▸ yêu cầu mới · **chỉ khi có Figma vẽ trước** | Nạp thiết kế Figma (Figma Ingest) | Biên dịch Figma thành artifact tĩnh trong spec repo (mapping unit↔frame + layout spec + PNG + Figma↔DS map + token gap) để Stage 4a/4b đọc file local. **Cố ý nằm NGOÀI slice-loop** — xem ghi chú "Figma vẽ trước" bên dưới | `_reference/figma/` (`figma-manifest.yaml`, `specs/*.json`, `frames/*.png`, `figma-ds-map.md`, `token-gap-report.md`) |
| **Batch** (1 lần per feature, sau 2b · trước vòng lặp) | **Stage 3b** | Cả 2 (phần có UI) · BF ▸ yêu cầu mới · **chỉ feature multi-screen mới** | Đặc tả UX hệ thống (System UX Spec) | Thiết kế trải nghiệm **tổng thể cho TOÀN BỘ feature** — union mọi `SCR/WGT` trải qua nhiều slice (không per-slice; SCR/WGT liên quan nằm rải rác nên phải design holistic 1 lần). **Có điều kiện:** chỉ chạy khi feature multi-screen mới (≥2 `SCR-*` nối journey, hoặc actor/flow mới); reuse-journey / single-screen / BE-only **skip** — `feature-design` Stage 4a kế thừa Journey Spec đã có / HLD §6 + `ux_conventions.md` (gate SSoT: `ntapp-ux-design` step-01 §2.0) | UX Journey Spec (slim) + UX Conventions (project singleton) |
| **Per-slice** (lặp mỗi SLICE-N) | **Stage 3a** | Cả 2 · BF ▸ yêu cầu mới | Đặc tả kỹ thuật (Technical Spec) | Đặc tả module thuộc SLICE-N | Technical Spec cho module trong SLICE-N |
| **Per-slice** | **Stage 4a** | Cả 2 · BF ▸ yêu cầu mới | Thiết kế chi tiết (Detailed Design) | Thiết kế từng unit thuộc SLICE-N (kế thừa phần liên quan từ Master UX Spec) — *song song 4b* | `{id}_detailed_design.md` per unit |
| **Per-slice** | **Stage 4b** | repo FE ▸ yêu cầu mới | Lược đồ giao diện (UI Schema) | Sinh schema cho FE unit thuộc SLICE-N — *song song 4a* | `ui_schema_{id}.json` per FE unit |
| **Per-slice** | **Stage 4c** | Cả 2 · BF ▸ yêu cầu mới | Cầu nối story (Story Bridge) | `/bmad-create-story` per unit, gắn `slice_id` | Story file per unit (tag `slice_id`) |
| **Per-slice** | **Stage 5** | Cả 2 · BF ▸ yêu cầu mới | Dựng & Kiểm thử (Build & Verify) | Code + Test + PR → demo lát cắt | Code + Test + Pull Request → demo SLICE-N |
| **Bug lane** (ngoài chuỗi stage · mỗi bug) | **Bug** | Cả 2 ▸ sau demo/test | Ghi nhận & vá lỗi (Log & Fix Bug) | Ghi bug theo slice (append-only, opt-in đẩy Jira) rồi vá — tuần tự 1 file / batch song song trên branch riêng. **KHÔNG qua Feature Triage** — triage là cổng vào của *yêu cầu mới*, không phải của *lỗi* | `BUGS-<SLICE>-<account>.md` + code đã vá (+ branch chưa merge & báo cáo merge order nếu chạy batch) |

> Sau Stage 5: học → quay lại Stage 2b cập nhật SLICE-(N+1) nếu cần, rồi lặp lại Stage 3a→5 cho slice kế tiếp. (Stage 3b UX Spec đã làm 1 lần ở batch — không lặp per-slice; chỉ re-run khi feature mở rộng thêm journey/actor mới.)

> **Bug lane nằm ngoài chuỗi stage, có chủ ý.** Lỗi phát hiện lúc test / demo / UAT đi đường riêng 2 chặng: `/ntapp-log-bug` ghi nhận trước (append-only, 1 file / 1 slice / 1 account — *log trước, fix sau*, đừng fix mò) → `/ntapp-fix-bug` vá tuần tự 1 file (hoặc 1 mã Jira), hoặc `/NTAPP-vsaf-fix-bug` vá cả loạt song song trên branch/worktree riêng có cổng duyệt plan. Cả hai đều ủy quyền việc "fix đúng 1 bug trên 1 unit" cho engine dùng chung `NTAPP-bug-fix-engine`. Chi tiết: [brownfield §3.6](Manual_phase_1_brownfield.md#36-bug-lane--log--fix-sau-demo) · [greenfield §8b](Manual_phase_1_greenfield.md#8b-bug-lane--log--fix-sau-demo) · bảng lệnh [mục 5](#5-bảng-slash-command--skill-xung-đột).

**Đọc bảng theo track:**
- **Greenfield** chạy liền mạch Stage 1.1 → Stage 5; phạm vi ban đầu đã là "yêu cầu mới" nên không cần triage.
- **Brownfield** dựng lại hiện trạng (Stage 1.0 → Stage 2) rồi dừng. Mỗi yêu cầu mới sau đó phải qua Feature Triage trước; triage chọn 1 trong 4 lane, chỉ Lane 3 đi trọn vòng per-slice (Stage 2b → 5). Ba lane còn lại đi đường ngắn hơn.

**Stage 1.0 (onboard) chạy gì** — tuỳ loại dự án và có frontend hay không:
- **System baseline** (`/ntapp-system-overview` — mode `baseline` là default) dựng lại kiến trúc hệ thống đang chạy — chỉ brownfield.
- **Design System bootstrap** sinh Master Design System (`master_token.json`, `components_metadata.json`, `stack-profile.json`) cho Stage 4b — chỉ khi dự án có frontend. Brownfield trích từ code FE đang chạy ([Stage 0](Manual_phase_1_brownfield.md#bước-a1--design-system-bootstrap-từ-code-hiện-tại)); greenfield khởi tạo từ component library ([Stage 0](Manual_phase_1_greenfield.md#7-chuẩn-hoá-design-system--sau-khi-xong-toàn-bộ-slice)). Dự án chỉ có backend thì bỏ qua.

**Figma vẽ trước (Stage 0.8) — ai là nguồn sự thật cho cái gì.** Khi các màn `SCR-*`/`WGT-*` đã có giao diện Figma trước khi build, Agent F3 ở Stage 4a chuyển từ **sáng tác** (author) sang **chép trung thực** (transcribe). Điều đó KHÔNG có nghĩa Figma thắng mọi thứ:

| Khía cạnh | Nguồn sự thật | Figma lệch thì đi đường nào |
|---|---|---|
| Bố cục, thứ bậc, mật độ, chữ hiển thị | **Figma** | — |
| Token (màu / khoảng cách / chữ) & component | **Master DS** | Qua `[NEW]`/`[MODIFIED]` ở Stage 4b + DSO duyệt. Cấm hardcode giá trị lấy từ Figma (Rule 4 chặn) |
| Dữ liệu / field / API | **Detailed Design §3 + Module 0** | Escalate — không tự thêm field vì Figma có vẽ |
| Thông báo lỗi, nhãn trạng thái, notification | **`ux_conventions.md`** | Sửa Figma, không sửa conventions |
| Danh sách unit tồn tại (inventory) | **`project_wbs.md`** | Frame không có unit → `/ntapp-architecture-design --append`, KHÔNG để Figma sinh unit |

Hai điều kiện thiết kế cần biết trước khi dùng:
- **Hai pass, không gộp được.** `ds-bootstrap` cần file token từ Figma để hoà giải, còn full ingest cần `master_token.json` để snap giá trị về token → chạy 1 lượt là deadlock. Trình tự: `/ntapp-figma-ingest --tokens-only` → `/ntapp-ds-bootstrap --external-tokens <path>` → Stage 1-2 (WBS lock) → `/ntapp-figma-ingest` (full).
- **Ingest nằm ngoài vòng lặp, có chủ ý.** Ba lý do: PAT không đi vào các subagent fan-out của slice-loop; slice-loop giữ được tính offline/replay (không network, không rate-limit, không "tuần sau chạy lại ra khác vì designer vừa sửa"); và cổng ký mapping của con người không chen vào giữa vòng lặp AFK. Phần Figma duy nhất nằm trong vòng lặp là **cổng phát hiện lệch, chỉ đọc file**: Hook 3 so `figma_ref.checksum` trong DD với `figma-manifest.yaml`; lệch → chặn, người chạy lại ingest **ngoài** vòng lặp rồi `/NTAPP-vsaf-resume`.

Người dùng chỉ phải cung cấp 3 thứ: env `FIGMA_TOKEN` (**không** đặt vào `.bmm-config.yaml` — file đó được commit), link Figma + phạm vi page, và **ký bảng mapping `WBS unit ↔ frame`**. Việc thứ ba là input người thật duy nhất không tự động hoá được — rẻ đi hẳn nếu yêu cầu designer đặt tên frame trùng ID unit (`SCR-LOGIN`). Không có Figma → mọi thứ chạy y như cũ, Stage 0.8 không tồn tại.

**Ba quy tắc không được phá:**
- Không nhảy cóc stage trong cùng một vòng slice. Chỉ viết code cho một unit sau khi Detailed Design + UI Schema của unit đó đã duyệt.
- Không đặc tả hàng loạt. Stage 3a-4 chỉ làm cho unit thuộc slice đang build; xong slice trước, rút kinh nghiệm rồi mới đặc tả slice sau. *Ngoại lệ: Stage 3b (UX Spec) là batch toàn feature 1 lần — trải nghiệm holistic không xé per-slice được; per-slice chỉ kế thừa.*
- Một slice chỉ **Done** khi chứng minh được nó **ghép vào hệ và chạy**. Review sạch với ATDD xanh chỉ nói từng phần đúng; các mối nối sang service khác còn phải gọi tới đúng endpoint thật. Xem [§6.1](#61-bằng-chứng-lắp-ráp) — ở đó có đủ năm việc cần làm, từ lúc vẽ WBS tới lúc lên staging.

> Mọi dự án tách **spec repo** (tài liệu + Master Design System) khỏi **code repo** (mã nguồn). Stage 1.0 và Stage 4b cần mở cả hai cùng lúc — chi tiết: [mục 7](#7-multi-repo-nếu-áp-dụng).

---

## 3. Set up onboard — bootstrap → skill check → repo

### 3.1 Chạy bootstrap script (bước đầu tiên)

Onboard bắt đầu từ đây. `./scripts/bootstrap.sh` thay ~10 step set up thủ công bằng 1 lệnh: sinh workspace, symlink skill cross-repo, nạp sẵn IDE skill cache (`.claude/skills/` + `.cursor/skills/`), cài pre-commit hook, detect repo scope. Chi tiết: [README.md](../../README.md).

Cài IDE trước (**Claude Code**, **Cursor** hoặc **Antigravity**), rồi chạy đúng mode:

| Mode | Command | PIC | Khi nào dùng |
|---|---|---|---|
| Full | `./scripts/bootstrap.sh` | Project Lead | Lần đầu setup project (1 lần, trước khi team join) |
| Upgrade | `./scripts/bootstrap.sh --upgrade` | Project Lead | Clone thêm code repo vào folder cha (single → multi-repo) |
| Refresh | `./scripts/bootstrap.sh --refresh` | Tất cả role | Team member join project đã setup |

Team member clone bằng `git clone <url>` mặc định để folder name khớp giữa các máy:

```bash
mkdir ~/work && cd ~/work
git clone <git-host>/<spec-repo>.git
git clone <git-host>/<code-repo-A>.git
git clone <git-host>/<code-repo-B>.git

cd ~/work/<spec-repo>
./scripts/bootstrap.sh --refresh
```

Refresh mode lo phần machine-local (symlinks, hook, IDE cache, code repo `.bmm-config.yaml`); không đụng artifact committed.

| Loại | Artifact | Bootstrap mode tạo |
|---|---|---|
| Committed (project lead push 1 lần) | `<project>.code-workspace`, spec repo `.bmm-config.yaml`, `.gitignore` block (cả 2 repo), repo scope block trong code repo `CLAUDE.md` | Full / Upgrade |
| Machine-local — gitignored (mỗi máy tự tạo lại) | Code repo `.bmm-config.yaml`, skill symlink `.agent/skills/`, IDE skill cache `.claude/skills/` `.cursor/skills/` | Full / Upgrade / Refresh |
| Machine-local — git design | Pre-commit hook (`.git/hooks/pre-commit`) | Full / Upgrade / Refresh |

Với multi-repo: sau khi auto-detect code repo, script đọc manifest (`package.json` / `pom.xml` / `go.mod` / ...) đoán mỗi repo `service-only` hay `fullstack`, present 1 bảng cho project lead duyệt cả lô. Repo đã có scope block thì giữ nguyên. Chi tiết: [mục 7.5](#75-repo-scope-service-only-vs-fullstack).

Phạm vi clone theo vai trò:

| Vai trò | Repo cần clone |
|---|---|
| PM, PO | Spec repo (làm việc Stage 1) |
| BA | Spec repo + (tuỳ chọn) code repo read-only cho brownfield analysis |
| SA, Tech Lead, UX Designer | Spec repo + tất cả code repo (đọc code cho HLD / TechSpec / UX) |
| Senior Dev, Dev, UI Engineer | Spec repo + tất cả code repo (Stage 4-5 implement) |
| QA Lead | Spec repo + tất cả code repo (test code sống ở code repo) |
| Design System Owner | Spec repo + tất cả code repo (Stage 0 / 4b cần đọc code) |

### 3.2 Kiểm tra skill đã active

Sau khi bootstrap, kiểm tra **cả 3 bộ skill** (NTAPP + BMAD + Superpowers) có mặt ở **cả 2 nơi**:

- **`.agent/skills/`** — skill canonical (bootstrap symlink cross-repo, nguồn chuẩn duy nhất).
- **`.claude/skills/`** (và `.cursor/skills/`) — IDE skill cache (bootstrap nạp sẵn để slash command hiện trong chat).

```bash
ls .agent/skills/      # phải thấy nhóm ntapp-*, bmad-*, superpowers-*
ls .claude/skills/     # mirror — cùng 3 nhóm
```

Mở IDE, gõ `/` kiểm tra slash command của cả 3 bộ:
- **NTAPP** — `/ntapp-architecture-design`, `/ntapp-ds-bootstrap`, `/ntapp-feature-triage`, ...
- **BMAD** — `/bmad-create-prd`, `/bmad-create-story`, `/bmad-quick-dev`, ...
- **Superpowers** — `/superpowers-test-driven-development`, `/superpowers-brainstorming`, `/superpowers-writing-plans`, ...

Thiếu một nơi hoặc một bộ: chạy lại `./scripts/bootstrap.sh --refresh`. Nếu riêng Superpowers vẫn không hiện (plugin chưa cài):

```
Claude Code:  /plugin install superpowers@claude-plugins-official
Cursor:       /add-plugin superpowers
```

### 3.3 Repo & workspace

Mở folder dự án trong IDE. Mọi artifact (spec repo) ghi vào root `NTAPP-output/`:

```
NTAPP-output/
├── Stage_1_Discovery/                              (PM/BA/PO + UX optional + Stage 0.5 triage)
│   ├── prd.md
│   ├── epics.md
│   ├── ux_sketch/                                  (optional sub-step)
│   │   ├── ux_sketch.md                            (latest)
│   │   ├── ux_sketch_parts/                        (atomic parts)
│   │   ├── previews/                                (preview hi-fi retained — review surface gate Step 05)
│   │   └── archive/                                (snapshot _v1, _v2...)
│   ├── triage/                                     (Stage 0.5 — per-feature intake decisions)
│   │   ├── YYYY-MM-DD-{slug}.md                    (decision file per feature, audit trail)
│   │   └── manifests/                              (opt-in: scope_creep_guardrail manifest YAML)
│   │       └── {id}.yaml
│   ├── Bugs_Issues/                                (Bug lane — /ntapp-log-bug, APPEND-ONLY)
│   │   ├── BUGS-{SLICE-ID}-{account}.md            (1 file / 1 slice / 1 account; bug id = {SLICE}-{account}-BUG-NN)
│   │   └── assets/{SLICE-ID}/{account}/            (ảnh chụp bug — tên file trùng mã bug)
│   └── brainstorms/                                (Superpowers)
│
├── Stage_2_Architecture/                           (SA + Stage 2b slice plan)
│   ├── architecture_design.md                      (HLD latest)
│   ├── 00_system_connectivity_integration.md      (Module 0)
│   ├── project_wbs.md                              (lock binding)
│   ├── slices/                                     (Stage 2b — SLICE-* manifest, drive vòng lặp 3-5)
│   │   ├── SLICE-{n}-{title}.md                    (latest)
│   │   └── archive/                                (snapshot khi re-run update slice)
│   ├── architecture_design_parts/                  (atomic parts)
│   └── archive/                                    (snapshot _v1, _v2...)
│
├── Stage_3_Specs/                                  (3a + 3b song song)
│   ├── techspec/                                   (3a — Tech Lead)
│   │   ├── {module}_techspec.md
│   │   ├── {module}.ts_parts/                      (atomic parts)
│   │   └── archive/
│   └── ux/                                         (3b — UX Designer)
│       ├── ux_design.md                            (journey spec — slim, per feature-batch)
│       ├── ux_conventions.md                       (PROJECT singleton — living doc, delta-update)
│       ├── ux_design_parts/                        (atomic parts)
│       └── archive/
│
├── Stage_4_Design/                                 (4a + 4b song song)
│   ├── detailed_design/                            (4a — Senior Dev)
│   │   ├── {id}_detailed_design.md                 (id = WBS unit ID — SCR-*/WGT-*/<BE-prefix>-*)
│   │   ├── feature_design_parts/{id}/              (atomic parts)
│   │   └── archive/
│   └── ui_schema/                                  (4b — UI Engineer; chỉ FE artifact)
│       ├── ui_schema_{id}.json                     (id = SCR-* hoặc WGT-*)
│       └── archive/
│
├── Stage_5_Build_Verify/                           (Dev / QA)
│   ├── {epic}-{story}-{title}.md                   (story file format BMAD từ Stage 4c, tag slice_id)
│   ├── plans/
│   ├── reviews/
│   ├── reports/
│   └── bug-batches/                                (Bug lane batch — /NTAPP-vsaf-fix-bug)
│       ├── {YYYY-MM-DD}-{slug}/                    (1 batch)
│       │   ├── bug-groups.yaml                     (nguồn sự thật điều khiển bước fix)
│       │   ├── bug-grouping-plan.md                (bản người đọc — duyệt ở HITL gate)
│       │   ├── conflict-matrix.md                  (bằng chứng overlap từng cặp bug/group)
│       │   ├── APPROVED                            (marker HITL — user touch để mở gate)
│       │   └── bug_batch_integration.md            (verify + MERGE ORDER đề xuất)
│       └── _unit-path-map.yaml                     (mapping unit → code repo đã học, không xoá entry cũ)
│
├── ledgers/                                        (cross-iteration context — engine inject vào đầu prompt, cap 16KB)
│   ├── slice-ledger.md                             (slice-loop, tạo per slice)
│   ├── knowledge/{slice}.md                        (bài học per slice)
│   └── bug-fix-ledger.md                           (bug-fix-batch — append per batch, cross-batch)
│
└── design-system/                                  (Master DS, cross-stage)
    ├── registry.yaml                                (CHỈ multi-DS — danh sách DS + binding repo, xem §7.6)
    ├── master_token.json                            (latest, nguồn chuẩn)
    ├── components_metadata.json                     (latest)
    ├── stack-profile.json                           (latest, từ /ntapp-ds-bootstrap)
    ├── master_token_parts/                          (atomic parts từ bootstrap pipeline)
    ├── components_metadata_parts/                   (atomic parts từ bootstrap pipeline)
    ├── bootstrap_report.md                          (report ngày bootstrap gần nhất)
    ├── feature_deltas/                              (per UI artifact delta + build trace)
    │   └── {id}/                                    (id = SCR-* hoặc WGT-*)
    │       ├── proposed_ds_updates.md                    (output Stage 4b Agent 1)
    │       └── build_report.md                      (output /ntapp-ds-build-component)
    ├── {ds_id}/                                     (CHỈ multi-DS — trọn bộ artifact DS thứ 2+ theo registry:
    │                                                  master_token.json, components_metadata.json, stack-profile.json,
    │                                                  component_catalog.md, _reference/, library_apis/, feature_deltas/, archive/)
    └── archive/                                     (snapshot _v1, _v2, ...)
        └── _v{N}_{timestamp}/
            ├── master_token.json
            ├── components_metadata.json
            ├── stack-profile.json
            └── build_report.md                      (nếu apply từ feature delta)
```

Mỗi lần chạy skill NTAPP, bản latest bị đè và snapshot `_v1`, `_v2`... lưu trong `archive/` để audit; folder `*_parts/` giữ phần atomic do sub-agent tạo. Đường dẫn output đọc từ config ở project root — đổi path xem [mục 5](#5-bảng-slash-command--skill-xung-đột).

### 3.4 Khi skill library cập nhật

Sau `git pull` có cập nhật skill (hoặc Tech Lead báo đã update skill), chạy lại:

```bash
./scripts/bootstrap.sh --refresh
```

Refresh reload IDE skill cache để slash command dùng version mới. Không refresh có thể chạy nhầm version cũ, output không khớp template hiện tại.

---

<!-- ════════════ PHẦN B · THAM CHIẾU DÙNG CHUNG — cả 2 track (tra khi cần) ════════════ -->

## 4. Vai trò, quyền approve & handoff

| Vai trò | Việc chính | Approve stage |
|---|---|---|
| **PM** | Đặt intent, business value | Stage 1 (PRD) |
| **PO** | Ưu tiên backlog, validate UX | Stage 1 + co-approve Stage 3b |
| **BA** | Acceptance criteria, user flow | Stage 1 + co-approve Stage 3b |
| **SA** | Architecture, Module 0, co-approve slice plan | Stage 2 + co-approve Stage 2b |
| **Tech Lead** | TechSpec module-level | Stage 3a |
| **UX Designer** | Personas, journey, wireframe | Stage 1 (UX Sketch optional) + Stage 3b (Master UX Spec) |
| **Senior Dev** | Slice plan, Detailed Design feature-level | Stage 2b (chính) + Stage 4a |
| **UI Engineer** | UI JSON Schema, FSM | Stage 4b |
| **Design System Owner** | Curate Master DS | Cross-stage |
| **Dev (FE/BE)** | Implement code | Stage 5 (PR) |
| **QA Lead** | Test strategy, sign-off | Stage 5 |
| **Compliance** | Module 0 changes, AI code review | Cross-stage |

Không tự duyệt artifact của stage mình không phụ trách. Vướng thì escalate, không bypass.

**Handoff giữa các stage:**
1. Người approve commit artifact vào repo (kèm tag version `vN`).
2. Báo người tiếp theo qua PR / Slack: `@<next role> Stage X done — ready for Stage X+1`.
3. Người làm stage tiếp theo pull về, kiểm tra input đủ chưa rồi mới trigger agent.

**Khi bất đồng:**
- Tech Lead vs SA về Module 0 → SA quyết.
- UX vs Tech Lead về data orchestration → iterate 1-2 vòng; không xong thì escalate PM.
- Dev vs Senior Dev về DD → quay lại Stage 4a, không tự sửa code lệch DD.
- Dev vs QA về tiêu chí kiểm thử → QA Lead quyết (QA chịu trách nhiệm sign-off).

---

## 5. Bảng slash command + skill xung đột

> Output skill NTAPP dual-write: bản latest + snapshot `_v{N}` trong `archive/`. Bảng dưới chỉ liệt kê bản latest; path rút gọn từ `NTAPP-output/`.

> **Ưu tiên dùng VSAF workflow — đừng gõ tay từng stage.** Bảng slash command bên dưới (gõ lần lượt `/ntapp-technical-design` → `/ntapp-feature-design` → … → `/bmad-dev-story`) **chỉ là fallback** khi cần can thiệp từng stage riêng lẻ hoặc debug một bước. Cách build **mặc định** là gõ một lệnh chạy nguyên DAG, **dừng ở HITL gate**; resume sau khi ký bằng `/NTAPP-vsaf-resume <runId>`:
> - **Lane 3 (Full per-slice)** — `/NTAPP-vsaf-slice-loop <slice_id>` (vd `/NTAPP-vsaf-slice-loop SLICE-01`) chạy Stage 3→4→5 (techspec → UX → DD → ui-schema → DS-build → story → ATDD → dev → commit → demo), dừng ở HITL **demo** gate. Tiền điều kiện: `project_wbs.md` lock (Stage 2) + slice plan approved (Stage 2b). Demo gate chỉ mở khi `slice-integration` đã kiểm xong **tới từng endpoint**; và trước khi lên staging còn một lượt chạy thử cả feature nữa — xem [§6.1](#61-bằng-chứng-lắp-ráp).
> - **Lane 4 (Ad-hoc per-unit)** — `/NTAPP-vsaf-ad-hoc-per-unit <unit_id>` cho unit mới độc lập, chưa có DD, no contract change: chạy DD → ui-schema → DS-build → story → ATDD → dev → review → commit (skip Stage 2b/3a/UX), dừng ở HITL commit gate. Tiền điều kiện: `project_wbs.md` lock + `unit_id` trong WBS.
> - **Bug lane (ngoài 4 lane)** — `/NTAPP-vsaf-fix-bug <--all | SLICE-01,SLICE-02 | path/BUGS-*.md>` vá **1..N bug** đã log: localize + gom nhóm parallel-safe → dừng ở HITL **approve-plan** gate (`touch <batch_dir>/APPROVED` rồi `/NTAPP-vsaf-resume <runId>`) → fix song song trên branch/worktree riêng → verify + đề xuất merge order. Tiền điều kiện: WBS lock + ≥1 file `BUGS-*.md` (sinh bởi `/ntapp-log-bug`). **KHÔNG merge, KHÔNG push, KHÔNG flip trạng thái bug tự động.** Vá nhanh 1 file / 1 mã Jira ngay tại chỗ thì dùng skill `/ntapp-fix-bug`.
>
> Chi tiết: [CLAUDE.md §VSAF Workflows](../../CLAUDE.md).

| Stage | Slash command | Input | Output folder | Output |
|---|---|---|---|---|
| 0 (pre) | `/ntapp-figma-ingest --tokens-only` (**chỉ khi có Figma**; chạy TRƯỚC ds-bootstrap) | env `FIGMA_TOKEN` + link/`file_key` (+ `--ds` khi multi-DS) | `design-system/.../_reference/figma/exports/` | `figma-tokens.w3c.json` (input cho `--external-tokens`) |
| 0 | `/ntapp-ds-bootstrap` (1 lần / FE repo — nhiều FE repo → mỗi repo 1 DS, xem §7.6) | `.bmm-config.yaml` (+ optional external tokens path khi mention trong prompt) | `design-system/` (multi-DS: `design-system/{ds_id}/`) | `master_token.json`, `components_metadata.json`, `stack-profile.json`, `bootstrap_report.md` |
| **0.8** | **`/ntapp-figma-ingest` (chỉ khi có Figma vẽ trước; sau WBS lock, NGOÀI slice-loop — 1 lần/feature + mỗi lần designer sửa)** | **env `FIGMA_TOKEN` + link + scope page + `project_wbs.md` + `master_token.json`; ⛔ HITL ký bảng mapping unit↔frame** | **`design-system/.../_reference/figma/`** | **`figma-manifest.yaml` (contract), `specs/{unit}.json` (layout tree + control/icon/copy hint), `frames/{unit}[__state].png`, `figma-ds-map.md`, `token-gap-report.md`, `figma_ingest_report.md`** |
| **0.5** | **`/ntapp-feature-triage "intent"` (mỗi feature mới, sau batch done)** | **Intent text + project state (WBS / Module 0 / slice plan / DS)** | **`Stage_1_Discovery/triage/`** | **`YYYY-MM-DD-{slug}.md` (decision file: recommended lane + reasoning + next command + refused paths + giới hạn) + optional `manifests/{id}.yaml` (opt-in `scope_creep_guardrail` cho Lane 4 trigger-B)** |
| 1 | `/bmad-create-prd` → `/bmad-create-epics-and-stories` | Intent prompt | `Stage_1_Discovery/` | `prd.md`, `epics.md` |
| 1 | `/superpowers-brainstorming` | Topic | `Stage_1_Discovery/brainstorms/` | `YYYY-MM-DD-<topic>-design.md` |
| 1 (sub) | `/ntapp-ux-sketch` (optional) | PRD + Epics | `Stage_1_Discovery/ux_sketch/` | `ux_sketch.md` |
| 1 (sub) | `/ntapp-system-overview` (**mode `baseline` là default** — brownfield, trước HLD) | Multi-root workspace + scope confirm + interactive Q&A | `Stage_1_Discovery/system_overview/` | `{sub_system}.md` × N (10 sections + Section 0 Service Identity + Section E Open Questions), `_overview.md` (gồm Contract Match Matrix cross-repo) |
| 1 (sub) | `/ntapp-system-overview --mode overview` (opt-in — per-repo onboarding doc, KHÔNG Contract Matrix / Q&A) | Multi-root workspace + scope confirm | `Stage_1_Discovery/system_overview/` | `{repo}_overview.md` × N (10 sections, prose-friendly) |
| 2 | `/ntapp-architecture-design` | "Trigger HLD cho module X" | `Stage_2_Architecture/` | `architecture_design.md`, `00_system_connectivity_integration.md`, **`project_wbs.md`** |
| **2b** | **`/ntapp-slice-planning` (sau WBS lock, trước Stage 3b + vòng lặp)** | **WBS + Module 0 + Epics (KHÔNG cần DD)** | **`Stage_2_Architecture/slices/`** | **`SLICE-{n}-{title}.md` (gom unit thành vertical slice demoable; cổng kiểm không sót unit, không vòng lặp phụ thuộc, đúng thứ tự build và không có hub âm thầm dùng chung; dùng cho vòng lặp Stage 3a-5)** |
| 3b | `/ntapp-ux-design` (**batch 1 lần toàn feature**, sau 2b · trước vòng lặp — union SCR/WGT mọi slice, KHÔNG per-slice; **chỉ feature multi-screen mới**: ≥2 `SCR-*` nối journey / actor mới; reuse/single-screen/BE-only skip → 4a kế thừa) | PRD + Epics + HLD + WBS | `Stage_3_Specs/ux/` | `ux_design.md` (journey spec slim: archetype + IA delta + journey screen tables với Key states — KHÔNG per-screen spec/§17) + `ux_conventions.md` (project singleton, delta-update) |
| 3a | `/ntapp-technical-design` (per slice, cho module thuộc SLICE-N) | Module name | `Stage_3_Specs/techspec/` | `{module}_techspec.md` |
| 4a | `/ntapp-feature-design` (per unit thuộc SLICE-N — kế thừa phần liên quan từ Master UX Spec; **có Figma → tự chạy TRANSCRIBE mode** theo `figma_status` trong manifest) | ID đơn vị work (`feature_id` / `screen_id` / `widget_id` từ WBS) | `Stage_4_Design/detailed_design/` | `{id}_detailed_design.md` (Figma: thêm `figma_ref` §1 + §2.5 Deviation log) |
| 4b | `/ntapp_ui_generation` (chỉ FE unit thuộc SLICE-N) | `SCR-*` hoặc `WGT-*` ID + Master DS | `Stage_4_Design/ui_schema/`, `design-system/feature_deltas/{id}/` | `ui_schema_{id}.json`, `proposed_ds_updates.md` |
| 4b (gate) | `/ntapp-ds-build-component` (nếu delta có `[NEW]`) | `proposed_ds_updates.md` | `design-system/`, `src/.../{component}/` | `build_report.md`, scaffolded files, updated `master_token.json` + `components_metadata.json` |
| 4c | `/bmad-create-story` (per `feature_id` BE / per `screen_id` FE thuộc SLICE-N, tag `slice_id`) | DD + UI schema + HLD + TechSpec + SLICE-N manifest | `Stage_5_Build_Verify/` | `{epic}-{story}-{title}.md` (story file format BMAD, status `ready-for-dev`, `slice_id` required) |
| 4c (optional) | `/bmad-sprint-planning` (1 lần per epic) | `epics.md` | `Stage_5_Build_Verify/` | `sprint-status.yaml` |
| 5 (Path A) | `/bmad-dev-story` | Story file (output 4c) | `<code-repo>/src/`, `<code-repo>/tests/` | Code + tests qua red-green-refactor cycle per subtask (TDD built-in) |
| 5 (Path B) | `/bmad-quick-dev` | Intent prompt | `<code-repo>/src/` + `NTAPP-output/Stage_5_Build_Verify/specs/` | Spec file + code (test-first KHÔNG enforced) |
| 5 (mandatory ATDD) | `/bmad-testarch-framework` (1 lần per module) | Code repo manifest | `<code-repo>/tests/`, `<code-repo>/NTAPP-output/test-artifacts/` | Test framework scaffold + setup log (rationale ghi trong commit message của lần setup) |
| 5 (mandatory ATDD) | `/bmad-testarch-atdd` (per feature) | Story file (output 4c) | `<code-repo>/tests/{e2e,api}/`, `<code-repo>/NTAPP-output/test-artifacts/atdd-checklist-{story_key}.md` | Red-phase test scaffolds + live checklist |
| 5 | `/bmad-code-review` (dev tự chạy trước PR + QA tuỳ chọn chạy lần 2) | Uncommitted diff hoặc PR diff | `Stage_5_Build_Verify/reviews/` | `<id>_review.md` theo template chốt `.agent/skills/bmad-code-review/templates/review_report_template.md` (mỗi finding = 1 dòng `okf-finding:`) |
| 5+ | `/superpowers-using-git-worktrees`, `superpowers-test-driven-development` (chỉ Path B), `superpowers-systematic-debugging`, `superpowers-verification-before-completion`, `superpowers-receiving-code-review`, `superpowers-finishing-a-development-branch` | Branch / feedback | (no artifact) | Disciplined merge |
| **Bug** | **`/ntapp-log-bug` (mỗi lần phát hiện lỗi — append-only)** | **Mô tả bug (+ màn hình & ảnh dán trong chat, + API path/method); opt-in: đẩy Jira + Assignee** | **`Stage_1_Discovery/Bugs_Issues/`** | **`BUGS-{SLICE-ID}-{account}.md` (append 1 entry `{SLICE}-{account}-BUG-NN`, trạng thái `Open`) + `assets/{SLICE-ID}/{account}/*.png`; opt-in: Jira issue `Bug`/`Issue` + dòng link Jira ghi ngược vào entry** |
| **Bug** | **`/ntapp-fix-bug` (vá tuần tự — 1 file bug hoặc 1 mã Jira)** | **Path `BUGS-*.md` HOẶC mã Jira / URL `/browse/<KEY>`; 2 HITL gate (duyệt fix plan · duyệt nội dung ghi lên Jira)** | **`<code-repo>/src/` + spec repo (doc-sync)** | **Code đã vá + doc spec đã sync + trạng thái bug flip `Fixed`; opt-in: Jira → `Resolved` + assign lại Reporter. KHÔNG tự commit** |
| **Bug** | **`/NTAPP-vsaf-fix-bug` (vá batch song song — 1..N file bug)** | **`--all` \| `SLICE-01,SLICE-02` \| path `BUGS-*.md`; 1 HITL gate (`approve-plan`)** | **`Stage_5_Build_Verify/bug-batches/{date}-{slug}/` + branch trong code repo** | **`bug-groups.yaml`, `bug-grouping-plan.md`, `conflict-matrix.md`, `bug_batch_integration.md` (MERGE ORDER) + branch/worktree chưa merge; append `ledgers/bug-fix-ledger.md`. KHÔNG merge / push / flip status** |

**Đổi đường dẫn output:**

| Stack | File config | Cách đổi |
|:---|:---|:---|
| BMAD official | `_bmad/bmm/config.yaml` | sửa `planning_artifacts`, `implementation_artifacts` |
| NTAPP | `_bmad/bmm/config.yaml` + `.bmm-config.yaml` | thêm/sửa section theo tên skill |
| Superpowers | `CLAUDE.md` ở project root | sửa block "Plugin output overrides" |

**Skill xung đột — chọn cái nào:**

| Tình huống | Chọn | KHÔNG dùng |
|---|---|---|
| Brainstorming | `bmad-brainstorming` | — |
| Code review | `bmad-code-review` | `superpowers:requesting-code-review` (duplicate) |
| TDD trong story-driven path (Path A Stage 5) | `bmad-dev-story` (TDD built-in) | Không lặp lại `superpowers-test-driven-development` |
| TDD trong quick path / refactor / bug fix (Path B) | `superpowers-test-driven-development` | — |
| Generate acceptance test scaffolds (Mandatory ATDD) | `bmad-testarch-atdd` | Không tự viết test stub manual |
| Setup test framework (1 lần per module) | `bmad-testarch-framework` | — |
| Implementation planning per feature | DD (Stage 4a) + Story file (Stage 4c) | `superpowers:writing-plans` (NTAPP đã có context sâu hơn) |
| Story execution (formal path) | `bmad-dev-story` | `superpowers:executing-plans`, `:subagent-driven-development` (overlap) |
| Plan execution non-NTAPP (vd refactor cross-cutting standalone) | `superpowers:executing-plans` | — |
| Receive code review feedback | `superpowers-receiving-code-review` | — |
| Branch finishing (merge/PR/discard) | `superpowers-finishing-a-development-branch` | — |
| Ghi nhận 1 lỗi phát hiện khi test / demo / UAT | `ntapp-log-bug` (append vào `BUGS-*.md`, tự suy slice qua WBS unit) | Ghi tay vào file rời hoặc tạo Jira tay — mất trace về WBS unit + slice, và mất quy ước đánh số chống conflict |
| Vá bug **đã được log** (file `BUGS-*.md` / mã Jira) | `ntapp-fix-bug` (1 file, tuần tự, không commit) hoặc `NTAPP-vsaf-fix-bug` (batch, song song trên branch riêng) | `path-b-quick-dev` — lane đó nhận **intent text** cho 1 unit, không đọc file bug và không quản trạng thái bug |
| Fix 1 bug **đã localize** chắc chắn unit + file | `NTAPP-bug-fix-engine` (được orchestration gọi) | Gõ trực tiếp khi chưa localize — phải qua intake `ntapp-fix-bug` / `NTAPP-vsaf-fix-bug` trước |

### 5.1 Phân loại Mandatory ATDD (canonical)

> **Nguồn sự thật duy nhất.** Greenfield/brownfield flow trỏ về bảng này; enforce bằng Hook 8 `hooks/atdd_classifier.sh` (decision point ⛔, event `UserPromptSubmit` trước `/bmad-dev-story`).

**Nguyên lý gốc:** Mandatory ATDD khi behavior sai gây **thiệt hại đo được** (tiền/dữ liệu/uy tín/compliance), **HOẶC** tính đúng chỉ xác nhận được **qua một ranh giới mà unit-test không vượt nổi**. Các trigger dưới là **proxy nhanh** của nguyên lý này — `match ≥1` (bất kỳ A* hoặc B*) → **Mandatory**.

| Nhóm | # | Trigger | Vì sao cần acceptance test (không phải chỉ unit-TDD) |
|---|---|---|---|
| **A — test-level necessity** | A1 | **Cross-system**: behavior phụ thuộc ≥2 service/process | seam vượt process → mock cho false confidence |
| | A2 | **Multi-actor stateful**: ≥2 actor HOẶC ≥2 chuyển-trạng-thái tuần tự có thứ tự/ủy quyền (duyệt, handoff, escalation, đồng ký) | journey phân mảnh qua nhiều unit |
| | A3 | **Async / eventual-consistency / resilience**: kết quả phụ thuộc retry, queue, lan truyền trễ, nhánh phục hồi lỗi | chỉ E2E quan sát được trạng thái hội tụ |
| **B — blast-radius** | B1 | **Critical domain** (danh sách hợp nhất): money/billing · auth · RBAC/permission · PII/audit-compliance | sai → thiệt hại tiền/bảo mật/compliance |
| | B2 | **Destructive / irreversible**: xóa hàng loạt, migration dữ liệu, đổi trạng thái không hồi phục | sai → mất dữ liệu không khôi phục |

**Fallback (QA Lead phán đoán):** không trigger A/B nào khớp nhưng fail gây thiệt hại đo được hoặc có audit requirement → escalate **Mandatory**. QA Lead ghi quyết định vào front-matter story (`atdd: mandatory` / `atdd: optional`) — override này luôn thắng classifier.

**Optional (allow-list):** UI tweak · copy/i18n · config · refactor **không đổi behavior** · spike/POC.

**Logic:** `khớp A*/B* → Mandatory` · `else Fallback (thiệt hại đo được / audit) → Mandatory` · `else → Optional`. KHÔNG có nhánh "ambiguous theo độ dài".

**Bugfix KHÔNG ở gate này.** Regression-reproduction (failing test tái hiện bug trước khi vá) là practice riêng, thuộc pipeline bugfix (`path-b-quick-dev` / `bug-fix-batch` / `ntapp-qa-pipeline-bugfix`) dưới dạng *mandatory failing regression test* — không gọi là acceptance-ATDD.

> Ở **bug lane**, gate này được engine `NTAPP-bug-fix-engine` áp **thích ứng** (ceremony-adaptive), không đồng loạt: `atdd_class = mandatory` (khớp ≥1 trigger A*/B* ở bảng trên) hoặc bug chạm contract → bật test-first RED→GREEN + DD reconstruct; bug vặt (express / style thuần) → chỉ fix + verify tĩnh. `severity` trong `BUGS-*.md` **không** trực tiếp bật gate nào — nó chỉ để sắp thứ tự và suy `lane` khi caller không truyền.

---

## 6. Quy tắc bắt buộc — Không bypass

Phase 1 không có gate tự động đầy đủ; chống bypass dựa vào kỷ luật + visibility.

**Pre-commit hook chặn (Rule 1-9):**

1. Mọi file code có header `id: <ID>` + `dd_version: vN` trong 10 dòng đầu (1 key `id:` duy nhất, không tách `feature_id` / `screen_id` / `widget_id`). Loại unit phân biệt qua ID prefix: UI extension (`.tsx/.jsx/.vue/.html/.css/.scss/.sass/.less`) bắt buộc `SCR-*` hoặc `WGT-*`; extension khác bắt buộc prefix khác.
2. `<id>` phải có trong `project_wbs.md` (markdown table cột đầu — mọi loại ID: feature / screen / widget / contract).
3. File `{id}_detailed_design.md` phải tồn tại trước khi merge code của unit đó.
4. UI code không hardcode color hex / px / font name — phải reference token từ Master DS.
5. UI code không tạo custom widget nếu Master DS đã có Component tương đương.
6. UI code: file `ui_schema_{id}.json` phải tồn tại trước merge (id lấy từ header).
7. `proposed_ds_updates.md` có `[NEW]` → `build_report.md` phải tồn tại trong cùng `feature_deltas/{id}/` (checksum khớp). Chưa chạy `/ntapp-ds-build-component` thì hook chặn.
8. Code repo `repo_type: service-only` → cấm commit infra paths (Dockerfile, CI config, helm / k8s / terraform / ansible, devcontainer). Repo `fullstack` hoặc không khai báo → không enforce. Test framework config KHÔNG thuộc forbidden. Chi tiết: [mục 7.5](#75-repo-scope-service-only-vs-fullstack).
9. UI files không chứa unicode emoji (U+2600-U+27BF, U+1F300-U+1FAFF). Emoji trong wireframe chỉ là gợi ý hình ảnh; Stage 4b đã chuyển sang `icon_bindings`, code import icon từ `stack-profile.icon_library`. Cần emoji thật (chat content, emoji picker/reaction): thêm pragma `// allow-emoji` (hoặc `# allow-emoji` / `<!-- allow-emoji -->`) trong 10 dòng đầu.

> 9 rule trên soi từng file. Ngoài ra còn hai hook soi **toàn bộ bản thiết kế**, chạy ở cổng duyệt Stage 2 và 2b: một hook kiểm WBS đã vẽ đủ đường đi chưa, một hook kiểm thứ tự build giữa các slice và cảnh báo hub dùng chung. Chi tiết: [§6.1](#61-bằng-chứng-lắp-ráp).

**Skill tự enforce (không qua hook):**

10. Stage 0 / 4b skill cần multi-root workspace mở cả 2 repo. `/ntapp-ds-bootstrap` và `/ntapp-ds-build-component` đọc code từ code repo, ghi metadata sang spec repo; workspace chỉ mở 1 repo thì skill báo lỗi rồi dừng. Mở đúng file `.code-workspace` (bootstrap đã sinh) trước khi gõ slash command. Trục trặc config: [mục 7.3](#73-khi-gặp-trục-trặc).
11. **(Chỉ project có Figma)** Hook 3 chặn khi thiết kế đã đổi sau lúc ký Detailed Design: so `figma_ref.checksum` trong `{id}_detailed_design.md` với `figma-manifest.yaml`. Chặn nghĩa là *phải chạy lại `/ntapp-figma-ingest` (ngoài slice-loop) rồi refresh DD + bump `dd_version`* — không phải bỏ qua. Cổng này **chỉ đọc file, không gọi mạng**, nên chạy được trong VSAF headless. Ba trường hợp KHÔNG chặn (chỉ cảnh báo): unit `figma_status: missing`/`stale` (đang ở author mode), DD chưa tồn tại (lần đầu), DD không có `figma_ref` (được author trước khi ingest). Bỏ qua có chủ ý: `DISABLE_FIGMA_DRIFT_GATE=1`.
    > Ngược lại — `figma_ref` **thiếu** trong DD của unit đã mapped thì cổng không chặn được gì. Đó là lý do Stage 4a bắt buộc ghi dòng này ở §1 khi chạy TRANSCRIBE mode.

**Header `id:` — prefix & ví dụ.** Hook đọc prefix của giá trị ID để biết loại file: `SCR-*` = màn hình FE · `WGT-*` = widget FE dùng chung · prefix khác (`MPF-`, `HUB-`, `INT-`...) = file BE / contract. File UI bắt buộc `SCR-*`/`WGT-*`; file khác bắt buộc prefix khác. Header viết theo syntax comment của ngôn ngữ:

```ts
// id: SCR-COMPOSE | dd_version: v1
```
```py
# id: HUB-01 | dd_version: v1
```
```html
<!-- id: WGT-SIDEBAR | dd_version: v1 -->
```

Hook reject nếu: thiếu dòng `id:` trong 10 dòng đầu (header cũ kiểu `feature_id:`/`screen_id:`/`widget_id:` cũng bị reject để buộc đổi sang convention mới); có `id:` nhưng thiếu `dd_version:`; prefix không khớp đuôi file. Dùng tập prefix UI khác (vd thêm `PAGE-`): set env trước khi commit (mặc định `^(SCR|WGT)-`):

```bash
export UI_ID_PREFIX_PATTERN="^(SCR|WGT|PAGE)-"
```

**Exception ghi 1 repo cho Stage 4b skill.** `/ntapp-ds-build-component` và `/ntapp_ui_generation` mặc định cần multi-root workspace (Rule 10). Khi một story Stage 5 chỉ ghi spec repo (vd chuẩn bị Master DS metadata + UI schema cho story khác implement), dev có thể chạy tay phần ghi spec repo nếu thoả cả 3:

1. Ghi rõ deviation trong story `Completion Notes`, tham chiếu section của canonical skill đã thay thế (`{skill}/workflow.md` + `step-N.md`).
2. Chứng minh tương đương trong `Debug Log`: output JSON / YAML khớp schema template (field-by-field hoặc checksum).
3. Phần code repo dời thành task tường minh ở story consumer (vd scaffold Angular component, flip `metadata.status` `experimental` → `active`).

Không dùng exception này nếu story scope có sửa code repo — lúc đó multi-root workspace là bắt buộc.

**Express lane cho hotfix.** Hotfix không phải lúc nào cũng cần full Detailed Design. Có mini-DD template (~30 phút) cho 5 loại pre-approved: typo, config change, log level, lint fix, test fix. Điều kiện: cập nhật full DD + ripple audit trong 48h sau merge, trễ thì block PR tiếp theo của dev đó. Bypass hook khẩn cấp: `SKIP_PRECOMMIT=1 git commit`.

**Tránh:**
- Skip stage sửa thẳng code (drift, audit fail).
- Tự sửa Module 0 trong app repo (phải qua SA + Compliance).
- Hardcode design token.
- Fork skill library sang app repo riêng (mất nguồn canonical).
- Cấm 100% hotfix thay vì dùng Express Lane.

### 6.1 Bằng chứng lắp ráp

Tình huống rất hay gặp: mỗi service đều qua review, ATDD của từng story đều xanh, nhưng ghép lại thì màn hình gọi API trả 404 — hoặc gọi đúng đường mà sai method, trả 405. Không cổng nào bắt được, vì mọi cổng chỉ hỏi *"phần này làm xong chưa"*, chưa ai hỏi *"hai phần này có thật sự nói chuyện được với nhau không"*.

Năm việc dưới đây bịt khoảng trống đó, trải từ lúc vẽ kiến trúc tới lúc bấm demo. Điểm chung của cả năm: chỉ kiểm những mối nối **đã được khai báo** trong WBS, không quét code để đoán xem còn mối nối nào nữa. Máy đoán thì máy sẽ bịa ra liên kết không có thật; còn khai thiếu là lỗi của bản thiết kế, và phải sửa ở bản thiết kế.

**1. Vẽ WBS thì vẽ đủ đường đi (Stage 2).** Bảng Coverage Matrix trong `project_wbs.md` là chỗ duy nhất máy đọc để biết ai gọi ai — đừng viết tay thêm bảng thứ hai cho người đọc, hai bảng rồi sẽ lệch nhau. Khi lập bảng, đảm bảo:

- Mỗi màn hình / widget (`SCR-*`, `WGT-*`) ghi rõ nó gọi những gì, ở cột `consumes`.
- Mỗi hợp đồng `INT-*` ghi rõ ai phục vụ (`provider`) và những ai gọi (`consumers`).
- Unit chỉ đứng giữa chuyển tiếp — proxy, gateway, BFF, tầng gom dữ liệu — khai `role` tương ứng, **và** khai tiếp nó gọi xuống đâu. Thiếu vế sau thì đường đi đứt ngay giữa bảng.
- Mọi lời gọi giữa hai service nội bộ đều gắn với một `INT-*`. Không có đường nào chạy chui mà không có hợp đồng.

Thiếu mục nào, cổng duyệt Stage 2 chặn kèm danh sách chỗ còn trống — sửa đúng những dòng đó rồi duyệt lại.

**2. Xếp slice thì xếp đúng thứ tự (Stage 2b).**

- Slice nào dùng tới một unit thì unit đó phải được build **ở chính slice ấy**, hoặc ở một slice nằm trước nó trong chuỗi `blocked_by`. Xây sau mà xài trước thì tới lúc chạy không có gì để gọi.
- Một unit được nhiều slice dùng chung nhưng chỉ build một lần thì phải đánh dấu `growable` cho rõ chủ ý. Không đánh dấu, nó lặng lẽ phình thành cục hub gánh cả hệ mà không ai để ý.
- Tốt hơn cả là **đừng để có hub**: ngay từ Stage 2, tách nó thành vài unit nhỏ theo từng việc, mỗi unit về đúng slice cần nó. Cách này gọn hơn hẳn `growable` — mỗi unit làm một lần là xong, không cần mở lại để thêm việc.

Còn vướng chỗ nào, hook ghi vào `_drift_report_slice.md` và cổng duyệt 2b chặn cho tới khi hết.

**3. Cuối mỗi slice, kiểm tới tận endpoint.** Node `slice-integration` không dừng ở mức "cả hai đầu đều tồn tại". Với mỗi lời gọi đã khai trong WBS, nó lấy đúng cặp (method, path) mà bên gọi dùng rồi đối chiếu với bảng route thật của bên phục vụ.

- Không khớp mà bên phục vụ **đã xong** → bug thật, chặn lại: slice bị đánh dấu không ship được và không cho bấm demo.
- Không khớp vì bên phục vụ **nằm ở slice sau chưa build** → bình thường, chỉ ghi nhận, không chặn.

**4. Trước khi lên staging, chạy thử cả feature.** Node `feature-integration-smoke` chạy trước bước scan/build của `staging-deploy`, gồm hai mức:

- **Kiểm tĩnh** (luôn chạy, nhanh và rẻ): mọi lời gọi phải đi trọn đường — từ màn hình, qua proxy, tới service cuối. Đây là bước tóm 404 / 405 trên phạm vi cả feature, chứ không chỉ trong một slice.
- **Kiểm live** (khi project dựng được): bật các service liên quan lên rồi chạy bộ smoke theo từng luồng người dùng.

Còn lời gọi nào chưa tới đích thì chưa lên staging.

**5. Slice xong không đồng nghĩa với slice chạy được.** Review sạch và ATDD xanh mới chỉ chứng minh từng phần đúng. Muốn bấm `demo_status: passed`, slice còn phải chứng minh các mối nối của nó thật sự thông: qua được bước 3 ở trên, và số liệu của nó vào được bước 4. Thiếu bằng chứng đó, demo gate không mở.

---

## 7. Multi-repo (nếu áp dụng)

### 7.0 Bối cảnh

Pattern brownfield phổ biến — project tách thành 2 repo trở lên:
- **Spec repo** — tài liệu (PRD, HLD, TechSpec, DD), Master DS metadata, `proposed_ds_updates.md` / `build_report.md`. Nguồn chuẩn cho documentation và Master DS.
- **Code repo** — source code app (1 repo / app / sub-system). Nơi component thật sự sống.
- (Tuỳ chọn) **Contracts / proto repo** — gRPC / REST IDL dùng chung.
- (Tuỳ chọn) **Meta repo** — skill library, workspace template, pre-commit script dùng chung.

Stage 0 và Stage 4b đọc code từ code repo nhưng ghi metadata về spec repo, nên IDE phải mở **multi-root workspace** thấy cả 2 repo cùng lúc. Single-repo greenfield không cần phần này.

### 7.1 Cấu trúc repo và workspace

> Khuyến nghị dùng bootstrap script ([mục 3.1](#31-chạy-bootstrap-script-bước-đầu-tiên)) — tự sinh workspace, `.bmm-config.yaml` per code repo, symlink skill library, cài hook + `.gitignore` block. Phần dưới là reference khi cần customize / debug.

Clone về cùng folder cha để đường dẫn tương đối (`../<repo>`) ngắn gọn:

```
~/work/
├── <spec-repo-folder>/             ← spec repo (tài liệu + Master DS metadata)
├── <code-repo-folder-A>/           ← code repo app A
├── <code-repo-folder-B>/           ← code repo app B (nếu có)
└── <meta-repo-folder>/             ← meta repo (tuỳ chọn — skill library + workspace template)
```

File `.code-workspace` liệt kê folder mở cùng lúc:

```json
{
  "folders": [
    { "name": "spec-repo", "path": "../../<spec-repo-folder>" },
    { "name": "code-repo-A", "path": "../../<code-repo-folder-A>" }
  ],
  "settings": {
    "files.exclude": { "**/node_modules": true, "**/NTAPP-output/archive": true }
  }
}
```

Mở bằng `code <path>/full.code-workspace`. Path phải tương đối (absolute `/Users/...` thì workspace không portable). Per code repo cần: `.bmm-config.yaml` (sửa `bmad.spec_repo_root` trỏ tới spec repo), skill library symlink tới `<meta-repo>/.agent/skills/` (không fork), và `CLAUDE.md` riêng mô tả domain repo.

### 7.2 Quy trình commit khi skill chạy xong

`/ntapp-ds-build-component` (Stage 4b) sinh thay đổi ở cả 2 repo.

Spec repo: `master_token.json`, `components_metadata.json` (cập nhật), `feature_deltas/{id}/build_report.md` (file mới), `archive/_v{N+1}_{ts}/` (snapshot).

Code repo: file mới ở `{component_target_root}/{component_name}/...` (NEW component), patch file cũ (MODIFIED), và file token runtime tại `{stack-profile.runtime_token_path}` (vd Angular `src/styles/_design-tokens.scss`, React `tailwind.config.js`) — overwrite full mỗi run, header `AUTO-GENERATED — DO NOT EDIT`; chỉ kèm commit khi NEW/MODIFIED token.

**Thứ tự commit:**
1. Commit code repo trước. Verify build / lint / type check pass. PR title `feat({id}): scaffold/patch components per Master DS delta`.
2. Commit spec repo sau, chỉ sau khi code repo PR merge (hoặc ít nhất CI pass). PR title `chore({id}): apply Master DS delta`, link tới PR code repo.
3. Merge spec repo PR sau khi xác nhận code repo PR đã merge.

Lý do thứ tự: nếu spec repo merge trước mà code repo fail thì spec repo "tin" có component mới nhưng code chưa scaffold, feature import sau sẽ fail. Truy vết: đặt cùng `<id>` ở header 2 commit, grep `git log --grep="id: <ID>"` ở từng repo.

### 7.3 Khi gặp trục trặc

| Triệu chứng | Nguyên nhân | Cách xử lý |
|:---|:---|:---|
| Skill báo "phải chạy trong code repo" rồi dừng | Workspace single-root, chỉ thấy spec repo | Mở lại file `.code-workspace` đa root, gõ lại slash command |
| Skill báo không tìm thấy `package.json` | `bmad.code_repo_root` config sai, hoặc chạy ngoài cả 2 repo | Verify đường dẫn trong `.bmm-config.yaml` của code repo |
| Skill báo "target dir rơi vào spec repo" | `component_target_root` resolve nhầm, hoặc spec/code repo cùng path | Kiểm tra `bmad.spec_repo_root` ≠ `bmad.code_repo_root` |
| File scaffold xong nhưng IDE không hiện diff | Code repo không nằm trong workspace | Mở lại multi-root workspace có cả code repo |
| Master DS commit OK nhưng component code chưa thấy | Quên commit code repo | Switch sang code repo, commit + push, link tới PR spec repo |
| Spec repo bỗng có file Angular / React | `bmad.spec_repo_root` = `bmad.code_repo_root`, hoặc run cũ trước khi có guard | Revert spec repo commit, di chuyển `src/` về code repo, sửa config 2 path khác nhau, chạy lại |

### 7.4 Hạn chế hiện tại

- Agent không tự discover symbol ở repo khác trừ khi multi-root workspace đang mở.
- Đổi contracts / proto repo không tự thông báo sang code repo phụ thuộc — phải báo thủ công.
- Commit cross-repo không atomic — phải bám thứ tự commit ở [mục 7.2](#72-quy-trình-commit-khi-skill-chạy-xong).

> Cross-repo task tần suất cao hoặc > 5 repo → cân nhắc Phase 1.5 (thêm MCP service headless cho cross-repo discovery + drift detection).

### 7.5 Repo scope (service-only vs fullstack)

Khi chạy Stage 5, agent hay tự sinh `Dockerfile`, `.github/workflows/`, `helm/`, `terraform/` vào code repo của service. Team chỉ own service code thường không muốn hạ tầng nằm chung repo (infra do team Platform / DevOps own ở repo khác). Để chặn, mỗi code repo declare `repo_type` trong marker block của `CLAUDE.md` (bootstrap tự ghi):

| `repo_type` | Áp dụng cho | Pre-commit Rule 8 |
|---|---|---|
| `service-only` | Repo chỉ chứa service code (BE microservice, API gateway, worker). Infra ở repo khác. | Chặn commit đụng forbidden paths |
| `fullstack` | Repo chứa cả service + UI (monorepo, BFF) hoặc cố ý hold infra. | Không enforce |
| `unknown` | Bootstrap không suy ra được từ manifest. | Không enforce; user sửa CLAUDE.md hoặc chạy `--upgrade` để re-detect |

**Forbidden paths khi `service-only`:** `Dockerfile`, `docker-compose*.y[a]ml`, `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`, `helm/`, `chart/`, `charts/`, `k8s/`, `kubernetes/`, `manifests/`, `terraform/`, `*.tf`, `*.tfvars`, `ansible/`, `.devcontainer/`.

Chỉ chặn hạ tầng thật (container / CI/CD / orchestration / IaC / dev env). Test framework (Playwright, Cypress, Vitest, Jest, Pytest, Junit, Supertest, Pact...) KHÔNG thuộc forbidden — đó là test code, do `/bmad-testarch-framework` tự detect stack chọn framework đúng.

**Bootstrap đoán scope ra sao:** sau khi auto-detect code repo, đọc manifest đoán scope, present 1 bảng cho project lead duyệt cả lô.

| Manifest signal | Đoán | Ví dụ |
|---|---|---|
| `package.json` có FE deps (`react` / `next` / `vue` / `svelte` / `@angular/core` / `nuxt` / `remix` / `astro` / `solid-js` / `preact` / `qwik`) | `fullstack` | Next.js app, Angular workspace |
| `package.json` chỉ có BE deps (`express` / `fastify` / `@nestjs/core` / `koa` / `hapi` / `hono`) | `service-only` | NestJS service, Express API |
| `pom.xml` / `build.gradle` / `go.mod` / `Cargo.toml` / `pyproject.toml` / `requirements.txt`, không kèm FE manifest | `service-only` | Spring Boot, Go service, FastAPI |
| Marker hệ Apple (`Package.swift` / `Podfile` / `*.podspec` / `Project.swift` / `Cartfile` / `*.xcworkspace` / `*.xcodeproj`) | `fullstack` | App iOS, SDK iOS, app macOS |
| Cả FE + BE manifest cùng repo | `fullstack` | Monorepo Next.js + Express, Nx workspace |
| Không match rule nào | `unknown` (user sửa thủ công) | Manifest custom |

Repo hệ Apple xếp `fullstack` chứ không `service-only` là có chủ ý: repo client cần giữ pipeline build và ký app trong chính repo đó, mà `service-only` lại chặn các đường dẫn CI ở Rule 8.

Duyệt: `Y` (accept tất cả) / `n` (abort) / `edit` (sửa từng repo, cú pháp `<số> <scope>`, `done` để xong). `AUTO_CONFIRM=1` cho CI. Repo đã có scope block thì giữ nguyên; muốn re-detect thì xoá marker block rồi chạy `--upgrade`.

Marker block bootstrap ghi vào code repo `CLAUDE.md`:

```markdown
<!-- >>> NTAPP repo scope (auto-managed, do not edit) >>>
## Repo scope
`repo_type`: service-only
[mô tả + danh sách forbidden paths]
<!-- <<< NTAPP repo scope <<< -->
```

Đổi scope sau commit: edit `CLAUDE.md` sửa `repo_type` rồi commit (hook commit sau áp dụng scope mới), hoặc chạy `./scripts/bootstrap.sh --upgrade`.

### 7.6 Multi-DS — nhiều FE repo, nhiều design system

Project có ≥2 FE repo (vd web admin React + mobile React Native) → mỗi FE repo có **một Master DS riêng** (1 DS = 1 design language + 1 stack). Mô hình:

- **`design-system/registry.yaml`** (commit ở spec repo) = SSoT danh sách DS: mỗi entry `{ds_id}` khai `root` (thư mục con trong `design-system/`; `"."` cho DS đầu tiên giữ layout flat cũ — zero-migration), `code_repo`, `framework`, + hint resolve `id_prefixes`/`modules`. Schema đầy đủ: `design-system/_shared/ds-registry-schema.md`.
- **KHÔNG có `registry.yaml` = legacy single-DS** — mọi hành vi y hệt trước, project 1 FE repo không phải làm gì.
- **Binding phía code repo:** `.bmm-config.yaml` mỗi code repo có `bmad.design_system_root` trỏ **thẳng DS root của repo đó** (`bootstrap.sh` tự sinh khi detect ≥2 FE repo). Skill chạy từ code repo (`/ntapp-ds-bootstrap`, `/ntapp-ds-build-component`) nhờ vậy tự trúng DS đúng.
- **Binding phía spec repo (per unit):** skill Stage 3b/4a/4b resolve DS root cho từng `SCR-*`/`WGT-*` theo thủ tục chuẩn `design-system/_shared/ds-resolution.md`: **thẻ `- repo: <code-repo-folder>` ở Cluster Header WBS** (primary — bắt buộc cho mọi cluster `frontend-app` khi ≥2 FE repo, audit tại Stage 2 step-04.1b) → `id_prefixes` → `modules` → `default_ds` → hỏi người. Khai thẻ `repo` khi lập WBS (coverage_matrix mục 0) + đặt WBS ID có prefix phân biệt app (vd `SCR-ADM-*` / `SCR-APP-*`) để resolve tự động.
- **`_shared/` luôn ở family root** (schema/rubric framework-level dùng chung); mỗi `{ds_id}/` chứa trọn bộ artifact DS đó (token/metadata/stack-profile/catalog/_reference/library_apis/feature_deltas/archive).
- **Figma ingest cũng per-DS:** `_reference/figma/` (gồm `figma-manifest.yaml`) nằm **trong DS root của unit**, không ở family root. Một Figma file phủ nhiều FE repo là hợp lệ → ingest sinh **N manifest**, mỗi manifest chỉ chứa unit của DS mình và chỉ snap giá trị theo `master_token.json` của DS đó. Snap chéo sang DS khác sẽ ra token sai và cảnh báo `STYLE_FRAGMENTATION` giả. Mode `--tokens-only` chưa có unit để suy ra DS → phải truyền `--ds <ds_id>`.
- **Chạy `/ntapp-ds-bootstrap` cho FE repo thứ 2:** skill phát hiện DS hiện có thuộc repo khác → HITL 3 nhánh (tạo DS mới — khuyến nghị / đè / abort), sinh registry, KHÔNG bao giờ overwrite im lặng.
- **Hooks + pre-commit** tự quét cả 2 layout (flat legacy + namespaced); gate "DS đã bootstrap" là per-repo — repo B chưa bootstrap không ăn theo repo A.
- **WBS ID phải global-unique toàn project** (2 app cùng có màn login → `SCR-ADM-LOGIN` / `SCR-APP-LOGIN`) — registry không cứu được ID trùng.

---

## 8. Khi nào hết Phase 1

Phase 1 đủ cho 1-3 module pilot. Đạt 1 trong các ngưỡng sau → đề xuất Tech Lead + SA review chuyển Phase 1.5:

- ≥ 15 feature, hoặc
- ≥ 5 module, hoặc
- Không ai grep nổi cross-feature ripple, hoặc
- Drift giữa DD và code phát hiện muộn (> 1 tháng sau merge), hoặc
- Compliance audit phải dò git log thủ công > 1 ngày.

Phase 1.5 thêm các MCP service headless (Knowledge Graph, Drift Detector, Pre-commit Validator nâng cao). IDE + Markdown vẫn là interface chính, không rebuild.
