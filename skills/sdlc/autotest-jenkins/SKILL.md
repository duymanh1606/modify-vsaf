---
name: autotest-jenkins
description: Tạo và cập nhật Jenkinsfile + Python runner scripts cho Robot Framework CI/CD pipeline. Hỗ trợ Vops và Telegram. Auto-detect create vs update mode.
user-invocable: true
argument-hint: "<yêu cầu bất kỳ>"
disable-model-invocation: true
---

# Jenkins CI/CD Skill

Bạn là **Senior DevOps / Automation Engineer** chuyên setup CI/CD pipeline cho Robot Framework test.

> **Quan trọng:** Chạy skill này từ bên trong **project directory** cần setup Jenkins — không phải từ thư mục template repo.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo, tóm tắt kết quả — viết bằng **tiếng Việt**. Giữ nguyên thuật ngữ kỹ thuật (Jenkinsfile, pipeline, param, cron, trigger...) không dịch.

> **Commit message:** Skill không tự commit (chỉ nhắc user tự chạy `git add`/`git commit`/`git push` — xem Step A4). Nếu user yêu cầu Claude commit hộ, viết message bằng **tiếng Việt** theo format `<type>: <mô tả ngắn gọn>` (feat/fix/refactor/docs/test) — giữ nguyên thuật ngữ kỹ thuật không dịch.

---

## Argument Parsing

Nhận **ngôn ngữ tự nhiên** — không cần cú pháp cố định.

```
/autotest-jenkins                                            # trống → hỏi 1 câu
/autotest-jenkins tạo jenkinsfile cho project vtm_android    # tạo mới
/autotest-jenkins thêm testcase TC99 vào account 84362579294 # cập nhật
/autotest-jenkins thêm param enableDebugLogs                 # thêm parameter
/autotest-jenkins cập nhật token vops                        # sửa chat config
/autotest-jenkins thêm account mới 84999999999               # thêm account mới
/autotest-jenkins đặt lịch chạy mỗi ngày 2h sáng              # thêm/sửa trigger cron
```

> **`account`** là tên gọi chung cho đơn vị chạy song song trong Jenkins UI (mỗi account → 1 danh sách TC riêng). Giá trị thực tế tuỳ project: số điện thoại (app cần đăng nhập bằng SĐT như ViettelMoney), username, device serial... Skill không cố định đây phải là số điện thoại.

Parse `$ARGUMENTS`:

1. **Trống** → hỏi một câu:
   > Bạn muốn làm gì? (vd: "tạo jenkinsfile mới", "thêm testcase cho account X", "cập nhật token vops")

2. **Trích xuất ý định:**
   - **MODE**: có từ "tạo", "tạo mới", "setup", "khởi tạo" → **Mode A (Create)**
   - **MODE**: có từ "thêm", "sửa", "cập nhật", "update", "xoá" → **Mode B (Update)**
   - **DETAIL**: thông tin cụ thể đi kèm (tên TC, account, param name, giá trị mới...)

3. Nếu không xác định được MODE → detect tự động ở Step 1.

---

## Step 0 — Guard

```bash
python -c "import os; print('TEMPLATE_REPO' if os.path.exists('IS_TEMPLATE_REPO') else 'OK')"
```

Nếu `TEMPLATE_REPO` → **STOP**:
> Bạn đang ở trong template repo. Hãy `cd` vào project cần setup Jenkins rồi chạy lại `/autotest-jenkins`.

---

## Step 1 — Detect State

```python
import os
has_jenkinsfile = os.path.exists('automation_test/Jenkinsfile')
print('EXISTING' if has_jenkinsfile else 'NEW')
```

- **NEW** → vào **Mode A (Create)**
- **EXISTING** → vào **Mode B (Update)** nếu argument rõ ràng, hoặc hỏi:
  > `automation_test/Jenkinsfile` đã tồn tại. Bạn muốn:
  > 1. **Cập nhật** — thêm TC, thêm param, sửa config
  > 2. **Tạo lại hoàn toàn** — xoá và generate mới

---

## Mode A — Create (Tạo mới)

### Step A1 — Thu thập config cơ bản (message 1)

> **Cần thông tin để generate Jenkinsfile:**
>
> **1. Project**
> - Tên project (vd: `vtm_android`, `vtm_ios`) — dùng làm tên folder và branch
> - Platform: `android` / `ios` / `web` / `api`
> - *(chỉ hỏi nếu platform là `web`)* Browser chạy test (vd: `chrome`, `firefox`, `edge`) — mặc định `chrome` nếu không trả lời
> - Đường dẫn project trên máy Jenkins (vd: `/Users/devicefarm/Documents/UPCODE_ANDROID/vtm_android`)
>
> **Platform quyết định luôn 2 param sau có xuất hiện trên giao diện "Build with Parameters" hay không — không hỏi thêm, tự suy ra từ platform đã chọn:**
> - `urlLinkApp` (link cài app) và `runOnDeviceFarm` (chạy trên Device Farm) — **chỉ thêm nếu platform là `android`/`ios`**. Web/API không có khái niệm cài app hay Device Farm, thêm 2 param này vào giao diện chỉ gây rối, không dùng tới bao giờ.
>
> **2. Git**
> - SSH URL repo chính (vd: `ssh://git@10.x.x.x:8081/aut/vtm_android.git`)
> - SSH URL submodule (nếu có, bỏ trống nếu không dùng)
> - Credentials ID trong Jenkins (vd: `bitbucket`) — **lưu ý:** đây phải là giá trị ở trường **"ID"** thật của credential, không phải tên hiển thị/mô tả bạn thấy trong dropdown khi chọn tay trên UI. Hai giá trị này có thể khác nhau (ID thật thường do Jenkins tự sinh nếu lúc tạo không đặt ID tuỳ chỉnh) — nếu gõ nhầm tên hiển thị, job vẫn tạo được nhưng git checkout sẽ fail với lỗi `CredentialId "..." could not be found` (bug đã xác nhận qua chạy thử thật). Cách lấy ID đúng: Manage Jenkins → Credentials → bấm vào credential đó → xem trường "ID".
>
> **3. Jenkins**
> - Agent label (vd: `worker-mac-mini`)
> - Tên branch master (vd: `master_viettelmoney_android`)
> - Có cần chạy tự động theo lịch định kỳ không (vd "mỗi ngày lúc 2h sáng", "mỗi thứ 2 lúc 9h", hoặc cron syntax `H 2 * * *`)? Nếu có, quy đổi mô tả tự nhiên sang cú pháp cron Jenkins (`PHÚT GIỜ NGÀY THÁNG THỨ`, dùng `H` thay số cụ thể cho phút/giờ để Jenkins tự rải tải — vd "mỗi ngày 2h sáng" → `H 2 * * *`). Nếu không → bỏ qua, không thêm `triggers{}` vào Jenkinsfile.
>   **⚠️ Bắt buộc phải nói rõ cho user (bug đã xác nhận qua chạy thử thật, không phải suy đoán):** `CascadeChoiceParameter` phụ thuộc param khác (`testSuite`, `testcases`) **luôn rỗng** trên build do cron tự bắn — Active Choices Plugin không tính lại cascade khi build không tương tác qua Jenkins UI, chỉ param KHÔNG phụ thuộc gì (`typeRun`) mới giữ đúng `:selected`. Vì vậy **nếu chọn có lịch chạy, bắt buộc phải tạo file `automation_test/data/param_file.yaml`** (xem schema + lý do đầy đủ ở Step A4a) khai rõ `testSuite`/`testcases` cho account/nhóm sẽ chạy theo lịch — nếu không, build cron sẽ fail. Hỏi luôn ở đây: nhóm/account nào sẽ chạy theo lịch, chạy suite nào, TC nào (hoặc để trống = chạy hết suite) — để điền vào YAML mẫu skill tạo sẵn ở Step A4.
> - Có hệ thống CI/CD khác (ngoài lịch cron vừa hỏi — vd 1 pipeline khác gọi job này qua Jenkins API) cần tự trigger job này không? Mặc định **không** nếu user không chủ động nói có — đa số project không cần.
>   - **Không** (mặc định) và **cũng không** dùng lịch chạy ở trên → bỏ hẳn param `triggerByCICD` khỏi giao diện, bỏ hẳn stage "Reload Jenkinsfile & parameters", không cần `param_file.yaml`. Giao diện gọn hơn, chỉ còn param thật sự dùng tới.
>   - **Có**, hoặc **có dùng lịch chạy ở trên** (dù không có CI/CD ngoài) → giữ stage "Reload Jenkinsfile & parameters". Chỉ giữ param `triggerByCICD` trên giao diện nếu user xác nhận **có** hệ thống ngoài thật sự cần bấm nút đó — nếu chỉ dùng cho lịch cron, `when` của stage chỉ cần `triggeredBy 'TimerTriggerCause'`, không cần thêm param `triggerByCICD` vào UI làm gì (không ai bấm tay).
>
> **4. Environments**
> - Danh sách môi trường (vd: `production, uat, staging` — cách nhau bằng dấu phẩy)
>
> **5. Python runner**
> - Đặt tên cho file Python chạy test (vd: `script_viettel_money.py`) — **skill tự viết toàn bộ nội dung** (File 2 ở Step A3), user không cần có sẵn file này, chỉ cần chọn tên
> - *(chỉ hỏi nếu platform là `android`/`ios`)* Package app tương ứng mỗi environment (vd: `production: com.abc, uat: com.abc.uat, staging: com.abc.staging`) — bỏ trống nếu không áp dụng
> - Có cần push report/screenshot lên storage online (S3/MinIO) để xem link trên Jenkins không? Nếu có, cho biết: **upload host** (dùng cho `mc alias set`), **static/public host** để tạo link xem báo cáo (**có thể khác** upload host — vd project tham chiếu vtm_android dùng `s3-static.digital.vn` cho link công khai, khác `s3-devops.digital.vn` dùng để upload; nếu chỉ có 1 host thì dùng chung), bucket, access key/secret. Nếu không → bỏ qua, kết quả chỉ xem trong `automation_test/results/` local.
>
> **6. Vops (chat nội bộ)**
> - Token: `X-Auth-Token`
> - User ID: `X-User-Id`
> - Room ID (`rid`) của group nhận thông báo
> - Tên group (dùng cho Referer header)
> - Link group (vd: `https://vops.viettel.vn/group/...`)
>
> **7. Telegram (bỏ trống nếu không dùng)**
> - Bot token
> - Chat ID
>
> **8. Test-management link (bỏ trống nếu không dùng)**
> - Nếu team có hệ thống quản lý test case/kịch bản kiểm thử riêng (vd testing-platform nội bộ) và muốn skill in link trỏ tới đó ra console Jenkins + Vops sau mỗi lần chạy: cho URL pattern, dùng `{account}` làm placeholder cho account/nhóm đang chạy (vd `http://testing-platform.congty.vn/detail/{account}`). Bỏ trống → skill không in dòng này, không suy đoán URL.

---

### Step A2 — Thu thập cấu trúc test (message 2)

Sau khi user trả lời Step A1, **hỏi cấu trúc trước khi hỏi data** — vì nó quyết định cascade có bao nhiêu cấp:

> **Câu hỏi cấu trúc:** Trong mỗi nhóm test, có cần tách theo 1 đơn vị con — mỗi đơn vị chạy 1 danh sách TC riêng — không?
> - **Có** — dùng khi app cần chạy song song theo tài khoản/số điện thoại/device riêng biệt. Vd: ViettelMoney phải đăng nhập bằng SĐT, nên mỗi SĐT có bộ TC khác nhau → cần tách.
> - **Không** — dùng khi 1 nhóm = 1 suite + 1 danh sách TC cố định, không cần tách nhỏ hơn. Phù hợp phần lớn project web/api, hoặc mobile không yêu cầu multi-login.
> - Không chắc? → mặc định **"Không"** (đơn giản hơn, ít cấp hơn). Có thể chuyển sang "Có" sau này qua Mode B nếu phát sinh nhu cầu.
>
> Đây là quyết định **tuỳ project, không có mặc định đúng cho mọi trường hợp** — ViettelMoney cần "Có", nhưng phần lớn project khác nên chọn "Không".

Sau khi biết cấu trúc, hỏi tiếp data theo đúng format tương ứng:

