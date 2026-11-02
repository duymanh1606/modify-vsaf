# Step 02 — Fix qua engine + flip status (per-bug loop, autonomous)

**Persona:** Orchestrator per-bug — ủy quyền fix cho engine, cập nhật file bug.

**Mục tiêu:** Với mỗi bug đã duyệt trong plan (trừ NEEDS-INFO): gọi engine `NTAPP-bug-fix-engine` để fix + verify + doc-sync, rồi flip trạng thái bug → `Fixed`. Tự chạy tuần tự hết, không dừng (trừ R5/BLOCKER).

Lặp cho **từng bug** theo thứ tự severity giảm dần (Critical → Low).

---

## 1. Gọi engine `NTAPP-bug-fix-engine` (fix + verify + doc-sync)
Ưu tiên `/NTAPP-bug-fix-engine`; chưa symlink (cần `./scripts/bootstrap.sh --refresh`) → FALLBACK đọc `.agent/skills/NTAPP-bug-fix-engine/workflow.md` và làm theo. Truyền:
- `bug_context`: mô tả / expected / actual / ảnh + unit + repo + file ứng viên (từ step-01). Lane `jira` → mô tả lấy từ `description` trên Jira, ảnh lấy từ attachment đã tải về; lane `file` → block bug trong file.
- `lane` / `atdd_class` / `severity`: tín hiệu classify từ step-01 (§4b).
- `commit_mode = in-place-nocommit` — **KHÔNG commit** (R2); hook fire khi user commit sau.
- `doc_sync_mode = inline` — tuần tự 1 phiên → doc-sync ngay, an toàn (không tranh ghi như fanout).

Engine tự lo TOÀN BỘ logic (KHÔNG lặp lại ở đây): root-cause → DD gate → ATDD gate → fix tối thiểu → pre-commit → verify bậc cao nhất → self-review inline → doc-sync spec. Chi tiết mỗi gate + điều kiện escalate ở CEREMONY RESOLVER của engine. Engine trả **fix-report có cấu trúc**.

Bug trải nhiều unit/repo → gọi engine cho từng unit liên quan.

## 2. Flip trạng thái bug (R1 — chỉ đúng bug này)
Chỉ làm khi **có `bug_file`** (lane `file`, hoặc lane `jira` mà §1b tra ngược thấy entry). Lane `jira` không có file log → bỏ qua mục này, trạng thái chỉ cập nhật trên Jira ở step-03.

Từ fix-report của engine, cập nhật trong `bug_file` block của bug đang xử lý — sửa **chỉ** dòng trạng thái + thêm ghi chú fix (không đụng mô tả / bug khác):
```markdown
- **Trạng thái:** Fixed
- **Ghi chú fix (<date>):** <nguyên nhân + đã sửa gì — từ fix-report>. File: `<repo>/<path>`. Verify: <verify-level>. Ceremony: <lane / atdd_class>.
```
- Engine trả **BLOCKER** (mandatory-ATDD thiếu test xanh), **ESCALATE** (Tier 3/4 / WBS gap phải đặt id mới / file ngoài blast radius), hoặc R5 (không tự fix được): **GIỮ trạng thái cũ**, KHÔNG ghi `Fixed`; ghi `- **Ghi chú (<date>):** <lý do / câu hỏi>` và đưa vào report. Đi tiếp bug khác.

## 3. Tích lũy cho report cuối + soạn nội dung ghi Jira
Gom fix-report từng bug (unit → files đã sửa → verify-level → doc-sync đã làm → finding còn lại → BLOCKER/ESCALATE) làm đầu vào step-03.

Bug nào có `jira_key` **và** fix thành công → soạn luôn 6 giá trị dưới (step-03 dùng để ghi lên Jira, KHÔNG gọi API ở đây):

| Giá trị | Lấy từ |
|---|---|
| **Nguyên nhân** | root-cause engine xác định — sai ở đâu, vì sao sinh ra triệu chứng. Không phải mô tả lại triệu chứng. |
| **Ảnh hưởng** | phạm vi bị tác động: WBS unit + màn/API liên quan, blast radius, có ảnh hưởng dữ liệu cũ hay không. |
| **Giải pháp** | đã sửa gì (diễn giải bằng lời, kèm file/hàm), mức verify đạt được, có test chống tái diễn hay chưa. |
| **Due Date** | ngày hệ thống hôm nay, `YYYY-MM-DD`. |
| **Người chịu trách nhiệm** | `assignee` của issue **đọc ở step-01** (người đang fix) — KHÔNG phải reporter. Đọc ở step-01 vì step-03 sẽ assign lại cho reporter. |
| **Original Estimate** | tự tính theo bảng dưới. |

3 mục đầu viết bằng văn xuôi tiếng Việt, mỗi mục 1-3 câu, đủ để reporter đọc là hiểu — KHÔNG dán nguyên diff.

**Tính Original Estimate** (từ tín hiệu classify step-01 §4b — không hỏi user):

| Thành phần | Giá trị |
|---|---|
| base theo `lane` | `express` → 1h · `path-b` → 2h · `ad-hoc` → 4h |
| `atdd_class = mandatory` | +2h (phải viết test RED→GREEN) |
| fix chạm > 3 file **hoặc** > 1 repo | +2h |

Trần **8h** (= 1 MD). Tính ra > 8h → dùng `8h` và ghi chú trong report rằng phạm vi này đáng ra là story chứ không phải bug. Giá trị hiện ở bảng preview step-03 nên user sửa được trước khi ghi.

---

**Sau khi hết bug đã duyệt:** Read fully and follow `./steps/step-03-doc-sync-report.md`
