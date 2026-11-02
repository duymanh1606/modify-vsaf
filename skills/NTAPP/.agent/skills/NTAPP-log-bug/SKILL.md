---
name: NTAPP-log-bug
description: Use when the user reports a bug/defect to be logged — gives a bug description plus optionally the screen (UI bug, with screenshot) and/or the API endpoint where it occurs. Records the bug into BUGS-<SLICE-ID>-<account>.md under NTAPP-output/Stage_1_Discovery/Bugs_Issues, auto-resolving which SLICE the affected feature belongs to via its WBS unit, append-only. Optionally pushes the same bug to Jira (Type = Bug for real defects, Type = Issue for system shortcomings needing a decision) with full description + screenshots + Assignee, then writes the Jira link back into the log file.
---

# Log Bug

## Overview
Ghi nhận 1 bug vào file log bug theo SLICE. Skill tự xác định feature bị lỗi thuộc SLICE nào (qua WBS unit) rồi append bug vào đúng file `BUGS-<SLICE-ID>-<account>.md`.

**Nguyên tắc cốt lõi:** 1 file / 1 slice / 1 account, **append-only** — thêm bug mới KHÔNG sửa/xoá bug đã có.

**2 nhánh:**
| Nhánh | Làm gì |
|---|---|
| **Local** (default) | Bước 0-5: ghi bug vào file log + ảnh vào `assets/`. |
| **+ Jira** (opt-in) | Bước 0-5 y hệt, rồi Bước 6: tạo issue Jira (`Bug` / `Issue`) kèm ảnh + Assignee, và ghi link Jira trở lại entry trong file log. |

## When to use
- User báo 1 lỗi và muốn lưu lại / log lại.
- Có mô tả bug; kèm (tuỳ chọn) màn hình + ảnh chụp, và/hoặc API phát sinh lỗi.
- User muốn đẩy bug đó lên Jira ("log bug lên jira", "tạo ticket jira cho lỗi này").

## Inputs
| Input | Bắt buộc | Ghi chú |
|---|---|---|
| Mô tả bug | ✅ | Lỗi gì, xảy ra khi nào |
| Màn hình (UI bug) | tuỳ | Tên/mô tả màn; ảnh chụp **dán trực tiếp trong chat** nếu có |
| API phát sinh bug | tuỳ | Path + method, vd `POST /api/composite/composites` |
| Đẩy lên Jira? | tuỳ | Mặc định KHÔNG. Hỏi ở Bước 6.1 (bỏ qua câu hỏi nếu user đã nói rõ từ đầu) |
| Assignee (chỉ khi đẩy Jira) | tuỳ | Username Jira; để trống = không gán |

Thiếu mô tả bug → hỏi user. User nói có ảnh nhưng chưa dán → nhắc user **dán/đính kèm ảnh ngay trong khung chat** rồi mới ghi (KHÔNG hỏi đường dẫn file có sẵn).

## Workflow

### Bước 0 — Xác định account người log
`account` dùng để đặt tên file, tránh 2 người log cùng lúc ghi chung 1 file gây conflict khi merge.

Thứ tự lấy: `git config user.name` → Username trong block Jira của `env.md` → hỏi user.

**Slugify trước khi dùng:** bỏ dấu tiếng Việt, khoảng trắng và ký tự đặc biệt → `-`, lowercase.
`dinhtq8` → `dinhtq8` · `Đinh Trọng Quang` → `dinh-trong-quang`.

### Bước 1 — Xác định WBS unit bị ảnh hưởng
Map input → WBS ID (`SCR-*`, `WGT-*`, `HUB-*`, `MPF-*`, `BIL-*`, `PMT-EXT-*`, ...):
- **Từ màn hình:** tìm SCR/WGT ID trong `NTAPP-output/Stage_2_Architecture/project_wbs.md` theo tên/mô tả màn (vd "màn tạo composite" → `SCR-COMPOSE`).
- **Từ API:** grep path trong `NTAPP-output/Stage_3_Specs/techspec/`, `NTAPP-output/Stage_4_Design/detailed_design/`, hoặc code để tìm unit sở hữu endpoint (vd `/api/composite/composites` → `HUB-02`). Fallback: tra trong `project_wbs.md`.
- Có thể ra nhiều unit (màn + API) — giữ tất cả để ghi vào entry; dùng unit chính để tra slice.

