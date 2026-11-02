---
name: NTAPP-jira-subtask-creator
description: Tự động tạo Jira Sub-task hàng loạt từ danh sách đầu việc người dùng nhập (Sprint, tên việc, ET, Task/Story cha). Use when the user wants to create Jira sub-tasks, bulk-create subtasks for a sprint, paste a sprint work list, or mentions "tạo sub-task", "tạo subtask Jira", "sprint subtask". Jira Server tại http://jira.digital.vn, credential từ env.md.
user-invocable: true
argument-hint: <danh sách đầu việc, mỗi dòng "Tên việc - ET - Task/Story cha">
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# /NTAPP-jira-subtask-creator — Tạo Jira Sub-task hàng loạt cho Sprint

## Arguments

`$ARGUMENTS` — danh sách đầu việc (paste inline) hoặc đường dẫn file chứa danh sách.
Nếu rỗng, yêu cầu người dùng nhập danh sách theo Input Format bên dưới.

## Mục tiêu

Từ danh sách đầu việc dạng văn bản, tự động:
parse → xác định Sprint → xác định Parent → quy đổi & chia ET → tạo Sub-task qua Jira REST API → trả về bảng kết quả.

---

## Bước 0 — Chuẩn bị credential (BẮT BUỘC làm trước)

1. File `env.md` mặc định ở `C:\Users\dinhtq7\Documents\.env\env.md`. Script tự dò các vị trí: thư mục hiện tại → thư mục skill → `~\Documents\.env\env.md` → `~\env.md`. Có thể chỉ định rõ qua `--env "<path>"`.
2. Nếu **không** tìm thấy `env.md`: dừng lại, đọc `env.example.md` trong thư mục skill, hướng dẫn người dùng tạo `env.md` rồi mới chạy tiếp. KHÔNG đoán credential.
3. Mọi lệnh gọi API thực hiện qua script `jira_subtask.py` (đặt cùng thư mục skill). Block Jira trong env.md được nhận diện qua URL chứa `jira.digital.vn`, dùng `Username`/`Pass` (basic auth) hoặc `token` (Bearer PAT).
4. **Project key**: skill cần project Jira. Nếu người dùng chưa nêu, hỏi project key trước khi tạo issue. Truyền qua `--project <KEY>`. (Gợi ý: các việc `[Nền tảng App]` thường thuộc project `TTCNSPQT` — vẫn nên xác nhận với người dùng.) Khi `find-parent`, nên kèm `--project` để thu hẹp kết quả, tránh trùng tên ở project khác.

---

## Input Format

```text
Sprint: 5.2.26

1. [Nền tảng App] Họp hành sprint 5.2.26 - 2d - [Nền tảng App] Họp hành Sprint 5.2.26
2. AI agent business-management-system - 6h - [Nền tảng App] Công việc khác Sprint 5.2.26
3. Check xử lý lỗi đối soát tập trung
4. [Nền tảng App] Quy trình Sprint 5.2.26 - 2h - [Nền tảng App] Quy trình Sprint 5.2.26
```

Mỗi dòng: `<Tên công việc> - <ET> - <Task/Story cha>`
- `<ET>` và `<Task/Story cha>` đều **tùy chọn**.
- Bỏ qua số thứ tự đầu dòng (`1.`, `2.` …) khi lấy tên việc.

---

## Rules

### Rule 1 — Sprint Label
Tìm `SprintCode` từ dòng `Sprint: <code>` hoặc từ chuỗi `Sprint <code>` trong tên việc.
Nếu không xác định được → **dừng, hỏi người dùng** Sprint code.
Mọi sub-task và parent tạo mới đều gắn `Labels = ["<SprintCode>"]`.

### Rule 2 — Parent Task
Mỗi Sub-task bắt buộc thuộc một Story/Task. Parent Summary = phần thứ 3 sau dấu `-` của dòng (nếu có).

