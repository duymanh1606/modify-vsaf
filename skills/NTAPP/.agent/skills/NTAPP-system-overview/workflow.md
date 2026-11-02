# NTAPP-system-overview — Workflow (router)

> **Mục đích:** Sinh tài liệu mô tả hệ thống cho multi-repo workspace. 2 mode: `baseline` (**DEFAULT**, audit-grade + cross-system matrix + Q&A) và `overview` (opt-in, ergonomic per-repo doc).
>
> **Portability:** Skill canonical KHÔNG hard-code project / repo / org name. Mọi runtime value đến từ (a) CWD, (b) tham số dòng lệnh, (c) BMM config, (d) user input ở scope confirm.

---

## Tham số (tự nhận từ user message)

| Param | Loại | Default | Áp dụng mode | Ý nghĩa |
|---|---|---|---|---|
| `--mode <baseline\|overview>` | enum | **`baseline`** | both | Chọn mode chạy. Không nêu → `baseline` |
| `--repos <list>` | csv | (auto-detect) | both | Explicit list (vd `--repos service-a,service-b`), skip auto-detect |
| `--workspace-root <path>` | string | parent của CWD | both | Override folder cha chứa sibling code repo |
| `--output-dir <path>` | string | mode-specific | both | Override output location |
| `--force` | flag | false | overview | Overwrite file đã tồn tại (default skip) |
| `--project-label <str>` | string | (none) | both | Optional header label (vd "ACME Payment Platform") |
| `--skip-qa` | flag | false | baseline | Bỏ qua interactive Q&A loop, mọi gap → TODO inline (CI / non-interactive) |

**Default output dir (cả 2 mode):**
- `{BMM stage_1_discovery}/system_overview/` (đọc qua `.bmm-config.yaml` section `ntapp-system-overview:` → `planning_artifacts`)
- `--output-dir` flag override vẫn áp dụng cho cả 2 mode

---

## STEP 0 — Mode resolution & sanity check

1. Parse `--mode`. **Default = `baseline`** — user KHÔNG nêu `--mode` (hoặc chỉ gõ `/ntapp-system-overview` trơn, hoặc nói "tạo overview cho các repo" bằng prose) → chạy `baseline`. Validate value ∈ {`baseline`, `overview`}.
   - Chỉ chạy `overview` khi user gõ tường minh `--mode overview`, hoặc nói rõ ý "chỉ cần doc onboarding / không cần contract matrix / không muốn Q&A".
   - KHÔNG tự downgrade sang `overview` để né gate multi-root (STEP 1.3) hay né Q&A loop. Gate fail → HALT và báo user, để user tự chọn `--mode overview`.
   - Echo mode đã resolve ở bảng scope confirm (STEP 1.4) kèm nguồn: `baseline (default)` / `baseline (explicit)` / `overview (explicit)`.
2. Resolve CWD = `$PWD`. Resolve workspace root = `--workspace-root` hoặc parent của CWD.
3. **Cả 2 mode:** Resolve output dir theo cascade 3 layer:
   - Layer 1: `{project-root}/_bmad/bmm/config.yaml` → key `stage_1_discovery`.
   - Layer 2: `{project-root}/.bmm-config.yaml` section `ntapp-system-overview:` → key `planning_artifacts`.
   - Layer 3: prompt user nhập default `{stage_1_discovery}/system_overview`, append vào `.bmm-config.yaml`.
   - Resolve `{project-root}` bằng walk-up tìm `_bmad/` rồi `.git/`. Không thấy → fallback CWD + warning.
4. Skill canonical KHÔNG verify CWD theo project name. User chịu trách nhiệm gọi skill đúng nơi.

---

## STEP 1 — Discover code repos (shared cả 2 mode)

### 1.1 Auto-detect (khi không có `--repos`)

Liệt kê sub-folder trong workspace root, filter: là directory, không phải CWD, không phải hidden / dot-folder.

Per candidate, áp dụng **two-tier detection** theo thứ tự ưu tiên:

**Tier 1 — `.bmm-config.yaml` (authoritative, bootstrap-generated)**

Check `{candidate}/.bmm-config.yaml` có tồn tại không.
- Nếu có: parse key `bmad.spec_repo_root` → resolve thành absolute path (join candidate abs path + relative) → so sánh với spec repo root (resolve CWD walk-up tới folder có `_bmad/` hoặc `.git/`).
  - **Match** (cùng project) → **include**. Lấy `stack_hint` từ block `stack:` (language / framework) thay vì re-detect từ marker. Gán `registered: true`.
  - **No match** (khác project) → **skip** silently. Ghi vào internal `other_project_repos` list để log cuối nếu cần debug.
- Nếu không có file → fall through Tier 2.

**Tier 2 — marker files (fallback, unregistered repos)**

Chỉ chạy khi Tier 1 không conclude (không có `.bmm-config.yaml`). Check ít nhất 1 marker: `pom.xml`, `build.gradle{,.kts}`, `package.json`, `go.mod`, `requirements.txt`, `pyproject.toml`, `setup.py`, `Cargo.toml`, `*.csproj`, `*.sln`, `Gemfile`, `composer.json`, `mix.exs`.
- Có marker → **include** nhưng gán `registered: false`. Infer `stack_hint` từ marker như trước.
- Không có marker → skip.

Per candidate capture: `repo_name` (folder), `stack_hint`, `repo_abs_path`, `registered` (true/false), `existing_overview` (= file đã tồn tại trong output dir?).

