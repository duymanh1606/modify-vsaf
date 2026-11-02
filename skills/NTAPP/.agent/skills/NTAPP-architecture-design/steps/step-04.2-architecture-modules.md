# STEP 04.2: MODULAR DEEPDIVE DESIGN

> **Acting as:** [Agent C — System Architect](../agents/agent_c_system_architect.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R4 (Traceability — WBS ID xuất hiện trong Sequence/Data Flow), R5 (Consistency — tên Container khớp L2).

**Input:** `part_04.1_global_architecture.md` + `project_wbs.md` (Functional SSoT) + `part_03_tech_research.md` (nếu có) + Epics
**Output:** `part_04.2_modular_deepdive.md` — (Bao gồm: Sequence Diagrams & Bảng Data Flow chi tiết cho từng Module)

---

## MỤC TIÊU BƯỚC NÀY

Phân rã từng Module thành các thành phần nội tại, đặc tả chi tiết trình tự tương tác (Sequence) và logic xử lý (Data Flow) theo hai luồng Inbound (Ghi) và Query (Đọc) để đảm bảo tính **Traceability** tối thượng.

---

## QUY TRÌNH THỰC THI

### 3.2 Mô hình phân rã chức năng/phân hệ

> ⚠️ **CẤM sinh §3.2.0 (Function Decomposition Tree / WBS Injection) trong file này.** §3.2.0 thuộc về `project_wbs.md` (SSoT) và sẽ được Step 07 inject verbatim vào HLD final. Agent C bắt đầu output của step 04.2 từ §3.2.1.

#### 3.2.1 Mô hình tổng thể
Liệt kê danh sách các module/microservices đã xác định ở Step 04.1 (thường trình diễn kết hợp một bảng `| Module | Nhiệm vụ cốt lõi | API/Topic |`). 
Với mỗi module, tuân thủ các quy định trình bày:
- **Nhiệm vụ cốt lõi:** BẮT BUỘC phải được mô tả cực kỳ chi tiết, dễ hiểu và viết hoàn toàn bằng TIẾNG VIỆT. Cấm viết theo kiểu liệt kê gạch đầu dòng vài chữ sơ sài. Phải nêu rõ lý do module này tồn tại để cover use_case nào.
- Danh sách API cung cấp (các chiều Inbound/Outbound).
- Các Topic/Queue đang lắng nghe hoặc đẩy thông báo.

#### 3.2.2 Mô hình luồng xử lý tổng thể (Sequence/Data Flow)

**Thực hiện lặp (Loop) cho từng Module:**

##### 3.2.2.x. [Tên Phân hệ]

**A. Sequence Diagram (Nội tại Module)**
**Sử dụng Mermaid sequenceDiagram.** Mô phỏng tương tác nội bộ để xử lý một yêu cầu nghiệp vụ tiêu biểu của module này.

**B. Bảng luồng dữ liệu (Data Flow)**
Lựa chọn các bảng phù hợp dựa trên tính chất của phân hệ:

**1. Luồng Lưu dữ liệu (Inbound/Write Flow):**
| Điểm nút (Node) | Hành động kích hoạt (Trigger) | Cơ chế xử lý & Chuyển hóa dữ liệu | Đích đến tiếp theo |
| :--- | :--- | :--- | :--- |
| `[Node nội bộ]` | `[Hành động]` | `[Logic chuyển hóa: Mapping, Validation, Storage]` | `[Node tiếp theo]` |

**2. Luồng Truy vấn dữ liệu (Query/Read Flow):**
| Đối tượng gọi | Nút kiểm tra / Xác thực | Nhánh xử lý (Condition) | Nguồn cấp dữ liệu & Cơ chế trả về |
| :--- | :--- | :--- | :--- |
| `[App/Web]` | `[Token check]` | `[VD: Cache HIT / MISS]` | `[Source of Truth & Format]` |

**Quy tắc:**
- **Zero Hallucination**: Chỉ sử dụng các định danh (Identifiers) đã có trong Container Diagram (L2).
- **ERD Alignment**: Tất cả các đối tượng dữ liệu trong Sequence Diagram và tên bảng/trường trong Data Flow **BẮT BUỘC** phải tồn tại hoặc liên kết trực tiếp với thực thể trong ERD ở Step 4.1.
- **Conditional Logic**: Luồng Query BẮT BUỘC phải thể hiện các nhánh rẽ (Success/Fail hoặc Hit/Miss).

## Ghi output ra file
Ghi kết quả vào file:
- `{intermediate_folder}/part_04.2_modular_deepdive.md` — (Bao gồm: Sequence Diagrams & Bảng Data Flow chi tiết cho từng Module)

---

## ĐIỀU KIỆN TIẾP TỤC (Exit Criteria)
- [ ] Mục 3.2.1 liệt kê đủ các module từ sơ đồ Container.
- [ ] Mỗi module trọng tâm đều có đủ 2 bảng luồng dữ liệu (Inbound và Query).
- [ ] 100% các thực thể dữ liệu trong Data Flow có thể truy vết ngược về ERD tại Step 4.1.
- [ ] Không còn placeholder `[Data]` trong bảng.

---

## ⛔ [GATE — Exit Criteria] (đặt TRƯỚC Next)

Chỉ sang Step 05 khi toàn bộ Exit Criteria trên PASS (đủ module, đủ 2 bảng luồng, traceability về ERD, không placeholder).

**Next:** Read fully and follow `./step-05-implementation-security.md`
