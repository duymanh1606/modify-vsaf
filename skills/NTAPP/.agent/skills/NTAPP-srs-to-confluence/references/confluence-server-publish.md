# REFERENCE: Publish lên Confluence **Server** — cơ chế thật + template fidelity

> Tổng hợp bài học vận hành thật khi publish SRS lên host `.35` (Confluence **Server**, space `TDOV`). Đọc khi tới §8/§9 (EXECUTE). Bổ sung cho `../NTAPP-dd-to-confluence/references/storage-format.md`.

## 0. Vàng: MCP KHÔNG upload attachment được — dùng REST qua auth file

- `mcp__atlassian*__confluence_upload_attachment` **và** `_upload_attachments` **luôn FAIL** trên Confluence Server này (`success:false` / "Failed to upload attachment"), kể cả trang nhỏ, kể cả file có đuôi chuẩn (`.png`). Đây KHÔNG phải lỗi hard-limit — body-only `update_page` vẫn chạy.
- ⇒ **Mọi attachment (draw.io mxfile, PNG, HTML tải về…) phải upload qua REST multipart.** Skill có script sẵn: [`../scripts/confluence-publish.ps1`](../scripts/confluence-publish.ps1).
- **Agent tự chạy script** (qua shell/PowerShell tool) — user KHÔNG gõ lệnh. Token đọc từ file `.confluence-auth` (gitignored) ở repo root:

  ```
  CONFLUENCE_BASE_URL=http://10.254.136.35:8090
  CONFLUENCE_PAT=<Personal Access Token>
  ```

  Setup 1 lần: copy `.confluence-auth.example` → `.confluence-auth`, dán PAT. Nếu thiếu file / PAT còn placeholder → script throw, DỪNG báo user setup (Confluence → avatar → Settings → Personal Access Tokens → Create token).
- **Cách gọi** (một lệnh làm cả upload attachment + PUT body, atomic — trang không kẹt macro rỗng):

  ```
  powershell -ExecutionPolicy Bypass -File <skill>/scripts/confluence-publish.ps1 -Manifest <feature>/confluence-publish.manifest.json
  ```

  Manifest mô tả pageId + titleFile/title + storageFile + versionMessage + danh sách attachment `{path,name,contentType,label,comment}` (path tương đối thư mục manifest). Xem mẫu `srs/BE-RP-17/confluence-publish.manifest.json`. Script tự đọc version live +1.

- **Body vẫn có thể đi MCP** `update_page(content_format="storage")` NẾU không có attachment (trang nhỏ). Nhưng khi có draw.io/ảnh → dùng luôn script để atomic. Trang **mature lớn** (>~150KB body) thì cả body cũng phải PUT REST (MCP cắt output) — xem storage-format.md.

## 1. Checkbox = `ac:task-list` (KHÔNG dùng `☑ / ☐` unicode)

Template SRS (api/tiến trình/web) dùng **task-list chọn được**, không phải ký tự unicode (user sẽ chê "không tích được"). Mọi ô tích trong SRS phải render bằng `ac:task-list` — **KHÔNG có ngoại lệ**, gồm: bảng Đơn vị phê duyệt cột ĐVYC/ĐVLQ · §1 Loại chức năng · §3 Loại dữ liệu · **§5 cột Trạng thái (Thành công/Chưa rõ/Thất bại)**. ⚠️ **§5 Trạng thái RẤT hay bị bỏ sót thành unicode `☑ Thành công ☐ Chưa rõ ☑ Thất bại`** (BE-RP-18 mắc lần đầu, phải sửa v4) — luôn dùng task-list 3 task, phần giải thích (vd "— fail ngay, báo Ops") để text NGAY SAU `</ac:task-list>` cùng ô. Render:

```html
<ac:task-list>
<ac:task><ac:task-id>NNN</ac:task-id><ac:task-status>incomplete</ac:task-status><ac:task-body>  Nhãn</ac:task-body></ac:task>
<ac:task><ac:task-id>NNN+1</ac:task-id><ac:task-status>complete</ac:task-status><ac:task-body>  Nhãn 2</ac:task-body></ac:task>
</ac:task-list>
```

