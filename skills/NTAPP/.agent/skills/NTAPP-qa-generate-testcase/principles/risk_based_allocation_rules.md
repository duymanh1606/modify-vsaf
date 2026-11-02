# RISK-BASED ALLOCATION RULES — Phân bổ test theo rủi ro (School B, chế độ Hybrid)

> **Mục đích:** Gán cho mỗi kịch bản 2 thuộc tính: **`@risk`** (P0/P1/P2) và **`@exec`** (automate/manual/exploratory),
> để (a) tối ưu effort theo rủi ro thay vì phủ phẳng, (b) định tuyến sang automation.
> Dùng ở [step-02b-risk-allocation.md](../steps/step-02b-risk-allocation.md), sau Step 02 (plan), trước Step 03 (write).
>
> **Triết lý Hybrid:** KHÔNG vứt bỏ phủ exhaustive. Có **2 mode**, chọn qua config `risk_mode` (Layer 3 `.bmm-config.yaml`,
> mặc định `exhaustive`). `risk_mode` chỉ ảnh hưởng **độ bung số case**; việc gán `@exec` áp dụng cho **cả hai mode**.

---

## 1. Hai mode (Hybrid)

| Mode | `risk_mode` | Hành vi bung case | Khi dùng |
|---|---|---|---|
| **Exhaustive** *(default)* | `exhaustive` | Giữ nguyên `cases_count` của mọi rule file (hành vi gốc skill). Không cắt case. | Regulated/audit, slice rủi ro cao, nghiệm thu cứng |
| **Risk-gated** *(opt-in)* | `risk-gated` | Bung đủ cho P0/P1; với **P2 visual/display** chỉ giữ **smoke subset** (phần cắt = **drop hẳn**, KHÔNG đẩy charter) | Slice rủi ro thấp, cần nhanh, tinh thần modern QA |

> Mode chỉ đổi **số lượng**; **không** đổi cấu trúc 3 khối, không đổi Iron Rules. Math Check Gate (R2) vẫn chạy:
> ở `risk-gated`, số case kỳ vọng = `cases_count` đã trừ phần P2 bị cắt — phải **ghi rõ công thức trừ** ra chat (vd `46 − 9 (P2 zoom/responsive drop) = 37`).

---

## 2. Chấm `@risk` (Risk tier = cột "Độ ưu tiên")

Risk = **Likelihood × Impact**, ánh xạ về 3 tier (giữ tương thích thang P0/P1/P2 sẵn có):

| Tier | Định nghĩa | Ví dụ điển hình |
|---|---|---|
| **P0** | Luồng chính / Blocker / Sanity / mất tiền / phân quyền-ATTT | Tạo-lưu thành công E2E; IDOR; SQLi; luồng thanh toán |
| **P1** | Luồng nhánh / biên / validation / lỗi do Backend spec | BVA maxlength; required-field; error path API |
| **P2** | Hiển thị / visual / layout / điều hướng phụ | Zoom/responsive; focus order; tab navigation; tooltip |

Nguồn để chấm: phần Tổng quan (nghiệp vụ), phần Logic (nhánh), khối testcase (UI/Functional/Security → security luôn ≥P1, thường P0).

---

## 3. Gán `@exec` (cổng automation) — áp dụng CẢ HAI mode

Quyết định theo **khả năng assert tự động của oracle** + **bản chất khối**:

| Điều kiện | `@exec` | `@target` | Lý do |
|---|---|---|---|
| Khối Functional/E2E có oracle `api`/`db`/`ui-deterministic` | `automate` | `robot` *(default)* | qa-robot assert được qua keyword + DB + request |
| Khối Security tái lập bằng API (IDOR, tampering, authz, SQLi qua payload) | `automate` | `robot` | Postman→Robot requests |
| Khối UI visual: zoom, responsive, focus order, màu/spacing, animation | `manual` | — | Automation giòn / cần mắt người |
| Rủi ro timing/đồng thời/phiên/ngắt-giữa-chừng (double-submit, đa tab, session timeout, back-forward, mạng chập chờn, TOCTOU) | `automate`/`manual` **scripted trong KHỐI 2/3** | `robot` | **CẤM đẩy charter** — phân tích ra oracle xác định (đúng 1 bản ghi, 401/409, degraded=true...) rồi viết case scripted. Đa số là deterministic |
| Vùng bất định cao (spec còn `[TBD]`, UX mới) | `automate`/`manual` **scripted trong KHỐI 2/3** | `robot`/— | KHÔNG hạ exploratory: viết case scripted với **expected = contract canonical** (dòng `[BR]`) hoặc `[TBD]` + Q&A; ghi Coverage Debt (§3 explore) — case KHÔNG bốc hơi khỏi coverage |
| Oracle chính phải người phán đoán (nội dung, thẩm mỹ, trải nghiệm) | `manual` + `@manual-verify` | — | Cấm automation giả vờ phủ |

