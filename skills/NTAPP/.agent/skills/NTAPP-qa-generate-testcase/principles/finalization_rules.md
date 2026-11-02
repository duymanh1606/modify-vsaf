# FINALIZATION RULES — Quy tắc Hoàn thiện Data và Defect Management

> **Mục đích:** Quy định cách điền thông tin phụ trợ và đóng gói tài liệu kiểm thử ở Step 04.

---

## 1. Các Chốt Chặn Bắt Buộc

1. **Đọc dữ liệu thiết kế (FETCHING GATE):** 
   - Đọc file testcase hiện tại: `{qa_artifacts}/{id}/{id}_detailed_test_manual_testcase.md`.
   - Đọc phần Dữ liệu trong `_detailed_design` của các Backend Unit để lấy schema, ràng buộc DB.
2. **Nạp cấu trúc Template (PRE-FLIGHT GATE):** 
   - Đọc mục 5.3, 5.4 và **5.6** trong template `references/templates/slice_testcase_table_template.md`. **KHÔNG còn Mục 5.5 charter** (rủi ro CH-CMP/CH-FLEX/gap-spec đã materialize thành case scripted KHỐI 2/3 ở Step 02b/03).

## 2. Chi tiết thực hiện

1. **Hoàn thiện `fixtures.yaml` (DATA canonical):** Hợp nhất toàn bộ `fixtures[]`/`datasets[]` mọi bề mặt đã sinh; điền `environment` (base_url, mocks). Điền `automation_prereq` **theo bề mặt**: *(ui)* `ui_schema_required` liệt kê `ui_schema_{id}.json` qa-robot cần · *(service)* `base_url` + `auth` + `api_contract` + `mocks` (các `[Downstream]` cần stub — [service_surface_rules.md §5](./service_surface_rules.md)), KHÔNG cần `ui_schema`. Thiếu → `[TBD]`.
2. **Mục 5.3: Hướng dẫn Data & Environment Setup (E2E):**
   - Tóm tắt người-đọc, trỏ canonical về `fixtures.yaml` (cấm ghi chung chung); nêu dữ liệu mồi mẫu cụ thể (biến, định dạng, giá trị mẫu) + điều kiện môi trường để chạy E2E.
3. **Mục 5.4: Defect Management (Quy trình quản lý lỗi):**
   - Đếm tổng số dòng testcase thực tế đã sinh điền vào mục báo cáo tiến độ `{total_tcs}`.
   - Để trống các chỉ số `{pass_tcs}`, `{fail_tcs}`, `{skip_tcs}` để Tester/round-trip điền sau.
   - Giữ nguyên các mẫu log bug Jira từ template.
4. **Mục 5.6: Coverage Debt Ledger (BẮT BUỘC in ra chat):** Theo [explore_and_consistency_rules.md §3](./explore_and_consistency_rules.md) — liệt kê mọi bất biến đang **nợ** vì spec/contract gap (`<bề mặt × bất biến> · gap-id · @id case [BR] · Q&A blocking`). Rỗng → ghi "Không có nợ coverage". Không để "màu xanh automation" ru ngủ.
5. **Final Sync Audit (toàn slice) — gate gốc + 2 phép chiếu:** Kiểm gate gốc `Y == X` toàn file (`X` = số tổng chốt ở Step 02 plan, gồm cả manual) + phép chiếu 1 (`@id .feature == A+E`, đếm dòng route sang feature) + phép chiếu 2 (`dataset == A`) theo [automation_contract_rules.md §1](./automation_contract_rules.md). `A/E/M` là phân hoạch của `X` theo Exec, KHÔNG đếm lại tổng. ID liên tục, không nhảy cóc (R8).
   - **[HARD CHECK — cross-artifact, cổng terminal]** chạy `comm` (automation_contract §1) — kèm **sàn chống false-pass** (`N_md == A+E`; `N_md==0` → FAIL). `comm` rỗng (thật) mới PASS. Lệch → bổ sung @id thiếu, KHÔNG hạ manual.
6. **Kiểm tra tính toàn vẹn file:**
   - Cập nhật trực tiếp các mục 5.3/5.4/5.6 vào cuối file `{qa_artifacts}/{id}/{id}_detailed_test_manual_testcase.md`.
   - Tuân thủ nghiêm ngặt [principles/markdown_safety_rules.md](../principles/markdown_safety_rules.md) để tránh vỡ bảng/xóa nhầm phần cuối file.
7. **Báo cáo hoàn tất:** In thông báo hoàn thiện + đường dẫn cả 3 artifact + thống kê (`automate/manual/exploratory`, số prereq automation còn thiếu) ra chat.
