# Resolve Confluence: host, trang cha, template, publish

---

## 0. Hai host là hai instance riêng

`10.254.136.32` (space `TTCN24`, MCP `mcp__atlassian32__*`) và `10.254.136.35` (space `TDOV`, MCP `mcp__atlassian__*`) là **hai Confluence khác nhau** — cùng một trang có pageId khác nhau ở hai bên, và pageId của bên này mở trên bên kia sẽ không ra (đã kiểm 2026-08-17 với `88716677`).

Vì vậy:
- **Điểm vào cố định là `.32` pageId `88716677`** (index các dự án). Luôn bắt đầu từ đây.
- **Host đích không được giả định trước.** Trang dự án trong index có thể là child page của `.32`, cũng có thể chỉ là một **link** trỏ sang `.35`. Host của trang cha tìm được chính là host sẽ ghi.
- Không tìm chéo: đã xác định host đích rồi thì mọi thao tác đọc/ghi trang đợt đi đúng MCP của host đó.

**Đọc `.32` khi MCP `.32` chết (403 token hết hạn, tình trạng từ 2026-07):** resolve `confluence-get.ps1` của skill SRS bằng Glob rồi chạy:

```bash
powershell -ExecutionPolicy Bypass -File "<path>/confluence-get.ps1" -PageId 88716677
```

Exit khác 0 (chưa cấu hình credential, hoặc HTTP lỗi) → DỪNG, báo người dùng cấu hình `.confluence-auth`, không tự đi đường khác.

## 1. Dò từ index tới nhánh KBNT

**Resolve một lần rồi cache.** Nhánh KBNT của một dự án gần như không đổi. Dò được thì ghi `{kbnt_root}/kbnt-branch.json` (host, `space_key`, `parent_id`, tên nhánh, convention tiêu đề đọc từ các trang con) và lần sau dùng luôn. File này thuộc **dự án**, không thuộc skill — pageId tuyệt đối không được nằm trong file skill.

### 1a. Hai cạm bẫy của `confluence_search`

- **CQL `title ~ "..."` xếp theo relevance rồi cắt theo `limit`, không xếp theo cây.** Nhánh đúng có thể nằm ngoài 30 kết quả đầu trong khi các trang con của nó thì nằm trong. Đã dính thật: `title ~ "KBNT"` trong space đúng vẫn **không** trả về nhánh `9.2.4 KBNT`, chỉ trả các trang con và các trang KBNT của dự án khác cùng space. → CQL chỉ dùng để **bổ sung**, kết luận "không có nhánh KBNT" phải dựa trên **duyệt children**.
- **Một space chứa nhiều dự án.** Trang tên rất giống nhau (`13.06. KBNT` vs `9.2.4 KBNT`) thuộc hai dự án khác hẳn. Luôn verify bằng `ancestors` xem trang có nằm dưới node dự án `{target_system_name}` không, đừng tin cái tên.

### 1b. Đường phụ khi index `.32` chết cả hai lối

MCP `.32` hết token (403) **và** `{auth_file}` không có block `CONFLUENCE_32_*` là tình huống thật, không phải giả định. Khi đó vẫn resolve được mà không cần đoán:

1. Lấy một pageId **đã biết chắc thuộc dự án** — trang template KBNT, hoặc link `Confluence SRS:` trong header một DP bất kỳ của dự án.
2. Trên host đích, `GET /rest/api/content/{id}?expand=ancestors` → được cả đường từ gốc space xuống, trong đó có node dự án.
3. Từ node dự án duyệt children xuống nhánh KBNT.
4. **Gọi REST bằng PowerShell `Invoke-RestMethod`.** `curl` của Git Bash đi qua proxy hệ thống và trả `403` HTML của Squid — nhìn giống hết hạn token nên rất dễ chẩn sai.
5. Nhánh KBNT hay nằm dưới **tài liệu yêu cầu/thiết kế**, không nằm dưới nhánh **Test** (nhánh Test thường chỉ có KBKT + test plan + report). Đừng suy "có chữ Test thì KBNT ở đó".

### 1c. Thủ tục gốc (khi index còn sống)

1. Đọc index `.32` `88716677`:
   - `confluence_get_page_children(parent_id=88716677, include_folders=true, limit=50)`, phân trang tới hết.
   - Fallback: `get_page(page_id=88716677, convert_to_markdown=true)` rồi trích link trong body — một số dự án chỉ là link, không phải child page.
