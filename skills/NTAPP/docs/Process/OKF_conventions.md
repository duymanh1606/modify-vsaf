# OKF — quy ước khai family và đánh số

Tài liệu tham chiếu cho người **cấu hình lớp OKF**: khai `okf.families` trong
`.bmm-config.yaml`, đặt số hiệu ADR, đánh số slice. Không phải tài liệu vận hành —
cách chạy engine nằm ở [`/NTAPP-okf-refresh`](../../.agent/skills/NTAPP-okf-refresh/SKILL.md),
logic nằm ở [`scripts/okf_project.py`](../../scripts/okf_project.py).

> **Chỉ dẫn tri thức THẬT nằm ở `<output_folder>/.okf/index.md`**, không phải ở đây.
> File này chỉ nói về *cấu hình* — thứ người viết trước khi bundle tồn tại.

## Marker — hai quy ước, chủ sở hữu ở nơi khác

Nêu ở đây để đủ bối cảnh; **đừng sửa bản này, sửa bản gốc**:

| Marker | Ở đâu | Chủ sở hữu (SSoT) |
|---|---|---|
| `<!-- okf-id: … -->` | Ngay dưới heading cố định trong DD / TechSpec / HLD / UX | Comment `QUY ƯỚC OKF` trong thân 4 template — đi theo vào mọi doc sinh ra |
| `<!-- okf-finding: … -->` | Ngay dưới heading mỗi finding trong báo cáo review | [`review_report_template.md`](../../.agent/skills/bmad-code-review/templates/review_report_template.md) + [CLAUDE.md](../../CLAUDE.md) §Báo cáo code review |

Hai điều kiện dễ sai, áp cho cả hai marker:

- Marker phải là **dòng không rỗng đầu tiên** dưới heading — bộ đọc dừng ở dòng đó
  ([`okf_project.py` `declared_section_id`](../../scripts/okf_project.py)), nên đặt sau một
  comment hướng dẫn là marker không được đọc.
- **Bảng tóm tắt không bao giờ mang marker.** Một bản review liệt kê cùng một finding
  ở hai nơi — bảng chỉ mục và mục chi tiết. Đánh dấu cả hai biến N finding thành 2N.
  Đó là lỗi **số học**, không phải lỗi độ chặt: nới hay siết mẫu nhận dạng đều không chữa được.

## Khai family trước khi stage của nó chạy

Project mới khai đủ 15 family ngay từ đầu (bootstrap rót sẵn vào
`.bmm-config.yaml` từ `scripts/templates/bmm-config-specrepo.template.yaml`), nhưng
Stage 3 và 4 thì còn lâu mới chạy. Mặc định, một family có nguồn không tồn tại
**giết cả lượt chiếu** — không phải ra 0 node, mà exit 1. Đó là hành vi đúng:
nguồn biến mất gần như luôn nghĩa là file bị đổi tên hoặc dời chỗ, và bỏ qua nó
chính là kiểu "quét hụt nhưng báo thành công" mà projector từ chối ở mọi chỗ khác.

Ngoại lệ phải **xin theo từng family**, bằng chữ:

```yaml
    ux-section:
      adapter: heading-split
      source: Stage_3_Specs/ux/ux_design.md
      allow_missing_source: true      # Stage 3b chưa chạy — chưa có gì để đọc
```

Family đó được bỏ qua, và lần bỏ qua nào cũng **ghi vào `log.md` + in ra màn
hình**. "Bỏ qua vì chưa có gì để đọc" và "đã chiếu nhưng không tìm thấy gì" là
hai sự thật khác nhau; một bundle không phân biệt được hai thứ đó thì đọc lên
như đã đầy đủ.

**`min_nodes` tắt ngoại lệ này.** Khai cả hai là tự mâu thuẫn — `min_nodes` là
lời khẳng định "family này phải ra ít nhất N node", không thể đúng với một nguồn
không có mặt — nên engine **báo lỗi** thay vì chọn hộ. Hai khoá ghép lại mô tả
một vòng đời: chịu đựng khoảng trống trong lúc stage chưa tới, rồi khi đã chiếu
thật thì điền `min_nodes` từ số node đo được và bỏ `allow_missing_source` đi.
Từ đó trở về sau, nguồn biến mất lại là lỗi — đúng như nó phải thế.

## Adapter — chín loại, chọn theo hình dạng của nguồn

Mỗi family trong `okf.families` khai đúng một `adapter`. Chọn sai thì engine vẫn
chạy sạch và vẫn ra node — chỉ là ra **sai hạt**. Nên đây là quyết định phải cân
trước, không phải thứ sửa sau. Khai tên không tồn tại thì engine **báo lỗi và liệt
kê đủ danh sách đã đăng ký**, không im lặng bỏ qua.

| Adapter | Nguồn có hình dạng gì | Một node là gì |
|---|---|---|
| `wbs-index` | một bảng WBS lớn | một work unit |
| `table-rows` | một bảng trong một mục có tên | một hàng |
| `id-header-scan` | cây mã nguồn gắn thẻ `// id:` | một file mã |
| `heading-split` | tài liệu dài, mọi mục đều quy phạm | một mục ở `split_level` |
| `heading-blocks` | nhật ký chỉ-thêm, lẫn cả ghi chú làm việc | một block khớp `key_pattern` |
| `knowledge-bullets` | ghi chú tri thức per-slice (`ledgers/knowledge/`) | một bullet |
| `whole-file` | thư mục mà mỗi file đã là một khái niệm | một file |
| `slice-manifest` | manifest slice của Stage 2b | một slice |
| `json-doc` | tài liệu JSON (`ui_schema_*.json`…) | một file |

