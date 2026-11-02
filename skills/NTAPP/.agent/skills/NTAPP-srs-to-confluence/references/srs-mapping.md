# SRS Mapping — spec (Stage 4 DD + Stage 5) → khung SRS Confluence

Ưu tiên khung **fetch được từ template Confluence** (workflow §3). Bảng dưới là *cách map nội dung spec vào từng mục* + **fallback khi fetch template lỗi**.

## Khung SRS fallback theo type

**Chung (mọi type):**
1. Thông tin tài liệu (tên, mã ID, hệ thống, version, lịch sử thay đổi)
2. Mục tiêu & phạm vi
3. Actor / đối tượng sử dụng
4. Thuật ngữ & viết tắt
5. Yêu cầu chức năng
6. Luồng nghiệp vụ (sequence)
7. Yêu cầu dữ liệu
8. Yêu cầu phi chức năng
9. Tài liệu liên quan

**type=api — thêm:** Đặc tả API (endpoint, method, request schema, response schema, mã lỗi, config/secret redacted).
**type=consumer — thêm:** Trigger (scheduler/listener/queue), tần suất, input source, xử lý idempotent/retry, output.
**type=web — thêm:** Đặc tả màn hình (HTML nhúng), danh sách control, mapping control ↔ API.

## Map nguồn → mục

| Mục SRS | Nguồn spec |
|:---|:---|
| Mục tiêu & phạm vi | DD §overview blockquote + story "so that" |
| Actor | story "As a" + DD actor |
| Yêu cầu chức năng | DD §logic + story Acceptance Criteria (mỗi AC → 1 yêu cầu) |
| Luồng nghiệp vụ | DD sequence / `feature_design_parts/{id}/f3_sequence_diagrams_part.md` |
| Crosslink luồng xử lý | DD §context/entrypoint (tiến trình cha gọi tới = upstream) + bước hand-off downstream → dòng `Refer` hyperlink trong ô Ghi chú §2.2. Chi tiết + cách tìm pageId: `confluence-server-publish.md §4 điểm 4` |
| Yêu cầu dữ liệu | DD §data (§8.1 field-level) |
| Đặc tả API | DD contract `INT-EXT-*` (request/response/URL/header/error) — pair-merge nếu chọn merge |
| Phi chức năng | DD §NFR |

**Redact secret:** User/Pass/ClientId/CIF/account/private-key → chỉ ghi config key + nơi nạp (không ghi giá trị thật).

## Nhúng HTML màn hình (type=web) — HTML macro

> 🔴 **KHÔNG được thay bản mô phỏng HTML bằng bản vẽ draw.io** — kể cả khi các trang SRS anh em trong space đang dùng macro draw.io cho màn hình. Lần SCR-EMBED-PMT đã đi đường tắt này và user bác: *"các màn hình cần vẽ html và đính kèm vào tài liệu, hiện đang vẽ draw.io là k đúng yêu cầu"*. Server `.35` tắt HTML macro ⇒ đi đúng nhánh **fallback** ở cuối mục này: upload `p_screen*.html` làm attachment + chèn **ảnh screenshot inline** (`<ac:image><ri:attachment/>`) + link `<ac:link><ri:attachment/>` để tải bản HTML. Chụp ảnh bằng Chrome headless (`--headless=new --force-device-scale-factor=2 --window-size=W,H --screenshot=...`), cắt sát nội dung, và **Read lại ảnh** trước khi publish.

**Nguồn `p_screen.html`:** SRS skill TỰ render (không delegate) — 1 file HTML self-contained (inline CSS) từ `ui_schema_{id}.json` (layout/component/control) + `{id}-full-screen.md` (mô tả filter/cột/nút/tab/luồng) + DD §UI. `NTAPP-ui-generation` chỉ sinh `ui_schema` khi thiếu (KHÔNG render HTML). Render chưa sát thực tế → tham chiếu code FE thật `*.component.html`/`.ts` render lại.

**Fidelity — BẮT BUỘC bám code FE thật khi màn hình ĐÃ được code (brownfield):** `ui_schema`/story hay drift so với UI thật (màu nút, màu header bảng, layout nhãn/ô). Nếu component đã tồn tại trong repo FE, dựng mock TỪ chính `*.component.html` + file theme (`common.css`/`btn.css`/`style.css`) + nhãn i18n (`vi.json`) — KHÔNG đoán màu/nhãn từ ui_schema. Rút đúng token: class nút thật (vd `btn-blue-green`), màu `thead th`, count, `form-control`, thứ tự + tên cột bảng, thứ tự trường modal. Đối chiếu screenshot mock với UI thật trước khi publish.