2. Tìm dự án `{target_system_name}` (mặc định *Đối soát tập trung*). Không chắc hoặc nhiều ứng viên → **AskUserQuestion** liệt kê.
3. Mở trang dự án theo đúng host của link. Từ đó dò xuống nhánh quản lý KBNT:
   - Duyệt children nhiều tầng, hoặc `confluence_search` CQL `ancestor = <id trang dự án> AND (title ~ "nghiệm thu" OR title ~ "KBNT")`.
   - Không thấy → **DỪNG hỏi người dùng chỉ nhánh**. Không tự tạo nhánh mới.
4. Ghi nhớ `{parent_id}`, `{space_key}`, host — lưu vào `{dot_dir}/page-ref.json` để lần sau khỏi dò lại.

## 2. Template

- Tìm theo tiêu đề, không hardcode pageId: `confluence_search` CQL `space = TDOV AND title = "Template KBNT"` trên host `.35`.
- `get_page(page_id, convert_to_markdown=false)` → parse thứ tự mục, tên mục, và **bộ cột của bảng case**.
- Template nằm ở `.35` kể cả khi host đích là `.32` — đây là ngoại lệ đọc chéo duy nhất được phép, vì template chỉ cung cấp **khung**, không quyết định nơi ghi. Ghi rõ điều này ở preview.
- Lưu khung parse được vào `{dot_dir}/template-snapshot.md`. Lần chạy sau, khung mới khác khung cũ → cảnh báo ở gate 2 (template đã đổi, các trang đợt cũ vẫn giữ khung cũ).

## 3. Storage format

Theo `storage-format.md` của skill `NTAPP-dd-to-confluence` (resolve bằng Glob). Điểm cần nhớ cho KBNT:

- Escape `&`, `<`, `>` ngoài CDATA.
- Xuống dòng trong ô bảng dùng `<br/>`, không dùng ký tự xuống dòng thật.

### 3a. CẤM copy nguyên byte header của template — tự viết lại

Hai lý do, đều đã làm vỡ trang thật (2026-08-18, `KBNT - Bàn giao tháng 8` v1):

- **Double-encode.** `Invoke-RestMethod` của PowerShell 5.1 decode response **Latin-1** khi Confluence không khai `charset` trong `Content-Type`. Lưu lại là UTF-8 của chuỗi đã sai → header hiện `Mô táº£ trÆ°á»ng há»£p` trên trang, trong khi body (build từ markdown local) vẫn đúng. Dấu hiệu chẩn đoán: **chỉ phần copy từ Confluence bị lỗi font, phần tự sinh thì không**. Nếu buộc phải đọc storage để phân tích thì lấy bytes rồi decode UTF-8 tường minh, đừng tin chuỗi PowerShell trả về.
- **Template có thể tự sai.** Template KBNT lệch một ô ở hàng header 2 (span 5, đúng phải 4) và hàng 3 (span 11, đúng phải 10). Copy byte là bê luôn lỗi, và Confluence render lệch cột. Tự viết header theo **bảng cột trong `template-snapshot.md`** thì vừa đúng chính tả vừa đúng lưới.

**Validator phải kiểm CẢ hàng header,** không chỉ hàng case: tổng `colspan` của hàng 1 = số cột; hàng 2 và 3 chỉ đếm phần **không** bị `rowspan` của hàng 1 phủ. Bỏ hàng header khỏi vòng kiểm là đúng cách để lỗi này lọt.

### 3b. Bullet hóa nội dung ô — bắt buộc, theo rule đã chốt ở skill SRS

Người dùng đã chốt hai lần ở `NTAPP-srs-to-confluence`: *"cần trình bày xuống dòng từng ý, có gạch đầu dòng rõ ràng, k viết chung 1 dòng gây khó nhìn"*. Bảng KBNT dùng **cùng** ngưỡng đó — nguồn: `**/NTAPP-srs-to-confluence/references/confluence-server-publish.md` và `srs-mapping.md`.

