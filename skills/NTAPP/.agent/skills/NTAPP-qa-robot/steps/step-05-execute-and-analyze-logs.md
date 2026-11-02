# STEP 05: CHẠY TEST & PHÂN TÍCH LOG (SELF-HEALING) — TERMINAL

> **Acting as:** [Agent Robot Generator](../agents/agent_robot_generator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R7/R7s (self-heal ≤3 retry; FAIL do bug thật thì KHÔNG self-heal — stopping error #5), R6, R10, R16. Chi tiết: [Robot Rules](../references/automation/auto_robot_rules.md), [Locator Strategy](../references/automation/auto_locator_strategy.md).
> **Điều kiện vào:** [Step 04](./step-04-review-code.md) verdict `PASS`. Chưa review → quay lại Step 04, **KHÔNG chạy `robot`**.
> ⛔ Step CUỐI — không có con trỏ Next **tiến**. Ngoại lệ đi LÙI: sửa code cấu trúc ở step này (dryrun đỏ, contract mismatch) phải quay lại Step 04 theo **§2f** trước khi chạy tiếp.

## 1. Input
* Test suite đã qua review Step 04.
* `datatest/{id}_gen_manifest.yaml` (ghi healed locator).
* `datatest/{id}_gen_manifest.yaml` — lấy `r10_decisions` + `excluded_ids` (và ghi `healed` locator). ⛔ `pending`/`tbd` đọc từ `[Tags]` + `Skip` của suite, không đối chiếu ngược lên manifest.

## 2. Trình tự thực thi

**a0. Chốt env trước khi chạy.** Liệt kê biến còn `[TBD]` → **đọc lại `{qa_artifacts}/data_sources.yaml` (bắt buộc, R5)** rồi 2 nguồn còn lại ở [step-01 §2.6e](./step-01-parse.md) → điền hết thứ tra được. Chỉ hỏi user phần không nguồn nào cấp (thường chỉ mật khẩu + connection DB), kèm sẵn câu lệnh export để điền.

**a. Dryrun compile-check:** 
`robot --dryrun --output NONE --log NONE --report NONE tests/`
Không ghi file nào — lỗi đọc ở console + exit code. Nếu FAIL -> Sửa code và quay lại Step 04 (R12).

**b0. Chạy theo bậc thang — CẤM chạy full ngay lần đầu.** Mỗi bậc: chạy → sửa hết đỏ → mới lên bậc kế. Lỗi hạ tầng lộ ra ở 5 phút đầu thay vì sau 40 phút.

| Bậc | Phạm vi | Mục tiêu |
|---|---|---|
| 1 · smoke | 1 case đại diện + đường đi chung (login → menu → mở màn → mở modal) | thông Suite Setup + Test Setup |
| 2 · đại diện | 1 case cho mỗi `@rule` / mỗi section | lộ hết lỗi locator theo nhóm control |
| 3 · lô | từng nhóm `@rule` (~20-30 ca), lần lượt | lỗi còn lại là của chính nhóm đó |
| 4 · full | cả suite | chỉ chạy khi 2 lô liên tiếp không sinh lỗi locator/hạ tầng mới |

Sau mỗi lần sửa: chạy lại **đúng tập vừa đỏ** (`--rerunfailed <output.xml>`), không chạy lại từ đầu. Bậc 3-4 phát sinh lỗi hạ tầng mới → tụt về bậc 2 cho nhóm đó.

**b. Chạy thật:** 
`robot --variable RUN_ID:<run_id> -d results/run-<run_id> tests/`
(Dùng `pabot` nếu chạy song song). Cấm dùng thư mục kết quả chung chung tránh race condition.
Chạy nền BẮT BUỘC ghi console ra file (`> results/run-<run_id>-console.log 2>&1`) để đọc tiến độ ở §b1.

**b1. Hiển thị tiến độ khi chạy.** Chạy nền thì **cứ ~2 phút in 1 lô ra chat**, đọc từ console log đang ghi — gồm 2 phần:

1. **Từng case đã chạy từ lần in trước** (mới → cũ), mỗi case 1 dòng:
   `<mã case> · <tên rút gọn> · PASS|FAIL|SKIP` — case FAIL kèm luôn message đỏ (1 dòng, ≤100 ký tự).
2. **Dòng tổng:** `[<đã chạy>/<tổng>] đang chạy: <mã case hiện tại> | PASS <n> · FAIL <m> · SKIP <k>`

Cấm chỉ in con số tổng; cấm để user chờ không biết đang ở case nào.

**b2. Ngắt mạch khi đỏ dây chuyền.** Theo dõi log lúc đang chạy, KHÔNG đợi hết suite. **≥5 case đỏ liên tiếp cùng một message → DỪNG run ngay** (chạy tiếp chỉ nhân bản 1 lỗi). Trước khi kết luận nguyên nhân phải **mở screenshot của case đỏ ĐẦU TIÊN** trong chuỗi — suy nguyên nhân từ message mà không xem ảnh là cách bỏ sót lỗi môi trường.

**b3. Ba dấu hiệu lỗi môi trường (không phải lỗi test) — kiểm trước khi sửa bất kỳ locator nào:**
* Màn login xuất hiện giữa suite → **phiên hết hạn**; suite phải tự đăng nhập lại trong Test Setup (self-heal, không nhảy URL), không đánh dấu case là FAIL thật.
* Chuỗi đỏ bắt đầu đúng sau 1 case cụ thể → case đó phá state chung (đăng xuất, xoá storage, để modal treo).
* Mọi case đỏ ở cùng 1 keyword của Setup/Teardown → hỏng state chung, không phải hỏng assert.

**c. Phân loại kết quả (5 bucket):**
* `PASS`: Xanh ngay lần đầu.
* `PASS_AFTER_RETRY`: Đỏ lần đầu nhưng xanh sau retry (Flaky). Nêu rõ số lần retry & nguyên nhân.
* `FAIL`: Đỏ sau khi kết thúc các lượt retry.
* `PENDING(skip)`: Case mang tag `pending` hoặc `tbd` bị SKIP.
* `total`: Tổng số case.

**d. Phân tích & Xử lý đỏ (FAIL):**
* **Locator (UI):** Do DOM thay đổi -> Dò lại locator tĩnh, cập nhật `{Page}Variables.resource`, retry ≤3. Cập nhật manifest `healed: true`.
* **Timing (UI):** Race condition -> Rà lại Smart Wait trong Keywords, retry ≤3.
* **Transient (Service):** Timeout/downstream transient -> Rà lại `Wait Until Keyword Succeeds`, retry ≤3. Cấm thêm `Sleep` tĩnh.
* **Contract mismatch:** Sửa Service Object -> append vào `touched_files` -> Quay lại Step 04 review -> Chạy lại.
* **Phiên hết hạn / state chung hỏng:** sửa Test Setup cho tự phục hồi (đăng nhập lại, đóng modal treo) rồi chạy lại — KHÔNG đếm các case đỏ theo sau vào thống kê FAIL.
* **Bug thật (Assertion/Logic):** DỪNG NGAY, báo user, cấm sửa test để né bug.

**d2. Báo cáo đếm theo GỐC, không theo số case đỏ.** Gom case đỏ theo message + theo keyword hỏng, quy về số nguyên nhân gốc và ghi rõ bao nhiêu case là dây chuyền. "77 đỏ" mà thực chất 4 gốc là con số đánh lừa cả người đọc lẫn chính mình.

**f. Sửa code tại Step 05 (Quy định review lại):**
* **Chỉ đổi giá trị locator** trong `{Page}Variables.resource`: **KHÔNG** cần review lại (self-heal R7).
* **Đổi cấu trúc** (keyword, timeout, import, logic `.robot`...): **CÓ** review lại (quay lại Step 04).

## 3. Hợp đồng Shard & Merge (Chống race condition)

* **`run_id`:** Dạng `<YYYYMMDD-HHMMSS>-<suffix>`, truyền qua `--variable RUN_ID:<giá trị>`.
* **Thư mục kết quả:** `results/run-<run_id>`.
* **Chạy 1 process (`robot`)** → KHÔNG sinh shard: resolver append thẳng vào `results/{id}_data_ledger.md` và `datatest/blacklist/<source_id>.jsonl`. Bỏ luôn lock và bước merge.
* **Chạy song song (`pabot`)** → áp hợp đồng shard dưới đây; xong merge thì **xoá `results/parts/{id}/${RUN_ID}/`**.
* **Shard append-only:** Resolver chỉ append vào shard của chính process, cấm ghi trực tiếp vào file chung:
  * Ledger -> `results/parts/{id}/${RUN_ID}/ledger-<shard>.jsonl`
  * Blacklist -> `results/parts/{id}/${RUN_ID}/blacklist-<source_id>-<shard>.jsonl`. **Tên shard BẮT BUỘC mang `<source_id>`** — bỏ đi thì bước merge (lặp theo từng source) không thấy shard nào, promote 0 record mà không báo lỗi ([db §11.11](../references/automation/auto_db_oracle_rules.md)).
* **Gộp shard (merge) ở cuối run:**
  1. Giành quyền merge bằng cách tạo folder lock `results/.merge-lock-{id}` (`mkdir` nguyên tử).
  2. Gộp các file jsonl shard, dedupe theo khoá (blacklist dedupe theo `subId`, KHÔNG `sort -u`).
  3. Ghi ra file tạm rồi đổi tên đè lên file chung:
     * Ledger -> `results/{id}_data_ledger.md`
     * Blacklist -> `datatest/blacklist/<source_id>.jsonl` (union bản cũ + shard mới, lặp theo từng `source_id`).
  4. Xoá thư mục shard `results/parts/{id}/${RUN_ID}/`, rồi nhả lock bằng cách xoá folder lock.

## 4. Đầu ra yêu cầu
* Báo cáo phân loại **5 bucket** (`PASS` / `PASS_AFTER_RETRY(flaky)` / `FAIL` / `PENDING(skip)` / `total`).
* Danh sách case Pending kèm nhóm và lý do.
* Locator/keyword tự vá (healed: true) kèm số lần retry.
* (Có data mồi) Link `results/{id}_data_ledger.md` kèm thống kê `tái dùng/seed mới/un-consumed` và cảnh báo cạn pool.
* Link tới báo cáo review Step 04.
