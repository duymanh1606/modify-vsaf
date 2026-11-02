# Bug-Fix Engine Workflow (ceremony-adaptive)

**Goal:** Fix đúng **một bug đã localize** trên một WBS unit, end-to-end, với mức ceremony vặn theo tín hiệu. Trả về **fix-report có cấu trúc** cho orchestration gọi nó.

**Your Role:** Bạn là **engine per-bug** — được gọi bởi một orchestration (NTAPP-fix-bug / bug-fix-batch). KHÔNG tự localize (caller đã làm), KHÔNG tự quyết concurrency/merge (orchestration lo). Chỉ nhận `bug_context` + tín hiệu, chạy 3 step, xuất report.

**Ngôn ngữ:** trả lời & viết report bằng **tiếng Việt** (thuật ngữ kỹ thuật giữ tiếng Anh).

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG (INITIALIZATION + CEREMONY RESOLVER + global rules + pipeline map). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại RỒI mới đọc step kế. State chuyển qua code + report, không qua giữ instruction trong context.

---

## INITIALIZATION (Configuration Resolution)

Caller thường đã resolve path và truyền qua `bug_context`. Nếu invoke standalone, resolve tối thiểu:

### Bước 0 — `{spec_repo_root}`
Walk up từ cwd: thấy `_bmad/` → `{spec_repo_root}`; else thấy `NTAPP-output/` → `{spec_repo_root}`; else fallback `cwd` + log warning.

### Bước 1 — Code repo(s)
Dual-repo: code KHÔNG nằm trong spec repo. Resolve repo sở hữu unit từ (theo thứ tự): (a) field repo trong `bug_context`; (b) `NTAPP-output/Stage_5_Build_Verify/bug-batches/_unit-path-map.yaml` (`containers[].repo`); (c) additional working dirs đang mở / sibling dirs chứa source (`src/`, `package.json`, `pom.xml`, `build.gradle`, `go.mod`, ...). **KHÔNG hardcode tên repo** — luôn resolve runtime.

### Bước 2 — Paths chuẩn (spec repo)
| Biến | Giá trị |
|---|---|
| `wbs` | `{spec_repo_root}/NTAPP-output/Stage_2_Architecture/project_wbs.md` |
| `techspec_dir` | `{spec_repo_root}/NTAPP-output/Stage_3_Specs/techspec/` |
| `dd_dir` | `{spec_repo_root}/NTAPP-output/Stage_4_Design/detailed_design/` |
| `ui_schema_dir` | `{spec_repo_root}/NTAPP-output/Stage_4_Design/ui_schema/` |
| `ds_root` | `{spec_repo_root}/NTAPP-output/design-system/` |
| `build_verify_dir` | `{spec_repo_root}/NTAPP-output/Stage_5_Build_Verify/` |
| `slices_dir` | helper trả về (`slices_dir`); mặc định `{spec_repo_root}/NTAPP-output/Stage_2_Architecture/slices/` |
| `date` | ngày hệ thống, `YYYY-MM-DD` |

> ⚠️ **`slices_dir` KHÔNG ghép tay — gọi helper:**
>
> ```
> python3 {project-root}/hooks/lib/slice_paths.py --resolve <SLICE-ID> --json
> ```
> *(Windows: dò `py -3` → `python3` → `python`.)* Trả về `slices_dir`, `bugs_dir`, `assets_dir`, `slice_files[]`, `bug_files[]`, `warnings[]`.
>
> Bảng này từng ghi `Stage_5_Build_Verify/slices/` — **thư mục không tồn tại**; slice thật ở `Stage_2_Architecture/slices/`. Helper còn khớp mã slice theo **ranh giới** (`SLICE-2` không bắt `SLICE-20`) và chuẩn hoá zero-pad (`SLICE-06` ↔ `SLICE-6`), đồng thời nhận cả bố cục phẳng lẫn thư mục feature.
>
> **Mã thoát:** `0` = tra được (danh sách rỗng nghĩa là *thật sự không có*); `3` = **không tra được**, DỪNG và đọc `warnings`; `2` = mã slice sai dạng.

---

## CEREMONY RESOLVER (bất biến — trái tim của engine)

Trước khi chạm code, quyết mức ceremony từ tín hiệu. Thiếu tín hiệu → classify tại chỗ (xem note). **Mặc định an toàn: mơ hồ → nghiêng NẶNG; critical-domain LUÔN test-first bất kể `lane`.**

> **`severity` KHÔNG phải trục gate** — không dòng nào dưới đây key trên nó; chỉ dùng để sắp thứ tự fix (Critical→Low) + suy `lane` khi thiếu. Đừng nhầm `severity=Critical` với **critical-domain** (trigger **B1** của `atdd_class`: auth/tiền/RBAC/PII) — bug Critical-severity nhưng UI-style thuần vẫn có thể `express`.

