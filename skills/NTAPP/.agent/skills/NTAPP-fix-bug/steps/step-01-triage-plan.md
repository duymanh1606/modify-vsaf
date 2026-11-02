# Step 01 — Triage & Plan (HITL gate)

**Persona:** Tech lead phân loại bug, xác định phạm vi sửa, trình plan để user duyệt.

**Mục tiêu:** Từ `bug_file` hoặc `jira_keys`, lọc bug đang mở → map mỗi bug về WBS unit + file code sở hữu (ở code repo) → trình **fix plan table** → DỪNG chờ user duyệt.

---

## 1. Nạp bug — theo `bug_source`

### 1a. `bug_source = file`
Đọc `bug_file`. Tách thành các block bug theo heading `## <SLICE>-<account>-BUG-NN — <title>` (mã bug có nhúng account, vd `SLICE-20-dinhtq8-BUG-01`). Với mỗi block đọc các field: `Trạng thái`, `Severity`, `Màn hình / API`, `WBS unit`, `Mô tả`, `Kết quả mong đợi`, `Kết quả thực tế`, ảnh (nếu có).

**Bắt luôn `jira_key`:** block nào có dòng `- **Jira:** [<KEY>](<url>) — Type: <Bug|Issue>` → ghi lại `<KEY>` + `<Type>` cho bug đó (step-03 dùng để resolve). Không có dòng này → `jira_key = null`, bug chỉ sống trong file.

### 1b. `bug_source = jira`
Với mỗi mã trong `jira_keys`:
```
python -X utf8 <jira_helper> get-issue --key <KEY> \
  --extra-fields customfield_13241,customfield_13406,customfield_15800,customfield_15801 \
  --download-dir <scratchpad>/jira-att
```
Lấy từ JSON trả về: `type` · `status` · `summary` · **`description`** (đây là mô tả bug — dùng THAY cho mô tả trong file) · `reporter` · `assignee` · `attachments[].saved` (ảnh đã tải về local) · `transitions` · `extra` (giá trị `Bug Type` hiện có).

- Status đã đóng → xử lý theo OPEN-STATUS FILTER trong `workflow.md` (hỏi user, không tự bỏ qua).
- `description` là **Jira wiki markup**: `!file.png!` là ảnh attachment, `[^file.zip]` là file đính kèm, `*text*` là bold. Đọc hiểu theo markup, đừng coi là markdown.

**Tra ngược file log (`bug_file` cho lane này):** grep mã Jira trong các file log để xem bug đã từng được log local chưa. Đây là tra **theo mã Jira**, không theo slice, nên quét cả thư mục — nhưng phải nhận **cả hai bố cục** (phẳng và thư mục feature):
```
rg -l --glob 'BUGS-*.md' "<KEY>" {bugs_dir}
```
`{bugs_dir}` lấy từ `slice_paths.py` (xem `workflow.md` Bước 2), không ghép tay. Dùng `rg --glob` thay vì `{bugs_dir}/BUGS-*.md`: glob của shell **không** xuống thư mục con, nên khi file bug chuyển vào `{bugs_dir}/<feature>/` thì lệnh cũ trả rỗng và bug local đã có sẽ bị coi là chưa từng được log.
- **Có match** → đó là `bug_file` + block bug tương ứng. Lấy thêm `WBS unit` / `Severity` / ảnh local từ block đó (đỡ phải suy lại ở §4), nhưng **mô tả vẫn ưu tiên bản trên Jira** (mới hơn). step-03 sẽ flip `Fixed` trong file này.
- **Không match** → không có file log; chỉ fix + resolve Jira. **KHÔNG tự tạo file log mới** (Jira là nguồn sự thật cho bug đó).

## 2. Lọc bug đang mở
Giữ bug có `Trạng thái` ∈ {`Open`, `In Progress`, `Reopened`} (xem OPEN-STATUS FILTER trong workflow.md). Bỏ `Fixed` / `Closed`.
- Không còn bug đang mở nào → báo user "không có bug đang mở trong file", DỪNG.

