# Layout & Composition Best Practices

**Schema version:** 1.0
**Type:** Rules library cho wireframe composition (structure-time)
**Twin của:** `best-practices.md` (token/visual). File này = **cấu trúc/bố cục**, KHÔNG trend.
**Used by:**
- `/ntapp-ux-design` step-09/step-10 + iron_rules R6 gate "Layout Best-Practice Compliance" — audit **journey/IA-level** (L5/L6/L9)
- `/ntapp-feature-design` step-02 §2.2 + iron_rules R6 gate "Wireframe Composition Audit" — audit **per-unit composition** (L1-L4/L7/L8/L10/L11)

---

## 1. Mục đích

Encoding best-practice **cấu trúc & bố cục** của wireframe: single primary action, mandatory states, field grouping, density, progressive disclosure, reading order, destructive separation, form linearity, IA depth, affordance, consistency. Rule dùng để **propose/warn** khi wireframe vi phạm, KHÔNG auto-rewrite. Owner gate (UX0 / Agent F0) duyệt từng case.

> **Phân tách rõ với `best-practices.md`:** file này KHÔNG đụng token/màu/spacing px/elevation (= visual, đổi theo trend → đó là `best-practices.md` + `aesthetic-rubric.md`). File này chỉ đo được trên **cấu trúc** ASCII wireframe / Layout Groups / Control table — durable 5-10 năm, deterministic.

## 2. Triết lý

> **"Detect existing pattern trước, áp best-practice sau."** (parity với `best-practices.md` §2)

Tool **không dogmatic**. Nếu project đã có pattern composition nhất quán + hợp lý (vd: data-heavy domain VDS gom 12 field thành 3 nhóm rõ ràng) → giữ, formalize làm chuẩn repo. Chỉ propose đổi khi pattern **không nhất quán** (chaotic) hoặc **vi phạm rule HARD**.

**3 confidence level cho mọi proposal:**
- **HIGH** — vi phạm rõ ràng, sửa tự nhiên, ít tranh cãi (vd: 2 nút `primary` cùng 1 view → L1). Tại gate feature-design (P2+) một số HIGH được promote thành **HARD** (block đến khi fix).
- **MEDIUM** — có deviation nhưng có thể intentional (vd: 9 field 1 cột — có thể hợp lệ nếu là 1 nhóm logic). Đề xuất + owner duyệt. **KHÔNG bao giờ HARD.**
- **LOW** — opinion-based (vd: vị trí focal point F vs Z). Đề xuất, default reject nếu owner không opt-in.

**Enforcement timeline (chốt 2026-06-12, plan §10):**
- **P1 (file này):** warn-only TOÀN BỘ rule, mọi gate. Mục tiêu thu false-positive rate trước.
- **P2+:** chỉ **L1 / L2 / L7** promote → **HARD**, và **chỉ tại gate `feature-design`** (per-unit composition). Gate `ux-design` (L5/L6/L9, journey/IA-level) **warn-only vĩnh viễn** — không rule HIGH ở journey-level.

## 3. Owner map (single owner per concern — chống drift)

Mỗi rule audit ở **đúng 1 gate**; layer kia chỉ cite ID, KHÔNG copy nội dung rule.

| Owner gate | Rule audit | Fidelity |
|---|---|---|
| **ux-design** (Stage 3b, gate sau step 09-10) | **L5, L6, L9** | journey-skeleton low-fi: flow + screen inventory + reading order. KHÔNG control-level composition |
| **feature-design** (Stage 4a, gate sau step-02 F3) | **L1, L2, L3, L4, L7, L8, L10, L11** | per-unit blueprint: composition đầy đủ, có machine contract |

> **R10 inheritance:** feature-design kế thừa wireframe layout từ UX Spec. Nếu composition-audit phát hiện UX Spec (L5/L6/L9) vi phạm → **escalate ngược UX Spec** (cơ chế R7), KHÔNG tự sửa lệch UX Spec.

## 4. Rules catalog

Mỗi rule format: **Best practice → Detection (đo được) → Proposal table (confidence)**. Detection luôn đếm/đo được trên artifact (control intent, state list, group member, tree depth) — KHÔNG phán đoán "gu".