### Bước 2 — Xác định SLICE
**Helper là đường mặc định; grep là đường lui khi không có helper.** Đường dẫn thư mục slice, ranh giới mã slice và chuẩn hoá zero-pad có **một** hiện thực chuẩn: `hooks/lib/slice_paths.py`.

```
python3 {project-root}/hooks/lib/slice_paths.py --find-unit <UNIT-ID>
```
*(Windows không có `python3` trên PATH — dò theo thứ tự `py -3` → `python3` → `python`.)*

In ra `unit_slices<TAB><đường dẫn manifest>`, mỗi slice một dòng; `slice_id` nằm ở frontmatter file đó.

**Đọc mã thoát, đừng chỉ đếm số dòng:**

| Thoát | Nghĩa | Làm gì |
|---|---|---|
| `0`, có dòng | tìm thấy | nhiều dòng → chọn slice khớp ngữ cảnh bug; vẫn mơ hồ → hỏi user |
| `0`, **không** dòng | đã tra, **không slice nào build unit này** | hỏi user mã SLICE (feature có thể là AS-IS ngoài slice plan) |
| `3` | **không tra được** — thư mục slice không tồn tại | **DỪNG** và báo dòng `WARNING` ở stderr. Đây **không** phải "không có slice" |
| `2` | `<UNIT-ID>` sai dạng | xem lại Bước 1 |

> ⚠️ **Vì sao phải tách `0`-rỗng khỏi `3`.** Bản trước bước này grep thẳng vào `Stage_5_Build_Verify/slices/` — một thư mục **chưa từng tồn tại**. `rg` trả rỗng, skill rơi xuống nhánh *"không slice nào chứa → hỏi user"*, và mọi lượt chạy trông vẫn bình thường. Bước này **hỏng suốt từ đó tới nay** mà không ai thấy, đúng vì *"tra rồi, không có"* và *"không tra được"* in ra giống hệt nhau. Helper tách hai thứ ấy; đừng gộp lại.

#### Fallback — không tìm thấy `slice_paths.py`

Skill chưa sync, hoặc đang chạy ngoài cây framework → **KHÔNG dừng**, grep theo đường dẫn mặc định:

```
rg -l --glob 'SLICE-*.md' --glob '!**/archive/**' "id:\s*<UNIT-ID>\b" NTAPP-output/Stage_2_Architecture/slices/
```

Ba mảnh của lệnh này đều là lỗi đã xảy ra thật, đừng lược:

| Mảnh | Thiếu nó thì |
|---|---|
| `Stage_2_Architecture/slices/` | grep vào `Stage_5_Build_Verify/slices/` — thư mục chưa từng tồn tại, luôn trả rỗng |
| `'!**/archive/**'` | mỗi slice trả **2 file** — bản sống và bản trong `archive/_v1_*/`, nội dung gần giống nhau nên chọn nhầm không có gì báo |
| `\b` cuối | `BE-INV-1` bắt luôn `BE-INV-10`, `-11`, … |

**Ranh giới của đường lui — nói ra để đừng tin quá:** grep rỗng ở đây **không** tách được *"không slice nào build unit này"* khỏi *"tra sai chỗ"*. Đó đúng là thứ helper sinh ra để tách. Nên khi fallback trả rỗng thì **hỏi user mã SLICE**, đừng kết luận là unit nằm ngoài slice plan. Và ghi rõ trong output rằng đã đi đường fallback.

- User đã cho sẵn mã SLICE → bỏ qua Bước 1-2.

