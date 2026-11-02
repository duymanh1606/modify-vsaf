# Báo cáo đánh giá quy trình code bằng AI (bản nền)

**Ngày đánh giá:** 2026-07-07  ·  **Lần đánh giá thứ:** 2

**Model AI đã dùng:** Opus 4.8 (98%), Haiku 4.5 (2%), Sonnet 4.6 (0%)  *(tỉ lệ tính theo tổng token input+output)*

> Báo cáo này do `scripts/eval-harvester.py` **tự đọc các tài liệu Stage 1–5 rồi đếm ra số**, KHÔNG phải nhận xét chủ quan của con người. Mỗi con số chỉ phản ánh đúng những gì tài liệu ghi lại; muốn biết chỗ nào dễ sai, đọc mục **6. Giới hạn** trước khi kết luận.

**Phạm vi:** 0 lát cắt (slice) — .  *Lát cắt (slice) = một mảng tính năng làm trọn vẹn từ thiết kế đến code+test.*


## 1. Bảng tổng hợp từng lát cắt

> Mỗi cột là một lát cắt; mỗi dòng là một chỉ số. Các chỉ số được xếp theo **4 nhóm kể thành một mạch** — đọc từ trên xuống là đi hết vòng đời một lát cắt:
>
> **① Quy mô** (làm bao nhiêu) → **② Chất lượng ngay lần đầu** (code sạch tới đâu trước khi sửa) → **③ Độ ổn định** (yêu cầu & thiết kế có phải làm đi làm lại không) → **④ Nợ để lại** (việc đã biết nhưng cố ý hoãn sang sau).
>
> Tên viết tắt (FPY, EFF-…) giữ để tra cứu, nhưng luôn kèm nghĩa tiếng Việt.

| Chỉ số |  |
|---||
| **▸ ① QUY MÔ — lát cắt này gồm những gì** |  |
| Số đơn vị code (unit) |  |
| Kiểu chạy (AFK tự động / HITL có người duyệt) |  |
| Số tiêu chí nghiệm thu (AC) |  |
| **▸ ② TÍNH NĂNG CHẠY ĐÚNG NGAY LẦN ĐẦU — đo đúng-spec, không tính gia cố** |  |
| Số lỗi review phải sửa (tổng Patch) |  |
|   ↳ lỗi CHỨC NĂNG (Acceptance) / gia cố (bảo mật·edge·chất lượng) / chưa rõ |  |
| **Tính năng chạy đúng ngay lần đầu — F-FPY** (% feature KHÔNG lỗi chức năng; càng cao càng tốt) |  |
|   ↳ theo mật độ AC (1 − lỗi-chức-năng/AC; dịu hơn, không nhị phân hoá cả unit) |  |
| Yield gồm CẢ gia cố — SFPY (số FPY kiểu cũ; F-FPY≫SFPY = chạy được nhưng tốn công gia cố) |  |
| **▸ ③ ĐỘ ỔN ĐỊNH — yêu cầu & thiết kế có phải làm lại không** |  |
| Số yêu cầu đổi giữa chừng (hủy/sửa/hoãn AC) |  |
| Tỉ lệ yêu cầu đổi giữa chừng (càng thấp càng ổn định) |  |
| Số lần làm khác thiết kế (Deviation) |  |
| Dòng code thêm/xoá đã commit (LOC +/−, prod đã gắn id) |  |
| Số lần làm lại thiết kế (phiên bản DD) |  |
| Số lần cập nhật sau khi tạo (Change Log, đã trừ dòng khai sinh) |  |
| **▸ ④ NỢ ĐỂ LẠI — việc đã biết nhưng cố ý hoãn sang sau** |  |
| **Việc bị hoãn lại** (đang mở / đã đóng) |  |
| **Defer review ghi vào sổ — G1** (sổ ÷ review-defer) |  |
| Trong đó: lẽ ra tránh được |  |
| **Tỉ lệ nợ lẽ-ra-tránh-được — EFF-7** (càng thấp càng tốt) |  |
| **Tỉ lệ nợ đã xử lý xong — EFF-8** (càng cao càng tốt) |  |
| Số ngày trung bình nợ còn treo (EFF-8) |  |
| Model AI dùng (% token) |  |

