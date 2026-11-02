---
name: NTAPP-business-overview-confluence
description: "Đóng vai Business Analyst sinh & XUẤT BẢN tài liệu Tổng quan nghiệp vụ lên Confluence theo TEMPLATE ĐỘNG (fetch template thật rồi bám khung mục), sơ đồ vẽ bằng draw.io. Nguồn: architecture_design (HLD) → project_wbs → PRD/Epics (+ code fallback); dựng Mục đích, Mô hình tổng quan, Quy trình nghiệp vụ, ERD, Trạng thái, Phân rã chức năng; dựng ERD **field-level nhóm theo datastore** (hợp nhất §11 techspec Stage 3 qua sub-agent ERD, từ điển field 2 tầng); Confluence qua MCP (đọc/tạo/body) + REST/PAT cho attachment sơ đồ. Dùng khi người dùng nói 'tạo/cập nhật tài liệu tổng quan nghiệp vụ lên Confluence', 'business overview Confluence theo template', 'vẽ ERD/quy trình/phân rã chức năng lên Confluence', 'đồng bộ tài liệu nghiệp vụ vào wiki'."
---

# HƯỚNG DẪN SKILL: BA — BUSINESS OVERVIEW → CONFLUENCE

**Version:** 2.1.0
**Mục tiêu:** Từ tài liệu thiết kế một dự án, dựng **Tài liệu Tổng quan nghiệp vụ** bám **template Confluence động**,
có **sơ đồ draw.io render được**, rồi **xuất bản** (tạo mới / cập nhật toàn bộ) đúng trang đích tra từ **bảng tổng hợp tài liệu hệ thống**.

> **Nguyên tắc no-silent-defaults:** không bịa số liệu/tên tổ chức/đối tác. Suy ra từ tài liệu → ghi kèm nguồn. Không chắc → `[Cần xác nhận]`.
> **Portability:** KHÔNG hardcode pageId / space / credential trong logic skill. Mọi giá trị đến từ tham số hoặc config (BƯỚC 0). Cùng skill chạy dự án khác chỉ đổi config.
> **Kết nối Confluence:** đọc/tạo/body qua **MCP**; **attachment sơ đồ + body-có-sơ-đồ qua REST** (`scripts/confluence-publish.ps1`, vì MCP không upload attachment được trên Server này). Chi tiết: [references/confluence-publish.md](references/confluence-publish.md).
> **Runbook chi tiết** (HITL gates + changelog continuity + **log lịch sử tác động**): [workflow.md](workflow.md). QUY TRÌNH 7 bước dưới là bản đồ tổng quát; khi EXECUTE bám workflow.md.

---

## THAM SỐ & CONFIG (BƯỚC 0 — resolve lúc runtime)

Lấy theo thứ tự: (a) tham số người dùng truyền → (b) config dự án (`docs/mcp/confluence-connections.md` / `.bo-confluence.yaml` nếu có) → (c) hỏi tương tác 1 lượt. Giá trị **đã biết** cho project reconciliation điền sẵn làm default:

| Khóa | Ý nghĩa | Default đã biết |
|---|---|---|
| `mcp_server` | Server MCP đọc/ghi trang đích | `mcp__atlassian` (host `.35`) |
| `confluence_base` | URL host chứa trang đích | `http://10.254.136.35:8090` |
| `template_page_id` | Trang **template** Tổng quan nghiệp vụ | `200745079` (space `TDOV`) |
| `target_space` | Space đích (khi tạo trang mới) | `TDOV` |
| `summary_table_page_id` | Trang chứa **bảng tổng hợp / index** tài liệu (có link + role BA) | *(resolve — hỏi/tra, đừng bịa)* |
| `ba_row_label` | Nhãn dòng cần khớp trong bảng tổng hợp | mặc định chứa `"Tổng quan"` + role `BA` |
| `auth` (REST) | Cho attachment/publish | `.confluence-auth` (PAT) ở repo root — xem confluence-publish.md §1 |

Bảng tổng hợp có thể ở host khác trang đích (link trong bảng trỏ instance nào thì cập nhật trang ở đó). MCP `.32` hay chết token (403) → đọc fallback bằng `scripts/confluence-get.ps1` (Basic).

---

## QUY TRÌNH 7 BƯỚC