**⚠️ DD/Story CŨNG có thể stale — không dừng lại ở "đối chiếu ui_schema", phải đối chiếu tới tận code khi có sẵn.** Case thật (SCR-COMPOSITE-DETAIL, 2026-08-06): SRS v1 dựng đúng theo DD §2.3 + tiêu đề Story ("4 tab Info/Sub-links/Timeline/Sync") — nhưng CẢ HAI nguồn này đã lag so với code đang chạy (CR gỡ tab Sync thành nút header, đổi tên 2 tab còn lại, và 1 AC — "Xác nhận quyết định hàng loạt" — thực ra CHƯA từng được code). User phải tự phát hiện qua ảnh chụp màn hình thật rồi yêu cầu sửa lại. Bài học — khi màn đã có code (brownfield):
- Tên tab/nhãn control: lấy trực tiếp từ file i18n (`vi.json`/`en.json`) đang được template `{{ 'key' | translate }}` trỏ tới — KHÔNG lấy từ tên biến/AC trong Story (tên biến thường đặt theo ý đồ thiết kế ban đầu, có thể khác nhãn hiển thị thật hoặc đã đổi mà Story quên cập nhật).
- Mỗi control/button liệt kê trong bảng §2.x PHẢI trỏ được tới đúng dòng code (`*ngIf`, `(click)`, method) đang tồn tại trong `*.component.html`/`.ts` — nếu không tìm thấy, đó là control CHƯA code (hoặc đã gỡ), phải bỏ khỏi bảng dù DD/Story có nhắc tới.
- Modal vs inline-panel/expand: đọc đúng cơ chế mở (`ModalDynamicService.open(...)` = modal thật; `*ngIf="xPanelOpen"` toggle bằng biến local = inline panel, KHÔNG phải modal) — đặt sai tên mục (vd "Modal Thêm ..." khi thực ra là panel) khiến user đọc xong thao tác trên UI thật không khớp.
- Khi nghi ngờ 1 mục có vẻ "không đúng thực tế" (user báo hoặc tự thấy lệch) → luôn quay lại đọc code gốc (`.component.html/.ts` + entity BE nếu cần xác nhận tên bảng/cột) trước khi sửa câu chữ — đừng chỉ diễn đạt lại theo DD/Story một lần nữa (2 nguồn đó chính là nguồn gây lệch).

**Bảng ĐVYC/ĐVLQ ("XÁC ĐỊNH ĐƠN VỊ YÊU CẦU...") — không phải lúc nào cũng cần:** mục này chỉ áp cho SRS gốc/độc lập cần quy trình phê duyệt riêng. Nếu target page là **trang con nằm trong 1 cây trang có sẵn** (không do skill này tạo mới từ đầu, ví dụ trang do user chỉ định thủ công nằm trong hierarchy KBNV/nghiệp vụ cũ) và user yêu cầu bỏ mục này (hoặc trang cha/trang anh em cùng cây đã có quy trình phê duyệt riêng ở nơi khác) → bỏ hẳn cả heading + bảng, không giữ lại dạng rút gọn. Mặc định (chưa có chỉ định khác) vẫn giữ theo template gốc.

**Bảng ghi nhận thay đổi tài liệu — GIỮ ĐỦ CỘT theo template gốc (8-10 cột, kèm Link PYC/Story/CR), KHÔNG rút gọn.** Ở lần **tạo mới (A)**, mô tả 1-2 câu tóm tắt phạm vi — KHÔNG liệt kê chi tiết từng control/AC (đó là việc của §2).
- Dòng mới thêm lên ĐẦU bảng, giữ nguyên toàn bộ dòng cũ, version +1. Sửa câu chữ/lỗi chính tả không đổi nội dung nghiệp vụ thì không chạm bảng này.

**🚫 KHÔNG chèn ghi chú META/NỘI BỘ vào trang — trang phải đọc được như một tài liệu nghiệp vụ độc lập:** mọi câu nói về *cách tài liệu được sinh ra* (tên file spec trong workspace, version spec, role sinh ra nó, tên template đã bám theo, quy ước đánh version của skill) là thông tin vận hành của skill → thuộc **report + log**, TUYỆT ĐỐI không đưa lên trang. Người đọc là cán bộ nghiệp vụ, không truy cập được workspace spec và không cần biết quy trình nội bộ. Hai dạng đã lọt trong case thật (SCR-EMBED-PMT, pageId 199112222, 2026-08-07 — user chỉ ra "2 phần này không mô tả trọn tài liệu"):
- **info-macro mở đầu trang** kiểu "Kịch bản nghiệp vụ chi tiết (role BA) cho chức năng giao diện ... Theo Template Chức năng FE. Nguồn: tên file detailed design, phiên bản 1.5" → **BỎ HẲN cả macro**, không giữ lại dạng rút gọn. Trang bắt đầu thẳng bằng bảng ghi nhận thay đổi (hoặc mục 1 Mô tả chung theo template).
- **Câu chú thích in nghiêng dưới bảng ghi nhận thay đổi** kiểu "Cột Phiên bản là số phiên bản trang Confluence sau khi cập nhật, không đánh số riêng cho tài liệu" → **BỎ HẲN**. Quy ước đánh version là chuyện của skill, ghi trong reference này là đủ; đưa lên trang chỉ làm nhiễu người đọc.
- Nhu cầu truy vết nguồn spec ĐÃ được đáp ứng bằng cột **Nguồn gốc** trong chính bảng ghi nhận thay đổi — không cần nhắc lại ở bất kỳ chỗ nào khác trên trang.
- Rà soát trước mỗi lần publish: quét toàn bộ storage.xhtml, hễ gặp câu chứa tên file `.md`, chữ "detailed design", "template", "role BA/skill", "spec version", hay giải thích ý nghĩa cột của chính bảng đang hiển thị → xóa. Đây là quy ước **hồi tố** (theo nguyên tắc đã ghi ở mục xuống dòng tách ý): phát hiện 1 chỗ thì quét cả trang, kể cả các trang SRS đã publish trước đó khi có dịp đụng lại.

