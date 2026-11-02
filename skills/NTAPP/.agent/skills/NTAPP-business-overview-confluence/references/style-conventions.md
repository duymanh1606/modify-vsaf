# Quy ước trình bày tài liệu Tổng quan nghiệp vụ

Mặc định khi template không nói khác — **template động thắng** (BƯỚC 3 fetch template thật, đọc hướng dẫn
trong từng mục để bám). Các default dưới đây **đã canh theo template `Tổng quan nghiệp vụ hệ thống`** (host `.35`,
space TDOV). Luôn **song ngữ**: non-tech đọc được, dev/vận hành vẫn đủ chi tiết. Tiếng Việt.

> ⚠️ Template chứa **nội dung ví dụ của dự án khác** (vd bảng VOUCHER_*, App VTP). Coi template là
> **khung mục + hướng dẫn trình bày**; **thay toàn bộ data ví dụ** bằng dữ liệu dự án thật (từ HLD/WBS/PRD/code).

## 0. VĂN PHONG & KHỐI BỊ CẤM (áp cho toàn tài liệu)

**0.1 Văn phong — nghiệp vụ chuyên nghiệp, không văn nói.** Đây là tài liệu bàn giao/nghiệm thu, người đọc là
PO · BA · SA · vận hành · kiểm thử. Viết như đặc tả, không như lời giảng.

| CẤM (văn nói / giảng giải) | DÙNG (thuật ngữ nghiệp vụ) |
|:---|:---|
| "Dễ hiểu:", "Tóm lại:", "Nói cách khác", "Hiểu đơn giản là" | Nêu thẳng nội dung, không rào đón |
| "bóc tách", "mổ xẻ", "xương sống", "bức tranh", "kết cấu xây dựng nên hệ thống" | "phân rã", "cấu trúc", "phạm vi", "thành phần" |
| "hệ thống làm được gì", "hệ thống nói chuyện với nhau bằng giao thức nào" | "phạm vi chức năng của hệ thống", "cơ chế tích hợp giữa các thành phần" |
| "chạy ngầm", "chạy nền", "kéo file", "đẩy sang", "bắn event" | "xử lý tự động theo lịch", "tiếp nhận tệp", "chuyển sang", "phát sự kiện" |
| "ok", "xong xuôi", "hơi", "khá là", "cực kỳ", "siêu" | bỏ hẳn hoặc thay bằng định lượng cụ thể |
| Emoji, dấu "!", câu cảm thán, ngoặc đơn kiểu ghi chú cá nhân | Câu trần thuật, dấu chấm |

Quy tắc bổ sung: câu trần thuật ngắn (≤ 30 từ); thuật ngữ dùng **nhất quán một cách gọi** xuyên tài liệu
(chốt theo `CONTEXT.md`/HLD, không đổi từ đồng nghĩa giữa các mục); tên service/bảng/mã đơn vị viết đúng
định danh thật; số liệu phải có nguồn.

**0.2 KHÔNG đưa lên trang xuất bản (khối meta — nói về cách làm tài liệu, không phải nghiệp vụ):**

| Khối bị cấm | Xử lý thay thế |
|:---|:---|
| Hộp `tip`/`note` tóm tắt kiểu "Dễ hiểu / Tóm lại" trước mỗi quy trình | Bỏ. Cần dẫn nhập → **1 câu văn xuôi** nêu phạm vi + đầu vào/đầu ra của quy trình |
| Hộp cảnh báo "Phạm vi — không đưa vào mục này…" và mọi đoạn giải thích **tiêu chí lựa chọn nội dung** | Bỏ. Đó là quy tắc sinh tài liệu (nằm ở skill), không phải nội dung nghiệp vụ |
| Đoạn "Nguyên tắc cốt lõi…" + bảng giải nghĩa **loại lá / loại thành phần** (`Loại lá \| Bản chất \| Ví dụ`) | Bỏ. Loại đã thể hiện bằng **màu nhóm trên sơ đồ** + cột *Kênh thực hiện* trong bảng |
| Hộp thông tin đối chiếu số lượng ("N dòng khớp N lá…", "xem Coverage Matrix §…") | Bỏ. Việc khớp 1-1 là điều kiện chất lượng khi sinh, không phải nội dung cần công bố |
| Hộp `warning` "Điểm cần xác nhận (N mục)" gom toàn bộ mâu thuẫn kỹ thuật | Bỏ khỏi trang. Giữ trong `{bo_dir}/erd-consolidated.md`; đánh dấu `[Cần xác nhận]` **tại đúng ô/dòng** liên quan; liệt kê đầy đủ cho user ở báo cáo cuối (workflow §10) |
| Mọi câu tự mô tả tài liệu ("tài liệu này được sinh bởi…", "phần dưới đây sẽ…") | Bỏ |