### BƯỚC 1 — Thu thập nguồn đầu vào (im lặng)
Đọc theo thứ tự ưu tiên, dừng khi đủ tín hiệu:
1. `**/architecture_design.md`** (HLD) — C4 context/container, ERD (§ Global Data Model), security zoning, NFR. Nguồn chính cho **Mô hình tổng quan** + **ERD**.
2. `**/project_wbs.md`** — **xương sống Phân rã chức năng toàn hệ** (§6 bám cái này). Mọi loại ID: features/screens/widgets/contracts.
3. **PRD & Epics** (`**/Stage_1_Discovery/prd.md`, `epics.md`) — bối cảnh, vấn đề, mục tiêu kinh doanh (phần code/thiết kế không nói).
4. (fallback) **Source code** — suy actor/flow/ERD khi tài liệu thiếu. Cách trích: [references/extract-from-code.md](references/extract-from-code.md).
5. **Stage 3 techspec §11** (`NTAPP-output/Stage_3_Specs/techspec/*_techspec.md`) — nguồn field-level cho ERD; hợp nhất qua Bước 1b (sub-agent `agent_erd_data_architect`). Loại `integration-*` + `observability`.
6. (tùy chọn, chỉ khi tách phần xây mới) `**/Stage_4_Design/**/feature_design_parts/*/`** — mỗi thư mục con = 1 feature xây mới thật.

> **Phân biệt phạm vi:** WBS TRỘN brownfield AS-IS + phần xây mới. Xem [references/scope-brownfield-vs-newbuild.md](references/scope-brownfield-vs-newbuild.md).
> **Bước 1b (hợp nhất ERD field-level):** sau khi thu thập nguồn, chạy sub-agent `agent_erd_data_architect` hợp nhất §11 kỹ thuật của tất cả techspec thành từ điển field 2 tầng theo datastore. Chi tiết: [workflow.md](workflow.md) §1b.

### BƯỚC 2 — Hỏi phạm vi (HITL, 1 lượt)
Hỏi người dùng chọn (mặc định = đầu tiên):
- **Toàn hệ theo WBS** — bức tranh đầy đủ, cây §6 dựng từ `project_wbs.md`, không phân lớp AS-IS/mới.
- **Toàn hệ 2 lớp** — thêm tách nhánh A (brownfield, xám) + B (xây mới, màu, từ `feature_design_parts`).
- **Chỉ phần xây mới** — chỉ feature trong `feature_design_parts`.
Kèm hỏi nhanh bối cảnh/mục tiêu kinh doanh còn thiếu (nếu PRD không đủ).

### BƯỚC 3 — Fetch template ĐỘNG + lấy bộ mục
- MCP `confluence_get_page(page_id=template_page_id, convert_to_markdown=false)` → storage XHTML thô. (MCP host chết → `scripts/confluence-get.ps1`.)
- **Parse các heading `<h1>`** làm bộ mục chuẩn (số lượng/tiêu đề bám template, KHÔNG cứng hoá). Đọc mô tả trong mỗi mục để biết yêu cầu trình bày (vd "bố cục theo vùng", "swimlane", "cây building-block 3 loại", cột bảng).
- ⚠️ **Template chứa nội dung ví dụ dự án khác** (vd VOUCHER_*, App VTP). Coi template là **khung mục + hướng dẫn**; **thay toàn bộ data ví dụ** bằng dữ liệu reconciliation thật. Giữ lại cấu trúc: bảng Đơn vị phê duyệt (task-list), macro `toc`, bảng ghi nhận thay đổi.
- Quy ước mặc định nếu template không nói rõ: [references/style-conventions.md](references/style-conventions.md).

### BƯỚC 4 — Dò plugin sơ đồ → xác nhận draw.io render
- MCP `confluence_search(query='macro="drawio"')` + đọc `body.view` **vài** trang thật dùng macro: có `unknown-macro?name=drawio` → plugin chưa cài. **Rỗng ≠ chưa cài** (chỉ nghĩa chưa ai dùng) → probe chủ động: tạo 1 trang nháp có macro, đọc `body.view`, rồi xoá.
- Host `.35` đã biết **có draw.io** (SEIBERT) → dùng draw.io. Chi tiết render + `revision`: [references/diagram-drawio.md](references/diagram-drawio.md).