**Tô màu header mọi bảng — áp dụng THỐNG NHẤT, không phân biệt có trang gốc hay không:** dùng `<th data-highlight-colour="#DEEBFF">` (thay `<td><strong>` mặc định) cho MỌI hàng header của MỌI bảng trong SRS (chuẩn storage-format "Cell background colour", render đúng Server lẫn Cloud). Kể cả khi user chỉ định 1 trang Confluence làm "gốc"/"template chuẩn" mà trang đó đang dùng `<th>` trơn không tô màu → VẪN tô màu theo quy ước này, không cần bám theo trang gốc ở điểm trình bày header.

**Mọi ô mô tả (§1 Mục đích/Precondition/Post-condition, §2.x cột Mô tả chi tiết, §3.3 cột Mô tả chi tiết & Quy tắc xử lý, §4-§6) — xuống dòng tách ý, KHÔNG dồn nhiều ý vào 1 đoạn văn dài:** hễ 1 ô có ≥2 ý độc lập (≥2 điều kiện, ≥2 trường hợp, ≥2 hành động nối tiếp, danh sách liệt kê...) → BẮT BUỘC tách dòng, không viết thành 1 câu/đoạn nối bằng dấu phẩy hoặc chấm phẩy chạy dài. Chọn đúng cách tách theo bản chất nội dung:
- **Nhiều bước/ý tuần tự nhưng KHÔNG cần rẽ nhánh riêng** (vd 1 câu mô tả 3 API gọi đồng thời, hoặc nhiều điều kiện cộng dồn) → `<ul><li>...</li></ul>` (bullet không đánh số) trong storage-format, mỗi `<li>` 1 ý trọn vẹn.
- **Có thứ tự bắt buộc / đánh số tham chiếu được** (Precondition 1-2-3, Post-condition 1-2-3-4) → numbered text nội dòng `"1. ...<br/>2. ..."` (đúng phong cách gốc 200765940) hoặc `<ol><li>` nếu template không dùng numbered-inline.
- **Rẽ nhánh điều kiện (nếu X thì A, nếu Y thì B)** → `<ul><li><strong>Nếu X:</strong> A</li><li><strong>Nếu Y:</strong> B</li></ul>`, bôi đậm điều kiện để dễ quét mắt (đã áp dụng ở B4 case thật SCR-COMPOSITE-DETAIL, 2026-08-06).
- **⚠️ Không nhét "nếu X thì Y" vào GIỮA 1 bullet bằng dấu gạch ngang "—"** (vd `<li>Truy vấn ... theo id — không thấy dòng nào thì trả 404.</li>` là VẪN SAI dù đã ở trong `<ul>`, vì 1 `<li>` vẫn đang gánh 2 ý: hành động + điều kiện lỗi). Mọi bullet có dạng "làm X — nếu/không Y thì Z" phải tách thành 2 `<li>` riêng: 1 bullet hành động chính + 1 bullet `<strong>Nếu ...:</strong>` cho nhánh điều kiện/lỗi, đúng mẫu đã áp cho "Nếu thành công/Nếu lỗi" ở trên — áp dụng NHẤT QUÁN cho toàn bộ bullet trong `<ul>`, không chỉ bullet đầu/cuối. (Case thật SCR-COMPOSITE-DETAIL 2026-08-06: bullet mô tả Backend Hub xác thực/truy vấn/kiểm tra quyền ở B4 đều nhét điều kiện lỗi bằng "—" dù đã bullet hóa — vẫn bị user chê phải tách tiếp.)
- **Case thật đã sai (SCR-COMPOSITE-DETAIL v1, 2026-08-05):** mô tả B2 ban đầu viết dồn "Giao diện gọi đồng thời: chi tiết hồ sơ tổng + danh sách yêu cầu thành phần; nếu là Admin, gọi thêm lịch sử thao tác..." thành 1 câu — user phải yêu cầu tách bullet + nêu rõ "là gì" từng phần mới đạt yêu cầu. Bài học: PHẢI tự rà mọi ô mô tả TRƯỚC khi publish, đếm số ý độc lập trong ô — ≥2 ý là phải tách, không chờ user chỉ ra.
- Áp dụng cả cho nội dung trong `ac:structured-macro ac:name="expand"` (luồng nghiệp vụ chi tiết §3.4) — không viết văn xuôi liền mạch trong đó, ưu tiên bảng bước hoặc `<ul>`/`<ol>` tùy ngữ cảnh (xem quy ước bảng bước ngay trên).
- **Ngoại lệ — không cần bullet:** cột đã compact theo bản chất bảng (vd cột "Hướng xử lý & Phản hồi FE" trong bảng mã lỗi §5 — nhiều dòng, mỗi ô cố tình ngắn gọn 1-2 mệnh đề) thì để nguyên câu ngắn, KHÔNG ép bullet — bullet hóa mọi ô của 1 bảng dày đặc (10+ dòng) làm bảng phình to, phản tác dụng. Chỉ áp rule này cho các khối mô tả "prose" (§1 Mô tả chung, §2.x cột Mô tả chi tiết, §3.x mô tả bước/luồng, §4.2 mô tả tác động dữ liệu) — nơi 1 ô/đoạn thường gánh nhiều câu dài.
- **⚠️ Bài học quan trọng (SCR-COMPOSITE-DETAIL, 2026-08-06) — viết rule vào skill KHÔNG tự động sửa nội dung ĐÃ xuất bản trước đó:** lần đầu thêm rule này vào skill, tôi chỉ áp dụng cho nội dung MỚI viết thêm sau đó (B2, B4 ở §3.3) mà quên quét lại toàn bộ tài liệu đã có từ trước (§1 Mục đích/Đối tượng sử dụng/Đường dẫn chức năng, §2.1.2 huy hiệu trạng thái, §2.4 intro, §4.2 bảng thực thể — tất cả đều đang dồn 2-5 ý vào 1 đoạn văn/1 câu dài mà không ai phát hiện tới khi user hỏi lại). **Quy tắc bắt buộc từ nay: mỗi khi thêm 1 convention MỚI vào skill (bất kỳ convention nào, không riêng bullet), phải NGAY LẬP TỨC quét lại toàn bộ file storage.xhtml đang có (đọc hết, không đọc lướt) đối chiếu với convention mới — sửa hết chỗ vi phạm cũ rồi mới coi là xong, không chỉ áp dụng cho phần viết thêm về sau.** Ghi convention vào skill mà không hồi tố lại = nửa vời, user sẽ phải chỉ ra lần 2.