*Cách đọc nhanh — lần theo đúng 4 nhóm:* **② F-FPY thấp** → tính năng KHÔNG chạy đúng spec ngay lần đầu (Acceptance Auditor phải sửa lỗi luồng chính/AC). *F-FPY chỉ đếm lỗi chức năng; lỗi bảo mật/edge/chất lượng nằm ở SFPY — F-FPY cao nhưng SFPY thấp = feature chạy được nhưng tốn nhiều công gia cố.* **③ Tỉ lệ đổi-giữa-chừng cao / Deviation nhiều / DD lên nhiều phiên bản** → yêu cầu & thiết kế chưa được chốt kỹ trước khi code. **④ Tỉ lệ nợ tránh-được cao** → phần lớn việc bị hoãn là do quy trình, không phải lý do khách quan.


## 2. Việc bị hoãn lại — phân theo lý do

> "Việc bị hoãn" (defer) = phần đã biết nhưng cố ý để làm sau. Chia 2 nhóm: **hợp lệ** (lý do khách quan, ngoài tầm kiểm soát) và **lẽ ra tránh được** (in đậm — nợ do quy trình). Mục tiêu là kéo nhóm tránh-được về 0.

| Lý do hoãn |  | Tổng | Đánh giá bản chất |
|---|---|---|

**Chưa có việc hoãn nào được ghi nhận** — không có nợ quy trình để xử lý ở thời điểm này.


## 2b. Gom nợ theo "một hành động đóng được nhiều việc"

> Nhiều việc bị hoãn thực ra cùng chờ MỘT điều kiện. Bảng này gom chúng lại: mỗi dòng là một hành động (hoặc sự kiện) mà khi xong sẽ đóng luôn nhiều việc cùng lúc — giúp biết nên ưu tiên làm gì. Dòng `— (rải rác)` = các việc không gom được, phải xử lý lẻ từng cái.

| Hành động đóng nợ | Số việc đóng được | Trong đó tránh-được | Thuộc lát cắt |
|---|--:|--:|---|
| **— (rải rác)** | 0 | 0 |  |

**Đang mở 0 việc tránh-được**: **0 việc gom cụm được** (chỉ cần làm xong 1 hành động/sự kiện là đóng cả cụm) + **0 việc rải rác** (phải xử lý từng cái). → Phần rải-rác chiếm n/a — đây mới là phần khó giải quyết thật sự (không có đòn bẩy chung).


## 3. Lỗi sinh ra ở đâu, bắt được ở đâu (từng đơn vị code)

> Bảng truy ngược theo từng unit: nhiều lỗi review (Patch) + ít việc hoãn → lỗi bị dồn về cuối; ngược lại nhiều việc hoãn → vấn đề được nhận ra nhưng đẩy sang sau.

> Cột **Lỗi chức năng** = patch luồng chính/AC (trừ F-FPY); **Gia cố** = bảo mật·edge·chất lượng (không trừ F-FPY). `⚠️suy luận` = story không tag lăng kính review nên phải đoán từ nội dung.

| Đơn vị code | Lát cắt | Số AC | Lỗi chức năng | Gia cố | Tổng Patch | Việc hoãn | Làm khác thiết kế | Lần cập nhật sau tạo |
|---|---|--:|--:|--:|--:|--:|--:|--:|

## 3b. Lệch thiết kế ↔ hợp đồng bắt ở cổng thiết kế (drift L3↔L2 — G8)

> 🔴 Chưa đọc được drift report nào (`Stage_4_Design/ui_schema/drift_report_*.md`). Khi có, phần này đếm số lệch L3↔L2 chặn được ở cổng thiết kế trước khi code.


## 3c. CR & lệch thiết kế trong Đặc tả chi tiết (L3 — G10)