### BƯỚC 5 — Sinh nội dung từng mục (storage format)
Bám thứ tự mục template. **Văn phong nghiệp vụ chuyên nghiệp — KHÔNG văn nói** ("Dễ hiểu", "Tóm lại", "bóc tách", "làm được gì", "chạy ngầm"…) và **KHÔNG in khối meta** nói về cách làm tài liệu (hộp phạm vi/tiêu chí chọn nội dung · bảng giải nghĩa loại lá · hộp đối chiếu số lượng · hộp "Điểm cần xác nhận" gom cụm). Bảng đối chiếu từ ngữ + blocklist đầy đủ: [references/style-conventions.md](references/style-conventions.md) **§0 — đọc TRƯỚC khi viết**. Quy ước từng mục:
- **Mô hình tổng quan:** bố cục **vùng trái→phải** (Nguồn dữ liệu · Lõi + bước xử lý/kho dữ liệu · Tích hợp · FE · Actor); actor người que; hệ ngoài xám nét đứt; **ít mũi tên** (chiều in→xử lý→out); bảng `STT | Tên thành phần | Mô tả`.
- **Quy trình nghiệp vụ:** tùy chọn **1 câu** nêu phạm vi + đầu vào/đầu ra (**không dùng hộp tip**) + sơ đồ **swimlane/3 cột** + bảng bước **5 cột** `STT | Bước | Vai trò thực hiện | Mô tả·Điều kiện·Dữ liệu | Bước tiếp theo`.
- **ERD:** **2 tầng** — Tầng A: sơ đồ cross-store rút gọn (entity thu gọn + FK bắc cầu giữa các datastore) + bảng `Bảng nguồn | Khoá | Bảng đích | Store↔Store | Nguồn`; Tầng B: mỗi cụm datastore 1 sơ đồ bảng lưới 1:N nội cụm + bảng tổng hợp `STT | Tên bảng | Ý nghĩa | Nguồn` + **expand lồng** từng bảng ra từ điển field 2 tầng (nghiệp vụ + kỹ thuật); tên bảng/trường = **tên DB thật**; nguồn hợp nhất từ Bước 1b, xem [references/erd-consolidation.md](references/erd-consolidation.md).
- **Trạng thái:** state diagram cho thực thể có vòng đời; xếp `states` theo thứ tự vòng đời thuận (trạng thái kết thúc bất thường để cuối) để phần lớn chuyển tiếp là liền kề.
- **Phân rã chức năng:** cây building-block **3 loại** (Frontend · Backend-kết nối · Backend-xử lý tự động); full-system → 2 lớp; **ĐÚNG 1 bảng** khớp **từng lá** `STT | Kênh thực hiện | Đối tượng sử dụng | Chức năng | Ý nghĩa` — không bảng giải nghĩa loại lá, không hộp đối chiếu số lượng. Quá ~40 lá / 6 cụm → tách nhiều sơ đồ theo cụm.

Storage XHTML: **escape `& < > "`** ngoài CDATA; **checkbox = `ac:task-list`** (không unicode ☑); **ngày = date macro**; bảng lồng OK; **HTML macro tắt** trên `.35`. Xem [references/confluence-publish.md](references/confluence-publish.md) §2–§4.
- **Changelog continuity (UPDATE):** đọc bản live lấy version + bảng "Ghi nhận thay đổi" cũ → **giữ dòng cũ**, thêm 1 dòng mới trên đầu, bump version doc +1. Lần đầu → `v1`. Chi tiết: [workflow.md](workflow.md) §4.

### BƯỚC 6 — Sinh sơ đồ + xuất bản
1. Xác định trang đích: tra `summary_table_page_id` tìm dòng khớp `ba_row_label` (role BA / "Tổng quan nghiệp vụ") → lấy link.
   - **Chưa có link** → MCP `confluence_create_page(content_format="storage")` tạo skeleton trong `target_space` → lấy `pageId`; sau publish xong cập nhật ô link trong bảng.
   - **Đã có** → cập nhật **toàn bộ** trang đó (Confluence giữ lịch sử version).
2. Sinh mxfile từng sơ đồ bằng `scripts/drawio_lib.py` → ghi file (tên = `diagramName`, không đuôi).
2b. **Soi sơ đồ:** `python scripts/preview.py <tất cả mxfile>` → mở PNG xem từng cái + đọc cảnh báo lint. Còn cảnh báo (mũi tên chồng/xuyên hộp, trang quá rộng) → **sửa data/tách sơ đồ rồi sinh lại**, không publish hình lỗi.
3. Ghi storage ra `*.storage.xhtml` + `confluence-publish.manifest.json` (pageId, title, storageFile, attachments: mxfile `label drawio` + PNG nếu có).
4. **Publish** `powershell -File scripts/confluence-publish.ps1 -Manifest <manifest.json>` → upload attachment + **auto-sync `revision`==attachment version** + PUT body version+1 (atomic).
   - Body-only, KHÔNG sơ đồ (vd cập nhật ô link bảng tổng hợp) → có thể đi MCP `confluence_update_page(content_format="storage")`.

