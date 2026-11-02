# Step 01 — Root-cause + DD gate + ATDD gate (quyết định TRƯỚC khi chạm code)

**Persona:** Dev điều tra nguyên nhân + chốt gate cần chạy cho bug này.

**Mục tiêu:** Xác định nguyên nhân gốc, rồi áp CEREMONY RESOLVER để quyết DD gate + ATDD gate ở mức đúng — TRƯỚC khi sửa một dòng code nào.

---

## 1. Root-cause (LUÔN — `superpowers-systematic-debugging`)
- Đọc kỹ file code đã localize trong `bug_context`. Xác minh giả thuyết nguyên nhân bằng đọc code thật (data flow / state / style cascade), KHÔNG sửa khi chưa chỉ ra được dòng/nguyên nhân.
- Đối chiếu `expected` vs `actual` + ảnh bug (nếu có). Bug có route/step → reproduce trước khi fix (mượn self-reproduce của `bug-report-jira` nếu cần).
- Bug UI typography/spacing/màu: tra token chuẩn trong `ds_root/master_token.json` + cách unit khác dùng, để fix về đúng token chung (không chế giá trị mới).

## 2. DD GATE (theo resolver — quyết định version/contract)
Với unit đã localize chắc (Tier 1/2):

- **DD đã có** (`dd_dir/<unit>_detailed_design.md` tồn tại) → đọc DD, fix cho conform contract/behavior mô tả.
  - Fix làm code CONFORM DD đang có → **GIỮ nguyên `dd_version`**.
  - Fix phát hiện DD SAI/THIẾU (DD đang mô tả chính hành vi lỗi) → update mục contract/behavior của vùng bug thành hành vi đúng + **bump `vN→vN+1`** trong DD, đồng bộ header `dd_version` file code.
  - Unit thuộc slice đã chạy Stage 4/5 → thường đã có DD + story + ATDD → rơi vào nhánh này; tái dùng ATDD/demo slice để verify ở step-02.

- **DD chưa có** (unit CÓ trong WBS nhưng chưa chạy Stage 4 — hay gặp legacy):
  - Nếu resolver quyết **reconstruct** (fix chạm contract/behavior mô tả bởi DD, HOẶC `commit_mode=branch-commit` mà Rule 3 active) → làm 2 nhịp, KHÔNG bypass:
    (i) **DD v1 AS-IS:** reconstruct DD từ code HIỆN CÓ, mô tả contract/state/behavior ĐANG CHẠY (dùng lại code THẬT, KHÔNG thiết kế lại) — snapshot trung thực, CÓ THỂ còn hành vi bug. Ưu tiên gọi `/NTAPP-feature-design <unit>` headless (không hỏi HITL); skill chưa symlink → viết DD theo template của nó (đọc code unit + WBS + consumer trong `ripples`). Ghi `dd_dir/<unit>_detailed_design.md` với `dd_version: v1`.
    (ii) **FIX + bump v2:** sửa mục contract/behavior của VÙNG BUG thành hành vi ĐÚNG (target) mà code sau-fix thoả; bump `dd_version: v2` trong DD + header code. Delta v1→v2 = audit trail (bug as-is → đúng ra sao).
  - Nếu resolver quyết **nhẹ** (fix internal-only + `in-place-nocommit`, không đụng contract) → KHÔNG reconstruct full: giữ header `id:`+`dd_version:` nhất quán, ghi flag "DD thiếu, fix internal-only, chưa reconstruct" vào report cho user quyết sau.

- **Tier 3/4 chưa định vị** → KHÔNG viết DD giả, KHÔNG đoán unit → đẩy `needs-investigation` + báo cần bổ sung route/file. DỪNG bug này (report escalate).

- **WBS gap** (unit chắc nhưng không có dòng nào trong `wbs`): id đã có trong header code → thêm 1 dòng đối chiếu DRAFT (copy đúng id + mô tả 1 dòng + container), đánh dấu review ở close-out; phải đặt tên unit mới → escalate `/ntapp-architecture-design`, KHÔNG commit id tự chế.

## 3. ATDD GATE (theo resolver — chống regression mien nhạy cảm)
- `atdd_class` đã có (caller gán) → dùng; chưa có → classify tại chỗ (5 trigger §5.1, xem CEREMONY RESOLVER).
- **`mandatory`** → BẮT BUỘC test-first, đúng thứ tự (test TRƯỚC fix):
  (a) **Framework guard:** detect config test của module/stack (FE: `playwright.config.*`/`cypress.config.*`; BE: `conftest.py`/`src/test/`/`go.mod` + `*_test.go`/`.rspec`). THIẾU → gọi `/bmad-testarch-framework` scaffold TRƯỚC (nếu không, `bmad-testarch-atdd` preflight HALT im lặng trong headless).
  (b) Viết 1 **regression test** tái hiện bug qua `/bmad-testarch-atdd` (story = `<unit>`) → test PHẢI FAIL (RED) trước khi fix. Unit thuộc slice đã có ATDD → THÊM/MỞ RỘNG case, KHÔNG viết lại.
  (c) Ghi nhớ: fix ở step-02 phải làm test XANH (GREEN). Critical-domain thiếu test phụ → **BLOCKER** (khác DD: DD reconstruct được, test mandatory thì KHÔNG bypass).
- **`optional`** → khuyến nghị viết regression test, KHÔNG chặn.

---

**Next:** Read fully and follow `./steps/step-02-fix-verify-review.md`
