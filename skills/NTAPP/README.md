# NTApp Project Template

Base template dùng chung để bootstrap nhiều project theo workflow NTAPP Phase 1 — Agentic Engineering 2026.

## Base template này là gì

Repo này (`ntapp-vsaf-blended-template/`) là **base dùng chung cho nhiều project** — nguồn source-of-truth cho skill + rule. **Giữ nguyên `.git`** để `git pull` cập nhật skill/rule mới về sau.

- **Skill + rule** cài về **global** `~/.claude/` (dùng cho mọi project trên máy) qua `scripts/sync-skills-to-user.sh`.
- **Project thật** sống ở một **spec repo riêng**, tạo bằng cách copy base (trừ `.git` và `.agent/skills` — ngoại lệ giữ lại đúng skill `NTAPP-sync-skills-global`). Spec repo hầu như không chứa skill — IDE đọc skill từ global; riêng skill này ở lại để tự đồng bộ global mà không cần clone base template.

Cấu trúc thư mục: base **song song** với thư mục cha của từng project (base KHÔNG nằm trong project):

```
<root>/
├── ntapp-vsaf-blended-template/   ← base dùng chung (giữ .git, pull update)
└── <your-project-name>/           ← thư mục cha 1 project (song song base)
    ├── <your-project-name>-spec/       ← spec repo (copy từ base, có git riêng)
    ├── <your-project-name>-frontend/   ← code repo FE (clone vào đây)
    └── <your-project-name>-backend/    ← code repo BE (clone vào đây)
```

## Khi nào dùng

Adopt base template này khi:
- Bắt đầu project mới muốn áp dụng workflow 5-stage (Discovery → Architecture → Specs → Design → Build & Verify)
- Cần skill library NTAPP + BMAD + Superpowers đã setup sẵn
- Cần cấu trúc `NTAPP-output/` chuẩn để output skill ghi đúng chỗ

