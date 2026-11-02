# Evaluation Metrics — Workflow AI Coding (NTAPP/BMAD Stage 1→5)

> Bộ chỉ số chuẩn để đánh giá **bản thân quy trình agentic engineering** (không phải sản phẩm).
> Đồng hành: harvester [`scripts/eval-harvester.py`](../../scripts/eval-harvester.py) → sinh
> [`metrics.json`](metrics.json) + [`scorecard.md`](scorecard.md). File này là **định nghĩa SSoT** cho mọi metric.

**Nguyên tắc phân định 2 trục:**

| Trục | Câu hỏi | Bản chất |
|---|---|---|
| **Hiệu quả (Effectiveness)** | Có làm *đúng thứ*, *đúng cách*, *bắt lỗi đúng chỗ*, *nợ trong tầm kiểm soát* không? | chất lượng / đúng |
| **Hiệu suất (Efficiency)** | Tốn bao nhiêu *thời gian / rework / context / chi phí* để ra một slice demoable? | tốc độ / rẻ |

Hai trục **độc lập có chủ đích**: defer & cancel làm *tăng* hiệu suất biểu kiến nhưng *giảm* hiệu quả — phải đo tách để không ngụy trang nợ thành năng suất (xem §Tradeoff).

Quy ước cột: **Hướng** ↑ = cao tốt / ↓ = thấp tốt · **Nguồn**: 🟢 đo được ngay (harvester) · 🟡 cần instrument nhẹ · 🔴 cần hạ tầng (timestamp/token).

---

# BỘ A — HIỆU QUẢ (Effectiveness) · EFF-1…12

## Nhóm A1 — Correctness (output đúng)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFF-1** | **F-FPY** — Functional First-Pass Yield (headline) | #unit có-AC KHÔNG có patch *chức năng* (`functional_patch=0`) ÷ tổng unit có-AC (unit-incidence). Phụ: `ffpy_acnorm` = 1 − lỗi-chức-năng ÷ AC | ↑ | ≥80% | 🟡 (proxy 🟢) | tính năng chạy **đúng-spec** ngay lần đầu (không tính gia cố) | *re-harvest* |
| **EFF-1b** | **SFPY** — Strict FPY (gồm cả gia cố) | 1 − **tổng** patch ÷ AC (= công thức FPY cũ; gồm cả patch bảo mật/edge/chất lượng) | ↑ | theo dõi | 🟢 proxy | gánh nặng review tổng — F-FPY≫SFPY = feature chạy được nhưng tốn công gia cố | proxy **71%** |
| **EFF-2** | Defect Escape Rate | finding truy về stage gốc upstream (Design 3–4) ÷ tổng finding | ↓ | ≤25% | 🟡 | lỗi đáng lẽ chặn ở spec lại rò xuống build | n/a |
| **EFF-3** | Critical-defect Containment | lỗi P0 (security/owner-guard/sanitize) bắt *trước* first-commit ÷ tổng P0 | ↑ | 100% | 🟡 | lỗi nghiêm trọng lọt gate | SLICE-3 ✓ |

> **EFF-1 (F-FPY) vs EFF-1b (SFPY)** — harvester phân loại MỖI bullet `[Review][Patch]` thành 3 nhóm: **chức năng** (lăng kính *Acceptance Auditor* / luồng-AC hỏng → TRỪ F-FPY) · **gia cố** (bảo mật / edge / chất lượng-convention → feature VẪN chạy, KHÔNG trừ F-FPY) · **chưa rõ** (thiếu tín hiệu → KHÔNG ngầm tính sạch, report riêng). F-FPY headline = *unit-incidence* (% feature chạy đúng luồng chính lần đầu) — dễ hình dung hơn tỉ-lệ-trên-AC; `ffpy_acnorm` là biến thể AC-normalized dịu hơn (không nhị-phân-hoá cả unit). SFPY giữ nguyên công thức cũ `1 − patch/AC` để so gánh nặng review tổng (baseline 71% = số FPY kiểu cũ, nay = SFPY). Phân loại 3 tầng theo độ tin: **tag lăng kính** `(auditor)`/`(blind+edge)` cuối bullet (cao) > **suy-luận lexicon** (AC-id + động-từ-hỏng ⇒ chức năng; lexicon bảo mật/edge/quality ⇒ gia cố) `⚠️` > **chưa-rõ**. Ngưỡng severity (Critical/High) hiện CHƯA dùng để lọc.