### Rule 3 — Default Parent
Nếu dòng không có Parent Summary → dùng mặc định:
`[Nền tảng App] Công việc khác Sprint <SprintCode>`

### Rule 4 — Find Parent First
Trước khi tạo Sub-task phải tìm Parent bằng:
```bash
python jira_subtask.py find-parent --env <env> --summary "<Parent Summary>"
```
Script trả JSON danh sách ứng viên (key, summary, issuetype). Ưu tiên **Story** trước **Task**.
Nhiều kết quả → chọn issue có summary **khớp nhất** với Parent Summary (so khớp theo phán đoán).

### Rule 5 — Create Parent When Missing
Nếu `find-parent` không trả ứng viên phù hợp → tạo Task mới làm parent:
```bash
python jira_subtask.py create-issue --env <env> --type Task --summary "<Parent Summary>" --labels <SprintCode>
```
Dùng key vừa tạo làm Parent.

### Rule 6 — ET Conversion (1 MD = 8 giờ)
| Input | MD | Giờ Jira |
|------|------|------|
| 1h | 0.125 | 1h |
| 2h | 0.25 | 2h |
| 4h | 0.5 | 4h |
| 8h / 1d | 1 | 8h |
| 16h / 2d | 2 | 16h |
| Nd | N | (N×8)h |
| Xh | X/8 | Xh |

Quy đổi ET đầu vào ra **MD**. Khi gọi script, truyền estimate dạng **giờ Jira** = `MD × 8` (ví dụ 2MD → `--et 16h`, 1MD → `--et 8h`, 0.5MD → `--et 4h`).
Nếu một dòng **không có ET** → tạo Sub-task không truyền `--et`.

### Rule 7 — Split Large Work (mỗi Sub-task ≤ 2MD)
Nếu ET > 2MD, chia thành nhiều Sub-task ≤ 2MD, đặt tên `"<Tên việc> - <n>"`.
- 4MD → 2MD + 2MD (2 sub-task)
- 5MD → 2MD + 2MD + 1MD (3 sub-task)
- 6MD → 2MD + 2MD + 2MD (3 sub-task)
Quy tắc: lấy phần nguyên `floor(MD/2)` sub-task mỗi cái 2MD, phần dư (>0) thêm 1 sub-task. Nếu ET ≤ 2MD và có ET → 1 sub-task, không thêm hậu tố số.

### Rule 8 — Create Sub-task
```bash
python jira_subtask.py create-subtask --env <env> --parent <PARENT_KEY> \
  --summary "<SUBTASK_NAME>" --labels <SprintCode> --et <16h|8h|...> \
  [--fields-json '<JSON field bắt buộc thêm>'] [--assignee <user>] [--no-assignee]
```
**Assignee mặc định = chính người dùng** (lấy username từ env.md, hoặc `/myself`). Muốn gán người khác dùng `--assignee <user>`; muốn bỏ trống dùng `--no-assignee`.

### Rule 9 — Required custom fields + ngày (theo project)
**Tự suy ra `Start Date` + `Due Date` từ mã sprint, rồi cho người dùng confirm hoặc tự nhập** (thay vì hỏi thẳng). Luôn hỏi thêm **`Ngày nghỉ` (nếu có)**.

**Suy ngày từ mã sprint** — chạy trước khi tạo issue:
```bash
python jira_subtask.py sprint-dates --sprint <SprintCode>
```
Script trả JSON `{"start_date","due_date","weeks",...}`. Quy tắc lịch (đã encode trong script, không tính nhẩm):
- Mã sprint `M.N.YY` (vd `7.1.26` = tháng 7, sprint 1, năm 2026). 1 tháng có 2 sprint, không tính T7/CN.
- **Sprint 1** (`*.1.*`): Start = thứ Hai của tuần chứa ngày 1 của tháng; Due = thứ Sáu tuần thứ hai (2 tuần).
- **Sprint 2** (`*.2.*`): Start = thứ Hai kế tiếp sau Sprint 1; Due = thứ Sáu cuối cùng của tháng (2 hoặc 3 tuần).

