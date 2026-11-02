# NTAPP (VSAF Blended) — Điểm vào & điều hướng

**NTAPP agentic-engineering workflow** — quy trình 5 stage, enforce bằng chuỗi 39 skill đã được chuẩn hoá + 9 workflow tự động + 16 event hook + 9 rule pre-commit.

**39 skill lõi** thực sự nằm trên đường chạy chuẩn. Template chứa 136 skill, nhưng phần còn lại là tiện ích rời (Confluence, Jira, research, keycloak, DDD) hoặc skill của pack khác (`sdlc-*`, `bmad-agent-*`) — **không** thuộc workflow:

| Nhóm | Đếm | Skill |
|---|---:|---|
| Pipeline Stage 0–4 | 12 | `ds-bootstrap` · `system-overview` · `architecture-design` · `slice-planning` · `figma-ingest` · `ux-sketch` · `ux-design` · `feature-triage` · `technical-design` · `feature-design` · `ui-generation` · `ds-build-component` |
| VSAF wrapper | 9 | `run` · `resume` · `reproduce-architecture` · `slice-loop` · `ad-hoc-per-unit` · `path-b-quick-dev` · `express-hotfix` · `fix-bug` · `staging-deploy` |
| QA chain Stage 5 | 5 | `qa-audit` · `qa-gap-resolver` · `qa-generate-testcase` · `qa-robot` · `qa-setup-data` |
| Bug lane | 3 | `log-bug` · `fix-bug` · `bug-fix-engine` (engine dùng chung, không gõ trực tiếp) |
| Ops | 2 | `okf-refresh` · `sync-skills-global` |
| **BMAD gọi làm node** | 8 | `create-prd` · `create-epics-and-stories` · `create-story` · `dev-story` · `quick-dev` · `code-review` · `testarch-framework` · `testarch-atdd` |

Gọi thêm khi cần (không phải node cố định): BMAD `testarch-test-design` / `testarch-trace` / `testarch-nfr` (snapshot per release) · Superpowers `systematic-debugging` (root-cause trong bug lane).

## File này chứa gì — và KHÔNG chứa gì

Chứa 6 thứ không nằm trong [CLAUDE.md](CLAUDE.md): **định vị repo** · **cài đặt** · **mở IDE đúng cách** · **tên file canonical để tra cứu** · **hai lớp hook** · **giới hạn OS**.

**KHÔNG nhắc lại** (đọc thẳng ở nguồn, đừng suy đoán từ file này):

| Cần | Nguồn duy nhất |
|---|---|
| Happy path 2 track · bảng 9 workflow · lane dispatch · bug lane · resume · QA chain | [CLAUDE.md](CLAUDE.md) §VSAF Workflows · §QA skills |
| 9 rule pre-commit · header `id:` + `dd_version:` · gotcha `ui_file_pattern` (Angular) · bypass | [CLAUDE.md](CLAUDE.md) §Workflow guardrails |
| Thứ tự SSoT khi lệch · reuse-first UI · dual-repo Stage 5 · portability · lavish · OKF · `FIGMA_TOKEN` | [CLAUDE.md](CLAUDE.md) §Process shape · §Nơi ghi artifact · §Portability |
| Thủ tục chi tiết một stage | `SKILL.md` của skill tương ứng trong `.agent/skills/` |

**Luật lệch nhau:** skill thắng README; CLAUDE.md thắng README. File này chỉ mô tả *nơi chốn* và *cách cài*, không định nghĩa luật quy trình.

---

## 1. Định vị: đang ở repo nào

Sai bước này là ghi artifact lạc chỗ. **Kiểm tra marker trước khi ghi bất cứ gì.**

| Marker ở root | Loại repo | Được ghi gì |
|---|---|---|
| `NTAPP-output/` + `.vsaf/workflows/NTAPP/` + `_bmad/` | **Spec repo** — SSoT quy trình | Toàn bộ artifact `NTAPP-output/`. KHÔNG ghi code sản phẩm |
| `package.json` / `pom.xml` / ... + `.bmm-config.yaml` (gitignored) | **Code repo** (FE/BE) | Code + test code + `NTAPP-output/test-artifacts/` (live artifact). KHÔNG ghi spec |
| `README.spec-template.md` tồn tại | **Base template** — nguồn skill/rule | Chỉ sửa khi phát triển framework. KHÔNG chạy workflow dự án ở đây |

