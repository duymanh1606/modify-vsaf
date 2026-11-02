# STEP 01: AMBIGUITY & QUALITY AUDIT (MODE 1: AUDIT)

> **Acting as:** [Senior QA Engineer](../agents/agent_qa_auditor.md)
> **Tuân thủ:** [ntapp-core-compliance.md](../references/ntapp-core-compliance.md) (Zero-Fabrication, Zero-Summarization, Traceability) + [no-hallucination-rule.md](../references/no-hallucination-rule.md) — Đặc biệt Zero-Fabrication (cấm bịa giải pháp cho gap) và Missing Input Handling (thiếu input → DỪNG, hỏi user, không mock).

---

## 1. Mục tiêu
Rà soát toàn diện các tài liệu đặc tả và **file thiết kế chi tiết `{id}_detailed_design.md`** để tìm ra các rủi ro, lỗ hổng logic nghiệp vụ, các tham số biên mập mờ và các vấn đề tích hợp trước khi tiến hành viết kịch bản kiểm thử.

## 2. Nguyên liệu đầu vào (Input)
- **Tài liệu nguồn (BẮT BUỘC đối chiếu — xem §3 mục 2: Cross-Unit & Cross-Document Gaps):** BE = `{module}_techspec.md` + Module 0 (`00_system_connectivity_integration.md`) + `project_wbs.md`; FE = `ux_design.md` + `{fe}_techspec.md`; chung = `prd.md`.
- **Thiết kế chi tiết** — đọc file `{detailed_design_root}/{id}_detailed_design.md` của **mỗi** unit; **bỏ phần Đảm bảo chất lượng / Kiểm thử** (heading — **không phân biệt hoa/thường** — chứa "chất lượng", "kiểm thử", "quality assurance" hoặc "testing"/"test"; thường là Mục 5 — bỏ từ heading đó đến ngay trước mục kế tiếp), vì phần này chứa KBKT nhúng sẵn, không dùng để audit.

> **SLICE mode:** `{id}` là SLICE ⇒ đọc file `{unit}_detailed_design.md` của **MỌI** unit trong `units:` (vẫn bỏ phần Đảm bảo chất lượng / Kiểm thử).

---

## 3. Chỉ thị thực thi chi tiết
1. **Kiểm tra đầu vào (Missing Input Handling)**: Đảm bảo các file input tồn tại và đọc được. Nếu thiếu, dừng ngay lập tức và báo cáo lỗi cho người dùng.
   - **Gate độ phủ (bắt buộc):** Liệt kê **mỗi unit** vào bảng pre-flight; **đọc file `_detailed_design` của MỌI unit** rồi mới kết luận. Bỏ sót unit = audit chưa xong.
   - **Cảnh báo:** phần Ma trận đồng bộ (Sync Matrix) trong DD mỗi unit chỉ chứng minh nhất quán **TRONG** unit đó — KHÔNG suy ra nhất quán cross-unit. Audit phải tự dựng lớp cross-unit (xem §3 mục 2 — Cross-Unit Contract Gaps).
2. **Quét chéo đa tầng để phát hiện Gaps** — chạy **ĐỦ** cả 2 bộ rule dưới; im lặng / lệch ở điểm nào → GAP + `[TBD]`:

   | Bộ rule | Gồm |
   |---|---|
   | [contract-consistency-rules.md](../references/contract-consistency-rules.md) | Contradiction & Core (Logic/Parameter/UI-Logic) · **Navigation/Post-action routing** · **cụm "A HOẶC B" tất định** · Cross-Unit Contract · Cross-Document · FE↔BE parity |
   | [behavior-completeness-rules.md](../references/behavior-completeness-rules.md) | Cross-System State-Sync · List/collection completeness · Field-Level Expectation Gate |

3. **Tuân thủ Zero-Fabrication (Cấm tự bịa)**: Không tự giả lập phương án giải quyết cho các lỗ hổng phát hiện được. 
4. **Tạo báo cáo Q&A**: Sử dụng template `../templates/qa_report_template.md` để ghi nhận các điểm mập mờ thành danh sách câu hỏi [TBD] cho người dùng/PO trả lời.

---

## 4. Đầu ra yêu cầu
- File báo cáo chất lượng: **`{qa_artifacts}/{id}/{id}_qa_report.md`** — đặt trong **thư mục con riêng theo chức năng** `{id}` (vd `test/HUB-01/HUB-01_qa_report.md`, `test/SLICE-03/SLICE-03_qa_report.md`), KHÔNG gom chung vào `reviews/` (template `../templates/qa_report_template.md` — theo đúng bố cục template).
- **Bố cục dễ đọc (bắt buộc):** (1) header + **bảng "📚 Tài liệu tham chiếu" đặt NGAY ĐẦU** (cột đầu = **tên file ĐẦY ĐỦ** bọc link tương đối từ root workspace + phiên bản; KHÔNG để bảng này xuống cuối) + "Cách dùng" → (2) mục 1 Pre-flight → (3) **3 bảng theo mức 🔴 Cao / 🟡 Trung bình / ⚪ Thấp**, mỗi mức 1 bảng, **cùng 5 cột đúng thứ tự: `Mã · Trạng thái · Vấn đề là gì & vì sao quan trọng · Phương án (✓=nên) · Trả lời`** → (4) GHI CHÚ.
- **Cột "Trạng thái" (cột 2, ngay sau Mã):** tick 1 trong 3 — **Todo** (mới, mặc định) · **Resolved** (đã có Trả lời) · **Pending** (đã trả lời nhưng cần làm rõ thêm). Render checkbox stack `☑&nbsp;Todo<br>☐&nbsp;Resolved<br>☐&nbsp;Pending`.
- **Cột "Vấn đề" (quan trọng nhất — để ai đọc cũng hiểu):** mỗi ô gồm **1 tiêu đề đậm** + các dòng có **NHÃN CỐ ĐỊNH**, mỗi nguồn 1 dòng, **trích dẫn clickable ĐẶT Ở ĐẦU DÒNG** dạng `**[<tên file ĐẦY ĐỦ> §<mục> · dòng <N>](<link>#L<N>):** <file này nói gì>`, kết thúc bằng dòng `**⇒ Hậu quả:** <chặn demo / expected mơ hồ / lọc sai…>`. TUYỆT ĐỐI KHÔNG viết tắt tên file (không `DD`/`L2`/`M0` trong link), KHÔNG telegraphic, KHÔNG để trích dẫn trôi về cuối câu, KHÔNG nhồi nhiều nguồn vào 1 câu dài. Link = đường dẫn tương đối từ root workspace + anchor `#L<N>` (range → dùng dòng đầu).
- **Mâu thuẫn cấp tài liệu** (Module 0 / techspec / ux / prd lệch nhau, hoặc 1 file tự mâu thuẫn): KHÔNG tách bảng riêng — đưa thành GAP trong 3 bảng theo mức (nếu ảnh hưởng testcase), hoặc gộp vào mục "Vệ sinh tài liệu" trong GHI CHÚ (nếu chỉ là drift version/số dòng, không chặn test). Luôn trích file/§/dòng.
- Đánh số `GAP-NN` **liên tục xuyên suốt 3 bảng** (không reset theo mức). Mỗi phương án A/B/C ngắn gọn, ô "Trả lời" để trống cho PO điền.
- **GATE:** chỉ chuyển sang Mode 2 GENERATE khi **mọi điểm 🔴 Cao = Resolved** (cột Trạng thái, do PO/Lead chốt). Điểm 🟡/⚪ chưa Resolved → có thể ghi nhận rủi ro và tiếp tục.

---