**Trình bày cho người dùng confirm:** in ngày suy ra (`Start` / `Due`) và hỏi "OK dùng ngày này, hay nhập ngày khác?". Nếu user nhập tay → dùng giá trị của user. Đây là giá trị dùng cho `duedate`, `customfield_12115` (Start Date) và `--start-date` khi log work.

**Câu hỏi ngày nghỉ (bắt buộc hỏi mỗi lần chạy):** "Trong khoảng log work có ngày nào nghỉ không? (vd `nghỉ sáng 1/7/2026`, `nghỉ ngày 2/7/2026`) — không có thì bỏ qua." Người dùng khai tự nhiên → chuyển thành `--days-off-json` (xem Rule 10). Không có → không truyền `--days-off-json`.

Một số project bắt buộc field riêng. **Project `TTCNSPQT`:**
- `duedate` (Due Date, **bắt buộc**) — `YYYY-MM-DD`.
- `customfield_12115` (Start Date) — `YYYY-MM-DD`.
- `customfield_15200` — "Vai trò - Công đoạn", **cascading** (cha → con). **Phải hỏi người dùng Vai trò (cha).**
  - Vai trò (cha): `PO, SA, BA, DEV CORE, DEV APP, DEV WEB, TEST, PM`.
  - **Công đoạn (con): mặc định `none`** — KHÔNG set con, chỉ set cha. Jira chấp nhận cascading chỉ có cha. **Không hỏi công đoạn.** Chỉ thêm con khi người dùng **chủ động** chỉ định.

Truyền qua `--fields-json`. Mặc định (chỉ Vai trò, không Công đoạn):
```bash
--fields-json '{"duedate":"2026-05-30","customfield_12115":"2026-05-29","customfield_15200":{"value":"SA"}}'
```
Khi người dùng chỉ định công đoạn, thêm `"child"`:
```bash
--fields-json '{... ,"customfield_15200":{"value":"SA","child":{"value":"Meeting"}}}'
```

**Khi chạy:** trước khi tạo issue, nếu project có field bắt buộc chưa biết giá trị → hỏi người dùng. Tự phát hiện field bắt buộc + giá trị hợp lệ bằng createmeta:
```bash
python -X utf8 -c "import jira_subtask as j; b,a,_=j.load_jira_credentials(r'<env>'); import json; print(json.dumps(j.api_request(b,a,'GET','/rest/api/2/issue/createmeta?projectKeys=<KEY>&issuetypeNames=Sub-task&expand=projects.issuetypes.fields'),ensure_ascii=False))"
```
Lưu ý: trên Windows luôn chạy Python với `-X utf8` khi in tiếng Việt để tránh lỗi cp1252.

### Rule 10 — Log work sau khi tạo (≤ 8h/ngày, tuần tự)
Sau khi tạo xong **tất cả** sub-task, log work cho chúng:
```bash
python jira_subtask.py distribute-worklog --env <env> \
  --start-date <Start Date YYYY-MM-DD> \
  --tasks-json '[{"key":"APP-124","hours":16},{"key":"HOP-1","hours":6,"maxPerDay":2}]'
```
- `hours` = ET của sub-task tính theo **giờ** (= MD × 8). Truyền các sub-task **theo đúng thứ tự** tạo.
- Script lấp đầy từng ngày: tổng **không quá 8h/ngày** (`--hours-per-day`), hết 8h thì sang ngày kế. Log **lần lượt** cho tới khi hết ET tất cả task.
- Mặc định **bỏ qua T7/CN** (dùng `--include-weekends` nếu muốn log cả cuối tuần). Giờ bắt đầu mỗi ngày mặc định `09:00`, timezone `+0700`.

