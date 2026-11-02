# DS Resolution — thủ tục resolve Design System root (SSoT)

> **Version:** v1.0 — thủ tục CHUẨN duy nhất để mọi skill/hook/script xác định DS root.
> Sinh ra cùng multi-DS support ([ds-registry-schema.md](ds-registry-schema.md)). Project single-DS (không có `registry.yaml`) đi qua thủ tục này với kết quả y hệt hành vi cũ.
> **Consumers phải REF file này thay vì tự chế logic resolve.**

## 0. Thuật ngữ

- **Family root** — thư mục `design-system/` cấp cao nhất (chứa `_shared/` và, nếu multi-DS, `registry.yaml`). Default: `{spec_repo_root}/NTAPP-output/design-system`.
- **DS root** — thư mục chứa trọn bộ artifact của MỘT design system (`master_token.json`, `stack-profile.json`, `feature_deltas/`, …). Legacy: DS root ≡ family root. Multi-DS: `{family_root}/{systems.{ds_id}.root}`.

## A. Skill chạy từ CODE REPO (`ntapp-ds-bootstrap`, `ntapp-ds-build-component`)

1. Đọc `bmad.design_system_root` từ `.bmm-config.yaml` của **code repo** (cwd). Default khi thiếu: `{spec_repo_root}/NTAPP-output/design-system`.
2. Giá trị này LÀ DS root của repo — dùng thẳng, KHÔNG cần đọc registry (bất biến #5 registry schema).
3. **Guard:** nếu `{design_system_root}/registry.yaml` tồn tại → config đang trỏ FAMILY root trong project multi-DS → STOP, yêu cầu DSO sửa `.bmm-config.yaml` trỏ vào `{family}/{ds_id}` của repo (liệt kê các `ds_id` có trong registry để chọn). KHÔNG tự đoán.
   - *Ngoại lệ:* registry có system `root: "."` mà `code_repo` khớp repo hiện tại → DS root hợp lệ chính là family root (DS legacy in-place) → tiếp tục, không STOP.

## B. Skill chạy từ SPEC REPO, làm việc PER-UNIT (`ntapp-ui-generation`, `ntapp-feature-design`)

1. Resolve **family root**: `bmad.design_system_root` từ `.bmm-config.yaml` spec repo → thiếu thì Layer 1 `_bmad/bmm/config.yaml` `design_system_root` → thiếu nữa thì `{spec_repo_root}/NTAPP-output/design-system`.
2. `{family_root}/registry.yaml` **không tồn tại** → DS root = family root. XONG (legacy — đường đi của mọi project 1 DS).
3. Registry có **đúng 1 system** → DS root = system đó. XONG.
4. Registry có **≥2 systems** → match unit theo thứ tự tín hiệu, dừng ở tín hiệu đầu tiên cho kết quả DUY NHẤT:
   1. **Thẻ `repo:` ở Cluster Header WBS** (PRIMARY): tìm cluster chứa `id` trong `project_wbs.md` (consumer nhánh B vốn đã load WBS cho pre-flight identity — đọc thẻ là miễn phí) → Cluster Header có thẻ `<br>- repo: <code-repo-folder>` (format + audit: `NTAPP-architecture-design` coverage_matrix mục 0 + step-04.1b — **bắt buộc cho mọi cluster `frontend-app` khi project ≥2 FE repo**, nên tín hiệu này tin cậy được) → match `systems.{ds}.code_repo` == giá trị thẻ → `ds_id`.
   2. **`id_prefixes`** — longest-prefix match trên `id` của unit (vd `SCR-ADM-LOGIN` ↔ `SCR-ADM-`).
   3. **`modules`** — module WBS chứa unit (skill nào đã lookup WBS/DD thì sẵn module) ∈ `systems.{ds}.modules`.
   4. **`default_ds`** (nếu khai trong registry).

   **Conflict = config drift:** tín hiệu 1 (thẻ WBS) và 2/3 (registry hints) trỏ 2 system KHÁC nhau → **STOP báo mismatch** (liệt kê cả 2 nguồn + giá trị), yêu cầu DSO sửa registry hints hoặc thẻ WBS cho khớp — KHÔNG chọn im lặng theo bất kỳ bên nào.
5. Không tín hiệu nào khớp (hoặc mâu thuẫn theo rule trên) → **STOP hỏi HITL** (R9 — không đoán): liệt kê `ds_id` + `framework` + `code_repo` từng system, yêu cầu user chọn cho unit này, đồng thời hint DSO bổ sung thẻ `repo:` vào Cluster Header WBS (primary) hoặc `id_prefixes`/`modules` vào registry để lần sau tự resolve.
6. Sau khi có DS root: **mọi** path artifact DS của unit (`master_token.json`, `components_metadata.json`, `stack-profile.json`, `component_catalog.md`, `_reference/`, `library_apis/`, `feature_deltas/{id}/`) đều prefix DS root đó. Ghi `ds_id` đã resolve vào artifact output (proposal header, build report, DD Section 1) để audit.

## C. Skill chạy từ SPEC REPO, làm việc PER-FEATURE đa màn (`ntapp-ux-design`)

Feature có thể trải screen trên NHIỀU DS (vd journey maker app-user + checker app-admin):

1. Resolve family root như B.1-B.2.
2. Legacy / 1 system → load 1 `component_catalog.md` như cũ.
3. ≥2 systems → resolve từng `SCR-*`/`WGT-*` của feature theo B.4; load `component_catalog.md` của **mọi DS xuất hiện**, label vocabulary theo `ds_id` khi nhắc component (vd "`DataTable` *(web-admin)*"). Screen không resolve được → dùng vocabulary chung chung + WARN (ux-design là journey-level, catalog chỉ recommended — KHÔNG STOP vì thiếu resolve).

## D. Hooks / pre-commit / scripts (bash — không có ngữ cảnh unit đầy đủ)

Không re-implement B — nhánh D **KHÔNG parse WBS/thẻ `repo:`** (bash không đọc cluster header); xác định DS qua **path artifact + glob** là đủ vì WBS ID global-unique. Dùng helpers trong `hooks/lib/common.sh`:

- `get_design_system_root` — giá trị config của repo hiện tại (code repo → DS root; spec repo → family root; thiếu → default). KHÔNG hardcode `NTAPP-output/design-system` trong hook.
- `ds_roots` — liệt kê mọi DS root: không có `registry.yaml` → chính nó; có → mỗi `systems.*.root`.
- `find_unit_delta_dir <ID>` — tìm `{ds_root}/feature_deltas/<ID>` qua các root (ID global-unique → tối đa 1 hit).
- Verify artifact của 1 build/proposal: **derive DS root từ chính path file tìm được** (`.../{ds_root}/feature_deltas/{id}/x.md` → DS root = `dirname/../..`) thay vì assume 1 root cố định.
- Gate "DS đã bootstrap chưa" per-repo (pre-commit): check `master_token.json` tại DS root của **chính repo đang commit** (config repo đó); spec-side gate (hook 3): block chỉ khi **KHÔNG system nào** bootstrap xong, warn liệt kê system còn thiếu.

## E. Bảng consumer → nhánh

| Consumer | Nhánh |
|---|---|
| `ntapp-ds-bootstrap`, `ntapp-ds-build-component` | A |
| `ntapp-ui-generation` (4b), `ntapp-feature-design` (4a) | B |
| `ntapp-ux-design` (3b) | C |
| `ntapp-feature-triage` (0.5) | B — **degraded**: advisory, unresolved → `unknown` + liệt kê ứng viên, KHÔNG STOP (unit chưa chốt tại intake) |
| hooks 3/5/5b/6, pre-commit Rule 4/6/7, VSAF prompt paths | D |
| `ntapp-ux-sketch` (Stage 1) | F — **cosmetic, read-only** (chỉ để skin preview hi-fi) |

## F. `ntapp-ux-sketch` (Stage 1) — resolve COSMETIC, read-only

Stage 1 chưa có unit nào để match (WBS chưa lock), và DS ở đây chỉ dùng để **skin preview hi-fi** — không phải contract. Vì vậy nhánh này KHÔNG BAO GIỜ STOP:

1. Resolve family root như B.1.
2. Không có `registry.yaml` → DS root = family root.
3. Registry có đúng 1 system → system đó. ≥2 systems → `default_ds`; không khai `default_ds` → hỏi user 1 lần (interactive) / lấy system đầu + WARN (headless).
4. `{ds_root}/master_token.json` không tồn tại (Stage 0 chưa chạy) → **không phải lỗi**: preview dùng theme placeholder (`sketch_preview_theme`, default `corporate`) và ghi rõ "placeholder look" ở header preview.
5. **Read-only tuyệt đối:** ux-sketch chỉ ĐỌC `master_token.json` + `_reference/`; KHÔNG ghi token, KHÔNG sinh `feature_deltas/`, KHÔNG suy ra component mapping (quyền đó ở Stage 4b). Ghi `ds_id` đã dùng vào header preview để audit.