## 3. Đọc ảnh bug (nếu có)
`Read` ảnh (dưới dạng image) để hiểu chính xác triệu chứng trực quan trước khi phán đoán. Không có ảnh → dựa mô tả + expected/actual.
- Lane `file`: ảnh nhúng trong entry `![...](assets/<SLICE>/<account>/...png)`.
- Lane `jira`: ảnh đã tải về ở §1b — `Read` các path trong `attachments[].saved`. Attachment không phải ảnh (`.zip`, `.log`) → bỏ qua, không giải nén.

## 4. Map mỗi bug → WBS unit → file code
Với mỗi bug đang mở:
1. **WBS unit:** lấy từ field `WBS unit` của bug; nếu trống, suy ra từ `Màn hình / API`:
   - Màn hình → tra `SCR-*` / `WGT-*` trong `wbs` (project_wbs.md) theo tên màn.
   - API path → grep path trong `techspec_dir`, `dd_dir`, hoặc code để tìm unit sở hữu endpoint.
2. **Owning repo + file:** xác định code repo chứa unit:
   - Đọc `dd_dir/<unit>_detailed_design.md` (và techspec nếu có) để biết module/service + component/class liên quan.
   - `Grep` qua các code repo ứng viên (additional working dirs / sibling repos) theo header `// id: <unit>` hoặc theo tên component/endpoint để khoanh vùng file thực tế.
   - UI bug (typography/spacing/layout) → tìm component `.tsx/.jsx` + token/style liên quan ở FE repo (resolve từ `_unit-path-map.yaml` / additional working dirs — không đoán tên repo).
3. Ghi lại: bug-id → unit → repo → (các) file ứng viên → loại bug (UI-style / UI-logic / BE-logic / API-contract / data).

> Không xác định được file code cho 1 bug → đánh dấu **NEEDS-INFO** trong plan (sẽ áp R5: bỏ qua khi chạy, flag ở report), KHÔNG chặn các bug khác.

## 4b. Classify ceremony (tín hiệu cho engine `NTAPP-bug-fix-engine`)
Với mỗi bug đang mở, gán 3 tín hiệu để engine vặn mức ceremony (bug nặng → rigor; bug vặt → nhẹ):
- `severity`: lấy từ field `Severity` của bug.
- `atdd_class`: đối chiếu 5 trigger Mandatory ATDD (canonical `docs/Process/Manual_phase_1.md` §5.1) — A1 cross-system · A2 multi-actor/stateful · A3 async/resilience · B1 critical-domain (auth/tiền/RBAC/PII) · B2 destructive. Match ≥1 → `mandatory` (engine ép test-first RED→GREEN); còn lại → `optional`. **Mặc định an toàn: mơ hồ → nghiêng `mandatory`; chạm critical-domain → luôn `mandatory` bất kể severity.**
- `lane`: suy từ severity + scope — bug UI-style/trivial không đổi contract → `express`; unit có DD, chỉ fix/refactor → `path-b`; còn lại → `ad-hoc`.

## 5. Trình Fix Plan table (HITL GATE)
In ra bảng plan cho toàn bộ bug đang mở:

| Bug | Jira | Severity | Loại | WBS unit | Repo | File ứng viên | Hướng fix (1 dòng) | Ceremony (lane / atdd_class) | Khả thi tự fix? |
|---|---|---|---|---|---|---|---|---|---|

Cột **Jira** = mã issue + Type (`—` nếu bug không gắn Jira) → user thấy trước bug nào sẽ bị resolve trên Jira ở step-03. Cột **Ceremony** cho user thấy bug nào sẽ nặng (`mandatory` → test-first) hay nhẹ (`express`) trước khi duyệt. Kèm 2-3 dòng tóm tắt root-cause sơ bộ cho bug phức tạp. Nêu rõ bug nào **NEEDS-INFO** + câu hỏi cần user trả lời.

**⛔ GATE:** DỪNG, hỏi user: *"Duyệt plan này để tiến hành fix? (có thể chỉnh phạm vi / trả lời các mục NEEDS-INFO)"*. Chỉ sang step-02 khi user duyệt. User chỉnh phạm vi → cập nhật plan rồi mới chạy.

---

**Next (sau khi user duyệt):** Read fully and follow `./steps/step-02-fix-and-verify.md`