**Header cột "Mô tả chi tiết" ở bảng control §2.x — KHÔNG thêm đuôi "& Quy tắc nghiệp vụ":** control table (§2.1-2.6) mô tả 1 phần tử UI tĩnh (button/badge/field/panel), không phải 1 bước xử lý có "quy tắc nghiệp vụ" riêng → header chỉ để **"Mô tả chi tiết"**. Đuôi "& Quy tắc xử lý"/"& Quy tắc nghiệp vụ" CHỈ giữ cho bảng bước §3.3/§3.4/entity §4.2 — nơi mỗi dòng đúng là 1 bước xử lý có rule/điều kiện thật (case thật SCR-COMPOSITE-DETAIL, 2026-08-07: user chỉ ra header control-table "Mô tả chi tiết & Quy tắc nghiệp vụ" là thừa/sai chỗ).

**Cột "Giá trị mặc định" — CHỈ điền khi control là input thật có default value, còn lại → N/A (nhất quán với cột Require/Maxlength):** không tự chế ra giá trị cho control không có khái niệm "mặc định":
- **Button** (mọi loại — primary/secondary/icon-button, kể cả disabled/ẩn-hiện theo điều kiện) → LUÔN **N/A**. "enabled"/"ẩn/hiện theo điều kiện" không phải "giá trị mặc định" — đó là hành vi runtime, đã mô tả đủ ở cột Mô tả, nhắc lại ở đây là thừa/gây hiểu lầm (case thật, 2026-08-07: user chỉ ra "button không có giá trị mặc định để N/A chứ").
- **Badge/banner/table/panel/display-only** (không nhận input) → **N/A**. Nếu có 1 thông tin đáng giữ (vd banner mặc định ẩn, danh sách giới hạn 50 bản ghi) thì DỜI câu đó sang cột Mô tả, KHÔNG để lại "—" hay câu mô tả trong cột Giá trị mặc định.
- **Input control thật** (textarea, dropdown, date-picker, tab mặc định chọn, checkbox-list mặc định không chọn gì) → giữ giá trị mặc định thật (`""`, `"Tất cả loại sự kiện"`, tab mặc định, "không chọn gì"...).
- **KHÔNG dùng "—"** cho cột này ở bất kỳ trường hợp nào — chỉ 2 dạng hợp lệ: giá trị thật hoặc `N/A`.

