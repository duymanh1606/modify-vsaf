# Markdown DD spec → Confluence storage-format (XHTML)

Confluence lưu body dạng **storage format** (XHTML mở rộng). Map từng phần tử Markdown của DD spec sang XHTML. Khuyến nghị dùng thư viện convert + hậu xử lý, hoặc build tay theo bảng dưới. Toàn bộ text phải escape XML (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`) TRỪ trong `<![CDATA[...]]>`.

## Ngôn ngữ & đối tượng đọc (BẮT BUỘC — xem workflow §Iron Rules 6/7 + §Nguyên tắc trình bày)

- **Giữ nguyên dấu tiếng Việt** ở mọi text (heading, prose, ô bảng, chú thích trong CDATA). Body gửi API là UTF-8 — ký tự có dấu giữ nguyên, hoặc dùng numeric entity `&#7841;`. **Không strip dấu / viết không dấu.** Nếu build bằng script sinh XHTML: viết string tiếng Việt có dấu trực tiếp và ghi file `encoding='utf-8'`, gửi curl với `Content-Type: application/json; charset=utf-8`.
- **Prose cột "Mô tả xử lý" viết cho tester/BA**, không phải chép code: dịch lời gọi hàm/tham số kỹ thuật (`Class.method(...)`, `PageRequest.of(...)`, kiểu Java, tên biến nội bộ) sang ý nghĩa nghiệp vụ. Giữ nguyên endpoint/path, tên tham số request, ngưỡng số, mã lỗi (dữ liệu test).
- **Điều kiện + mã lỗi giữ đúng, thêm chú thích ý nghĩa trong ngoặc:** `totalElements == 0 (số bản ghi tìm được) → PMT-019 (không có dữ liệu export)`.

## Ánh xạ phần tử cơ bản

| Markdown | Storage-format XHTML |
|:---|:---|
| `# H1` | `<h1>...</h1>` |
| `## H2` / `### H3` | `<h2>...</h2>` / `<h3>...</h3>` |
| đoạn văn | `<p>...</p>` |
| `**bold**` | `<strong>...</strong>` |
| `*italic*` | `<em>...</em>` |
| `` `code` `` | `<code>...</code>` |
| `- item` (list) | `<ul><li>...</li></ul>` |
| `1. item` | `<ol><li>...</li></ol>` |
| `[text](url)` | `<a href="url">text</a>` |
| `---` (hr) | `<hr/>` |
| code block ` ``` ` | Code Block macro (xem dưới) |
| ` ```mermaid ` | PlantUML Macro (xem `mermaid-to-plantuml.md`) |
| bảng `| a | b |` | `<table>...` (xem dưới) |

## Bảng

```xml
<table>
  <tbody>
    <tr><th>Cột 1</th><th>Cột 2</th></tr>
    <tr><td>giá trị</td><td>giá trị</td></tr>
  </tbody>
</table>
```
Nội dung ô có thể chứa `<p>`, `<code>`, `<a>`. Xuống dòng trong ô: `<br/>`.

## Code block (không phải diagram)

```xml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">java</ac:parameter>
  <ac:plain-text-body><![CDATA[<code nguyên văn>]]></ac:plain-text-body>
</ac:structured-macro>
```
`language`: map từ info-string của code fence (`json`, `yaml`, `sql`, `bash`...). Không rõ → `text`.

## Macro tiện ích (dùng khi Template có)

- Mục lục: `<ac:structured-macro ac:name="toc"/>`.
- Info/Note panel: `<ac:structured-macro ac:name="info"><ac:rich-text-body><p>...</p></ac:rich-text-body></ac:structured-macro>`.

## Expand macro (thu gọn / mở rộng)

Dùng để nhúng curl / SQL / Response / Kafka message mẫu vào bảng mô tả nghiệp vụ (xem workflow §6D). Body là rich-text nên bên trong **bọc một Code Block macro** đúng ngôn ngữ.

```xml
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">Expand</ac:parameter>
  <ac:rich-text-body>
    <ac:structured-macro ac:name="code">
      <ac:parameter ac:name="language">bash</ac:parameter>
      <ac:plain-text-body><![CDATA[<curl / SQL / JSON nguyên văn>]]></ac:plain-text-body>
    </ac:structured-macro>
  </ac:rich-text-body>
</ac:structured-macro>
```

- `title` = `Expand` (khớp mẫu Confluence hiện có).
- `language` map theo loại nội dung: curl → `bash`; SQL → `sql`; Response / Kafka message → `json`.
- Đặt Expand **ngay trong ô** "Logic xử lý nội bộ" của bước tương ứng (sau đoạn prose mô tả bước). Expand nằm trong `<td>` là storage hợp lệ.
- Nếu một bước cần chú thích mapping tham số (vd `:params` của SQL, `Trong đó:`), giữ nguyên phần chú thích đó **bên trong** `<![CDATA[...]]>` của Code Block (giống mẫu spec), không tách ra XHTML.
- **BẮT BUỘC với SQL/curl có tham số — thêm khối "trong đó:" ở cuối** (xem workflow §6D.d): sau lệnh, cách 1 dòng trống, thêm `-- trong đó:` (SQL/bash) hoặc `// trong đó:` (JSON), liệt kê từng tham số: tên — ý nghĩa nghiệp vụ — **nguồn/lấy ở bước nào** (vd "người dùng nhập ở B2", "server default ở B3", "hằng số"). Nội dung faithful theo §4.1 Mapping Field + §3.2 Logic Matrix, không bịa. Chú thích viết bằng tiếng Việt có dấu, để trong CDATA nên không cần escape.

## Map theo Template DD Core

- **Giữ đúng thứ tự + tiêu đề mục** như Template fetch được ở workflow Bước 2 (không tự đổi tên mục).
- Mục Template có nhưng spec **không có dữ liệu** → ghi `<p>N/A</p>` (giống mẫu tổ chức: "6. Yêu cầu phi chức năng: N/A", "8.1 Thiết kế CSDL: N/A").
- Nội dung DD spec map vào **đúng mục tương ứng** của Template; nếu spec có mục không nằm trong Template → gộp vào mục gần nghĩa nhất hoặc đặt cuối, và ghi chú trong log.
- Bảng changelog: theo cột Template "BẢNG GHI NHẬN THAY ĐỔI TÀI LIỆU" (xem workflow Bước 5+6, map cột).
- Bảng "Danh sách tài liệu tham khảo": lấy các link tham chiếu trong DD spec (TechSpec, Module 0, WBS, CR/Jira) → 2 cột Tên tài liệu · Link.

## Nguyên tắc an toàn convert

- Không mất nội dung: mọi mục/bảng/đoạn của spec phải có mặt (hoặc N/A) trên trang.
- Không tự thêm nội dung không có trong spec.
- Escape XML đúng để tránh vỡ trang; test bằng cách GET lại storage sau khi ghi (chỉ khi user đã confirm ghi) — nhưng không sửa tiếp nếu không cần.
- Verify nhanh: đếm số `<h2>`/`<table>`/macro so với số mục/bảng/diagram nguồn để phát hiện thiếu.
