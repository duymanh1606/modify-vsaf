---
name: NTAPP-fix-bug
description: Use when the user wants still-open bugs analyzed and fixed — "fix bug", "sửa bug", "rà soát bug đang mở", "vá bug trong file bug", "fix bug jira TTCNSPQT-1234". Accepts TWO input sources — a bug log file (BUGS-<SLICE-ID>-<account>.md under NTAPP-output/Stage_1_Discovery/Bugs_Issues), or a Jira issue key / browse URL (reads the bug description + screenshots straight from Jira). Triages every bug whose status is Open / In Progress / Reopened, maps each to its WBS unit + owning code repo, fixes the code, flips status to Fixed, then syncs any spec-repo docs that drifted from the new code. When a bug carries a Jira link, also transitions that issue to Resolved and reassigns it to the Reporter (Type = Bug additionally requires Nguyên nhân / Ảnh hưởng / Giải pháp). Dual-repo (spec ↔ code). Does NOT auto-commit.
---

# Fix Bug (from bug log file)

## Overview
Rà soát mọi bug **đang mở** (`Open` / `In Progress` / `Reopened`), phân tích nguyên nhân, **fix code** ở code repo, đổi trạng thái bug → `Fixed`, rồi **đồng bộ tài liệu spec** đã lệch so với code mới.

**2 nguồn bug (`bug_source`):**

| Nguồn | Input | Mô tả bug đọc từ | Kết thúc |
|---|---|---|---|
| `file` | path `BUGS-<SLICE-ID>-<account>.md` | block bug trong file | flip `Fixed` trong file · **+ resolve Jira nếu entry có dòng `- **Jira:**`** |
| `jira` | mã Jira / URL browse (vd `jira TTCNSPQT-5067`) | **description + ảnh attachment trên Jira** | resolve Jira · **+ flip `Fixed` trong file nếu tra ngược thấy entry gắn đúng mã Jira đó** |

**Resolve Jira** = set `Nguyên nhân` / `Ảnh hưởng` / `Giải pháp` (bắt buộc với Type = `Bug`) → **assign lại cho Reporter** → transition sang `Resolved`. Chỉ chạy sau **1 HITL gate** ở step-03 và chỉ cho bug fix thành công.

**Nguyên tắc cốt lõi:** bug file là **đầu vào read-mostly** — chỉ được sửa **dòng trạng thái** (+ ghi chú fix) của đúng bug đang xử lý; KHÔNG đụng mô tả hay bug khác. Fix nằm ở **code repo**; doc-sync nằm ở **spec repo**. **KHÔNG tự commit** — dừng để user review.

**REQUIRED SUB-SKILL:** việc fix từng bug được ủy quyền cho engine **`NTAPP-bug-fix-engine`** (ceremony-adaptive: root-cause qua `superpowers-systematic-debugging` → DD gate → ATDD gate → fix → verify → self-review → doc-sync). Skill này là **intake adapter file-local** — không tự viết lại logic fix.

## When to use
- User đưa đường dẫn 1 file `BUGS-SLICE-NN-<account>.md` (hoặc mở sẵn trong IDE) và muốn fix các bug trong đó.
- User đưa **mã Jira** hoặc link browse — vd `jira TTCNSPQT-5067`, `http://jira.digital.vn/browse/TTCNSPQT-5067`.
- Cần rà bug đang mở → phân tích → vá → cập nhật lại tài liệu cho khớp code.

## When NOT to use
- Chỉ muốn **ghi nhận** bug mới → dùng `NTAPP-log-bug`.
- Chỉ muốn sinh/kiểm thử **testcase** cho bug đã vá (chống tái diễn) → dùng `ntapp-qa-pipeline-bugfix`.
- Feature mới theo WBS → `slice-loop` / `NTAPP-feature-design`.

## Inputs
| Input | Bắt buộc | Ghi chú |
|---|---|---|
| Nguồn bug | ✅ | **1 trong 2**: đường dẫn `BUGS-<SLICE-ID>-<account>.md` (mở sẵn trong IDE cũng được), HOẶC mã Jira / URL browse (nhiều mã cách nhau bằng dấu phẩy) |
| Phạm vi bug | mặc định | Xử lý status ∈ {`Open`, `In Progress`, `Reopened`}; bỏ `Fixed` / `Closed` |

Thiếu cả 2 nguồn → hỏi user (đừng tự đoán slice, đừng tự đoán mã Jira).

**Nhiều file / 1 slice:** `NTAPP-log-bug` đặt tên file theo account nên 1 slice có thể có nhiều file (`BUGS-SLICE-6-dinhtq8.md`, `BUGS-SLICE-6-dinhtq9.md`). User chỉ đưa mã slice → **KHÔNG glob `BUGS-<SLICE-ID>*.md`** (tiền tố: `SLICE-2` bắt luôn `SLICE-20/21/24`). Gọi `python3 {project-root}/hooks/lib/slice_paths.py --resolve <SLICE-ID> --json` rồi lấy `bug_files` — đã khớp theo ranh giới và chuẩn hoá zero-pad. Nhiều file → hỏi user chọn, hoặc xử lý hết nếu user nói "tất cả". Chi tiết mã thoát: `workflow.md` Bước 2. Mã bug là `<SLICE-ID>-<account>-BUG-NN` (vd `SLICE-20-dinhtq8-BUG-01`) — account nằm trong mã nên **mã bug duy nhất toàn project**, tra ngược ra file nguồn được ngay từ mã.

## Flow (1 HITL gate)
**Báo plan tổng thể → user duyệt → tự chạy hết.** Sau khi duyệt plan, fix tuần tự tất cả bug rồi doc-sync, không dừng giữa chừng (trừ khi gặp bug không thể tự fix — flag và bỏ qua).

## Workflow
Đọc đầy đủ và tuân theo: **`./workflow.md`** (chứa INITIALIZATION 3-layer + pipeline map + global rules). Tuyệt đối tuân thủ progressive disclosure: đọc **đúng một step file mỗi lần**.