Ngoại lệ được giữ: hộp `info` đầu trang mô tả nguồn dữ liệu + định dạng sơ đồ (template quy định), macro `toc`,
bảng đơn vị liên quan, bảng ghi nhận thay đổi.

## 1. Mục đích
Đoạn ngắn nêu mục tiêu và phạm vi tài liệu + **bảng góc nhìn**:
`Phần | Góc nhìn | Nội dung trả lời` — Mô hình tổng quan = cấu trúc (tĩnh) / Quy trình = hành vi (động) / ERD = dữ liệu.
+ **Vai trò tài liệu** (tiếp nhận hệ thống · nền tảng cho tài liệu chi tiết · thống nhất cách hiểu · bàn giao/vận hành)
+ **Nguyên tắc nhất quán chéo**: thành phần trong Mô hình xuất hiện đúng trong Quy trình; thực thể ERD khớp dữ liệu chạy qua các bước.

## 2. Mô hình tổng quan — bố cục VÙNG (zone) trái→phải
- Sơ đồ (`overview_zones`) chia **các vùng từ trái sang phải**:
  1. **Nguồn dữ liệu đầu vào** (trái) — nhóm theo loại: (a) tổ chức tài chính ngoài (NAPAS, các bank…), (b) hệ đối tác/merchant, (c) hệ nội bộ (core payment, SOF, gateway, BI…).
  2. **Hệ thống lõi** (giữa) — hệ thống chính cần mô tả, kèm **các bước xử lý bên trong** (thu thập → mapping → đối soát → gửi kết quả → ghi lịch sử) và **kho dữ liệu trung gian**.
  3. **Cơ chế tích hợp** — kênh truyền giữa các vùng: API, file (ftp/sftp), message queue (Kafka topic)…
  4. **Giao diện người dùng (FE)** (phải) — các màn hình chính, nhóm theo vai trò.
  5. **Actor** (ngoài cùng phải) — người que, mỗi actor 1 mũi tên tới FE tương tác.
- Quy ước: **màu/khung phân biệt** hệ ngoài (xám nét đứt) vs nội bộ vs lõi; thể hiện **chiều mũi tên in → xử lý → out**; ít mũi tên cấp cao giữa các vùng. Full-system: đánh dấu thành phần **xây mới** (viền nhấn).
- Kèm **bảng "Mô tả các thành phần"**: `STT | Tên thành phần | Mô tả` (Mô tả = bullet liệt kê chi tiết bên trong). Mỗi thành phần trên sơ đồ có 1 dòng.

## 3. Quy trình nghiệp vụ (mỗi nghiệp vụ 1 mục con)
- **KHÔNG dùng hộp `tip` "Dễ hiểu"** (§0.2). Nếu cần dẫn nhập: **đúng 1 câu văn xuôi** nêu phạm vi quy trình +
  đầu vào → đầu ra (vd "Quy trình tiếp nhận tệp đối soát từ đối tác, đối chiếu giao dịch và phát hành báo cáo chênh lệch."), rồi vào thẳng sơ đồ.
- **Sơ đồ swimlane / 3 cột** (`process_3col`): cột 1 = **đối tượng/vai trò** thực hiện bước (lane), cột 2 = bước đánh số (hình thoi cho điểm quyết định, nhãn Yes/No trên nhánh), cột 3 = mô tả; có node Bắt đầu/Kết thúc; nhánh rẽ phải quay về hoặc dẫn tới kết thúc hợp lý.
- **Bảng bước 5 cột** (đúng template): `STT | Bước | Vai trò thực hiện | Mô tả / Điều kiện / Dữ liệu | Bước tiếp theo`.
  - *Vai trò thực hiện* = **tên service/đơn vị thật** (vd `reconciliation-process`), không "hệ thống" chung chung; hệ ngoài để tên đối tác + chú "(hệ thống ngoài)".
  - *Mô tả / Điều kiện / Dữ liệu* = ngôn ngữ nghiệp vụ + gộp kết quả/rẽ nhánh; bước ghi DB → nêu **điều kiện + trường ghi** ngay tại ô (không viết câu lệnh SQL).
