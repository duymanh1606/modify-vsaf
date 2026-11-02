---
name: NTAPP-sprint-worklog-from-git
description: Từ một mã sprint (vd 6.2.26), tự bóc ngày bắt đầu/kết thúc sprint rồi quét git tất cả repo trong workspace để liệt kê các đầu việc chính người dùng đã làm, gom theo repo + chủ đề, ước lượng ET, và xuất ra block đúng format /NTAPP-jira-subtask-creator để người dùng duyệt trước khi log work. Use when the user wants to "tổng hợp việc đã làm trong sprint", "bóc worklog từ git", "log work sprint từ git", "liệt kê đầu việc sprint", "chuẩn bị logwork sprint <mã>". KHÔNG tự gọi Jira / không tự log work.
user-invocable: true
argument-hint: <mã sprint, vd 6.2.26> [--root <path>]... [--author <pattern>]... [--start YYYY-MM-DD --due YYYY-MM-DD]
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# /NTAPP-sprint-worklog-from-git — Bóc worklog sprint từ git

## Arguments

`$ARGUMENTS` — **mã sprint** dạng `M.N.YY` (vd `6.2.26`, `7.1.26`). Bắt buộc.
Optional (đều **lặp lại được**):
- `--root <path>` — **THÊM** một workspace root vào danh sách quét (không thay thế danh sách đã có).
- `--author <pattern>` — **THÊM** một git identity của người dùng (tên hoặc email, khớp kiểu regex).
- `--start YYYY-MM-DD --due YYYY-MM-DD` — chỉ định thẳng ngày sprint, bỏ qua Bước 1.

Nếu không có mã sprint (và cũng không có `--start`/`--due`) → **hỏi người dùng**, dừng. KHÔNG tự bịa.

## Mục tiêu

Nhập mã sprint → tự bóc ngày → quét git tất cả repo → gom đầu việc của người dùng → ước ET → in ra block đúng format `/NTAPP-jira-subtask-creator` để người dùng **duyệt**.

> **Ranh giới cứng:** skill này CHỈ đọc git và in text. KHÔNG gọi Jira API, KHÔNG log work, KHÔNG tạo issue. Người dùng tự copy block sang `/NTAPP-jira-subtask-creator` khi đã duyệt.

> **Nguyên tắc portable:** skill này KHÔNG chứa đường dẫn, tên người, hay email của bất kỳ ai. Mọi thứ riêng của từng người/máy đều nằm ở file config bên ngoài (Bước 0) hoặc được tự dò lúc chạy. Khi sửa skill, TUYỆT ĐỐI không hardcode giá trị cá nhân vào file này.

---

## Bước 0 — Nạp config người dùng (tùy chọn, không có vẫn chạy)

Skill chạy được với **zero config**. Config chỉ để nhớ câu trả lời của các lần trước, khỏi phải hỏi lại mỗi sprint.

Dò file `sprint-worklog.md` theo thứ tự, lấy file đầu tiên tìm thấy:
1. thư mục hiện tại
2. thư mục skill này
3. `~/Documents/.env/sprint-worklog.md`
4. `~/.sprint-worklog.md`

Format (xem `config.example.md` trong thư mục skill):

```markdown
# roots
<đường dẫn workspace 1>
<đường dẫn workspace 2>

# identities
<git username>
<email cá nhân dùng ở một số repo>

# non-code-items
[<tên đội>] Họp hành sprint <sprint>
Hỗ trợ support các hệ thống
```

Không tìm thấy config → **không dừng**, chạy chế độ tự dò (Bước 2/3 sẽ hỏi người dùng), rồi ở Bước 7 mời người dùng lưu lại.

## Bước 1 — Bóc ngày sprint (tái dùng script, KHÔNG tính nhẩm)

Nếu người dùng đã truyền `--start`/`--due` → dùng luôn, bỏ qua bước này.

Ngược lại, tìm script suy ngày ở skill anh em (dò bằng glob, KHÔNG hardcode tên thư mục đầy đủ):
`<thư mục skill này>/../*jira-subtask-creator*/jira_subtask.py`

