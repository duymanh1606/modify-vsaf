# CHUẨN ĐẶC TẢ CHI TIẾT (MASTER DETAILED DESIGN - L3) - [AI Agent: Điền Tên Chức Năng]

*Tài liệu này là Master Template (v4) hợp nhất đặc tả (Full-stack) cho một tính năng. Cấu trúc chia vùng (Zoning) nghiêm ngặt để các Frontend Agent và Backend Agent có thể thực thi chính xác phần việc của mình.*

<!-- QUY ƯỚC OKF: dòng bắt đầu bằng "okf-id:" ngay dưới mỗi heading H2 là ĐỊNH DANH
     ỔN ĐỊNH của mục đó trong đồ thị OKF. Đổi tiêu đề thì GIỮ NGUYÊN marker. Xoá marker
     thì danh tính tụt về slug của tiêu đề, và mọi cạnh trỏ tới mục này sẽ đứt lặng lẽ
     ngay lần đầu ai đó sửa câu chữ của tiêu đề. -->


---

## BẢNG LỊCH SỬ THAY ĐỔI
<!-- okf-id: change-log -->
`[AI Agent: Trích xuất lịch sử cập nhật. Giữ nguyên 100% version, vị trí thay đổi và mô tả.]`

| Ngày thay đổi | Vị trí thay đổi | A*, M, D | Nguồn gốc | Link CR/Jira | Mô tả thay đổi | Phiên bản |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `[Data]` | `[Data]` | `[Data]` | `[Data]` | `[Data]` | `[Data]` | `[Data]` |

*(A - Tạo mới, M - Sửa đổi, D - Xóa bỏ)*

---

## 1. TỔNG QUAN & RANH GIỚI (OVERVIEW & SCOPE)
<!-- okf-id: overview-scope -->
`[AI Agent: BẮT BUỘC cung cấp context tổng quan cho tính năng.]`

| Tiêu chí | Nội dung / Tham chiếu |
| :--- | :--- |
| **Parent TechSpec (L2)** | `[Link tới file TechSpec của Module/Service]` |
| **WBS ID** | `[vd: FEA-01]` |
| **Mục đích** | `[Mục tiêu nghiệp vụ của tính năng này]` |
| **Loại chức năng** | `[Web App / Mobile App / API Job / Background Worker]` |
| **Pre-condition** | `[Điều kiện tiên quyết trước khi thực thi tính năng (VD: Đã login, Có token...)]` |
| **Post-condition** | `[Trạng thái hệ thống/Dữ liệu sau khi thực thi (VD: Record sinh ra, trạng thái chuyển X...)]` |

---

## 2. ĐẶC TẢ GIAO DIỆN & TƯƠNG TÁC (FRONTEND / UI WORKSPACE)
<!-- okf-id: ui-workspace -->
`[Chỉ thị Frontend Agent: Đây là vùng thiết kế khung xương và đặc tả kỹ thuật của Frontend agent. Backend agent bỏ qua. Nhiệm vụ là đề xuất cấu trúc thông tin và lập bảng đặc tả controls chi tiết.]` 
`[Lưu ý: Nếu Loại chức năng là API Server-to-Server hoặc Job ngầm, ghi "N/A" cho toàn bộ mục 2.]`

### 2.1. Kiến trúc thông tin & Điều hướng (IA & Navigation)
`[AI Agent: Mô tả vị trí tính năng trong sơ đồ trang và phân cấp thông tin (Hierarchy) trên màn hình.]`

### 2.2. Bản vẽ khung xương (Wireframe Blueprint)
`[AI Agent: BẮT BUỘC sử dụng ASCII Art (Code block "text") để mô tả khung xương/bố cục màn hình. CẤM sử dụng Mermaid cho Wireframe tại đây. Đảm bảo thể hiện rõ: Header, Content, Sidebars, các Action zones,etc.]`

`[AI Agent — Annotation conventions (BẮT BUỘC):]`
`[(a) Control ID: mỗi control phải có [control_id] (snake_case, khớp cột "Tên control" §2.3). Vd: [input_name], [button_search].]`
`[(b) Emoji = visual hint. Mỗi emoji kèm annotation 🔍[icon-name] (kebab-case, semantic intent — KHÔNG phải tên component lib). Emoji là UI content thực (chat body, emoji picker) prefix 'content:' vd 🎉[content:celebration].]`
`[(c) Sau wireframe BẮT BUỘC kèm: Icon Legend (nếu ≥1 emoji) + Layout Groups (nếu ≥2 sibling controls).]`