**KHÔNG dùng ký hiệu "§" khi tham chiếu số mục trong văn xuôi SRS (Mô tả/Ghi chú/info-macro/note) — viết "mục X.Y" hoặc thẳng số "X.Y":** case thật (2026-08-07): user chỉ ra "§3.4 là cái gì, 3.4 thôi chứ" — "§" là ký hiệu văn bản luật/quy chuẩn, không tự nhiên với văn phong SRS đang dùng. Áp dụng cho MỌI cross-reference dạng "xem §X", "→ §Y", kể cả trong heading nếu heading có ghi kèm — thay bằng "xem mục X.Y" hoặc "→ mục X.Y" (heading tự thân đã là số thuần "3.4 Luồng nghiệp vụ...", không cần đổi). Đây là quy ước hồi tố — khi user chỉ ra 1 chỗ dùng "§" là sai thì phải quét TOÀN BỘ tài liệu thay hết, không chỉ sửa đúng chỗ được chỉ ra (áp dụng cùng nguyên tắc "viết rule không tự hồi tố" đã ghi ở trên).

**Mapping Nhãn ↔ trường dữ liệu — bảng lồng BẮT BUỘC ở CẢ HAI vị trí: §2.x control table VÀ §3.3/§2.2 bảng bước.** Quy tắc chung, không phụ thuộc vị trí: **hễ 1 ô Mô tả nhắc tới ≥2 field dữ liệu thì ô đó phải nhúng 1 bảng con, KHÔNG liệt kê bằng câu văn.** Tên bảng/cột/trường lấy từ **code thật** (entity / type định nghĩa cột / response DTO — như quy ước Fidelity ở trên), KHÔNG bịa/dịch.

| Vị trí | Loại ô cần bảng lồng | Bảng lồng 3 cột (điển hình) |
|:---|:---|:---|
| **§2.x control table** | Control hiển thị ≥2 field (bảng dữ liệu, thẻ thông tin, danh sách…) | `Nhãn cột trên giao diện \| Trường dữ liệu nguồn \| Mô tả` |
| **§3.3 bước HIỂN THỊ** | Bước "Hiển thị biểu mẫu / bảng / khu vực kết quả …" liệt kê ≥2 field | `Nhãn trên giao diện \| Giá trị khi mở màn \| Mô tả`; bảng kết quả nhiều nhóm → thêm cột nhóm dùng `rowspan` (`Bảng kết quả \| Nhãn cột \| Trường dữ liệu nguồn`) |
| **§3.3 bước NHẬP** | Bước "Người dùng nhập A và B …" (kể cả ô lọc) | `Nhãn trên giao diện \| Bắt buộc \| Ràng buộc giá trị` |
| **§3.3 bước GHI** | Bước tạo/cập nhật/ghi nhật ký bản ghi (mỗi bảng bị ghi = 1 bảng lồng riêng, kể cả bảng audit) | `Trường nghiệp vụ \| Cột trong CSDL \| Giá trị ghi vào` (xem `confluence-server-publish.md` §4 điểm 4, mục "Bước ghi DB") |
| **§4.2 bảng thực thể** | Ô Mô tả của mỗi entity do hệ thống own | `Cột trong CSDL \| Ý nghĩa` — liệt kê cột, KHÔNG viết prose "gồm mã hồ sơ, tên, mô tả…" |

