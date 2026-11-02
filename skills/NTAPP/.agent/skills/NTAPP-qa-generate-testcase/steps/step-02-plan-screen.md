# STEP 02: LẬP PLAN CHO BỀ MẶT TEST (MÀN HÌNH hoặc OPERATION)

> **Acting as:** [Senior QA Engineer](../agents/agent_generate_manual_testcase.md)
> **Tuân thủ:** [principles/iron_rules.md](../principles/iron_rules.md) (đặc biệt R1, R5) · [principles/run_mode_rules.md](../principles/run_mode_rules.md) §3–4.

## 1. Mục tiêu
Lập **Math Forcing (phân rã số case theo control × rule)** + Test Plan cho **bề mặt hiện tại** — màn hình (`surface_type=ui`) hoặc operation/endpoint (`surface_type=service`). KHÔNG bung checklist ≥N dòng vào plan (materialize 1-1 ở Step 03 — xem Chốt 8).

> **VÒNG LẶP PER-MÀN (BẮT BUỘC):** Step 02 chạy cho **ĐÚNG MỘT màn/operation/cụm hành động** — chính bề mặt đang tới lượt trong thứ tự E2E (Step 01). Làm xong Step 02 của màn này thì đi thẳng **02b → 03 cho CHÍNH màn này** rồi MỚI quay lại Step 02 cho màn kế. **CẤM** lập plan (Step 02) cho nhiều màn cùng lúc rồi mới chạy 02b/03 hàng loạt — mỗi màn là một chu trình khép kín `02 → 02b → 03`. Đây là điểm mù tái diễn khi output dài: "dài quá" KHÔNG bao giờ là lý do gộp pha xuyên màn; dài thì chia nhiều lần ghi.

## 2. Các Bước Thực Hiện

> **RẼ NHÁNH theo `surface_type` (từ Step 00 / Ledger):**
> - **`surface_type=service` (không giao diện)** → chạy **9 chốt chặn service** tại **[principles/service_surface_rules.md §2](../principles/service_surface_rules.md)** (Contract Map thay Ánh xạ Nhãn UI; rule 10-be + request-validation tầng payload; case từ error catalog / state machine / idempotency / resilience). **BỎ** mục 3 (Ánh xạ Nhãn Giao diện) bên dưới. Sau đó vẫn sang [Step 02b](step-02b-risk-allocation.md) → [Step 03](step-03-write-testcase.md).
> - **`surface_type=ui` (mặc định)** → chạy 9 chốt chặn UI dưới đây.
> - **`surface_type=ui` + bề mặt mượn** → vẫn 9 chốt UI, nhưng **bề mặt = cụm hành động** và Chốt 3/4/6/8 áp override tại [borrowed_surface_rules.md §6](../principles/borrowed_surface_rules.md); màn host chỉ là Precondition.

**Nhánh `ui` — 9 chốt chặn tại [principles/slice_planning_rules.md](../principles/slice_planning_rules.md):**

1. **Nạp trí nhớ E2E:** Xác định Màn hình/Widget hiện tại từ `implementation_plan.md` + **Context Ledger** (fact dùng chung — không đọc lại) (Chốt chặn 1).
2. **Nạp tài liệu thiết kế (SCOPED RELOAD):** Theo [run_mode_rules.md](../principles/run_mode_rules.md) §4 — dùng `view_file` đọc **chỉ** phần Giao diện (+ phần Logic/Dữ liệu khi cần) trong `_detailed_design` của FE *màn hiện tại* và BE *trực tiếp* map màn đó. Fact dùng chung (slice overview, BE contract map) lấy từ **Context Ledger** (nhãn cụ thể do màn tự map đầy đủ ở Chốt 3, không glossary chung), KHÔNG reload toàn bộ `_detailed_design` của *mọi* BE lại (Chốt chặn 2).
3. **Ánh xạ Nhãn Giao diện (LIỆT KÊ ĐẦY ĐỦ TỪNG ELEMENT):** Điền "Nhật Ký Đọc File" và ánh xạ **MỌI** element của màn (control/tiêu đề/placeholder/cột bảng/empty-state/banner/dialog/toast/inline-error) sang **Nhãn hiển thị UI** verbatim + cite DD (Chốt chặn 3). KHÔNG gom về glossary chung; **thiếu element = thiếu testcase ở Step 03**.
4. **Lập Bảng Mapping Rule:** Khớp các control thực tế với file rule tương ứng trong `references/kbkt-generation/` (Chốt chặn 4). `00-core/*` + `01-ui/*` đánh dấu "đã nạp qua Context Ledger" (Step 01), không phải load mới.
5. **Nạp Rule kiểm thử:** BẮT BUỘC dùng `view_file` cho từng file Rule **per-screen chưa có trong Ledger** (control-specific: `02-input/*`, `03-selection/*`, ...) trong bảng Mapping để nạp ngữ cảnh (Chốt chặn 5).
6. **Tính toán số lượng case:** Sử dụng Decision Table/Math Forcing để tính tổng số testcase tối thiểu (Chốt chặn 6). Nếu tổ hợp lớn (> 30 dòng), thực hiện viết và chạy script Python dùng `allpairspy` để sinh ma trận tối ưu.
7. **Tự đối soát (Self-Reflection):** Rà soát độ bao phủ tổ hợp đa nguồn (Chốt chặn 7).
8. **Chốt chặn 8 — KHÔNG sinh checklist vào plan (ĐÃ BỎ):** Plan KHÔNG có section Checklist / danh sách `[ ]`. `X` (tổng math-forcing) lấy từ **Chốt chặn 6**. Chỉ ghi kèm **phân định Action-Verify** + (định nghĩa) HARD CHECK grep cho Step 03 (xem [slice_planning_rules.md](../principles/slice_planning_rules.md) Chốt 8). Materialize 1-1 mỗi rule-case (và mỗi dòng Ma Trận Quyết Định) → 1 dòng testcase thực hiện ở [Step 03](step-03-write-testcase.md); Math Check `X = Y` (`Y` = số dòng testcase).
9. **Ghi và duyệt Plan (HITL GATE):** Nối tiếp (append) Kế hoạch vào `implementation_plan.md` theo đúng định dạng tại **[references/templates/plan_template.md](../references/templates/plan_template.md)** (Chốt chặn 9). **Dừng/defer theo `run_mode`** — áp [run_mode_rules.md §3](../principles/run_mode_rules.md) (`full` = dừng duyệt + narrate; `batch` = defer + checkpoint im lặng → gộp Step 04).
   - *Chuyển tiếp:* Thực thi [Step 02b](step-02b-risk-allocation.md) để gán **policy `@risk/@exec` per rule-group** (từ Math Forcing), rồi sang [Step 03](step-03-write-testcase.md).
