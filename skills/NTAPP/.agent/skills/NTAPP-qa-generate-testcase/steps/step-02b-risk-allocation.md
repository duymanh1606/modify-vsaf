# STEP 02b: RISK-BASED ALLOCATION (Risk tier + Exec routing)

> **Acting as:** [Senior QA Engineer](../agents/agent_generate_manual_testcase.md)
> **Tuân thủ:** [principles/risk_based_allocation_rules.md](../principles/risk_based_allocation_rules.md) · [principles/automation_contract_rules.md](../principles/automation_contract_rules.md) · [principles/explore_and_consistency_rules.md](../principles/explore_and_consistency_rules.md) (Oracle phủ định + Surface Invariant + TBD-escape)
> **Vị trí:** Chạy SAU [Step 02](step-02-plan-screen.md) đã duyệt (plan/Math Forcing có rồi), TRƯỚC [Step 03](step-03-write-testcase.md). Per màn `[Action]`, trong vòng lặp.

## 1. Mục tiêu
Gán **policy cho từng rule-group** (mỗi control × rule trong Math Forcing Step 02) hai thuộc tính `@risk` (P0/P1/P2) và `@exec` (automate/manual/exploratory) + `@oracle`/`@target`, để Step 03 áp xuống từng dòng testcase khi bung (tag `.feature` + cột `Exec`).

## 2. Các Bước Thực Hiện

1. **Đọc mode:** Lấy `risk_mode` từ config cascade (Layer 3 `.bmm-config.yaml`, mặc định `exhaustive`). In rõ mode đang dùng ra chat.
2. **Chấm `@risk`:** Với mỗi rule-group, gán P0/P1/P2 theo Likelihood × Impact ([risk_based_allocation_rules.md](../principles/risk_based_allocation_rules.md) §2). Security luôn ≥ P1 (IDOR/SQLi = P0).
3. **Gán `@exec` + `@oracle` + `@target`:** Theo bảng chính sách §3–§4. Mỗi `automate` phải có ≥1 oracle tự động + `@target` (mặc định `robot`).
3b. **Surface Invariant + Oracle phủ định (`view_file` [explore_and_consistency_rules.md](../principles/explore_and_consistency_rules.md) §1–§3):**
   - Lập **Surface Inventory** cho bề mặt hiện tại: *(ui)* dùng bảng bề mặt UI (§2.1: Search/Filter, List/Grid, Có phân quyền, Action ghi, Filter+list cùng màn, Dependent select, Field maxlength) · *(service)* dùng bảng bề mặt service tại [service_surface_rules.md §4](../principles/service_surface_rules.md) (Write op, Money op, Idempotent/consumer, Query/list, Có phân quyền, State-changing, Gọi downstream). Liệt kê bất biến bắt buộc + data đối nghịch phải seed cho từng loại. Ghi vào `implementation_plan.md`.
   - Với mỗi rule-group (và case đối nghịch của nó), ép **oracle phủ định bất biến** (§1): cấm kỳ vọng nông kiểu "list có dữ liệu là pass"; phải nêu **con số + điều kiện phủ định**. Spec im lặng → `[TBD]` + Q&A, không bịa.
   - Case bị chặn do spec gap → **TBD-escape** (§3): **viết case scripted** (`@exec:automate`/`manual`) trong KHỐI 2/3 với **expected = contract canonical** (chú thích `[BR]`) hoặc `[TBD]`; kèm 1 mục Q&A blocking + 1 dòng Coverage Debt Ledger (Mục 5.6, in ở Step 04). **KHÔNG** hạ xuống `exploratory`, KHÔNG để case bốc hơi.
4. **Áp mode + rebalance ngân sách:**
   - `exhaustive`: giữ nguyên `cases_count` mọi rule (không cắt).
   - `risk-gated`: cắt P2 visual/display về smoke subset (phần dư **drop hẳn**, KHÔNG đẩy `exploratory`). **Ghi rõ công thức trừ** ra chat (vd `46 − 9 = 37`) để Math Check Gate ở Step 03 dùng đúng số kỳ vọng.
   - **Rebalance ([§6](../principles/risk_based_allocation_rules.md)):** validation single-field cùng-logic viết **N `Scenario` riêng per-case** (data nạp từ `fixtures.yaml`, count không đổi — CẤM `Scenario Outline`); ghim chiều integration/behavior (filter-correctness, cross-actor, volume, error-code side-effect, stale-state) = P0/P1 — cấm risk-gated cắt, cấm rút về 1 case oracle nông.