### Bước 3 — Lưu ảnh chụp
**Nguyên tắc:** KHÔNG bịa / tái tạo nội dung ảnh từ chat — phải có **file ảnh thật** rồi mới nhúng. Dùng 1 helper cross-OS `capture-bug-image.sh` (macOS + Windows Git Bash/WSL). **Ưu tiên dò file trong folder trước; clipboard chỉ là fallback** — vì 1 bug thường kèm **nhiều ảnh**, mà clipboard chỉ giữ được 1.

1. **Liệt kê ảnh mới + trạng thái clipboard:**
   ```
   <skill-dir>/capture-bug-image.sh --minutes 20
   ```
   Quét đúng nơi hot-key mặc định lưu theo OS — **macOS**: `~/Desktop` (default `Cmd+Shift+3/4/5`) + folder cấu hình qua `defaults` (`com.apple.screencapture location`) + Downloads/Pictures/Documents; **Windows**: `Pictures\Screenshots` (default `Win+PrtScn`) + Downloads/Desktop. In block `RECENT FILES` (mới nhất trước, tối đa 10, kèm time / bytes / path) + `CLIPBOARD: HAS_IMAGE | NONE`. Nếu có block `BLOCKED` → macOS TCC chặn đọc folder đó (xem note cuối) → xử lý theo hướng dẫn rồi chạy lại.

2. **Ưu tiên file (hỗ trợ nhiều ảnh / 1 bug):** với mỗi candidate hợp lý, `Read` dưới dạng ảnh, so khớp nội dung với ảnh user dán trong chat. Khớp → `cp` vào assets (path bước 4 dưới). Nhiều ảnh khớp → copy hết, hậu tố `-1`, `-2`.

3. **Fallback clipboard** — chỉ khi `RECENT FILES` không có / không khớp **mà** `CLIPBOARD: HAS_IMAGE`:
   ```
   <skill-dir>/capture-bug-image.sh --clip NTAPP-output/Stage_1_Discovery/Bugs_Issues/assets/<SLICE-ID>/<account>/<SLICE-ID>-<account>-BUG-NN.png
   ```
   `SAVED: <path>` → xong. `NO_IMAGE_IN_CLIPBOARD` → sang bước 5.

4. **Đường dẫn assets & nhúng:** lưu vào `NTAPP-output/Stage_1_Discovery/Bugs_Issues/assets/<SLICE-ID>/<account>/<SLICE-ID>-<account>-BUG-NN.png` (tạo thư mục nếu chưa có; nhiều ảnh → `-1`, `-2`, vd `SLICE-20-dinhtq8-BUG-01-1.png`). Tên ảnh **trùng mã bug** để nhìn file là biết thuộc bug nào. Nhúng relative path từ file log: `![<SLICE-ID>-<account>-BUG-NN](assets/<SLICE-ID>/<account>/<SLICE-ID>-<account>-BUG-NN.png)`.

5. **Không lấy được ảnh nào** (không file khớp + clipboard trống) → nhắc user lưu ảnh thành file rồi báo đường dẫn (macOS: `Cmd+Shift+4` lưu Desktop; Windows: `Win+Shift+S` lưu `Pictures\Screenshots`). TUYỆT ĐỐI KHÔNG bịa nội dung ảnh.

> **macOS (TCC):** `~/Desktop` và `~/Documents` là folder được bảo vệ — tiến trình chạy skill có thể bị chặn đọc (hiện `BLOCKED` trong output), kể cả khi đó là nơi screenshot mặc định lưu (`~/Desktop`). Khi gặp `BLOCKED`, báo user chọn 1 trong: (a) cấp **Full Disk Access** cho app terminal / Claude Code ở *System Settings → Privacy & Security → Full Disk Access* rồi chạy lại; (b) đổi nơi lưu screenshot sang `~/Downloads` (`Cmd+Shift+5 → Options → Save to`) — thường đọc được không cần cấp quyền; hoặc (c) dùng fallback clipboard (chỉ 1 ảnh).
>
> **Windows:** clipboard đọc qua `powershell.exe` có thể trả `NONE` do session-isolation → cứ dựa vào nhánh dò file (bước 1-2) là chính; đó cũng là lý do đặt folder scan trước.