- `ac:task-status` = `incomplete` (chưa tích) | `complete` (đã tích). `ac:task-body` = nhãn (rỗng ` ` cho ô chỉ-tích như ĐVYC/ĐVLQ).
- **`ac:task-id` phải DUY NHẤT toàn trang.** Đặt dải riêng cho tài liệu sinh mới (vd 201+, 231+, 241+) tránh trùng id template gốc.
- Map mặc định Đơn vị phê duyệt (theo template `199113677`): hàng 1-3 (P.KTDV/CSKH/Trải nghiệm KH) `ĐVLQ=complete` + ghi chú "Bắt buộc approved tài liệu"; các hàng còn lại `incomplete`. Đơn vị nghiệp vụ chính của feature → tích `ĐVYC=complete`.

## 2. Ngày = date macro (chip lịch), không phải text

Cột ngày trong "Bảng ghi nhận thay đổi" render bằng inline date macro để ra chip 📅 (giống các trang mature):

```html
<td><div class="content-wrapper"><p><time datetime="2026-07-14"></time></p></div></td>
```

KHÔNG để `<td>2026-07-14</td>` (text trần, xuống dòng xấu).

## 3. §2.1 Biểu đồ activity = draw.io (không phải sequence)

Template API/tiến trình đặt tên mục **"2.1. Biểu đồ activity diagram"** → dùng **activity diagram vẽ draw.io** (editable), KHÔNG phải sequence PlantUML.

**Single-source-of-truth generator:** [`../scripts/build-activity-diagram.mjs`](../scripts/build-activity-diagram.mjs).
- Input: 1 file `<feature>-activity.model.json` (mảng `nodes` {id,type,x,y,w,h,t} + `edges` {f,t,k,l}). Xem mẫu `srs/BE-RP-17/BE-RP-17-activity.model.json`.
- Output (1 lệnh): `<base>` (mxfile draw.io) **+** `<base>.png` (Chrome headless screenshot @2x, khớp toạ độ mxfile 100% vì cùng model).

  ```
  node <skill>/scripts/build-activity-diagram.mjs <feature>-activity.model.json <out_dir> <base_name>
  # base_name = tên diagram, vd BE-RP-17-activity-flow (mxfile KHÔNG đuôi)
  ```
