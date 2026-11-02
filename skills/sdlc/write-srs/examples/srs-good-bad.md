# Few-shot: SRS Good vs Bad

> Nạp bởi `sdlc-write-srs` Bước 3 ở mode `standard`/`full` (mode `draft` bỏ qua).
> Mục đích: ổn định chất lượng sinh cho **FR / BR / UC / Data Model / NFR**. Bám mẫu Good, tránh lỗi mẫu Bad.
> Nguyên tắc chung: mỗi mục **truy vết được nguồn**, **đo được**, **không bịa**. Thiếu → `{{Cần bổ sung}}`.

---

## 1. Functional Requirement (§5)

**❌ Bad**
> FR-05-02: Hệ thống xử lý hồ sơ nhanh và thông báo cho người dùng khi cần.

Lỗi: "nhanh", "khi cần" mơ hồ; không rõ actor/điều kiện/kết quả; không truy nguồn PRD.

**✅ Good**
> **FR-05-02** (nguồn: PRD FR-05): Khi *Nhân viên thẩm định* nhấn **Phê duyệt** trên màn hình `SCR-05-01`, hệ thống chuyển hồ sơ sang trạng thái `APPROVED`, publish event `LOAN_APPROVED`, và gửi thông báo cho khách hàng trong `{{Cần bổ sung: SLA thông báo — PRD chưa nêu}}`.
> - **Actor:** Nhân viên thẩm định
> - **Tiền điều kiện:** hồ sơ ở trạng thái `UNDER_REVIEW`
> - **Kết quả:** trạng thái = `APPROVED`; event `LOAN_APPROVED` phát tới `notification-service`

---

## 2. Business Rule (§7)

**❌ Bad**
> BR: Khoản vay phải hợp lệ thì mới được giải ngân.

Lỗi: "hợp lệ" không định nghĩa; không mã BR; không điều kiện kiểm được.

**✅ Good**
> **BR-07-03** (nguồn: PRD §Business Rules, invariant `LEP-INV-04`): Chỉ giải ngân khi *tất cả* điều kiện đúng:
> 1. Trạng thái hồ sơ = `APPROVED`
> 2. Đã ký hợp đồng điện tử (`contract.signed = true`)
> 3. Số tiền giải ngân ≤ hạn mức duyệt (`disbursed_amount <= approved_limit`)
>
> Vi phạm → chặn giao dịch, trả mã lỗi `ERR-DISB-001` (§7 Error Codes).

---

## 3. Use Case (§5)

**❌ Bad**
> UC: Người dùng đăng nhập rồi làm các thao tác trên hệ thống.

Lỗi: thiếu Pre/Main/Alt/Exception/Post; goal không rõ; không thể test.

**✅ Good**
> **UC-05-01 — Nộp hồ sơ vay** (actor: Khách hàng)
> - **Precondition:** đã eKYC thành công; chưa có hồ sơ `PENDING` cùng sản phẩm.
> - **Main flow:** 1) chọn gói vay → 2) nhập số tiền/kỳ hạn → 3) xác nhận điều khoản → 4) hệ thống tạo hồ sơ `PENDING`, phát `APPLICATION_CREATED`.
> - **Alternative:** A1 — số tiền ngoài hạn mức gói → hiện cảnh báo, quay lại bước 2.
> - **Exception:** E1 — mất kết nối scoring-service → lưu nháp, hiển thị `ERR-SCR-timeout`, cho retry.
> - **Postcondition:** hồ sơ `PENDING` tồn tại; audit log ghi nhận.

---

## 4. Data Model (§4)

**❌ Bad**
> Bảng LoanInfo lưu các thông tin khoản vay và một vài trường khác.

Lỗi: "một vài trường khác" mơ hồ; không kiểu dữ liệu; không khoá/quan hệ; tên không theo glossary.

**✅ Good**
> **Entity `LoanApplication`** (tái dùng tên từ Reuse Index — feature `onboarding`):
>
> | Field | Kiểu | Ràng buộc | Ghi chú |
> |-------|------|-----------|---------|
> | `application_id` | UUID | PK | |
> | `customer_id` | UUID | FK → `Customer` | |
> | `status` | enum | `PENDING/UNDER_REVIEW/APPROVED/REJECTED/DISBURSED` | khớp state machine §6 |
> | `approved_limit` | decimal(15,2) | ≥ 0 | `{{Cần bổ sung: trần hạn mức — PRD chưa nêu}}` |
>
> Quan hệ: `Customer 1..* LoanApplication`. Kafka event khi tạo: `APPLICATION_CREATED` (consumer: `decision-service`).

---

## 5. NFR (§8)

**❌ Bad**
> Hệ thống phải nhanh, ổn định và bảo mật.

Lỗi: không con số, không đo được, không kiểm thử được.

**✅ Good**
> - **Performance:** API `POST /applications` p95 ≤ 800ms ở 200 TPS (nguồn: ADR §NFR). *(không có trong ADR → `{{Cần bổ sung}}`, KHÔNG tự chế số)*
> - **Reliability:** khả dụng 99.9%/tháng; retry 3 lần với backoff cho call scoring-service.
> - **Security:** mọi endpoint yêu cầu JWT; dữ liệu CMND/CCCD mã hoá at-rest + masking khi log.