5. **Gán policy per rule-group:** Ghi vào bảng **Math Forcing** trong `implementation_plan.md` — mỗi (control × rule) 1 dòng policy (default + ngoại lệ sub-split) theo định dạng tại [risk_based_allocation_rules.md](../principles/risk_based_allocation_rules.md) §5. Step 03 áp policy này xuống từng dòng testcase khi bung (điền cột Độ ưu tiên/Exec). KHÔNG cần checklist ≥N dòng trong plan.
   ```
   <control> × <rule> → P0/P1/P2 · automate/manual · @oracle:… (trừ <sub-case>, vd hiển thị placeholder/label = P2·automate; visual zoom/font = P2·manual)
   ```
6. **Materialize rủi ro "explore" vào KHỐI 2/3 (KHÔNG tách charter):** Mọi heuristic CH-FLEX/CH-CMP ([explore_and_consistency_rules.md](../principles/explore_and_consistency_rules.md) §4–§5) và mọi rủi ro timing/đồng thời/phiên/[TBD] phải **phân tích ra oracle xác định** rồi viết thành **dòng testcase scripted** (`@exec:automate`/`manual`) trong **KHỐI 2 (Functional/E2E resilience)** hoặc **KHỐI 3 (Security/RBAC)** ở Step 03 — vd double-submit→đúng 1 bản ghi, đa tab→409, session timeout→401, degraded→banner+header. **KHÔNG** gom thành charter, **KHÔNG** để `@exec:exploratory` sinh section riêng. Chỉ chừa `exploratory` cho quan sát thẩm mỹ thuần (nằm trong KHỐI 1 UI).
7. **Self-Audit Allocation Gate:**
   - Mọi mục đã có đủ `@risk` + `@exec` (+ `@target` nếu automate). Không sót.
   - Không có P0 nào là `exploratory`.
   - **Không còn rủi ro nào được đẩy sang charter/khối exploratory riêng:** mọi mục timing/đồng thời/phiên/[TBD] đã nằm trong KHỐI 2/3 dạng scripted. Nếu còn mục `exploratory` → nó phải là visual thuần trong KHỐI 1, ngược lại → gate FAIL, phân tích lại ra oracle.
   - **Oracle-first theo bề mặt:** *(ui)* **UI-first** — mọi mục test được qua UI có `@oracle:ui` (rule cứng §3); không có mục drive UI mà oracle backend-only. *(service)* **API-first** ([service_surface_rules.md §3](../principles/service_surface_rules.md)) — mọi mục có `@oracle:api` (hoặc `@oracle:db`/`@oracle:msg` khi là job/consumer không trả HTTP); CẤM `@oracle:ui` (không có UI); CẤM oracle nông "trả 200 là pass" (phải assert body/schema + side-effect).
   - **Rebalance (§6):** cụm ≥2 mục single-field cùng-logic viết per-case (N `Scenario`/dòng riêng, data ở fixtures — KHÔNG gom Outline); mọi chiều integration/behavior đạt `cases_count` rule nguồn, không có chiều nào chỉ 1 case oracle "list hiển thị".
   - **Surface Invariant (explore §2.2):** in bảng đối soát `<bề mặt> × <bất biến> → <@id case | THIẾU>`. Còn ô `THIẾU` → bổ sung case (hoặc TBD-escape §3 nếu chặn vì spec gap) trước khi sang Step 03.
   - Số case kỳ vọng (sau mode) được tính lại và ghi ra chat — đây là `X` cho Math Check Gate của Step 03.
8. **Chuyển tiếp:** KHÔNG có HITL gate riêng (annotation nằm trong plan đã duyệt). Đọc và thực thi [Step 03](step-03-write-testcase.md) cho **màn hiện tại** (chính màn vừa annotate). **KHÔNG** annotate 02b gộp cho nhiều màn, và KHÔNG bỏ qua Step 03 của màn hiện tại để nhảy sang màn khác — mỗi màn khép kín `02 → 02b → 03` rồi mới sang màn kế (theo vòng lặp per-màn ở Step 03 §11).

> **Lưu ý không lấn việc:** Bước này KHÔNG sinh testcase, KHÔNG sinh selector. Chỉ annotate. Việc render `.feature`/markdown/fixtures là của Step 03–04.