- node types: `action`(rounded) `decision`(rhombus) `term`(ellipse start/end) `bar`(nhãn vòng lặp) `group`(**khung nét đứt bao vòng lặp** — nhãn góc trên-trái, vẽ SAU cùng nên nằm dưới) `lane`(**swimlane dọc theo actor** — dải tiêu đề cao 40 + thân, vẽ dưới cùng; node nằm trong lane thuần bằng toạ độ `x/y` của chính nó) `outcome`(hộp phải xanh: tiếp tục/loop-back) `abort`(hộp phải đỏ: dừng lỗi). edge `k`: `v`(dọc — **tự bẻ khuỷu xuống/ngang/xuống khi hai node khác lane**, thẳng khi cùng tâm-x) `R`(rẽ phải tới hộp cạnh) `L`(rẽ **trái** tới hộp cạnh — gương của `R`, dùng khi hộp nhánh nằm ở lane bên trái) `join`(hộp phải quay về node chính) `end`(hộp cạnh → **bus dọc phải `endRail`** → node Kết thúc) `loopL`/`loopR`(**mũi tên nét đứt xanh quay lại đầu vòng lặp**, rail chỉ định qua `edge.rail`; với `loopR` thì rail **phải** nằm bên phải cạnh phải của node đích, không thì đoạn cuối cắt xuyên qua node).
- **🎯 CHIA LANE THEO ACTOR LÀ MẶC ĐỊNH** (user chốt: "activity diagram chưa chia lane"). Mỗi actor/hệ thống tham gia = 1 node `lane` (cột dọc, tiêu đề = **tên actor/tên service thật**, khớp cột *Đối tượng* của bảng §2.2/§3.3). Mỗi node nghiệp vụ đặt vào đúng lane của đối tượng thực hiện nó; hộp `abort`/`outcome` cũng thuộc lane của đối tượng thực hiện, đặt ở **cột phụ bên phải trong chính lane đó** (lane có nhánh → chừa bề rộng cho 2 cột). Chỉ bỏ lane khi toàn luồng do đúng **một** đối tượng thực hiện.
- **Quy ước vẽ activity (đã chốt qua review — model.json phải tuân đủ 7 quy ước):**
  1. **Đánh số MỌI hình = một bước, tuần tự theo thứ tự đọc** — action, **ô quyết định**, VÀ hộp nhánh (abort/outcome) đều mang số `B1…Bn` liên tục (user chê "ô chữ nhật có số, ô [quyết định] thì không → khó mô tả"). KHÔNG để hình nào không số, KHÔNG dùng số vòng tròn rời. §2.2 tách **1 dòng / 1 hình**, cột Bước khớp số trên sơ đồ 1-1. (Terminal Bắt đầu/Kết thúc không cần số.)
  2. **Nhánh dừng phải nối tới Kết thúc** — mọi hộp `abort` (và outcome kết thúc như file-rỗng) dùng edge `end` gộp về **một** node `term` "Kết thúc" qua bus dọc bên phải (`endRail`), KHÔNG để hộp lơ lửng.
  3. **Vòng lặp = khung bao + mũi tên quay lại** — mỗi vòng lặp bọc bằng 1 node `group` (nhãn "⟳ Vòng lặp: …") **và** 1 edge `loopL`/`loopR` từ điểm quyết định cuối vòng quay lại đầu vòng. Rõ hơn hẳn `bar` nhãn suông (user chê "vẽ vòng lặp k rõ nghĩa"). Nhãn group để 1 dòng (tránh đè node dưới).
  4. **Nhãn node = NGÔN NGỮ NGHIỆP VỤ, không phải DD** — mô tả *việc nghiệp vụ đang xảy ra* ("Xin mã truy cập từ hệ thống trung gian", "Kiểm tra chữ ký số của VIB để đảm bảo dữ liệu đáng tin"), KHÔNG bê tên class/method/factory/endpoint/biến kỹ thuật vào nhãn (`RetrievalMethodFactory`, `isRunAble`, `POST /switching/...`, `saveCheckpoint`). Chi tiết kỹ thuật đó thuộc §4 (đặc tả API) + DD — user chê "câu chữ như mô tả DD, chưa mô tả nghiệp vụ gì". Quy ước này áp cho **cả nhãn sơ đồ §2.1 và ô mô tả §2.2**.
  5. **🎯 Spine (trục dọc) CÙNG TÂM X trong PHẠM VI MỘT LANE** — các node liên tiếp cùng lane đặt sao cho `x + w/2` bằng nhau (vd BE-RP-17 cx=370) để edge `v` ra **thẳng đứng**. Khi luồng **nhảy sang lane khác** thì tâm-x lệch là đúng: generator tự bẻ edge `v` thành khuỷu xuống/ngang/xuống (chỉnh cao độ đoạn ngang bằng `edge.rail`), KHÔNG được kéo node ra khỏi lane của nó để "cho thẳng trục".
  6. **🎯 Hộp cạnh (abort/outcome) CĂN THẲNG TÂM-Y với ô quyết định nguồn** — đặt `side.y = decision.cy − side.h/2` để edge `R` thành **đường ngang thuần, KHÔNG cần waypoint**. Đây là geometry đơn giản nhất, không renderer nào routing sai (generator tự bỏ waypoint khi `|Δy|<1`). *(Đừng để hộp cạnh lệch tâm-y → sinh waypoint elbow thừa, dễ glitch bộ render server-side.)*
  7. **🎯 CÁC LANE PHẢI DÙNG CHUNG VIỀN — KHÔNG hở khe giữa hai lane.** Lane kề nhau phải khít tuyệt đối: `lane[i].x + lane[i].w == lane[i+1].x` (và mọi lane cùng `y` + cùng `h`). Chỉ cần hở vài pixel là trang render ra **mấy khối chữ nhật rời**, đọc không còn ra swimlane — user chê ngay: *"phần activity diagram từng lane đang tách ra, k khớp vào nhau"* (case thật SCR-COMPOSE 2026-08-07: lane để hở 10px ở `290→300` và `860→870`, phải publish lại). Chuẩn đúng đang chạy ở SCR-EMBED-PMT (pageId `199112222`): `20..340 | 340..960 | 960..1580 | 1580..1830`.
     - **Cách bố cục an toàn:** chọn trước các mốc biên (vd `40, 300, 870, 1430`) rồi tính `w = biên_sau − biên_trước`; ĐỪNG đặt `w` tròn số rồi cộng thêm khoảng cách trang trí giữa các lane.
     - **Lane rộng bao nhiêu:** lane có nhánh (`abort`/`outcome` ở cột phụ) phải đủ chứa **cả** cột spine lẫn cột phụ — nới `w` của chính lane đó, KHÔNG đẩy hộp nhánh tràn sang lane bên cạnh.
     - 🎯 **LANE PHẢI BAO CẢ HAI BUS DỌC — `endRail` và rail của `loopL`/`loopR` nằm TRONG lane, KHÔNG được chạy ở lề trang.** User chốt: *"đường nối từ B5, B11, B15, B21, B24, B27 tới Kết thúc hay đường từ B18 về B17 đang bị chờm ra khỏi lane → chỉnh cho lane rộng hơn bao các đường đó nữa"* (case thật SCR-COMPOSE 2026-08-07, phải publish lại lần 3). Nhìn ảnh thấy nét vẽ nằm ngoài khung lane là sai, dù sơ đồ vẫn "đúng logic".
       - `endRail` phải thoả `lane_cuối.x < endRail < lane_cuối.x + w` → nới `w` lane cuối (chừa ~25px từ rail tới viền lane).
       - rail của `loopL` phải nằm trong **lane đầu** → nới lane đầu sang trái (giảm `x`, cộng bù vào `w` để biên phải không đổi, giữ nguyên quy tắc khít lane).
       - `canvasW` phải lớn hơn biên phải của lane cuối (chừa lề ~25px), nếu không lane bị cắt.
       - Cấu hình đúng đang chạy ở SCR-COMPOSE: lane `10..300 | 300..870 | 870..1475`, `endRail=1450`, rail vòng lặp `=30`, `canvasW=1500`.
     - Generator tự kiểm và **cảnh báo** (không chặn) khi phát hiện khe hở / lane chồng nhau / lane lệch `y`-`h` / node nằm ngoài mọi lane / **`endRail` hoặc rail vòng lặp nằm ngoài dải lane** — thấy dòng `LANE WARN:` thì sửa model rồi gen lại trước khi publish.