> **Nếu chọn "Không" (3 cấp: nhóm → suite → testcases)** — điền:
> ```
> [Tên nhóm]
> Suite: <tên_file.robot>
> TCs:
>   <TC_001_Ten_TC>:selected
>   <TC_002_Ten_TC>
>   <TC_003_Ten_TC>
>
> [Tên nhóm khác]
> Suite: <file2.robot>
> TCs:
>   <TC_001>:selected
> ```
>
> **Nếu chọn "Có" (4 cấp: nhóm → account → suite → testcases)** — điền:
> ```
> [Tên nhóm]
> Account: <định danh — số điện thoại/username/device/...>
> Suite: <tên_file.robot>
> TCs:
>   <TC_001_Ten_TC>:selected
>   <TC_002_Ten_TC>
>
> [Tên nhóm có nhiều account]
> Account: <định danh 1>
> Suite: <file1.robot>
> TCs:
>   <TC_001>:selected
>
> Account: <định danh 2>
> Suite: <file2.robot>
> TCs:
>   <TC_001>:selected
> ```
>
> **Lưu ý (áp dụng cả 2 trường hợp):**
> - `:selected` ở cuối TC name → TC đó được tích sẵn khi mở Jenkins UI
> - Nếu cùng 1 nhóm (hoặc account) có danh sách TC khác nhau theo môi trường (production vs staging) → ghi thêm `[Env: staging]` trước block TCs đó
> - **Chưa có sẵn cấu trúc?** Gõ `để trống` — skill vẫn tự generate skeleton hợp lệ (1 nhóm mặc định `Default`, list rỗng) đúng theo số cấp đã chọn ở câu hỏi cấu trúc. Jenkinsfile chạy được ngay, không cần sửa Groovy tay. Bổ sung nhóm/account/suite/TC thật sau bằng lệnh tự nhiên (`/autotest-jenkins thêm nhóm ...`, `/autotest-jenkins thêm account ...`, `/autotest-jenkins thêm testcase ...` — Mode B).
> - **⚠️ Tên nhóm/account nên tránh dấu cách** (vd dùng `Web_Demoblaze` hoặc `WebDemoblaze` thay vì `Web Demoblaze`). Giá trị này được dùng làm tên thư mục kết quả, segment URL báo cáo (S3/MinIO), và tham số dòng lệnh xuyên suốt toàn bộ pipeline (Jenkinsfile → runner script → `common_utilities.py`) — dù skill đã quote đúng chỗ để không crash khi có dấu cách, dùng tên liền không dấu cách vẫn đơn giản/an toàn hơn hẳn (bug đã xác nhận qua chạy thử thật: nhiều lớp lỗi khác nhau xuất phát chính từ việc tên nhóm/account có dấu cách). Không bắt buộc — nếu user vẫn muốn dùng dấu cách, skill vẫn xử lý đúng, chỉ là khuyến nghị.

**Validate trước khi generate:** với mỗi `Suite: <file>.robot` user khai, kiểm tra `automation_test/tests/<file>.robot` có tồn tại trong project không:

```python
import os
missing = [s for s in suite_names if not os.path.exists(f"automation_test/tests/{s}")]
```

Nếu có file thiếu → **cảnh báo, không chặn** (user có thể chưa viết test tới file đó, hoặc file nằm chỗ khác):
> ⚠️ Chưa thấy các file sau trong `automation_test/tests/`: `<danh sách>`. CascadeChoiceParameter vẫn sẽ trỏ tới các suite này — build sẽ fail ở stage "Run test" nếu chưa tạo trước khi chạy. Bạn xác nhận vẫn generate tiếp chứ?

**Phân tích format user cung cấp → generate CascadeChoiceParameter blocks theo đúng cấu trúc đã chọn ở câu hỏi trên.**

**Block 1 — `typeRun` (radio):** dùng chung cho cả 2 trường hợp. Lấy tất cả tên nhóm từ `[Tên nhóm]`, nhóm đầu tiên thêm `:selected`

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_RADIO',
    name: 'typeRun',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: '''
        return [
            '<Nhóm 1>:selected',
            '<Nhóm 2>',
            ...
        ]
    ''']]
],
```

---

### Nếu chọn "Không tách" — 5 block

**Block 2 — `testSuite` (single select, phụ thuộc typeRun):** mỗi nhóm → case trong switch, trả về tên file robot

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_SINGLE_SELECT',
    name: 'testSuite',
    referencedParameters: 'typeRun',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: """
        switch(typeRun) {
            case "<Nhóm 1>":
                return ["<file1.robot>"]
                break
            case "<Nhóm 2>":
                return ["<file2.robot>"]
                break
            ...
        }
    """]]
],
```

**Block 3 — `selectALL` (checkbox):**

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_CHECKBOX',
    name: 'selectALL',
    referencedParameters: 'count_size',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: "return ['ALL']"]]
],
```

**Block 4 — `testcases` (checkbox, phụ thuộc typeRun + selectALL):** mỗi nhóm → case trong switch, list TC names. Nếu user cung cấp `[Env: staging]` → wrap trong `if (envRun.equals("staging")) { ... } else { ... }`

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_CHECKBOX',
    name: 'testcases',
    referencedParameters: 'envRun,testSuite,typeRun,selectALL',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: """
        def list_tc = []
        switch(typeRun) {
            case "<Nhóm 1>":
                list_tc = [
                    "<TC_001>:selected",
                    "<TC_002>",
                    ...
                ]
                break
            case "<Nhóm 2>":
                // Có conditional theo env
                if (envRun.equals("staging")) {
                    list_tc = [ ... ]
                } else {
                    list_tc = [ ... ]
                }
                break
            ...
        }
        if (selectALL.equals("ALL")) {
            list_tc = list_tc.collect { it.endsWith(":selected") ? it : it + ":selected" }
        }
        return list_tc
    """]]
],
```

**Block 5 — `count_size`:** xem cuối phần này (dùng chung cho cả 2 trường hợp).

---

### Nếu chọn "Có tách theo account" — 6 block

**Block 2 — `account` (radio, phụ thuộc typeRun):** mỗi nhóm → case trong switch, list account của nhóm đó

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_RADIO',
    name: 'account',
    referencedParameters: 'typeRun',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: """
        switch(typeRun) {
            case "<Nhóm 1>":
                return ['<ACCOUNT_1>:selected']
                break
            case "<Nhóm 2>":
                return ['<ACCOUNT_2>:selected', '<ACCOUNT_3>']
                break
            ...
        }
    """]]
],
```

**Block 3 — `testSuite` (single select, phụ thuộc account + typeRun):** mỗi account → case trong switch, trả về tên file robot

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_SINGLE_SELECT',
    name: 'testSuite',
    referencedParameters: 'account,typeRun',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: """
        switch(account) {
            case "<ACCOUNT_1>":
                return ["<file1.robot>"]
                break
            case "<ACCOUNT_2>":
                return ["<file2.robot>"]
                break
            ...
        }
    """]]
],
```

**Block 4 — `selectALL` (checkbox):**

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_CHECKBOX',
    name: 'selectALL',
    referencedParameters: 'count_size',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: "return ['ALL']"]]
],
```

**Block 5 — `testcases` (checkbox, phụ thuộc account + selectALL):** mỗi account → case trong switch, list TC names. Nếu user cung cấp `[Env: staging]` → wrap trong `if (envRun.equals("staging")) { ... } else { ... }`

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_CHECKBOX',
    name: 'testcases',
    referencedParameters: 'envRun,testSuite,typeRun,selectALL,account',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: """
        def list_tc = []
        switch(account) {
            case "<ACCOUNT_1>":
                list_tc = [
                    "<TC_001>:selected",
                    "<TC_002>",
                    ...
                ]
                break
            case "<ACCOUNT_2>":
                // Có conditional theo env
                if (envRun.equals("staging")) {
                    list_tc = [ ... ]
                } else {
                    list_tc = [ ... ]
                }
                break
            ...
        }
        if (selectALL.equals("ALL")) {
            list_tc = list_tc.collect { it.endsWith(":selected") ? it : it + ":selected" }
        }
        return list_tc
    """]]
],
```

**Block 6 — `count_size`:** xem cuối phần này (dùng chung cho cả 2 trường hợp).

---

### `count_size` (hidden, đếm số TC) — dùng chung cho cả 2 trường hợp

```groovy
[$class: 'CascadeChoiceParameter',
    choiceType: 'PT_SINGLE_SELECT',
    name: 'count_size',
    referencedParameters: 'testcases',
    script: [$class: 'GroovyScript', script: [sandbox: true, script: """
        return [testcases.size()]
    """]]
]
```

> Nếu user gõ `để trống` → vẫn generate đủ số block Groovy đúng theo cấu trúc đã chọn (không để lại comment yêu cầu viết tay), dùng data mặc định:
> - Block 1 (`typeRun`): `return ['Default:selected']`
> - **Nếu "Không tách":** Block 2 (`testSuite`): `case "Default": return []`; Block 4 (`testcases`): `case "Default": list_tc = []`
> - **Nếu "Có tách":** Block 2 (`account`): `case "Default": return []`; Block 3 (`testSuite`): `case "": return []`; Block 5 (`testcases`): `case "": list_tc = []`
>
> Jenkinsfile parse và load được ngay trên Jenkins (dropdown sẽ trống cho tới khi user chạy `/autotest-jenkins thêm nhóm/account/testcase ...` để bổ sung dữ liệu thật — không cần đụng vào Groovy).

### Step A3 — Generate files

Tạo **7 files** theo thứ tự (Jenkinsfile, runner script, common_utilities.py, convert_fail_to_skip.py, create_index_file_table.py, read_output_file.py, push_chat_apps.py). Tất cả đều do skill tự viết — user không cần có sẵn file nào. Không bao giờ ghi đè file đang có (hỏi trước nếu file tồn tại).

---

#### File 1: `automation_test/Jenkinsfile`