```bash
python -X utf8 "<path>/jira_subtask.py" sprint-dates --sprint <mã sprint>
```

Trả JSON `{"start_date","due_date","weeks"}`. Giữ lại cho các bước sau.

Không tìm thấy script → **hỏi người dùng nhập ngày** (`--start`/`--due`) rồi chạy tiếp. KHÔNG tự tính ngày, KHÔNG dừng hẳn.

## Bước 2 — Xác định workspace root (ĐA ROOT)

Gom danh sách root theo **hợp** của các nguồn sau (không nguồn nào thay thế nguồn nào):
1. Mọi `--root` người dùng truyền vào
2. Mọi dòng trong mục `# roots` của config (Bước 0)
3. **Thư mục cha của cwd** — luôn thêm, coi như fallback

Root không tồn tại → bỏ qua im lặng. Khử trùng lặp và khử root nằm lồng trong root khác.

Với mỗi root, tìm repo:

```bash
find "<root>" -maxdepth 5 -name .git \( -type d -o -type f \) 2>/dev/null
```

- `-maxdepth 5` (không phải 3) để bắt repo lồng sâu trong mono-folder nhiều tầng.
- `-type f` để bắt git worktree / submodule, nơi `.git` là **file** chứ không phải thư mục.
- Nếu một root quá lớn làm `find` treo (> ~60s) → giảm maxdepth cho riêng root đó và báo người dùng biết đã giảm.

**In ra trước khi sang Bước 3:** số root đã quét (kèm đường dẫn) + số repo tìm được. Để người dùng phát hiện ngay nếu thiếu workspace.

> ⚠️ **Bẫy dấu cách — bắt buộc đọc.** Đường dẫn thường chứa khoảng trắng (`Code git`, `product catalog`, `tms management`).
> BẮT BUỘC duyệt kết quả bằng `while IFS= read -r`.
> CẤM `for x in $(find ...)` — bash word-split sẽ xé path thành nhiều mảnh và vòng lặp trả về **rỗng mà không báo lỗi**.
> Mọi biến path phải bọc trong nháy kép: `git -C "$repo" ...`.

## Bước 3 — Xác định identity của người dùng (TỰ DÒ, không hardcode)

Skill không biết trước người dùng là ai. Làm 4 bước:

**3a. Seed** — gom identity chắc chắn đúng:
```bash
git config --global user.name ; git config --global user.email
git -C "<repo>" config --local user.name ; git -C "<repo>" config --local user.email
```
(local config có thể khác nhau giữa các repo → gom hết thành tập hợp)

**3b. Liệt kê mọi author có hoạt động trong khoảng sprint**, trên toàn bộ repo:
```bash
git -C "<repo>" shortlog -sne --all --no-merges \
  --since="<start_date> 00:00" --until="<due_date+1> 00:00" 2>/dev/null
```

**3c. Đối chiếu:**
- Author khớp seed → chắc chắn của người dùng, nhận luôn.
- Author **không** khớp seed nhưng có commit → in bảng `identity | số commit | repo xuất hiện` và **HỎI người dùng**: "những identity nào dưới đây cũng là của bạn?"

  Bước này bắt buộc, không được bỏ. Lý do: rất hay gặp trường hợp cùng một người commit bằng email cá nhân ở một số repo (máy khác, tool khác, config cũ) trong khi `git config` hiện tại chỉ trả về identity công ty. Bỏ qua bước hỏi = mất trắng phần việc đó mà không có dấu hiệu gì.

- Identity từ `--author` hoặc mục `# identities` trong config → nhận luôn, khỏi hỏi.

**3d. Quét commit** với tập identity đã chốt:
```bash
git -C "<repo>" log --all --no-merges \
  --since="<start_date> 00:00" --until="<due_date+1> 00:00" \
  --pretty=format:"%h|%ad|%an <%ae>|%s" --date=format:"%m-%d %H:%M" \
  --author="<id1>\|<id2>\|..." --shortstat 2>/dev/null
```