Workspace chuẩn — spec repo nằm **cạnh** code repo, cùng thư mục cha:

```
<project>/
├── <project>-spec/       ← spec repo (artifact + config + hook + scripts/)
├── <project>-frontend/   ← code repo FE
└── <project>-backend/    ← code repo BE
```

**Output root hợp lệ duy nhất: `NTAPP-output/`.**

---

## 2. Cài đặt

Cài lần đầu đi qua package `vsaf` — không cần clone base template.

**Project lead — khởi tạo dự án mới:**

```bash
npm install -g @ngocsangairvds/vsaf      # cài engine + CLI
vsaf sync NTAPP                          # đồng bộ skill NTAPP ra global (~/.claude) — dùng chung mọi project
vsaf install NTAPP --new <project>       # khởi tạo spec repo
```

> Tên có khoảng trắng → đặt trong ngoặc kép: `vsaf install NTAPP --new "my project"`.

**Team member — join dự án đã có:**

```bash
npm install -g @ngocsangairvds/vsaf
vsaf sync NTAPP
git clone <url-project-repo> && cd <project>-spec
vsaf install NTAPP --refresh             # dựng lại artifact machine-local (symlink, hook, IDE cache)
vsaf init --pack NTAPP                   # nạp pack NTAPP vào workspace
```

**Re-run:** `scripts/bootstrap.sh` vẫn giữ nguyên trong spec repo đích → dùng `vsaf` hay script đều được.

| Use case | PIC | `vsaf` | Script trong spec repo |
|---|---|---|---|
| Dev mới join / sau `git pull` | Mọi role | `vsaf install NTAPP --refresh` | `./scripts/bootstrap.sh --refresh` |
| Clone thêm code repo → multi-repo | Lead | — | `./scripts/bootstrap.sh --upgrade` |
| Preview, không apply | Bất kỳ | — | `./scripts/bootstrap.sh --dry-run` |
| Cập nhật skill/rule global | Mọi role | `vsaf sync NTAPP` | `/NTAPP-sync-skills-global` (trong chat) |
| Non-interactive (CI) | — | — | `PROJECT_NAME="app" AUTO_CONFIRM=1 ./scripts/bootstrap.sh` |

> **⚠️ Đừng dùng `--refresh` để upgrade single → multi-repo** — nó skip workspace + gitignore block, IDE không mở được multi-folder. Case này bắt buộc `--upgrade`.

**Skill 2 tầng:** base skill ở global `~/.claude/skills` (qua `vsaf sync NTAPP`, dùng chung mọi project) + skill **riêng project** ở `.agent/skills/` của spec repo (thêm xong chạy `--refresh` để IDE nhận). IDE thấy cộng dồn cả hai.

**Verify:** gõ `/` trong chat — phải thấy `/ntapp-`, `/bmad-`, `/superpowers:`. Không thấy → `vsaf sync NTAPP` chưa chạy.

---

## 3. Mở IDE: BẮT BUỘC mở file workspace, KHÔNG mở folder

`File → Open Folder` (hay `code <project>-spec/`) là **cách sai**, và nó fail im lặng — IDE vẫn mở, skill vẫn chạy, chỉ là chạy sai.

**Vì sao:** NTAPP là multi-repo — spec repo giữ artifact, code repo giữ code, hai bên nằm ở **hai folder khác nhau, ngang cấp**. Mở đúng một folder thì:

