# Fix Bug Workflow (NTAPP Self-Contained Orchestrator)

**Goal:** Từ 1 file `BUGS-<SLICE-ID>-<account>.md`, fix mọi bug đang mở ở code repo, flip trạng thái → `Fixed`, rồi đồng bộ tài liệu spec đã lệch so với code mới. KHÔNG tự commit.

**Your Role:** Bạn là **intake adapter cho nguồn file-local** (đối xứng với workflow `bug-fix-batch` — adapter Jira). Điều phối tuần tự 3 step, là điểm chạm duy nhất với user (**1 HITL gate** sau step-01). Việc **fix đúng một bug trên một unit** được ủy quyền cho **engine dùng chung `NTAPP-bug-fix-engine`** (ceremony-adaptive) — skill này KHÔNG tự viết lại logic root-cause/DD/ATDD/pre-commit/verify/doc-sync; chỉ lo parse file, localize, classify, plan (HITL), gọi engine per-bug (`in-place-nocommit`), rồi flip status trong file + report.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (INITIALIZATION + pipeline map + global rules). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm GATE nếu có) RỒI mới đọc step kế. KHÔNG đọc trước nhiều step. State chuyển qua artifact (bug file + code), không qua việc giữ instruction trong context.

---

## INITIALIZATION (Configuration Resolution)

Trước khi chạy step nào, resolve config theo cascade.

### Bước 0 — Resolve `bug_source` (file hay Jira)
Đọc input user:
- Khớp mã Jira (`^[A-Z][A-Z0-9]+-\d+$`) hoặc URL chứa `/browse/<KEY>` → `bug_source = jira`, `jira_keys = [...]` (nhiều mã cách nhau bằng dấu phẩy/space; bỏ tiền tố `jira` nếu user gõ kèm).
- Còn lại (path `.md`, hoặc file đang mở trong IDE) → `bug_source = file`.
- Cả 2 đều thiếu → DỪNG, hỏi user.

### Bước 0b — Resolve `{spec_repo_root}` (project-root)
File bug nằm trong spec repo. Walk up từ thư mục chứa file bug: thấy `_bmad/` → `{spec_repo_root}`; else thấy `NTAPP-output/` → `{spec_repo_root}`; else fallback `cwd` + log warning. `bug_source = jira` (không có file làm mốc) → walk up từ `cwd`.

### Bước 1 — Resolve code repo(s)
Code không nằm trong spec repo (dual-repo). Code repo là các **thư mục anh em** của spec repo (cùng folder cha), hoặc các additional working directory đang mở. Lập danh sách ứng viên repo từ:
- Các additional working directory đang mở.
- Các thư mục anh em chứa source (`src/`, `package.json`, `pom.xml`, `build.gradle`, `go.mod`, ...).
- `NTAPP-output/Stage_5_Build_Verify/bug-batches/_unit-path-map.yaml` nếu có (`containers[].repo`).

Map **WBS unit → repo** thực hiện ở step-01 (qua mô tả module trong WBS / techspec / detailed_design + grep code). KHÔNG đoán repo ở đây.

### Bước 2 — Paths cố định trong spec repo
| Biến | Giá trị |
|---|---|
| `bug_file` | đường dẫn user cung cấp (`{bugs_dir}/BUGS-<SLICE-ID>-<account>.md`) — user chỉ đưa mã slice thì **KHÔNG glob**: gọi helper, lấy `bug_files` (xem hộp dưới bảng). `bug_source = jira` → resolve qua tra ngược ở step-01 §1b, có thể không có |
| `bugs_dir` | helper trả về (`bugs_dir`); mặc định `{spec_repo_root}/NTAPP-output/Stage_1_Discovery/Bugs_Issues/` |
| `jira_helper` | `<skills-dir>/NTAPP-log-bug/jira_bug.py` — skill sibling cùng cấp trong skill dir (Jira client dùng chung với `NTAPP-log-bug`). Chạy `python -X utf8 <jira_helper> <subcommand>`; không tìm thấy → DỪNG nhánh Jira, báo user chạy `./scripts/sync-skills-to-user.sh --skills-only` |
| `wbs` | `{spec_repo_root}/NTAPP-output/Stage_2_Architecture/project_wbs.md` |
| `techspec_dir` | `{spec_repo_root}/NTAPP-output/Stage_3_Specs/techspec/` |
| `dd_dir` | `{spec_repo_root}/NTAPP-output/Stage_4_Design/detailed_design/` |
| `ui_schema_dir` | `{spec_repo_root}/NTAPP-output/Stage_4_Design/ui_schema/` |
| `ds_root` | `{spec_repo_root}/NTAPP-output/design-system/` |
| `build_verify_dir` | `{spec_repo_root}/NTAPP-output/Stage_5_Build_Verify/` |
| `slices_dir` | helper trả về (`slices_dir`); mặc định `{spec_repo_root}/NTAPP-output/Stage_2_Architecture/slices/` |
| `date` | ngày hệ thống, `YYYY-MM-DD` |