- Nhúng vào storage: macro `ac:name="drawio"` param `diagramName` = **đúng tên attachment mxfile** (không đuôi), `diagramWidth` = `canvasW`, `revision` = **version attachment mxfile** (script tự set — xem cảnh báo 🔴 cuối §3; hand-set số bất kỳ, script ghi đè đúng):

  ```html
  <ac:structured-macro ac:name="drawio" ac:schema-version="1"><ac:parameter ac:name="border">true</ac:parameter><ac:parameter ac:name="diagramName">BE-RP-17-activity-flow</ac:parameter><ac:parameter ac:name="simpleViewer">false</ac:parameter><ac:parameter ac:name="links">auto</ac:parameter><ac:parameter ac:name="tbstyle">top</ac:parameter><ac:parameter ac:name="lbox">true</ac:parameter><ac:parameter ac:name="diagramWidth">1100</ac:parameter><ac:parameter ac:name="revision">2</ac:parameter></ac:structured-macro>
  ```
- Attach 2 file (qua confluence-publish.ps1 manifest): mxfile (`contentType application/vnd.jgraph.mxfile`, `label drawio`) + PNG (`contentType image/png`, `comment "<base> exported to image"`).
- ⚠️ **Bẫy Chrome "stale PNG"**: nếu Chrome đang mở, `--headless` cũ **attach vào instance sẵn có rồi return NGAY mà KHÔNG ghi PNG** → để lại file cũ (timestamp không đổi). Generator đã fix: `--headless=new` + `--user-data-dir` profile tạm riêng + đường dẫn PNG **tuyệt đối** (headless=new ghi path tương đối theo cwd của Chrome) + check `existsSync` sau khi chạy. Luôn **xem lại PNG** (Read image) trước khi publish để chắc đã đổi.
- ℹ️ **Cơ chế hiển thị trên .35**: macro draw.io render mxfile **sống bằng mxGraph** (đúng engine draw.io) theo `revision` (xem 🔴 cuối §3). PNG export đính kèm (comment "exported to image") là bản tĩnh dự phòng (dùng khi export PDF/email hoặc JS tắt). *(Note cũ "license hết hạn → watermark" là suy đoán SAI hướng — thủ phạm thật của mọi lần "diagram chưa update" là revision lệch version, KHÔNG phải watermark.)* Title để NGOÀI svg (generator tự làm) tránh đè node start.
- ⚠️ **draw.io PHẢI là nguồn hiển thị (macro editable), KHÔNG chèn ảnh PNG riêng.** User chốt: "phải theo draw.io, k phải mỗi ảnh; mũi tên vẽ đúng như ảnh gen". ⇒ ĐỪNG thêm `<ac:image>` cạnh macro — chỉ để **1 macro draw.io** trong §2.1.
- ⚠️ **mxfile edge PHẢI dùng `edgeStyle=none` + waypoint + port — KHÔNG dùng `orthogonalEdgeStyle`.** (Đã bake trong `build-activity-diagram.mjs`.)
  - `edgeStyle=none` → draw.io vẽ **đoạn thẳng nối qua đúng waypoint** (tái tạo path SVG chính xác). `orthogonalEdgeStyle` (dù có waypoint) vẫn **tự re-route, kéo mũi tên chụm vào giữa** → user chê "mũi tên dính hết vào giữa".
  - mỗi edge emit `exitX/exitY/entryX/entryY` (đúng cạnh nối như SVG: `end`=right→right, `loopL`=left→left, `loopR`=left→right, `R`=right→left, `join`=bottom→right, `v`=bottom→top) + `<Array as="points">` góc rail/elbow (END_RAIL cho `end`, `edge.rail` cho loop). Điểm axis-aligned với port ⇒ đoạn thẳng = orthogonal sắc nét, trùng PNG.
  - **Bỏ waypoint thừa/suy biến** (điểm trùng `(585,234)(585,234)` / zero-length segment) — glitch bộ render. Nhờ **quy ước 5 (spine cùng cx)** + **quy ước 6 (hộp cạnh căn tâm-y)** thì edge `v` không cần waypoint và edge `R` chỉ còn đường ngang thuần → geometry sạch nhất.