## Nhóm A2 — Conformance (đúng spec & ổn định yêu cầu)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFF-4** | AC Completion | AC `pass` ÷ (tổng AC − AC `cancelled` hợp lệ) | ↑ | ≥95% | 🟡 | scope giao thiếu so với cam kết | n/a |
| **EFF-5** | AC Churn / Volatility | (#AC `cancelled`+`v3-changed`+`defer`) ÷ tổng AC | ↓ | ≤15% | 🟢 | spec Stage 3–4 chốt chưa kỹ | **SLICE-2 = 32%** ⚠ |
| **EFF-6** | Spec-Defect Ratio | deviation *do upstream sai* ÷ tổng deviation | ↓ | ≤30% | 🟡 | deviation là lỗi-thiết-kế hay cải-tiến-chủ-động | VEE-HOME 1/4 |

## Nhóm A3 — Debt governance (Defer / CR / Change Log — cluster trọng tâm)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFF-7** | Defer Avoidability Index | defer `avoidable` ÷ tổng defer | ↓ | ≤30% | 🟢 | nợ workflow đội lốt "ngoại sinh" | **54%** |
| **EFF-7b** | Residual Scattered Avoidability | defer `avoidable` & `excludable-by = —` ÷ tổng defer open | ↓ | ≤15% | 🟢 | nợ tránh-được KHÔNG gom cụm được (khó-giải thật) | **17%** |
| **EFF-8** | Defer Closure & Aging | defer đóng ÷ mở lũy kế; tuổi trung vị mục đang mở | ↑/↓ | ≥70% / ≤2 slice | 🟡 | backlog phình âm thầm | *cần ledger* |
| **EFF-9** | Traceability Integrity | 1 − (#mâu thuẫn xuyên artifact ÷ tổng cross-ref) | ↑ | ≥98% | 🟡 | drift kiểu `LEARN_VADA_URL` 3 giá trị | ≥1 defect mở |

> **EFF-7 vs EFF-7b**: EFF-7 đếm *tất cả* nợ tránh-được; EFF-7b chỉ phần **không gom cụm được** (`excludable-by: —`). Phân biệt vì nợ gom-cụm (vd 7 mục `testarch-framework`) đóng bằng **1 hành động**, còn nợ rải rác phải sửa từng mục — EFF-7b mới là chỉ số khó-giải thật. Defer-ledger field `excludable-by` (`testarch-framework`/`crm-contract-freeze`/`icon-sync`/`marketing-url`/`slice-SLICE-N`/`—`) drive cả hai + bảng "cụm đóng-một-nút" §2b của scorecard.

## Nhóm A4 — Verification rigor (gate có thực sự bắt lỗi)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFF-10** | Critical-domain Gate Compliance | slice critical chạy mandatory ATDD trước first-commit ÷ tổng slice critical | ↑ | 100% | 🟡 | bỏ qua gate bắt buộc | SLICE-3 ✓ |
| **EFF-11** | Review Effectiveness | yield = finding/unit · **patch:defer ratio** | ↑/↑ | — / ≥1.0 | 🟢 | review chỉ "ghi nhận" thay vì sửa | **PUBLIC 0.36** ⚠ |
| **EFF-12** | Triage Accuracy | lane đề xuất == lane thực thi (hồi cứu) ÷ tổng feature | ↑ | ≥90% | 🟢 | routing sai từ intake | 1/1 ✓ |

---

# BỘ B — HIỆU SUẤT (Efficiency) · EFFY-1…11

## Nhóm B1 — Throughput (nhanh)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFFY-1** | Slice Lead Time | Δ(intake → demo_status=done) | ↓ | đặt sau 1 cohort | 🔴 | slice kéo dài, nghẽn ở đâu | *timestamp giả* |
| **EFFY-2** | Stage Cycle Time | Δ start↔end mỗi stage | ↓ | — | 🔴 | stage nào ngốn thời gian | *timestamp giả* |

## Nhóm B2 — Rework economy (ít làm lại)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFFY-3** | Design Rework Ratio | #version archived ÷ #artifact (DD/HLD/spec) | ↓ | ≤1.0 | 🟢 | thiết kế phải làm lại nhiều vòng | DD: VEE-HOME 2 vòng, HLD 1 vòng |
| **EFFY-3b** | Code Churn Ratio | Σ(LOC added+deleted, prod, git) ÷ LOC prod sống-sót | ↓ | ≤1.5× (đặt sau cohort) | 🟢 git | code thrash — viết-rồi-xoá-rồi-viết-lại; bù lỗ hổng "rework **tầng code**" mà EFFY-3 (chỉ **tầng thiết kế**) bỏ trống | *git numstat* |
| **EFFY-4** | Backflow Count | #lần slice quay lại stage trước (escalate/correct-course) | ↓ | ≤1/slice | 🟡 | quy trình lùi bước | n/a |

> **EFFY-3b vs EFFY-3** (cặp "rework economy" phủ cả 2 tầng): EFFY-3 đếm vòng làm-lại **artifact thiết kế**; EFFY-3b đếm dòng code viết-rồi-xoá ở **tầng code** — trước đây hoàn toàn vô hình. Harvester báo **số tuyệt đối `LOC added` & `LOC deleted`** (base data, §5.3b scorecard) rồi mới suy ra ratio (1.0 = mọi dòng viết ra đều sống; >1 = thrash). Đo được ngay (🟢) vì đếm dòng `git numstat`, **không phụ thuộc timestamp** (khác EFFY-1/2). EFFY-3b là **companion diagnostic**, KHÔNG fold vào EffyI để tránh đếm-đôi rework với EFFY-3. ⚠️ LOC là **mẫu số chuẩn-hoá / tín hiệu thrash**, KHÔNG phải KPI năng suất — nhiều dòng ≠ nhiều giá trị (xem §LIMITS).

## Nhóm B3 — Reuse leverage (đòn bẩy tái dùng)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFFY-5** | DS Component Reuse Rate | reuse/promote ÷ (reuse + new) | ↑ | ≥40% | 🟢 | DS không được tái dùng, đẻ component mới liên tục | SLICE-1: 3 reuse / 8 ≈ 37% |
| **EFFY-6** | Code No-Fork Rate | unit reuse module sẵn ÷ tổng unit | ↑ | ≥50% | 🟡 | fork code thay vì refactor dùng chung | VEE-HOME no-fork ✓ |

## Nhóm B4 — Automation leverage (tự động hoá)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFFY-7** | AFK : HITL Ratio | #slice AFK ÷ tổng slice | ↑ | ≥60% | 🟢 | quá nhiều can thiệp tay | 2/3 ≈ 67% |
| **EFFY-8** | Gate Automation Coverage | #rule enforce tự động (pre-commit) ÷ tổng rule chất lượng | ↑ | ≥85% | 🟢 | gate phụ thuộc review thủ công | 8/9 ≈ 89% |

## Nhóm B5 — Context / cost economy

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **EFFY-9** | Context-Split Overhead | #file `_parts/` (proxy chẻ nhỏ vì giới hạn context) | ↓ | theo dõi xu hướng | 🟢 | artifact quá lớn, tốn vòng tổng hợp | DD-parts **20**, HLD 7, DS-meta 8 |
| **EFFY-10** | Token / Cost per Slice | output token ÷ slice | ↓ | đặt sau baseline | 🔴 | chi phí LLM mỗi slice | *cần instrument* |
| **EFFY-11** | Ceremony Cost | #artifact sinh ÷ #unit build | ↓ | theo dõi | 🟢 | overhead tài liệu / unit | ~31 artifact/unit (gồm DS) |

---

# BỘ C — CHI PHÍ (Cost) · COST-1…8

> Đo **token** — tách bạch 2 khái niệm tuyệt đối không được trộn:
> - **Trọng lượng deliverable** (proxy `~chars/4`): bao nhiêu *văn bản* được sinh ra (artifact + code). Đo được ngay từ file size. Các tỉ lệ spec:code / test:code thuộc nhóm này — "mỗi token code đổi lấy mấy token tài liệu".
> - **Burn thật LLM** (input+thinking+retry+re-read+tool-call): *chi phí $* thực để sinh ra chừng đó deliverable. Thường **gấp 5–50× trọng lượng**. CHỈ có khi đặt [`token-log.json`](token-log.json) vào thư mục này; không suy ra được từ artifact.

## Nhóm C1 — Tỉ lệ đầu tư / code (deliverable-weight, đo ngay 🟢)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **COST-2** | Spec+Design : Code | (Stage 3 + Stage 4 token) ÷ code-prod token | ↓ | ≤2.0× | 🟢 proxy | thiết kế phình so với code thật sinh ra | **2.99×** |
| **COST-3** | Test+Review : Code | (Story/Review + Test/ATDD + test-code) ÷ code-prod | ↓ | ≤1.5× | 🟢 proxy | tài liệu kiểm thử/review nặng hơn giá trị | **1.39×** |
| **COST-4** | Total Artifact : Code | tổng artifact ÷ code-prod | ↓ | theo dõi | 🟢 proxy | tổng overhead tài liệu / code | **9.63×** ⚠ (xem note DS) |
| **COST-5** | Governance : Code | (Discovery+Arch+Design System) ÷ code-prod | ↓ | theo dõi | 🟢 proxy | overhead khung/quản trị (phần lớn amortize) | **5.69×** |
| **COST-6** | Archive Waste | token bản cũ (archived) ÷ (current+archived) của Arch+Design | ↓ | ≤15% | 🟢 | công thiết kế bỏ đi qua các vòng version | **36%** ⚠ |

> **LOC làm mẫu số cross-check (bổ trợ COST-2…4):** mẫu số "code-prod token" của C1 là proxy `~chars/4` — file tự gắn cờ "proxy ≠ chuẩn" (§LIMITS). Harvester nay đếm thêm **LOC committed thật** (git numstat, §5.3b scorecard) → dùng làm mẫu số song song để sanity-check: nếu tỉ lệ spec:code lệch nhiều giữa "chars/4" và "LOC" thì proxy đang nói dối. KHÔNG thêm KPI mới (LOC/slice, LOC/AC = vanity, loại bỏ) — chỉ dùng LOC để chuẩn-hoá + bắt thrash (EFFY-3b).

## Nhóm C2 — Burn thật LLM (cần `token-log.json` 🔴)

| ID | Metric | Công thức | Hướng | Target | Nguồn | Bắt lỗi gì | Baseline |
|---|---|---|---|---|---|---|---|
| **COST-1** | Total Token Burn | Σ(input+output) toàn workflow | ↓ | đặt sau 1 cohort | 🔴 token-log | chi phí $ tuyệt đối | *cần log* |
| **COST-7** | Burn per AC | burn total ÷ tổng AC | ↓ | đặt sau baseline | 🔴 token-log | chi phí mỗi đơn vị giá trị giao | *cần log* |
| **COST-8** | Burn Amplification | burn thật ÷ delivered-weight (artifact+code proxy) | ↓ | theo dõi | 🔴 token-log | "đốt" bao nhiêu token để giao 1 token — thinking/retry/re-read | *cần log* |

> **COST-7 thay thế EFFY-10** (Token/Cost per Slice — placeholder cũ). COST-8 là chỉ số chẩn đoán quan trọng nhất của burn: amplification cao = nhiều vòng thử-sai / đọc lại context, không phải sản phẩm.

> **⚠️ Note DS amortization (đọc trước khi kết luận COST-4/5):** Design System = **45% tổng trọng lượng artifact** (~240k proxy) nhưng là **đầu tư một lần, dùng lại cho mọi feature tương lai** — brownfield reconstruct dồn toàn bộ chi phí này vào feature *đầu tiên*. Vì vậy COST-4 (9.63×) **thổi phồng** chi phí thực của feature. Tỉ lệ **feature-scoped** sát thực tế hơn = COST-2 + COST-3 ≈ **4.4×** (spec+design+review+test : code, đã loại DS/discovery/arch). Theo dõi COST-4 *giảm dần* qua các feature kế tiếp khi DS được khấu hao.

> **Cách lấy `token-log.json`** (mở khoá C2): xuất usage từ log phiên agent (Claude Code session JSONL / API usage) gộp theo stage hoặc slice → ghi `{"total":{"input":N,"output":N},"by_stage":{...},"by_slice":{...}}`. Harvester tự tính COST-1/7/8 khi file tồn tại; không có → hiển thị 🔴 n/a, không chặn.

---

# COMPOSITE INDICES

### Effectiveness Index (EI) — 0..100 / slice
```
EI = 0.30·EFF-1 + 0.20·(1−EFF-2) + 0.15·(1−EFF-7)
   + 0.15·(1−EFF-5) + 0.10·EFF-10 + 0.10·EFF-11_norm
```
Trọng số dồn vào correctness + escape (lõi "đúng"); EFF-7/EFF-5 là leading-indicator cảnh báo sớm. **EFF-1 trong công thức = F-FPY** (headline functional yield) — chỉ lỗi chức năng vào điểm "đúng", gia cố bảo mật/edge nằm ở EFF-1b/SFPY (companion, KHÔNG fold vào EI để tránh phạt feature đã chạy đúng nhưng được gia cố thêm).

### Efficiency Index (EffyI) — 0..100 / slice
```
EffyI = 0.25·(1−EFFY-3_norm) + 0.20·EFFY-5 + 0.15·EFFY-7
      + 0.15·EFFY-8 + 0.15·(1−EFFY-9_norm) + 0.10·(1−EFFY-1_norm)
```
EFFY-1 (lead time) chỉ vào công thức khi có timestamp; trước đó tái phân bổ trọng số sang rework + reuse.

### Band chung
**≥85 xanh · 70–85 vàng · <70 đỏ.**

---

# TRADEOFF — đọc EI và EffyI cùng nhau (ma trận 2 chiều)

|  | **EffyI cao** | **EffyI thấp** |
|---|---|---|
| **EI cao** | ✅ Lý tưởng — nhanh & đúng | 🟡 Chắc nhưng chậm — tối ưu throughput |
| **EI thấp** | 🔴 **Bẫy nợ** — nhanh nhờ defer/cancel, chất lượng rỗng | ⛔ Khủng hoảng — vừa chậm vừa sai |

> Ô **🔴 Bẫy nợ** là rủi ro lớn nhất của AI coding: EFF-7 cao (62%) + EFFY-7 cao (67%) có thể tạo ảo giác "AFK chạy nhanh" trong khi đang dồn nợ test/bug. Luôn chấm cặp, không chấm lẻ.

---

# NGUỒN DỮ LIỆU & TRẠNG THÁI ĐO

| Đo được ngay 🟢 | Cần instrument nhẹ 🟡 | Cần hạ tầng 🔴 |
|---|---|---|
| EFF-1/**1b**(proxy),5,7,7b,11,12 · EFFY-3,**3b**,5,7,8,9,11 · **COST-2,3,4,5,6** (proxy) | EFF-2,3,4,6,8,9,10 · EFFY-4,6 | EFFY-1,2 · **COST-1,7,8** (token-log) |

**Instrument 🟡 — chi phí thấp, giá trị cao (làm trước):**
1. Mỗi review-finding/deviation thêm `affects: AC-N` + `root-cause-stage:` → mở khoá EFF-2/4/6. Mỗi bullet `[Review][Patch]` gắn **tag lăng kính** `(auditor)`/`(blind)`/`(edge)` ở cuối → nâng F-FPY (EFF-1) từ *suy-luận lexicon* lên *phân-loại tin cao*.
2. Nâng [`deferred-work.md`](../Stage_5_Build_Verify/deferred-work.md) → **defer-ledger** (`id/opened/closed/category/owner/blocking-condition`) → mở khoá EFF-8 (closure & aging).
3. Consistency-check script quét hằng (URL/enum) xuyên artifact → EFF-9.
4. Tag `severity:P0` + `gate:` trong story → EFF-3/10.

**Hạ tầng 🔴:** stamp `started_at`/`ended_at` thật mỗi stage (hook commit) → EFFY-1/2; dump usage token mỗi run vào `evaluation/token-log.json` → COST-1/7/8 (burn thật). (Mọi Change Log hiện = 2026-06-11 nên lead-time chưa đo được. Token *trọng-lượng* COST-2…6 đã đo proxy ngay.)

> **EFFY-3b (code churn) KHÔNG thuộc nhóm 🔴 này** — đếm `LOC added/deleted` qua `git log --numstat` của code repo, không cần timestamp giả nên đo được **ngay** (harvester `harvest_code_churn`). Đây là lợi thế so với EFFY-1/2 vốn kẹt vì mốc thời gian đồng nhất.

---

# CADENCE

| Nhịp | Khi nào | Chấm gì |
|---|---|---|
| Per-slice retro | sau mỗi close-out | chạy harvester → EI + EffyI cho slice, cập nhật defer-ledger | 
| Per-phase gate | hết batch / hết vòng per-slice | escape-map (EFF-2) + traceability audit (EFF-9) + tradeoff matrix |
| Project-level | cuối Phase 1 | xu hướng EI/EffyI qua các slice; quyết định cải tiến quy trình |

---

# LIMITS (đọc trước khi kết luận)
- **n nhỏ** (3 slice) → xu hướng định tính; brownfield reconstruct đẩy defer/reuse cao do baseline cũ, không phải lỗi workflow.
- **Self-reported**: deviation/defer do agent tự khai → phụ thuộc tính trung thực (đúng cảnh báo "Honest Limits" của triage).
- **Proxy ≠ chuẩn**: EFF-1b/SFPY (patch/AC), EFFY-9 (#_parts), EFFY-11 (artifact/unit), **COST-2…6 (token ~chars/4)** là proxy — đọc kèm chú thích, đừng tuyệt đối hoá.
- **F-FPY phân-loại patch bằng heuristic**: tử số chỉ gồm patch *chức năng* (luồng-AC hỏng, bám lăng kính Acceptance Auditor); patch bảo mật/edge/chất lượng cố ý loại (→ SFPY). Story KHÔNG tag lăng kính review → harvester phải *suy-luận lexicon* (gắn `⚠️suy luận`) → kém chắc; patch *chưa-rõ* không ngầm tính sạch mà report riêng. Tag lăng kính `(auditor)`/`(blind+edge)` ở cuối bullet patch để F-FPY chính xác. Severity CHƯA dùng để lọc (một AC-nit nhỏ vẫn tính như một lỗi chức năng).
- **Token proxy ≠ burn thật**: COST-2…6 đo *trọng lượng deliverable*, KHÔNG phải token LLM thực burn (thường gấp 5–50×). Burn thật COST-1/7/8 cần `token-log.json`.
- **DS amortize**: COST-4/5 phồng vì Design System (45% trọng lượng) là đầu tư một-lần cho mọi feature — dùng tỉ lệ feature-scoped (~4.4×) khi so feature đơn lẻ; theo dõi COST-4 giảm dần qua các feature.
- **Code attribution theo header `id:`**: chỉ file code có header workflow mới được tính; test e2e `tests/` không tag → đếm riêng, không quy slice. Code repo auto-detect sibling (override `EVAL_CODE_ROOT`).
- **LOC churn (EFFY-3b) — 3 caveat**: (1) churn của file **đã xoá hẳn** không quy được về prod/slice (mất header `id:`) → gom vào dòng "Khác" §5.3b. (2) **Đổi-tên file** mà git không nhận rename → tính thành xoá+thêm → thổi nhẹ ratio. (3) Commit **đầu** của dự án brownfield dồn cả codebase cũ một lần → cột `added` rất lớn nhưng `deleted`≈0 nên ratio **không** bị thổi (vẫn ~1.0). LOC = mẫu số chuẩn-hoá + tín hiệu thrash, **không** phải thước đo năng suất.
- **Keyword-categorize thô** (defer): cần defer-ledger để chính xác hoá EFF-7/8.
- **Baseline timestamp giả** → EFFY-1/2 + COST-1/7/8 chưa có số; đừng suy diễn throughput/burn từ dữ liệu hiện tại.
