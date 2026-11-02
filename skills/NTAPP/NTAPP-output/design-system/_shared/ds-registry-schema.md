# DS Registry Schema — `registry.yaml`

> **File:** `{design_system_family_root}/registry.yaml` (family root = thư mục `design-system/` cấp cao nhất, nơi chứa `_shared/`).
> **Version:** v1.0
> **Producer:** `/ntapp-ds-bootstrap` (nhánh "tạo DS mới" khi bootstrap FE repo thứ 2) hoặc `scripts/bootstrap.sh` (scaffold khi detect ≥2 FE repo). DSO được phép hand-edit.
> **Consumers:** skill phía spec repo (`ntapp-ui-generation`, `ntapp-feature-design`, `ntapp-ux-design`), hooks (3/5/5b/6), pre-commit template, VSAF workflow prompts.

## 1. Khi nào file này tồn tại

| Trạng thái | Ý nghĩa |
|---|---|
| **KHÔNG có `registry.yaml`** | **Legacy single-DS mode** (mặc định). Toàn bộ artifact DS nằm phẳng ngay tại family root (`master_token.json`, `components_metadata.json`, `stack-profile.json`, `component_catalog.md`, `_reference/`, `library_apis/`, `feature_deltas/`, `archive/`). Mọi hành vi y hệt trước khi có registry — project 1 FE repo KHÔNG cần tạo file này. |
| **Có `registry.yaml`** | **Multi-DS mode.** Mỗi DS là 1 entry trong `systems:`, artifact nằm trong `{family_root}/{root}/`. |

## 2. Format

```yaml
# design-system/registry.yaml
version: 1
default_ds: web-admin          # optional — dùng khi unit không resolve được (thay vì HITL)

systems:
  web-admin:                   # ds_id — kebab-case, ổn định, KHÔNG đổi sau khi tạo
    root: "."                  # relative với family root. "." = DS legacy giữ chỗ cũ (flat)
    code_repo: acme-admin-fe   # tên folder code repo trong workspace cha (khớp bootstrap.sh detect)
    framework: react           # khớp stack-profile.json → framework.name
    id_prefixes: [SCR-ADM-, WGT-ADM-]   # optional — hint resolve unit→DS (longest-prefix match)
    modules: [SHELL, ADM]      # optional — hint resolve theo module WBS của unit

  mobile-app:
    root: "mobile-app/"
    code_repo: acme-mobile
    framework: react-native
    id_prefixes: [SCR-APP-, WGT-APP-]
```

## 3. Field semantics

| Field | Bắt buộc | Quy tắc |
|---|---|---|
| `version` | ✅ | Hiện tại `1`. |
| `default_ds` | ❌ | `ds_id` fallback khi unit không match hint nào. Không khai → fallback là HITL STOP (xem [ds-resolution.md](ds-resolution.md)). |
| `systems.{ds_id}` | ✅ ≥1 | `ds_id` kebab-case `[a-z0-9-]+`, unique, bất biến (đổi tên = migration tay: `git mv` + sửa registry + sửa `.bmm-config.yaml` code repo). |
| `root` | ✅ | Path relative với family root. `"."` hợp lệ cho DUY NHẤT 1 system (DS đầu tiên giữ layout flat cũ — zero-migration). Các root KHÔNG được lồng nhau (trừ `"."` với các sibling). |
| `code_repo` | ✅ | Tên folder code repo (basename trong workspace cha). **Đây là giá trị mà thẻ `- repo:` ở Cluster Header WBS match vào** (primary binding unit→DS — xem [ds-resolution.md](ds-resolution.md) B.4.1 + `NTAPP-architecture-design` coverage_matrix mục 0). 1 DS có thể phục vụ nhiều repo (share UI lib) → cho phép list: `code_repo: [repo-a, repo-b]`; khi đó `bmad.design_system_root` của cả 2 repo trỏ cùng 1 DS root. |
| `framework` | ✅ | Mirror `stack-profile.json.framework.name` của DS đó (denormalized cho tra cứu nhanh — SSoT vẫn là stack-profile). |
| `id_prefixes` | ❌ | Hint resolve unit→DS, **fallback sau thẻ `repo:` WBS** (B.4.2). Match theo longest-prefix trên WBS ID (`SCR-ADM-LOGIN` khớp `SCR-ADM-`). Prefix phải phân biệt lẫn nhau giữa các system, và KHÔNG được mâu thuẫn thẻ WBS (conflict → consumer STOP báo drift). |
| `modules` | ❌ | Hint resolve theo module WBS chứa unit (fallback B.4.3). |

## 4. Bất biến (invariants)

1. **Mỗi DS root chứa TRỌN BỘ artifact của DS đó:** `master_token.json`, `components_metadata.json`, `stack-profile.json`, `component_catalog.md`, `_reference/`, `library_apis/`, `feature_deltas/`, `archive/`, `bootstrap_report.md`. Không có artifact DS nào share chéo giữa 2 root.
2. **`_shared/` LUÔN ở family root** — schema/rubric/thuật toán là framework-level, DS-agnostic. KHÔNG copy `_shared/` vào từng `{ds_id}/`.
3. **1 DS = 1 framework.** Repo monorepo đa framework vẫn STOP ở stack-detect (luật cũ giữ nguyên) — registry không phải cách lách luật đó.
4. **WBS ID là global-unique toàn project** (2 app có màn login → ID phải phân biệt, vd `SCR-ADM-LOGIN` / `SCR-APP-LOGIN`). Registry KHÔNG cứu được ID trùng — `feature_deltas/{id}` chỉ hết collision nhờ namespace, nhưng `ui_schema_{id}.json` (Stage_4_Design, flat) và Rule 2/6 pre-commit vẫn cần ID unique.
5. `bmad.design_system_root` trong `.bmm-config.yaml` của **mỗi code repo** trỏ **thẳng vào DS root của repo đó** (`{family}/{root}` sau resolve), KHÔNG trỏ family root. Skill chạy từ code repo (`ds-bootstrap`, `ds-build-component`) nhờ vậy không cần đọc registry.
6. `bmad.design_system_root` trong `.bmm-config.yaml` của **spec repo** (nếu khai) trỏ **family root**.

## 5. Vòng đời

| Sự kiện | Hành động |
|---|---|
| Project 1 FE repo | Không có registry. Không làm gì. |
| Bootstrap FE repo thứ 2 (`/ntapp-ds-bootstrap` phát hiện DS đã tồn tại ở root config trỏ tới) | HITL 3 nhánh: re-bootstrap DS hiện có / **tạo DS mới** (khuyến nghị — sinh registry, DS cũ nhận `root: "."` + `ds_id` do DSO đặt, DS mới vào `{ds_id}/`) / abort. Xem `ntapp-ds-bootstrap` step-01. |
| Muốn gọn layout sau khi lên multi | Migration tay tùy chọn: `git mv` toàn bộ artifact flat vào `{ds_id}/`, sửa `root: "."` → `root: "{ds_id}/"`, sửa `.bmm-config.yaml` code repo tương ứng. |
| Thêm hint resolve | DSO edit `id_prefixes` / `modules` / `default_ds` trực tiếp — không cần chạy skill. |