### Bước 4 — Ghi vào file BUGS-<SLICE-ID>-<account>.md
**Đường mặc định là helper — đừng tự ghép chuỗi khi còn helper:**

```
python3 {project-root}/hooks/lib/slice_paths.py --resolve <SLICE-ID> --json
```

Dùng `slice_id` (đã chuẩn hoá), `bugs_dir`, `assets_dir` trong kết quả. File cần ghi là `<bugs_dir>/BUGS-<slice_id>-<account>.md`.

> ⚠️ **`<SLICE-ID>` user gõ KHÔNG phải mã để đặt tên file.** Skill này nhiều chỗ viết ví dụ `SLICE-06`, trong khi trên đĩa là `SLICE-6-…`. Ghép thẳng chuỗi user gõ sẽ **tạo file thứ hai** cho cùng một slice (`BUGS-SLICE-06.md` nằm cạnh `BUGS-SLICE-6.md`) — và vì cả hai đều tồn tại, không có gì báo lỗi; bug chỉ đơn giản là **rơi vào file mà người đi sửa không mở**. Trường `slice_id` của helper luôn là dạng chuẩn duy nhất (không zero-pad). Dùng nó cho **cả** tên file lẫn `assets_dir`.

#### Fallback — không tìm thấy `slice_paths.py`

Tự dựng lại đúng ba thứ helper trả về. **Thứ tự quan trọng: chốt `slice_id` trước, vì hai đường dẫn kia đều treo vào nó.**

1. **`slice_id` — hỏi đĩa, đừng tin chuỗi user gõ.** Gọi `<n>` là phần số đã bỏ số 0 ở đầu (`SLICE-06` → `6`):
   ```
   rg --files --glob 'SLICE-<n>-*.md' --glob 'SLICE-0<n>-*.md' --glob '!**/archive/**' NTAPP-output/Stage_2_Architecture/slices/
   ```
   Có file → `slice_id` là tiền tố `SLICE-…` của **chính tên file đó** (đĩa là trọng tài, không phải quy tắc trong đầu). Không file nào → dùng dạng bỏ zero-pad, và nói với user rằng slice này không có manifest.
2. **`bugs_dir`** = `NTAPP-output/Stage_1_Discovery/Bugs_Issues/`
3. **`assets_dir`** = `<bugs_dir>/assets/<slice_id>/` — `<slice_id>` ở bước 1, không phải chuỗi user gõ.

Thư mục ở (2) **không tồn tại** → DỪNG, báo user; đừng `mkdir`. Lý do y hệt nhánh thoát `3` bên dưới.

Ghi rõ trong output rằng đã đi đường fallback.

- **File chưa tồn tại / rỗng:** tạo mới với header (Bước 5) + entry bug đầu tiên (`BUG-01`).
- **File đã tồn tại:** đọc file, tìm số bug lớn nhất hiện có → entry mới = số kế tiếp. **Chỉ APPEND** entry mới vào cuối file, KHÔNG đụng entry cũ.
- **Helper trả thoát `3`** (thư mục bug không tồn tại) → **DỪNG**, báo user. Không tự `mkdir` rồi ghi: một cây thư mục mới sinh ra ở sai chỗ sẽ trông y hệt cây đúng.

Bug ID format: `<SLICE-ID>-<account>-BUG-NN` (NN 2 chữ số, vd `SLICE-20-dinhtq8-BUG-01`).

**Đánh số độc lập theo từng file** — chỉ quét `BUGS-<SLICE-ID>-<account>.md` của chính account đang log, KHÔNG quét file của account khác. Vì `<account>` đã nằm trong mã bug nên **mã bug là duy nhất toàn project** dù mỗi người đánh số riêng: `SLICE-20-dinhtq8-BUG-01` và `SLICE-20-dinhtq9-BUG-01` là 2 bug khác nhau, gọi tên là biết ngay của ai và ở slice nào.

