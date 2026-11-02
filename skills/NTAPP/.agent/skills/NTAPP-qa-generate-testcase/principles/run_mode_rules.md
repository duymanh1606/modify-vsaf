# RUN MODE RULES — 3 lane chạy + Context Ledger + batch-gate

> **Mục đích:** Giảm ceremony, mở incremental, chống context-drift trên SLICE lớn — **mà không nới Iron Rules**.
> Cùng một skill, 3 lane khác nhau ở *tần suất dừng người* (HITL) + *phạm vi reload tài liệu* + *điểm vào (entry)*.
> Chất lượng (R1 zero-fabrication, R2 Math Check, R6 canonical-only, R8 ID liên tục, Sync Invariant 3 chiều) **enforce ở MỌI lane**.

---

## 1. Resolve `run_mode`

Thứ tự ưu tiên (cao → thấp):
1. **Ý định người dùng trong câu lệnh:** "chế độ nhanh / batch" → `batch`; "cập nhật / sửa label / chạy lại delta" → `delta`; "đầy đủ / governance / audit" → `full`.
2. **Layer 3 `.bmm-config.yaml`** mục `ntapp-qa-generate-testcase:` key `run_mode`.
3. **Auto-detect (chỉ gợi ý, không tự ép):** ở [Step 00](../steps/step-00-shiftleft-gate.md), nếu **đã tồn tại đủ 3 artifact** của `{id}` (`{id}_testspec.feature` + `{id}_detailed_test_manual_testcase.md` + `{id}_fixtures.yaml`) tại `{qa_artifacts}/{id}/` → **đề xuất** `delta` và hỏi 1 lần; người đồng ý mới vào delta.
4. **Default = `full`** (backward-compat tuyệt đối: project cũ không khai `run_mode` → hành vi y như trước).

---

## 2. Ma trận 3 lane

| Đặc tính | `full` *(default)* | `batch` | `delta` |
|---|---|---|---|
| **Khi dùng** | Slice mới quan trọng, cần governance/audit | Lặp nhanh, slice mới nhưng tin tay nghề, muốn ít gián đoạn | Re-run trên slice **đã có** 3 artifact (đổi unit / label / logic) |
| **Entry point** | Step 00 → 01 → … | Step 00 → 01 → … | **Bỏ qua** 00/01/02 → vào thẳng [Step 05 Nhánh A](../steps/step-05-roundtrip.md) |
| **HITL gate** | 4 (E2E flow + Plan + per-screen + finalize) | **2**: ① E2E flow (Step 01) ② Batch review *toàn bộ* testcase cuối (Step 04) | **0–1**: in delta-map chờ 1 OK rồi patch |
| **Giữa các màn** | Dừng từng màn | **Auto-proceed** (không dừng) | n/a (chỉ chạm màn delta) |
| **9 checkpoint (Step 02)** | Chạy + narrate đầy đủ | Chạy **im lặng**, chỉ in `X = Y` tổng hợp | Chỉ chạy trên màn bị ảnh hưởng |
| **Reload tài liệu** | Per-screen reload đầy đủ | **Scoped reload** (Context Ledger + phần Giao diện màn hiện tại) | Chỉ tài liệu của delta |
| **Số lần dừng (slice 20 màn)** | ~41 | ~2 | ~1 |

> **Lưu ý ceremony:** `batch`/`delta` chỉ gộp/bỏ **HITL của người**, KHÔNG bỏ **internal checkpoint**. 9 chốt chặn [slice_planning_rules.md](./slice_planning_rules.md) vẫn chạy để giữ độ phủ; chỉ thôi narrate từng dòng.

---

## 3. Batch-gate (lane `batch`)

- Phân biệt rõ 2 loại cổng:
  - **HITL gate** = cần *người ký* (`RequestFeedback: true`, DỪNG).
  - **Internal checkpoint** = self-audit của AI (Math Check, Sync Invariant, mapping rule) — *không* dừng người.
- Ở `batch`: các HITL gate per-screen của [Step 03](../steps/step-03-write-testcase.md) **chuyển thành "defer"** — không dừng, ghi artifact rồi tự sang màn kế. Tích lũy đến hết màn cuối → **một** batch review ở [Step 04](../steps/step-04-finalize-testcase.md): in **bảng tổng hợp đầy đủ** (mọi màn, mọi `@id`, thống kê automate/manual/exploratory) + kết quả Sync Invariant, rồi mới `RequestFeedback: true` 1 lần.
- **Guard bắt buộc:** trước khi mở batch review, **Math Check Gate (R2)** và **Sync Invariant 3 chiều** phải PASS toàn slice. Nếu lệch ở bất kỳ màn nào → **rớt về dừng-tại-màn-đó** (không cho silent-pass lỗi), báo màn lỗi ra chat.

---

## 4. Context Ledger (load-once — chống drift, giải reload dư)

**Vấn đề:** Step 02/03 hiện ép "tải lại trọn bộ `_detailed_design`" *mỗi màn* → với 20+ màn, phần dùng chung bị đọc lại hàng chục lần. *(Lưu ý: thiết kế đã gộp về 1 file `_detailed_design.md` — "scoped reload" nghĩa là đọc theo **section/heading** cần trong file đó, KHÔNG mở lại toàn file mỗi màn.)* Cùng vấn đề xảy ra với **rule-library tĩnh** (`00-core/*` bắt buộc mọi màn + `01-ui/*` bắt buộc mọi màn FE theo [slice_planning_rules.md §4](./slice_planning_rules.md)) — nội dung các file này **không đổi theo màn**, nhưng nếu không cache thì bị `view_file` lại nguyên vẹn ở mỗi màn.