### L1 — Single primary action

**Owner:** feature-design. **Confidence vi phạm:** HIGH (P2+ HARD).

**Best practice:** Mỗi view/section độc lập có **đúng 1** control intent=`primary`; còn lại `secondary`/`tertiary`. Nhiều primary = loãng focus, user không biết "đường chính".

**Detection:** Đếm control có `intent: primary` trong Control table §2.3 (feature-design) per view/section scope.

| Case | Proposal | Confidence |
|---|---|---|
| Đúng 1 primary | OK. | — |
| 0 primary nhưng view có action | "View không có primary action. Đề xuất nâng action chủ đạo lên `primary`." | HIGH |
| ≥2 primary cùng scope | "View có {N} `primary`. Giữ 1, hạ phần còn lại xuống `secondary`. Action chủ đạo là gì?" | **HIGH (HARD P2+)** |
| Multi-section view, mỗi section 1 primary | OK (primary tính per-section, không per-screen). | — |

**Skip:** view read-only/display thuần (0 action) — không áp.

### L2 — Mandatory states

**Owner:** feature-design. **Confidence vi phạm:** HIGH (P2+ HARD).

**Best practice:** Mọi view render data PHẢI khai báo tối thiểu **3 state: `empty` + `loading` + `error`** (sàn cứng). `success` **chỉ bắt buộc khi view có mutation** (create/update/delete); view read-only (report/dashboard/list-only) KHÔNG ép `success`.

**Detection:** Check FSM/journey/state list của view có đủ 3 floor state. Nếu Control table có control intent ∈ {submit, create, update, delete, save} → view có mutation → thêm `success` vào required set.

| Case | Proposal | Confidence |
|---|---|---|
| Có đủ empty+loading+error (+success nếu mutation) | OK. | — |
| Thiếu ≥1 floor state | "View thiếu state {list}. 3 state empty/loading/error là sàn cứng cho mọi view có data." | **HIGH (HARD P2+)** |
| View có mutation nhưng thiếu `success` | "View có mutation ({control}) nhưng chưa khai báo `success` state." | HIGH |
| View read-only thiếu `success` | OK — read-only không ép success. | — |

**Skip:** view tĩnh không fetch/mutate data (vd: trang static content) — chỉ cần state mặc định.

### L3 — Field grouping

**Owner:** feature-design. **Confidence vi phạm:** MEDIUM.

**Best practice:** Field liên quan ngữ nghĩa phải gom qua layout primitive (fieldset/card/section); không để field rời rạc trôi nổi.

**Detection:** Layout Groups table có group bao ≥2 sibling field cùng concern. Field flat không thuộc group nào + có sibling cùng concern → flag.

| Case | Proposal | Confidence |
|---|---|---|
| Field liên quan đã trong group chung | OK. | — |
| ≥2 field cùng concern nhưng rời rạc | "Field {list} cùng concern nhưng chưa nhóm. Đề xuất gom vào 1 layout group." | MEDIUM |

### L4 — Column density

**Owner:** feature-design. **Confidence vi phạm:** MEDIUM (KHÔNG bao giờ HARD).

**Best practice:** Không quá **N=7** field flat (chưa nhóm) trong 1 column. Vượt → gợi ý L3 (nhóm lại), KHÔNG fail.

> **Chốt 2026-06-12:** default **N=7**, MEDIUM, DSO-overridable, KHÔNG HARD. Lý do: Miller 7±2 áp dụng cho memory chunk, KHÔNG cho field đã được nhóm. Domain VDS data-heavy nhiều field hợp lệ vì đã nhóm logic → L4 chỉ là trigger nhắc L3, không phải lỗi.

**Detection:** Đếm member flat trong 1 Stack/column chưa qua group wrapper.

| Case | Proposal | Confidence |
|---|---|---|
| ≤ N field flat / column | OK. | — |
| > N field flat / column | "Column có {count} field flat (>{N}). Cân nhắc nhóm qua L3 (fieldset/section)." | MEDIUM |

**Override:** `ds-rules-overrides.md` → `## layout` → `column-density.max_flat_fields: <N>`.