**Ví dụ tham khảo:**
```text
+-----------------------------------------------------------+
| [LOGO]              NAV BAR (Home | [input_search 🔍[search]] | [link_profile]) |
+-----------------------------------------------------------+
| SIDEBAR      |                                            |
| - Menu 1     |           MAIN CONTENT AREA                |
| - Menu 2     |                                            |
| - Menu 3     |   [button_create + Tạo mới]  [select_filter ⬇[chevron-down]] |
|              |                                            |
|              |   +------------------------------------+   |
|              |   |       DATA TABLE / FORM            |   |
|              |   |   [button_close_row ✖[close]]      |   |
|              |   +------------------------------------+   |
+-----------------------------------------------------------+
```

**Icon Legend:** (bắt buộc nếu wireframe có ≥1 emoji)

| Emoji | Icon name | Mục đích |
| :--- | :--- | :--- |
| 🔍 | search | Trigger global search bar |
| ⬇ | chevron-down | Expand dropdown filter |
| ✖ | close | Đóng modal / dialog / row detail |

> Bảng Icon Legend là **machine-readable contract** cho Stage 4b `ui_schema_agent` — agent này sẽ map `Icon name` (semantic intent) sang component cụ thể của icon library trong stack (vd `lucide-react → Search`, `@ant-design/icons → SearchOutlined`, `primeicons → pi pi-search`). Stage 5 dev agent KHÔNG được copy emoji glyph sang code — phải đọc icon từ `ui_schema_{id}.json` (key `icon_bindings`).

**Layout Groups:** (bắt buộc nếu wireframe có ≥2 sibling controls hoặc form multi-field)

| Group ID | Type | Members | Props |
| :--- | :--- | :--- | :--- |
| R1 | Sidebar | sidebar_menu, G_main | side=start, side_width=sidebar.md, gap=md |
| G_main | Stack | G_nav, G_actions, G_content | direction=column, gap=lg |
| G_nav | Stack | logo, input_search, link_profile | direction=row, align=center, gap=md, justify=between |
| G_actions | Cluster | button_create, select_filter | gap=sm, align=center |
| G_content | Stack | data_table, button_close_row | direction=column, gap=md |

> Bảng Layout Groups là **machine-readable contract** cho Stage 4b — `ui_schema_agent` build `layout` tree refer tới control IDs từ §2.3. Type chọn từ inventory 10 canonical primitives (xem `_shared/component-metadata-schema.md` §12). Stage 5 dev render UI bằng primitive components (đã materialize bởi `/ntapp-ds-build-component` theo `stack-profile.layout_library`) — KHÔNG tự viết wrapper `<div style="display:flex">`.

### 2.3. Đặc tả UI Controls
`[AI Agent: ĐÂY LÀ PHẦN CỐT LÕI CHO FRONT-END. Lập bảng liệt kê 100% các thành phần UI (Controls). MỨC ĐỘ CHI TIẾT: High-Fidelity. Với mỗi control, AI Agent phải cung cấp mô tả nghiệp vụ sâu, danh sách giá trị (nếu có). Bắt buộc cung cấp bảng VALIDATION PHỤ lồng bên trong mỗi control. Cột "DS candidate": tên component có sẵn trong component_catalog.md khớp control này (non-binding hint cho Stage 4b reuse audit — match hiển nhiên mới điền, không chắc để "-"; KHÔNG bịa tên ngoài catalog).]`

| Tên control | Loại control | DS candidate | Max length | Require (Y/N) | Giá trị mặc định | Mô tả chi tiết (Business Rules & Validations) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `[Số - Tên]` | `[Combobox / Textbox / ...]` | `[tên component từ catalog / "-"]` | `[Int / N/A]` | `[Y / N]` | `[Text/Null]` | `[1. Mục tiêu: ...]` <br> `[2. Danh sách value: (nếu có)]` <br> `[3. Bảng Validation:]` <br> <table><tr><th>Action</th><th>Trường hợp</th><th>Thông báo lỗi inline (Nguyên văn)</th></tr><tr><td>`[Action]`</td><td>`[Case]`</td><td>`["Lỗi..."]`</td></tr></table> |

