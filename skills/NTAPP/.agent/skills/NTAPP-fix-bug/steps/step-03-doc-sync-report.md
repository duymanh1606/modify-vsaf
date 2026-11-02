# Step 03 — Resolve Jira + Report cuối (terminal)

**Persona:** Người đóng gói kết quả cho user review.

**Mục tiêu:** Tổng hợp fix-report các bug (doc-sync đã do engine làm inline ở step-02) → **đóng bug trên Jira** (nếu có, qua 1 HITL gate) → trình báo cáo cuối. KHÔNG commit.

---

## 1. Reconcile doc-sync (chỉ khi cần)
Doc-sync per-bug đã do engine `NTAPP-bug-fix-engine` làm inline ở step-02 (`doc_sync_mode=inline`, surgical theo bảng doc ứng viên dd/techspec/ui_schema/ds/slice). Ở đây chỉ **rà chéo**: nếu nhiều bug cùng chạm **một doc chung** (techspec / `master_token.json` / ui_schema dùng chung) → xác nhận các cập nhật không mâu thuẫn; lệch → chỉnh surgical cho nhất quán. Không có doc chung bị chạm → bỏ qua.

## 2. Đóng bug trên Jira (chỉ bug có `jira_key` + fix thành công)

Không bug nào có `jira_key` → bỏ qua mục này. Bug BLOCKER / ESCALATE / R5 → **loại khỏi danh sách** (R7): trạng thái Jira giữ nguyên.

### 2.1 — Preview + HITL GATE (bắt buộc, 1 lần cho cả lô)
In bảng preview rồi DỪNG:

| Bug | Jira | Type | Đường đi trạng thái | Due Date | Người chịu TN | Est. | Assignee cuối (Reporter) | Nguyên nhân | Ảnh hưởng | Giải pháp |
|---|---|---|---|---|---|---|---|---|---|---|

- Cột **Đường đi trạng thái** là thông tin (`To Do → In Progress → Resolved`), KHÔNG phải câu hỏi — user chỉ duyệt nội dung.
- Nội dung 3 cột cuối lấy từ step-02 §3 (in đủ, không tóm tắt — user cần đọc đúng thứ sẽ ghi lên Jira).
- **Type = `Bug` mà thiếu 1 trong 3 nội dung → không được đi tiếp**, phải bổ sung trước (quy định nội bộ, Jira không tự chặn).
- Type = `Issue` → 3 field không bắt buộc; có thì vẫn ghi, không có thì bỏ.
**Đường đi trạng thái là quy định cứng của `jira.digital.vn`, KHÔNG hỏi user.** Type = `Bug` bắt buộc đi `To Do → In Progress → Resolved`; Jira chỉ trả transition từ trạng thái hiện tại nên `Resolved` không hiện ra khi đang ở `To Do` — đó là bình thường, cứ đi 2 hop. Đã verify trên project `TTCNSPQT`:

| Trạng thái hiện tại | Đường đi tới `Resolved` |
|---|---|
| `To Do` (bug mới log) | 2 hop: `In Progress` → `Resolved` |
| `In Progress` | 1 hop trực tiếp |
| `Pending` · `Verifying` | 1 hop trực tiếp |
| `Cancelled` | ❌ không có đường — báo user, bỏ qua bug đó |

Chỉ dừng hỏi user ở đúng 1 trường hợp: **`Cancelled`** (hoặc trạng thái lạ không có đường tới `Resolved`) → nêu trạng thái hiện tại + transition khả dụng, bỏ qua bug đó. **KHÔNG tự chọn transition khác thay `Resolved`.**

**Hop `To Do → In Progress` bắt 3 field theo quy định nội bộ** (Jira trả `required: false` nên KHÔNG tự chặn — skill phải tự bắt, hệt như 3 field Nguyên nhân/Ảnh hưởng/Giải pháp):

| Field | ID | Giá trị |
|---|---|---|
| Due Date | `duedate` | ngày hôm nay `YYYY-MM-DD` |
| Người chịu trách nhiệm | `customfield_15400` (userpicker) | `{"name":"<assignee đọc ở step-01>"}` — người đang fix, KHÔNG phải reporter |
| Original Estimate | `timetracking` | `{"originalEstimate":"<Nh>","remainingEstimate":"<Nh>"}` — tự tính ở step-02 §3 |

3 field này nằm trên **edit screen**, không nằm trên transition screen → phải set bằng `update-issue` **trước** khi transition, KHÔNG nhét vào payload của `transition` (Jira sẽ từ chối field không có trên transition screen).

**⛔ GATE:** *"Duyệt ghi các nội dung trên lên Jira (update field + assign lại Reporter + chuyển Resolved)?"*. User chưa duyệt → KHÔNG gọi lệnh ghi nào. User sửa nội dung → cập nhật rồi in lại preview.

### 2.2 — Ghi lên Jira (sau khi duyệt)
Với mỗi bug, chạy **4 lệnh theo đúng thứ tự dưới**. Thứ tự này bắt buộc: `Người chịu trách nhiệm` phải được set khi assignee **vẫn còn là người fix**, trước khi (c) assign lại cho reporter.