### BƯỚC 7 — Write-back, LOG & báo cáo
- **Verify:** MCP `get_page` / `get_attachments`: **không còn `unknown-macro`**; **version attachment mxfile == `revision` macro** (điều kiện sống còn — không 404, không kẹt render cũ); số dòng bảng/sơ đồ khớp.
- **Write-back:** cập nhật ô link trong bảng index (dòng role BA) trỏ tới URL trang — body-only qua MCP.
- **Log lịch sử tác động:** ghi audit `{bo_dir}/.confluence-sync/{timestamp}.log` + append `{bo_dir}/business-overview-publish-history.md` (`Ngày | Action | Phạm vi | pageId | Version | URL | Người`). Chi tiết: [workflow.md](workflow.md) §10.
- **Báo:** URL trang, version mới, danh sách sơ đồ + attachment, các điểm `[Cần xác nhận]`, đường dẫn log. Nhắc user hard-refresh (Ctrl+F5).

---

## SCRIPTS KÈM THEO (portable — nhận tham số, không hardcode)
- [scripts/drawio_lib.py](scripts/drawio_lib.py) — sinh mxfile: `overview_zones` (mô hình tổng quan bố cục vùng) · `process_3col` (quy trình) · **`erd_graph`** (ERD mức bảng — phân tầng + định tuyến qua kênh/máng, dùng cho sơ đồ quan hệ) · `erd` (lưới field-level) · `state_diagram` · `breakdown_tree`.
- [scripts/preview.py](scripts/preview.py) — **render mxfile ra PNG để SOI + lint hình học** (hộp đè hộp · cạnh xuyên hộp · 2 cạnh chồng trục · tràn khổ · trang quá rộng). **BẮT BUỘC chạy sau khi sinh mxfile, trước preview HITL** — không có bước này thì không ai nhìn thấy sơ đồ trước khi nó lên wiki. `python scripts/preview.py <mxfile...> [-o OUT] [--strict]`; exit 2 = thiếu Chrome, chỉ mất ảnh, KHÔNG chặn publish.
- [scripts/confluence-publish.ps1](scripts/confluence-publish.ps1) — upload attachment (REST multipart) + PUT body version+1 + **auto-sync drawio `revision`**; đọc PAT từ `.confluence-auth` (walk-up). Agent tự chạy, user không gõ lệnh.
- [scripts/confluence-get.ps1](scripts/confluence-get.ps1) — đọc trang qua REST Basic (fallback khi MCP host chết / cần đọc host khác).

## RUNBOOK & REFERENCES
- [workflow.md](workflow.md) — **runbook thực thi** 10 bước: INIT+pre-flight · sources · scope HITL · template động · gen+changelog continuity · review · locate · preview HITL · execute · write-back+**LOG lịch sử**. Sơ đồ quyết định cuối file.
- [references/confluence-publish.md](references/confluence-publish.md) — cơ chế MCP+REST, auth, storage format, task-list checkbox, date macro, escaping, draw.io macro + revision auto-sync, quy trình publish an toàn.
- [references/diagram-drawio.md](references/diagram-drawio.md) — cấu trúc mxfile, render trên `.35`, `revision`==version, edge routing.
- [references/style-conventions.md](references/style-conventions.md) — quy ước trình bày từng mục (canh theo template thật).
- [references/scope-brownfield-vs-newbuild.md](references/scope-brownfield-vs-newbuild.md) — nguồn arch→WBS→PRD, phân biệt phạm vi toàn hệ vs xây mới.
- [references/extract-from-code.md](references/extract-from-code.md) — bảng trích actor/ERD/flow/state từ source code (fallback).
- [agents/agent_erd_data_architect.md](agents/agent_erd_data_architect.md) — sub-agent hợp nhất ERD field-level từ Stage 3 §11.
- [references/erd-consolidation.md](references/erd-consolidation.md) — quy tắc nhóm store, 2 tầng, cross-store bridge, no-fabrication.
