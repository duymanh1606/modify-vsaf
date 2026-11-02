# REFERENCE: Từ điển thuật ngữ SRS — dùng từ nào, KHÔNG tự dịch thuần Việt

> **BẮT BUỘC đọc trước khi sinh nội dung SRS** (workflow §4) và **quét lại trước khi publish** (§9).
> Lý do tồn tại: user bác 2 lần vì skill tự dịch thuật ngữ kỹ thuật sang tiếng Việt lạ tai —
> *"Khóa lạc quan là gì vậy? nếu là version thì cứ để là version"*, *"Nhật ký là việc lưu log đúng k → để là 'lưu log' k cần chuyển thuần việt như vậy"* (2026-08-11).

## Nguyên tắc

**Thuật ngữ mà đội dự án vốn nói bằng tiếng Anh thì GIỮ tiếng Anh.** Chỉ dịch sang tiếng Việt khi
từ tiếng Việt đó là cách đội đang thật sự gọi. Người đọc là BA/QA/PO trong đội — họ quen `version`,
`log`, `cache`; họ KHÔNG quen "khóa lạc quan", "nhật ký kiểm toán", "bộ nhớ đệm".

Tự kiểm: đọc câu ra thành tiếng, nếu nghe như bản dịch sách giáo khoa chứ không như lời một
người trong đội nói → dùng từ tiếng Anh.

## Bảng chuẩn hóa (áp dụng cho MỌI trang SRS)

| ❌ KHÔNG dùng | ✅ Dùng | Ghi chú |
|:---|:---|:---|
| khóa lạc quan · optimistic lock (dịch) | **version** | Nói thẳng "version dùng để chống ghi đè khi hai người sửa cùng lúc" |
| nhật ký · nhật ký kiểm toán | **log** | "ghi log", "bảng log", "log lần tạo thất bại" |
| bộ nhớ đệm | **cache** | "tra cache", "ghi cache", "cache giữ 30 giây" |
| mã nối vết | **trace id** | |
| giao dịch (theo nghĩa DB transaction) | **transaction** | ⚠️ Bắt buộc: hệ thống này là hệ tài chính, "giao dịch" nghĩa là giao dịch tiền → dùng "giao dịch" cho DB transaction gây hiểu sai nghiệp vụ |
| ảnh chụp trạng thái | **snapshot** | |
| cờ suy giảm | **cờ degraded** | Giữ "cờ" + từ tiếng Anh |
| bản ghi mồ côi | **bản ghi rác** | Hoặc diễn đạt lại bằng lời |

## Giữ nguyên tiếng Việt (KHÔNG đổi sang tiếng Anh)

`bảng` · `cột` · `trường` · `khóa chính` · `khóa ngoại` · `ràng buộc duy nhất` · `phân vùng` ·
`đối tác` · `sản phẩm` · `chính sách phí` · `hồ sơ tổng hợp` · `yêu cầu thành phần` · `phân hệ` ·
`phiên đăng nhập` · `thẻ đăng nhập` — đây là từ đội đang dùng thật, dịch ngược sang tiếng Anh mới là sai.

## Quy tắc hồi tố

Bảng này **áp cho cả trang đã publish**: khi bổ sung một dòng mới vào bảng, phải quét lại các trang
SRS đã xuất bản và sửa luôn (cùng nguyên tắc "viết rule không tự hồi tố" ở `srs-mapping.md`).
Bổ sung dòng mới mỗi khi user chỉ ra một từ dịch không tự nhiên — đừng chỉ sửa đúng chỗ được chỉ.

## Phạm vi quét — nhớ cả file model sơ đồ

Khi áp bảng này, quét **4 loại file** của mỗi feature ID, không chỉ file chữ:

1. `{id}_srs.md`
2. `{id}_srs_confluence.storage.xhtml`
3. **`{id}-activity.model.json`** — nhãn node/edge của sơ đồ hoạt động
4. `p_screen.html` (nếu là SRS web) — nhãn trên bản mô phỏng màn hình

> **Bài học 2026-08-13 (HUB-01/HUB-02):** đợt chuẩn hóa thuật ngữ 2026-08-11 chỉ quét mục 1 và 2. Hai ngày sau user mở trang và thấy sơ đồ vẫn ghi "bộ nhớ đệm", "mã nối vết", "nhật ký kiểm toán", "suy giảm" — nhãn sơ đồ là thứ người đọc thấy trước cả bảng mô tả. Sửa model xong phải **chạy lại** `build-activity-diagram.mjs` rồi publish lại, nếu không attachment trên trang vẫn là bản cũ.