---

## 3. ĐẶC TẢ LOGIC THỰC THI (BACKEND / LOGIC WORKSPACE)
<!-- okf-id: logic-workspace -->
`[Chỉ thị Backend Agent: Đây là vùng làm việc của bạn. Chỉ tập trung vào cách luồng dữ liệu di chuyển, logic thuật toán và rẽ nhánh. Không xử lý giao diện.]`

### 3.1. Sơ đồ trình tự tính năng (Feature Sequence Diagram)
`[AI Agent: BẮT BUỘC dùng Mermaid SequenceDiagram để mô phỏng tương tác nội bộ của API/Module này.]`
```mermaid
sequenceDiagram
    %% Agent: Điền mã Mermaid tại đây
```

### 3.2. Giải thuật Step-by-Step (Logic Matrix)
`[AI Agent: Phân rã logic thuật toán nội bộ từ A->Z (Validate -> Tính toán -> Tích hợp -> Trả kết quả). Bảng IF-ELSE chi tiết.]`

| Bước | Thành phần / Module xử lý | Logic xử lý nội bộ & Quy tắc nghiệp vụ | Điều kiện Rẽ nhánh (IF-ELSE, Nhánh Thành Công / Thất Bại) |
| :--- | :--- | :--- | :--- |
| `[B]` | `[Tên Controller/Service]` | `[Logic chính thức cần xử lý]` | `[Các luồng Unhappy Paths, Exception, Error handling]` |

---

## 4. ĐẶC TẢ DỮ LIỆU & TÍCH HỢP (DATA & INTEGRATION)
<!-- okf-id: data-integration -->
`[Chỉ thị: Dành cho cả BE và FE để quy chuẩn định dạng truyền nhận dữ liệu.]`

### 4.1. Bảng Mapping Field Dữ liệu (UI <-> DB)
| Tên Field hiển thị (UI) / API Param | Kiểu Dữ Liệu | Mapping Database Table & Column | Ghi chú (Mã hóa, Format...) |
| :--- | :--- | :--- | :--- |
| `[Field]` | `[Type]` | `[Table.Field]` | `[Note]` |

### 4.2. Danh sách Schema & Integration Error Codes
`[AI Agent: Hệ thống mã lỗi tích hợp với các phân hệ khác hoặc đối tác (Partner Code).]`

| Tên Integration (Hoặc API gọi ra) | HTTP/gRPC Status | Trạng thái (Trường hợp) | Trả về (Mã Lỗi / Code) | Diễn giải lỗi nội bộ |
| :--- | :--- | :--- | :--- | :--- |
| `[VD: Gọi API Thanh toán]` | `[500/400]` | `[Khách hết hạn mức]` | `[E_PAY_01]` | `[Xử lý cho FE hiểu để show UI]` |

### 4.3. Đặc tả Ghi dữ liệu theo Unit (Persistence Write-Spec)
`[Chỉ thị: Áp dụng cho unit CÓ ghi dữ liệu (BE feature / widget own-state). FE consume thuần → ghi "N/A".]`
`[AI Agent: Với MỖI thao tác ghi (INSERT/UPDATE/DELETE) mà unit thực hiện, đặc tả ở mức FIELD — bảng nào, cột nào, ghi giá trị/biểu thức gì, giá trị lấy từ đâu. BẮT BUỘC liệt kê cả field hệ thống tự gán không có nguồn từ UI (vd `status`, `created_at`, FK lấy từ context/session). Giá trị ghi phải khớp đặc tả, không tự suy diễn.]`

| Unit / Thao tác | Bảng | Op | Cột | Giá trị / Biểu thức ghi | Nguồn giá trị | Điều kiện áp dụng |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `[VD: OrderService.create]` | `[orders]` | `[INSERT]` | `[status]` | `["init"]` | `[Hằng số]` | `[Luôn]` |
| `[" (cùng thao tác)]` | `[orders]` | `[INSERT]` | `[created_at]` | `[now()]` | `[System]` | `[Luôn]` |
| `[" (cùng thao tác)]` | `[orders]` | `[INSERT]` | `[user_id]` | `[ctx.userId]` | `[Context/Session]` | `[Luôn]` |
| `[" (cùng thao tác)]` | `[orders]` | `[INSERT]` | `[amount]` | `[req.body.amount]` | `[Request/Input]` | `[Luôn]` |