Hai cặp dễ chọn nhầm:

**`heading-split` vs `heading-blocks`** — khác nhau ở **chiều của bộ lọc**.
`heading-split` dùng `skip_headings`, tức **danh sách đen**: mặc định mọi mục là
node. Đúng cho đặc tả, nơi mục nào cũng quy phạm. `heading-blocks` dùng
`key_pattern`, tức **danh sách trắng**: chỉ heading khớp mẫu mã mới thành node.
Đúng cho nhật ký, nơi văn bản không-phải-mục-cần-chiếu xen kẽ tự nhiên. Dùng danh
sách đen cho nhật ký thì mỗi lần ai đó nghĩ ra một kiểu tiêu đề ghi chú mới, một
ghi chú lặng lẽ thành một node bug.

**`heading-split` vs `whole-file`** — hỏi *"đọc riêng một mục của file này có
nghĩa không?"*. Một mục của DD thì có; một ADR thì không — tách `## Considered
Options` rời khỏi `## Consequences` là chia đôi một quyết định. Ở `whole-file`,
`source_sha` và `content_sha` **bằng nhau** có chủ đích: node là cả file, nên đó
là sự thật, và rẻ hơn việc bắt mọi consumer viết một nhánh riêng.

`split_level` là **list**, không phải số: corpus không chia ở một độ sâu duy nhất.
HLD và UX chia ở `[2, 3]` nên marker `okf-id` gắn cho **cả H2 lẫn H3**; DD và
TechSpec chia ở `[2]` (mặc định) nên chỉ H2.

## Hai loại quyết định — `designed-adr` và `runtime-adr`

Quyết định kiến trúc không cùng một loại, và gộp chúng làm một là mất thông tin:

| | `designed-adr` | `runtime-adr` |
|---|---|---|
| Là gì | Quyết định **được thiết kế**, chốt trước khi xây | Quyết định **nảy ra trong lúc chạy**, ở stage sau |
| Ở đâu | `Stage_1_Discovery/adr/*.md` (file thật) | `architecture_design.md` §6 (khối `### ADR-00x`) |
| Đánh số | **4 chữ số** — `0001`..`000N` | **3 chữ số** — `001`..`00N` |
| Nhận `governed_by` | có | có |
| Trỏ `governed_by` đi | không | chỉ tới `designed-adr` |

**Cạnh chỉ đi ngược thời gian.** `runtime-adr` khai `adr_refs: [designed-adr]`, nên
một quyết định lúc chạy có thể bị chi phối bởi quyết định thiết kế, nhưng không có
chiều ngược lại — Stage 1 không thể bị chi phối bởi thứ quyết định sau nó.

**Bề rộng số là thứ duy nhất phân biệt hai chuỗi trong văn xuôi**, và tài liệu nguồn
cũng tự nói vậy: *"Hai chuỗi ADR song song — đừng nhầm số hiệu."* Bản đầu của engine
khớp theo *giá trị số*, nên `ADR-001` bị nối vào `0001-…` — một quyết định hoàn toàn
khác, và mỗi cạnh sai đọc lên đều hợp lý.

Nay index khoá theo **chuỗi chữ số nguyên văn**, nên `"001"` và `"0001"` vốn đã là
hai khoá khác nhau và tự trỏ về hai họ khác nhau — không cần thêm máy móc gì. Hệ quả
phải nhớ: **hai chuỗi không được cùng bề rộng.** Trùng bề rộng thì engine ghi số đó
vào `adr_ambiguous`, **không sinh cạnh `governed_by`** cho nó và cảnh báo, chứ không đoán.

Thêm một chuỗi thứ ba (ví dụ quyết định phát sinh ở Stage 5) = khai một family với
`adr_series: true` và một bề rộng chưa ai dùng. Engine không cần biết trước có bao
nhiêu chuỗi; nó lấy số hiệu từ chính node mà mỗi chuỗi sinh ra, nên index và node
không thể lệch nhau.

## Định danh slice — số slice **không** bị dùng lại

**Stage 2b chỉ nối thêm số, không đánh số lại.** `slices/` không rỗng thì Bước 1
của `/ntapp-slice-planning` **luôn** rẽ sang Re-run mode — không có đường chạy nào
quay về Initial mode để đánh số từ 1. Re-run sửa tại chỗ và chỉ emit slice mới +
slice bị sửa.

**`archive/` là bản SAO, không phải bản chuyển đi.** Re-run copy toàn bộ
`SLICE-*.md` sang `archive/_v{N}_{timestamp}/` để rollback được, rồi mới sửa bản
sống. Nên file trong `slices/` **luôn là bản mới nhất**, và `**/archive/**` nằm
trong `exclude` mặc định ở mọi độ sâu → bản cũ không bao giờ vào bundle. Không cần
luật "chọn bản mới nhất": không có bản cũ nào để chọn nhầm.

**Vậy `feature:` để làm gì?** Nó trả lời *"slice này ra đời từ feature nào"* — thứ
manifest trước đây không ghi, mà ledger / bài học / node OKF (`slice_set`) đều cần
để gom nhóm. Nó **không** phải thứ đang gánh danh tính, vì `slice_id` hiện đã duy
nhất toàn cục.

Nó vẫn là lớp phòng hờ, và engine vẫn thủ: nếu một số bị **hai** feature cùng
nhận, chỉ mục **bỏ** số đó khỏi bảng tra phẳng, nên tham chiếu không đủ định tính
sẽ **báo lỗi kèm tên cả hai chủ** thay vì chọn bừa. Điều kiện đó chưa từng xảy ra
— và cách viết này giữ cho nó không bao giờ xảy ra *âm thầm*.
