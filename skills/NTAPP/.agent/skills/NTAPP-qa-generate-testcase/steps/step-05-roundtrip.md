# STEP 05: ROUND-TRIP (Delta update + Result ingestion)

> **Acting as:** [Senior QA Engineer](../agents/agent_generate_manual_testcase.md)
> **Tuân thủ:** [principles/incremental_update_rules.md](../principles/incremental_update_rules.md) · [principles/iron_rules.md](../principles/iron_rules.md) (R6)
> **Vị trí:** (a) **Entry-mode `delta`** — vào THẲNG đây từ [Step 00](step-00-shiftleft-gate.md) khi auto-detect 3 artifact đã tồn tại (bỏ qua Step 01–04, xem [run_mode_rules.md](../principles/run_mode_rules.md) §5); hoặc (b) chạy SAU [Step 04](step-04-finalize-testcase.md) như bước tùy chọn khi đã có `results/` từ qa-robot.
> **Fallback:** nếu delta phủ rộng (>40% màn / đổi cấu trúc luồng E2E) → KHÔNG dùng delta, chuyển về `full`/`batch`.

## 1. Mục tiêu
Đóng vòng lifecycle: cập nhật delta khi SLICE/spec đổi, và nuốt ngược kết quả automation để điền Mục 5.4 + chọn regression.

## 2. Các Bước Thực Hiện

### Nhánh A — Delta update (slice/spec đổi)
1. Phát hiện thay đổi so với artifact hiện có theo [incremental_update_rules.md](../principles/incremental_update_rules.md) §1 (unit thêm/gỡ, nhãn Giao diện, logic/dữ liệu).
2. In **delta map** (`@id`/`@rule`/`@scr` bị ảnh hưởng) ra chat trước khi sửa.
3. Regen đúng phần delta trên cả 3 artifact (`.feature`, markdown, `fixtures.yaml`); đánh dấu `@regression` các case logic đổi.
4. Chạy lại **Math Check Gate (R2)** + **Sync Invariant 3 chiều** trên toàn file; đảm bảo ID liên tục (R8).

### Nhánh B — Result ingestion (có results/ từ qa-robot)
5. Đọc `results/output.xml` (read-only) → map test ↔ `@id`.
6. Điền `{pass_tcs}`/`{fail_tcs}`/`{skip_tcs}` vào Mục 5.4 markdown từ kết quả thật.
7. Gắn `@regression` cho case `@exec:automate` PASS ổn định → liệt kê tập regression guard ra chat (đầu vào cho `/bmad-testarch-ci`).
8. Báo cáo: tổng case, tỉ lệ pass, danh sách `@id` cần chạy lại chọn lọc (nếu delta).

> **Ranh giới (R6):** Chỉ ghi canonical vào `{qa_artifacts}`; chỉ ĐỌC `results/` của code repo; KHÔNG thực thi test, KHÔNG sửa Robot code.
