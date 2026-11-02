---
name: NTAPP-okf-refresh
description: Refresh the OKF knowledge bundle under <output_folder>/.okf/ by invoking scripts/okf_project.py through Bash — hash every source declared in the families config, reproject only the families whose sources changed, run the coverage / orphan / dd_version-drift checks, then append the run report to .okf/log.md. Supports --full (reproject everything, ignoring hashes, still preserving human-written verified[]), --audit (checks and report only, writes no nodes), --family <name> (single family, used when bootstrapping a phase) and --verify <node-id> (a human signs one node; the signer is derived automatically from git, and the command refuses to run in CI). Use when the user says "chiếu lại OKF", "refresh bundle OKF", "cập nhật .okf", "audit OKF", "ký verify node OKF", "OKF stale", or when a scheduled job triggers the projection. This skill never produces node files with the agent's own Write/Edit tools — all node I/O belongs to the Python engine.
user-invocable: true
argument-hint: "[--full] [--audit] [--family <name>] [--verify <node-id>] [--allow-shrink] [--dry-run] [--json]"
allowed-tools: [Bash, Read]
---

# /NTAPP-okf-refresh — Chiếu bundle OKF

## Overview

Chiếu artifact NTAPP thành **bundle OKF** (`<output_folder>/.okf/`) — mỗi node một file markdown, quan hệ nằm ở frontmatter. Bundle là **dẫn xuất một chiều**: master được viết và ký, node sinh ra từ master, không bao giờ ngược lại.

Skill này là **vỏ**. Toàn bộ logic nằm trong `scripts/okf_project.py`; skill chỉ dò interpreter, dựng lệnh, chạy, rồi đọc lại báo cáo.

> **Việc chiếu tách rời khỏi mọi workflow.** Không workflow YAML nào, không hook nào ghi node OKF. Đồ thị trễ tối đa một chu kỳ lịch — chấp nhận được vì `content_sha` khiến node cũ **lộ ra lúc đọc**, nên mất *độ tươi* chứ không mất *tính đúng*.

## Ràng buộc cứng — CHỈ gọi engine qua `Bash`

> **TUYỆT ĐỐI KHÔNG dùng công cụ `Write` / `Edit` / `MultiEdit` của agent để tạo, sửa hay xoá bất kỳ file nào trong `.okf/`.** Mọi I/O node nằm trong tiến trình Python. Skill chỉ được `Bash`-gọi `okf_project.py` và `Read` kết quả.

Đây là **ràng buộc đúng-sai, không phải khuyến nghị phong cách**. Lý do cụ thể:

`.claude/settings.json` đăng ký `drift_detector.py` ở `PostToolUse` với matcher `Write|Edit|MultiEdit`. Nếu skill ghi 2.340 node bằng công cụ agent thì mỗi lần ghi sẽ **kích mọi `PostToolUse` hook đang có** — kể cả `drift_detector.py`, vốn trả **exit code 2 để CHẶN**. Kết quả: lượt chiếu chết giữa chừng, bundle còn một nửa, và không ai biết nửa nào.

"0 hook OKF" **không** có nghĩa là không hook nào phản ứng. Nó chỉ có nghĩa là không hook nào *của OKF*. Các hook khác vẫn ở đó và vẫn bắn.

Hệ quả thực hành:

| Việc | Cách đúng | Cách sai |
|---|---|---|
| Sinh / cập nhật node | `Bash` → `okf_project.py` | ❌ `Write` từng file node |
| Ký duyệt một node | `Bash` → `okf_project.py --verify <node>` | ❌ `Edit` frontmatter `verified[]` |
| Xem báo cáo | `Read` `.okf/log.md`, `.okf/status.md` | — |
| Sửa nội dung tri thức | Sửa **master**, rồi chiếu lại | ❌ Sửa tay node |

Nếu có lúc nào bạn thấy mình sắp mở một file trong `.okf/` ra sửa — **dừng lại**. Thiết kế đã hỏng ở chỗ khác; đừng vá ở đây.

## When to use

- User muốn chiếu lại / làm mới bundle OKF sau khi spec đổi.
- User muốn kiểm tra độ phủ, orphan, lệch `dd_version` mà **không** ghi gì (`--audit`).
- User muốn ký xác nhận một node đã trỏ đúng chỗ (`--verify`).
- Bộ lập lịch (CI / launchd / cron / Task Scheduler) gọi định kỳ.
- Trước một ceremony lớn (demo, review, chốt stage).

## Arguments

`$ARGUMENTS` — không bắt buộc. Không có gì → chạy **tăng dần**, mặc định.