**⚠️ Task họp (summary chứa "họp"/"họp hành"/"meeting"): KHÔNG dồn vào 1 ngày.**
Đặt `"maxPerDay": 2` cho các task họp để rải ~2h/ngày qua nhiều ngày. Các task khác vẫn lấp đầy phần còn lại của ngày (tổng vẫn ≤ 8h/ngày).
- Ví dụ: HOP=6h (maxPerDay 2) + DEV=8h, start 2026-06-01 → 01/06: HOP 2h + DEV 6h · 02/06: HOP 2h + DEV 2h · 03/06: HOP 2h.

**Ngày nghỉ (tùy chọn — hỏi người dùng):** khi log work bỏ qua ngày nghỉ. Truyền `--days-off-json`:
```bash
--days-off-json '[{"date":"2026-05-20","off":"full"},{"date":"2026-05-29","off":"morning"}]'
```
- `off`: `full` = nghỉ cả ngày (bỏ qua như T7/CN) · `morning` = nghỉ sáng (ngày đó chỉ log **4h buổi chiều**, bắt đầu 13:00) · `afternoon` = nghỉ chiều (chỉ log **4h buổi sáng**).
- Có thể không có ngày nghỉ → bỏ `--days-off-json`.

**Kiểm tra worklog đã log tay từ trước (mặc định BẬT):** trước khi log vào mỗi ngày, script query tổng giờ user hiện tại đã tự log tay trên **mọi issue** trong ngày đó, rồi **trừ vào trần 8h/ngày**.
- Ngày đã có 4h → chỉ log thêm 4h (bắt đầu sau phần đã log).
- Ngày đã có ≥ 8h → bỏ qua, không log thêm.
- Kết hợp với nửa ngày nghỉ: trần ngày đó = 4h, trừ tiếp phần đã log.
- Tắt kiểm tra bằng `--ignore-existing-worklog` (khi muốn log nhanh, chấp nhận có thể vượt trần).

**Ngày nghỉ (khai tự nhiên):**
- Người dùng có thể khai tự nhiên, kể cả định dạng `D/M/YYYY` ("nghỉ ngày 2/7/2026", "nghỉ sáng 1/7/2026") → model tự chuyển thành JSON trên với `date` dạng `YYYY-MM-DD` (`sáng`→morning, `chiều`→afternoon, không nói rõ→full). Ví dụ: `nghỉ sáng 1/7/2026, nghỉ ngày 2/7/2026` → `[{"date":"2026-07-01","off":"morning"},{"date":"2026-07-02","off":"full"}]`.

### Rule 11 — Close task đã log đủ ET
Sau khi log work xong, task nào đã log **đủ full ET** (remaining ~0) thì **close** luôn. Bật bằng `--close-when-done` ngay trong `distribute-worklog`:
```bash
python jira_subtask.py distribute-worklog --env <env> \
  --start-date <YYYY-MM-DD> --tasks-json '[...]' --close-when-done
```
- Script tự dò transition đóng (tên/trạng thái đích chứa `close`/`done`/`resolve`/`hoàn thành`/`đóng`). Workflow **nhiều bước** cũng xử lý được: nếu chưa lộ transition đóng, tự đi qua transition trung gian (In Progress) rồi đóng.
- Chỉ đóng task đã log đủ ET — task còn dư ET (vd log bị chặn do ngày đầy) sẽ **không** bị đóng.
- Đóng lẻ một issue bất kỳ: `python jira_subtask.py close-issue --key <KEY> [--transition <tên>]`.

---

## Execution Flow