### Bước 5 — Template

Header file (chỉ khi tạo mới):
```markdown
# BUGS — <SLICE-ID>: <slice title> (log by <account>)

> Log bug cho <SLICE-ID>, người log: <account>. Append-only: thêm bug mới KHÔNG sửa bug cũ.
> Units thuộc slice: <list unit IDs>
```

Entry bug (append mỗi bug):
```markdown
---

## <SLICE-ID>-<account>-BUG-NN — <tiêu đề ngắn>

- **Trạng thái:** Open
- **Severity:** Critical | High | Medium | Low
- **Màn hình / API:** <màn hình> / <API path + method>
- **WBS unit:** <unit IDs>
- **Người báo:** <reporter>
- **Ngày báo:** <YYYY-MM-DD>

**Mô tả:**
<mô tả lỗi>

**Các bước tái hiện:**
1. ...

**Kết quả mong đợi:** <...>
**Kết quả thực tế:** <...>

**Ảnh chụp:**
![<SLICE-ID>-<account>-BUG-NN](assets/<SLICE-ID>/<account>/<SLICE-ID>-<account>-BUG-NN.png)
```
Bỏ dòng **Ảnh chụp** nếu không có ảnh; bỏ **Các bước tái hiện / Kết quả mong đợi / thực tế** nếu user không cung cấp đủ (đừng bịa).

Dòng `- **Jira:**` KHÔNG viết ở bước này — chỉ chèn ở Bước 6.7 sau khi tạo issue thành công.

### Bước 6 — (tuỳ chọn) Đẩy bug lên Jira

Chỉ chạy khi user muốn. **Thứ tự cố định: ghi file xong (Bước 4-5) TRƯỚC, tạo Jira SAU** — Jira lỗi (mạng / credential / field bắt buộc) thì bug vẫn đã được log, chỉ cảnh báo và cho retry, không mất dữ liệu.

Helper: `<skill-dir>/jira_bug.py` (chỉ stdlib, 3 subcommand `probe` / `find-user` / `create`). Mọi output là 1 dòng JSON. Trên Windows luôn chạy `python -X utf8 jira_bug.py ...` để tránh lỗi cp1252 khi in tiếng Việt.

#### 6.1 — Hỏi có đẩy Jira không
User đã nói rõ từ đầu ("log lên jira", "tạo ticket") → bỏ qua câu hỏi, đi tiếp. Chưa nói → hỏi 1 câu: *"Đẩy bug này lên Jira không?"*. Không đẩy → dừng, báo đường dẫn file log là xong.

#### 6.2 — Project key
Đọc `jira.project_key` trong `.bmm-config.yaml` ở project root (repo chứa `NTAPP-output/`):
```yaml
jira:
  project_key: <KEY>
```
Chưa có block → hỏi user project key, tạo/append block trên vào `.bmm-config.yaml`, lần sau tự đọc. User chỉ định key khác trong câu lệnh → dùng key đó, KHÔNG sửa config.

Thiếu `env.md` (credential) → script trả `ok:false` kèm danh sách path đã thử. Báo user tạo `env.md` theo mẫu `<skill-dir>/env.example.md` rồi chạy lại **chỉ Bước 6** (file log đã ghi xong, KHÔNG log lại).

#### 6.3 — Probe project + chọn Type
```
python -X utf8 <skill-dir>/jira_bug.py probe --project <KEY>
```
Trả `type_names` (issue type project cho phép tạo) + `required_fields` từng type (field bắt buộc ngoài các field skill tự điền).

**Phân loại — skill tự đề xuất kèm lý do, user confirm hoặc đổi:**

| Type | Dấu hiệu |
|---|---|
| `Bug` | Hành vi lệch spec / DD / techspec; exception / stacktrace; sai số liệu; UI vỡ layout; API sai status code / sai format; regression so với bản chạy được trước đó. |
| `Issue` | Code chạy đúng như đang thiết kế nhưng nghiệp vụ chưa hợp lý; thiếu định nghĩa cho case biên chưa ai chốt; 2 tài liệu nói khác nhau; đề xuất cải tiến UX. Tóm lại: **cần người chốt trước khi làm được**. |

