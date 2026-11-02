# Confluence — đọc & xuất bản (cơ chế MCP + REST, bài học thực chiến)

> Áp cho Confluence **Server** nội bộ (vd host `.35` space `TDOV`). Tài liệu Tổng quan nghiệp vụ
> có draw.io → **phải** dùng đường REST cho attachment (xem §0). Đọc khi tới BƯỚC 4/6/7.

## 0. Vàng: đọc/tạo qua MCP — nhưng attachment & body-có-sơ-đồ đi REST

| Việc | Kênh | Ghi chú |
|---|---|---|
| Đọc trang (template, index, bảng tổng hợp) | **MCP** `confluence_get_page(convert_to_markdown=false)` | Lấy storage XHTML thô để parse heading/macro. Nếu host MCP chết (403 token) → fallback `scripts/confluence-get.ps1` (Basic auth). |
| Tìm trang / dò macro | **MCP** `confluence_search` (CQL) | `macro="drawio"` … (xem §5). |
| Tạo trang mới (skeleton) | **MCP** `confluence_create_page(content_format="storage")` | Lấy `pageId` để bước sau upload attachment + PUT body. `create_page` KHÔNG nhận `version_comment`. |
| Cập nhật body **không có** attachment (trang nhỏ) | **MCP** `confluence_update_page(content_format="storage")` | Nhanh, atomic đủ. `update_page` CÓ `version_comment`. |
| **Upload attachment (draw.io mxfile / PNG / file tải về)** | **REST** `scripts/confluence-publish.ps1` | 🔴 MCP `confluence_upload_attachment` **LUÔN FAIL** trên Server này (`success:false`), kể cả trang nhỏ. |
| Cập nhật body **có** draw.io/ảnh, hoặc trang **mature lớn** (>~150KB) | **REST** `scripts/confluence-publish.ps1` | Upload attachment + PUT body **atomic** (trang không kẹt macro rỗng). Trang mature lớn: MCP cắt output → buộc REST. |

**Nguyên tắc:** tài liệu Tổng quan nghiệp vụ luôn có ≥1 sơ đồ draw.io ⇒ vòng publish mặc định là
**MCP create skeleton → sinh mxfile → `confluence-publish.ps1` (upload + body + auto-sync revision)**.

## 1. Auth cho REST (agent tự chạy, user không gõ lệnh)

`confluence-publish.ps1` / `confluence-get.ps1` đọc token từ **`.confluence-auth`** (dotenv, **gitignored**, ở repo root — walk-up tự tìm):

```
CONFLUENCE_BASE_URL=http://10.254.136.35:8090
CONFLUENCE_PAT=<Personal Access Token>
# (tuỳ chọn) host đọc-fallback khác:
CONFLUENCE_32_BASE_URL=http://10.254.136.32:8090
CONFLUENCE_32_USER=<user>
CONFLUENCE_32_PASS=<pass>
```

Setup 1 lần: copy `.confluence-auth.example` (repo root) → `.confluence-auth`, dán PAT
(Confluence → avatar → Settings → Personal Access Tokens → Create token). Thiếu file / PAT còn
placeholder → script throw → **DỪNG, báo user setup**, không tự bịa.

Gọi (agent chạy qua shell tool):
```
powershell -ExecutionPolicy Bypass -File scripts/confluence-publish.ps1 -Manifest <feature>/confluence-publish.manifest.json
```

`manifest.json`: `{ pageId, baseUrl?, title, storageFile, versionMessage, attachments:[{path,name,contentType,label,comment}] }`
— path tương đối thư mục manifest; script tự đọc version live +1, tự sync revision (§4).

## 2. Storage format (XHTML) — luật cứng

- **Escape mọi text node tự chèn**: `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;`, `"`→`&quot;`. Bẫy 400 hay gặp:
  `&` TRẦN trong câu tiếng Việt ("đối tượng & tham chiếu") → `Error parsing xhtml: Unexpected character '&'`.
  Trước khi PUT quét raw `&` bằng regex `&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)`. Ưu tiên `→`/`·` thay `>`/`&`.
- Khối code/diagram trong `<![CDATA[ ... ]]>` (bên trong CDATA KHÔNG cần escape).
- Bảng: `<table class="wrapped"><tbody><tr><th>…</th></tr><tr><td>…</td></tr></tbody></table>`. Bảng lồng
  `<table>` trong `<td>` render OK trên Server.
- Panel: `<ac:structured-macro ac:name="tip|info|note"><ac:rich-text-body><p>…</p></ac:rich-text-body></ac:structured-macro>`.
- Thu gọn: `<ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">…</ac:parameter><ac:rich-text-body>…</ac:rich-text-body></ac:structured-macro>`.
- Mục lục: `<ac:structured-macro ac:name="toc"><ac:parameter ac:name="maxLevel">3</ac:parameter></ac:structured-macro>`.
- ⚠️ **HTML macro (`ac:name="html"`) BỊ TẮT** trên host `.35` → "Unknown macro: 'html'". Đừng nhúng mock bằng
  HTML macro; dùng markup native (table `wrapped` + `info`).

## 3. Checkbox = `ac:task-list` (KHÔNG dùng `☑ / ☐` unicode)