`[Nguồn giá trị — enum chuẩn: Request/Input · Hằng số · Tính toán (computed) · Query/Lookup · Context/Session · System (now()/uuid/seq).]`

---

## 5. ĐẢM BẢO CHẤT LƯỢNG (QUALITY ASSURANCE & TEST PROTOCOL)
<!-- okf-id: quality-assurance -->
`[Chỉ thị QA Agent: Đây là vùng thực thi của bạn. Sử dụng tài liệu SRS/DD làm đầu vào để xây dựng bộ kịch bản kiểm thử (KBKT) toàn diện.]`

### 5.1. Impact Analysis (Phân tích ảnh hưởng)
`[AI Agent: Xác định các phân hệ bị tác động để khoanh vùng Regression Test.]`

| Chức năng ảnh hưởng | Mức độ | Lý do / Nội dung chi tiết |
| :--- | :--- | :--- |
| `[Tên chức năng]` | `[H/M/L]` | `[Mô tả thay đổi logic/dữ liệu]` |

### 5.2. Kịch bản kiểm thử chi tiết (Detailed Test Scenarios - KBKT)
`[AI Agent: Áp dụng các kỹ thuật (Phân vùng tương đương, Giá trị biên, Bảng quyết định) để bao phủ 100% các luồng/nhánh trong DD. Cột "Kết quả mong muốn" phải đáp ứng đủ UI, Logic và DB state sau ghi (theo §4.3). Dữ liệu cột "Data Test" kế thừa Exact Sample Data từ F2 — không tự bịa.]`
`[KHÔNG đặc tả ở đây: quy trình review, setup môi trường/công cụ, log defect, theo dõi Pass/Fail.]`

| ID | Mục đích kiểm thử | Trường hợp kiểm thử | Data Test | Các bước thực hiện | Kết quả mong muốn (UI, DB, Log) | Độ ưu tiên |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `[KB-01]` | `[Mục đích]` | `[Hành vi]` | `[Dữ liệu]` | `[1, 2, 3...]` | `[Kỳ vọng: UI + DB state + Log]` | `[P0/P1]` |

---

## 6. MA TRẬN ĐỒNG BỘ FE-BE (INTERACTION SYNC MATRIX)
<!-- okf-id: sync-matrix -->
`[Chỉ thị Orchestrator/Auditor Agent: Đây là chốt chặn cuối cùng để kiểm tra tính khép kín của thiết kế.]`
`[Mục tiêu: Đảm bảo mọi trường hợp logic ở BE đều có phương án hiển thị ở FE và ngược lại.]`

| Case ID | Hành động từ FE (Trigger/Input) | Xử lý tại BE (Business Logic) | Dữ liệu / Trạng thái BE trả về | UI Hiển thị tương ứng (Output/Response) | KBKT ID (Tham chiếu Mục 5.2) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[ID]` | `[User làm gì?]` | `[Hệ thống kiểm tra/xử lý gì?]` | `[Mã lỗi hoặc Dữ liệu trả về]` | `[Màn hình hiện gì, Toast báo gì?]` | `[KB-xx]` |

`[AI Agent Checklist:]`
- [ ] 100% các mã lỗi ở mục 4.2 đã có Case ID tương ứng ở bảng này chưa?
- [ ] **Write-Spec Coverage:** 100% thao tác ghi ở mục 4.3 đã có ít nhất 1 KBKT (mục 5.2) kiểm chứng trạng thái DB sau ghi chưa?
- [ ] 100% các bước Logic Matrix ở mục 3.2 đã được map với hành động UI ở phần mô tả chưa?
- [ ] Có Case nào BE trả về dữ liệu mà FE chưa có Wireframe/Control để hiển thị không?
- [ ] **Traceability Check:** 100% các Case ID ở bảng này đã được ánh xạ tới ít nhất một KBKT ID ở mục 5.2 chưa?