Không chắc → nêu cả 2 khả năng và để user chọn, KHÔNG tự quyết im lặng.

`type_names` không có type cần dùng (project không expose `Issue` chẳng hạn) → in danh sách type khả dụng và hỏi user chọn lại. KHÔNG tự đổi sang type khác.

`required_fields` của type đã chọn có field chưa biết giá trị → **hỏi user**, đừng bịa. Truyền qua `--fields-json '{"<field_id>": <value>}'` (field có `allowedValues` → dùng dạng `{"value":"..."}`).

**Ví dụ thực tế** — project `TTCNSPQT`, type `Bug` bắt 3 field (type `Issue` không bắt field nào). Luôn chạy `probe` để lấy danh sách đúng của project đang dùng, KHÔNG copy cứng bảng này:

| Field | id | Giá trị hợp lệ |
|---|---|---|
| Bug Type | `customfield_13241` | Performance / Logic / Enviroment / Config / GUI / UI |
| Giai đoạn phát hiện | `customfield_15544` | Testing / UAT |
| Severity | `customfield_11205` | Critical / Major / Minor |

```
--fields-json '{"customfield_13241":{"value":"Logic"},"customfield_15544":{"value":"Testing"},"customfield_11205":{"value":"Major"}}'
```

⚠️ **Thang Severity của Jira có thể khác thang trong file log** (`Critical/High/Medium/Low`). KHÔNG gửi thẳng giá trị lấy từ file log — map về đúng `allowedValues` mà `probe` trả về (vd `High → Major`, `Medium`/`Low` → `Minor`) và cho user xác nhận bản map. Gửi sai giá trị → Jira trả HTTP 400.

#### 6.4 — Assignee
Hỏi user gán cho ai. Có tên → validate:
```
python -X utf8 <skill-dir>/jira_bug.py find-user --query <keyword>
```
Không ra kết quả → báo user và hỏi lại; nhiều kết quả → cho user chọn. User để trống / nói không gán → bỏ `--assignee`, issue không có assignee.

#### 6.5 — Soạn description (Jira wiki markup)
Ghi ra file tạm UTF-8 trong scratchpad (KHÔNG truyền multi-line qua command line), rồi truyền `--description-file`. Nội dung phải **khớp với entry trong file log** — cùng mô tả, cùng steps, cùng expected/actual, cùng ảnh:

```
h3. Thông tin
||Thuộc tính||Giá trị||
|Bug ID|<SLICE-ID>-<account>-BUG-NN|
|SLICE|<SLICE-ID>|
|WBS unit|<unit IDs>|
|Màn hình / API|<màn hình> / <API path + method>|
|Severity|<Critical/High/Medium/Low>|
|Người báo|<reporter>|
|Ngày báo|<YYYY-MM-DD>|
|File log|BUGS-<SLICE-ID>-<account>.md|

h3. Mô tả
<mô tả lỗi>

h3. Các bước tái hiện
# <bước 1>
# <bước 2>

h3. Kết quả mong đợi
<...>

h3. Kết quả thực tế
<...>

h3. Ảnh chụp
!<SLICE-ID>-<account>-BUG-NN-1.png|thumbnail!
```
- Bỏ section nào user không cung cấp (giống Bước 5 — không bịa).
- Dòng `!<tên file>.png|thumbnail!` phải **đúng basename của ảnh được attach**; Jira render được vì ảnh attach ngay sau khi tạo issue trong cùng lệnh `create`.