```groovy
properties([
    parameters([
        // Chỉ thêm param 'triggerByCICD' nếu Step A1 xác nhận CÓ hệ thống CI/CD
        // ngoài thật sự cần bấm trigger job này qua API. Nếu chỉ dùng lịch cron
        // (không có CI/CD ngoài) → bỏ hẳn param này, đừng thêm cho có — không ai
        // dùng tới trên giao diện, chỉ gây rối.
        booleanParam(
            name: 'triggerByCICD',
            defaultValue: false,
            description: 'true → job đọc tham số từ param_file.yaml | false → nhập tay trên Jenkins UI'
        ),
        choice(
            name: 'envRun',
            choices: [<ENVIRONMENTS_LIST>],
            description: 'Môi trường chạy test'
        ),
        // urlLinkApp + runOnDeviceFarm: CHỈ thêm nếu platform là android/ios (Step
        // A1 câu 1). Web/API không có khái niệm cài app hay Device Farm — bỏ hẳn 2
        // param này khỏi giao diện, không để cho có rồi không ai dùng.
        string(
            name: 'urlLinkApp',
            defaultValue: '',
            description: 'Link download app (để trống nếu không cần cài lại). Chỉ cài trong lần build đầu tiên.'
        ),
        booleanParam(
            name: 'runOnDeviceFarm',
            defaultValue: true,
            description: 'Chạy trên Device Farm. Bỏ chọn để chạy local.'
        ),

        // ════════════════════════════════════════════════════════════
        // CascadeChoiceParameter — Active Choices Plugin
        // Chèn nguyên văn các block đã generate ở Step A2 vào đúng vị trí
        // này, theo thứ tự đó — kể cả khi user gõ "để trống" (dùng skeleton
        // nhóm Default). Không bao giờ để lại comment yêu cầu viết Groovy
        // tay — mọi cập nhật sau này đi qua Mode B.
        // - "Không tách" (5 block): typeRun, testSuite, selectALL, testcases, count_size
        // - "Có tách theo account" (6 block): typeRun, account, testSuite, selectALL, testcases, count_size
        // ════════════════════════════════════════════════════════════

        booleanParam(
            name: 'rerun',
            defaultValue: false,
            description: 'Chạy lại các TC fail của lần chạy gần nhất'
        ),
        booleanParam(
            name: 'debugVideo',
            defaultValue: false,
            description: 'Record video để debug TC fail (tăng thời gian chạy)'
        ),
        booleanParam(
            name: 'pullCode',
            defaultValue: false,
            description: 'Pull code mới nhất từ remote trước khi chạy'
        ),
    ])
])

def getProjectPath(branchName) {
    def causes = currentBuild.getBuildCauses()[0]._class
    def build_user = ""
    if (causes.contains("TimerTriggerCause")) {
        echo "Triggered by TIMER"
    } else if (causes.contains("UserIdCause")) {
        build_user = currentBuild.getBuildCauses()[0].userId.split('@')
    } else if (causes.contains("UpstreamCause")) {
        build_user = currentBuild.upstreamBuilds[0].getBuildCauses()[0].userId.split('@')
    } else if (causes.contains("BranchIndexingCause")) {
        currentBuild.result = 'ABORTED'
        error("Job stopped: Branch Indexing trigger ignored.")
    } else {
        currentBuild.result = 'ABORTED'
        error("Job stopped: Unknown trigger.")
    }
    if (branchName == "<MASTER_BRANCH>" || build_user == "") {
        return "<PROJECT_PATH>"
    } else {
        return "<PROJECT_BASE_PATH>/${build_user[0]}/<PROJECT_NAME>"
    }
}

pipeline {
    environment {
        // Nếu Step A2 chọn "Có tách theo account": account = "$account" (param thật, từ Block 2)
        // Nếu chọn "Không tách": không có param `account` trên Jenkins UI — alias sang "$typeRun"
        // để mọi phần downstream (output path, runner script, common_utilities.py) dùng chung
        // biến `account`, không cần đổi gì theo cấu trúc đã chọn.
        account     = "$account"   // "Không tách" → đổi thành: account = "$typeRun"
        envRun      = "$envRun"
        // Chỉ thêm 2 dòng dưới nếu platform là web/api (KHÔNG có param urlLinkApp/
        // runOnDeviceFarm trên giao diện — xem Step A1). Gán cứng trực tiếp ở đây
        // thay vì đọc "$urlLinkApp"/"$runOnDeviceFarm" (param không tồn tại sẽ ra
        // giá trị null/"null" khó lường) — rõ ràng, không phụ thuộc hành vi ngầm
        // của Jenkins khi param bị thiếu.
        urlLinkApp      = ""       // web/api không cần cài app
        runOnDeviceFarm = "false"  // web/api không có khái niệm Device Farm
        projectPath = getProjectPath("${BRANCH_NAME}")
        // Không nhúng quote literal vào path ở đây (vd results_'${envRun}'_...) — account
        // là free-text có thể chứa dấu cách, nhúng quote nửa vời không bảo vệ được toàn bộ
        // path và chỉ gây rối khi debug. Quote đầy đủ ở đúng nơi dùng (mỗi lệnh `sh` bên dưới).
        outputFilePath = "${projectPath}/automation_test/results/results_${envRun}_${account}/output_copy.xml"
        outputLink     = "${projectPath}/automation_test/results/results_${envRun}_${account}/link_results.xml"
    }
    options {
        skipDefaultCheckout()
    }
    // Chỉ thêm block triggers này nếu user xác nhận có dùng lịch chạy tự động ở
    // Step A1 câu 3. Không thêm nếu user không cấu hình — đừng để lại block rỗng
    // hay comment yêu cầu viết tay.
    triggers {
        cron('<CRON_EXPR>')
    }
    agent { label "<AGENT_LABEL>" }

    stages {
        stage("Setup Build Description") {
            steps {
                script {
                    currentBuild.description = "${envRun.toUpperCase()}_${account}"
                }
            }
        }

        // Stage này CHỈ tồn tại nếu Step A1 xác nhận có lịch cron VÀ/HOẶC có hệ
        // thống CI/CD ngoài. Nếu KHÔNG dùng cả 2 → bỏ hẳn stage này (không để lại
        // rỗng/comment viết tay) — không cần param_file.yaml, giao diện + pipeline
        // gọn hơn.
        stage("Reload Jenkinsfile & parameters") {
            // `triggeredBy 'TimerTriggerCause'` — PHẢI có nếu có dùng lịch cron, không
            // chỉ params.triggerByCICD. Bug đã xác nhận qua chạy thử thật: build do
            // cron tự bắn không đi qua Jenkins UI, nên các CascadeChoiceParameter phụ
            // thuộc param khác (testSuite, testcases — phụ thuộc typeRun qua
            // referencedParameters) LUÔN rỗng, dù typeRun (không phụ thuộc gì) vẫn giữ
            // đúng giá trị :selected. testSuite rỗng + không quote trong lệnh sh ở
            // stage "Run test" khiến toàn bộ vị trí argv phía sau lệch, crash với
            // IndexError khó hiểu. Đây là giới hạn thật của Active Choices Plugin
            // (không tự tính lại cascade khi build không tương tác qua UI), không
            // phải lỗi Groovy — cách duy nhất chạy đúng là đọc testSuite/testcases từ
            // file YAML thay vì params.
            //
            // Ghép when theo đúng lựa chọn Step A1:
            // - Có cả lịch cron + CI/CD ngoài (param triggerByCICD tồn tại)  → anyOf
            //   { expression { return params.triggerByCICD == true }; triggeredBy
            //   'TimerTriggerCause' } (giữ nguyên như dưới)
            // - CHỈ có lịch cron (không có param triggerByCICD trên UI)      → khi đó
            //   không còn `params.triggerByCICD` để tham chiếu, `when` chỉ còn:
            //   `triggeredBy 'TimerTriggerCause'` (bỏ hẳn nhánh expression/anyOf)
            // - CHỈ có CI/CD ngoài (không có lịch cron)                     → `when`
            //   chỉ còn: `expression { return params.triggerByCICD == true }` (bỏ
            //   hẳn nhánh triggeredBy/anyOf)
            when {
                anyOf {
                    expression { return params.triggerByCICD == true }
                    triggeredBy 'TimerTriggerCause'
                }
            }
            steps {
                script {
                    dir("${env.projectPath}") {
                        datas = readYaml(file: 'automation_test/data/param_file.yaml')
                        env.pullCode       = "${datas."${account}".pullCode}"
                        // Chỉ thêm dòng dưới nếu platform là android/ios (có param
                        // runOnDeviceFarm thật trên UI — xem Step A1). Với web/api, BỎ HẲN
                        // dòng này — env.runOnDeviceFarm đã gán cứng "false" ở environment{}
                        // rồi; nếu vẫn để dòng này mà YAML không khai `runOnDeviceFarm` cho
                        // account đó, Groovy sẽ trả null → GString interpolate ra chuỗi
                        // literal "null", ĐÈ MẤT giá trị "false" đúng đã gán trước đó.
                        env.runOnDeviceFarm = "${datas."${account}".runOnDeviceFarm}"
                        // Ưu tiên testSuite/testcases khai trong YAML (bắt buộc phải có khi
                        // build có thể bị trigger bởi cron — xem lưu ý ở Step A4a) — chỉ fallback
                        // về params khi YAML không khai (trường hợp hệ thống CI/CD ngoài tự
                        // truyền params thật qua triggerByCICD, không qua cron).
                        env.testSuite      = "${datas."${account}".testSuite ?: params.testSuite}"
                        env.testcases      = "${datas."${account}".testcases ?: params.testcases}"
                        env.rerun          = "${rerun}"
                        env.debugVideo     = "${debugVideo}"
                    }
                }
            }
        }

        stage('Set Branch Name For Submodule') {
            steps {
                script {
                    env.BRANCH_NAME_SUBMODULE = BRANCH_NAME.replace('<PLATFORM>', 'submodule')
                }
            }
        }

        stage('Git Pull Code') {
            steps {
                script {
                    dir("${env.projectPath}") {
                        if ("${pullCode}" == "true") {
                            git(url: "<GIT_SSH_URL>", credentialsId: "<CREDENTIALS_ID>", branch: "${BRANCH_NAME}")
                            <SUBMODULE_BLOCK>
                        }
                    }
                }
            }
        }

        stage('Run test') {
            steps {
                script {
                    dir("${env.projectPath}") {
                        // QUOTE TOÀN BỘ tham số, kể cả những cái tưởng "an toàn" (testSuite,
                        // rerun, debugVideo, runOnDeviceFarm) — không chỉ account/testcases.
                        // Bug đã xác nhận qua chạy thử thật 2 lần, 2 nguyên nhân khác nhau: (1)
                        // account có dấu cách bị shell tách làm đôi; (2) build do cron tự bắn
                        // khiến testSuite RỖNG — 1 biến rỗng KHÔNG QUOTE biến mất hoàn toàn khỏi
                        // câu lệnh shell (không phải thành chuỗi rỗng), lệch hết vị trí argv phía
                        // sau, Python crash với IndexError khó hiểu ở dòng không liên quan gì.
                        // Quote hết = mỗi tham số luôn chiếm đúng 1 vị trí argv dù rỗng hay có
                        // dấu cách.
                        sh "python3 automation_test/config/<RUNNER_SCRIPT> '${env.urlLinkApp}' '${env.runOnDeviceFarm}' '${env.testSuite}' '${env.rerun}' '${env.account}' '${env.envRun}' '${env.debugVideo}' '${env.projectPath}' '${env.testcases}'"
                    }
                }
            }
        }

        stage('Read output file') {
            steps {
                script {
                    dir("${env.projectPath}") {
                        // Quote '${env.outputFilePath}'/'${env.outputLink}' — cùng lý do account
                        // có thể chứa dấu cách (bug đã xác nhận qua chạy thử thật: thiếu quote ở
                        // đây khiến path bị shell tách làm đôi, read_output_file.py đọc sai file
                        // (bắt exception rồi trả về total/pass/fail/skip = 0 giả — Jenkins vẫn
                        // báo build SUCCESS dù không hề đọc được kết quả test thật).
                        def scriptOutput = sh(
                            script: "python3 automation_test/python_lib/read_output_file.py '${env.outputFilePath}' '${env.outputLink}'",
                            returnStdout: true
                        ).trim()
                        currentBuild.description = "${scriptOutput}"
                        def report_content = "${scriptOutput}".replaceAll("<br />", "---")
                        def data = ['"', "'", ",", "<a", "</a>", ">", " ", "Screenshot", "Report", "href=", "\n"]
                        data.each { val -> report_content = report_content.replaceAll(val, "") }
                        env.BUILD_TAG = "${report_content}"
                        sh "python3 automation_test/python_lib/push_chat_apps.py '${env.BUILD_TAG}' '${env.outputFilePath}' ${BRANCH_NAME}"
                    }
                }
            }
        }
    }
}
```

**Thay thế placeholders:**

| Placeholder | Giá trị từ config |
|---|---|
| `<ENVIRONMENTS_LIST>` | Danh sách env từ câu hỏi 4, cách nhau bằng `','` trong Groovy list |
| `<MASTER_BRANCH>` | Branch master từ câu hỏi 3 |
| `<PROJECT_PATH>` | Đường dẫn đầy đủ từ câu hỏi 1 |
| `<PROJECT_BASE_PATH>` | Parent folder của project path |
| `<PROJECT_NAME>` | Tên project từ câu hỏi 1 |
| `<AGENT_LABEL>` | Agent label từ câu hỏi 3 |
| `<PLATFORM>` | Platform từ câu hỏi 1 (android/ios/web/api) |
| `<GIT_SSH_URL>` | SSH URL từ câu hỏi 2 |
| `<CREDENTIALS_ID>` | Credentials ID từ câu hỏi 2 |
| `<RUNNER_SCRIPT>` | Tên file Python từ câu hỏi 5 |
| `<SUBMODULE_BLOCK>` | Block git pull submodule nếu có URL, bỏ trống nếu không |
| `<CRON_EXPR>` | Cú pháp cron Jenkins quy đổi từ câu hỏi 3 (lịch chạy tự động) |

**Lịch chạy tự động (`triggers { cron(...) }`):** chỉ đưa block này vào Jenkinsfile nếu user xác nhận có dùng ở Step A1 câu 3. Nếu user không dùng → **bỏ hẳn cả block `triggers { }`**, không để lại rỗng hay comment yêu cầu viết tay. `getProjectPath()` đã tự xử lý sẵn `TimerTriggerCause` (không abort, dùng `<PROJECT_PATH>` chính — không phải path riêng theo user) nên không cần sửa gì thêm ở đó.

**`<SUBMODULE_BLOCK>`** khi có submodule:
```groovy
dir("${env.projectPath}/automation_test") {
    git(url: "<SUBMODULE_SSH_URL>", credentialsId: "<CREDENTIALS_ID>", branch: "${BRANCH_NAME_SUBMODULE}")
}
```

---

#### File 2: `automation_test/config/<RUNNER_SCRIPT>.py`

User không có sẵn file này — skill viết toàn bộ nội dung dưới đây, chỉ thay `<RUNNER_SCRIPT>` bằng tên đã chọn ở Step A1 câu 5.

```python
import os
import subprocess
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from python_lib.common_utilities import Utilities


def run_testcases():
    Utilities.identify_os_running()
    Utilities.init_variables(
        project_path=projectPath,
        env_run=envRun,
        account=account,
        test_suite=testSuite,
        test_cases=testcases,
        run_on_device_farm=runOnDeviceFarm,
        re_run=rerun,
        url_link_app=urlLinkApp,
        debug_video=debugVideo,
    )
    Utilities.delete_media_files(Utilities.common_result_path, Utilities.patterns_media_files)
    Utilities.execute_test(
        account=Utilities.account,
        runOnDeviceFarm=Utilities.run_on_device_farm,
        link_app=Utilities.url_link_app,
        app_package=Utilities.package_app,
        envRun=Utilities.env_run,
        # browser=<browser>,  # chỉ thêm dòng này nếu platform là web (giá trị từ Step A1 câu 1)
        projectPath=Utilities.project_path,
        debugVideo=Utilities.debug_video,
        transactionID=Utilities.transactionID,
    )
    Utilities.set_report_links()  # tính link_screenshot_base/link_screenshot/link_report — PHẢI chạy trước test_result_reporting() để create_index_file_table.py nhúng đúng link ảnh vào index.html
    Utilities.test_result_reporting()  # tạo index.html ở đây — report.html do robot tự sinh từ execute_test()
    Utilities.push_report_to_s3_minio()  # upload thật — PHẢI chạy SAU test_result_reporting(), nếu không index.html chưa tồn tại lúc upload (bug đã xác nhận qua chạy thử thật: link "Screenshot" luôn lỗi vì index.html không có mặt trên S3)
    Utilities.copy_output_file()
    Utilities.process_test_result_for_jenkins_display()


if len(sys.argv) < 2:
    print("Usage: python3 <RUNNER_SCRIPT>.py [args]")
    sys.exit(1)

urlLinkApp      = "" if sys.argv[1] == "null" else sys.argv[1]
runOnDeviceFarm = sys.argv[2]
testSuite       = sys.argv[3]
rerun           = sys.argv[4]
account         = sys.argv[5]
envRun          = sys.argv[6]
debugVideo      = sys.argv[7]
projectPath     = sys.argv[8]
testcases       = None if rerun == "true" else sys.argv[9]

try:
    transactionID = sys.argv[10]
except IndexError:
    transactionID = ""

run_testcases()
```