Ghi chú:
- `--no-merges` để loại merge/"Pull request #NNN" trùng nội dung.
- `--author` là regex; gọi một lần với regex gộp, hoặc nhiều lần rồi khử trùng theo hash.
- Đếm số commit bằng `git rev-list --count`, KHÔNG dùng `... | wc -l` (`--pretty=format:` không xuống dòng ở dòng cuối → hụt 1).
- `--all` kéo cả `refs/stash`. **Loại** commit có message bắt đầu bằng `index on `, `untracked files on `, `WIP on ` — đó là stash entry, không phải việc.
- `--shortstat` để lấy khối lượng (insertions/deletions) phục vụ ước ET.
- Bỏ commit rác không mô tả việc (message rỗng, `.`, `wip`) — vẫn tính vào khối lượng repo nhưng không tách thành đầu việc riêng. Liệt kê chúng ở mục "ĐÃ LOẠI" cuối bảng bằng chứng.

## Bước 3.5 — GATE kiểm tra độ phủ (KHÔNG được bỏ qua)

Đếm số ngày distinct có commit, so với số ngày công của sprint (`weeks × 5`).

| Độ phủ | Hành động |
|---|---|
| < 60% | **DỪNG**, cảnh báo và hỏi người dùng, chỉ chạy tiếp sau khi họ xác nhận |
| 60–80% | Chạy tiếp nhưng ghi cảnh báo rõ trong output |
| > 80% | Chạy tiếp bình thường |

Nội dung cảnh báo khi < 60%:
> Chỉ tìm thấy commit ở **N/M** ngày công. Nhiều khả năng còn workspace hoặc git identity chưa được quét.
> Đã quét các root: `<liệt kê>`. Identity đang dùng: `<liệt kê>`.
> Bạn có workspace nào khác không, hoặc có identity nào tôi bỏ sót?

Kiểm thêm 2 tín hiệu, có thì nêu ra:
- Repo có commit của **người khác** trong sprint nhưng **0 commit** của người dùng → liệt kê riêng, để người dùng tự soi xem có thiếu identity nào không.
- Root nào quét ra 0 repo → nêu tên, có thể người dùng gõ nhầm đường dẫn.

## Bước 4 — Gom đầu việc (theo repo → chủ đề)

Gom commit theo **repo**, trong repo gom tiếp theo **chủ đề** (scope conventional-commit `feat(x)/fix(x)` + phán đoán ngữ nghĩa). Một chủ đề = một đầu việc lớn.

- Gộp các commit cùng scope/feature (vd mọi `fix(i18n)` reactive language → 1 đầu việc "i18n reactive đổi ngôn ngữ").
- Một chủ đề trải trên nhiều repo (spec + BE + FE của cùng một feature/slice) → gom thành **một** đầu việc, đặt tên theo hệ thống/sản phẩm thay vì theo repo.
- Đặt tên đầu việc dạng `[<repo hoặc hệ thống>] <chủ đề ngắn gọn>`, kèm mã contract/feature nếu có (vd `INT-PCM-01`, `SLICE-06`).
- Giữ danh sách commit-hash thuộc mỗi đầu việc để làm **bảng bằng chứng**.

## Bước 5 — Ước lượng ET + normalize về capacity

1. **Ước thô** mỗi đầu việc theo khối lượng: số commit, insertions/deletions, độ phức tạp (feat > fix > chore), số ngày distinct có commit.
2. **Normalize về capacity sprint**: scale các ET thô sao cho **tổng ET phần code ≈ số ngày làm việc của sprint** (số working day = `weeks × 5`, trừ T7/CN).
3. **Làm tròn** về bậc Jira: `0.5d (4h)`, `1d`, `1.5d`, `2d`... Mỗi đầu việc tối thiểu `0.5d`.
4. **Nếu hệ số scale < 0.6** (tổng thô > 1.67× capacity): CẢNH BÁO người dùng và đề xuất **gộp bớt đầu việc nhỏ cùng nhóm trước khi scale**. Để nguyên sẽ khiến hàng loạt item rơi hết về sàn 0.5d, ET mất hoàn toàn khả năng phân biệt việc nặng/nhẹ.
5. Việc phi-code (họp/support) ở Bước 6 KHÔNG tính vào tổng normalize; người dùng tự phân bổ lại khi duyệt.

