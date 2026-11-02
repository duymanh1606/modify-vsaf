# draw.io — cấu trúc mxfile & cách render trên Confluence

## Nguyên tắc
- draw.io Confluence plugin (host `.35` = //SEIBERT/MEDIA) render sơ đồ **live bằng mxGraph từ nội dung mxfile** (attachment), KHÔNG cần ảnh PNG.
- Dùng mxGraph XML **không nén** (đặt thẳng `<mxGraphModel>` trong `<diagram>`) — plugin đọc được, khỏi phải deflate+base64.
- Sinh mxfile bằng `scripts/drawio_lib.py` (5 hàm: `overview_zones` / `process_3col` / `erd` / `state_diagram` / `breakdown_tree`).

## 🔴 `revision` PHẢI KHỚP version attachment (bài học xương máu)
Plugin SEIBERT dùng param `revision` của macro để chọn **đúng version attachment mxfile** cần render:
- `revision` **< version** → hiển thị **bản CŨ** ("diagram chưa update"); `>` → **404**; `=` → đúng bản mới nhất. ✓
- Mỗi lần publish re-upload mxfile → attachment version +1. **KHÔNG hand-set revision** — `scripts/confluence-publish.ps1`
  tự đọc version vừa upload rồi ghi đè `<ac:parameter ac:name="revision">` (khớp `diagramName`). Với CREATE (mxfile version 1) → `revision=1`.
- Điều kiện để auto-sync bắt được: trong macro, param `revision` nằm **SAU** `diagramName` (drawio_lib emit đúng thứ tự).
- **Verify sau publish**: `get_attachments` → version mxfile == `revision` macro. Đây là điều kiện SỐNG CÒN (không 404, không kẹt render cũ).

## Cạnh (edge) — routing

🔴 **Bài học: `orthogonalEdgeStyle` làm mũi tên CHỒNG NHAU.** draw.io tự re-route và kéo mọi cạnh chụm vào trục giữa;
với state diagram (có bước nhảy + quay lui) và cây phân rã (nhiều lá dưới cùng một nhóm) thì các đường đè lên nhau và
cắt xuyên qua hộp — trang xuất bản bị phản hồi "đường dẫn mũi tên bị trùng nhau" (thực tế 2026-08-07).

| Sơ đồ | Routing | Cơ chế |
|:---|:---|:---|
| `state_diagram`, `breakdown_tree`, `process_3col`, **`erd_graph`** | **`edgeStyle=none` + port + waypoint** (helper `_edge_px`) | Node đã canh trục sẵn nên toạ độ tính chính xác; draw.io vẽ đúng các đoạn thẳng qua waypoint, không tự bẻ lại |
| `erd` (lưới field-level) | `entityRelationEdgeStyle` | Ít quan hệ, hộp lớn — để draw.io tự lo |
| `overview_zones` | `orthogonalEdgeStyle` | Rất ít cạnh cấp cao giữa các vùng liền kề |

**Quy tắc LÀN (rail) — không hai đường nào cùng một trục:**
- `state_diagram`: chuyển tiếp **liền kề** → thẳng trục chính; **nhảy tiến** + cạnh vào *Kết thúc* → rail bên **phải** (đỏ nếu vào Kết thúc);
  **quay lui / tự lặp** → rail bên **trái**, nét đứt xanh. Mỗi cạnh rail chiếm một làn riêng, cách nhau 38px; làn trong cùng dành cho bước nhảy ngắn nhất (ít cắt nhau nhất).
- `breakdown_tree`: gốc → bus ngang → rẽ xuống từng cụm; trong cụm dùng **một trục dọc**, mỗi lá một nhánh ngang vào **cạnh trái** của lá.
- `erd_graph`: đoạn **ngang** chỉ chạy trong **kênh giữa hai hàng**, đoạn **dọc** chỉ chạy trong **máng giữa hai cột** — cả hai vùng đều không có hộp, nên cạnh không bao giờ cắt hộp. Ba mức chống chồng: (a) mỗi cạnh một làn trong kênh, (b) mỗi cạnh một làn trong máng, (c) **cổng cấp theo (cột, kênh)** chứ không theo hộp — hai đoạn cùng chạy trong một kênh ở cùng một cột (một đi ra từ hộp trên, một đi vào hộp dưới) sẽ trùng x nếu cấp cổng theo hộp.
- Cạnh chỉ thẳng đứng khi hai node **cùng trục x** — nếu không, bắt buộc phát waypoint gấp khúc, đừng để draw.io tự đoán.
- Nhãn cạnh đặt `labelBackgroundColor=#ffffff` để chữ không dính vào đường.

Khi thêm loại sơ đồ mới: nếu node đã canh trục → dùng `_edge_px`; chỉ để `orthogonalEdgeStyle` cho bố cục tự do.

**Cấp slot cổng (port slot).** Chia làn rail thôi CHƯA đủ: hai cạnh nối vào cùng một hộp ở cùng độ cao sẽ dùng
chung đoạn ngang sát mép hộp → vẫn chồng nhau dù rail khác nhau. `state_diagram` vì vậy cấp cho mỗi điểm nối
trên mỗi cạnh hộp một `exitY`/`entryY` riêng (chia đều theo chiều cao, tự nới cao hộp khi nhiều cổng).
Chia sẻ điểm nối chỉ chấp nhận khi các cạnh **cùng nguồn** (thân cây dùng chung, có chủ đích — như `breakdown_tree`).

## Soi hình trước khi publish — `scripts/preview.py`

mxfile là XML: không render thì **không ai nhìn thấy sơ đồ cho tới khi nó đã nằm trên Confluence**. Đó chính là
đường mà lỗi mũi tên trùng nhau đi lên trang. Bắt buộc chạy sau khi sinh mxfile (workflow §7b):

```bash
python scripts/preview.py <mxfile> [mxfile2 ...] -o <outdir>      # --strict để cảnh báo => exit 1
```

Ghi `<tên>.preview.svg` + `<tên>.preview.png` (Chrome headless, 2x) và chạy 5 lint: hộp đè hộp · cạnh xuyên hộp
· hai cạnh chồng trục · node tràn khổ · trang rộng > 2600px. Exit `0` sạch/PNG OK · `2` thiếu Chrome (**không chặn** —
macro vẫn render live, chỉ mất ảnh soi) · `1` mxfile hỏng hoặc `--strict` mà còn cảnh báo.

Độ trung thực: cạnh `edgeStyle=none` (state/tree/process) vẽ **đúng** đường draw.io sẽ vẽ; cạnh
`orthogonalEdgeStyle`/`entityRelationEdgeStyle` (overview/erd) chỉ **xấp xỉ** nối tâm — xem bố cục, đừng phán xét
đường đi, và lint cũng bỏ qua nhóm này để tránh báo động giả.

## Khung mxfile
```xml
<mxfile host="<confluence-host>" type="atlas" version="20.8.2">
  <diagram id="D1" name="Page-1">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" page="1" pageScale="1"
                  pageWidth="{PW}" pageHeight="{PH}" math="0" shadow="0">
      <root>
        <mxCell id="0"/><mxCell id="1" parent="0"/>
        <!-- vertices -->
        <mxCell id="n1" value="Nhãn" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
                vertex="1" parent="1"><mxGeometry x="40" y="40" width="160" height="40" as="geometry"/></mxCell>
        <!-- edges -->
        <mxCell id="e1" value="1 : N" style="edgeStyle=orthogonalEdgeStyle;html=1;endArrow=block;"
                edge="1" parent="1" source="n1" target="n2"><mxGeometry relative="1" as="geometry"/></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Escape trong mxfile
- Value là thuộc tính XML → escape `& < > "`.
- Xuống dòng trong 1 ô: dùng ký tự newline `&#10;` (khi sinh bằng Python: build với `\n` rồi `.replace(chr(10),"&#10;")` **sau khi** đã escape, để không bị escape nhầm `&#10;` thành `&amp;#10;`).
- Bật `html=1` để dùng `<br>` / định dạng; khi đó `<b>` phải viết `&lt;b&gt;` (drawio tự giải mã).

## Kiểu (style) hay dùng
| Mục đích | style |
|---|---|
| Actor người que | `shape=umlActor;html=1;verticalLabelPosition=bottom;verticalAlign=top;fillColor=#fff2cc;strokeColor=#d6b656;` |
| Hộp chức năng | `rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;` |
| Quyết định (hình thoi) | `rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;` |
| Bắt đầu/Kết thúc | `ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;` |
| CSDL | `shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;` |
| Vùng/khối bao (container nhìn) | `rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#4472c4;strokeWidth=3;verticalAlign=top;fontStyle=1;` |
| Ô bảng ERD | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#b3b3b3;align=left;spacingLeft=4;overflow=hidden;` |
| Cạnh ERD 1:N | `edgeStyle=entityRelationEdgeStyle;html=1;endArrow=ERmany;startArrow=ERone;` |

## Bảng lưới ERD (mỗi thực thể)
Không dùng shape=table phức tạp; dựng bằng **ô rectangle tuyệt đối**:
- 1 ô header (tên bảng, tô màu miền), rộng W.
- Mỗi trường = 3 ô kề nhau trên 1 hàng: `[kiểu dữ liệu | tên trường | khóa/ghi chú]` (rộng ~64 / ~152 / ~120, cao ~24).
- Cạnh 1:N nối **ô header** của 2 thực thể.
→ Xem hàm `erd_grid_entity()` trong `scripts/drawio_lib.py`.

## Bố cục gọn (tránh rối mũi tên)
- **§2 Mô hình tổng quan = bố cục VÙNG trái→phải** (`overview_zones`): Nguồn dữ liệu đầu vào · Hệ thống lõi · Cơ chế tích hợp · Giao diện (FE) · Actor. Mỗi vùng = 1 khung bao chứa thành phần xếp dọc; **KHÔNG vẽ cạnh nội bộ chằng chịt** — cấu trúc thể hiện bằng phân vùng.
- Mũi tên **cấp cao** thể hiện chiều dữ liệu **in → xử lý → out** giữa các vùng liền kề (ít thôi); hệ thống ngoài tô **xám nét đứt** để nhận diện.
- Actor = người que ngoài cùng phải, nối **1 cạnh** tới đúng FE tương tác.
- Nhiều cạnh giao nhau chỉ chấp nhận ở ERD (bản chất quan hệ).