- Mỗi node trên sơ đồ có đúng 1 dòng trong bảng (khớp số 1-1).

## 4. ERD (2 tầng — nguồn: erd-consolidated.md)

**Tầng A — Bức tranh quan hệ tổng (cross-store):**
- 1 sơ đồ draw.io `erd(entities, rels, collapsed=True)` — entity thu gọn (tên + PK/FK), FK bắc cầu giữa các store.
- Bảng: `STT | Bảng nguồn | Khoá | Bảng đích | Store ↔ Store`.

**Tầng B — Chi tiết per-datastore:**
- Mỗi datastore 1 heading con + 1 sơ đồ cụm (bảng + quan hệ nội cụm).

> **Chọn hàm vẽ:** sơ đồ mà trọng tâm là **quan hệ giữa các bảng** (Tầng A + Tầng B, field nằm trong expand
> bên dưới) → dùng **`erd_graph()`**: xếp bảng theo tầng (BFS + barycenter), giới hạn `max_cols` cột mỗi hàng,
> định tuyến trực giao qua kênh/máng nên **cạnh không cắt hộp và không đè nhau**. Chỉ dùng `erd()` khi thật sự
> cần **vẽ lưới field ngay trên sơ đồ** — với vài chục quan hệ thì `erd()` để draw.io tự định tuyến sẽ ra
> chùm đường chéo cắt xuyên các bảng (thực tế DSTT 2026-08-07: 30 quan hệ / 28 bảng).
- Bảng tổng hợp: `STT | Tên bảng | Datastore | Ý nghĩa`.
- Mỗi bảng → macro `ac:structured-macro ac:name="expand"` (title = tên bảng) chứa:
  - Bảng Tầng 1: `Tên field | Kiểu | Ý nghĩa`.
  - `expand` LỒNG (title "Chi tiết kỹ thuật đầy đủ") chứa bảng Tầng 2: `Field | Type | Constraints | Storage | Description`.
- Tên bảng/field = tên DB thật (đúng nguồn §11.2). Drift/ghi chú code-as-is chỉ ở Tầng 2.
- Thiếu Stage 3 → chỉ render Tầng A từ arch §ERD + ghi `[Cần xác nhận]` field-level.
- 🔴 **Gate đối chiếu code (bắt buộc):** mọi bảng và quan hệ phải xác minh bằng khai báo thật trong code trước khi render; mỗi quan hệ phải ghi **khoá nối** + **loại quan hệ** (khoá ngoại / khoá nghiệp vụ / khoá tài liệu / luồng xử lý / nhật ký). Bảng chỉ có trong HLD → loại khỏi sơ đồ và báo user kèm bằng chứng. Chi tiết + các bẫy nhận dạng: [erd-consolidation.md](erd-consolidation.md) §6b.
- ⚠️ **KHÔNG publish hộp "Điểm cần xác nhận" gom cả cụm** (§0.2). Điểm chưa chốt ghi `[Cần xác nhận]` **tại đúng ô field/dòng quan hệ**;
  danh sách đầy đủ nằm ở `erd-consolidated.md` + báo cáo cuối cho user.

## 5. Biểu đồ trạng thái
State diagram (`state_diagram`) cho **mỗi thực thể có vòng đời rõ** (vd đối tác Cover→Active→Inactive; lệnh chi trả INIT→PROCESS→SUCCESS/FAIL/TIMEOUT; điều chỉnh APPROVING→APPROVED/REJECTED; hồ sơ tổng hợp Draft→InProgress→…). Ghi nhãn điều kiện chuyển trạng thái. Bỏ qua thực thể CRUD đơn giản không có vòng đời.
- Trạng thái xếp **dọc theo trục chính** theo đúng thứ tự vòng đời thuận. `state_diagram` tự tách làn: chuyển tiếp liền kề đi thẳng trục,
  bước nhảy tiến và cạnh vào *Kết thúc* đi rail bên phải, quay lui/tự lặp đi rail bên trái (nét đứt) — **mỗi cạnh một làn riêng, không chồng nhau**.
  → Xếp thứ tự `states` sao cho phần lớn chuyển tiếp là liền kề; trạng thái kết thúc bất thường (FAIL/TIMEOUT/REJECTED) đặt **cuối danh sách**.
- Nhãn chuyển trạng thái = **điều kiện nghiệp vụ** ngắn (≤ 6 từ), không mô tả kỹ thuật.