Template Tổng quan có bảng **"Đơn vị yêu cầu / Đơn vị liên quan"** (ĐVYC/ĐVLQ) dùng checkbox **chọn được**:

```html
<ac:task-list>
<ac:task><ac:task-id>NNN</ac:task-id><ac:task-status>incomplete</ac:task-status><ac:task-body> </ac:task-body></ac:task>
</ac:task-list>
```
- `ac:task-status` = `incomplete` (chưa tích) | `complete` (đã tích). `ac:task-body` rỗng ` ` cho ô chỉ-tích.
- **`ac:task-id` DUY NHẤT toàn trang** — đặt dải riêng cho phần sinh mới (vd 201+) tránh trùng id template gốc.
- Đơn vị nghiệp vụ chính của hệ thống → tích `ĐVYC=complete`; các đơn vị "Bắt buộc approved" giữ `ĐVLQ=complete`.

## 4. Ngày = date macro (chip lịch), không phải text

Bảng "ghi nhận thay đổi": cột ngày render inline date macro (giống trang mature):
```html
<td><div class="content-wrapper"><p><time datetime="2026-07-16"></time></p></div></td>
```
KHÔNG để `<td>2026-07-16</td>` (text trần).

## 5. Dò plugin sơ đồ (macro) — probe CHỦ ĐỘNG, đừng suy từ "không ai dùng"

- CQL đếm trang dùng macro: `confluence_search(query='macro="drawio"')` (hoặc `mermaid`/`plantuml`). Có kết quả =
  từng có người dùng — **CHƯA chắc render**; **rỗng ≠ chưa cài plugin** (chỉ nghĩa chưa ai dùng).
- **Xác định render được hay không** = đọc `body.view`/`body.storage` của trang thật dùng macro đó (đọc **vài** trang,
  không chỉ 1); nếu chứa `plugins/servlet/confluence/placeholder/unknown-macro?name=<macro>` → **plugin CHƯA cài**.
  Không chắc → **tạo 1 trang nháp có đúng macro, đọc `body.view`, rồi xoá** (probe chủ động) thay vì đoán từ trang lạ.
- Kinh nghiệm host `.35`: **có draw.io** (plugin //SEIBERT/MEDIA) → ưu tiên draw.io. Không có mermaid.

## 6. draw.io — macro + attachment + `revision` (auto-sync bởi script)

Mỗi sơ đồ = 1 attachment mxfile (tên không đuôi, `contentType application/vnd.jgraph.mxfile`, `label drawio`),
nội dung mxGraph XML **không nén** (xem [diagram-drawio.md](diagram-drawio.md)). Chèn macro:
```html
<ac:structured-macro ac:name="drawio" ac:schema-version="1"><ac:parameter ac:name="border">true</ac:parameter><ac:parameter ac:name="diagramName">TEN_SO_DO</ac:parameter><ac:parameter ac:name="simpleViewer">false</ac:parameter><ac:parameter ac:name="links">auto</ac:parameter><ac:parameter ac:name="tbstyle">top</ac:parameter><ac:parameter ac:name="lbox">true</ac:parameter><ac:parameter ac:name="diagramWidth">1200</ac:parameter><ac:parameter ac:name="revision">1</ac:parameter></ac:structured-macro>
```
🔴 **`revision` PHẢI = ĐÚNG version của attachment mxfile** (plugin SEIBERT dùng nó để chọn version render):
- `revision` **< version** → hiển thị **bản CŨ** ("diagram chưa update"). `>` → **404**. `=` → đúng bản mới. ✓
- Mỗi publish re-upload mxfile → version +1. **KHÔNG hand-set revision** — `confluence-publish.ps1` tự đọc version
  vừa upload rồi ghi đè `<ac:parameter ac:name="revision">` khớp `diagramName` (điều kiện: param `revision` nằm SAU
  `diagramName` trong macro — drawio_lib.py emit đúng thứ tự). Với **CREATE** (mxfile version 1) thì `revision=1` là đúng.
- draw.io = **nguồn hiển thị** (macro editable). ĐỪNG chèn `<ac:image>` PNG riêng cạnh macro. PNG "exported to image"
  (nếu có) chỉ là backup tĩnh.

## 7. Quy trình an toàn khi publish (draw.io)

1. MCP `create_page` skeleton (trang mới) **hoặc** xác định `pageId` cần update.
2. Sinh nội dung storage → **validate escape** (không `&` trần ngoài CDATA) → ghi ra file `*.storage.xhtml`.
3. Sinh mxfile qua `drawio_lib.py` → ghi file (tên = `diagramName`, không đuôi).
4. Viết `confluence-publish.manifest.json` (pageId + title + storageFile + attachments).
5. Chạy `confluence-publish.ps1 -Manifest …` → upload attachment + **auto-sync revision** + PUT body version+1 (atomic).
6. **Verify**: MCP `get_page` / `get_attachments` → **version attachment mxfile == `revision` trong macro**;
   `body.view` không còn `unknown-macro`; số dòng bảng/sơ đồ khớp. Báo user hard-refresh (Ctrl+F5).
7. Cập nhật ô link trong bảng tổng hợp tài liệu (body-only qua MCP `update_page` — không đụng attachment).
