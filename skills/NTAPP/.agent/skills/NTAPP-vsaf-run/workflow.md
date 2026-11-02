# VSAF Run — Engine Protocol

## Step 1: Parse user input

Extract từ message của user:
- **`workflow`** — path đầy đủ, ví dụ `NTAPP/slice-loop`
- **`args`** — chuỗi sau `--args` (không có quotes); nếu không có `--args` lấy token đầu tiên sau workflow name; nếu hoàn toàn không có → dùng `""`
- **`projectPath`** — thư mục gốc của project hiện tại (working directory)

## Step 2: Start workflow

Gọi `mcp__vsaf__vsaf_start`:
```
workflow:     <workflow>
args:         <args>
projectPath:  <projectPath>
```

Lưu `runId` từ response.

Thông báo cho user: `▶ Bắt đầu workflow <workflow> [runId: <runId>]`

## Step 3: Thực thi các node được trả về

Engine trả về step chứa `nodes: [{ nodeId, description, prompt, skill?, model }]`
(fanout → nhiều node/batch, engine đã cap theo `max_concurrency`). `prompt` đã
self-contained (ledger + context + biến resolved) → subagent không cần thêm context.

- **Bash node**: engine tự chạy, kết quả có sẵn trong response — không cần action.
- **AI node (prompt/command)**: mỗi node / fanout-item = 1 subagent, chạy song song tới
  `max_concurrency`. Truyền **`model: <node.model>`** (opus/sonnet) cho subagent → node chạy
  đúng model khai trong workflow YAML thay vì model mặc định của session. Thiếu `model`
  → kế thừa session. Output node = tóm tắt cuối của subagent.

### Luật bắt buộc khi dispatch AI node

Đo trên 171 lần dispatch thật: orchestrator viết lại prompt **100%** số lần và tự thêm lối thoát
kiểu *"or implement directly if the skill misfits"* — kết quả là node đáng lẽ chạy skill thì chỉ
thực gọi skill **24%**. Sáu luật dưới đây chặn đúng cơ chế đó, không có ngoại lệ.

1. **Cấm viết lại prompt.** `prompt` engine trả về phải truyền **verbatim** vào subagent. Được phép
   **thêm** context dưới dạng block phụ **đặt sau** prompt gốc — không diễn giải lại, không rút gọn,
   không thay thế, không dịch.
2. **Cấm mọi lối thoát.** Tuyệt đối không sinh các cụm như *"or implement directly"*, *"nếu rườm rà
   thì tự làm"*, *"if the skill misfits"*, *"you may invoke ... if useful"*, *"following the X
   discipline"*. Skill có hợp hay không là **quyết định của human**, không phải của orchestrator
   giữa chừng run.
3. **Prompt đã nêu tên skill** (`Invoke: Skill(skill="X", ...)`): giữ nguyên dòng đó ở đầu prompt
   subagent. Prompt **không** nêu nhưng payload **có** field `skill` → tự thêm làm dòng đầu:
   `Invoke: Skill(skill="<skill>", args="<args>") — bắt buộc, không thay thế bằng cách tự làm.`
4. **Command node**: payload luôn kèm field `skill` → subagent invoke `/<skill>`. Ràng buộc verbatim
   ở luật 1 áp dụng y hệt.
5. **Bắt buộc báo cáo bằng chứng.** Subagent kết thúc bằng đúng một dòng:
   `SKILL_INVOKED: <skill> | <yes|no|skipped> | <lý do nếu no/skipped>`
   - `yes` — đã gọi skill.
   - `skipped` — node có điều kiện và điều kiện **không** thoả (artifact đã tồn tại, skill tự SKIP theo
     applicability gate). Đây là kết quả **hợp lệ**, phải kèm lý do cụ thể.
   - `no` — điều kiện thoả nhưng subagent vẫn không gọi skill. Đây là **bypass**.
   Node không gắn skill nào thì bỏ dòng này.
6. **Subagent báo `no`** → **không** đưa node đó vào `results` như thành công. Dừng loop, báo cho user
   tên node + skill bị bỏ + lý do subagent đưa ra, rồi chờ human quyết (chạy lại node, hay chấp nhận
   và cho `vsaf_next` đi tiếp). `skipped` thì đi tiếp bình thường — nhưng nhắc lại lý do skip trong
   summary cuối, vì skip sai chỗ là cách hỏng im lặng thường gặp nhất của các node idempotent.

## Step 4: Report kết quả và advance

Sau khi mọi subagent của batch xong, gọi `mcp__vsaf__vsaf_next`:
```
runId:    <runId>
results:  [{ nodeId: "<id>", output: "<subagent final report>" }, ...]
```

Chỉ đưa **AI node** vào `results` (mỗi `nodeId` một entry). Bash node do engine tự quản lý.

Node nào subagent báo `SKILL_INVOKED: <skill> | no` thì **không** đưa vào đây — dừng và hỏi human
(luật 6 ở Step 3). Đưa vào rồi thì run tính là thành công và lần bỏ skill đó biến mất khỏi audit.

## Step 5: Loop

Lặp lại Step 3–4 với các node mới từ response của `vsaf_next`.

**Kết thúc loop khi:**
- Engine trả về `status: "done"` hoặc `done: true`
- Danh sách node rỗng
- Engine trả về exit code lỗi — báo cho user và dừng

## Step 6: HITL gate (nếu workflow dừng chờ human)

Nếu engine dừng ở bash gate (exit 1 chờ approval):
- Thông báo cho user: file nào cần ký `approved_by:` + `approved_at:`
- Hướng dẫn: sau khi ký xong → `/NTAPP-vsaf-resume <runId>`

## Step 7: Summary

Sau khi hoàn tất, báo cáo:
- Workflow đã chạy + runId
- Trạng thái cuối: `completed` / `paused (HITL)` / `failed`
- Artifact chính được tạo (nếu có)