### L5 — Progressive disclosure

**Owner:** ux-design (journey/IA-level). **Confidence vi phạm:** MEDIUM (warn-only vĩnh viễn).

**Best practice:** Option nâng cao / hiếm dùng phải collapse (accordion / drawer / "more") thay vì phơi hết lên view chính. Giảm tải nhận thức.

**Detection:** Trong journey wireframe, secondary/advanced group có disclosure wrapper hay phơi flat.

| Case | Proposal | Confidence |
|---|---|---|
| Advanced option đã collapse | OK. | — |
| Nhóm advanced/rare phơi flat cùng primary content | "Nhóm {name} là advanced/hiếm dùng — đề xuất collapse (accordion/drawer/more)." | MEDIUM |

### L6 — Reading order / focal point

**Owner:** ux-design (journey/IA-level). **Confidence vi phạm:** LOW (warn-only vĩnh viễn).

**Best practice:** Primary CTA nằm ở điểm kết tự nhiên của luồng đọc (F-pattern cho content-heavy, Z-pattern cho landing). 1 focal point chính / screen.

**Detection:** Vị trí primary trong tree order của wireframe + đếm số phần tử "đòi attention" tương đương.

| Case | Proposal | Confidence |
|---|---|---|
| Primary ở điểm kết luồng đọc, 1 focal point | OK. | — |
| Primary đặt lệch luồng / nhiều focal point cạnh tranh | "Primary CTA / focal point đặt lệch reading order. Cân nhắc reposition theo F/Z-pattern." | LOW |

### L7 — Destructive separation

**Owner:** feature-design. **Confidence vi phạm:** HIGH (P2+ HARD).

**Best practice:** Action phá hủy (delete/reject/remove) phải **tách khỏi** cụm action thường (không kề sát primary) + có confirm state (dialog/undo).

**Detection:** Control intent=`destructive` có (a) tách khỏi cụm primary/secondary, và (b) journey có confirm state đi kèm.

| Case | Proposal | Confidence |
|---|---|---|
| Destructive tách + có confirm | OK. | — |
| Destructive kề sát primary | "Action phá hủy {control} kề sát primary — risk mis-click. Tách ra." | **HIGH (HARD P2+)** |
| Destructive thiếu confirm state | "Action phá hủy {control} thiếu confirm (dialog/undo)." | **HIGH (HARD P2+)** |

### L8 — Form linearity

**Owner:** feature-design. **Confidence vi phạm:** MEDIUM.

**Best practice:** Form nhập tuyến tính ưu tiên **single-column** (mắt đi thẳng, ít lỗi). Multi-column chỉ cho field độc lập ngắn (vd: city/zip).

**Detection:** Layout direction của form group — đếm field input trong row multi-column.

| Case | Proposal | Confidence |
|---|---|---|
| Form chính single-column | OK. | — |
| Form tuyến tính bị xếp multi-column | "Form {name} multi-column — đề xuất single-column trừ field độc lập ngắn." | MEDIUM |

### L9 — IA depth

**Owner:** ux-design (journey/IA-level). **Confidence vi phạm:** MEDIUM (warn-only vĩnh viễn).

**Best practice:** Nesting điều hướng ≤ **N=3** cấp; sâu hơn cần breadcrumb / cơ chế định hướng.

**Detection:** §6 navigation tree depth (ux-design IA).

| Case | Proposal | Confidence |
|---|---|---|
| Depth ≤ N | OK. | — |
| Depth > N, không breadcrumb | "IA depth {d} > {N} cấp, thiếu breadcrumb. Đề xuất flatten hoặc thêm wayfinding." | MEDIUM |

**Override:** `ds-rules-overrides.md` → `## layout` → `ia-depth.max_levels: <N>`.

### L10 — Affordance state

**Owner:** feature-design. **Confidence vi phạm:** MEDIUM.

**Best practice:** Mọi interactive control khai báo hover/focus/disabled (token-level resolve ở Stage 4b — file này chỉ check **khai báo có mặt**, không check màu).

**Detection:** Control table §2.3 — cột state có hover/focus/disabled cho control interactive.