| Cột | Cách trình bày |
|:---|:---|
| Mã case (`STT`) | text thuần |
| `Mô tả trường hợp` | thường một câu → để nguyên; ≥ 2 câu **và** ≥ 80 ký tự → `<ul><li>` |
| `Điều kiện` | `<ul><li>`, mỗi vế `<br>` gốc một `<li>`; vế mở đầu bằng nhãn (`Dữ liệu:`) → `<li><strong>Dữ liệu:</strong> …` |
| `Các bước thực hiện` | **`<ol><li>`** (có thứ tự), **bỏ tiền tố `1.` `2.`** vì `<ol>` tự đánh số |
| `Kết quả mong muốn` | `<ul><li><strong>Giao diện:</strong> …` — mỗi tầng hệ quả một `<li>` |
| `Ghi chú` | như `Điều kiện` |
| 10 ô kết quả | luôn `<br />` rỗng |

Ngưỡng máy móc khỏi tranh luận: **≥ 2 câu VÀ ≥ 80 ký tự → bullet**; ô một câu hoặc ngắn thì để nguyên. Tách câu theo dấu chấm **và dấu chấm phẩy** — `;` trong tiếng Việt ngăn hai vế, và **một `<li>` không được gánh hai ý**. Vế còn ≥ 2 câu sau khi tách nhãn thì lồng `<ul>` cấp 2.

Thêm `<colgroup>` đặt bề rộng từng cột. Không có nó, Confluence auto-size theo nội dung: cột `Mô tả trường hợp` bị bóp thành một chữ mỗi dòng khi các cột khác dài hơn.
- Checkbox chọn được dùng `ac:task-list` với `ac:task-id` duy nhất toàn trang, không dùng ký tự ô vuông unicode.
- Ngày dùng date macro `<time datetime="YYYY-MM-DD"/>` để ra chip lịch.
- **Link sang trang Confluence khác dùng page-link theo tiêu đề**, không dùng `<a href>`: `<ac:link><ri:page ri:content-title="Tiêu đề trang" /></ac:link>` — Confluence tự render tên trang và tự theo khi trang bị di chuyển. Cùng space thì không cần `ri:space-key`. Tiêu đề phải **khớp tuyệt đối** (lấy từ `get_page_children` của nhánh thật, đừng gõ lại tay) và phải escape XML; sai một ký tự là ra link đỏ. Thẻ `<a href>` với URL `pageId` vẫn mở được nhưng hiện URL thô và chết khi đổi host.
- **Không thêm mục ngoài template.** Cần chỗ ghi thứ template không có thì nêu ở gate 2 để người dùng quyết.

## 4. Publish

**Tiêu đề trang theo convention của nhánh, không theo khuôn skill.** Đọc tên các trang con hiện có trước khi đặt tên. Nhánh đã dùng `KBNT - <nội dung đợt>` thì theo dạng đó; chỉ nhánh rỗng mới dùng mặc định `KBNT — {YYYY-MM} — {tên đợt}`.

- Mặc định đi MCP, body-only (KBNT không có attachment):
  - CREATE: `confluence_create_page(space_key, title, content, parent_id, content_format="storage")`.
  - UPDATE: `confluence_update_page(page_id, title, content, content_format="storage", is_minor_edit=false, version_comment="KBNT {tên đợt} — sync {ngày}")`.
- Body lớn (khoảng trên 150KB — đợt nhiều case) làm MCP cắt output → đi REST. **UPDATE:** resolve `confluence-publish.ps1` của skill SRS bằng Glob, soạn manifest (pageId, baseUrl, title, storageFile, versionMessage, attachments rỗng), agent tự chạy. **CREATE:** script đó chỉ PUT trang đã có, nên phải tự `POST {base}/rest/api/content` với body JSON `{type:"page", title, space:{key}, ancestors:[{id}], body:{storage:{value, representation:"storage"}}}` — gửi bằng `Invoke-RestMethod` với bytes UTF-8, header `Authorization: Bearer <PAT>`.
- Sau khi ghi, `get_page` lại và **đếm số hàng `<tr>`**: phải bằng `số hàng header + số mục + số case`. Kích thước byte trả về **to hơn bản gửi lên là bình thường** (Confluence tự re-encode ký tự thành entity), đừng coi đó là dấu hiệu lỗi. Thiếu `.confluence-auth` hoặc PAT còn placeholder → DỪNG hỏi người dùng, không publish một nửa.
- Lỗi 401/403/404/409/timeout → DỪNG, báo nguyên nhân, **không retry sang host khác**. 409 nghĩa là version đã đổi — quay lại bước merge, không ép ghi.