- 🔴 **ROOT CAUSE cả loạt "diagram chưa update" + lỗi 404 (BE-RP-17 v3→v12): `revision` PHẢI BẰNG ĐÚNG version của attachment mxfile.** Plugin SEIBERT dùng `revision` để chọn **đúng version attachment** cần render:
  - `revision` **< version** → macro hiển thị **bản render CŨ** của revision đó (mxfile mới đã upload nhưng KHÔNG hiện) → user chê "diagram chưa update / vẫn chưa được". *(Đây là bug ẩn suốt v3–v10: mỗi publish re-upload mxfile → version +1, nhưng revision hand-set lệch thấp hơn → luôn kẹt render cũ.)*
  - `revision` **> version** → **404** (không có revision đó). *(v11 nhảy revision=12 khi attachment mới version 9 → §2.1 404.)*
  - `revision` **= version** → hiển thị đúng bản mới nhất. ✓
- ✅ **Script `confluence-publish.ps1` giờ TỰ đồng bộ**: sau khi upload attachment `drawio`, đọc version vừa lên rồi ghi đè `<ac:parameter ac:name="revision">` trong macro (khớp `diagramName`) = version đó, và ghi lại vào file storage (repo == live). ⇒ **KHÔNG hand-set revision nữa** — cứ để script lo. (Điều kiện: macro có `diagramName` khớp `name` attachment, và param `revision` nằm SAU `diagramName` trong macro — generator emit đúng thứ tự này.) PNG "exported to image" (`<base>.png`) là preview tĩnh dự phòng, cũng cập nhật theo lần re-upload.

