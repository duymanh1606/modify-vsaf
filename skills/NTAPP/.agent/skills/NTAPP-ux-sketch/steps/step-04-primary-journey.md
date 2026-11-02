# STEP 04: PRIMARY USER JOURNEY (§4)

> **Thực hiện bởi:** Agent UXS0 (UX Sketch Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R2 (Screen Fidelity relaxed), R3, R4**.

## 1. Mục tiêu

Mô tả 1-2 luồng user journey chính: Mermaid sequence + Screen Intent Table (3-5 screen) cho mỗi luồng. Đây là phần forcing function chính của sketch — buộc thinking về tương tác user-system chi tiết, và là input để Step 05 render preview hi-fi.

## 2. Đầu vào

- §2 Personas (Step 02) — biết actor + goals
- §3 Rough IA (Step 03) — biết navigation context
- PRD: detailed user flow descriptions
- Epics: user stories with acceptance criteria

## 3. Chỉ thị thực thi

### 3.1. Chọn 1-2 luồng chính

Tiêu chí "primary journey":
- Luồng critical nhất (vd onboarding cho new user, transaction flow chính)
- Có ≥ 1 Epic dedicated trong Epics document
- Touchpoint với ≥ 2 personas hoặc cross-system

Nếu PRD có > 2 luồng critical → ưu tiên 2 luồng:
1. **Onboarding / first-time use** (high value cho HLD design)
2. **Core daily transaction** (high value cho ongoing UX)

KHÔNG cố gắng cover edge cases / secondary flows ở sketch — đó là việc của Master UX Spec ở Stage 3b.

### 3.2. Cho mỗi journey, generate

#### a. Mermaid Sequence Diagram (rough)

```mermaid
sequenceDiagram
    participant {Actor}
    participant System
    
    {Actor}->>System: Step 1 — {action}
    System-->>{Actor}: Show {response}
    ...
```

**Rough means:**
- Chỉ 2-3 participant (Actor + System hoặc Actor + System + ExternalService).
- KHÔNG cần protocol detail (REST/Kafka/JWT...).
- Mỗi step trace về Epic/Story ID.

#### b. Screen Intent Table (3-5 screen / journey)

**KHÔNG vẽ ASCII wireframe.** Bố cục được diễn đạt bằng bảng structured — đây là input máy-đọc-được để Step 05 render **preview hi-fi** (frame thật bằng component + token của product). Một nguồn duy nhất: bảng này. *(v1 dùng ASCII + preview lo-fi → 2 bản wireframe lệch nhau mỗi vòng feedback; xem [step-05](./step-05-validation.md) §3.1b.)*

| Screen | Role | Content blocks | Primary CTA | Branch | Trace |
|:--|:--|:--|:--|:--|:--|
| Compose Message | form | `Form: recipient, message body`, `Card: cost estimate` | `Send` | validation fail → inline error dưới field | Epic E-02 / Story S-04 |
| Review & Confirm | review | `Summary card: recipient + body`, `Table: fee breakdown` | `Confirm` | quota exceeded → chặn, hiện upgrade prompt | Epic E-02 / Story S-05 |

**Yêu cầu từng cột:**

| Cột | Yêu cầu |
|:--|:--|
| **Screen** | Identifier ổn định, trace được về 1 step trong Mermaid sequence. Đây là nguồn của `{screen_slug}` (kebab-case) — anchor preview + Preview Index step-06 đều theo nó, nên **đổi tên là đổi anchor**. |
| **Role** | 1 từ quyết định vốn component khi render: `form` / `list` / `table` / `dashboard` / `review` / `detail` / `wizard-step` / `empty`. |
| **Content blocks** | `Kind: nội dung` cách nhau bằng dấu phẩy — `Form:` / `Table:` / `List:` / `Card:` / `Editor:` / `Widget:` / `Filter:`. Kèm field/column chính (vd `Table: mã đơn, trạng thái, ngày tạo`) để frame render ra dữ liệu đúng kiểu. |
| **Primary CTA** | Label control user click để sang step tiếp (hoặc kết thúc journey) — đúng chữ hiển thị. |
| **Branch** | `trigger → hệ quả` nếu screen có conditional flow (validation fail, role check, dependency). Không có → `—`. |
| **Trace** | ≥ 1 Epic ID hoặc Story ID (R4). |

**Rough means (R2 relaxed):**
- ✅ Đủ: screen identifier + content blocks + CTA + branch + trace.
- ❌ KHÔNG cần: layout grid / tỉ lệ chính xác, mapping component DS (chưa audit — Stage 4b own), interaction state đầy đủ, copywriting chuẩn.
- Preview hi-fi ở Step 05 trông như sản phẩm thật, nhưng vẫn là **v0 intent** — không phải visual đã approve.

**Trace:** Mỗi row phải tương ứng ≥ 1 step trong Mermaid sequence + ≥ 1 Epic/Story ID.

### 3.3. Save into part file

Append §4 vào `{intermediate_folder}/uxs0_journey_part.md` (file đã tạo ở Step 03 với §3 IA).

## 4. Đầu ra yêu cầu

- **Lưu trữ:** Append `{intermediate_folder}/uxs0_journey_part.md` (§3 + §4 cùng file)
- Nội dung: 1-2 journey, mỗi journey có Mermaid sequence + Screen Intent Table 3-5 row
- Báo cáo: "§4 Primary Journey hoàn tất. X journey, Y screen (Screen Intent rows), Z trace points đến Epic/Story."

## NEXT
[step-05-validation.md](./step-05-validation.md)