> File này gọi `Utilities` class từ `automation_test/python_lib/common_utilities.py` — xem **File 2b** ngay dưới đây để tự động tạo file đó.

---

#### File 2b: `automation_test/python_lib/common_utilities.py`

Người dùng thường **không có sẵn file này** — luôn tự generate, không hỏi đường dẫn file có sẵn. Chỉ đưa vào file những phần thực sự cần dựa trên câu trả lời đã thu thập ở Step A1 câu 5:

- **`package_app` per environment**: chỉ sinh mapping trong `init_variables` nếu platform là `android`/`ios` **và** user đã cho danh sách package app. Nếu platform `web`/`api`, hoặc user bỏ trống → không sinh phần này (không để TODO chết, đơn giản là không có).
- **Push report S3/MinIO**: chỉ sinh lệnh `mc` thật trong `push_report_to_s3_minio` nếu user xác nhận có dùng, hỏi host/bucket + access key/secret rồi fix cứng literal vào file (cùng cách xử lý với Vops/Telegram — xem lưu ý private repo ở Step A4). Nếu user nói không dùng → method này để `pass` (no-op), không viết logic giả định.
- **`process_test_result_for_jenkins_display`**: luôn sinh (bắt buộc — `read_output_file.py` ở stage "Read output file" phụ thuộc vào file `link_results.xml` này để hiển thị build description). Nếu có báo report/screenshot link (khi push S3 = có) → đưa link vào; nếu không → chỉ ghi env + account, không có link.
- Nếu thiếu thông tin bắt buộc để sinh đúng (vd platform là mobile nhưng chưa có package app cho 1 trong các environment đã khai ở câu 4) → **hỏi lại đúng phần thiếu**, không tự đoán giá trị.

Template (ví dụ: platform android, có package app 3 env, không dùng S3/MinIO):

```python
import os
import shutil
import subprocess


class Utilities:
    project_path = ""
    env_run = ""
    account = ""
    test_suite = ""
    test_cases = ""
    run_on_device_farm = ""
    re_run = ""
    url_link_app = ""
    debug_video = ""
    transactionID = ""
    os_name = ""
    package_app = ""
    common_result_path = ""
    link_screenshot_base = ""  # tiền tố URL cho ảnh trong report — rỗng = link tương đối, xem local
    link_screenshot = ""  # link trang index.html (danh sách TC fail + screenshot) — rỗng nếu không dùng S3
    link_report = ""  # link report.html — rỗng nếu không dùng S3
    run_datestr = ""  # timestamp riêng cho mỗi lần chạy — chỉ set khi dùng S3/MinIO (set_report_links())
    patterns_media_files = [".html", ".png", ".mp4"]

    @staticmethod
    def identify_os_running():
        Utilities.os_name = Utilities.project_path.split('_')[-1]

    @staticmethod
    def init_variables(**kwargs):
        for key, value in kwargs.items():
            setattr(Utilities, key, value)
        package_by_env = {
            "production": "<PACKAGE_PRODUCTION>",
            "uat": "<PACKAGE_UAT>",
            "staging": "<PACKAGE_STAGING>",
        }
        Utilities.package_app = package_by_env.get(Utilities.env_run, "")
        Utilities.common_result_path = f"{Utilities.project_path}/automation_test/results/results_{Utilities.env_run}_{Utilities.account}"
        os.makedirs(Utilities.common_result_path, exist_ok=True)

    @staticmethod
    def delete_media_files(path, patterns):
        if not os.path.isdir(path):
            return
        for filename in os.listdir(path):
            if filename.endswith(tuple(patterns)):
                os.remove(os.path.join(path, filename))

    @staticmethod
    def execute_test(**kwargs):
        # kwargs -> robot -v key:value, để test .robot truy cập qua ${key}
        # (vd -v account:xxx cho phép RF login bằng ${account} nếu app cần)
        # Quote {value} — account/group name là free-text do user đặt (Step A2),
        # có thể chứa dấu cách (vd "Web Demoblaze"); không quote thì shell tách
        # thành nhiều arg (bug đã xác nhận qua chạy thử thật trên Jenkins server
        # thật, không phải suy đoán).
        robot_vars = " ".join(f'-v {key}:"{value}"' for key, value in kwargs.items())
        # Không dùng "-t *" — chạy qua shell=True, dấu * sẽ bị shell glob-expand
        # thành tên file/thư mục trong cwd trước khi robot nhận được (bug đã xác
        # nhận qua chạy thử thật). Không truyền -t nào = robot tự chạy hết.
        testcases_name = "" if Utilities.test_cases in ("*", None) else \
            " ".join(f"-t {tc}" for tc in Utilities.test_cases.split(","))
        # common_result_path chứa {env_run}_{account} — cùng lý do trên, PHẢI quote
        # (bug đã xác nhận qua chạy thử thật: --output/-d bị cắt ngay tại dấu cách
        # đầu tiên, robot ghi output.xml sai chỗ, các bước đọc kết quả sau đó fail
        # với FileNotFoundError).
        rerun_flag = f'--rerunfailed "{Utilities.common_result_path}/output.xml"' if Utilities.re_run == "true" else ""
        command = (
            f'robot --output "{Utilities.common_result_path}/output.xml" --loglevel TRACE '
            f'-d "{Utilities.common_result_path}" {robot_vars} {rerun_flag} {testcases_name} '
            f'"{Utilities.project_path}/automation_test/tests/{Utilities.test_suite}"'
        )
        print("=======================         ROBOT COMMAND          =======================")
        print(command)
        subprocess.run(command, shell=True)

    @staticmethod
    def test_result_reporting():
        subprocess.run(
            f'python3 "{Utilities.project_path}/automation_test/python_lib/convert_fail_to_skip.py" '
            f'"{Utilities.common_result_path}" "{Utilities.common_result_path}"',
            shell=True,
        )
        # Quote từng arg — nếu link_screenshot_base rỗng (không dùng S3), string rỗng
        # nằm giữa 2 khoảng trắng sẽ bị shell nuốt mất, làm lệch vị trí sys.argv ở
        # create_index_file_table.py (bug đã xác nhận qua chạy thử thật: IndexError).
        subprocess.run(
            f'python3 "{Utilities.project_path}/automation_test/python_lib/create_index_file_table.py" '
            f'"{Utilities.common_result_path}" "{Utilities.link_screenshot_base}" "{Utilities.test_suite}"',
            shell=True,
        )

    @staticmethod
    def set_report_links():
        pass

    @staticmethod
    def push_report_to_s3_minio():
        pass

    @staticmethod
    def copy_output_file():
        shutil.copy2(
            f"{Utilities.common_result_path}/output.xml",
            f"{Utilities.common_result_path}/output_copy.xml",
        )

    @staticmethod
    def process_test_result_for_jenkins_display():
        # link_screenshot/link_report để rỗng khi không dùng S3 — vẫn phải có đủ
        # 4 attribute (env, account, link_screenshot, link_report) để số field
        # khớp với push_chat_apps.py parse_result() (luôn mong đợi 5 segment:
        # env/account/screenshot_url/report_url/stats — đúng theo cấu trúc dùng
        # thật trong project tham chiếu vtm_android). Bug đã xác nhận qua chạy
        # thử thật: thiếu 1 attribute ở đây làm lệch hết vị trí field phía sau.
        xml_content = (
            f"<total><stat env='{Utilities.env_run[:3].upper()}&lt;br /&gt;' "
            f"account='{Utilities.account}&lt;br /&gt;' "
            f"link_screenshot='&lt;br /&gt;' "
            f"link_report='&lt;br /&gt;'>All Tests</stat></total>"
        )
        with open(f"{Utilities.common_result_path}/link_results.xml", "w") as f:
            f.write(xml_content)
```

**Nếu user xác nhận có dùng S3/MinIO** — hỏi ở Step A1: **upload host** (host dùng cho `mc alias set`, vd `s3-devops.digital.vn`), **static/public host** dùng để tạo link xem báo cáo (**có thể khác** upload host — project tham chiếu vtm_android dùng `s3-static.digital.vn` cho link công khai trong khi upload qua `s3-devops.digital.vn`; nếu user chỉ có 1 host thì dùng chung cho cả hai), bucket, access key/secret. Thay 2 method này bằng bản có logic thật, fix cứng literal (cùng cách với Vops/Telegram):

```python
    MINIO_ACCESS_KEY = "<MINIO_ACCESS_KEY>"
    MINIO_SECRET_KEY = "<MINIO_SECRET_KEY>"

    @staticmethod
    def set_report_links():
        # Chỉ tính chuỗi URL — KHÔNG upload gì ở đây. Phải gọi hàm này (từ File 2,
        # run_testcases()) TRƯỚC test_result_reporting(), vì create_index_file_table.py
        # cần link_screenshot_base làm tham số để nhúng đúng link ảnh vào index.html.
        import urllib.parse
        import time
        # Timestamp riêng cho mỗi lần chạy — khớp đúng convention của project tham
        # chiếu vtm_android (vd "2026_07_02_10_51"). Không dùng chung 1 path cho
        # mọi lần chạy: (1) mỗi build sẽ ĐÈ MẤT report/log/screenshot của build
        # trước tại đúng key đó trên S3 — mất lịch sử; (2) browser cache theo URL,
        # cùng URL qua nhiều lần chạy sẽ hiển thị NHẦM nội dung cũ (bug đã xác
        # nhận qua chạy thử thật: user thấy ảnh cache cũ dù S3 đã có ảnh mới).
        # Thêm timestamp vào path giải quyết cả 2 vấn đề cùng lúc.
        Utilities.run_datestr = time.strftime("%Y_%m_%d_%H_%M_%S")
        # QUAN TRỌNG: `mc cp` nhận path THẬT trên S3 (giống filesystem), không phải
        # URL — phải dùng account RAW (chưa quote) cho lệnh mc cp, chỉ quote khi
        # ghép vào URL để hiển thị. Bug đã xác nhận qua chạy thử thật: dùng
        # urllib.parse.quote(account) làm path thật cho mc cp khiến S3 tạo ra
        # folder tên literal chứa ký tự "%20" (thay vì dấu cách thật), rồi URL lại
        # quote thêm 1 lần nữa lên trên path đã sai đó → link luôn trỏ sai key
        # (403/"specified key does not exist"), dù response 403 nhìn giống lỗi
        # quyền truy cập chứ không phải lỗi path.
        result_dir_name = Utilities.common_result_path.rstrip("/").split("/")[-1]  # raw, có thể chứa dấu cách
        dest_prefix_url = f"{Utilities.env_run}/{urllib.parse.quote(Utilities.account)}/{Utilities.run_datestr}"
        base_url = f"http://<MINIO_STATIC_HOST>/<BUCKET>/{dest_prefix_url}/{urllib.parse.quote(result_dir_name)}"
        Utilities.link_screenshot_base = f"{base_url}/"
        Utilities.link_screenshot = f"{base_url}/index.html"
        Utilities.link_report = f"{base_url}/report.html"
        # In ra console Jenkins để user xem trực tiếp trong build log mà không cần
        # bấm vào description — cùng format với project tham chiếu vtm_android.
        print("=======================      LIST OF RESULT FILES      =======================")
        print(f"Link Screenshot Error: {Utilities.link_screenshot}")
        print("=======================           LINK REPORT          =======================")
        print("Link Report", Utilities.link_report)

    @staticmethod
    def push_report_to_s3_minio():
        # Upload thật — PHẢI gọi (từ File 2) SAU test_result_reporting(), không
        # phải trước. Bug đã xác nhận qua chạy thử thật: gọi trước khi
        # test_result_reporting() tạo xong index.html khiến index.html không có
        # mặt trong lần upload — link "Screenshot" luôn ra lỗi not-found, dù
        # report.html vẫn OK (report.html do robot tự sinh ngay từ execute_test(),
        # nên đã tồn tại trước cả bước này).
        # dùng cùng run_datestr đã set ở set_report_links() — PHẢI khớp chính xác
        # với dest_prefix_url ở đó (chỉ khác account raw vs quote), không thì link
        # sẽ trỏ sai key giống hệt lớp bug account đã gặp trước đây.
        dest_prefix_raw = f"{Utilities.env_run}/{Utilities.account}/{Utilities.run_datestr}"  # dùng cho lệnh mc cp thật — KHÔNG quote
        try:
            subprocess.run(
                f"mc alias set minio http://<MINIO_UPLOAD_HOST> {Utilities.MINIO_ACCESS_KEY} {Utilities.MINIO_SECRET_KEY} > /dev/null",
                shell=True, check=True,
            )
            subprocess.run(
                f'mc cp "{Utilities.common_result_path}" '
                f'"minio/<BUCKET>/{dest_prefix_raw}/" --recursive > /dev/null',
                shell=True, check=True,
            )
        except subprocess.CalledProcessError as e:
            # Không để lỗi push (network/MinIO down) làm sập các bước report còn lại
            print(f"Push S3/MinIO failed: {e}")

    @staticmethod
    def process_test_result_for_jenkins_display():
        xml_content = (
            f"<total><stat env='{Utilities.env_run[:3].upper()}&lt;br /&gt;' "
            f"account='{Utilities.account}&lt;br /&gt;' "
            f"link_screenshot='&lt;a href={Utilities.link_screenshot}&gt;Screenshot&lt;/a&gt;&lt;br /&gt;' "
            f"link_report='&lt;a href={Utilities.link_report}&gt;Report&lt;/a&gt;&lt;br /&gt;'>All Tests</stat></total>"
        )
        with open(f"{Utilities.common_result_path}/link_results.xml", "w") as f:
            f.write(xml_content)
```