**✅ Checklist mỗi lần vẽ/sửa activity diagram (chạy tuần tự, đừng bỏ bước):**
1. model.json tuân đủ **7 quy ước vẽ** ở trên (đặc biệt **5 spine cùng cx** + **6 hộp cạnh căn tâm-y** + **7 lane dùng chung viền, không hở khe**).
2. `node build-activity-diagram.mjs <model.json> <out_dir> <base>` → sinh mxfile + PNG.
3. **Read lại PNG** (image) xác nhận mũi tên đúng **và các lane khít thành một khối liền** (quy ước 7 — nhìn ảnh là thấy ngay có hở khe hay không) — PNG khớp mxfile 100% (cùng model), nên PNG chuẩn ⇒ mxfile chuẩn.
4. Publish qua `confluence-publish.ps1 -Manifest ...` (script tự sync revision, không hand-set).
5. **Verify sau publish**: `get_attachments` → **version attachment mxfile == `revision` trong macro** (log script in "revision auto-synced: … -> N"). Đây là điều kiện SỐNG CÒN để trang hiển thị đúng bản mới (không 404, không kẹt render cũ).
6. Báo user hard-refresh (Ctrl+F5). Nếu user vẫn thấy sai → **xin screenshot render hiện tại** (đừng blind-fix; so ngay `revision` vs `version` trước tiên).

## 4. Template fidelity — bám ĐÚNG khung template, đừng thêm mục lạ

Fetch template (§3 workflow) rồi map **đúng thứ tự + tên mục**, KHÔNG chèn mục ngoài template. Với **Template API nghiệp vụ** (`199113677`):

1. **Bảng "XÁC ĐỊNH ĐƠN VỊ YÊU CẦU VÀ ĐƠN VỊ LIÊN QUAN"** (10 dòng đơn vị, task-list ĐVYC/ĐVLQ — §1 trên).
2. **Bảng ghi nhận thay đổi** đúng 8 cột: Ngày (date macro) · Vị trí · A/M/D · Nguồn gốc · Link CR · Mô tả · Phiên bản confluence · Phiên bản mới.
   - 🎯 **Cột phiên bản = SỐ VERSION TRANG CONFLUENCE sau khi cập nhật** (vd `7`), **KHÔNG** đánh số riêng cho tài liệu kiểu `1.0` / `2.0` (user chốt: "phiên bản cần theo version sau update confluence, k lấy 2.0"). Publish làm version trang `N → N+1` thì dòng mới ghi `N+1`. Thêm 1 dòng ghi chú ngay dưới bảng: *"Cột Phiên bản = số phiên bản trang Confluence sau khi cập nhật."*
2b. 🎯 **BẤT KỲ ĐOẠN TEXT NÀO CÓ NHIỀU Ý ĐỀU PHẢI TÁCH DÒNG + GẠCH ĐẦU DÒNG — KHÔNG VIẾT DỒN 1 ĐOẠN.**
   - User chốt 2 lần: *"cần trình bày xuống dòng từng ý, có gạch đầu dòng rõ ràng, k viết chung 1 dòng gây khó nhìn"* → và sau đó: *"cần áp dụng cho **mọi** đoạn text nào có nhiều ý, ví dụ mục 2.2/3.3 cột Mô tả, cột Ghi chú mỗi ô từng bước"*.
   - **Phạm vi = TOÀN TÀI LIỆU, không chỉ §1**: ô bảng ở **mọi** mục (bảng bước §2.2/§3.3 cột *Mô tả* + *Ghi chú* + *Bảng/Thực thể*, bảng control cột *Mô tả*, bảng mã lỗi, bảng chức năng ảnh hưởng, bảng thực thể, ô *Mô tả thay đổi* của bảng ghi nhận thay đổi) **và** đoạn văn ngoài bảng, kể cả text trong macro `note`/`warning`/`info`.
   - **Ngưỡng máy móc để khỏi tranh luận:** ô/đoạn có **≥ 2 câu** và **≥ 80 ký tự** → chuyển thành `<ul><li>`, mỗi câu (hoặc mỗi vế `<br />` sẵn có) là một `<li>`. Ô 1 câu hoặc quá ngắn thì để nguyên. Ý có thứ tự → `<ol>`; ý phụ → lồng `<ul>` cấp 2; mỗi nhóm mở đầu bằng `<strong>Nhãn:</strong>`.
   - Trong **file markdown nguồn** (ô bảng markdown không chứa list thật): dùng `<br>• ` cho cấp 1 và `<br>&nbsp;&nbsp;– ` cho cấp 2.
   - Việc này **làm lúc sinh nội dung**, đừng để review xong mới đi vá.