| Cờ | Nghĩa |
|---|---|
| *(không cờ)* | Chiếu tăng dần — chỉ family có nguồn đổi theo hash |
| `--full` | Chiếu lại toàn bộ, **bỏ qua hash**. Vẫn bảo tồn `verified[]` do người ghi |
| `--audit` | Chỉ bước 3+4 (kiểm + báo cáo). **Không ghi node nào** |
| `--family <name>` | Chỉ một family — dùng khi bootstrap từng phase P1–P5 |
| `--verify <node-id>` | Người ký một node. Xem mục riêng bên dưới |
| `--allow-shrink` | Cho phép một family kết thúc với **ít node hơn** số đang có trên đĩa. Xem mục dưới |
| `--dry-run` | Liệt kê việc sẽ làm, không ghi |
| `--json` | In kết quả dạng JSON (dành cho bộ lập lịch / CI) |
| `--root <dir>` · `--config <path>` | Ghi đè gốc quét / file config |
| `--self-test` | Chạy bộ test nội bộ của engine |

**KHÔNG bịa cờ mới.** Danh sách trên là toàn bộ CLI đã chốt. Cờ lạ → engine trả lỗi tham số, không phải bỏ qua im lặng.

## Bước 0 — Dò Python interpreter (BẮT BUỘC, không viết cứng `python3`)

Windows **không có `python3` trên PATH** — chỉ có launcher `py` hoặc `python`. Viết cứng `python3` là cách chắc chắn nhất để skill này chết trên máy Windows với thông báo `command not found` vô nghĩa.

Dò theo đúng thứ tự `py -3` → `python3` → `python`:

```bash
PY=""
for c in "py -3" python3 python; do
  # $c CỐ Ý không quote — "py -3" phải tách thành 2 từ.
  if $c -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
    PY="$c"; break
  fi
done

if [ -z "$PY" ]; then
  echo "ERROR: không tìm thấy Python 3.8+ (đã thử: py -3, python3, python)." >&2
  echo "  Windows : cài Python từ python.org / Microsoft Store (kèm launcher 'py')." >&2
  echo "  macOS   : xcode-select --install" >&2
  echo "  Linux   : sudo apt install python3" >&2
  exit 1
fi
echo "python: $PY"
```

Hai chi tiết dễ sai:

- **`$c` không được quote.** `"py -3"` phải word-split thành hai từ; `"$c"` sẽ đi tìm một lệnh tên `py -3` và luôn trượt.
- **Luôn thêm `-X utf8` khi gọi engine.** Corpus là tiếng Việt có dấu; `open()` trên Windows mặc định là code page ANSI (cp1252), không phải UTF-8 → hoặc `UnicodeDecodeError`, hoặc tệ hơn là đọc trôi thành ký tự rác rồi băm ra một SHA "hợp lệ" mà sai.

Định vị engine + gốc dự án:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ENGINE="$ROOT/scripts/okf_project.py"

if [ ! -f "$ENGINE" ]; then
  echo "skipped: okf engine missing ($ENGINE)"
  exit 0