> **`<MINIO_UPLOAD_HOST>` vs `<MINIO_STATIC_HOST>`:** `push_report_to_s3_minio()` PHẢI chạy (set `link_screenshot`/`link_report`) **trước khi** `process_test_result_for_jenkins_display()` đọc chúng — đã đúng thứ tự sẵn trong `run_testcases()` ở File 2, không đổi thứ tự khi generate.

---

#### File 2c: `automation_test/python_lib/convert_fail_to_skip.py`

Được `test_result_reporting()` gọi. Generic cho mọi project — chuyển FAIL thành SKIP khi log lỗi chứa marker `[KNOWN_ISSUE]` (convention: test tự đánh dấu lỗi đã biết/không phải bug thật bằng cách chèn marker này vào message trước khi fail), rồi đếm lại tổng số pass/fail/skip trong `output.xml`.

```python
import sys
import xml.etree.ElementTree as ET

KNOWN_ISSUE_MARKER = "[KNOWN_ISSUE]"


def recount_test_status(root):
    total_pass, total_fail, total_skip = 0, 0, 0
    for test in root.findall(".//test"):
        status_elem = test.find("status")
        if status_elem is not None:
            result = status_elem.attrib.get("status")
            if result == "PASS":
                total_pass += 1
            elif result == "FAIL":
                total_fail += 1
            elif result == "SKIP":
                total_skip += 1
    return total_pass, total_fail, total_skip


def convert_fail_to_skip(input_dir, output_dir):
    tree = ET.parse(input_dir + "/output.xml")
    root = tree.getroot()

    for test in root.findall(".//test"):
        status_elem = test.find("status")
        if status_elem is not None and status_elem.attrib.get("status") == "FAIL":
            fail_message = (status_elem.text or "").strip()
            if KNOWN_ISSUE_MARKER in fail_message:
                status_elem.attrib["status"] = "SKIP"

    total_pass, total_fail, total_skip = recount_test_status(root)
    for total in root.findall(".//total"):
        stat = total.find("stat")
        if stat is not None:
            stat.attrib["pass"] = str(total_pass)
            stat.attrib["fail"] = str(total_fail)
            stat.attrib["skip"] = str(total_skip)

    tree.write(output_dir + "/output.xml", encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    convert_fail_to_skip(sys.argv[1], sys.argv[2])
```

---

#### File 2d: `automation_test/python_lib/create_index_file_table.py`

Được `test_result_reporting()` gọi. Generic — tạo `index.html` liệt kê toàn bộ file kết quả (screenshot, report) trong `common_result_path`, kèm bảng chi tiết các TC FAIL/SKIP-known-issue với log + ảnh lỗi. `extract_run_id` đọc số định danh lần chạy (account/run id) từ tên thư mục `results_<env>_<id>` — khớp với convention `common_result_path` đã dùng xuyên suốt skill này.

```python
import os
import re
import sys
import xml.etree.ElementTree as ET

KNOWN_ISSUE_MARKER = "[KNOWN_ISSUE]"


def read_detail_report(output_xml_path):
    results = []
    try:
        root = ET.parse(output_xml_path).getroot()
        for test in root.findall(".//test"):
            name = test.attrib["name"]
            status_elem = test[-1]
            status = status_elem.attrib["status"]
            if status == "PASS":
                results.append(f"{status}--{name}")
            else:
                results.append(f"{status}--{name}--{status_elem.text}")
    except Exception as e:
        print(e)
    return results


def extract_run_id(result_dir):
    last_dir = os.path.basename(os.path.normpath(result_dir))
    # [^_]+ cho phần env (production/uat/staging — không chứa "_"), rồi (.+)
    # (không phải \w+) lấy trọn phần account còn lại — account có thể chứa "_"
    # (vd "acc_login_01") nên không dùng \w+ (bug đã xác nhận qua chạy thử thật:
    # \w+ greedy cắt mất phần đầu, chỉ còn lại "01" thay vì "acc_login_01").
    match = re.match(r"results_[^_]+_(.+)$", last_dir)
    return match.group(1) if match else None


def create_index_file(result_dir, link_address, test_suite):
    detail_report = read_detail_report(result_dir + "/output.xml")
    with open(result_dir + "/index.html", "w", encoding="utf-8") as f:
        f.write(
            '<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
            "<style>table{border-collapse:collapse;width:100%}th,td{border:1px solid black;"
            "padding:8px;text-align:center}th{font-size:30px;background-color:#f2f2f2}"
            "h1{text-align:center}p.wrap{word-wrap:break-word;word-break:break-all}</style>"
            "</head><body><h1>Summary Report</h1><hr>"
        )
        run_id = extract_run_id(result_dir)
        if run_id:
            f.write(f'<h2 style="color:blue;">RUN ID: {run_id}</h2><hr>')

        f.write("<ul>")
        for filename in os.listdir(result_dir):
            if not filename.endswith(".png"):
                f.write(f'<li><a href="{link_address}{filename}">{filename}</a></li><br>')
        f.write("</ul>")

        failing = [
            row for row in detail_report
            if (parts := row.split("--"))[0] == "FAIL"
            or (parts[0] == "SKIP" and len(parts) > 2 and KNOWN_ISSUE_MARKER in parts[2])
        ]
        if failing:
            f.write("<table><tr><th>Test Case</th><th>Screenshot</th></tr>")
            for row in failing:
                parts = row.split("--")
                status, name = parts[0], parts[1]
                log = parts[2] if len(parts) > 2 else ""
                color = "red" if status == "FAIL" else "orange"
                log_html = f'<p class="wrap" style="font-family:courier;color:{color};">{log}</p>'
                img_path = f"{link_address}{name}.png"
                # KHÔNG fix cứng width="400" height="800" (khung dọc — giả định
                # screenshot mobile). Bug đã xác nhận qua chạy thử thật: với web
                # (screenshot khổ ngang), khung cứng đó bóp méo/cắt ảnh sai tỷ lệ.
                # Dùng max-width + height:auto để giữ đúng tỷ lệ gốc dù ảnh dọc
                # (mobile) hay ngang (web).
                f.write(
                    f"<tr><td><h3>{name}</h3>{log_html}</td>"
                    f'<td><img src="{img_path}" alt="{name}" style="max-width:500px;width:100%;height:auto;"></td></tr>'
                )
            f.write("</table>")
        f.write("</body></html>")


if __name__ == "__main__":
    create_index_file(sys.argv[1], sys.argv[2], sys.argv[3])
```

---

#### File 3: `automation_test/python_lib/read_output_file.py`

```python
import json
import os
import sys
import xml.etree.ElementTree as ET


def get_xml_root(file_path):
    tree = ET.parse(file_path)
    return tree.getroot()


try:
    result_text = ""
    if len(sys.argv) >= 3 and sys.argv[1].strip() == "":
        root = get_xml_root(sys.argv[2])
        stat = root.find('stat')
        if stat is not None:
            for value in stat.attrib.values():
                result_text += f"{value}\n"
        print(result_text)

    elif len(sys.argv) >= 2:
        root = get_xml_root(sys.argv[1])
        total_data = root[1][0][0].attrib
        total = sum(int(v) for v in total_data.values())
        new_data = {"total": str(total)}
        new_data.update(total_data)

        root2 = get_xml_root(sys.argv[2])
        stat = root2.find('stat')
        if stat is not None:
            for key, value in stat.attrib.items():
                if key == "env":
                    result_text += f"{value[:-6].upper()}<br />\n"
                else:
                    result_text += f"{value}\n"
        result_text += json.dumps(new_data) + "\n"
        os.remove(sys.argv[2])
        print(result_text)
    else:
        raise ValueError("Not enough arguments")

except Exception:
    print(json.dumps({"total": "0", "pass": "0", "fail": "0", "skip": "0"}) + "\n")
```

---

#### File 4: `automation_test/python_lib/push_chat_apps.py`

Hỏi user token/user id/bot token/chat id thật ở Step A1 rồi fix cứng literal vào file này (theo đúng cách file mẫu tham chiếu ban đầu làm) — **quyết định có chủ ý của user**, chấp nhận đánh đổi so với rule "never hardcode credentials" ở CLAUDE.md gốc cho riêng file chat-notification này. Vì vậy: **repo chứa Jenkinsfile/`push_chat_apps.py` này phải là private**, không được để public — nhắc user 1 lần duy nhất khi generate xong (Step A4), không hỏi lại mỗi lần update.