**🔴 Tên trường thuần Việt KHÔNG BAO GIỜ đứng một mình — luôn kèm tên bảng + tên cột THẬT trong CSDL:** bảng lồng chỉ có `Trường | Giá trị ghi vào` (hoặc `Trường | Ý nghĩa`) là **CHƯA ĐẠT** — người đọc không biết dữ liệu nằm ở bảng/cột nào để tra. Bắt buộc:
- **Tên bảng ghi dạng schema-qualified** (`bms_hub.composite_requests`), nêu ngay ở câu dẫn trước bảng lồng ("Giá trị ghi vào bảng `<schema>.<table>`:") và ở cột "Bảng/thực thể liên quan" của bảng bước — không để trần tên bảng thiếu schema. Schema lấy từ migration SQL / javadoc entity / `V*__create_*.sql`, KHÔNG suy đoán.
- **Mỗi dòng có đúng 1 cột DB** — không gộp kiểu "Người tạo và thời điểm tạo", "Mã đối tác và mã sản phẩm"; tách thành các dòng riêng để cột `Cột trong CSDL` map 1-1.
- **Giá trị enum/hằng ghi nguyên văn giá trị lưu xuống** (`InProgress`, `COMPOSITE_CREATED`, `WEB_UI`, `version` = 0, `created_by_partner` = false) — không chỉ dịch nghĩa tiếng Việt. Lấy từ converter/enum thật, không đoán từ tên Java.
- **Nêu tên ràng buộc/khoá thật khi có** (`uk_subsystem_subid` trên cặp `sub_system` + `sub_id`) thay vì chỉ nói "ràng buộc duy nhất theo cặp phân hệ và mã yêu cầu".
- **Màn/luồng KHÔNG own DB** (dữ liệu từ API phân hệ khác) — **KHÔNG được dừng ở tên field API.** Bảng lồng thêm cột thứ 3 **"Bảng và cột gốc trong CSDL"**, điền theo thứ tự ưu tiên sau:
  1. **Repo phân hệ nguồn CÓ trong workspace (multi-root / additional working directories) → BẮT BUỘC truy tới bảng gốc**, không được ghi chung chung. Cách truy (mất ~5 phút, luôn làm được): lấy **base-url + path** của leg từ `application.yml`/`.properties` của service gọi → grep path đó trong repo phân hệ nguồn để ra **controller** → **service impl** → **mapper** (chỗ này cho biết field API lấy từ property nào của entity, kể cả field nối bảng kiểu `merchantTmp.code`) → **entity** (`@Table` + `@Column`, thường qua hằng `TABLE_NAME`/`COLUMN_*`) → **schema** lấy từ `jdbc:` URL trong config. Ghi ra dạng `<table>.<column>` + 1 bullet nêu lược đồ, bảng chính và các cột nối (`@JoinColumn`).
  2. **Repo KHÔNG có sẵn → ghi tên dịch vụ sở hữu + giao diện gom dữ liệu thật** (vd "Thuộc dịch vụ `product-catalog-cms-be`; HUB-01 gom qua `/private/hubint/pending-requests`") — lấy từ config base-url/path, dùng `rowspan` cho cả nhóm. Chỉ khi đó mới được nói "tên bảng và cột gốc do tài liệu phân hệ đó mô tả".
  - Tuyệt đối KHÔNG bịa tên bảng của hệ thống khác để lấp cột, và cũng KHÔNG được dùng câu "bảng gốc thuộc tài liệu `<FEATURE-ID>`" như cách thoát khi repo nguồn đang nằm ngay trong workspace.
  - Nhân đây kiểm luôn **trạng thái thật của từng leg** trong config (vd `enabled-systems`, cờ mock): leg đang chạy dữ liệu mẫu là thông tin nghiệp vụ người đọc cần biết → ghi 1 bullet, đừng mô tả như đã nối thật.

Bước hiển thị ở §3.3 KHÔNG được thay bảng lồng bằng dòng tham chiếu kiểu *"Cấu trúc cột từng bảng nêu ở control số 9 đến 11 mục 2.1"* — cross-reference chỉ được dùng để trỏ **mô tả chi tiết/ràng buộc**, còn bản thân mapping nhãn ↔ trường phải đọc được ngay tại bước. Lặp lại mapping ở 2 chỗ (§2.1 và §3.3) là **có chủ đích**, không tính là trùng lặp: §2.1 đọc theo control, §3.3 đọc theo luồng.

Cột thứ 2 đổi theo **nguồn dữ liệu thật của màn hình** — đây là chỗ dễ hiểu sai nhất, xem đúng 2 biến thể:

| Màn hình | Bảng lồng 3 cột | Khi nào |
|:---|:---|:---|
| **Đọc thẳng CSDL** (màn có DB của chính hệ thống) | `Nhãn trên giao diện \| Bảng DB tương ứng \| Trường DB tương ứng & Mô tả` | Tên bảng/cột lấy từ `@Entity`/`@Table`/`@Column` hoặc migration SQL. Đã áp dụng SCR-COMPOSITE-DETAIL §2.1.2 dòng 6. |
| **FE consumer, KHÔNG own DB** (render field từ response API) | `Nhãn cột trên giao diện \| Trường dữ liệu nguồn (API nào trả về) \| Bảng và cột gốc trong CSDL \| Mô tả` | Tên trường lấy từ type/DTO FE thật (vd hằng định nghĩa cột bảng). **Cột 3 bắt buộc** — truy tới bảng gốc nếu repo phân hệ nguồn có trong workspace, nếu không thì ghi dịch vụ sở hữu + endpoint (xem 2 bước ưu tiên ở trên). Đã áp dụng SCR-COMPOSE §2.1 control 9/10/11 + B16. |