| Case | Proposal | Confidence |
|---|---|---|
| Control interactive khai báo đủ state | OK. | — |
| Thiếu khai báo state | "Control {name} thiếu khai báo hover/focus/disabled (token resolve ở 4b)." | MEDIUM |

### L11 — Consistency placement

**Owner:** feature-design (cross-screen, tinh chỉnh ở P4). **Confidence vi phạm:** MEDIUM.

**Best practice:** Cùng loại action ở cùng vị trí xuyên các screen (action bar, primary CTA position) — giảm tải scan.

**Detection:** So sánh vị trí action bar / primary giữa các screen cùng feature.

| Case | Proposal | Confidence |
|---|---|---|
| Action bar / primary nhất quán cross-screen | OK. | — |
| Cùng action đặt khác vị trí giữa screens | "Action {type} đặt khác vị trí giữa {screenA}/{screenB}. Thống nhất placement." | MEDIUM |

## 5. Rule application order

Gate apply rules theo thứ tự (mỗi gate chỉ chạy rule thuộc owner mình — §3):

1. **HARD-eligible** (L1, L2, L7) — P1 warn, P2+ block tại feature-design gate.
2. **Composition MEDIUM** (L3, L4, L8, L10) — propose, không block.
3. **Journey/IA MEDIUM-LOW** (L5, L6, L9) — ux-design gate, warn vĩnh viễn.
4. **Cross-screen** (L11) — tinh chỉnh P4.

## 6. Confidence-based gating

```markdown
## [HIGH — P2+ HARD tại feature-design gate]
(L1/L2/L7; P1: warn-only)

## [MEDIUM — propose, owner review]

## [LOW — opinion, default skip nếu không opt-in]
```

Flag trong `.bmm-config.yaml`:

```yaml
feature-design:
  layout_rules:
    enforce_hard: false          # P1 = false (warn-all). P2 flip true → L1/L2/L7 block
ux-design:
  layout_rules:
    enforce_hard: false          # vĩnh viễn false (journey-level warn-only)
```

## 7. Override per-rule

DSO disable / customize rule riêng trong `.bmm-config.yaml`:

```yaml
feature-design:
  layout_rules:
    rules:
      single-primary-action:    { enabled: true }
      mandatory-states:         { enabled: true, floor: [empty, loading, error] }
      column-density:           { enabled: true, max_flat_fields: 7 }
      destructive-separation:   { enabled: true }
ux-design:
  layout_rules:
    rules:
      ia-depth:                 { enabled: true, max_levels: 3 }
```

## 8. Customization — repo-specific overrides

Domain-specific layout rule → **tái dùng** `{design_system_root}/ds-rules-overrides.md` (cùng file với token overrides, best-practices.md §8), thêm section `## layout`:

```markdown
## layout
column-density:
  max_flat_fields: 9            # VDS data-heavy: nới lên 9
ia-depth:
  max_levels: 4
# disable rule: liệt kê rule id
disabled:
  - form-linearity
```

> **KHÔNG tạo file override riêng cho layout** (chốt 2026-06-12). Hai file override = hai SSoT = drift (rủi ro chính plan §7). Gate load `ds-rules-overrides.md` section `## layout` và merge với rules built-in.

## 9. Edge cases

| Case | Xử lý |
|---|---|
| Wireframe chưa có Control table (ux-design journey-skeleton) | Chỉ chạy L5/L6/L9 (không cần control-level data). L1-L4/L7/L8/L10 skip — chờ feature-design. |
| Feature reuse-journey / single-screen (skip Stage 3b) | ux-design gate không chạy; feature-design gate vẫn chạy full composition audit. |
| 2 rule conflict (vd L4 muốn nhóm, L8 muốn single-column) | L8 (form linearity) win cho form input; L4 chỉ nhắc, không block. |
| Project đã có pattern composition nhất quán hợp lý | Non-dogmatic: giữ, formalize. Chỉ propose khi chaotic / vi phạm HARD. |
| DSO override toàn bộ | Gate chỉ scan + report, không propose. |

---

**End of layout-best-practices v1.0.**