**Cơ chế:** Tại [Step 01](../steps/step-01-init-slice.md), dựng **một** mục `## Context Ledger` trong `implementation_plan.md`, gom **fact + rule dùng chung toàn slice** (đọc 1 lần):
- **Slice overview**: mục tiêu, danh sách unit + vai trò (Action/Verify/Nav).
- **BE contract map**: endpoint / story-code / bảng DB mà nhiều màn cùng tham chiếu.
- **(KHÔNG dùng Glossary nhãn dùng chung)** — nhãn cụ thể KHÔNG gom về Ledger; **mỗi màn tự liệt kê ĐẦY ĐỦ từng element ở Step 02 (Chốt 3)**. Ledger chỉ giữ luật **UI Text Source Map** (dưới đây) + Bảng Override cho nhãn phải-giống-cross-screen.
- **UI Text Source Map** *(chống bịa text):* mọi chuỗi hiển thị (placeholder/label/option/message/tiêu đề) lấy **verbatim từ DD** (bảng control F-0x / wireframe / text DD trích) + cite `DD §/F-0x`. Generate **chỉ đọc DD + qa_report** (KHÔNG ui_schema/i18n/ux) → DD im lặng hoặc chỉ có i18n-key không kèm text → **`[TBD]`+Q&A**. Cấm cả **bịa** (text không có trong DD) lẫn **over-`[TBD]`** (hạ giá trị đang có trong DD, vd `"Tất cả"` ở F-01). **Label-vs-code drift** (DD stale, vd DD "Áp dụng"/"Cập nhật" nhưng code "Tìm kiếm"/"Thời gian tạo") design-time KHÔNG bắt được → thuộc **runtime**: qa-robot assert text render == expected.
- **Core rules đã nạp**: `view_file` toàn bộ `00-core/*` (+ toàn bộ `01-ui/*` nếu slice có ≥1 FE unit) **một lần duy nhất**, ghi danh sách tên file đã nạp vào Ledger. Đây là rule-library cố định của cả slice, không phải fact riêng màn.

**Per-screen (Step 02/03) — scoped reload:**
- Reload **chỉ**: phần Giao diện của *riêng* màn hiện tại (nhãn + control cụ thể) + phần Logic/Dữ liệu của BE *trực tiếp* map màn đó + các file rule **đặc thù theo control của màn đó** (`02-input/*`, `03-selection/*`, `04-dynamic-form/*`, ... — tùy Bảng Mapping của màn).
- Fact dùng chung → lấy từ **Context Ledger**, KHÔNG đọc lại `_detailed_design` của *mọi* BE.
- **Rule dùng chung** (`00-core/*`, `01-ui/*`) → lấy từ mục "Core rules đã nạp" trong Ledger, KHÔNG `view_file` lại — chỉ cite tên file khi áp dụng. Chỉ `view_file` lại 1 file cụ thể nếu nội dung Ledger cho file đó bị nghi ngờ sai/thiếu.
- **Anti-drift vẫn giữ:** Ledger là nguồn ổn định thay cho "đọc lại tất cả"; nếu màn hiện tại phát hiện mâu thuẫn với Ledger (fact hoặc rule) → cập nhật Ledger (1 dòng) và ghi chú, không reload toàn bộ.

**Ngưỡng slice lớn:** nếu slice > 12 màn Action → Ledger ghi cảnh báo, khuyến nghị chunk sub-batch (xử lý 6–8 màn/đợt) hoặc tách slice. Không tự động tách.

> Context Ledger áp dụng cho **mọi lane** (kể cả `full`) — nó chỉ thay "reload tất cả" bằng "reload có phạm vi", không bỏ bất kỳ tài liệu nào của *màn đang xử lý*.

---

## 5. Delta entry-mode (lane `delta`)

- Điều kiện: 3 artifact của `{id}` đã tồn tại + input (SLICE / `_detailed_design`) đã đổi.
- **Bỏ qua** Step 00/01/02/02b/03 ceremony; vào thẳng [Step 05 Nhánh A](../steps/step-05-roundtrip.md), theo [incremental_update_rules.md](./incremental_update_rules.md) §1:
  1. So khớp theo `@id` + `@rule` + `@scr` → in **delta-map** (mục bị ảnh hưởng) ra chat.
  2. Người xác nhận (1 OK) → patch đúng phần delta trên **cả 3 artifact**.
  3. Chạy lại **Math Check (R2)** + **Sync Invariant 3 chiều** *toàn file*; ID không nhảy cóc (R8).
  4. Đánh dấu `@regression` các case logic đổi → xuất tập regression chọn lọc.
- **Fallback an toàn:** nếu delta phủ rộng (đổi >40% màn, hoặc đổi cấu trúc luồng E2E) → KHÔNG dùng delta; báo và chuyển về `full`/`batch` chạy lại có kiểm soát.

---

## 6. Bất biến chung (mọi lane)

- Iron Rules R1/R2/R3/R6/R8 + Sync Invariant 3 chiều **không đổi** theo lane.
- Triple-emit ([automation_contract_rules.md](./automation_contract_rules.md)) áp dụng như nhau; `emit_automation:false` (legacy) độc lập với `run_mode`.
- Lane chỉ điều chỉnh **khi nào dừng người** và **đọc lại bao nhiêu**, KHÔNG điều chỉnh **độ phủ** hay **độ chính xác**.