Nêu rõ trong output: `Tổng ET code = X d ≈ capacity Y ngày (sprint <weeks> tuần), hệ số scale = Z`.

## Bước 6 — Chèn việc phi-code + xuất format

Thêm ở đầu danh sách các dòng việc phi-code (ET để trống cho người dùng điền):
- Lấy từ mục `# non-code-items` của config nếu có (thay `<sprint>` bằng mã sprint thật).
- Không có config → dùng mặc định trung tính: `Họp hành sprint <mã sprint>`.

Rồi in **một block** đúng format input của `/NTAPP-jira-subtask-creator` để người dùng copy:

```text
/NTAPP-jira-subtask-creator
Sprint: <mã sprint>

1. Họp hành sprint <mã> -  -
2. [<repo>] <chủ đề> - <ET>
3. [<repo>] <chủ đề> - <ET>
...
```

Sau block, in **bảng bằng chứng** để người dùng verify ET (mỗi đầu việc ↔ commit gộp vào + ET thô → ET scale):

```text
Khoảng sprint: <start_date> → <due_date> (<weeks> tuần, <working days> ngày công)
Root đã quét: <liệt kê>
Identity: <liệt kê>
Độ phủ: <N>/<M> ngày công
Tổng ET code: <X> d ≈ capacity <Y> ngày (hệ số scale <Z>)

#2 [<repo>] <chủ đề>                                  ET 2d
   8 commit (06/07): 5339f0c, 505579f, 15da1a4, ...   thô 1.5d → scale 2d
#3 [<repo>] <chủ đề>                                  ET 1d
   4 commit (07/07): d193447, 22700c1, ...            thô 1d → scale 1d

--- ĐÃ LOẠI ---
<repo>: <hash> — commit rác / stash entry
```

## Bước 7 — Mời lưu config (chỉ khi có phát hiện mới)

Nếu trong lần chạy này người dùng đã cung cấp thêm root hoặc xác nhận thêm identity mà config chưa có → hỏi: *"Lưu lại vào `sprint-worklog.md` để sprint sau khỏi hỏi lại?"*

Đồng ý → ghi/cập nhật file config ở vị trí người dùng chọn (mặc định `~/Documents/.env/sprint-worklog.md`). Chỉ ghi file config — KHÔNG bao giờ ghi giá trị cá nhân vào `SKILL.md`.

Kết thúc bằng lời nhắc: *"Duyệt/chỉnh ET rồi copy block trên chạy `/NTAPP-jira-subtask-creator`. Skill này không tự log work."*

---

## Quy tắc chuyển ET (đồng bộ với /NTAPP-jira-subtask-creator)

1 MD = 1 ngày công = 8h. Bậc thường dùng: `0.5d=4h`, `1d=8h`, `2d=16h`. In ET dạng `Nd` (ngày) hoặc `Nh` (giờ) — khớp cột ET của mẫu logwork.

## Important Constraints

- **KHÔNG hardcode dữ liệu cá nhân** (đường dẫn, tên, email, tên đội) vào SKILL.md. Dữ liệu riêng chỉ nằm ở file config ngoài hoặc tự dò lúc chạy.
- Không xác định được mã sprint → hỏi người dùng, KHÔNG tự bịa.
- Ngày sprint lấy từ `jira_subtask.py sprint-dates`; không có script thì hỏi người dùng, không tính nhẩm.
- Root là **hợp** của `--root` + config + thư mục cha cwd — không bao giờ chỉ một root.
- Identity phải qua bước tự dò + hỏi lại (Bước 3c); không giả định người dùng chỉ có một git identity.
- Duyệt kết quả `find` bằng `while IFS= read -r`; cấm `for x in $(find ...)`.
- Đếm commit bằng `git rev-list --count`, không dùng `wc -l` trên `--pretty=format:`.
- GATE Bước 3.5 là bắt buộc — độ phủ < 60% thì dừng và hỏi, không được im lặng xuất kết quả.
- Chỉ đọc git + in text. TUYỆT ĐỐI không gọi Jira, không log work, không tạo issue.
- Luôn kèm bảng bằng chứng (commit ↔ đầu việc) + danh sách commit đã loại.