```python
import json
import os
import re
import ssl
import sys
import urllib.request

# ── Config — điền theo project ──────────────────────────────────────────────
VOPS_TOKEN        = "<VOPS_TOKEN>"
VOPS_USER_ID      = "<VOPS_USER_ID>"
VOPS_ROOM_ID      = "<VOPS_ROOM_ID>"
VOPS_GROUP_NAME   = "<VOPS_GROUP_NAME>"
VOPS_GROUP_LINK   = "<VOPS_GROUP_LINK>"

TELEGRAM_BOT_TOKEN = "<TELEGRAM_BOT_TOKEN>"   # để trống "" nếu không dùng
TELEGRAM_CHAT_ID   = "<TELEGRAM_CHAT_ID>"     # để trống "" nếu không dùng

MASTER_BRANCH     = "<MASTER_BRANCH>"
# Chỉ thêm dòng dưới nếu user có cấu hình test-management link ở Step A1 câu 8
# (dùng {account} làm placeholder) — bỏ hẳn dòng này (không để `None`/rỗng) nếu
# user không dùng, đừng để lại biến chết không ai gán.
SCENARIO_LINK_TEMPLATE = "<SCENARIO_LINK_TEMPLATE>"  # vd: "http://testing-platform.congty.vn/detail/{account}"
# ────────────────────────────────────────────────────────────────────────────


def send_message_vops(message: str):
    import random, string
    url = "https://vops.viettel.vn/api/v1/method.call/sendMessage"
    headers = {
        "Content-Type": "application/json",
        "Referer": VOPS_GROUP_LINK,
        "X-Auth-Token": VOPS_TOKEN,
        "X-User-Id": VOPS_USER_ID,
    }
    random_id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    # QUAN TRỌNG: field "message" phải là 1 CHUỖI JSON tự ghép tay (không phải
    # json.dumps() lồng bên trong) — API Vops (kiểu Rocket.Chat/DDP) mong đợi
    # payload bên trong là 1 JSON string, để json.dumps(data) ở dưới encode
    # đúng 1 lớp. Bug đã xác nhận qua chạy thử thật: dùng json.dumps() lồng 2
    # lớp làm literal "\n" trong `message` (từ format_summary) bị escape sai,
    # Vops hiển thị chữ "\n" thật trên màn hình thay vì xuống dòng.
    data = {
        "message": (
            '{"msg":"method","id":"65","method":"sendMessage",'
            '"params":[{"_id":"' + random_id + '","rid":"' + VOPS_ROOM_ID + '","msg":"' + message + '"}]}'
        )
    }
    req = urllib.request.Request(url, json.dumps(data).encode(), headers)
    try:
        urllib.request.urlopen(req, context=ssl._create_unverified_context())
    except Exception as e:
        print(f"Vops send failed: {e}")


def send_message_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import urllib.parse
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data, method="POST"), timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")


def parse_result(raw: str) -> dict:
    # 5 segment, khớp đúng số attribute mà process_test_result_for_jenkins_display()
    # (common_utilities.py) ghi vào link_results.xml: env, account, link_screenshot,
    # link_report, stats — đúng theo cấu trúc dùng thật trong project tham chiếu
    # (vtm_android: env, phone_number, screenshot_url, report_url, result). Bug đã
    # xác nhận qua chạy thử thật: nếu common_utilities.py ghi thiếu/thừa 1 attribute
    # so với đây, mọi field phía sau sẽ lệch vị trí.
    lines = raw.split("---")
    env_map = {"PRO": "production", "UAT": "uat", "STA": "staging", "STO": "STORE"}
    env = env_map.get(lines[0].strip(), lines[0].strip())
    result = {
        "env": env,
        "account": lines[1].strip() if len(lines) > 1 else "",
        "screenshot_url": lines[2].strip() if len(lines) > 2 else "",
        "report_url": lines[3].strip() if len(lines) > 3 else "",
        "result": lines[4].strip() if len(lines) > 4 else "",
    }
    return result


def is_pass(description: str) -> bool:
    m = re.search(r'fail:\s?(\d+)', description)
    return bool(m and int(m.group(1)) == 0)


def get_failing_tests(output_xml_path: str) -> list:
    # Đọc output.xml lấy danh sách TC FAIL kèm message — để đưa chi tiết lỗi vào
    # tin Vops. Đọc trực tiếp từ output_xml_path (argv[2], đã có sẵn) thay vì
    # nhét thêm field vào chuỗi BUILD_TAG "---"-separated — tránh lặp lại đúng
    # lớp bug lệch-vị-trí-field đã gặp nhiều lần khi thêm field mới vào đó.
    import xml.etree.ElementTree as ET
    results = []
    try:
        root = ET.parse(output_xml_path).getroot()
        for test in root.findall(".//test"):
            status = test[-1]
            if status.attrib.get("status") == "FAIL":
                results.append((test.attrib["name"], (status.text or "").strip()))
    except Exception as e:
        print(f"Không đọc được chi tiết lỗi: {e}")
    return results


def format_summary(data: dict, failing_tests: list = None, scenario_link: str = None) -> str:
    # Format khớp đúng tin nhắn thật team đang nhận trên Vops (đối chiếu trực
    # tiếp, không phải suy đoán): KHÔNG có header "SUMMARY REPORT", KHÔNG có
    # dòng env riêng — chỉ account, các link, TOTAL, rồi tới chi tiết từng TC
    # fail (mỗi TC 2 dòng: "❌ - <tên>" rồi tới message lỗi, cách nhau 1 dòng
    # trống). Cách build "total" (replace chuỗi nối tiếp) giữ đúng quy ước thật
    # — không đổi dù nhìn có vẻ ngược (:white_check_mark: gắn trước "fail", :x:
    # gắn trước "skip") vì đó là format team đang quen nhìn.
    total = data["result"].replace(":", ": ").replace("total", "TOTAL") \
        .replace("pass", " - pass").replace("fail", " :white_check_mark: - fail") \
        .replace("skip", " :x: - skip") + " :warning:"
    lines = ["`" + data["account"] + "`"]
    # screenshot_url/report_url có thể rỗng khi không dùng S3/MinIO — chỉ thêm
    # dòng khi thật sự có link, tránh gửi dòng trống lên Vops.
    if data.get("screenshot_url"):
        lines.append(data["screenshot_url"])
    if data.get("report_url"):
        lines.append(data["report_url"])
    if scenario_link:  # chỉ có khi user cấu hình test-management link ở Step A1
        lines.append(scenario_link)
    lines.append(total)
    if failing_tests:
        lines.append("")
        for i, (name, msg) in enumerate(failing_tests):
            if i > 0:
                lines.append("")
            lines.append(f":x: - {name}")
            if msg:
                lines.append(msg)
    return "\\n".join(lines)


def add_text_to_image(image_path: str, label: str) -> str:
    # Dán tên TC lên ảnh trước khi gộp — khớp đúng tính năng add_text_to_image()
    # của project tham chiếu vtm_android. Lưu ra file MỚI (không ghi đè
    # image_path gốc) — screenshot gốc không cần sửa gì thêm ở bước này (đã
    # upload lên S3 xong từ trước, trong push_report_to_s3_minio()), tránh phụ
    # thuộc vào thứ tự gọi hàm giữa 2 tiến trình khác nhau (runner script vs
    # push_chat_apps.py). Vẽ thêm nền đen phía sau chữ để chữ trắng luôn đọc
    # được dù ảnh nền màu gì.
    from PIL import Image, ImageDraw
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, img.height - 24), (img.width, img.height)], fill="black")
    draw.text((6, img.height - 20), label, fill="white")
    labeled_path = image_path[:-4] + "_labeled.png"  # bỏ ".png", thêm hậu tố
    img.save(labeled_path)
    img.close()
    return labeled_path


def concatenate_images(image_paths: list, columns: int = 3):
    from PIL import Image
    images = [Image.open(p) for p in image_paths]
    col = min(columns, len(images))
    row = -(-len(images) // col)  # ceil
    w = max(im.width for im in images)
    h = max(im.height for im in images)
    grid = Image.new("RGB", (w * col, h * row), color=(255, 255, 255))
    for i, im in enumerate(images):
        grid.paste(im, ((i % col) * w, (i // col) * h))
        im.close()
    return grid


def upload_image_vops(file_path: str, description: str):
    # Multipart tự ghép tay bằng bytes thật (không round-trip qua ISO-8859-1
    # như project tham chiếu) — tránh rủi ro hỏng dữ liệu nhị phân khi ảnh có
    # byte không map gọn qua encode/decode text.
    import mimetypes
    url = f"https://vops.viettel.vn/api/v1/rooms.upload/{VOPS_ROOM_ID}"
    headers = {
        "Origin": "https://vops.viettel.vn",
        "Referer": VOPS_GROUP_LINK,
        "X-Auth-Token": VOPS_TOKEN,
        "X-User-Id": VOPS_USER_ID,
    }
    boundary = "----jenkinsSkillBoundary"
    file_name = os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="description"\r\n\r\n{description}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    # Vops API có thể trả HTTP 200 kèm body {"success": false, "error": "..."} —
    # urlopen() không tự raise cho trường hợp này (chỉ raise khi status 4xx/5xx),
    # nên phải tự đọc + kiểm tra body, không thì lỗi bị nuốt êm hoàn toàn (bug đã
    # xác nhận qua chạy thử thật: ảnh không lên Vops nhưng không có log lỗi nào).
    with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as resp:
        resp_body = resp.read().decode("utf-8", errors="replace")
        try:
            resp_json = json.loads(resp_body)
        except json.JSONDecodeError:
            resp_json = None
        if resp_json is not None and resp_json.get("success") is False:
            raise RuntimeError(f"Vops rejected upload: {resp_body}")
        print(f"Vops upload response: {resp_body[:300]}")


def push_image_telegram(file_path: str, caption: str = ""):
    # Bỏ qua êm nếu không cấu hình Telegram — cùng quy ước với send_message_telegram().
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import mimetypes
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    boundary = "----jenkinsSkillBoundary"
    file_name = os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    fields = [("chat_id", TELEGRAM_CHAT_ID)]
    if caption:
        fields.append(("caption", caption))
    body = b""
    for key, value in fields:
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
        ).encode()
    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="{file_name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        # Telegram Bot API trả JSON với "ok": false kèm HTTP status lỗi (400 v.v.)
        # cho hầu hết trường hợp — khác Vops (200 kèm success:false) — nhưng vẫn tự
        # đọc + kiểm tra "ok" thay vì chỉ dựa vào urlopen() không raise, cho nhất
        # quán với cách xử lý upload_image_vops() và không bỏ sót trường hợp lạ.
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            try:
                resp_json = json.loads(resp_body)
            except json.JSONDecodeError:
                resp_json = None
            if resp_json is not None and resp_json.get("ok") is False:
                print(f"Telegram từ chối ảnh: {resp_body}")
            else:
                print(f"Telegram photo response: {resp_body[:200]}")
    except Exception as e:
        print(f"Telegram photo send failed: {e}")


def push_merged_screenshots(failing_tests: list, result_dir: str):
    # Gộp screenshot của các TC fail (file <tên_TC>.png trong result_dir, do
    # library chụp màn hình lúc fail tạo ra — vd SeleniumLibrary/AppiumLibrary)
    # thành 1 ảnh lưới rồi upload lên Vops + Telegram (nếu có cấu hình). Bỏ qua êm
    # (không raise) nếu thiếu PIL/Pillow hoặc không tìm thấy ảnh nào — tính năng
    # bổ sung, không được làm sập pipeline chính.
    try:
        import PIL  # noqa: F401 — chỉ kiểm tra PIL có cài trên agent không
    except ImportError:
        print("PIL/Pillow chưa cài trên agent — bỏ qua gộp ảnh lỗi (cài `pip3 install Pillow` nếu muốn dùng).")
        return
    originals = [
        (name, p) for name, _ in failing_tests
        if os.path.exists(p := os.path.join(result_dir, f"{name}.png"))
    ]
    if not originals:
        return
    merged_path = os.path.join(result_dir, "merged_failures.png")
    labeled_paths = []
    try:
        for name, path in originals:
            labeled_paths.append(add_text_to_image(path, name))
        concatenate_images(labeled_paths).save(merged_path)
        upload_image_vops(merged_path, "ảnh lỗi")
        push_image_telegram(merged_path, "ảnh lỗi")
    except Exception as e:
        print(f"Gộp/upload ảnh lỗi thất bại: {e}")
    finally:
        if os.path.exists(merged_path):
            os.remove(merged_path)
        for p in labeled_paths:
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: push_chat_apps.py <BUILD_TAG> <output_xml_path> <branch_name>")
        sys.exit(1)

    build_tag   = sys.argv[1]
    xml_path    = sys.argv[2]
    branch_name = sys.argv[3]

    data = parse_result(build_tag)
    failing_tests = get_failing_tests(xml_path) if xml_path and os.path.exists(xml_path) else []
    # Chỉ tính scenario_link nếu SCENARIO_LINK_TEMPLATE có khai báo ở phần Config
    # phía trên (Step A1 câu 8). Nếu user không dùng tính năng này thì xoá hẳn
    # biến SCENARIO_LINK_TEMPLATE khỏi Config và dòng try/except này luôn — đừng
    # để lại code chết tham chiếu biến không tồn tại.
    try:
        scenario_link = SCENARIO_LINK_TEMPLATE.format(account=data["account"])
    except NameError:
        scenario_link = None
    message = format_summary(data, failing_tests, scenario_link)

    send_message_vops(message)
    send_message_telegram(message.replace("\\n", "\n"))

    if failing_tests and xml_path:
        push_merged_screenshots(failing_tests, os.path.dirname(xml_path))

    if xml_path and os.path.exists(xml_path):
        os.remove(xml_path)
```

---

### Step A3.5 — Verify files vừa generate

Trước khi in checklist Step A4, chạy 2 bước verify sau:

**1. `py_compile`** — bắt lỗi cú pháp/import:

```bash
python3 -m py_compile automation_test/config/<RUNNER_SCRIPT>.py automation_test/python_lib/common_utilities.py automation_test/python_lib/convert_fail_to_skip.py automation_test/python_lib/create_index_file_table.py automation_test/python_lib/read_output_file.py automation_test/python_lib/push_chat_apps.py
```

> **Lưu ý:** `py_compile` **không** bắt được lỗi kiểu gọi `Utilities.<attr>` mà `<attr>` không tồn tại trong class `Utilities` (lỗi runtime `AttributeError`, không phải lỗi cú pháp — đã tự kiểm chứng bằng test thực tế, không phải suy đoán). Vì vậy cần thêm bước 2.

**2. Cross-check attribute `Utilities.*`** giữa File 2 (runner script) và File 2b (`common_utilities.py`) — đây là lớp lỗi thực tế đã từng xảy ra (bug `Utilities.data_env` không tồn tại):

```python
import re, sys
runner_code = open('automation_test/config/<RUNNER_SCRIPT>.py').read()
sys.path.insert(0, 'automation_test')
from python_lib.common_utilities import Utilities
referenced = sorted(set(re.findall(r'Utilities\.(\w+)', runner_code)))
missing = [a for a in referenced if not hasattr(Utilities, a)]
if missing:
    print(f"MISSING ATTRS: {missing}")
```

Nếu `missing` không rỗng → sửa `common_utilities.py` (thêm attribute/method thiếu) hoặc sửa runner script (bỏ tham chiếu thừa), rồi chạy lại. Không báo "xong" khi còn attribute thiếu.

Cả 2 bước đều không bắt được lỗi logic runtime khác (vd sai đường dẫn thật, sai schema YAML, lỗi Groovy trong Jenkinsfile) — vì skill không có môi trường Jenkins thật để chạy full pipeline.

---

### Step A4 — Jenkins Setup

Sau khi generate files xong, hỏi user **1 câu duy nhất** trước khi làm gì tiếp:

> Bạn muốn tự làm theo checklist thủ công, hay để skill **tự tạo + config job trên Jenkins qua REST API**?

- Không trả lời / chọn thủ công → dùng **Step A4a — Checklist thủ công** (giữ nguyên như cũ, không đổi).
- Chọn tự động → dùng **Step A4b — Tự tạo job qua Jenkins API**.