| Mở folder thường | Hệ quả |
|---|---|
| Chỉ thấy spec repo | Agent không đọc/ghi được code repo → `dev-story`, `ds-build-component`, `fix-bug` không có source để sửa |
| Chỉ thấy code repo | Agent không đọc được `project_wbs.md` / DD → tự suy contract. Hook pre-commit chặn lúc `git commit`, nhưng công đã làm sai rồi |
| Không load `files.exclude` / `search.exclude` của workspace | Search quét cả `node_modules` + `NTAPP-output/archive` → agent đọc snapshot `_v1` cũ và tưởng là bản latest |

### File workspace nằm ở đâu

Bootstrap sinh file tên `<project>.code-workspace` (tên project, không phải tên template):

| Trường hợp | Vị trí |
|---|---|
| **Mặc định** | **Root của spec repo** → `<project>-spec/<project>.code-workspace` |
| Workspace có meta repo | `<meta-repo>/workspaces/<project>.code-workspace` |
| Chưa clone code repo nào (greenfield thuần) | **Chưa sinh** — clone code repo rồi `./scripts/bootstrap.sh --upgrade` |

Không thấy file → `ls *.code-workspace` trong spec repo. Vẫn trống thường là vì bootstrap chỉ chạy ở mode `--refresh` (mode này **không** sinh workspace) → chạy lại full hoặc `--upgrade`.

### Cách mở

```bash
cd <project>-spec
code       <project>.code-workspace      # VS Code
cursor     <project>.code-workspace      # Cursor
antigravity <project>.code-workspace     # Antigravity
```

GUI: `File → Open Workspace from File…` → chọn `.code-workspace`. **Không** dùng `Open Folder`.

**Kiểm tra đã mở đúng:** sidebar hiện **nhiều folder root** (vd `spec-repo`, `code-repo-fe`, `code-repo-be`) — không phải một cây duy nhất; title bar hiện tên workspace.

> **WSL2:** mở từ Ubuntu terminal (`code <project>.code-workspace`) để IDE attach vào WSL. Mở từ Windows rồi trỏ vào `/mnt/...` là quay lại đúng vấn đề I/O chậm + symlink fail ở §6.
>
> Path trong workspace file phải **tương đối** — absolute `/Users/...` làm file mất portability giữa máy, và file này là **committed**.

---

## 4. Tra cứu: cần biết gì → mở file nào

Path tương đối từ `NTAPP-output/` trong **spec repo**. (Cấp thư mục + vai trò từng stage: [CLAUDE.md](CLAUDE.md) §Output structure — dưới đây là **tên file canonical**.)

| Cần biết | File |
|---|---|
| Unit ID có tồn tại? Thuộc module nào? | `Stage_2_Architecture/project_wbs.md` ← **SSoT inventory** |
| Kiến trúc tổng thể, actor, sequence | `Stage_2_Architecture/architecture_design.md` (HLD) |
| Contract giữa module / hệ thống | `Stage_2_Architecture/00_system_connectivity_integration.md` (Module 0) |
| Slice nào chứa unit này? | `Stage_2_Architecture/slices/SLICE-*.md` |
| Yêu cầu nghiệp vụ, epic | `Stage_1_Discovery/prd.md` · `epics.md` |
| Hiện trạng hệ thống (brownfield) | `Stage_1_Discovery/system_overview/_overview.md` |
| Bug đang mở | `Stage_1_Discovery/Bugs_Issues/BUGS-*.md` |
| Tech spec module | `Stage_3_Specs/techspec/{MODULE}_techspec.md` |
| Journey + convention UX | `Stage_3_Specs/ux/ux_design.md` · `ux_conventions.md` |
| **Contract chi tiết 1 unit** | `Stage_4_Design/detailed_design/{id}_detailed_design.md` (DD) |
| Semantic schema UI unit | `Stage_4_Design/ui_schema/ui_schema_{id}.json` |
| Token / component có sẵn | `design-system/` (multi-FE-repo → `registry.yaml` + `{ds_id}/`) |
| Slice trước học được gì | `ledgers/slice-ledger.md` · `ledgers/knowledge/` |

---

## 5. Hai lớp hook — đừng nhầm

