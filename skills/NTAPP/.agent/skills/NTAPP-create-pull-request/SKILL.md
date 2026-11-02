---
name: NTAPP-create-pull-request
description: Use when the user wants pull requests opened on Bitbucket — for the current branch of every repo in a workspace, for a single repo, or between two named branches such as staging into release — and when they want to merge those pull requests afterwards. Triggers on "tạo pull request", "tạo PR lên staging", "mở PR", "PR từ staging vào release", "merge PR", "create pull request", "raise PR". Bitbucket Server tại bitbucket.digital.vn, credential từ env.md.
user-invocable: true
argument-hint: [nhánh nguồn] [nhánh đích] [--dry-run] [--cwd-only]
allowed-tools: [Bash, Read]
---

# /NTAPP-create-pull-request — Tạo pull request lên Bitbucket

## Arguments

`$ARGUMENTS` — tùy chọn, diễn giải theo ngôn ngữ tự nhiên rồi map sang cờ của script:

| Người dùng nói | Cờ |
|---|---|
| (không nói gì) | mặc định: nhánh hiện tại từng repo → `staging` |
| "từ staging vào release" | `--source staging --target release` |
| "lên master" | `--target master` |
| "chỉ repo này" | `--cwd-only` |
| "xem trước", "thử" | `--dry-run` |
| "merge PR của repo X" | `--merge --repo <đường dẫn> --pr <số>` (một PR mỗi lần) |

## Chạy

```bash
python "<thư mục skill này>/bitbucket_pr.py" [--source X] [--target Y] [--dry-run] [--cwd-only]
```

Script tự lo: tìm repo, đọc credential, bỏ qua repo không hợp lệ, chống tạo PR trùng,
báo conflict. In lại nguyên output cho người dùng.

## Trình tự bắt buộc

Ba bước, đúng thứ tự này. Không đảo, không gộp hai bước vào một câu hỏi.

**Bước 1 — Tạo PR.** Chạy script ngay khi vào skill. Người dùng gọi skill này *chính là* để
tạo PR, nên **không hỏi "có tạo PR không"** — cứ tạo. Chỉ dừng lại hỏi khi gặp một trong hai
tình huống, và chỉ hỏi cho đúng repo bị vướng:

- script báo `[ERROR]` ở một repo → nêu repo nào, lỗi gì, hỏi người dùng muốn xử lý ra sao;
- repo đã có PR mở cùng cặp nhánh → script `[SKIP]` kèm link PR cũ; nêu link đó ra và hỏi
  người dùng muốn dùng tiếp PR cũ hay xử lý khác.

Các repo còn lại vẫn chạy tiếp bình thường, không bị chặn vì một repo vướng.

**Bước 2 — Báo cáo.** Chỉ báo cáo những PR **thực sự tồn tại** sau bước 1 (vừa tạo, hoặc PR
cũ mà người dùng xác nhận dùng tiếp). Không có PR thì không có gì để báo cáo — nói thẳng là
chưa tạo được và vì sao, **đừng bịa số PR hay link PR**.

**Bước 3 — Hỏi merge.** Chỉ hỏi sau khi đã hiện xong báo cáo ở bước 2, để người dùng đọc rồi
mới quyết định. Câu hỏi merge **chỉ gồm merge hay không merge** — việc tạo PR đã xong ở bước
1, không được xuất hiện lại như một lựa chọn ở đây.

## Quy tắc quyết định nội dung PR

**PR chỉ phản ánh những gì đã được push lên remote.**

Mọi phép so sánh dùng `origin/<nguồn>` với `origin/<đích>` — **không bao giờ dùng `HEAD`**.
`HEAD` là trạng thái local; dùng nó sẽ đếm cả commit chưa push và mô tả PR sai so với thứ
Bitbucket thực sự nhận.

Thay đổi chưa commit và commit chưa push **không nằm trong PR**: script cảnh báo và đi tiếp.

| Tình huống | Xử lý đúng |
|---|---|
| Working tree bẩn | Cảnh báo, vẫn tạo PR cho phần đã push |
| Nhánh local đi trước remote | Cảnh báo số commit chưa push, vẫn tạo PR cho phần đã push |
| Nhánh nguồn chưa từng push | Bỏ qua repo đó — không có gì trên remote để PR |

**Không bao giờ tự chạy `git push`, `git commit`, hay `git merge` để "làm cho PR đầy đủ".**
Nếu người dùng muốn đẩy phần còn thiếu, họ sẽ nói. Việc của skill này là mở PR, không phải
thay đổi lịch sử nhánh.

## Repo nào được xử lý

Mặc định quét **workspace** = thư mục cha của repo hiện tại, nếu chứa từ 2 git repo trở lên.
Nếu không → chỉ repo hiện tại. `--cwd-only` ép luôn về repo hiện tại.

Repo bị bỏ qua tự động (kèm lý do, không phải lỗi): không có remote origin · remote không
phải Bitbucket · không có nhánh đích trên remote · nhánh nguồn chưa push · **0 commit mới so
với nhánh đích** (PR rỗng sẽ bị Bitbucket từ chối) · đã có PR mở cùng cặp nhánh.

## Sau khi tạo PR — báo cáo

Script in ra tiêu đề commit + diffstat + lệnh đọc diff cho từng PR. Đó là **nguyên liệu**,
không phải bản báo cáo. Script không tự diễn giải code; phần đó là việc của bạn.

Với **mỗi repo đã tạo PR**, chạy lệnh `doc dien diff` mà script in ra để đọc diff thật, rồi
viết một mục gồm đúng ba phần:

1. **Link PR** (kèm repo và cặp nhánh).
2. **Thay đổi chính** — 3-5 gạch đầu dòng, tiếng Việt thường ngày, giải thích *tác dụng* chứ
   không đọc lại tên file. Phải **bao quát hết** vùng code đã đổi: mỗi nhóm file trong
   diffstat phải được nhắc tới ở ít nhất một gạch đầu dòng.
3. **Điểm cần biết trước khi merge** — chỉ ghi khi có thật: script migration DB phải chạy
   tay, đổi contract, thay đổi cấu hình, PR có conflict, phụ thuộc thứ tự với PR khác.

Tóm tắt từ **diff thật**, không phải từ tiêu đề commit. Tiêu đề commit là điều tác giả nói họ
đã làm; diff là thứ thực sự sẽ vào nhánh đích.

Ngoài phần PR, vẫn nêu repo nào bị bỏ qua và **vì sao**. "0 commit mới" nghĩa là nhánh đó đã
nằm trọn trong nhánh đích — nói rõ như vậy, đừng trình bày như lỗi.

## Hỏi merge — từng repo một

Sau khi đã hiện báo cáo, hỏi người dùng có merge hay không **cho từng repo riêng biệt**, bằng
`AskUserQuestion`: **mỗi repo là một câu hỏi độc lập**, lựa chọn chỉ gồm merge / không merge
repo đó.

Gộp các câu hỏi đó vào **một lần gọi `AskUserQuestion`** — người dùng thấy một hộp thoại, mỗi
repo một tab, và trả lời riêng cho từng tab. Một lần gọi chứa tối đa 4 câu hỏi; nhiều hơn 4
repo thì chia làm nhiều lần gọi. Gộp vào một hộp thoại là để đỡ phiền, **không phải** để gộp
quyết định: mỗi tab vẫn là một quyết định riêng của một repo.

Đặt tên `header` của mỗi câu hỏi theo tên repo, để người dùng biết tab nào là repo nào.

Nếu bước 1 không tạo được PR nào và cũng không có PR cũ nào được người dùng xác nhận dùng
tiếp → **không hỏi merge**, kết thúc ngay sau báo cáo. Không có PR thì không có gì để merge.

**Không bao giờ gộp phê duyệt.** Cụ thể là cấm:

- một câu hỏi chung kiểu "merge những PR nào?" rồi để người dùng liệt kê;
- bất kỳ lựa chọn nào mang nghĩa "cả 3", "tất cả", "merge hết", "A và C";
- suy ra sự đồng ý cho repo B từ việc người dùng đã đồng ý repo A.

Người dùng đồng ý merge một repo **chỉ tính cho đúng repo đó**. Repo còn lại vẫn phải hỏi
riêng, kể cả khi các PR cùng thuộc một ticket và trông như một gói.

Merge repo nào thì gọi script đúng một lần cho repo đó:

```bash
python "<thư mục skill này>/bitbucket_pr.py" --merge --repo <đường dẫn repo> --pr <số PR>
```

Script từ chối merge khi PR đã đóng, đang conflict, hoặc bị veto — và không có chế độ merge
nhiều PR cùng lúc. Nếu PR conflict → nêu ra, hỏi người dùng. **Đừng tự merge nhánh đích vào
nhánh nguồn để gỡ conflict.**

## Sai lầm thường gặp

| Sai | Đúng |
|---|---|
| Dùng `gh` CLI | Đây là Bitbucket Server, không phải GitHub — dùng REST API `/rest/api/1.0` |
| Lấy dòng `token:` đầu tiên trong env.md | env.md có nhiều block (Confluence/Jira/Grafana/Bitbucket), mỗi block một `token:`. Phải lấy trong block có header chứa `bitbucket.digital.vn`, nếu không sẽ nhận HTTP 401 lúc POST |
| Hardcode project key | Lấy từ URL remote: `.../scm/<key>/<repo>.git` |
| `git fetch` lỗi thì dừng | Tên nhánh remote không hợp lệ trên Windows làm fetch exit 1 nhưng ref khác vẫn cập nhật — cảnh báo rồi đi tiếp |
| Lọc PR trùng bằng `at=` một mình | Phải kèm `direction=OUTGOING`, thiếu nó API trả rỗng và sinh PR trùng |
| Tạo PR cho repo 0 commit mới | Bitbucket từ chối `EmptyPullRequestException` — bỏ qua trước |
| Hỏi người dùng "có tạo PR không" trước khi tạo | Tạo PR là việc chính của skill — cứ tạo, chỉ hỏi khi lỗi hoặc đã có PR cũ |
| Đưa "tạo PR" thành một lựa chọn trong câu hỏi merge (vd "Tạo PR + merge / Chỉ tạo PR") | PR đã tạo xong ở bước 1; câu hỏi merge chỉ còn merge / không merge |
| Hỏi merge trước khi hiện báo cáo thay đổi | Báo cáo trước, người dùng đọc xong mới quyết định |
| Gộp phê duyệt merge nhiều repo vào một câu hỏi (kể cả khi các PR cùng một ticket) | Mỗi repo một câu hỏi riêng trong cùng một hộp thoại, không có lựa chọn "tất cả" |
| Tóm tắt thay đổi bằng cách chép lại tiêu đề commit | Đọc diff thật qua lệnh script in ra rồi mới viết |

## Credential

`env.md` (tự dò `./env.md` → thư mục skill → `~/.env/env.md` → `~/Documents/.env/env.md` →
`~/env.md`, hoặc truyền `--env <path>`). Block Bitbucket cần header chứa `bitbucket.digital.vn`
kèm `token:` (ưu tiên, dùng Bearer) hoặc `Username:` + `Pass:` (Basic).

**Không in token ra output.**
