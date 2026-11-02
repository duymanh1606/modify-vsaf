# Step 03 — Doc-sync + commit + fix-report (terminal)

**Persona:** Người giữ spec khớp code + đóng gói kết quả trả orchestration.

**Mục tiêu:** Đồng bộ tài liệu spec đã lệch (theo `doc_sync_mode`), commit theo `commit_mode`, xuất **fix-report có cấu trúc**.

---

## 1. Doc-sync (theo `doc_sync_mode`)
- `doc_sync_mode=inline` (tuần tự — vd NTAPP-fix-bug) → chạy doc-sync ngay.
- `doc_sync_mode=deferred` (fanout song song — vd bug-fix-batch) → **KHÔNG ghi spec repo ở đây** (tránh tranh ghi giữa các fix song song); chỉ **emit TODO** trong report (unit + doc ứng viên + bản chất thay đổi) để node serial của orchestration sync sau.

Khi `inline`, xác định doc ứng viên theo bản chất thay đổi code (chỉ sửa khi **thực sự lệch**, surgical — R3):

| Loại thay đổi code | Doc cần đối chiếu |
|---|---|
| Behavior / luồng xử lý | `dd_dir/<unit>_detailed_design.md`; `techspec_dir/*<unit>*` |
| API contract (path/method/request/response) | techspec + `dd_dir/<unit>_detailed_design.md` (mục API) |
| Props / cấu trúc component UI, state | `dd_dir/<unit>_detailed_design.md`; `ui_schema_dir/ui_schema_<unit>.json`; `build_verify_dir/<unit>.md` |
| Token / component design-system (NEW/MODIFIED) | `ds_root/master_token.json`, `ds_root/components_metadata.json`, `ds_root/feature_deltas/<unit>/` |
| Tiêu chí demo / acceptance của slice | `slice_files[]` từ `slice_paths.py --resolve <SLICE>` (**không** glob `slices_dir/<SLICE>*.md` — `SLICE-2` bắt luôn `SLICE-20/21/24`); story file ở `build_verify_dir/` |

- **Bug UI-style thuần** (chỉ chỉnh token/spacing về đúng chuẩn, không đổi behavior/contract/props) → thường **không** cần sửa doc; chỉ cập nhật nếu doc/ui_schema ghi sai giá trị token. Ghi "không có doc lệch" nếu vậy.
- **Đổi behavior/contract/props** → sửa đúng đoạn doc mô tả sai cho khớp code mới (surgical, không viết lại toàn bộ).
- **`*_detailed_design.md` đổi bản chất** → bump `dd_version` (đã làm ở step-01 nếu reconstruct/đổi contract); đảm bảo header code khớp.
- **`ui_schema` JSON** → chỉnh field lệch (binding/props/token ref) cho khớp component mới.

## 2. Commit (theo `commit_mode`)
- `branch-commit` → verify pass (ATDD `mandatory` phải XANH) → `git add -A && git commit` trên `<branch>` trong worktree. **KHÔNG push. KHÔNG merge vào main.**
- `in-place-nocommit` → **KHÔNG commit**; để orchestration/user review. (Việc flip status file / báo cáo cuối do caller lo.)

## 3. Fix-report có cấu trúc (trả orchestration)
Xuất block gọn cho caller tiêu thụ:
- **unit** + **bug keys/id**
- **root-cause** (1-2 dòng)
- **files đã sửa** (repo/path)
- **ceremony đã áp**: lane / atdd_class / DD action (giữ|bump vN→vN+1|reconstruct v1→v2|flag) / code-review (có|self)
- **dd_version delta** (nếu có)
- **verify-level**: atdd-green | build-smoke | static-only | BLOCKER + chi tiết
- **review findings còn lại**
- **doc-sync**: đã sync (liệt kê doc) | deferred-TODO (liệt kê doc ứng viên) | không lệch
- **BLOCKER / ESCALATE** (nếu có): mandatory-ATDD thiếu test, Tier 3/4, WBS gap cần đặt id mới, file ngoài blast radius...

---

**DONE.** Engine dừng sau report. Không HITL, không hành động ngoài phạm vi bug (orchestration quyết bước tiếp: commit/merge/flip-status/demo).