| Gate | Bật đầy đủ khi | Nhẹ / skip khi |
|---|---|---|
| **root-cause** | **LUÔN** (superpowers-systematic-debugging) | — |
| **DD gate** | DD thiếu **và** (fix chạm contract/behavior mô tả bởi DD **hoặc** `commit_mode=branch-commit` mà Rule 3 đang active) → **reconstruct DD v1 as-is → fix → bump v2**. DD có + fix đổi contract → update DD + bump version | DD có + fix conform → **giữ version**. DD thiếu + fix internal-only + `in-place-nocommit` → chỉ giữ header nhất quán + flag report (KHÔNG reconstruct full) |
| **ATDD gate** | `atdd_class=mandatory` → framework guard + **test-first RED→GREEN** (critical-domain thiếu test = **BLOCKER**, KHÔNG bypass) | `atdd_class=optional` → khuyến nghị regression test, **KHÔNG chặn commit** |
| **verify** | LUÔN, ở **bậc cao nhất có sẵn**: slice ATDD/demo (nếu unit thuộc slice có test) → per-unit test/build → static. Ghi TRUNG THỰC bậc đã verify | (không hard-require slice) |
| **code-review** | INLINE self-review theo rubric (KHÔNG gọi `/bmad-code-review`: skill đó có chuỗi HALT wait-for-human + persist theo story → **treo/mất finding trong headless & fanout**). `lane≠express` → self-review đầy đủ | `lane=express` → self-review nhanh. Finding LUÔN xuất trong fix-report; orchestration lo persist |
| **pre-commit** | `commit_mode=branch-commit` → enforce 9 rule (`SKIP_PRECOMMIT` CHỈ cho diện escalate) | `commit_mode=in-place-nocommit` → giữ header `id:`+`dd_version:` nhất quán để commit sau của user pass Rule 1 |

**Classify tại chỗ nếu thiếu:**
- `atdd_class`: đối chiếu 5 trigger Mandatory ATDD (canonical `docs/Process/Manual_phase_1.md` §5.1) — A1 cross-system · A2 multi-actor/stateful · A3 async/resilience · B1 critical-domain (auth/tiền/RBAC/PII) · B2 destructive. Match ≥1 → `mandatory`.
- `lane`: suy từ severity + scope (trivial + không đổi contract → express; unit có DD, chỉ fix/refactor → path-b; còn lại → ad-hoc).

**Escalate (KHÔNG bịa):** unit chưa localize chắc (Tier 3/4) → `needs-investigation`, KHÔNG bịa DD / KHÔNG đoán unit. WBS gap (unit chắc nhưng không có dòng nào trong `project_wbs.md`) → KHÔNG bịa id mới: id có sẵn trong header → thêm dòng đối chiếu DRAFT; phải đặt tên mới → escalate `/ntapp-architecture-design`.

---

## GLOBAL RULES (mọi step)

- **R1 — Root-cause trước khi fix:** tuân `superpowers-systematic-debugging`. Cấm fix mò triệu chứng khi chưa chỉ ra nguyên nhân.
- **R2 — Blast radius:** fix đúng vùng đã localize; chạm hot node → kiểm consumer trong `ripples` không vỡ (giữ signature/contract). Phải chạm file NGOÀI blast radius / của unit khác → DỪNG, ghi ESCALATE (dấu hiệu localize/grouping thiếu), KHÔNG tự lan sang unit khác.
- **R3 — Code là nguồn sự thật sau fix:** doc-sync chỉnh doc theo code mới (surgical); DD đổi bản chất → bump `dd_version` + đồng bộ header code.
- **R4 — Không đổi hành vi ngoài phạm vi bug** (Simplicity First — không refactor thừa).
- **R5 — Secret:** không in/log/commit secret.
- ⛔ Đọc đúng một step file mỗi lần.

---

## PIPELINE MAP (neo thường trực)

| # | Step file | Mục tiêu |
|---|---|---|
| 01 | steps/step-01-rootcause-gates.md | root-cause[luôn] → DD gate[dial] → ATDD gate[dial] (quyết định TRƯỚC khi chạm code) |
| 02 | steps/step-02-fix-verify-review.md | fix tối thiểu → pre-commit[dial] → verify[bậc cao nhất] → code-review[dial] |
| 03 | steps/step-03-close.md | doc-sync[inline\|deferred] → commit[commit_mode] → xuất fix-report |

Chuỗi: **01 → 02 → 03 (terminal)**. Không HITL gate trong engine (gate nằm ở orchestration).

---

## LAUNCH
Sau INITIALIZATION + CEREMONY RESOLVER (chốt mức mỗi gate): **Next:** Read fully and follow `./steps/step-01-rootcause-gates.md`
