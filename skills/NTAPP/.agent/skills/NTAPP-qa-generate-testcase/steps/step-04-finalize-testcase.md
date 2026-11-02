# STEP 04: HOÀN THIỆN DATA SETUP VÀ QUẢN LÝ LỖI (FINALIZATION)

> **Acting as:** [Senior QA Engineer](../agents/agent_generate_manual_testcase.md)
> **Tuân thủ:** [principles/iron_rules.md](../principles/iron_rules.md) · [principles/run_mode_rules.md](../principles/run_mode_rules.md) §3 (batch review).

## 1. Mục tiêu
Hoàn thiện dữ liệu mồi, môi trường, quy trình defect; **đóng gói + kiểm tính toàn vẹn cả 3 artifact** (markdown + `.feature` + `fixtures.yaml`); in Coverage Debt Ledger.

## 2. Các Bước Thực Hiện
Thực hiện các quy định tại **[principles/finalization_rules.md](../principles/finalization_rules.md)** + [automation_contract_rules.md](../principles/automation_contract_rules.md):

1. **Đọc dữ liệu thiết kế:** Đọc lại file testcase đã sinh và phần Dữ liệu trong `_detailed_design` của các BE Unit trong SLICE.
2. **Nạp cấu trúc Template:** Đọc mẫu mục 5.3/5.4/5.6 trong `references/templates/slice_testcase_table_template.md`. (KHÔNG còn Mục 5.5 charter.)
3. **Hoàn thiện `fixtures.yaml` (DATA canonical):** Hợp nhất toàn bộ `fixtures[]`/`datasets[]` các bề mặt đã sinh; điền `environment` (base_url, mocks). Điền `automation_prereq` theo bề mặt: *(ui)* `ui_schema_required` liệt kê `ui_schema_{id}.json` qa-robot cần · *(service)* `base_url` + `auth` + `api_contract` + `mocks` (các `[Downstream]` cần stub — theo [service_surface_rules.md §5](../principles/service_surface_rules.md)); KHÔNG cần `ui_schema`. Thiếu → `[TBD]`.
4. **Hoàn thiện Mục 5.3 (Data Setup VIEW):** Tóm tắt người-đọc, trỏ canonical về `fixtures.yaml` (cấm ghi chung chung).
5. **Hoàn thiện Mục 5.4 (Defect Management):** Điền tổng số kịch bản scripted `{total_tcs}`; để trống chỉ số chạy thực tế (sẽ được [Step 05 round-trip](step-05-roundtrip.md) điền từ `results/`).
6. **(BỎ Mục 5.5 charter):** Skill **KHÔNG** còn sinh section charter. Rủi ro CH-CMP (§4) / CH-FLEX (§5) / gap-spec (§3) đã được Step 02b/03 materialize thành **case scripted trong KHỐI 2/3** (đếm vào `{total_tcs}`). Nếu còn sót mục `@exec:exploratory` không phải visual thuần KHỐI 1 → quay lại Step 02b phân tích ra oracle, KHÔNG đẩy sang charter.
6b. **In Mục 5.6 (Coverage Debt Ledger):** Theo [explore_and_consistency_rules.md](../principles/explore_and_consistency_rules.md) §3 — liệt kê mọi bất biến đang **nợ** vì spec/contract gap (`<bề mặt × bất biến> · gap-id · @id case [BR] tương ứng · Q&A blocking`). Bắt buộc in ra chat để User thấy rõ chỗ nợ, không bị ru ngủ bởi "màu xanh automation". Ledger rỗng → ghi "Không có nợ coverage".
7. **Final Sync Audit (toàn slice) — gate gốc + 2 phép chiếu ([automation_contract_rules §1](../principles/automation_contract_rules.md) CANONICAL):** Kiểm **gate gốc `Y == X`** (tổng dòng markdown, kể cả manual) + **phép chiếu 1** (`count(@id .feature) == A+E`) + **phép chiếu 2** (`count(dataset fixtures) == A`) trên toàn file. Mọi `@id` xuất hiện đồng thời ở `.feature` + bảng markdown + (nếu automate) `fixtures.datasets`. ID liên tục, không nhảy cóc (R8). In bảng đối soát ra chat.
   - **[HARD CHECK — cross-artifact, cổng terminal]** chạy lệnh `comm` ở [automation_contract_rules §1](../principles/automation_contract_rules.md) — kèm **sàn chống false-pass** (`N_md == A+E`; `N_md==0` → FAIL, KHÔNG PASS). `comm` rỗng (thật) mới PASS. CẤM đếm nội bộ `.feature` (tautology). Lệch → bổ sung @id thiếu, KHÔNG hạ manual.
   - **[HARD CHECK — định tuyến dynamic-data, cổng terminal]** chạy lại kiểm §2b của [step-03 §10c](step-03-write-testcase.md) trên `fixtures.yaml` TOÀN slice (đối chiếu từng dataset động với bảng `sub_system → source_id` dựng từ `data_sources.yaml` — [dynamic_data_rules.md §2b](../principles/dynamic_data_rules.md)): field trỏ source sai owner sub-system, hoặc sub-system no-source không đánh `[UNRESOLVED-BACKEND]` → FAIL. Vi phạm → DỪNG, route lại theo §2b rồi mới PASS.
8. **Kiểm tra tính toàn vẹn file:** Cập nhật 5.3/5.4/5.6 vào cuối markdown (Tuân thủ [principles/markdown_safety_rules.md](../principles/markdown_safety_rules.md)).
9. **Báo cáo hoàn tất + Batch Review Gate (theo lane):** In đường dẫn cả 3 artifact + thống kê (`automate/manual/exploratory`, số ui_schema còn thiếu cho automation) ra chat.
   - **Lane `batch`:** đây là **HITL gate gộp duy nhất** cho phần testcase. Trước khi mở, **bắt buộc** Math Check (R2) + Sync Invariant 3 chiều PASS *toàn slice* (đã guard ở Step 02/03). In **bảng tổng hợp đầy đủ mọi màn / mọi `@id`** rồi bật `RequestFeedback: true`, DỪNG chờ User duyệt 1 lần (xem [run_mode_rules.md](../principles/run_mode_rules.md) §3).
   - **Lane `full`:** từng màn đã duyệt ở Step 03 → ở đây chỉ chốt finalize (giữ HITL finalize như cũ).
   - Gợi ý bước kế: `/ntapp-qa-robot {id}` (chạy automate) hoặc [Step 05](step-05-roundtrip.md) (round-trip).