3. **§1 Mô tả chung**: Mục đích · Loại chức năng (task-list Web/Mobile/Tiến trình/API) · Đối tượng sử dụng · Pre/Post-condition · **Chính sách & ràng buộc** ← dồn **NFR/bảo mật/config** vào đây (KHÔNG tách §7 NFR riêng).
4. **§2 Luồng nghiệp vụ**: 2.1 activity draw.io · 2.2 bảng bước **đúng 5 cột của template** (fetch template `199113677` xác nhận): `Bước · Đối tượng · Mô tả · Ghi chú · Bảng/Thực thể liên quan`. Chi tiết từng cột:
   - **Mô tả** = ngôn ngữ nghiệp vụ (KHÔNG class/method/endpoint — §3 quy ước 4) **và gộp luôn kết quả/rẽ nhánh vào ô này** (vd "… → Ngoài khung giờ thì bỏ qua, kết thúc"). KHÔNG tách cột "Kết quả/rẽ nhánh" riêng (không có trong template).
   - **Đối tượng** = **TÊN SERVICE thực hiện** (vd `reconciliation-process`, `reconciliation-external-data-service`), KHÔNG ghi chung chung "hệ thống" (user chê "để tên service ấy, đừng chung chung"). Chỉ **hệ thống ngoài** mới để tên đối tác chung (vd "Core Transfer", "VIB") — kèm chú "(hệ thống ngoài)". Bước gọi ra ngoài: `<service> ↔ <đối tác ngoài>`.
   - **Bảng/Thực thể liên quan** = **TÊN BẢNG DB THẬT** (`configuration_retrieval_data`, `config_business_list`, `detail_retrieval_data`, `statistic_retrieval_data`, hoặc "MinIO (file tạm)") + loại (truy vấn/insert/update) — **KHÔNG dịch sang tên tiếng Việt** (user chê "để đúng tên bảng/thực thể trong DB đi").
   - **Bước ghi DB → KHÔNG viết câu lệnh SQL/WHERE/SET**; đặt **NGAY trong ô Mô tả của chính bước đó** (user chê "để dưới khó theo dõi, đưa luôn vào tại bước"). ⚠️ **Bài học 2026-08-11 (HUB-02 v5):** tôi đặt bảng ánh xạ ở mục 4.2 rồi ở bước chỉ ghi *"thêm một dòng vào bảng hồ sơ tổng hợp"* + câu trỏ "chi tiết tại mục 4.2" — user bác ngay: *"B16 cụ thể ghi như nào, trường nào, với giá trị như nào, đừng chỉ ghi chung chung"*. Cross-reference KHÔNG thay được bảng lồng tại bước. Áp cho **MỌI** bước ghi: ghi nghiệp vụ, **ghi log**, và cả **bước ghi khi thất bại** (vd ghi log lần tạo thất bại ở nhánh 409): dòng **`Điều kiện thực hiện/truy vấn:`** (điều kiện chọn bản ghi, WHERE bằng lời) + **bảng lồng 3 cột** `Trường nghiệp vụ | Cột trong CSDL | Giá trị ghi vào` (UPDATE: `Trường nghiệp vụ | Cột trong CSDL | Giá trị mới`) — cột giữa là **tên cột thật** trong DB, và câu dẫn trước bảng phải nêu **tên bảng schema-qualified** (vd "Giá trị ghi vào bảng `bms_hub.composite_requests`:"). Bảng lồng chỉ có tên trường thuần Việt là **CHƯA ĐẠT** (case thật SCR-COMPOSE 2026-08-07 — xem `srs-mapping.md`, mục "Tên trường thuần Việt KHÔNG BAO GIỜ đứng một mình"). **Mỗi bảng bị ghi = 1 bảng lồng riêng**, kể cả bảng nhật ký/audit. Bảng lồng `<table>` trong `<td>` — Confluence Server render OK (đã verify v6).
   §3 (bảng thực thể) trỏ về các bước này cho **giá trị ghi**, nhưng vẫn phải có bảng lồng `Cột trong CSDL | Ý nghĩa` liệt kê **cấu trúc cột** của từng entity do hệ thống own (không mô tả cấu trúc bảng bằng prose).
   - **🔗 Crosslink luồng xử lý (process-flow) — BẮT BUỘC nếu feature là một mắt trong chuỗi tiến trình.** Nếu feature được **một tiến trình cha gọi tới** (upstream) và/hoặc **bàn giao sang tiến trình kế tiếp** (downstream), chèn dòng **`Refer`** hyperlink vào ô **Ghi chú** của đúng bước giáp ranh (không tạo mục/section mới):
     - Bước **entry** (nơi cron/tiến trình cha kích hoạt, thường B1) → `<strong>Refer</strong> (tiến trình cha điều phối): <a href="…viewpage.action?pageId=<UP>">NN. <tên trang tiến trình cha></a>.`
     - Bước **hand-off/persist cuối** (nơi bàn giao downstream, vd bước gộp file + tạo bản ghi thống kê) → `<strong>Refer</strong> (tiến trình kế tiếp): <a href="…pageId=<DOWN>">NN. <tên trang kế tiếp></a>.`
     - Đây là convention **có sẵn ở các trang anh em cũ** (vd họ partner-pull `05.01–05.03` đều `Refer: 01. KBNV tiến trình download file dữ liệu đối soát từ đối tác` → pageId `63738338`; downstream = `02. KBNV tiến trình gửi yêu cầu đọc dữ liệu từ file để xử lý đối soát` → `63739095`). **Tìm pageId thật** bằng `confluence_search`/`get_page_children` trên đúng host (KHÔNG bịa link, KHÔNG cross-host). Contract `INT-EXT-*` đã pair-merge (§4) là "gọi ra ngoài" nội trang → KHÔNG cần link ngoài, chỉ trỏ "§4".
     - Chèn crosslink vào trang có sẵn = **body-only `update_page(content_format="storage")` qua MCP** (không đụng attachment/diagram) — nhanh, không cần chạy `confluence-publish.ps1`.