> ⚠️ **`slices_dir`, `bugs_dir`, `bug_file` KHÔNG được ghép bằng tay.** Gọi:
>
> ```
> python3 {project-root}/hooks/lib/slice_paths.py --resolve <SLICE-ID> --json
> ```
> *(Windows: dò `py -3` → `python3` → `python`.)*
>
> Trả về `slices_dir`, `bugs_dir`, `assets_dir`, `slice_files[]`, `bug_files[]`, `warnings[]` — đã chuẩn hoá zero-pad và khớp theo **ranh giới**, nhận cả bố cục phẳng lẫn bố cục thư mục feature.
>
> Ba lý do, cả ba là lỗi đã xảy ra thật:
> 1. **Bảng này từng ghi `Stage_5_Build_Verify/slices/` — thư mục không tồn tại.** Slice thật ở `Stage_2_Architecture/slices/`. Sáu file khác trong framework ghi đúng, ba file nhánh bug ghi sai; phe đúng thắng bằng số đông chứ không bằng cơ chế nào.
> 2. **Glob `BUGS-<SLICE-ID>*.md` khớp theo tiền tố.** `SLICE-2` bắt luôn `SLICE-20`, `SLICE-21`, `SLICE-24` — 4 file thay vì 1, và skill fix nhầm bug của ba slice khác.
> 3. **Zero-pad không khớp.** Skill viết `SLICE-06`, đĩa có `SLICE-6-…`.
>
> **Mã thoát:** `0` = tra được (danh sách có thể rỗng — nghĩa là *thật sự không có*); `3` = **không tra được**, DỪNG và đọc `warnings`; `2` = mã slice sai dạng.

---

## OPEN-STATUS FILTER (bất biến)

Bug "đang mở" = trạng thái ∈ **{`Open`, `In Progress`, `Reopened`}**. Bỏ qua `Fixed` và `Closed`.
Parse entry theo format `NTAPP-log-bug`: mỗi bug là 1 block `## <SLICE>-<account>-BUG-NN — <title>` với dòng `- **Trạng thái:** <status>`.

**Với `bug_source = jira`** — trạng thái là workflow Jira, không phải 4 giá trị trên. Coi là **đang mở** khi status KHÔNG thuộc {`Resolved`, `Closed`, `Cancelled`, `Done`}. Issue đã đóng → báo user trạng thái hiện tại và hỏi có fix tiếp không, KHÔNG tự bỏ qua im lặng (khác lane file: file thì bỏ qua im lặng vì đang quét cả danh sách).

---

## PIPELINE MAP (neo thường trực — 1 dòng/step)

| # | Step file | Mục tiêu | Output |
|---|---|---|---|
| 01 | steps/step-01-triage-plan.md | Parse + filter bug đang mở → map unit→repo → **classify** (severity/atdd_class/lane) → fix plan → **HITL gate** | Plan table (in chat) |
| 02 | steps/step-02-fix-and-verify.md | Per-bug: **gọi engine `NTAPP-bug-fix-engine`** (in-place-nocommit, doc-sync inline) → flip status `Fixed` | Code đã sửa + doc synced + bug file cập nhật status |
| 03 | steps/step-03-doc-sync-report.md | Reconcile doc chung → **resolve Jira (HITL gate)** → report tổng cuối | Jira đã Resolved + báo cáo cuối (in chat) |

Chuỗi: **01 → [GATE: user duyệt plan] → 02 → 03 (có [GATE: user duyệt nội dung ghi lên Jira]) → terminal**.

---

## GLOBAL RULES (áp dụng mọi step)

- **R1 — Bug file read-mostly:** chỉ được sửa dòng `- **Trạng thái:**` (+ thêm `- **Ghi chú fix:**`) của đúng bug đang xử lý. KHÔNG sửa mô tả, KHÔNG đụng bug khác (append-only như `NTAPP-log-bug`).
- **R2 — Không tự commit:** sau khi fix + doc-sync, DỪNG để user review. Không `git commit`, không `git push`.
- **R3 — Tôn trọng pre-commit hook:** *(engine thực thi)* giữ header `id:`+`dd_version:`, UI dùng design token (không hardcode color/px/font), không emoji unicode — chi tiết ở engine.
- **R4 — Root-cause trước khi fix:** *(engine thực thi)* tuân `superpowers-systematic-debugging`. Cấm "fix mò" triệu chứng mà chưa xác định nguyên nhân.
- **R5 — Bug không tự fix được** (mơ hồ / không tái hiện / phụ thuộc ngoài / cần quyết định sản phẩm), hoặc engine trả **BLOCKER / ESCALATE**: GIỮ nguyên trạng thái, ghi lý do vào report, KHÔNG flip `Fixed`, đi tiếp bug khác.
- **R6 — Code là nguồn sự thật sau fix:** *(engine doc-sync inline thực thi)* tài liệu chỉnh theo code mới (surgical); `*_detailed_design.md` đổi bản chất → bump `dd_version` + đồng bộ header code. step-03 chỉ reconcile doc chung + report.
- **R7 — Jira là state dùng chung ngoài repo:** mọi lệnh ghi Jira (`update-issue`, `transition`) chỉ được gọi ở step-03 **sau khi user duyệt gate**, và chỉ cho bug engine trả thành công. Bug BLOCKER / ESCALATE / R5 → **KHÔNG đụng Jira**. Không tự comment, không tự đổi priority/label, không đóng issue của người khác ngoài danh sách đang xử lý. Đọc Jira (`get-issue`) thì tự do, không cần gate.
- ⛔ Đọc đúng một step file mỗi lần.

---

## LAUNCH

Sau INITIALIZATION:
- `bug_source = file` → xác nhận `bug_file` tồn tại và đọc được. Thiếu → DỪNG, hỏi user đường dẫn file bug.
- `bug_source = jira` → xác nhận `jira_helper` tồn tại và `get-issue` chạy được cho mã đầu tiên. Lỗi credential (thiếu `env.md`) → DỪNG, hướng dẫn theo `env.example.md` trong skill dir `NTAPP-log-bug`.

**Next:** Read fully and follow `./steps/step-01-triage-plan.md`