| Lớp | Cơ chế | Khi nào chạy | Tắt khẩn cấp |
|---|---|---|---|
| **Git pre-commit** | `.git/hooks/pre-commit` | lúc `git commit` | `SKIP_PRECOMMIT=1` |
| **Event hook (Claude Code)** | block `hooks` trong `.claude/settings.json` + `.claude/hooks/` (16 hook) | real-time theo event (UserPromptSubmit / PostToolUse / SubagentStop) | `DISABLE_HOOK_<TÊN>=1` · `DISABLE_HOOKS_ALL=1` |

Nội dung 9 rule pre-commit + điều kiện skip: [CLAUDE.md](CLAUDE.md) §Workflow guardrails. Behavior từng event hook: [hooks/README.md](hooks/README.md).

> ⚠️ Hook **KHÔNG merge** giữa `settings.json` ↔ `settings.local.json` — local *thay thế hoàn toàn* project. Block `hooks` PHẢI ở `settings.json` committed. Đặt vào `settings.local.json` là xoá sạch hook.
>
> ⚠️ `SubagentStop` chỉ fire cho Task-subagent. Skill `/ntapp-*` chạy ở main loop thì 7 hook SubagentStop có thể không kích hoạt → smoke-test lúc rollout, fallback đổi sang event `Stop` trong manifest.

Hook skip 4 path để tránh false-positive Rule 1: `.agent/skills/` · `.claude/skills/` · `.cursor/skills/` · `_bmad/`. Thêm skill third-party path khác → update `EXCLUDED_PATHS` trong `scripts/templates/pre-commit.template.sh`.

---

## 6. Môi trường — biết trước khi chạy

**Không OS nào chạy trọn vẹn framework này.** Phần lớn bash-only, một góc nhỏ PowerShell-only.

| Thành phần | Đếm | Chạy ở đâu |
|---|---:|---|
| `hooks/*.sh` — barie gate | 15 | macOS / Linux |
| Toàn bộ `.sh` (hook + `scripts/` + script kèm skill) | 31 | macOS / Linux |
| `hooks/*.py` + `scripts/okf_project.py` | — | **mọi OS** (Python stdlib, 0 symlink) |
| `.ps1` của 2 skill Confluence | 4 | **chỉ Windows** (không có bản `.sh`) |

- **macOS / Linux là môi trường native** — chạy thẳng `.sh`, không cần prefix. macOS cần `python3` (`xcode-select --install`) cho bước merge `hooks` vào `settings.json`; bash 3.2 mặc định vẫn chạy.
- **Windows chưa hỗ trợ, và thất bại của nó là thất bại IM LẶNG.** `bootstrap.sh` trên Windows cho ra cài đặt *trông như đã xong*: `ln -sf` cần Developer Mode, `git clone` với `core.symlinks=false` biến symlink thành file text chứa đường dẫn → `.claude/hooks` và `.agent/skills` thành file rác, **15 barie hook không bao giờ chạy**, không một dòng cảnh báo. → Dùng **WSL2** (clone vào `/home/<user>/`, **không** `/mnt/c/`), hoặc Git Bash + `core.symlinks=true` + Developer Mode.
- **Lịch chạy OKF** do dự án tự cắm: CI `schedule:` · `launchd` · `cron` · `schtasks` (Windows không có cron).

---

## 7. Đọc thêm

| Cần | File |
|---|---|
| **Luật quy trình, workflow, guardrail — nguồn chính** | [CLAUDE.md](CLAUDE.md) |
| Set up + vai trò/quyền approve + bảng slash command + skill xung đột | [docs/Process/Manual_phase_1.md](docs/Process/Manual_phase_1.md) |
| Workflow brownfield / greenfield chi tiết | `docs/Process/Manual_phase_1_brownfield.md` · `_greenfield.md` |
| Quy ước `okf.families`, đánh số ADR & slice | [docs/Process/OKF_conventions.md](docs/Process/OKF_conventions.md) |
| Behavior từng event hook | [hooks/README.md](hooks/README.md) |
| Rule code FE (Angular) / BE (tài chính số) + Sonar | `rules/` (sync ra `~/.claude/rules/`) |