> **Windows:** script viết bằng bash + Unix tools. Chạy qua WSL2 (khuyến nghị) hoặc Git Bash — xem mục [Windows users](#windows-users) bên dưới.

## Yêu cầu môi trường

Nói thẳng trước khi bạn cài: **hôm nay không OS nào chạy được trọn vẹn framework này.** Phần lớn là bash-only, một góc nhỏ là PowerShell-only.

| Thành phần | Đếm | Chạy ở đâu |
|---|---:|---|
| `hooks/*.sh` — barie gate (approval, verification, stage, triage, DS) | **15** | macOS / Linux |
| Toàn bộ `.sh` của repo (hook + `hooks/lib` + `scripts/` + script kèm skill) | **31** | macOS / Linux |
| `hooks/*.py` (`drift_detector.py`, `slice_coverage_dag_validate.py`) | 2 | mọi OS |
| `scripts/bootstrap.sh` | **2.156 dòng bash**, dùng `ln -sf` ở 4 chỗ | macOS / Linux |
| `.ps1` của 2 skill Confluence (`NTAPP-srs-to-confluence`, `NTAPP-business-overview-confluence`) | **4** (không có bản `.sh`) | **chỉ Windows** |
| Lớp OKF — `scripts/okf_project.py` + `/NTAPP-okf-refresh` | — | **mọi OS** |

- **macOS / Linux — bắt buộc** cho bootstrap, hook và mọi script kèm skill. Đây là môi trường native; xem [macOS / Linux users](#macos--linux-users).
- **Windows — chưa hỗ trợ** cho phần trên, và **thất bại của nó là thất bại im lặng**. Chạy `bootstrap.sh` hôm nay trên Windows cho ra một cài đặt **trông như đã xong**: `ln -sf` cần Developer Mode hoặc quyền admin, còn `git clone` với `core.symlinks=false` biến symlink thành **file text chứa đường dẫn** — nên `.claude/hooks` và `.agent/skills` thành file rác, **15 barie hook không bao giờ chạy**, và không một dòng cảnh báo nào được in ra. Dùng WSL2 (khuyến nghị) hoặc Git Bash + `core.symlinks=true` — xem [Windows users](#windows-users).
- **Lớp OKF là ngoại lệ, và là ngoại lệ có chủ đích.** `okf_project.py` thuần Python stdlib: 0 script shell, 0 symlink, 0 giả định về cron → chạy được mọi OS. Skill `/NTAPP-okf-refresh` dò interpreter theo thứ tự `py -3` → `python3` → `python` vì **Windows không có `python3` trên PATH**. Lịch chạy do dự án tự cắm: CI `schedule:`, `launchd` (macOS), `cron` (Linux), `schtasks /create /sc DAILY` (Windows — **không có cron**). Quy ước khai `okf.families` / đánh số ADR & slice: [docs/Process/OKF_conventions.md](docs/Process/OKF_conventions.md).
- **Hai skill Confluence đi ngược chiều:** chúng là `.ps1` và **chỉ chạy trên Windows**. Không có bản `.sh` tương đương.

> Con số ở trên đếm trên cây nguồn (`git ls-files`), không tính `node_modules/`, các git worktree tạm trong `.vsaf/worktrees/`, và bản sao IDE cache `.claude/skills/` · `.cursor/skills/` (do `reload_ide_skills` sinh, đã gitignore).

## Setup dự án mới

Hướng dẫn dưới đây dùng **Windows CMD** làm chính. Lưu ý: bước copy (Bước 2) là lệnh CMD-native, nhưng **`sync-skills-to-user.sh` và `bootstrap.sh` là script bash** → trong CMD phải gọi qua `bash <script>` (Git for Windows có sẵn `bash.exe`). Nếu mở thẳng **Git Bash / WSL** thì chạy `.sh` trực tiếp không cần prefix — xem biến thể bash ở mỗi bước + mục [Windows users](#windows-users).

Chạy 3 bước dưới đây **từ trong base template**. Xong bước 3, chuyển sang `README.md` của spec repo để clone code repo + chạy bootstrap.

### Bước 1 — Clone base template (giữ `.git`)

```cmd
git clone <template-url> ntapp-vsaf-blended-template
cd ntapp-vsaf-blended-template
```

> Đã clone base trước đó rồi thì bỏ qua — dùng chung base cho nhiều project. Chỉ cần `git pull` cho mới.

### Bước 2 — Tạo spec repo cho project (copy trừ `.git`; giữ lại 1 skill bootstrap trong `.agent/skills`)

Loại skill base khỏi bản copy (đã ở global), **nhưng giữ lại đúng skill `NTAPP-sync-skills-global`** trong `.agent/skills/` — dùng để tự đồng bộ skill/rule global về sau mà không cần clone base template (xem README của spec repo, mục Verify skill). Thư mục `.agent/skills/` vẫn là chỗ thêm skill **riêng project** khác về sau — xem [Skill distribution](#skill-distribution-base-global--skill-riêng-project).

**CMD** (thay `my-project` bằng tên project của bạn — không dùng dấu `< >` trong `set`):

```cmd
set PROJECT=my-project

robocopy "." "..\%PROJECT%\%PROJECT%-spec" /E /XD ".git" "%CD%\.agent\skills"

rem giữ lại đúng skill NTAPP-sync-skills-global để bootstrap đồng bộ skill/rule global (không cần clone base template)
robocopy ".agent\skills\NTAPP-sync-skills-global" "..\%PROJECT%\%PROJECT%-spec\.agent\skills\NTAPP-sync-skills-global" /E

move /Y "..\%PROJECT%\%PROJECT%-spec\README.spec-template.md" "..\%PROJECT%\%PROJECT%-spec\README.md"

pushd "..\%PROJECT%\%PROJECT%-spec"
git init && git add -A && git commit -m "chore: bootstrap spec from NTAPP template"
popd
```

- `/E` copy cả thư mục con (kể cả rỗng); `/XD` loại `.git` và toàn bộ `.agent\skills` (base skill đã ở global, không cần copy). Dòng `robocopy` thứ 2 copy lại riêng skill `NTAPP-sync-skills-global` vào đúng chỗ.
- ⚠️ `robocopy` báo **exit code 1 khi copy thành công** (không phải lỗi) — cứ chạy tiếp.

<details><summary><b>Biến thể bash</b> (Git Bash / WSL / macOS / Linux)</summary>

```bash
PROJECT=<your-project-name>
mkdir -p "../$PROJECT"
# rsync nếu có; không thì dùng cp -R rồi xoá 2 thư mục loại trừ
rsync -a --exclude='.git' --exclude='.agent/skills' ./ "../$PROJECT/$PROJECT-spec/" \
  || { mkdir -p "../$PROJECT/$PROJECT-spec"; cp -R ./. "../$PROJECT/$PROJECT-spec/"; \
       rm -rf "../$PROJECT/$PROJECT-spec/.git" "../$PROJECT/$PROJECT-spec/.agent/skills"; }
# giữ lại đúng skill NTAPP-sync-skills-global để bootstrap đồng bộ skill/rule global (không cần clone base template)
mkdir -p "../$PROJECT/$PROJECT-spec/.agent/skills"
cp -R .agent/skills/NTAPP-sync-skills-global "../$PROJECT/$PROJECT-spec/.agent/skills/"
( cd "../$PROJECT/$PROJECT-spec" \
  && mv -f README.spec-template.md README.md \
  && git init && git add -A && git commit -m "chore: bootstrap spec from NTAPP template" )
```
</details>

### Bước 3 — Đồng bộ skill + rule về global

**CMD** (gọi script bash qua `bash`):

```cmd
bash ./scripts/sync-skills-to-user.sh
```

> `'bash' is not recognized`? Dùng đường dẫn đầy đủ: `"C:\Program Files\Git\bin\bash.exe" ./scripts/sync-skills-to-user.sh`. Trong Git Bash / WSL thì chạy thẳng `./scripts/sync-skills-to-user.sh`.

Script copy toàn bộ skill trong `.agent/skills/` → `~/.claude/skills/` (Claude Code quét được cho mọi project) và copy rule stack (`rules/*.md`) → `~/.claude/rules/`. Sau đó IDE thấy `/ntapp-`, `/bmad-`, `/superpowers:` cho mọi project.

- Xem trước không ghi: thêm `--dry-run`
- Chỉ skill: `--skills-only` · chỉ rule: `--rules-only`
- Gỡ skill đã bỏ khỏi nguồn: `--clean`

→ **Xong phần base.** Tiếp tục setup project (clone BE/FE + bootstrap) theo `README.md` trong `<your-project-name>-spec/`.

## Cập nhật skill / rule mới

Khi base có skill/rule mới, cập nhật cho **mọi project** trên máy bằng cách pull base rồi re-sync:

```cmd
cd ntapp-vsaf-blended-template
git pull
bash ./scripts/sync-skills-to-user.sh
```

> `--clean` nếu muốn gỡ skill đã xoá khỏi base. Git Bash / WSL: chạy thẳng `./scripts/sync-skills-to-user.sh` không cần `bash`.

Không cần đụng vào từng spec repo — skill/rule sống ở global `~/.claude/`, sync một lần là áp cho tất cả. Spec repo cũ muốn nhận thay đổi về hook/script bootstrap thì merge tay từ base (spec repo có git riêng, không tự pull từ base).

### Re-run modes

Script chạy được nhiều lần, idempotent. Chọn mode theo use case:

| Use case | Lệnh | PIC | Bước thực hiện |
|---|---|---|---|
| Lần đầu setup | `./scripts/bootstrap.sh` | Project Lead | Full: project name + workspace + per-code-repo configs + symlink skills + gitignore + pre-commit hook + event hook (`.claude/hooks` + settings) |
| **Upgrade single → multi-repo** (clone thêm code repo vào folder cha) | `./scripts/bootstrap.sh --upgrade` | Project Lead | Skip project name (đã set), re-detect code repo, sinh workspace + configs + symlinks + gitignore + event hook. File cũ backup `.bak.<timestamp>` |
| Team member (PO/BA/DEV) join project đã setup | `./scripts/bootstrap.sh --refresh` | Tất cả role | Re-create machine-local symlinks (gồm `.claude/hooks`) + cài pre-commit hook + reload IDE skill cache. KHÔNG đụng workspace/configs đã commit (merge settings.json hooks block idempotent, no-diff) |
| Skill canonical update sau `git pull` | `./scripts/bootstrap.sh --refresh` | Tất cả role | Re-sync skill cache (`.claude/skills/`, `.cursor/skills/`) |
| Preview trước khi apply | `./scripts/bootstrap.sh --dry-run` | Bất kỳ | Show full plan, không tạo/sửa file nào |

**Mode comparison matrix:**

| Bước | full | `--upgrade` | `--refresh` |
|---|:---:|:---:|:---:|
| **PIC** | **Project Lead** | **Project Lead** | **Tất cả role (PO/BA/DEV)** |
| **VSAF engine pre-flight** (auto-install vsaf → sdlc scaffold → fanout patch)² | ✓ | ✓ | ✓ |
| Project name prompt | ✓ | ✗ | ✗ |
| Workspace file (committed) | ✓ | ✓ | ✗ |
| Spec repo `.gitignore` block (committed) | ✓ | ✓ | ✗ |
| Code repo `.gitignore` block (committed) | ✓ | ✓ | ✗ |
| **Code repo `.bmm-config.yaml`** (machine-local, gitignored) | ✓ | ✓ | ✓ |
| Skill symlinks (machine-local, gitignored) | ✓ | ✓ | ✓ |
| Pre-commit hook (machine-local, `.git/hooks/`) | ✓ | ✓ | ✓ |
| **Event hook symlink** `.claude/hooks` (machine-local, gitignored) | ✓ | ✓ | ✓ |
| **Event hook block** trong `.claude/settings.json` (committed) | ✓ | ✓ | ✓¹ |
| IDE skill cache `.claude/`, `.cursor/` (machine-local) | ✓ | ✓ | ✓ |

> ¹ `--refresh` cũng merge block `hooks` vào `settings.json` nhưng **idempotent** — nếu lead đã commit block thì re-run cho byte y hệt (no diff). Self-healing nếu thiếu.
>
> ² Chain chạy trong `check_prerequisites` (trước khi rẽ mode) nên áp dụng **cả 3 mode**, đều idempotent: vsaf đã có → skip install; file `.vsaf/docs/`/`CONTEXT.md` đã có → giữ nguyên (KHÔNG overwrite, `.gitignore` chỉ ADD entry thiếu); patch đã apply → guard nhận diện & bỏ qua. Thiếu npm → warn, không gate. `--dry-run` chỉ preview, không thực thi.

→ `--refresh` xử lý **tất cả artifact machine-local** (code repo configs + symlinks + hook + IDE cache). `full`/`--upgrade` thêm artifact committed (workspace + gitignore block).

> **Skill 2 tầng:** base skill ở global `~/.claude/skills` (cài qua `scripts/sync-skills-to-user.sh` từ base template, dùng chung mọi project); skill **riêng project** bỏ vào `.agent/skills` của spec repo (mặc định chỉ có sẵn skill bootstrap `NTAPP-sync-skills-global`). 2 dòng `Skill symlinks` + `IDE skill cache` trong bảng đồng bộ **skill riêng project** sang code repo + IDE — có skill (kể cả chỉ 1) là hoạt động. Base skill luôn sẵn qua global. Cập nhật base skill = `git pull` base + re-run sync (**KHÔNG** phải `--refresh`).

**⚠️ Đừng dùng `--refresh` để upgrade single → multi-repo.** Skip workspace + gitignore → IDE không mở được multi-folder, code repo mới chưa có gitignore guard. Dùng `--upgrade` cho case này.

**Full / upgrade / refresh mode re-run an toàn vì:**
- `setup_project_name` (full only): thấy CLAUDE.md không còn `<PROJECT_NAME>` placeholder → hỏi "Override?" default **n** → giữ nguyên
- `generate_workspace`, `install_hooks`, `setup_gitignore`: backup file cũ thành `.bak.<timestamp>` rồi sinh lại
- `generate_code_repo_configs` (all modes): file gitignored, mỗi máy generate riêng. Backup nếu file local đã tồn tại
- `link_skills`: relative path — survive git clone. Idempotent: check symlink target trùng thì skip. Auto-migrate legacy absolute symlink → relative
- `link_event_hooks`: symlink `.claude/hooks` relative (idempotent, fix nếu trỏ sai) + merge block `hooks` vào `settings.json` bằng python3 — giữ `enabledPlugins`/`permissions`, ghi đè trọn block `hooks` (re-run nhặt hook mới), byte y hệt nếu không đổi
- `setup_gitignore`: marker block (`# >>> NTAPP bootstrap >>>`) — strip + re-append, không duplicate entry

**Pre-commit hook scope:**

Hook chỉ check **project code** (files trong `src/`, `lib/`, `tests/`, ...). Skip 4 path third-party / IDE caches để tránh false positive Rule 1:

- `.agent/skills/` — skill canonical (NTAPP + BMAD + Superpowers)
- `.claude/skills/` — Claude Code IDE cache
- `.cursor/skills/` — Cursor IDE cache
- `_bmad/` — BMM core bundled config

Nếu thêm skill third-party khác (Cline, Aider...) ở path mới → update `EXCLUDED_PATHS` trong `scripts/templates/pre-commit.template.sh`.

### Non-interactive mode (CI / automation)

```bash
PROJECT_NAME="my-app" AUTO_CONFIRM=1 ./scripts/bootstrap.sh
```

### Pre-commit hook — 9 rules

Script cài hook check 8 trong 9 rules từ Manual mục 6 (Rule 5 semantic, skip):

| Rule | Check | Action |
|---|---|---|
| 1 | File code có header `feature_id` + `dd_version` | Block nếu thiếu |
| 2 | `feature_id` tồn tại trong `project_wbs.md` | Block; skip nếu WBS chưa có |
| 3 | `{feature_id}_detailed_design.md` tồn tại | Block; skip nếu Stage 4 chưa chạy |
| 4 | UI code (`.tsx/.jsx/.css/.scss/.html`) không hardcode `#hex`, `Npx`, `font-family: "name"` | Block |
| 5 | (skip) Component reuse check | — |
| 6 | UI file → `ui_schema_{feature_id}.json` tồn tại | Block; skip nếu chưa có UI schema dir |
| 7 | `proposed_ds_updates.md` có `[NEW]` → `build_report.md` phải tồn tại | Block; chạy `/ntapp-ds-build-component` |
| 8 | Repo `repo_type: service-only` trong CLAUDE.md → KHÔNG được commit infra paths (Dockerfile / CI / helm / k8s / terraform / ansible / devcontainer) | Block; chỉ áp dụng cho service-only repo, fullstack/unknown bypass. Test framework configs KHÔNG bị block (đó là test code, không phải infra) |
| 9 | UI files KHÔNG chứa unicode emoji (range U+2600-U+27BF + U+1F300-U+1FAFF) — wireframe emoji chỉ là visual hint, Stage 4b đã translate sang `icon_bindings` trong `ui_schema_{id}.json`, code phải import icon component từ `stack-profile.icon_library` | Block; bypass với pragma `// allow-emoji` (hoặc `# allow-emoji` / `<!-- allow-emoji -->`) trong 10 dòng đầu — legit case: chat content, emoji picker, emoji reaction component |

**Bypass khẩn cấp (hotfix only):**
```bash
SKIP_PRECOMMIT=1 git commit -m "hotfix: ..."
# Phải compensate đầy đủ header + WBS + DD trong 48h
```

**Repo scope (Rule 8):** Bootstrap script khi `--full` / `--upgrade` detect mỗi code repo thuộc `service-only` hay `fullstack` từ manifest, present 1 bảng cho project lead duyệt cả lô (Y/n/edit), rồi ghi marker block vào `CLAUDE.md` mỗi code repo. Rule 8 hook đọc block này để enforce. Chi tiết: [Manual_phase_1.md §7.5](docs/Process/Manual_phase_1.md#75-repo-scope-service-only-vs-fullstack).

### Event hooks (Claude Code) — khác pre-commit hook

Project có **2 lớp hook tách biệt**, đừng nhầm:

| Lớp | Cơ chế | Khi nào chạy | Cài bởi |
|---|---|---|---|
| **Git pre-commit** | `.git/hooks/pre-commit` | Lúc `git commit` | `install_hooks` |
| **Event hook (Claude Code)** | block `hooks` trong `.claude/settings.json` + `.claude/hooks/` | Real-time theo event (UserPromptSubmit / PostToolUse / SubagentStop) khi dùng Claude Code | `link_event_hooks` |

`link_event_hooks` per repo (spec + code):

1. **Symlink** `hooks/` → `.claude/hooks/` (relative, machine-local → gitignored).
2. **Merge** block `hooks` từ manifest `scripts/templates/claude-hooks.settings.json` vào `.claude/settings.json` (committed → cả team có khi clone). Giữ nguyên `enabledPlugins`/`permissions`.

16 event hook (manifest map sẵn event/matcher đã verify với Claude Code docs). Thêm/sửa hook = sửa manifest 1 lần rồi chạy lại bootstrap. Chi tiết từng hook + behavior: [hooks/README.md](hooks/README.md).

> ⚠️ **Hook KHÔNG merge giữa `settings.json` ↔ `settings.local.json`** — local *thay thế hoàn toàn* project. Block `hooks` PHẢI ở committed `settings.json`. **Đừng** đặt `hooks` vào `settings.local.json` kẻo xoá sạch. (Permissions thì merge — không sao.)
>
> ⚠️ **`SubagentStop` chỉ fire cho Task-subagent.** Nếu skill `/ntapp-*` chạy ở main loop, 7 hook SubagentStop có thể không kích hoạt → smoke-test thật lúc rollout; fallback đổi event sang `Stop` trong manifest. Self-test `self_test_event_hooks` đã nhắc điều này cuối mỗi run.
>
> 🔧 **Tắt khẩn cấp:** `DISABLE_HOOK_<TÊN>=1` (vd `DISABLE_HOOK_BUILD_LOOP=1`) tắt 1 hook; `DISABLE_HOOKS_ALL=1` tắt hết. (Khác `SKIP_PRECOMMIT=1` chỉ cho git pre-commit.)

### Skill distribution (base global + skill riêng project)

Hai tầng skill, cộng dồn trong IDE:

- **Base skill** (NTAPP + BMAD + Superpowers) → cài **global** `~/.claude/skills` qua `scripts/sync-skills-to-user.sh` chạy từ **base template**, dùng chung **mọi project** trên máy — xem [Setup dự án mới](#setup-dự-án-mới) bước 3 + [Cập nhật skill / rule mới](#cập-nhật-skill--rule-mới). Claude Code / Cursor quét global nên mở IDE là thấy `/ntapp-`, `/bmad-` ngay, **không phải gõ "duplicate skill X"**.
- **Skill riêng project** → bỏ vào `.agent/skills/` của **spec repo** (mặc định chỉ có sẵn skill bootstrap `NTAPP-sync-skills-global` — xem [Bước 2](#bước-2--tạo-spec-repo-cho-project-copy-trừ-git-giữ-lại-1-skill-bootstrap-trong-agentskills)). Skill khác thêm vào đây chỉ phục vụ project đó, commit cùng spec repo. Thêm xong chạy `bash ./scripts/bootstrap.sh --refresh` (từ spec repo) để symlink sang code repo + pre-populate IDE cache. IDE thấy **cả** base skill (global) lẫn skill riêng project.

Cập nhật **base skill** làm ở base template, không phải spec repo:

```cmd
cd ntapp-vsaf-blended-template
git pull
bash ./scripts/sync-skills-to-user.sh
```

### macOS / Linux users

Không cần WSL, Git Bash hay bật Developer Mode — macOS/Linux **là môi trường native** của các script này. Bỏ qua toàn bộ mục "Windows users" bên dưới.

Khác biệt duy nhất so với hướng dẫn CMD ở [Setup dự án mới](#setup-dự-án-mới): dùng **biến thể bash** ở mỗi bước và **chạy thẳng `.sh`** (không cần prefix `bash`).

```bash
# Bước 2 — tạo spec repo: dùng khối "Biến thể bash" (rsync / cp -R)
# Bước 3 — sync skill + rule
./scripts/sync-skills-to-user.sh

# Bootstrap (chạy từ spec repo)
./scripts/bootstrap.sh
```

Script đã portable sẵn cho BSD tools của macOS: `sed` in-place tự phân nhánh `darwin*`, `readlink -f` có fallback `realpath`, pre-commit dùng `python` thay `grep -P`. `rsync` + symlink hoạt động native.

**Lưu ý trước khi chạy:**

| Vấn đề | Ghi chú |
|---|---|
| `python3` không có sẵn (macOS) | Cài Xcode Command Line Tools: `xcode-select --install`. Cần cho bước merge `hooks` vào `settings.json`; thiếu thì một số fallback dùng path hardcode, kém đầy đủ hơn. |
| `bash` mặc định macOS là 3.2 (cũ) | Script không dùng syntax bash 4+ (`declare -A`, `mapfile`) nên vẫn chạy; nếu muốn bản mới: `brew install bash`. |
| Symlink | Native, không cần thao tác đặc biệt như Git Bash trên Windows. |
| `git` | macOS có sẵn qua Xcode CLT; Linux cài qua package manager (`apt install git`, ...). |

### Windows users

Bootstrap script viết bằng bash + Unix tools (`rsync`, `sed`, `python3`). Windows native cmd/PowerShell **không chạy được trực tiếp**. Có 2 cách:

#### Cách 1 — WSL2 (khuyến nghị mạnh)

WSL2 (Windows Subsystem for Linux) chạy Ubuntu thật bên trong Windows. Bootstrap script chạy 100% như trên Linux — không phải workaround gì cả.

**Setup WSL2 lần đầu (~10 phút):**

1. Mở PowerShell as Administrator, gõ:
   ```powershell
   wsl --install
   ```
   Lệnh này tự cài WSL2 + Ubuntu mặc định. Restart máy khi được hỏi.

2. Sau restart, mở "Ubuntu" từ Start Menu. Đặt username + password lần đầu.

3. Trong Ubuntu terminal, cài git nếu chưa có:
   ```bash
   sudo apt update && sudo apt install -y git
   ```

4. Clone base + setup vào **WSL filesystem** (KHÔNG phải Windows filesystem):
   ```bash
   cd ~                                      # → /home/<user>/, đây là WSL filesystem
   git clone <template-url> ntapp-vsaf-blended-template
   cd ntapp-vsaf-blended-template
   # → làm theo "Setup dự án mới" (tạo spec repo + sync-skills), rồi
   #   chạy bootstrap từ spec repo theo README của spec repo.
   ```

   ⚠️ **Quan trọng:** Đừng clone vào `/mnt/c/Users/...` (Windows filesystem mount trong WSL). Tốc độ I/O cross-filesystem chậm 5-10 lần, symlink có thể fail. Luôn dùng `/home/<user>/`.

**Mở IDE từ WSL:**

- **VS Code / Cursor:** Cài extension "Remote - WSL" trên Windows. Mở Ubuntu terminal, gõ:
  ```bash
  code .
  ```
  IDE tự mở và connect vào WSL. Mọi feature (extension, terminal, debug) hoạt động native trong WSL.

- **Antigravity:** Tương tự, install extension WSL Remote rồi `antigravity .` trong WSL terminal.

**Pros:** UX y hệt Linux, mọi feature script chạy 100% (symlink thật, python3 sẵn có, rsync native).

**Cons:** Cài WSL 1 lần ~10 phút, repo phải ở trong WSL filesystem (không share trực tiếp với Windows apps).

#### Cách 2 — Git Bash (fallback)

Git for Windows installer đi kèm Git Bash — bash shell emulator chạy native trên Windows, không cần WSL. Phù hợp khi:
- IT policy không cho cài WSL (cần Hyper-V/virtualization)
- Máy cấu hình thấp không chạy WSL2 mượt
- Cần share folder repo với Windows-native apps (vd Figma desktop sync vào folder)

**Setup Git Bash:**

1. Cài Git for Windows từ [git-scm.com/download/win](https://git-scm.com/download/win). Trong installer:
   - Chọn "Use Git from Git Bash only" (hoặc "Git from the command line and 3rd-party software")
   - Bật **"Enable symbolic links"** (mặc định OFF) — critical cho skill symlink
   - Các option khác để mặc định

2. Sau cài, mở Git Bash (Start Menu → Git Bash).

3. Trước khi clone repo, **enable symlink ở global git config:**
   ```bash
   git config --global core.symlinks true
   ```

4. Clone base vào folder Windows bình thường:
   ```bash
   cd /c/Users/<user>/Documents          # path Windows trong Git Bash style
   git clone -c core.symlinks=true <template-url> ntapp-vsaf-blended-template
   cd ntapp-vsaf-blended-template
   # → làm theo "Setup dự án mới" (tạo spec repo + sync-skills), rồi
   #   chạy bootstrap từ spec repo theo README của spec repo.
   ```

**Limitations + workaround:**

| Vấn đề | Tại sao | Workaround |
|---|---|---|
| **Symlink fail nếu chưa enable** | Windows mặc định cấm tạo symlink (cần admin hoặc Developer Mode) | Enable Developer Mode trong Windows Settings → Update & Security → For developers. Hoặc chạy Git Bash as Administrator. |
| **`python3` không có sẵn** | Git Bash không bundle Python | (a) Cài Python for Windows từ python.org + add to PATH. (b) Để script fallback dùng path hardcode `../../<name>` — vẫn work cho folder structure chuẩn |
| **`rsync` không có sẵn** | Git Bash không bundle rsync | Script fallback dùng `cp -R`. Output identical cho lần đầu, chỉ chậm hơn khi `--refresh` (full copy thay vì incremental sync) |
| **Path absolute Windows** | `C:\Users\...` không hợp lệ trong bash | Dùng `/c/Users/...` thay thế (Git Bash MSYS style) |
| **Line endings CRLF** | Windows mặc định CRLF, bash expect LF | `git config --global core.autocrlf input` trước khi clone |

**Tóm tắt Git Bash status:**

| Feature | Hoạt động | Note |
|---|:---:|---|
| Auto-detect repos | ✅ | |
| Replace `<PROJECT_NAME>` | ✅ | |
| Generate workspace JSON | ✅ | Path tương đối có thể không tối ưu |
| Generate code repo configs | ✅ | |
| Symlink skills cross-repo | ⚠️ | Cần enable Developer Mode + `core.symlinks=true` |
| Skill cache `.claude/.cursor/` | ✅ | |
| Pre-commit hook | ✅ | |
| Event hook symlink `.claude/hooks` | ⚠️ | Cần symlink (như skills); nếu không, copy `hooks/` → `.claude/hooks/` thủ công |
| Event hook `settings.json` merge | ✅ | python3 merge — cần Python trên PATH |
| Hook e2e self-test (pre-commit + event) | ✅ | |
| `--dry-run` / `--refresh` | ✅ | |

**Pros:** Không cần WSL, dùng Git Bash dev đã quen.
**Cons:** Cần setup vài config Windows, symlink fragile, một số fallback kém polish.

#### Quy ước recommend

| Tình huống | Cách |
|---|---|
| Máy mới, không có ràng buộc | **WSL2** |
| Đã quen Git Bash, không muốn cài WSL | **Git Bash** + setup checklist trên |
| CI/CD chạy trên GitHub Actions `windows-latest` | **WSL** không pre-installed → dùng `ubuntu-latest` runner thay vì port script |
| Enterprise IT khóa virtualization | **Git Bash** (WSL cần Hyper-V) |

### Auto-detected stacks

Script đọc manifest file để detect:

| Manifest | Lang | Framework detect |
|---|---|---|
| `package.json` | typescript | angular (`@angular/core`), react (`react`), vue (`vue`), browser-lib (có bundler + dùng `window`/`document`), node (có server framework), else TODO |
| `pom.xml` | java | spring-boot (nếu có `spring-boot`), else java |
| `build.gradle` / `*.kts` | java | TODO (manual fill) |
| `go.mod` | go | TODO (manual fill) |
| `Cargo.toml` | rust | TODO (manual fill) |
| `pyproject.toml` / `requirements.txt` | python | TODO (manual fill) |
| Marker Apple: `Package.swift`, `Podfile` / `*.podspec`, `Project.swift`, `Cartfile`, `*.xcworkspace`, `*.xcodeproj` | swift / objective-c / swift+objc | swiftui, uikit, appkit (trộn thì ghi cả 2, cái đa số trước) |

Marker hệ Apple xét **cuối cùng**: repo cross-platform như React Native có `package.json` ở root vẫn nhận stack chính. Project của Xcode là *directory* và mang tên app nên dò bằng glob theo phần mở rộng, không nằm trong list tên file cố định. Build tool suy theo marker: `swiftpm` · `tuist` · `xcodebuild+cocoapods` · `xcodebuild+carthage` · `xcodebuild`.

Repo Apple **có giao diện** (tìm thấy UIKit / SwiftUI / AppKit) được tính là **FE** cho mục đích Design System (multi-DS cấp DS root riêng) nhưng **không** import `fe-angular-rules.md` — bộ rule FE hiện có là rule Angular, chưa có rule Swift. Repo Apple **không giao diện** (SDK thuần dữ liệu) là thư viện client: không FE không BE → không DS root, không rule import.

Nguyên tắc chung của cả bảng: thà để `<TODO>` cho người điền hơn là ghi một giá trị sai trông có vẻ chắc chắn — `framework` sai khiến agent viết code chạy sai môi trường.

Stack khác? Sửa tay `.bmm-config.yaml` sau khi script chạy.

## Cấu trúc folder

```
.
├── .agent/skills/              ← Skill canonical (NTAPP + BMAD + Superpowers + SDLC)
├── .bmm-config.yaml            ← Per-skill output path override
├── .claude/
│   ├── settings.json           ← Event hook registration (committed) + enabledPlugins
│   └── hooks → ../hooks         ← Symlink (machine-local, gitignored)
├── .vsaf/workflows/NTAPP/      ← VSAF workflow YAML (chạy qua /NTAPP-vsaf-<name>)
├── hooks/                      ← Event hook canonical (16 hook + lib/ + manifest qua scripts/templates/)
├── scripts/                    ← bootstrap.sh + engine-patches/ + templates/ (pre-commit, hooks settings, workspace, bmm-config)
├── CLAUDE.md                   ← Project rules cho Claude Code
├── _bmad/                      ← BMM core config
├── NTAPP-output/               ← Output mọi skill (rỗng ban đầu)
│   ├── Stage_1_Discovery/      ← PRD, epics
│   ├── Stage_2_Architecture/   ← HLD, WBS, Module 0
│   ├── Stage_3_Specs/          ← TechSpec, UX Spec
│   ├── Stage_4_Design/         ← Detailed Design, UI Schema
│   ├── Stage_5_Build_Verify/   ← Story files, tests, reviews
│   ├── design-system/          ← Master DS metadata
│   └── ledgers/                ← slice-ledger + knowledge/ (slice-loop, tạo per slice)
└── docs/Process/               ← Manual + process docs
    ├── Manual_phase_1.md            ← set up lần đầu + tham chiếu chung + điều hướng
    ├── Manual_phase_1_brownfield.md ← workflow dự án brownfield
    └── Manual_phase_1_greenfield.md ← workflow dự án greenfield
```

## Workflow tham khảo

Đọc `docs/Process/Manual_phase_1.md` (set up lần đầu + tham chiếu chung) để hiểu:
- Vai trò + quyền approve mỗi stage
- Slash command tương ứng mỗi stage
- Quy tắc bắt buộc (pre-commit hook, header `id:`, Master DS lock)
- Multi-repo setup (chung cả 2 track)

Sau đó chọn workflow theo loại dự án:
- **Brownfield** (dựng lại hiện trạng + triage yêu cầu mới) → `docs/Process/Manual_phase_1_brownfield.md`
- **Greenfield** (tuyến tính từ Stage 1 Discovery) → `docs/Process/Manual_phase_1_greenfield.md`

**Build nhanh 1 slice end-to-end:** gõ `/NTAPP-vsaf-slice-loop <slice_id>` (vd `/NTAPP-vsaf-slice-loop SLICE-01`) — chạy nguyên Stage 3→4→5 một lệnh, dừng ở HITL demo gate, resume bằng `/NTAPP-vsaf-resume <runId>`. Tiền điều kiện: WBS lock + slice plan approved. Chi tiết: `CLAUDE.md` §VSAF Workflows.