fi
```

**Thiếu engine hoặc thiếu config → in `skipped: …` và thoát 0.** Không bao giờ chặn ai. Engine tự xử lý trường hợp thiếu config; skill chỉ xử lý trường hợp thiếu chính engine.

## Workflow — bốn bước, tuần tự

Cả bốn bước nằm trong **một lời gọi** `okf_project.py`. Skill không tự thực hiện bước nào.

| # | Bước | Engine làm gì |
|---|---|---|
| 1 | **Quét** | Băm mọi nguồn khai trong `families`; so `source_sha` của **file** (cổng rẻ, 1 lần/file) rồi `content_sha` của **từng section** |
| 2 | **Chiếu** | Chỉ family có nguồn đổi. Đọc node cũ trước khi ghi, **giữ nguyên `verified[]`** và mọi key người thêm |
| 3 | **Kiểm** | Coverage · orphan · lệch `dd_version` · repo vắng mặt |
| 4 | **Báo cáo** | Ghi `.okf/log.md` (xoay vòng) + `.okf/status.md` + mục lục `.okf/<type>/_index.md` cho **mỗi family đã chạm** |

> ⚠️ **Mục lục `_index.md` KHÔNG phải node.** Nó là bản đồ *của* bundle — không frontmatter, không `resource`, không bao giờ bị đếm / khai tử / quét. Báo cáo số node thì lấy đúng con số `--audit` in ra; **đừng cộng thêm số mục lục vào**. Engine loại nó ra theo tên file, nên nếu số node nhảy lên **đúng bằng số family đã chạm** thì đó là dấu phép loại trừ đã hỏng, không phải đồ thị lớn lên.
>
> `--family <name>` chỉ ghi lại mục lục của **một** family đó — đúng như nó chỉ chiếu lại node của family đó. Mục lục là dẫn xuất của family, không phải của bundle.

Lệnh:

```bash
$PY -X utf8 "$ENGINE" --root "$ROOT" $ARGUMENTS
```

Sau khi chạy, `Read` `.okf/log.md` (mục mới nhất) và `.okf/status.md` để tóm tắt cho user. Không đoán kết quả từ exit code.

## Ba đường chạy — cùng một engine

| # | Đường | Ai gọi | Khi nào |
|---|---|---|---|
| 1 | **Bootstrap** | Người triển khai | Một lần mỗi phase (P1–P5), thường kèm `--family <name>` |
| 2 | **Định kỳ** | Bộ lập lịch của dự án | Theo chu kỳ đã chốt (khuyến nghị: hằng ngày, ngoài giờ) |
| 3 | **Theo yêu cầu** | Người | Trước ceremony lớn, hoặc sau khi sửa `goal` / `notes` |

Framework **không áp đặt bộ lập lịch**. Mỗi dự án tự cắm: CI (`schedule:`), `launchd` trên macOS, `cron` trên Linux, **`schtasks /create /sc DAILY` trên Windows** (Windows không có cron). Không đường nào chặn bất cứ thứ gì.

## `--verify <node-id>` — chữ ký của NGƯỜI

```bash
$PY -X utf8 "$ENGINE" --root "$ROOT" --verify design-section/BE-INV-09/4-dac-ta-du-lieu-tich-hop-data-integration
```

Lệnh append **đúng một** mục `{by, at}` vào `verified[]` của node đó. Người ký; máy ghi. Không ai mở file node ra gõ tay.

Ba điều phải nói rõ với user:

1. **`by` KHÔNG phải tham số — user không bao giờ gõ tên mình.** Engine tự suy: `git config user.name/user.email` → `git check-mailmap` chuẩn hoá → lấy local-part của email → `human:<id>`. **Đừng hỏi user tên/email, đừng truyền `--by`** — không có cờ đó.
2. **Từ chối chạy khi `CI=true` hoặc không có TTY.** Ký là hành vi của người; máy không ký thay. Gặp từ chối trong CI thì đó là **hành vi đúng**, không phải lỗi cần workaround.
3. **`verified` là bậc thấp, phạm vi hẹp:** *"tôi đã mở tài liệu gốc và xác nhận thẻ này trỏ đúng chỗ, mô tả đúng nội dung"*. Nó **không** có nghĩa *"tôi đồng ý với đặc tả này"* — thẩm quyền duyệt nằm ở `approval_gate.sh` / `ds_build_approval_gate.sh`, không ở thẻ node.

`verified[]` là lịch sử **chỉ-thêm**, không dựng lại được. Vì thế `--full` cũng phải bảo tồn nó — đó là ràng buộc của engine, không phải tuỳ chọn.

Một người có nhiều email trên nhiều máy → thêm `.mailmap` ở gốc spec repo (cơ chế chuẩn của git, thường 2 dòng là đủ). **Không bắt buộc**: thiếu `.mailmap` thì hệ vẫn chạy, chỉ là một người xuất hiện dưới hai tên.

## Khoá `.okf/.lock`

CI chạy đêm và một người gõ `/NTAPP-okf-refresh` trước demo hoàn toàn có thể trùng nhau. Engine giữ `.okf/.lock` (PID + timestamp).

> Lượt thứ hai thấy khoá còn sống thì **thoát 0 với thông báo `skipped: locked`** — **không chờ, không ghi, không báo lỗi.**

Gặp `skipped: locked` thì báo user rằng đang có lượt chiếu khác chạy và thử lại sau. **Đừng xoá `.lock` bằng tay** để "chữa" — khoá còn sống nghĩa là đúng nghĩa đen có tiến trình khác đang ghi bundle.

## Khi engine từ chối vì family bị co lại

Engine dừng với thông báo `would deprecate N existing node(s)`. **Đây không phải lỗi cần bypass.**
Nó bắt đúng thứ `min_nodes` không bắt được: một lượt chiếu vẫn đủ số sàn mà **vẫn mất node**, vì
glob hoặc `split_level` bị thu hẹp. Trình tự xử lý:

1. Đọc danh sách node trong thông báo — chúng thuộc file nào?
2. File nguồn đó **còn tồn tại** không? Còn thì `source_glob` hoặc `split_level` vừa bị sửa hỏng → sửa config, đừng thêm cờ.
3. Nguồn **thật sự đã bị xoá** thì chạy lại kèm `--allow-shrink` và nói rõ với user đã khai tử những node nào.

Node bị khai tử **không bị xoá ngay** — nó mang `status: deprecated`, chờ hết thời gian ân hạn rồi mới bị quét đi ở lượt `--full`.

## Khi engine từ chối vì slice không phân giải được

Ba thông báo, ba nguyên nhân khác nhau. **Không cái nào sửa được bằng cờ.**

**`slice manifest <file> has no feature: field`** — manifest thiếu `feature:` và cũng không nằm
trong thư mục feature, nên không gì nói được nó thuộc feature nào. Ledger / bài học / `slice_set`
đều gom nhóm qua trường đó. Sửa ở nguồn — thêm `feature: <slug>` vào frontmatter manifest
(template ở `NTAPP-slice-planning/workflow.md`), hoặc chuyển manifest xuống thư mục feature.
Đừng chiếu vòng qua bằng cách bỏ family.

**`refers to SLICE-N, which exists in more than one feature`** — **chưa từng xảy ra**, và không
xảy ra được với Stage 2b hiện tại: re-run chỉ nối thêm số, không đánh số lại. Gặp nó nghĩa là
quy ước đánh số đã đổi thật. Thông báo có in tên cả hai chủ — chuyển file gọi xuống thư mục
feature đúng, **đừng đoán**, và báo user rằng giả định "số slice duy nhất toàn cục" đã vỡ.

**`refers to SLICE-N, which has no slice manifest`** — trỏ tới một slice không tồn tại. Hoặc gõ
sai số, hoặc manifest đã bị xoá. Đây là lỗi dữ liệu thật, báo user chứ đừng tự sửa số.

## Khi log ghi cảnh báo đối chiếu slice (`⛔`)

Family `slice` đối chiếu **ba chiều**: manifest ∧ knowledge ∧ ledger. Bốn kết cục, chỉ ba trong
số đó là lỗi:

| Dấu vết | Nghĩa là gì | Có phải lỗi? |
|---|---|---|
| có manifest, **không** knowledge, **không** ledger | slice làm tay, chưa từng gọi `slice-loop` | **không** |
| có manifest, **có** knowledge, **thiếu** ledger | `slice-loop` đã chạy và **mất lượt ghi ledger** | ⛔ có |
| có manifest, **có** ledger, **thiếu** knowledge | qua node demo mà **không** qua node code-review | ⛔ có |
| có ledger/knowledge, **không** manifest | mục mồ côi — manifest đã bị xoá | ⛔ có |

Dòng đầu bảng là lý do luật hai chiều cũ ("manifest nào cũng phải có trong ledger") **báo động
giả vĩnh viễn**. Đừng "sửa" nó bằng cách thêm mục vào ledger cho khớp.

Đối chiếu **vẫn chạy khi có nhiều feature** — số slice không bị dùng lại nên `SLICE-3` trong
ledger vẫn trỏ đúng một slice. Nó chỉ tắt khi một số **thật sự** bị hai feature cùng nhận, và
lúc đó log in rõ số nào.

**Giới hạn đã biết, phải nói với user khi báo cáo:** một lượt `slice-loop` chết **trước** node
code-review để lại dấu vết **giống hệt** slice làm tay. Đối chiếu không phân biệt được hai ca đó.

## Báo cáo cuối

In gọn cho user: chế độ đã chạy · số family đã chạm · số node ghi mới / cập nhật / chuyển `deprecated` · kết quả 4 truy vấn kiểm · đường dẫn `.okf/log.md`. Có `skipped: …` thì nói rõ **skip vì lý do gì**, đừng báo "xong".

## Common mistakes

- ❌ Dùng `Write`/`Edit` tạo node → kích `drift_detector.py` ở `PostToolUse`, hook trả exit 2 và **chặn** giữa chừng. Chỉ `Bash` gọi engine.
- ❌ Viết cứng `python3` → chết trên Windows. Luôn dò `py -3` → `python3` → `python`.
- ❌ Quote `"$c"` trong vòng dò interpreter → `"py -3"` không bao giờ khớp.
- ❌ Quên `-X utf8` → tiếng Việt có dấu đọc trôi trên Windows, SHA sai mà không báo lỗi.
- ❌ Hỏi user tên/email cho `--verify`, hoặc bịa cờ `--by` → actor suy tự động từ git, không có tham số nào.
- ❌ Coi `--verify` bị từ chối trong CI là bug → đó là thiết kế (§ ký là hành vi của người).
- ❌ Sửa tay frontmatter node (kể cả `verified[]`) → phá tính dẫn xuất một chiều.
- ❌ Xoá `.okf/.lock` để ép chạy → giẫm lên tiến trình đang ghi.
- ❌ Báo "xong" khi engine in `skipped:` → phải nói rõ skip vì thiếu engine, thiếu config, hay bị khoá.
- ❌ Thêm `--allow-shrink` cho "chạy được" khi engine từ chối → cờ đó là để xác nhận nguồn ĐÃ BỊ XOÁ, không phải để tắt cảnh báo.
- ❌ Chèn bước OKF vào workflow YAML hoặc thêm hook OKF → thiết kế là **0 dòng OKF trong workflow, 0 hook OKF**.
