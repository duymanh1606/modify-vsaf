---
cases_count: 8
---
# Inline Error Rule

## Mục đích

Chuẩn hóa cách sinh testcase validate lỗi inline.

## Điều kiện kích hoạt

Khi field có validate: required, format, maxlength, business rule, duplicate, invalid relation.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Trigger lỗi bằng focus out (click vào field → click ra ngoài) nếu spec yêu cầu.
2. Trigger lỗi bằng nhấn Lưu/Áp dụng **chỉ khi nút submit vẫn click được lúc form invalid** (xem "Chọn cách trigger đúng").
3. Kiểm tra vị trí (neo đúng field) + loại message lỗi (inline validation, không phải toast/lỗi hệ thống generic).
4. Kiểm tra nội dung message lỗi.
5. Kiểm tra màu sắc/icon lỗi nếu UI design có quy định.
6. Kiểm tra lỗi biến mất khi nhập lại dữ liệu hợp lệ.
7. Kiểm tra button Lưu có enable/disable theo trạng thái lỗi.
8. Nếu nút submit disabled khi form invalid: trigger lỗi bằng focus-in → blur-out, KHÔNG dùng bước "bấm Lưu/Submit" (nút disabled không click được).

## Chọn cách trigger đúng (BẮT BUỘC — tránh mâu thuẫn với case #7)

Bước trigger PHẢI khớp cơ chế lỗi thật nổi lên:

- **Lỗi required/empty** (field bỏ trống): chỉ nổi khi field ở trạng thái `touched` → trigger = **click vào field → click ra ngoài (blur)**.
- **Nút submit disabled khi invalid** (case #7 khẳng định): nút disabled → KHÔNG click được → KHÔNG được viết bước "Bấm <Submit> để hiện lỗi". Dùng focus-in → blur-out.
- **Nút submit vẫn enabled khi invalid**: mới được dùng "nhấn Lưu/Áp dụng" làm trigger.

> [!CAUTION]
> **Cấm mâu thuẫn:** với CÙNG một field, KHÔNG sinh đồng thời case "bấm Submit → hiện lỗi" (#2) và case "Submit disabled khi field lỗi" (#7). Nếu #7 đúng thì #2 phải chuyển sang focus-in/blur-out (#8). Không rõ trạng thái nút → tạo Q&A.

## Expected chuẩn

```text
Hiển thị báo lỗi inline ngay dưới trường dữ liệu với nội dung: <message>.
```

```text
Khi nhập lại dữ liệu hợp lệ, message lỗi không còn hiển thị và field trở về trạng thái bình thường.
```

## Exclusivity + message-correctness áp cho MỌI trigger (không chỉ 1)

> [!CAUTION]
> Điểm mù kinh điển: agent chỉ gắn check "đúng 1 lỗi / đúng field / đúng loại" vào **một** trigger đại diện (thường là regex-fail, vd `"đx"`) rồi coi như xong. Nhưng đa lỗi/sai field/sai loại thường **chỉ nổ trên trigger khác** (đặc biệt **over-length lọt tới BE** khi `N_attr > N_be` — xem [maxlength-rule](../02-input/maxlength-rule.md)).
>
> BẮT BUỘC: liệt kê **tất cả đường sinh lỗi** của field (required/empty · sai format-regex · **over-length tới server** · min/max nghiệp vụ · duplicate · invalid relation) và áp check #3 (đúng loại + neo đúng field) + reject "sai field / sai loại / >1 lỗi" cho **TỪNG đường**, không dùng lại 1 trigger cho tất cả. Trigger nào chưa rõ hành vi → Q&A, không bỏ qua.

## Điều kiện reject

- Không được để message là `???`.
- Không được viết `Báo lỗi phù hợp`.
- Không được thiếu vị trí hiển thị lỗi.
- Lỗi validation hiển thị dưới dạng lỗi hệ thống/generic (sai loại) hoặc gắn sai field.
- Xuất hiện >1 thông báo lỗi khi spec chỉ định 1 (toast generic thừa) — xem [kbkt-format-rule §Chất lượng Expected](../00-core/kbkt-format-rule.md).