> **Lưu ý bootstrap:** `.bmm-config.yaml` là machine-local (gitignored trong code repo). Nếu repo chưa chạy `bootstrap.sh` trên máy hiện tại thì file không tồn tại → Tier 2 fallback là bình thường. Nhắc user trong scope confirmation nếu có `registered: false` repo.

### 1.2 Explicit list (`--repos a,b,c`)

Verify mỗi folder tồn tại. Per folder: check `.bmm-config.yaml` trước (Tier 1) → fallback marker files (Tier 2) → nếu cả hai đều không có: log warning + skip. Gán `registered` như STEP 1.1.

### 1.3 Mode baseline (default) — extra gate (multi-root required)

Mode baseline: nếu sau detect không có repo nào → HALT:

```
❌ MULTI-ROOT WORKSPACE REQUIRED (mode baseline — default)

Mode `baseline` cần ≥1 code repo trong workspace root.
Detected: (rỗng)

Cách xử lý:
  - Mở IDE multi-root workspace gồm spec repo + code repo, hoặc
  - Dùng `--repos` / `--workspace-root` chỉ định rõ, hoặc
  - Nếu chỉ cần doc onboarding per-repo (không Contract Matrix): /ntapp-system-overview --mode overview
```

KHÔNG tự fallback sang `overview` — user quyết định.

Mode overview: nếu rỗng → báo user (không HALT formal), gợi ý kiểm tra `--workspace-root` / `--repos`.

### 1.4 Scope confirmation

Render bảng cho user:

```
Mode:           <baseline (default) | baseline (explicit) | overview (explicit)>
Workspace root: <abs-path>
Output dir:     <abs-path>

Detected code repos:

| # | Repo | Stack | Registered | Overview status |
|---|------|-------|------------|-----------------|
| 1 | <repo-a> | java (Maven) | ✓ bootstrap | EXISTS — will SKIP (--force để regen) |
| 2 | <repo-b> | node         | ✓ bootstrap | missing — will GENERATE |
| 3 | <repo-c> | go           | ⚠ unregistered (no .bmm-config.yaml) | missing — will GENERATE |

⚠  Repo <repo-c> không có .bmm-config.yaml — chưa chạy bootstrap.sh hoặc không thuộc project này.
   Xác nhận trước khi include: đây có phải code repo của project không?

Bạn muốn:
  (a) Generate tất cả "will GENERATE"
  (b) Chọn subset (vd "2,3")
  (c) Đổi tên sub-system trước confirm (mode baseline only — vd "2=auth-svc, 3=core-api")
  (d) Override file đã tồn tại (mode overview — vd "--force 1")
  (e) Đổi mode: chỉ cần doc onboarding per-repo, bỏ Contract Matrix + Q&A → "mode overview"
  (f) Hủy

Lựa chọn?
```

**Pause & Wait** — KHÔNG default. KHÔNG tự suy đoán scope. Đặc biệt mode baseline phải honest (`Detected vs Scope` sẽ được ghi vào cross-system file).

Nếu tất cả repos đều `registered: true` → không hiện warning ⚠ unregistered. Nếu không có repo nào `registered: true` (bootstrap chưa chạy trên máy này) → thêm note: `ℹ  Không tìm thấy .bmm-config.yaml trong bất kỳ repo nào. Chạy ./scripts/bootstrap.sh --refresh để register repos với project này.`

Sau confirm:
- Nếu user chọn (e) → set `mode = overview`, re-render bảng scope confirm 1 lần với mode mới (option (c) biến mất, (d) xuất hiện), Pause & Wait lại. Chỉ hạ mode qua lựa chọn tường minh này.
- Build `scope_list` = list `(repo_name, repo_abs_path, stack_hint)` đã chọn.
- Build `out_of_scope_list` = `detected_list \ scope_list` (mode baseline cần).
- Verify mọi `repo_abs_path` readable. Fail → báo user, không proceed.

---

## STEP 2 — Dispatch theo mode

| Mode | File | Nội dung |
|---|---|---|
| `baseline` (default) | [./modes/baseline.md](./modes/baseline.md) | Spawn N parallel sub-agent có Section 0, sau đó cross-system synthesis + interactive Q&A, dual-write archive |
| `overview` (opt-in) | [./modes/overview.md](./modes/overview.md) | Spawn N parallel sub-agent, mỗi agent sinh 1 file 10-section / repo |

Đọc file mode tương ứng và thực thi.

---

## Evidence policy (cả 2 mode)

Tuân thủ [./principles.md](./principles.md). Tóm tắt:
- **Body sections** (Executive Summary, Business Features, Risks, ...) — cho phép `**Assumption:** ...` prose khi suy luận business intent, evidence không bắt buộc per dòng.
- **Bảng Integration / Contract / API** — bắt buộc cột `File evidence` (file:line). Thiếu → dán `<TODO: SA verify — câu hỏi cụ thể>`.
- **Mode baseline only**: Contract Match Matrix evidence-driven, không có Assumption.

---

## Notes

- Skill chỉ ghi file. Không commit, không stage, không push.
- Cả 2 mode ghi vào `NTAPP-output/Stage_1_Discovery/system_overview/` — feed input cho `/ntapp-architecture-design` Stage 2. Override qua `--output-dir` nếu cần.
- Wrapper / automation muốn tích hợp: gọi skill này với param phù hợp, KHÔNG sửa skill canonical.