> 🔴 Chưa đọc được file `detailed_design/*_detailed_design.md` nào. Khi có, phần này đếm CR (bảng lịch sử thay đổi), lệch thiết kế L3↔TechSpec (§1.2) và quyết định treo `[TBD]`.


## 3d. Drift & điều chỉnh tài liệu xuyên tầng (L2 → L3 → Story)

> Chưa đủ dữ liệu unit để tính drift xuyên tầng.


## 4. Cảnh báo tự động — lát cắt nào cần chú ý

> Máy tự gắn cờ khi một chỉ số vượt ngưỡng đáng lo. Không có cờ = chỉ số trong vùng an toàn.


## 5. Chi phí token

> **Đọc kỹ phần này có 2 loại token, đừng nhầm:**
>  - **Token-proxy** = cân độ dài tài liệu/code (~4 ký tự = 1 token). Đây CHỈ là thước đo "khối lượng sản phẩm làm ra", **không phải tiền**. Dùng để so tỉ lệ tài-liệu/code.
>  - **Token thật (burn)** = số token LLM thực sự xử lý (gồm đọc-lại ngữ cảnh, suy luận, thử lại). Đây mới là cái **ra tiền $** — xem §5.4.

> 📦 Đo gộp **8 code repo** (multi-repo FE+BE): `BMAD-METHOD`, `BMAD-METHOD-NTAPP`, `NTAPP-VSAF-Blended copy`, `VSAFV2`, `ai-operation-copilot`, `cdcn-policy-management-web`, `paperclip`, `product-catalog-cms-fe`


**5.1 Khối lượng theo từng bước (stage)**

> Cột **Token-proxy** = độ dài tài liệu sinh ra ở mỗi bước (không phải tiền). Cột **Token thật** = token LLM đã burn ở bước đó (ra tiền). Đặt cạnh nhau để thấy bước nào "nhẹ giấy tờ nhưng tốn AI" và ngược lại.

| Bước (stage) | Token-proxy (giấy tờ) | % giấy tờ | Token thật (ra tiền) | Model AI |
|---|--:|--:|--:|--:|
| Design System | 40.6k | 100% | — | — |
| **Tổng tài liệu** | **40.6k** | 100% | 1.00B | Opus 4.8 (98%), Haiku 4.5 (2%), Sonnet 4.6 (0%) |
| _Code chạy thật (đã gắn id)_ | 33.0k | — | — | — |
| _Code test (đã gắn id)_ | 0 | — | — | — |
| _Code test (chưa gắn id, thư mục `tests/`)_ | 488.0k | — | — | — |

> *Vài lưu ý khi đọc bảng:*
> - *Cột **Token thật** là tiền thật; cột **Token-proxy** chỉ là độ dài văn bản. Hai cột lệch nhau nhiều là bình thường — bước ít giấy tờ vẫn có thể tốn nhiều AI (đọc lại ngữ cảnh, thử nhiều lần).*
> - *Dòng `Stage 5 Test/ATDD` để token-thật `—` vì phần burn đó đã gộp chung trong `Stage 5 Story+Review` (cùng một bước), ghi lại sẽ thành đếm hai lần.*
> - *Các dòng code để `—` vì việc viết code do AI làm ngay trong bước Stage 5 rồi — không có "bước viết code" riêng để gán token.*
> - ***Tổng token thật** lớn hơn tổng các dòng phía trên, vì có cả những lượt làm việc đầu phiên chưa kịp gán vào bước nào.*
> - *`Design System` để model `—` vì không nhận diện được bước riêng cho nó.*

**5.2 Đầu tư bao nhiêu "giấy tờ" cho mỗi phần code? (token-proxy)**

> Mỗi tỉ lệ trả lời: cứ 1 phần code chạy thật thì kèm theo bao nhiêu phần tài liệu. **Số càng nhỏ càng gọn.** (Đây là token-proxy — đo công sức, không phải tiền.)