**Ranh giới cố định cho cả 2 nhánh (không bao giờ đổi, không phụ thuộc user chọn gì):**
- **Không bao giờ tự tạo/sửa Jenkins Credentials** — credential ID phải đã tồn tại sẵn, skill chỉ tham chiếu bằng ID user cung cấp.
- **Không bao giờ tự cài plugin** — plugin (Active Choices, Pipeline Utility Steps...) phải đã cài sẵn, skill chỉ kiểm tra/nhắc, không cài hộ.
- **Không bao giờ tự tạo agent/node** — agent label phải đã online sẵn.
- Việc "tự tạo job qua API" chỉ giới hạn ở: tạo Multibranch Pipeline job + trỏ đúng Branch Source (git URL + credentialsId có sẵn) + trigger scan — không mở rộng ra ngoài phạm vi này.

---

#### Step A4a — Checklist thủ công

**Đây chỉ là phân tích + lời khuyên cho user tự làm** — skill không tự gọi Jenkins API/CLI để cài plugin, tạo credentials, tạo agent/node, hay bất kỳ thay đổi nào khác lên Jenkins server, dù có khả năng kỹ thuật để làm việc đó. Nếu skill detect được thiếu gì (vd thiếu credential, thiếu plugin) → chỉ nêu ra trong checklist, không tự động sửa.

> **Checklist config Jenkins Multibranch Pipeline:**
>
> **0. Điều kiện tiên quyết (phải có trước khi tạo job):**
> - **Commit & push** 7 file vừa generate lên remote (`git add`, `git commit`, `git push`) — Jenkins Multibranch Pipeline chỉ quét thấy `Jenkinsfile` khi nó đã có trên branch ở remote, không phải chỉ ở local. Skill không tự làm bước này (chỉ commit khi user yêu cầu) — nhắc để user tự chạy.
> - Credential `<CREDENTIALS_ID>` đã được tạo trong Jenkins → Manage Jenkins → Credentials → tạo mới nếu chưa có
> - Node/agent mang label `<AGENT_LABEL>` đã online và nhận job
>
> **1. Tạo Multibranch Pipeline job:**
> - Jenkins → New Item → Multibranch Pipeline → đặt tên → OK
>
> **2. Branch Sources:**
> - Add source → Git
> - Project Repository: `<GIT_SSH_URL>`
> - Credentials: chọn `<CREDENTIALS_ID>`
>
> **3. Filter by name (Branch Filter):**
> - Behaviors → Add → Filter by name (with regular expression)
> - Include: `<MASTER_BRANCH>|<MASTER_BRANCH>_.*` *(hoặc pattern phù hợp)*
>
> **4. Build Configuration:**
> - Mode: by Jenkinsfile
> - Script Path: `automation_test/Jenkinsfile`
>
> **5. Scan Multibranch Pipeline Triggers:**
> - Tích "Periodically if not otherwise run" → Interval: `1 hour` *(tùy chọn)*
>
> **6. Save → Scan Multibranch Pipeline Now**
>
> **7. Cài plugin** (nếu chưa có):
> - **Active Choices** — cần cho CascadeChoiceParameter (typeRun/account/testSuite/testcases)
> - **Pipeline Utility Steps** — cần cho `readYaml()` ở stage "Reload Jenkinsfile & parameters"
> - Manage Jenkins → Plugins → Available → tìm tên plugin → Install
>
> **8. Công cụ CLI trên agent** (nếu chưa có — skill không tự cài, chỉ nhắc):
> - **`mc`** (MinIO Client) — bắt buộc nếu dùng S3/MinIO (Step A1 câu 5). `mc alias set`/`mc cp` trong `push_report_to_s3_minio()` sẽ fail nếu agent chưa có `mc` trên PATH.
> - **Pillow** (`pip3 install Pillow`) — chỉ cần nếu muốn tính năng gộp ảnh lỗi gửi Vops (`push_merged_screenshots()`). Không bắt buộc — nếu thiếu, skill tự bỏ qua êm (in log, không làm fail build), chỉ mất phần ảnh gộp.
>
> **⚠️ Nếu dùng `triggerByCICD = true` HOẶC có đặt lịch chạy tự động (`triggers { cron(...) }`, Step A1 câu 3):** Jenkinsfile đọc `automation_test/data/param_file.yaml` ở stage "Reload Jenkinsfile & parameters" — **file này skill không tự sinh**, phải tự tạo tay theo schema:
> ```yaml
> <account_1>:
>   pullCode: "true"
>   runOnDeviceFarm: "true"   # chỉ cần field này nếu platform là android/ios — bỏ hẳn khỏi YAML nếu web/api (Jenkinsfile không đọc field này cho web/api)
>   testSuite: "<file.robot>"
>   testcases: "TC_001,TC_002"   # hoặc để trống "" để chạy toàn bộ suite
> <account_2>:
>   pullCode: "false"
>   runOnDeviceFarm: "true"
>   testSuite: "<file2.robot>"
>   testcases: ""
> ```
> **`testSuite`/`testcases` bắt buộc phải có trong YAML nếu có đặt lịch chạy (cron)** — bug đã xác nhận qua chạy thử thật: build do cron tự bắn không đi qua Jenkins UI, nên `CascadeChoiceParameter` phụ thuộc param khác (`testSuite`, `testcases`) luôn rỗng (giới hạn thật của Active Choices Plugin, chỉ param KHÔNG phụ thuộc gì — như `typeRun` — mới giữ đúng giá trị `:selected`). Thiếu 2 field này trong YAML → build cron sẽ fail ở stage "Run test". Nếu chỉ dùng `triggerByCICD` cho hệ thống CI/CD ngoài (không dùng cron) và hệ thống đó tự truyền `testSuite`/`testcases` qua params khi trigger → có thể bỏ trống 2 field này trong YAML, Jenkinsfile sẽ tự fallback về `params.testSuite`/`params.testcases`.
> Nếu không dùng `triggerByCICD` và không đặt lịch (chỉ chạy tay qua Jenkins UI) → bỏ qua, không cần file này.
>
> **⚠️ Credential đã fix cứng literal** trong `push_chat_apps.py` (Vops/Telegram token) và `common_utilities.py` (MinIO access key/secret nếu có dùng) — theo yêu cầu, không đọc từ biến môi trường. **Repo này phải để private**, không push lên nơi công khai. Muốn đổi token → `/autotest-jenkins cập nhật token vops`.
>
> **CascadeChoiceParameter:** đã được generate đầy đủ trong Jenkinsfile (kể cả khi chưa có data thật — dùng skeleton nhóm `Default`). Không cần viết Groovy tay. Muốn bổ sung nhóm/account/suite/TC sau này → chạy `/autotest-jenkins thêm nhóm ...`, `/autotest-jenkins thêm account ...` (nếu project có tách theo account), `/autotest-jenkins thêm testcase ...`.

---

#### Step A4b — Tự tạo job qua Jenkins API

Chỉ chạy nhánh này khi user **chủ động chọn** ở câu hỏi đầu Step A4 — không bao giờ tự ý làm mà không hỏi trước, vì đây là hành động ghi vào hạ tầng thật, không đảo ngược dễ dàng.

**1. Hỏi đủ thông tin (1 message, gộp hết):**

> - **Jenkins base URL** — URL gốc, không phải URL của 1 job cụ thể (vd `https://autotest-jenkins.congty.com/jenkins`, không phải `.../job/xxx/`)
> - **Vị trí tạo job** — root hay trong 1 folder có sẵn? Nếu trong folder → tên folder (folder phải đã tồn tại sẵn, skill không tự tạo folder)
> - **Tên job** (mặc định = tên project)
> - **API user + API token** của 1 tài khoản Jenkins đã có quyền `Job/Create` + `Job/Configure` — user tự tạo token này (Jenkins → User → Configure → API Token), skill không tạo hộ
>
> Nhắc lại 3 điều kiện vẫn phải có sẵn (skill không tự làm): credential `<CREDENTIALS_ID>` đã tồn tại trong Jenkins, agent label `<AGENT_LABEL>` đã online, plugin Active Choices + Pipeline Utility Steps đã cài.

**2. Bảo mật token — quy tắc bắt buộc:**
- **Không bao giờ ghi token vào bất kỳ file nào trong repo** (không SKILL.md, không file generate, không log file).
- Chỉ dùng token trong lệnh gọi API của phiên làm việc hiện tại (biến môi trường tạm hoặc tham số lệnh trực tiếp), không lưu lại sau khi xong việc.
- Nhắc user 1 lần: nếu token từng bị dán vào nơi không an toàn (chat, file, ticket...), nên revoke/tạo token mới sau khi xong.

**3. Verify kết nối + auth trước khi làm gì khác:**

```bash
curl -s -o /dev/null -w "%{http_code}" -u "<API_USER>:<API_TOKEN>" "<BASE_URL>/api/json"
```

- `200` → tiếp tục. `401`/`403` → **dừng lại ngay**, báo lỗi rõ (sai user/token, hoặc token hết hạn/bị revoke) — không đoán mò thử lại nhiều lần, không tự ý đổi username/token.
- Không kết nối được (timeout/DNS fail) → dừng, báo user kiểm tra mạng/URL — môi trường chạy skill có thể không có đường mạng tới Jenkins nội bộ.

**4. Lấy CSRF crumb** (Jenkins mặc định bật CSRF protection cho request ghi):

```bash
curl -s -u "<API_USER>:<API_TOKEN>" "<BASE_URL>/crumbIssuer/api/json"
# → lấy .crumbRequestField và .crumb từ JSON trả về, dùng làm header cho bước POST
```

**5. Build config.xml cho Multibranch Pipeline job — ưu tiên lấy template thật từ chính server đó:**

> **Quan trọng — job mẫu chỉ để lấy đúng SCHEMA, không copy VALUE:** nếu dùng 1 job có sẵn (vd job của project khác) làm tham chiếu, chỉ lấy cấu trúc XML/tên class đúng version plugin đang cài trên server đó. **Toàn bộ giá trị thật** (git URL, `credentialsId`, branch filter pattern, tên job) **luôn phải lấy từ thông tin user đã cung cấp ở Step A1 cho đúng project đang tạo** (`<GIT_SSH_URL>`, `<CREDENTIALS_ID>`, `<MASTER_BRANCH>`) — không bao giờ bê nguyên giá trị của job mẫu (dù user có nói "làm giống job X" — đó là nói về kiểu cấu trúc, không phải giá trị). Nếu chưa rõ giá trị nào, hỏi lại user, không tự suy đoán/copy từ job khác.

- Nếu trong cùng folder/Jenkins đã có sẵn ít nhất 1 Multibranch Pipeline job khác → `GET <job_url_có_sẵn>/config.xml` để lấy nguyên bản XML thật (đảm bảo đúng schema/version plugin đang chạy trên server đó), rồi thay **toàn bộ** giá trị: git URL, `credentialsId`, branch filter pattern, `scriptPath` bằng thông tin thật của project đang tạo job. Cách này an toàn hơn hẳn so với tự đoán XML, nhưng chỉ mượn cấu trúc — không mượn nội dung. **Luôn ưu tiên nhánh này khi có thể** — đây là cách chắc chắn nhất để job tạo ra tương thích 100% với server đích.
- Nếu chưa có job mẫu nào trong folder đích (folder mới, chưa từng tạo Multibranch job nào) → dùng template chuẩn dưới đây. Template này đã được verify thực tế (đối chiếu `config.xml` thật lấy từ 1 Jenkins server production đang chạy branch-api 2.x / scm-api 690.x / git-plugin 5.x, 2026-07-07) — không phải đoán mò. Các attribute `plugin="..."` **cố tình bỏ version** (vd `plugin="branch-api"` thay vì `plugin="branch-api@2.1169..."`) vì version thật khác nhau tuỳ server; Jenkins không cần pin version để resolve class, chỉ cần đúng tên class/package:

```xml
<?xml version='1.1' encoding='UTF-8'?>
<org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject plugin="workflow-multibranch">
  <actions/>
  <description></description>
  <properties/>
  <folderViews class="jenkins.branch.MultiBranchProjectViewHolder" plugin="branch-api">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </folderViews>
  <healthMetrics>
    <com.cloudbees.hudson.plugins.folder.health.WorstChildHealthMetric plugin="cloudbees-folder">
      <nonRecursive>false</nonRecursive>
    </com.cloudbees.hudson.plugins.folder.health.WorstChildHealthMetric>
  </healthMetrics>
  <icon class="jenkins.branch.MetadataActionFolderIcon" plugin="branch-api">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </icon>
  <orphanedItemStrategy class="com.cloudbees.hudson.plugins.folder.computed.DefaultOrphanedItemStrategy" plugin="cloudbees-folder">
    <pruneDeadBranches>true</pruneDeadBranches>
    <daysToKeep>-1</daysToKeep>
    <numToKeep>-1</numToKeep>
    <abortBuilds>false</abortBuilds>
  </orphanedItemStrategy>
  <triggers>
    <com.cloudbees.hudson.plugins.folder.computed.PeriodicFolderTrigger>
      <spec>H/60 * * * *</spec>
      <interval>3600000</interval>
    </com.cloudbees.hudson.plugins.folder.computed.PeriodicFolderTrigger>
  </triggers>
  <disabled>false</disabled>
  <sources class="jenkins.branch.MultiBranchProject$BranchSourceList" plugin="branch-api">
    <data>
      <jenkins.branch.BranchSource>
        <source class="jenkins.plugins.git.GitSCMSource" plugin="git">
          <id>generated-by-jenkins-skill</id>
          <remote><GIT_SSH_URL></remote>
          <credentialsId><CREDENTIALS_ID></credentialsId>
          <traits>
            <jenkins.plugins.git.traits.BranchDiscoveryTrait/>
            <jenkins.scm.impl.trait.WildcardSCMHeadFilterTrait plugin="scm-api">
              <includes><MASTER_BRANCH>|<MASTER_BRANCH>_*</includes>
              <excludes></excludes>
            </autotest-jenkins.scm.impl.trait.WildcardSCMHeadFilterTrait>
          </traits>
        </source>
        <strategy class="jenkins.branch.DefaultBranchPropertyStrategy">
          <properties class="empty-list"/>
        </strategy>
      </autotest-jenkins.branch.BranchSource>
    </data>
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </sources>
  <factory class="org.jenkinsci.plugins.workflow.multibranch.WorkflowBranchProjectFactory">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
    <scriptPath>automation_test/Jenkinsfile</scriptPath>
  </factory>
</org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>
```