**Quy tắc cứng:**
- **`@exec` quyết định theo ASSERT-ABILITY (§3), KHÔNG theo tier/Khối:** case hiển thị có oracle **tất định** — placeholder, nhãn/label, default value, enable/disable state, control tồn tại, count "(N kết quả)", **message lỗi text** — là `automate` (`@oracle:ui`, qa-robot assert text/attribute/state). **CHỈ** visual thẩm mỹ (zoom, responsive, font/màu/spacing, focus order, animation) mới `manual`. ⚠️ CẤM xếp placeholder/label/default/message vào `manual` chỉ vì nó "thuộc Khối 1 UI".
- Mỗi `@exec:automate` PHẢI có ≥1 `@oracle` trong {ui, api, db, msg} và một `@target`.
- Tầng oracle KHÔNG tự động được (vd `Log:` cần soi tay) → vẫn ghi ở Then nhưng gắn `@manual-verify`; case vẫn có thể `automate` nếu còn oracle khác tự động.
- **Mặc định KHÔNG dùng `@exec:exploratory`** và **KHÔNG tạo khối/charter exploratory riêng**. Mọi rủi ro — kể cả timing/đồng thời/phiên/UX mới/spec `[TBD]` — phải phân tích ra oracle rồi ghi thành **case scripted (`automate` hoặc `manual`) trong KHỐI 2 (Functional/E2E) hoặc KHỐI 3 (Security)**. `exploratory` chỉ được giữ cho **quan sát thẩm mỹ thuần không thể assert** (so màu/spacing/thiện cảm) và **nằm trong KHỐI 1 UI**, không sinh section riêng.
- **P0 không bao giờ là `exploratory`** — luồng chính/ATTT phải có testcase tường minh (automate hoặc manual scripted).
- **Oracle-first theo `surface_type`:**
  - *(bề mặt `ui`)* **UI-first (CỨNG):** test được trên UI thì BẮT BUỘC drive qua UI (`@scr` + `@oracle:ui` + dòng `Then UI:`, cột Công cụ `Chrome`/`Chrome+Postman`). API-only (`Postman`, bỏ `@scr`) CHỈ khi hành vi không thể thao tác/quan sát qua UI (backend thuần: audit log, fan-out nội bộ, bypass FE). CẤM drive UI nhưng oracle backend-only.
  - *(bề mặt `service` — no-UI)* **API-first (CỨNG):** dùng `@svc` + `@oracle:api` (hoặc `@oracle:db`/`@oracle:msg` khi job/consumer không trả HTTP), cột Công cụ `Postman`/`RequestsLibrary`. **CẤM `@oracle:ui`** và CẤM tag `@scr` (không có màn). Oracle nông "trả 200 là pass" bị cấm — phải assert body/schema + side-effect (xem [service_surface_rules.md §3](./service_surface_rules.md)).

---

## 4. Bảng chính sách tổng hợp (cheat-sheet)

**Bề mặt `ui`:**

| Khối \ Tier | P0 | P1 | P2 |
|---|---|---|---|
| **Functional/E2E** | automate (full) | automate (full) | exhaustive: automate(smoke) · risk-gated: smoke hoặc drop |
| **Security/ATTT** | automate (full) | automate/manual (full) | hiếm |
| **UI/Visual** | manual (sanity) | manual | exhaustive: manual(full) · risk-gated: manual(smoke) hoặc drop |

**Bề mặt `service` (no-UI)** — không có khối UI/Visual; oracle `api/db/msg/log`:

| Khối \ Tier | P0 | P1 | P2 |
|---|---|---|---|
| **Nghiệp vụ & E2E** (decision table, state machine, idempotency, side-effect API→DB→MSG) | automate (full) | automate (full) | exhaustive: automate(smoke) · risk-gated: smoke |
| **Hợp đồng & Request Validation** (required/length/format/enum tầng payload) | automate | automate (full) | exhaustive: automate · risk-gated: cắt bớt SỐ case (per-case, data ở fixtures — KHÔNG gom Outline) |
| **Phân quyền & ATTT** (IDOR, role/scope, injection, rò rỉ dữ liệu nhạy cảm) | automate (full) | automate/manual | hiếm |

---

## 5. Output của bước allocation