| Mã | So sánh | Cách tính | Kết quả |
|---|---|---|--:|
| COST-2 | Thiết kế (spec+design) so với code | (Stage 3 + Stage 4) ÷ code chạy thật | **0.00×** |
| COST-3 | Kiểm thử + review so với code | (story/review + test/ATDD + code test) ÷ code chạy thật | **14.77×** |
| COST-4 | Toàn bộ tài liệu so với code | tổng tài liệu ÷ code chạy thật | **1.23×** |
| COST-5 | Quản trị/định hướng so với code | (discovery + kiến trúc + design-system) ÷ code chạy thật | 1.23× |
| COST-6 | Tỉ lệ "phí phạm" do làm lại | phần tài liệu bản cũ đã thay ÷ tổng (cũ+mới) của kiến trúc & thiết kế | n/a |

**5.3 Khối lượng code theo từng lát cắt (token-proxy)**

> "Code chạy thật" so với "code test" của từng lát cắt; tỉ lệ test/code cao = phủ test nhiều hơn.

| Lát cắt | Code chạy thật | Code test | Test so với code |
|---|--:|--:|--:|
| (chưa gán lát cắt) | 33.0k | 0 | 0.00× |

**5.3b Sửa đi sửa lại ở tầng code — LOC đã commit (EFFY-3b)**

> Đếm trực tiếp từ `git log --numstat` của code repo (đo **dòng chảy commit**, khác với token-proxy ở trên đo **trạng thái file cuối**). Cột **+/−** là số dòng tuyệt đối đã thêm/xoá qua toàn bộ lịch sử. **Tỉ lệ thrash** = (thêm+xoá) ÷ số dòng prod còn sống = bao nhiêu dòng phải viết để giữ lại 1 dòng (**1.0 = không phí**; càng cao càng viết-rồi-xoá nhiều).

> Quét **8360** commit.

| Loại code | Dòng thêm (+) | Dòng xoá (−) | Dòng còn sống | Tỉ lệ thrash |
|---|--:|--:|--:|--:|
| **Code chạy thật (prod, đã gắn id)** | +2,874 | −274 | 2,600 | **1.21×** |
| Code test | +40,671 | −4,260 | — | — |
| Khác (đã xoá / chưa gắn id) | +655,865 | −258,446 | — | — |

*Phân theo lát cắt (chỉ file prod đã gắn id còn trên đĩa):*

| Lát cắt | Dòng thêm (+) | Dòng xoá (−) |
|---|--:|--:|
| (chưa gán lát cắt) | +2,874 | −274 |

> *Lưu ý:* commit ĐẦU TIÊN của dự án dựng-lại (brownfield) dồn cả codebase cũ vào một lần → cột **+** phình to nhưng **−**≈0 nên tỉ lệ thrash vẫn ~1.0 (không bị thổi). Dòng "Khác" gom churn của file đã bị xoá hẳn (không còn header để quy về prod/slice) — đây là giới hạn attribution, không phải lỗi.


**5.4 Chi phí tiền thật (token LLM đã burn)**

> ⚠️ **Độ phủ nhật ký phiên thấp (G2) — burn dưới đây là CẬN DƯỚI, không phải con số đủ.** Phiên Claude Code chỉ trải **2026-06-05 → 2026-07-07**, trong khi commit git của code repo trải **2020-11-17 → 2026-06-17** (8360 commit). Phủ ~1% khoảng hoạt động → nhiều phiên (chạy máy khác / đã xoá / không gom đủ) **thiếu**. Mọi con số $/token bên dưới là **một phần**, KHÔNG dùng để so sánh giữa dự án.

> Token thật chia làm 4 loại; **đơn giá theo TỪNG model** (Opus/Sonnet/Haiku khác nhau — chi tiết ở bảng 5.4b). Quy ước cache giống nhau mọi model: **ghi cache = 1.25× input** (lưu ngữ cảnh, TTL 5 phút), **đọc cache = 0.1× input** (rẻ bằng 1/10), **output** đắt nhất (= 5× input). Cột "Đơn giá TB" bên dưới là bình quân gia quyền theo cơ cấu model.