> **Lưu ý:** `jenkins.scm.impl.trait.WildcardSCMHeadFilterTrait` (namespace `scm-api`) là class **đúng** trên các server Jenkins hiện đại (branch-api ≥ 2.x) — namespace cũ `jenkins.plugins.git.traits.WildcardSCMHeadFilterTrait` (đã bị xoá khỏi bản sửa này) có thể không tồn tại nữa trên git-plugin mới, khiến job tạo ra lỗi ngay khi Jenkins parse `config.xml`. Nếu server đích cực cũ và vẫn dùng git-plugin cũ, nhánh "lấy schema từ job mẫu có sẵn" ở trên vẫn là lựa chọn an toàn hơn — chỉ dùng template chuẩn này khi thực sự không có job nào để tham chiếu.

**6. Hiện preview đầy đủ trước khi tạo — bắt buộc, không bỏ qua:**

> Sắp tạo job **`<tên job>`** tại **`<BASE_URL>/<job/folder/>createItem?name=<tên job>`**, dùng credential `<CREDENTIALS_ID>` (có sẵn), git `<GIT_SSH_URL>`, branch filter `<MASTER_BRANCH>|<MASTER_BRANCH>_*`. Xác nhận tạo?

**7. Tạo job (chỉ sau khi user xác nhận ở bước 6):**

```bash
curl -s -X POST "<BASE_URL>/<đường dẫn folder nếu có>/createItem?name=<tên job>&mode=org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" \
  -u "<API_USER>:<API_TOKEN>" \
  -H "<crumbRequestField>: <crumb>" \
  -H "Content-Type: application/xml" \
  --data-binary @config.xml
```

**8. Trigger scan** để Jenkins quét thấy `Jenkinsfile` trên remote (nhắc lại: phải đã `git push` trước — xem Step A4a mục 0):

```bash
curl -s -X POST "<BASE_URL>/<đường dẫn job vừa tạo>/build" \
  -u "<API_USER>:<API_TOKEN>" -H "<crumbRequestField>: <crumb>"
```

**9. Báo kết quả:** thành công (kèm link job) hoặc lỗi thật (HTTP code + response body, không suy diễn nguyên nhân nếu không chắc) → user tự xử lý tiếp nếu lỗi liên quan tới credential/plugin/agent (skill không tự sửa các phần đó).

---

## Mode B — Update (Cập nhật)

### Step B1 — Đọc Jenkinsfile hiện tại

```python
with open('automation_test/Jenkinsfile', 'r') as f:
    content = f.read()
print(content[:500])  # preview để xác nhận đúng file
```

### Step B2 — Xác định loại thay đổi

Trước tiên xác định project này đang dùng cấu trúc nào (đọc Jenkinsfile: có `referencedParameters` chứa `account` không → "Có tách"; không có param `account` nào → "Không tách"). Sau đó phân tích ý định từ argument:

**Nếu project "Không tách" (typeRun → testSuite → testcases):**

| Ý định | Hành động |
|---|---|
| "thêm testcase TC99 vào nhóm X" | Tìm `case "X"` trong `testcases` block → thêm TC vào list |
| "xoá testcase TC99 khỏi nhóm X" | Tìm `case "X"` trong `testcases` block → xoá đúng dòng TC |
| "thêm nhóm mới `<Tên nhóm>`" | Thêm 3 chỗ đồng thời: (1) list trong `typeRun` (Block 1), (2) case mới trong `testSuite` (Block 2), (3) case mới trong `testcases` (Block 4) — thiếu 1 trong 3 sẽ làm Jenkins UI hiện danh sách rỗng |
| "xoá nhóm `<Tên nhóm>`" | **Cảnh báo trước khi xoá**: liệt kê suite/TC đang gắn với nhóm này → hỏi xác nhận, vì xoá sẽ xoá cascade ở cả 3 block trên |
| "chuyển sang có tách theo account" | Đây là đổi cấu trúc (thêm Block account), xem "Đổi cấu trúc" bên dưới |

**Nếu project "Có tách theo account" (typeRun → account → testSuite → testcases):**

| Ý định | Hành động |
|---|---|
| "thêm testcase TC99 vào account 84362579294" | Tìm `case "84362579294"` trong `testcases` block → thêm TC vào list |
| "xoá testcase TC99 khỏi account 84362579294" | Tìm `case "84362579294"` trong `testcases` block → xoá đúng dòng TC |
| "thêm account mới 84999... vào nhóm X" | Thêm case mới vào `account` (Block 2), `testSuite` (Block 3), `testcases` (Block 5) — nhóm X phải đã tồn tại ở `typeRun` |
| "xoá account 84999..." | Xoá case `<account>` khỏi cả `account` (Block 2, list của nhóm cha), `testSuite` (Block 3), `testcases` (Block 5) |
| "thêm nhóm mới `<Tên nhóm>`" | Thêm 4 chỗ đồng thời: (1) list trong `typeRun` (Block 1), (2) case mới trong `account` (Block 2), (3) case mới trong `testSuite` (Block 3), (4) case mới trong `testcases` (Block 5) — thiếu 1 trong 4 sẽ làm Jenkins UI hiện danh sách rỗng |
| "xoá nhóm `<Tên nhóm>`" | **Cảnh báo trước khi xoá**: liệt kê account/suite/TC con của nhóm này → hỏi xác nhận, vì xoá sẽ xoá cascade ở cả 4 block (1, 2, 3, 5) |

**Chung cho cả 2 cấu trúc:**

| Ý định | Hành động |
|---|---|
| "thêm param enableDebugLogs" | Thêm `booleanParam` vào `parameters([...])` |
| "cập nhật token vops" | Sửa `VOPS_TOKEN` trong `push_chat_apps.py` |
| "thêm môi trường preprod" | Thêm vào `choices` của `envRun` |
| "đổi agent label" | Sửa `agent { label "..." }` |
| "thêm lịch chạy mỗi ngày 2h sáng" / "đặt lịch chạy tự động ..." | Nếu Jenkinsfile **chưa có** `triggers{}` → thêm cả block `triggers { cron('<CRON_EXPR>') }` (quy đổi mô tả sang cron syntax). Nếu **đã có** → sửa giá trị trong `cron('...')`. Nhắc lại đúng 1 lần lưu ý: build theo lịch dùng tham số mặc định (nhóm/TC có `:selected`), không phải do user chọn tay. |
| "xoá lịch chạy" / "tắt chạy tự động" | Xoá cả block `triggers { ... }` khỏi Jenkinsfile |

> **Lưu ý về cascade:** các block CascadeChoiceParameter tham chiếu lẫn nhau qua `referencedParameters`, nên thêm/xoá ở tầng cha (`typeRun`, hoặc `account` nếu có) luôn kéo theo thay đổi ở các block con. Không sửa 1 block rồi bỏ qua các block còn lại — sẽ để lại case orphan (tồn tại ở block cha nhưng không có nhánh tương ứng ở block con → Jenkins UI trả về list rỗng). `count_size` không cần sửa tay vì tự tính `testcases.size()`.
>
> **Đổi cấu trúc (từ "Không tách" sang "Có tách theo account" hoặc ngược lại):** đây là thay đổi lớn — cảnh báo user trước, vì phải: thêm/xoá hẳn 1 block (`account`), sửa `referencedParameters` của `testSuite` và `testcases`, và sửa dòng `account = "$typeRun"` ↔ `account = "$account"` trong `environment{}`. Show diff đầy đủ trước khi ghi, không tự ý làm ngầm.

### Step B3 — Áp dụng thay đổi

- Với mỗi thay đổi: hiển thị **diff trước** (old vs new) → xác nhận → ghi file
- Chỉ sửa đúng phần liên quan, không đụng phần khác
- Format: giữ nguyên indentation và style của file gốc

### Step B4 — Confirm

Sau khi sửa xong:
> Đã cập nhật `automation_test/Jenkinsfile`:
> - [liệt kê các thay đổi đã làm]
>
> Bạn có muốn thay đổi gì thêm không?

---

## Rules

- **Không hardcode credentials trong Jenkinsfile.** Riêng `push_chat_apps.py` (Vops/Telegram token) và `common_utilities.py` (MinIO access key/secret nếu có dùng push S3): hỏi user giá trị thật rồi fix cứng literal (quyết định có chủ ý của user, khác với rule chung "never hardcode credentials" ở CLAUDE.md gốc) — nhắc user 1 lần ở Step A4 rằng repo phải để private.
- **Không tạo file đè lên file có sẵn** mà không hỏi trước
- **Parameters block** (CascadeChoiceParameter) luôn được generate đầy đủ Groovy (5 hoặc 6 block tuỳ cấu trúc đã chọn ở Step A2), kể cả khi chưa có data thật (dùng skeleton nhóm `Default`) — không bao giờ để lại comment yêu cầu viết tay. Bổ sung data thật về sau qua Mode B.
- **Update mode**: chỉ sửa đúng phần được yêu cầu, show diff trước khi ghi
- **Submodule**: chỉ generate block submodule nếu user cung cấp submodule URL
- Khi thiếu thông tin → hỏi **1 lần**, gộp tất cả câu hỏi còn thiếu vào 1 message
- **Jenkins server — ranh giới cố định, không đổi dù user chọn nhánh nào ở Step A4:** không bao giờ tự tạo/sửa credentials, không bao giờ tự cài plugin, không bao giờ tự tạo agent/node — 3 thứ này luôn phải có sẵn, skill chỉ tham chiếu bằng tên/ID user cung cấp.
- **Tạo/config job trên Jenkins qua API** (Step A4b) chỉ làm khi **user chủ động chọn** ở câu hỏi đầu Step A4 — mặc định (không trả lời) luôn là checklist thủ công (Step A4a). Khi làm A4b: verify auth trước khi làm gì khác, hiện preview + xác nhận trước khi POST tạo job thật, không tự ý thử lại nhiều lần khi auth fail. Token API không bao giờ ghi vào file trong repo.
- **Validate suite `.robot` tồn tại** ở Step A2 trước khi generate — cảnh báo (không chặn) nếu chưa thấy file trong `automation_test/tests/`.
- **Verify bằng `py_compile`** sau khi generate xong 6 file Python (Step A3.5) — bắt lỗi cú pháp/reference trước khi báo "xong", không chờ tới lúc build thật trên Jenkins mới phát hiện.
- **Không tự commit/push** file vừa generate lên git — chỉ nhắc user tự làm ở Step A4 (đúng theo git safety protocol chung: chỉ commit khi user yêu cầu).
- **Luôn quote MỌI tham số vị trí** khi ghép lệnh `sh`/`subprocess.run(..., shell=True)` — kể cả tham số "tưởng chừng an toàn" (boolean, số). Một giá trị rỗng không quote sẽ biến mất khỏi câu lệnh (không phải thành chuỗi rỗng), làm lệch vị trí mọi tham số phía sau — lớp bug này đã gặp lại nhiều lần ở nhiều nơi khác nhau (account có dấu cách, testSuite rỗng do cron trigger...). Không có ngoại lệ "chắc chắn không rỗng".
- **Lịch chạy cron (`triggers { cron(...) }`) bắt buộc đi kèm `param_file.yaml`** khai `testSuite`/`testcases` cho account sẽ chạy — Active Choices Plugin không tính lại cascade param cho build không tương tác qua UI, thiếu YAML sẽ crash. Xem chi tiết Step A1 câu 3 + Step A4a mục 8.
- **Tên nhóm/account nên tránh dấu cách** (khuyến nghị, không bắt buộc) — dùng làm tên thư mục, segment URL, tham số dòng lệnh xuyên suốt pipeline; có dấu cách vẫn chạy đúng (đã quote đủ chỗ) nhưng dễ phát sinh lỗi mới hơn khi có thay đổi sau này.
