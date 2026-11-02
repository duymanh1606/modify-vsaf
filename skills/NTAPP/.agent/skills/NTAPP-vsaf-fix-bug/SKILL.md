---
name: NTAPP-vsaf-fix-bug
description: 'Chạy workflow NTAPP/bug-fix-batch qua VSAF engine — batch bug-fixing có hệ thống cho 1..N bug từ file BUGS-*.md: localize + gom nhóm parallel-safe → HITL duyệt plan → fix SONG SONG trên branch/worktree riêng qua NTAPP-bug-fix-engine (branch-commit) → verify + đề xuất merge order. Usage: /NTAPP-vsaf-fix-bug <bug file spec>. Ví dụ: /NTAPP-vsaf-fix-bug --all | /NTAPP-vsaf-fix-bug SLICE-01,SLICE-02 | /NTAPP-vsaf-fix-bug NTAPP-output/Stage_1_Discovery/Bugs_Issues/BUGS-SLICE-01.md. Dùng khi người dùng nói "fix batch bug", "chạy bug-fix-batch", "fix nhiều bug song song", "vá cả loạt bug trên branch riêng". KHÔNG merge vào main, KHÔNG push, KHÔNG flip status tự động (read-mostly). Tiền điều kiện: WBS locked + có file BUGS-*.md (sinh bởi NTAPP-log-bug).'
---

# VSAF Fix Bug (batch)

Chạy `NTAPP/bug-fix-batch` qua VSAF engine — lane bug-fixing có hệ thống, bỏ qua feature-triage, fix song song 1..N bug trên branch riêng.

8 node: `plan-bugs → approve-plan (HITL) → resolve-groups → fix-foundation → fix-parallel → fix-serial → integrate-verify → batch-demo`.

**Ba đợt fix, không phải hai.** `fix-foundation` (`mc:1` — hot node phải land trước) → `fix-parallel` (`mc:5` — chỉ nhóm có blast radius rời nhau) → `fix-serial` (`mc:1` — nhóm phụ thuộc nhau). Nhóm phụ thuộc **bắt buộc** ở đợt 3: engine bắn tới `max_concurrency` item cùng lúc và không chờ item trước xong, nên `mc:1` là rào chắn duy nhất — để chung với đợt 2 thì `git worktree add -B b2 <path> b1` vẫn trả về 0 khi `b1` chưa có commit, và nhóm sau lặng lẽ base về `main`, nuốt mất fix của nhóm trước.

Một nhóm hỏng sẽ dừng cả batch tại đó (nhóm sau rebase lên nó — chạy tiếp là fix trên nền sai). Bằng chứng còn lại nằm ở `<batch>/reviews/<gid>.md`: mọi node fix bắt buộc ghi file này trước khi kết thúc, kể cả khi hỏng.

Node `plan-bugs` ủy quyền intake cho skill `NTAPP-fix-bug` ở **chế độ plan-only headless** (parse `BUGS-*.md` → localize → classify), rồi gom nhóm parallel-safe; các node fix gọi engine dùng chung `NTAPP-bug-fix-engine` per-bug (`commit_mode=branch-commit`, `doc_sync_mode=deferred`).

## Khi nào dùng skill này vs `NTAPP-fix-bug`

| | `/NTAPP-fix-bug` (skill trực tiếp) | `/NTAPP-vsaf-fix-bug` (workflow này) |
|---|---|---|
| Nguồn | 1 file `BUGS-<SLICE>-<account>.md` | 1..N file `BUGS-*.md` |
| Fix | tuần tự, **in-place-nocommit** (không commit) | **song song trên branch/worktree riêng**, branch-commit |
| Gom nhóm | không | parallel-safe (foundation / parallel / serial / needs-investigation) |
| Đầu ra | code sửa + flip status `Fixed` tại chỗ | branch chưa merge + đề xuất merge order (HITL merge thủ công) |

Muốn fix nhanh 1 file, ngay tại chỗ → `/NTAPP-fix-bug`. Muốn fix cả loạt bug cách ly nhau trên branch riêng, có gate duyệt plan → skill này.

## Instructions