#### 6.6 — Tạo issue + attach ảnh
```
python -X utf8 <skill-dir>/jira_bug.py create \
  --project <KEY> --type <Bug|Issue> \
  --summary "[<SLICE-ID>-<account>-BUG-NN] <tiêu đề ngắn>" \
  --description-file <scratchpad>/jira-desc.txt \
  --assignee <username> \
  --labels <SLICE-ID> --labels <UNIT-ID> \
  --attach NTAPP-output/Stage_1_Discovery/Bugs_Issues/assets/<SLICE-ID>/<account>/<SLICE-ID>-<account>-BUG-NN-1.png
```
- `--labels` / `--attach` lặp lại nhiều lần cho nhiều giá trị. Label = `<SLICE-ID>` + các WBS unit ID (label Jira không được có khoảng trắng — ID vốn đã hợp lệ).
- Output: `{"ok":true,"key":"...","url":"...","attached":[...],"attach_errors":[...]}`.
- `attach_errors` khác rỗng → issue **vẫn giữ**, báo user tên file chưa attach lên được (có thể attach tay trên Jira), KHÔNG tạo lại issue.

#### 6.7 — Ghi link Jira trở lại file log
Chèn 1 dòng ngay **dưới** dòng `- **Trạng thái:**` của entry vừa append:
```markdown
- **Jira:** [<KEY>](<url>) — Type: <Bug|Issue>
```
Đây là lần duy nhất được sửa entry — và chỉ sửa entry **vừa tạo trong lượt này**. Vẫn KHÔNG đụng entry cũ (append-only).

#### 6.8 — Báo cáo cuối
In: đường dẫn file log · Bug ID · Jira key + url + Type + Assignee · số ảnh đã attach (kèm cảnh báo nếu có `attach_errors`).

## Status lifecycle
`Open → In Progress → Fixed → Closed` (thêm `Reopened` nếu bug tái xuất). Log mới luôn bắt đầu `Open`.

Trạng thái trong file log và trạng thái trên Jira **không tự đồng bộ** — skill này chỉ tạo issue lúc log. Đổi trạng thái sau đó là việc thủ công ở cả 2 nơi.

## Reporter / Date mặc định
- **Người báo:** lấy từ user hiện tại (handle/email); không rõ thì hỏi.
- **Ngày báo:** ngày hiện tại, định dạng `YYYY-MM-DD`.

## Portability
`jira_bug.py` KHÔNG hardcode path máy nào: credential dò theo `$NTAPP_JIRA_ENV` → `./env.md` → `<skill-dir>/env.md` → `~/Documents/.env/env.md` → `~/env.md`; base URL lấy từ `--url` → `JIRA_URL=` trong `env.md` → URL trong header block Jira. Project key đến từ `.bmm-config.yaml` của project. **KHÔNG commit `env.md` thật** — chỉ commit `env.example.md`.

## Common mistakes
- ❌ Ghi đè / sửa bug cũ khi thêm bug mới → chỉ APPEND (ngoại lệ duy nhất: chèn dòng `Jira:` vào entry vừa tạo ở Bước 6.7).
- ❌ Đoán đại SLICE → phải tra qua WBS unit; mơ hồ thì hỏi.
- ❌ Bịa steps / expected / actual khi user không cung cấp → để trống mục đó.
- ❌ Đánh số bug trùng trong cùng file → luôn quét số lớn nhất hiện có trong file của mình trước khi append.
- ❌ Quên `<account>` trong **mã bug** / tên file / đường dẫn assets → quay lại đúng cảnh 2 người ghi chung 1 file, mã bug trùng nhau, conflict khi merge.
- ❌ Quên copy ảnh vào `assets/<SLICE-ID>/<account>/` → link ảnh sẽ chết.
- ❌ Tạo Jira TRƯỚC khi ghi file log → Jira lỗi là mất luôn bug.
- ❌ Tự quyết `Bug` vs `Issue` khi tín hiệu mơ hồ → phải để user chốt.
- ❌ Bịa giá trị field bắt buộc của project (duedate, customfield_*) cho đủ payload → phải hỏi user.
- ❌ Truyền description multi-line trực tiếp trên command line → dùng `--description-file`.
- ❌ In token / password ra màn hình khi debug credential.
