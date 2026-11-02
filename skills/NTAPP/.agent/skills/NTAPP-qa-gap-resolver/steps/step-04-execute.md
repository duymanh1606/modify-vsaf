# STEP 04: EXECUTE & GATE 2 (Phase 2 — Execute)

> **Acting as:** Senior Engineer / Tech Lead
> **Tuân thủ:** [priority-resolution-rule.md](../references/priority-resolution-rule.md), [no-hallucination-rule.md](../references/no-hallucination-rule.md)
> **Chỉ chạy sau khi người dùng đã chọn gap ở GATE 1.**

## 1. Mục tiêu
Thực thi các gap đã được chọn: sửa docs trực tiếp, sinh diff cho code, giữ gap nghiệp vụ chờ PO. Xử lý **song song theo file đích**.

## 2. Gom theo FILE ĐÍCH (bắt buộc — chống ghi đè lẫn nhau)
Từ "Việc cần làm" của các gap đã chọn (Step 02 phần 6), **gom theo file đích, KHÔNG theo gap**:
- Nhiều gap cùng đụng 1 file (vd GAP-01/02/03/04/06 đều regen `HUB-02/f2`) → **1 worker cho file đó**, áp *tất cả* thay đổi liên quan cùng lúc.
- Song song là **giữa các file khác nhau**, không phải giữa các gap. Hai worker không bao giờ ghi cùng 1 file.
- Dùng subagent per-file-đích cho các file độc lập; chờ tất cả xong rồi mới sang GATE 2.

## 3. Thực thi theo loại (dựa trên nhãn phân loại)

| Nhãn / loại đích | Hành động | Ràng buộc |
|---|---|---|
| **stale-docs → DD part** | Regen DD part theo canonical đã chốt: **gọi skill `NTAPP-feature-design` / `NTAPP-dd-design`** đúng convention (header `id:` + bump `dd_version`, format part) | KHÔNG tự tay viết part lệch convention; tôn trọng pre-commit hook |
| **stale-docs / code-mới-docs-cũ → TechSpec / Module 0 / ux / wbs** | Sửa docs trực tiếp tại đúng §/dòng cho khớp giá trị canonical (hoặc khớp code nếu `code-mới-docs-cũ`) | Sửa tối thiểu, đúng chỗ; giữ nguyên phần khác |
| **lệch-code-vs-contract (bug) → code** | **CHỈ sinh diff + lý do**, trình bày cho user duyệt (và tuỳ chọn ghi `{qa_artifacts}/reviews/{id}_code_diff_proposals.md`) | **TUYỆT ĐỐI KHÔNG tự sửa/commit code.** Nêu rõ file, hàm, thay đổi, rủi ro (tài chính) |
| **mơ-hồ-nghiệp-vụ** | KHÔNG execute | Giữ Trạng thái `Todo`, ghi rõ đang chờ PO |

> Nếu một docs edit tự chế có thể tốt hơn khi delegate (DD part) → luôn ưu tiên gọi skill chuyên biệt. Với hệ tài chính: BigDecimal/transaction/idempotency/audit — dù chỉ là diff đề xuất, phải nêu rõ tác động (xem be-finance-rules).

## 4. Cập nhật report gốc sau execute
Với mỗi gap đã xử lý xong (docs đã sửa, hoặc diff đã trình):
- **Docs đã sửa trực tiếp** → cột Trạng thái `→ Resolved`; cột Trả lời thêm `✓ Đã xử lý: <file đã sửa / DD đã regen>`.
- **Code (diff đề xuất)** → giữ `Pending`; ghi `⏳ Diff code chờ dev duyệt: <file>`. KHÔNG flip Resolved vì code chưa merge.
- **mơ-hồ-nghiệp-vụ** → giữ `Todo`, ghi `⏸ Chờ PO chốt`.

Cập nhật cả section "## PHÂN TÍCH & ĐỀ XUẤT (AI)": thêm dòng "Kết quả execute {date}" dưới gap tương ứng.

## 5. Rà lại code đã đụng (nếu Phase 2 có sinh diff code BE)
Trước GATE 2, tự review diff code đề xuất theo [be-finance-rules] + rule Sonar (S3776, S1192, S125, S1128…) đã nêu trong CLAUDE.md của dự án; nêu vi phạm (nếu có) trong báo cáo. Diff docs không áp rule code.

## 6. GATE 2 (bắt buộc — DỪNG)
Báo cáo cuối:
- **Đã sửa trực tiếp:** danh sách file docs/DD + tóm tắt thay đổi.
- **Diff code chờ duyệt:** danh sách + rủi ro.
- **Còn chờ PO:** gap `mơ-hồ-nghiệp-vụ`.
- **Trạng thái report:** bao nhiêu Resolved / Pending / Todo.
Nhắc user: gap 🔴 chỉ mở gate viết testcase khi = Resolved (theo report gốc).