1. Đọc `env.md` (Bước 0).
2. Parse `SprintCode` (Rule 1). Không có → hỏi người dùng, dừng.
3. Parse từng dòng → `{tên việc, ET, parent summary}`.
4. Với mỗi dòng: xác định Parent Summary (Rule 2/3).
5. `find-parent` (Rule 4). Không thấy → `create-issue` Task (Rule 5).
6. Chia ET nếu > 2MD (Rule 6/7).
7. **Suy `Start Date + Due Date` từ mã sprint** (`sprint-dates`, Rule 9) → cho người dùng confirm hoặc tự nhập. Thu thập thêm **ngày nghỉ (nếu có)** và field bắt buộc theo project — vd `TTCNSPQT` cần `duedate`, `customfield_12115` (Start Date), **Vai trò** (cha của "Vai trò - Công đoạn"; **Công đoạn con mặc định none, không hỏi**). Hỏi người dùng nếu chưa biết, **trước khi** tạo.
8. `create-subtask` cho từng phần (Rule 8) — assignee mặc định = chính người dùng, kèm `--fields-json` các field bắt buộc.
9. **Log work** cho toàn bộ sub-task vừa tạo (Rule 10): `distribute-worklog` với `--start-date` = Start Date, `--tasks-json` = danh sách `{key, hours}` theo thứ tự. ≤ 8h/ngày, bỏ qua cuối tuần **và ngày nghỉ** (`--days-off-json`), **tự trừ giờ đã log tay từ trước** mỗi ngày (mặc định bật). **Task họp → thêm `"maxPerDay": 2`** để rải mỏng, không dồn 1 ngày. Thêm `--close-when-done` để **đóng task đã log đủ ET** (Rule 11).
10. In bảng kết quả (Output Format) gồm cả lịch log work và trạng thái đóng.

**Gợi ý hiệu năng:** các dòng độc lập nhau — có thể xử lý tuần tự cho dễ theo dõi, hoặc gọi song song nếu nhiều việc. Cache key parent đã tìm/tạo để cùng một Parent Summary không bị tạo trùng.

---

## Output Format

```text
✓ Parent: APP-123  ([Nền tảng App] Công việc khác Sprint 5.2.26)

✓ APP-124  AI agent business-management-system - 1   ET: 2MD   (assignee: dinhtq8)
✓ APP-125  AI agent business-management-system - 2   ET: 2MD   (assignee: dinhtq8)
✓ APP-126  AI agent business-management-system - 3   ET: 1MD   (assignee: dinhtq8)

Log work (start 2026-05-29, ≤8h/ngày, bỏ T7/CN):
  APP-124  29/05: 8h | 01/06: 8h
  APP-125  02/06: 8h | 03/06: 8h
  APP-126  04/06: 8h
```

Nếu có lỗi từ API, in dòng `✗ <tên việc>: <thông báo lỗi>` và tiếp tục các việc còn lại.

---

## Important Constraints

- KHÔNG tạo Sub-task khi chưa xác định được Parent.
- Luôn gắn Sprint Label cho mọi issue tạo mới.
- Luôn `find-parent` trước khi tạo parent mới (tránh tạo trùng).
- KHÔNG tạo Sub-task có ET > 2MD (luôn chia nhỏ).
- Chỉ tạo issue trong project người dùng chỉ định (`--project`) hoặc `JIRA_PROJECT` trong env.md.
- Không xác định được Sprint Code → yêu cầu người dùng cung cấp, không tự bịa.
- Assignee mặc định = chính người dùng (env username), trừ khi chỉ định khác.
- Tự suy Start Date + Due Date từ mã sprint (`sprint-dates`) rồi cho người dùng confirm/tự nhập trước khi tạo.
- Sau khi log work, đóng (`--close-when-done`) task đã log đủ ET; task còn dư ET không đóng.
- Log work: **không quá 8h/ngày**, log tuần tự đến khi hết ET; mặc định bỏ qua T7/CN **và ngày nghỉ người dùng khai** (nghỉ cả ngày bỏ hẳn; nghỉ nửa ngày chỉ log 4h). Trần 8h/ngày tính **cả worklog user đã tự log tay từ trước** (mặc định kiểm tra; ngày đã đủ 8h → bỏ qua).
- KHÔNG in token/password ra màn hình.