1. **workflow** = `NTAPP/bug-fix-batch`
2. **args** = bug file spec lấy từ user input — 1 trong 4 dạng (node `plan-bugs` tự resolve):
   - **`--all`** — mọi `BUGS-*.md` dưới `bugs_dir`, **kể cả trong thư mục con** (`rg --files --glob 'BUGS-*.md' <bugs_dir>`; glob shell không xuống thư mục con nên sẽ hụt khi file bug chuyển vào `<bugs_dir>/<feature>/`)
   - **slice id(s)** — vd `SLICE-01` hoặc `SLICE-01,SLICE-02` → **KHÔNG glob `BUGS-<slice>*.md`**. Với mỗi mã, gọi `python3 {project-root}/hooks/lib/slice_paths.py --resolve <slice> --json` và lấy `bug_files` (log-bug đặt tên theo account nên 1 slice có thể nhiều file)
   - **đường dẫn file** — path tới `BUGS-*.md` (nhiều path cách nhau bằng space/comma)
   - trống → mặc định coi như `--all`
3. **projectPath** = thư mục gốc **spec repo** hiện tại (nơi chứa `NTAPP-output/`)

> ⚠️ **Vì sao mã slice không được dùng làm glob.** `BUGS-SLICE-2*.md` khớp theo **tiền tố**, nên `SLICE-2` bắt luôn `BUGS-SLICE-20.md`, `-21`, `-24` — batch fix bốn slice trong khi user chỉ yêu cầu một, và không có gì báo. Thêm nữa, mã user gõ thường zero-pad (`SLICE-01`) còn file trên đĩa thì không (`BUGS-SLICE-1.md`), nên cùng một glob vừa **bắt thừa** vừa **bắt hụt** tuỳ số. `slice_paths.py` khớp theo ranh giới và chuẩn hoá zero-pad một chiều; nó là nơi duy nhất giữ luật này.
>
> **Mã thoát:** `0` = tra được (rỗng nghĩa là *thật sự không có bug*); `3` = **không tra được** (thư mục không tồn tại) → DỪNG, đừng coi là "slice sạch"; `2` = mã slice sai dạng.

Thực hiện đúng theo protocol trong [`../NTAPP-vsaf-run/workflow.md`](../NTAPP-vsaf-run/workflow.md) từ Step 2.

## HITL gate (node `approve-plan`)

Workflow **DỪNG** sau khi `plan-bugs` sinh plan. Đây là cổng xác nhận **duy nhất** trước khi các node fix chạm code thật, nên đừng ký lướt. Nhắc user mở 3 file trong batch dir (`bug-grouping-plan.md`, `bug-groups.yaml`, `conflict-matrix.md`), chỉnh gom nhóm nếu cần, rồi duyệt bằng **đúng lệnh mà cổng in ra** — chữ ký gắn với checksum của bản plan, không phải một file rỗng:

```
echo "<checksum cổng in ra>" > "<batch_dir>/APPROVED"
/NTAPP-vsaf-resume <runId>
```

Batch dir = nội dung `NTAPP-output/.current-bug-batch`. Chưa có `APPROVED` → workflow đứng tại gate. Sửa `bug-groups.yaml` sau khi ký → checksum đổi → cổng đóng lại và bắt ký lại; đó là chủ ý, nó chặn trường hợp chạy lại cùng ngày rơi trúng batch dir cũ và chữ ký lần trước tự duyệt cho bản plan chưa ai đọc.

## Sau khi hoàn tất

- **Close point** = node `batch-demo`. Đọc `bug_batch_integration.md` → tóm tắt "N bug → M group đã fix (K song song, F foundation), X need-investigation" + BLOCKER (nếu có).
- **KHÔNG merge vào main / KHÔNG push / KHÔNG flip status tự động.** Hướng dẫn user thủ công:
  - Review + merge theo MERGE ORDER (foundation trước), dọn worktree sau merge (`git -C <repo> worktree remove <wt>`).
  - Cập nhật trạng thái bug (`Open`/`In Progress`/`Reopened` → `Fixed`) trong file `BUGS-*.md` **sau khi merge** (workflow read-mostly, tránh spec lệch code chưa land).
  - Bug `needs-investigation` (chưa localize được) → bổ sung route/file/stack vào `BUGS-*.md` rồi chạy lại skill này cho batch phụ.
- **Cross-batch ledger**: mỗi batch append bài học vào `NTAPP-output/ledgers/bug-fix-ledger.md` (engine inject lại làm context cho batch sau).

> Slash command chưa xuất hiện sau khi tạo skill → chạy `./scripts/bootstrap.sh --refresh` để symlink `.agent/skills/` sang `.claude/skills/`.