Step 02b gán **policy per rule-group** (từ Math Forcing Step 02) — mỗi (control × rule) 1 dòng policy trong plan; Step 03 áp policy này xuống TỪNG dòng testcase khi bung (điền cột Độ ưu tiên + Exec). Định dạng policy per rule-group (default + ngoại lệ sub-split):
```
Tên hồ sơ × textbox-base   → P1 · automate · @oracle:ui  (trừ case hiển thị thuần placeholder/label/default = P2 · automate; KHÔNG manual)
UI toàn màn × layout-visual → P2 · manual · @oracle:ui   (chỉ zoom/font/spacing/focus-order)
Tạo hồ sơ × save-button    → P0 · automate · @oracle:ui,api,db (happy 201); nhánh lỗi = P1 · automate
double-submit / session / degraded (KHỐI 2 · [BR]) → P0/P1 · automate · @oracle:db/api  (spec [TBD] → expected=canonical + Q&A + Coverage Debt)
IDOR/SQLi/tampering (KHỐI 3) → P0 · automate · @oracle:api
```
> Không còn dòng `exploratory · charter:CH-xx`: rủi ro timing/đồng thời/phiên/[TBD] được viết thẳng thành dòng scripted KHỐI 2/3 với oracle xác định (chú thích `[BR]` nếu expected neo theo contract canonical mà code chưa đạt).
Các annotation này là **đầu vào trực tiếp** để Step 03 sinh tag `@risk/@exec/@target/@oracle` trong `.feature` và cột `Exec` trong markdown — đảm bảo Sync Invariant (automation_contract_rules §1).

---

## 6. Rebalance ngân sách case (chống over-invest single-field / under-invest integration)

Áp CẢ HAI mode. Không để validation single-field lặp nuốt hết ngân sách trong khi chiều tích hợp/behavior — nơi bug thật hay lọt — chỉ có 1 case nông.

### 6.1 Validation lặp single-field — per-case, data ở fixtures (CẤM gom)
Một trường có ≥2 case cùng-một-logic chỉ khác giá trị input (EP/EG/BVA/space/security) → viết **N `Scenario` riêng** trong `.feature`, mỗi case 1 `@id` (giữ R2 — [automation_contract_rules §1](./automation_contract_rules.md)). **CẤM `Scenario Outline`/`Examples`.** Chống trùng-lặp bằng cách để giá trị input ở `fixtures.yaml` (mỗi case 1 dataset), KHÔNG bằng cách gom scenario. Markdown liệt kê đủ mỗi case thành 1 dòng; count KHÔNG đổi.

> **⚠️ Rebalance = quản ngân sách số case (`cases_count`), KHÔNG phải gom block.** N case cùng-logic → **N `@id` = N `Scenario`** (mỗi cái = 1 dòng `.md` `Exec=automate`), KHÔNG giữ 1 @id "đại diện" rồi bỏ phần còn lại. Rebalance chỉ điều tiết SỐ case giữa single-field vs integration, KHÔNG giảm @id, KHÔNG đổi cấu trúc thành Outline — kiểm bằng HARD CHECK cross-artifact [automation_contract_rules §1](./automation_contract_rules.md). Drop @id = vi phạm R2.

### 6.2 Sàn chiều sâu integration (bắt buộc)
Mọi chiều tích hợp/behavior có mặt trong slice là **P0/P1** (không P2, không bị risk-gated cắt); số case + độ sâu oracle theo ĐÚNG `cases_count` của rule nguồn, KHÔNG rút về 1 scenario nông:

| Chiều | Rule nguồn | Oracle tối thiểu |
|---|---|---|
| Filter-correctness | [11-independent-filter](../references/kbkt-generation/11-independent-filter/independent-filter-rule.md) | khớp TỪNG bản ghi (Like/Equal), bản ghi không khớp vắng mặt |
| Cross-actor visibility | [10-be/data-visibility](../references/kbkt-generation/10-be/data-visibility-rule.md) | ≥2 principal, phạm vi thấy theo scope/role |
| Volume-boundary | [09-data-grid](../references/kbkt-generation/09-data-grid/grid-base-rule.md) | count > page size + > default framework |
| Error-code → UI side-effect | [06-validation/error-response-behavior](../references/kbkt-generation/06-validation/error-response-behavior-rule.md) | hành vi UI đúng per mã lỗi |
| Stale-state | [11-independent-filter](../references/kbkt-generation/11-independent-filter/independent-filter-rule.md) | danh sách khớp filter hiện tại sau xóa/đổi |

CẤM chiều integration chỉ 1 case oracle "list hiển thị" / "không rỗng".