⚠️ **Bài học (SCR-COMPOSE, 2026-08-07 — user phải chỉ ra):** bản v11–v13 để 3 control bảng kết quả ở dạng prose `"Cột: Mã đối tác · Tên đối tác · Tên dịch vụ · Người tạo · Thời gian tạo."` đúng kiểu rule cấm, trong khi bảng lồng thì lại chỉ xuất hiện ở bước ghi dữ liệu §3.3. **Nguyên nhân là lỗ hổng của rule, không phải người viết bỏ qua rule:** rule cũ chỉ nói "field đọc thẳng từ **CSDL**" + cột 2 là "**Bảng DB** tương ứng", nên với màn FE consumer (không own DB, không có bảng nào để điền vào cột 2) thì rule đọc như **không áp dụng** → rơi về prose. Từ nay: **trigger là "control hiển thị ≥2 field", KHÔNG phụ thuộc nguồn là DB hay API**; không có bảng DB thì điền trường của response API, tuyệt đối không hạ xuống prose.
⚠️ **Bài học lần 2 (SCR-COMPOSE, 2026-08-07 — user lại phải chỉ ra):** ngay sau khi sửa xong 3 control §2.1, §3.3 vẫn còn nguyên các bước hiển thị/nhập viết prose (B2 *"Hiển thị biểu mẫu gồm tên hồ sơ, mô tả và hai ô lọc…"*, B3, B6, và B16 chỉ trỏ *"cấu trúc cột nêu ở control 9 đến 11 mục 2.1"*), trong khi bảng lồng ở §3.3 lại chỉ có ở **bước ghi** B22. **Nguyên nhân lại là lỗ hổng phạm vi của rule:** rule cũ neo vào **vị trí** (`§2.x control`) và ở §3.3 chỉ nói tới **"bước ghi DB"** ⇒ bước *hiển thị*/*nhập* ở §3.3 không thuộc nhánh nào của rule → rơi về prose. Từ nay rule neo vào **bản chất ô** (ô nhắc ≥2 field) áp cho **cả 3 loại bước** (hiển thị / nhập / ghi) ở mọi vị trí.
- Hai lần liên tiếp cùng một dạng lỗi ⇒ khi sửa 1 vi phạm mapping field, **BẮT BUỘC quét cả tài liệu ở mọi mục có bảng** (§2.x, §3.3, §3.4, §4.2), không sửa xong đúng mục user chỉ rồi dừng.
⚠️ **Bài học lần 3 (SCR-COMPOSE, 2026-08-07 — user chỉ ra lần thứ ba):** *"phần mô tả này đang chỉ mô tả tên trường, ý nghĩa, chưa rõ bảng lưu db có tên gì"*. Sau khi đã có đủ bảng lồng ở cả §2.1 và §3.3, các bảng lồng của **bước ghi** vẫn chỉ có `Trường | Giá trị ghi vào` với tên trường **thuần Việt** ("Mã hồ sơ", "Người tạo và thời điểm tạo") — không có cột nào cho tên cột DB, tên bảng thì để trần thiếu schema, và §4.2 vẫn mô tả cấu trúc bảng bằng prose. **Nguyên nhân:** rule chỉ yêu cầu *"tên bảng/cột lấy từ code thật, không bịa"* nhưng KHÔNG yêu cầu **phải xuất hiện** tên bảng/cột trong bảng lồng ⇒ bảng lồng đúng hình thức mà vẫn không tra được về DB. Từ nay áp mục "Tên trường thuần Việt không bao giờ đứng một mình" ở trên như điều kiện xuất bản.
- **Tự kiểm trước khi publish (áp cho MỌI bảng, không riêng control table):** quét mọi ô Mô tả, hễ gặp mẫu `"Cột: A · B · C"` / `"gồm các trường X, Y, Z"` / `"Hiển thị … gồm A, B và C"` / `"Nhập A và B"` / dòng tham chiếu `"cấu trúc cột nêu ở …"` / liệt kê ≥2 tên field trong một câu → phải chuyển thành bảng lồng.
⚠️ **Bài học lần 4 (SCR-COMPOSE, 2026-08-07 — user rà lại và chỉ ra tiếp):** sau khi vá xong lần 3, **3 bảng kết quả ở §2.1 (control 9/10/11) và bảng lồng B16 vẫn không có tên bảng/cột DB nào** — chỉ có field API + câu "bảng và cột gốc ở phân hệ nguồn thuộc tài liệu HUB-01". **Nguyên nhân KHÔNG phải rule sai mà là do người viết dừng quá sớm:** rule cho phép "không own DB thì trỏ sang tài liệu feature BE", và tôi coi đó là đủ — trong khi **repo phân hệ nguồn (`merchant-profile-service`) đang nằm ngay trong workspace multi-root**, chỉ cần đi 4 bước config → controller → mapper → entity là ra `merchant_profile_service.merchant_service_tmp` + `merchant_tmp.code` / `service.name`. Câu "thuộc tài liệu HUB-01" biến thành **đường thoát hợp lệ hoá việc không tra**. Từ nay: rule bắt buộc thử bước 1 (truy repo trong workspace) TRƯỚC, chỉ rơi xuống bước 2 khi repo thật sự không có.
- **Nhắc lại nguyên tắc hồi tố:** lần 3 đã sửa bảng lồng ở §3.3/§4.2 mà không quét §2.1 — đúng lỗi "viết rule không hồi tố" đã ghi ở trên, lặp lại lần thứ hai. Khi bổ sung 1 loại thông tin (vd tên cột DB), phải quét **mọi bảng lồng trong tài liệu**, kể cả bảng vừa tạo ở vòng trước.
- **Tự kiểm bổ sung (lần 3):** quét mọi bảng lồng đã có — nếu bảng nào **không có cột nào chứa tên cột DB thật** (hoặc tên field API thật với màn không own DB), hoặc câu dẫn trước bảng **không nêu tên bảng schema-qualified**, thì bảng đó chưa đạt. Grep nhanh: tên cột DB thường ở dạng `snake_case` trong `<code>` — bảng lồng của bước ghi/entity mà không có `<code>` nào là dấu hiệu vi phạm.

**§3.3/§2.2 bảng bước — mô tả luồng truy vấn/ghi CSDL khi user cần xem (áp dụng cả template FE lẫn API):** mô tả bằng lời, tên bảng/cột DB **thật** lấy từ entity code (`@Entity`/`@Table`/`@Column` Java, hoặc migration SQL) — KHÔNG bịa/dịch sang tiếng Việt, KHÔNG viết SQL. Chọn 1 trong 2 vị trí đặt nội dung này tuỳ theo có trang gốc chỉ định hay không:
- **Không có trang gốc chỉ định (mặc định):** thêm 1 cột riêng "Luồng CSDL" ngay trong bảng bước §3.3/§2.2 (hoặc dòng riêng trong ô Ghi chú nếu template không cho thêm cột).
- **Có trang gốc chỉ định và trang đó gộp chi tiết CSDL vào bảng thực thể riêng (case 200765940, §4.2 "Bảng tác động dữ liệu"):** dồn hết chi tiết điều kiện CSDL vào cột Mô tả của bảng thực thể §4.2, KHÔNG tách cột riêng ở §3.3 — giữ bảng bước gọn theo đúng gốc, mọi query/update detail nằm ở đúng 1 chỗ (§4.2) tránh lặp 2 nơi.

**HTML tương tác — wire ĐỦ mọi modal/popup:** khi file HTML mô phỏng cho tải về (interactive), phải liệt kê MỌI `ng-template`/modal trong component thật và nối MỌI nút mở popup (`onShowModal`, `open*.emit()`, ...) tới đúng modal của nó. Nút bấm không hiện popup = mock lỗi. Mỗi modal dựng đủ trường + nhãn i18n như code; test bằng cách bấm từng nút (hoặc chụp từng modal ở trạng thái mở) trước khi publish.

Lấy nội dung trong `<body>...</body>` của `p_screen.html`, bọc vào macro:

```xml
<ac:structured-macro ac:name="html">
  <ac:plain-text-body><![CDATA[
  <!-- nội dung <body> của p_screen.html, inline CSS -->
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

**Fallback** (HTML macro bị admin chặn → update/create lỗi macro, hoặc user báo trắng — server `.35` TẮT HTML macro): upload `p_screen.html` làm attachment **qua REST script `scripts/confluence-publish.ps1`** (MCP `confluence_upload_attachment` FAIL trên Confluence Server — xem `confluence-server-publish.md` §0) + chèn link "📎 Tải HTML màn hình" + (nếu render được) ảnh screenshot inline. Ghi rõ fallback trong report + log.

## Map changelog spec → SRS

Cấu trúc 1 dòng bảng "LỊCH SỬ THAY ĐỔI"/"Bảng ghi nhận thay đổi tài liệu": Ngày · Vị trí · Loại (A khi tạo mới / M khi update / D khi xóa) · Nguồn gốc (spec version DD+story) · Mô tả (tóm tắt delta) · Phiên bản (số version trang Confluence sau khi cập nhật). Giữ nguyên dòng cũ, dòng mới thêm lên đầu.

Mỗi lần publish có thay đổi nội dung nghiệp vụ → thêm 1 dòng tương ứng.

### KHÔNG thêm dòng khi publish chỉ là sửa cách trình bày

Bảng ghi nhận thay đổi chỉ ghi **thay đổi nghiệp vụ** — thứ làm người đọc phải đọc lại và làm QA phải test lại. Publish thuộc các loại dưới đây **KHÔNG được thêm dòng**, chỉ ghi vào `versionMessage` + log sync:

- Chuẩn hóa thuật ngữ theo `terminology.md` (đổi cách gọi, nghiệp vụ y nguyên).
- Làm rõ / chi tiết hóa mô tả sẵn có (vd bước ghi dữ liệu từ mô tả chung chung → bảng lồng đủ bảng + cột + giá trị), khi hành vi hệ thống không đổi.
- Sửa lỗi chính tả, format, bố cục, vẽ lại sơ đồ mà luồng không đổi, sửa lỗi tự gây ở lần publish trước.

> **Bài học 2026-08-11 (HUB-01 v13 / HUB-02 v8):** tôi thêm 1 dòng "Chuẩn hóa thuật ngữ..." vào bảng cho đợt rà soát chữ nghĩa; user bác — *"việc điều chỉnh này k tạo thành 1 thay đổi ở bảng ghi nhận thay đổi"*. Phải gỡ dòng rồi publish lại. Hệ quả bình thường và chấp nhận được: version trang Confluence chạy tiếp (12→13) trong khi dòng mới nhất của bảng vẫn dừng ở version cũ (11) — cột phiên bản ghi version **tại thời điểm thay đổi nghiệp vụ đó**, không phải version hiện hành của trang.

Không chắc thuộc loại nào → hỏi user trước khi thêm dòng, đừng mặc định thêm.
