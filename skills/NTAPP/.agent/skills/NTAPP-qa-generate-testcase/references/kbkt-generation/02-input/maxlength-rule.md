---
cases_count: 6
---

# Maxlength Rule

## Mục đích

Sinh testcase kiểm tra giới hạn độ dài field.

## Điều kiện kích hoạt

Kích hoạt khi field có maxlength trong UI/API/DB/DD hoặc KBKT cũ.

## ⚠️ BA con số — CẤM lấy nhầm nguồn (điểm mù kinh điển)

Bug hay lọt vì tester/agent lấy `N` từ **attribute DOM** rồi test biên quanh đó — trong khi giới hạn nghiệp vụ + giới hạn BE ở chỗ khác, nên input phá luật hoặc không bao giờ bị gõ, hoặc lọt tới server rồi nổ lỗi lạ. Bắt buộc tách **3 con số**:

- `N_spec` = giới hạn nghiệp vụ trong spec (phần Logic/Dữ liệu của `_detailed_design`) — **mốc chính để tính BVA (N-1 / N / N+1)**.
- `N_attr` = giá trị attribute `maxlength` render thực tế trong DOM (FE).
- `N_be` = giới hạn BE **thực thi**: `@Size(max=)` / độ dài cột DB / validation payload (phần Hợp đồng API / Logic BE của `_detailed_design`).

**Nguồn đọc + fallback (KHÔNG bịa số):** `N_spec` từ spec/DD Logic — im lặng → `[TBD]`+Q&A. `N_attr`/`N_be` ưu tiên đọc DD *Giao diện*/*Hợp đồng API* + `ui_schema` + techspec DB; **không khai trong tài liệu → quan sát runtime** (inspect DOM đọc attribute cho `N_attr`; Postman gửi payload dài dò mốc reject cho `N_be`) — đây là quan sát hành vi, KHÔNG phải đọc code. Chưa quan sát được → `[TBD]`, tuyệt đối không đặt số.

**Hoà giải 3 nguồn (BẮT BUỘC):** so `N_spec` ↔ `N_attr` ↔ `N_be`. Lệch bất kỳ cặp nào → **GAP mâu thuẫn** (`[TBD]`, không tự chọn). BVA drive quanh `N_spec`, NHƯNG **mốc enforce thật = min(N_attr-clamp, N_be)** — đây mới là chỗ hành vi đổi.

**Ca bắt buộc khi `N_attr > N_be` (FE cho gõ nhiều hơn BE nhận — điểm mù chết người):** FE KHÔNG clamp tại `N_be` ⇒ input dài `(N_be+1 .. N_attr)` **lọt tới server**. PHẢI sinh 1 ca: gõ `N_be + 1` ký tự → trigger search/submit → tới BE → **đúng 1 lỗi validation, neo đúng field, gọi đúng tên field của nó, KHÔNG phải lỗi hệ thống/generic, KHÔNG kèm toast trùng** (áp [inline-error-rule §Expected + reject](../06-validation/inline-error-rule.md) cho trigger over-length này, không chỉ cho regex-fail). Đây đúng lớp bug "FE 100 / BE 64 → gõ >64 nổ cả toast + inline sai field".

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

> **Nguồn N (bắt buộc):** trích verbatim từ spec của chính control đang test, không lấy từ control khác — xem [no-hallucination-rule §Value Provenance](../00-core/no-hallucination-rule.md).

Với maxlength = N:

1. Nhập N - 1 ký tự.
2. Nhập N ký tự.
3. Nhập N + 1 ký tự.
4. Copy/paste N + 1 ký tự.
5. Kiểm tra lưu thành công với N ký tự nếu field hợp lệ.
6. Kiểm tra không bị cắt sai tiếng Việt có dấu/Unicode nếu field cho phép Unicode.
7. **(BẮT BUỘC — boundary-agnostic, chạy được KỂ CẢ khi `N_be`=[TBD]) Kiểm chất-lượng-lỗi over-limit:** Nhập chuỗi **vượt rõ rệt** (dài hơn hẳn `N_spec` — vd ≥ 2×N_spec, hoặc 200 ký tự nếu N_spec nhỏ) → bấm search/submit cho input tới BE → assert **CHẤT LƯỢNG lỗi**, KHÔNG cần biết mốc chính xác: **đúng 1 lỗi** (không kèm toast/inline trùng) · **neo + gọi đúng tên field của nó** · **loại = validation, KHÔNG phải "hệ thống gián đoạn"/5xx**. Đây là lưới bắt lớp bug "FE cho nhiều hơn BE" mà không phụ thuộc `N_be`.
8. **(Tinh chỉnh mốc — chỉ khi xác định được `N_be < N_attr`)** Drive đúng `N_be + 1` để chốt biên BE thật (giá trị lấy từ DD hoặc Postman-probe; chưa có → `[TBD]`, bỏ ca này, KHÔNG đoán mốc).

## Expected chuẩn

- N - 1: cho nhập và hiển thị đủ.
- N: cho nhập và hiển thị đủ.
- N + 1: đúng 1 hành vi over-limit spec đã chốt (chỉ 1 trong: chặn nhập / auto-cut tại N / báo lỗi) — spec chưa chốt → Q&A, không tự chọn.
- Không được làm mất ký tự hợp lệ trước giới hạn.
- **Over `N_be` (khi `N_attr > N_be`):** input tới BE → **đúng 1 lỗi validation** đúng field + đúng loại; CẤM kỳ vọng "hệ thống gián đoạn"/lỗi 5xx cho lỗi độ dài, CẤM chấp nhận nhiều lỗi (toast + inline) cùng lúc. Nếu runtime hiện đa lỗi/sai field/sai loại → đó là BUG (log defect, không sửa expected về khớp bug).

## Template

```text
Hệ thống hiển thị đúng thông tin dữ liệu đang nhập là <data_N_chars>.
```

```text
Hệ thống tự động dừng khi đủ <N> ký tự, không cho nhập ký tự thứ <N+1>.
```

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ hành vi khi vượt maxlength:

- Chặn nhập?
- Tự cắt?
- Báo lỗi inline?
- Báo lỗi toast khi lưu?