5. **§3 Bảng/thực thể**: STT·Bảng·Mô tả·Phát sinh mới·Ý nghĩa·**Loại dữ liệu (task-list Truy vấn/Update/Insert)**. Cột-giá-trị runtime trỏ về §2.2 (đừng lặp bảng riêng).
6. **§4 Thông tin dữ liệu API — gộp đầu vào + đầu ra THEO TỪNG API**: mỗi API/hop một mục con (vd `4.1 API Hop-1 …`, `4.2 API Hop-2 …`), trong đó **đầu vào (request) rồi đầu ra (response) liền nhau**. KHÔNG tách "4.1 Thông tin đầu vào / 4.2 Thông tin đầu ra" gộp mọi API (user chê "mô tả đầu vào đầu ra cho cùng 1 API luôn"). Bảng field: Thông tin·Require·Maxlength·Mặc định·Mô tả·Ràng buộc (đầu vào), Thông tin·Require·Maxlength·Mô tả (đầu ra). Pair-merge contract INT-EXT vào đây; endpoint phụ (thủ công) + config-driven để mục con cuối.
7. **§5 Danh sách trường hợp lỗi**: Trường hợp·Mã·**Trạng thái (BẮT BUỘC `ac:task-list` 3 task Thành công/Chưa rõ/Thất bại — KHÔNG unicode ☑/☐, xem §1)**; giải thích để text sau task-list cùng ô.

**Bỏ** các mục skill từng tự thêm ngoài template (§2 "Yêu cầu chức năng" riêng, §7 NFR riêng, §8 "Tài liệu liên quan" đứng riêng) — nội dung gộp vào mục template tương ứng (NFR→§1; tài liệu nguồn→info macro cuối §5).

## 5. XML escaping (nhắc lại — bẫy 400 hay gặp)

Ngoài CDATA, mọi text node tự chèn phải escape `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;`. Trước khi PUT quét raw `&` bằng `&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)`. Ưu tiên `→`/`·` thay `>`/`&` trong câu văn. Bên trong `<![CDATA[...]]>` (code/plantuml) thì literal an toàn.