## 6. Biểu đồ phân rã chức năng

> **Quy tắc sinh (nội bộ skill — KHÔNG in ra trang, xem §0.2).** Cây phân rã chỉ chứa **chức năng nghiệp vụ**: phần người dùng thao tác + phần hệ thống xử lý tự động điều phối luồng dữ liệu. Loại khỏi cây:
> - **Hợp đồng tích hợp** (contract event/API — INT-EXT/INT-INT, Kafka topic, format tệp) → thuộc §2 Mô hình tổng quan (cơ chế tích hợp) / tài liệu tích hợp.
> - **Observability / vận hành** (logging, metrics, tracing, correlation-id, audit hạ tầng) → mối quan tâm vận hành xuyên suốt.
>
> Áp quy tắc này khi **chọn lá**; tuyệt đối không diễn giải lại quy tắc thành nội dung trên trang.

- Cây building-block **3 loại** (`breakdown_tree`; mỗi lá thuộc 1 loại, tô màu phân biệt):
  - **Frontend** — chức năng người dùng thao tác (màn hình, widget).
  - **Backend — kết nối** — API/endpoint/gateway/adapter phục vụ FE hoặc **thực thi** tích hợp hệ ngoài (đơn vị *thực thi* pull/push, không phải bản *hợp đồng* contract).
  - **Backend — xử lý tự động** — job định kỳ, consumer/producer hàng đợi, đồng bộ, phát sự kiện. **Không bỏ sót phần xử lý tự động.**
- **Full-system (tùy chọn):** tách **2 nhánh** — A "Nền tảng sẵn có (brownfield)" (tô xám, mức cụm, đọc từ WBS) + B "Xây mới" (tô màu theo 3 loại, mức feature, đọc từ feature_design_parts). Build-scope: chỉ nhánh B. Xem [scope-brownfield-vs-newbuild.md](scope-brownfield-vs-newbuild.md).
- **Bố cục sơ đồ:** `breakdown_tree` vẽ bracket kiểu sơ đồ tổ chức — gốc xuống bus ngang rồi rẽ vào từng cụm; trong cụm dùng **một trục dọc**, mỗi lá một nhánh ngang vào cạnh trái. Không có cạnh nào cắt qua hộp khác.
  - ⚠️ **Quá ~40 lá / quá 6 cụm trên MỘT sơ đồ** → chữ bị thu nhỏ không đọc được khi Confluence scale. Khi đó **tách nhiều sơ đồ theo cụm nghiệp vụ** (mỗi heading con 1 sơ đồ, dùng chung 1 bảng mô tả phẳng ở cuối), KHÔNG kéo dài một sơ đồ khổng lồ.
- **Bảng mô tả — bám template: ĐÚNG 1 bảng** khớp **từng lá** (`STT | Kênh thực hiện | Đối tượng sử dụng | Chức năng | Ý nghĩa`). Để mã đơn vị làm tiền tố trong ô *Chức năng* cho truy vết.
  - ⚠️ **KHÔNG thêm** bảng giải nghĩa 3 loại lá, đoạn "Nguyên tắc cốt lõi", hộp đối chiếu số lượng lá/dòng, bảng "tổng hợp số đơn vị theo cụm", hay nhiều bảng con per-cụm (§0.2). Template chỉ có 1 bảng mô tả phẳng; loại lá đọc qua **màu nhóm trên sơ đồ**, cụm đọc qua **thứ tự dòng + cột Kênh thực hiện**.
  - Việc bảng khớp 1-1 với số lá là **điều kiện chất lượng khi sinh** — tự kiểm rồi báo cho user ở báo cáo cuối, không công bố trên trang.

## Chung
- Đầu trang: giữ **bảng Đơn vị yêu cầu/liên quan** (task-list ĐVYC/ĐVLQ — xem confluence-publish.md §3) + macro `toc` + hộp `info` mô tả nguồn/định dạng sơ đồ + **bảng ghi nhận thay đổi** (ngày = date macro).
- Diễn giải kỹ thuật → nghiệp vụ ở phần thân; chi tiết kỹ thuật để ở cột/khối riêng, không trộn khiến non-tech khó đọc.
- **No-silent-defaults:** không bịa số liệu/tên tổ chức/đối tác; suy từ tài liệu → ghi kèm nguồn; không chắc → `[Cần xác nhận]`.