**(a) Set 3 field của hop In Progress** — bỏ qua nếu issue đã ở `In Progress`/`Pending`/`Verifying` **và** 3 field đã có giá trị (đã có thì KHÔNG ghi đè):
```
python -X utf8 <jira_helper> update-issue --key <KEY> \
  --fields-json '{"duedate":"<hôm nay>","customfield_15400":{"name":"<assignee đang fix>"},"timetracking":{"originalEstimate":"<Nh>","remainingEstimate":"<Nh>"}}'
```

**(b) Hop trung gian** — chỉ khi đang ở `To Do`:
```
python -X utf8 <jira_helper> transition --key <KEY> --to "In Progress"
```

**(c) Set 3 field kết quả fix + assign lại Reporter:**
```
python -X utf8 <jira_helper> update-issue --key <KEY> \
  --assignee <reporter.name> \
  --fields-json '{"customfield_13406":"<Nguyên nhân>","customfield_15800":"<Ảnh hưởng>","customfield_15801":"<Giải pháp>"}'
```
`customfield_13406` = Nguyên nhân · `customfield_15800` = Ảnh hưởng · `customfield_15801` = Giải pháp.

**(d) Hop cuối sang Resolved:**
```
python -X utf8 <jira_helper> transition --key <KEY> --to Resolved \
  --fields-json '{"customfield_13241":{"value":"<Bug Type>"}}'
```
Transition screen của `Resolved` bắt lại **Bug Type** (`customfield_13241`). Lấy giá trị đang có từ `extra` ở step-01 §1b và **gửi lại y nguyên**; đang trống → hỏi user chọn trong `allowedValues` mà `get-issue` trả về (`Performance` / `Logic` / `Enviroment` / `Config` / `GUI` / `UI`). Helper tự chặn trước nếu thiếu field bắt buộc, nên đừng đoán.

> Mọi `customfield_*` trên là id đã verify trên `jira.digital.vn`. **Project/instance khác thì id khác** — đọc lại bằng `get-issue --extra-fields` hoặc editmeta rồi map theo tên field, đừng dùng cứng bảng này.

**⚠️ `transition` và `update-issue` GHI THẬT, không auto-undo.** Luôn `--dry-run` trước để validate; chỉ bỏ `--dry-run` sau khi gate §2.1 được duyệt. Hop trung gian cũng là ghi thật — đã nằm trong đường đi user duyệt thì mới chạy, KHÔNG tự hop thêm ngoài đường đi đó.

Lệnh nào trả `ok:false` → **dừng chuỗi của bug đó tại đúng chỗ đó**, ghi lỗi vào report, đi tiếp bug khác. KHÔNG retry vòng lặp. Dừng giữa chuỗi (vd (b) xong mà (d) lỗi) → **nêu rõ trong report issue đang dừng ở trạng thái nào và còn thiếu bước nào** để user xử lý tay — quan trọng vì `Resolved → To Do` KHÔNG revert được.

### 2.3 — Đối chiếu lại file log
Bug có `bug_file` (lane `file`, hoặc lane `jira` tra ngược thấy entry) → dòng trạng thái đã flip `Fixed` ở step-02; bổ sung mã Jira vào ghi chú fix nếu chưa có. Lane `jira` không có file log → không tạo file mới.

## 3. Báo cáo cuối (in chat — không tạo file mới)
Trình bảng tổng (gom từ fix-report các bug ở step-02):

| Bug | Trạng thái mới (file) | Jira (key → status → assignee) | Nguyên nhân | File code đã sửa | Ceremony (lane / atdd) | Verify | Doc đã sync |
|---|---|---|---|---|---|---|---|

Thêm:
- **Jira lỗi khi ghi:** bug nào `update-issue` / `transition` trả lỗi → nêu mã + thông báo lỗi + việc user cần làm tay trên Jira.
- **Bug chưa fix (R5 / BLOCKER / ESCALATE):** liệt kê + lý do / câu hỏi cần user — mandatory-ATDD thiếu test xanh (BLOCKER); Tier 3/4 chưa localize; WBS gap phải đặt id mới; file ngoài blast radius.
- **Cần verify thủ công:** bug UI-style có `verify-level = static-only` → cần so ảnh / chạy app.
- **Self-review:** engine đã self-review inline mỗi bug (correctness / blast-radius / contract-ripples / regression / Rule 4-6-9); nêu finding còn lại (từ fix-report) đã sửa hay còn tồn.
- **Bước tiếp theo cho user:** review diff ở code repo + spec repo, rồi **tự commit** theo workflow chuẩn (skill **KHÔNG** commit — R2). Gợi ý: `ntapp-qa-pipeline-bugfix` để sinh regression test chống tái diễn (cho bug `optional` chưa có test).

---

**DONE.** Không thực hiện thêm hành động nào sau report (đặc biệt: không commit/push).