| Loại token | Số token | Đơn giá TB ($/1M) | Thành tiền | % chi phí |
|---|--:|--:|--:|--:|
| Input mới (chưa cache) | 7.4M | 4.96 | $36.71 | 3% |
| Ghi cache | 51.5M | 6.04 | $311.09 | 27% |
| Đọc cache | 927.9M | 0.49 | $457.32 | 40% |
| Output (AI sinh ra) | 13.8M | 24.76 | $340.84 | 30% |
| **Tổng cộng** | **1.00B** | — | **$1,145.96** | 100% |


**5.4b Chi phí theo model AI**

> Mỗi model một đơn giá (Opus 4.8 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5 — input/output trên 1 triệu token). Sub-agent thường chạy model rẻ (Haiku) → tách ra để thấy đúng cơ cấu tiền, không quy hết về Opus.

| Model | Input mới | Ghi cache | Đọc cache | Output | Tổng token | Thành tiền | % chi phí |
|---|--:|--:|--:|--:|--:|--:|--:|
| Opus 4.8 | 7.3M | 49.1M | 910.1M | 13.5M | 980.1M | $1,137.25 | 99% |
| Haiku 4.5 | 69.8k | 2.0M | 15.4M | 104.0k | 17.5M | $4.60 | 0% |
| Sonnet 4.6 | 0.1k | 399.7k | 2.5M | 125.2k | 3.0M | $4.12 | 0% |
| <synthetic> | 0 | 0 | 0 | 0 | 0 | $0.00 | 0% |
| **Tổng** | | | | | **1.00B** | **$1,145.96** | 100% |

- **Tổng token thật đã burn**: 1.00B token **(một phần — cận dưới)** (gồm input 986.8M + output 13.8M)
- **Tổng chi phí tiền thật: $1,145.96** (định giá theo từng model)
- **Chi phí cho mỗi tiêu chí nghiệm thu (AC)**: n/a token/AC
- **Hệ số khuếch đại**: 13590.66× — cứ mỗi 1 token "sản phẩm cuối" (73.6k token-proxy) thì AI thực sự xử lý chừng đó token. Phần lớn là đọc lại ngữ cảnh và thử lại — bình thường với quy trình nhiều bước.

## 6. Giới hạn của báo cáo — đọc trước khi kết luận

> Báo cáo do máy đọc văn bản đếm ra, nên có những chỗ dễ lệch. Biết trước các giới hạn này để không hiểu sai con số.

