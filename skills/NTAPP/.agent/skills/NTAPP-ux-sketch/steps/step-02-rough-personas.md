# STEP 02: ROUGH PERSONAS (§2)

> **Thực hiện bởi:** Agent UXS1 (Research Analyst — Mary)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R3, R4, R10**.

## 1. Mục tiêu

Tạo 2-3 personas **rough** từ PRD/Epics actors. Lightweight — chỉ name + role + top 3 pain + top 3 goals. KHÔNG cần behavioral pattern detail / day-in-life narrative / demographic.

## 2. Đầu vào

- PRD: actor list, problem statement, user pain points hints
- Epics: user stories ("As a X, I want Y, so that Z")
- Briefing từ Step 01

## 3. Chỉ thị thực thi

### 3.1. Identify Personas (2-3 max)

Từ PRD/Epics extract distinct user types:
- Mỗi persona = 1 actor role distinct trong PRD.
- Nếu PRD có > 3 actors → chọn 2-3 critical nhất (theo frequency của actor reference trong Epics).
- Tránh: tạo persona không có trong PRD (vi phạm R3 + R10).

### 3.2. Cho mỗi persona, fill template

| Field | Source |
|:--|:--|
| **Name** | Tự đặt (vd "Anna - Merchant Operations") — nhớ trace về role thực |
| **Role** | Từ PRD §X actor list |
| **Trace to PRD actor** | Cite cụ thể PRD §X — "{{actor_name}}" |
| **Top 3 Pain Points** | Từ PRD problem statement + Epics user stories ("I want X" → pain implied) |
| **Top 3 Goals** | Từ Epics user stories ("so that Z") |

### 3.3. Validation per persona

Trước khi save:
- [ ] Trace về PRD actor cụ thể (KHÔNG phải bịa).
- [ ] Pain points đều có evidence trong PRD/Epics (KHÔNG phải general assumption).
- [ ] Goals đều có ≥ 1 Epic/Story tương ứng.

Nếu thông tin chưa đủ → đánh dấu `[TBD - cần PM/BA confirm]` (R3).

## 4. Đầu ra yêu cầu

- **Lưu trữ:** `{intermediate_folder}/uxs1_personas_part.md`
- Nội dung: 2-3 personas theo format template §2
- Báo cáo: "§2 Rough Personas hoàn tất. X personas, trace về Y actors, bao phủ Z user stories từ Epics."

## NEXT
[step-03-rough-ia.md](./step-03-rough-ia.md)