- **Cách đếm số tiêu chí nghiệm thu (AC)**: máy thử 3 cách theo thứ tự ưu tiên — (1) đề mục đậm `**AC-N**`, (2) danh sách đánh số `N. **…**`. Cả hai đều đáng tin. Chỉ khi cả hai đều trượt mới rơi xuống (3) *đếm gián tiếp* (`⚠️`): gom mọi chuỗi `AC-N` xuất hiện trong phần AC rồi đếm số khác nhau — cách này dễ lệch (không nở dải `AC7–AC14`, đếm nhầm cả tham chiếu chéo) nên FPY của unit đó kém tin cậy. *Hiện chưa unit nào rơi vào cách (3); nếu thấy `⚠️` ở §3 thì mới cần dè chừng.*
- **F-FPY chỉ đo lỗi CHỨC NĂNG, không đo gia cố**: tử số chỉ gồm patch khiến *tính năng chạy sai spec/luồng chính* — bám theo lăng kính **Acceptance Auditor** của `/bmad-code-review`. Lỗi bảo mật, edge-case, chất lượng/convention **cố ý loại** (feature vẫn chạy, chỉ cần gia cố) → xem ở **SFPY** và cột *Gia cố* §3. Cách phân loại 3 tầng: (1) **tag lăng kính** `(auditor)`/`(blind+edge)` ở cuối bullet patch — tin cao; (2) story không tag → *suy luận* (`⚠️`): dẫn `AC-N` + động từ hỏng ⇒ chức năng, còn lexicon bảo mật/edge/quality ⇒ gia cố; (3) không đủ tín hiệu → **chưa phân loại** (cột Gia cố ghi `(+N?)`), KHÔNG ngầm tính sạch. *6/17 story HUB không tag lăng kính → rơi tầng (2), F-FPY của chúng kém chắc hơn — đã gắn `⚠️suy luận`.* Ngưỡng severity (Critical/High) hiện CHƯA dùng để lọc; một AC-nit nhỏ vẫn tính như một lỗi chức năng.
- **Chưa đo được tốc độ làm việc**: mọi mốc thời gian trong Change Log đều ghi cùng một ngày, nên không tính được mất bao lâu cho mỗi bước. Muốn đo cần ghi mốc bắt đầu/kết thúc cho từng stage.
- **"Số lần cập nhật sau khi tạo"**: đếm số dòng Change Log có ngày rồi **trừ 1 dòng khai sinh** (dòng "tạo story / scaffold" đầu tiên) — để unit tạo-xong-là-done tính 0 lần sửa, không phải 1. Giả định dòng đầu luôn là dòng tạo; nếu một unit ghi Change Log bắt đầu giữa chừng (thiếu dòng tạo) thì con số sẽ bị hụt 1.
- **Có thể sót "làm khác thiết kế"**: máy chỉ bắt được khi ghi rõ là deviation; nếu viết lẫn trong đoạn văn dài thì có thể bỏ lọt.
- **Phân loại việc-hoãn do người ghi**: lý do/đánh-giá-tránh-được/trạng-thái lấy thẳng từ sổ `deferred-work.md` (do người điền), không phải máy đoán. Tuổi nợ tính tới ngày mốc 2026-06-11.
- **Số liệu do AI tự khai**: số lần làm-khác-thiết-kế và việc-hoãn là do agent tự ghi, nên phụ thuộc mức độ trung thực khi ghi chép.
- **Dòng code thêm/xoá (LOC committed, §5.3b)**: đếm từ `git log --numstat` của **mọi code repo** phát hiện được (multi-repo FE+BE: gộp qua từng repo, mỗi repo chạy git log riêng). Churn của file đã **bị xoá hẳn** không quy được về prod/lát cắt (không còn header `id:`) → gom vào dòng "Khác". Repo brownfield **chưa gắn `id:` header** (code cũ Java/FE) sẽ rơi hết vào "Khác" và prod=0 — đó là theo thiết kế (attribution dựa header), không phải lỗi đọc. Đổi-tên file (nếu git không nhận diện được rename) bị tính thành xoá+thêm → có thể thổi nhẹ tỉ lệ thrash. Commit đầu của dự án brownfield dồn codebase cũ vào một lần làm cột "thêm" rất lớn (nhưng không thổi tỉ lệ vì gần như không có dòng xoá). LOC chỉ là **mẫu số chuẩn-hoá**, KHÔNG phải thước đo năng suất — nhiều dòng ≠ nhiều giá trị.
- **Mẫu còn nhỏ** (3 lát cắt): chỉ nên xem là xu hướng, chưa đủ để kết luận chắc; dự án dựng lại từ code cũ (brownfield) thường có nhiều việc-hoãn/tái-sử-dụng hơn do nền tảng cũ.
- **Hai loại token khác nhau, đừng nhầm**: §5 có cả *token-proxy* (cân theo độ dài văn bản, ~4 ký tự/token — KHÔNG phải tiền) và *token thật* (LLM thực sự xử lý, gồm cả đọc-lại ngữ cảnh + suy luận + thử lại, mới ra chi phí $). Token thật được tự gom từ nhật ký phiên Claude Code; nếu không có sẽ hiện `n/a`. Token code đếm theo file có dòng `id:` trong code repo; test `tests/` không gắn id thì đếm riêng, không quy về lát cắt nào.
