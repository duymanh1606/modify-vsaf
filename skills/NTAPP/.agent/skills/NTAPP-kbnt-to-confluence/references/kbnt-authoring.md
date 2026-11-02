# Luật viết case KBNT

Đọc trước khi viết case đầu tiên. KBNT là tài liệu **người dùng cuối ký**, không phải bản sao của KBKT.

---

## 1. Luật cắt — case nào thuộc KBNT

**Thuộc KBNT:**
- Mỗi AC của story ít nhất một case đường thuận.
- Nhánh **có hệ quả nghiệp vụ**: lệch và khớp, trùng, đối tác trả lỗi hoặc không phản hồi, quyền theo vai trò, dữ liệu biên ngày và cut-off, trạng thái không cho phép thao tác.
- Hồi quy quanh vùng vừa sửa, khi target đã nghiệm thu ở đợt trước.
- Luồng E2E của phần nghiệm thu ảnh hưởng.

**KHÔNG thuộc KBNT (để KBKT lo):**
- Validate field-level: bắt buộc, độ dài tối đa, định dạng, ký tự cấm, tab-order, focus, responsive.
- An toàn thông tin: giả mạo request, SQL injection, IDOR, upload file độc.
- Kiểm tra kỹ thuật thuần: có index chưa, log có đủ trường chưa, hiệu năng truy vấn.

**Định lượng gợi ý:** 3 đến 8 case cho một unit, 5 đến 12 case cho một luồng E2E.

Đây là **gợi ý mềm để phát hiện mình đang viết lệch**, KHÔNG phải giới hạn cứng của hệ thống:
- Dưới 3 case cho một unit vừa sửa nhiều → khả năng bỏ sót nhánh có hệ quả nghiệp vụ.
- Trên 8 case → khả năng đang viết case field-level hoặc chẻ một hành vi thành nhiều dòng.

Vượt trần vẫn hợp lệ khi có lý do thật (ví dụ một menu mới thay hẳn hiện trạng làm tay). Khi vượt thì **nêu lý do ở gate 2, KHÔNG cắt case cho vừa trần** — cắt case để đẹp số là đánh đổi sai: mất một nhánh có hệ quả tiền còn tệ hơn một tài liệu dài.

## 2. Cột và cách viết

Bám **đúng bộ cột của template fetch được**. Ánh xạ nội dung vào cột theo nghĩa, không đổi tên cột của template.

### Mã case (nằm trong ô đầu, thường là `STT`)

`NT-<target>-<nn>`, ví dụ `NT-BE-RA-13-01`, `NT-SCR-BC1-DETAIL-04`, `NT-FLOW-DOISOAT-T1-02`. Cấp từ registry, không renumber. Thứ tự đọc do thứ tự dòng quyết định, không do số trong mã.

### Mục đích

Bắt đầu bằng "Kiểm tra" hoặc "Xác nhận", nêu rõ **đối tượng nghiệp vụ** và **khía cạnh** được nghiệm thu. Viết theo góc nhìn người dùng, không theo góc nhìn hàm.

- Đúng: `Xác nhận giao dịch lệch số tiền sau khi gửi xử lý được ghi nhận người gửi và thời điểm gửi trên báo cáo chi tiết TCTC.`
- Sai: `Kiểm tra API updateReconciliationAdjustments trả về 200.`

### Tiền điều kiện

Nêu trạng thái hệ thống và dữ liệu cần có trước khi bấm nút đầu tiên: người dùng đăng nhập với vai trò nào, dữ liệu ngày nào đã có, job nào đã chạy xong, file đối tác nào đã về.

### Các bước thực hiện

Chuỗi thao tác vật lý đầy đủ, mỗi bước một dòng, tách bằng `<br>` trong ô bảng: mở menu nào, lọc điều kiện gì, chọn dòng nào, bấm nút gì, xác nhận ở đâu.

Cấm bước trống nghĩa kiểu "Quan sát", "Mở màn hình", "Kiểm tra kết quả" — phải nêu rõ mở màn nào, nhìn vùng nào.

### Dữ liệu

Mô tả bằng **đặc tính phân biệt đủ để tự tìm hoặc tự dựng**, không bịa định danh cụ thể, không nói trống.

- Đúng: `Một giao dịch của TCTC X, ngày đối soát T-1, lệch số tiền giữa nội bộ và đối tác, chưa từng gửi xử lý.`
- Sai vì trống: `Một giao dịch lệch bất kỳ.`
- Sai vì bịa: `Giao dịch 00JKFQ66S2JWQANSG7A2026081B3 của merchant MC001.`

Lấy dữ liệu theo thứ tự ưu tiên: `{id}_fixtures.yaml` của KBKT → ví dụ trong DD hoặc story → mô tả người dùng cung cấp. Không có thì ghi `[TBD]` và gom vào mục "Chuẩn bị dữ liệu và môi trường" ở đầu tài liệu.

### Kết quả mong đợi

Nêu **đủ mọi tầng hệ quả có thật** của case, mỗi tầng một dòng (`<br>` trong ô), nhãn tiếng Việt, nội dung diễn đạt nghiệp vụ:

- `Giao diện:` cái người dùng thấy đổi trên màn.
- `Dữ liệu:` bản ghi nghiệp vụ đổi thế nào — nói bằng tên nghiệp vụ, ví dụ "giao dịch chuyển trạng thái Đã gửi xử lý, ghi nhận người gửi và thời điểm gửi".
- `Gửi đi:` thông điệp hoặc file đi ra hệ thống khác, nói bằng tên nghiệp vụ.
- `Nhật ký:` dấu vết kiểm toán ghi lại được.

Tên kỹ thuật (bảng, cột, topic) chỉ đặt trong ngoặc khi thực sự cần để đội hỗ trợ tra, không thay thế câu nghiệp vụ. Tầng nào case không tạo ra thì bỏ hẳn dòng đó, không ghi "không có".

Chất lượng bắt buộc:
- **Xác định:** một hành vi rõ ràng, cấm "chặn hoặc báo lỗi", cấm "A hoặc B".
- **Loại trừ:** khẳng định cả cái phải xảy ra lẫn cái không được xảy ra khi dễ nhầm (ví dụ chỉ một thông báo, không kèm lỗi hệ thống).
- **Không bịa chữ hiển thị:** thông báo trích nguyên văn từ nguồn (khóa i18n hoặc phần giao diện của DD); nguồn không có thì ghi `[TBD]`, không tự đặt câu chữ.

### Ghi chú

Dùng cho: đánh dấu case hồi quy, đánh dấu case cần hỗ trợ kỹ thuật, ghi target và nguồn (`code-only`), ghi liên kết tới đợt trước nếu là mã case cũ, và **tiền tố trạng thái** khi có.

Hai tiền tố trạng thái, đặt ở **đầu** ô Ghi chú, đừng lẫn nhau:

| Tiền tố | Nghĩa | Đợt sau |
|:---|:---|:---|
| `[Chưa nghiệm thu đợt này — dời đợt KBNT sau: <lý do>]` | còn nợ, phải quay lại | mang case sang, **xóa tiền tố**, dùng lại mã cũ |
| `[Đã hủy — đợt <tên đợt>]` | bỏ vĩnh viễn | không mang sang, mã không tái sử dụng |

**Chỉ đặt tiền tố dời khi người dùng chốt rõ đúng case đó.** Ba tình huống khác nhau, đừng gộp thành một:

| Tình huống | Xử lý |
|:---|:---|
| Người dùng chốt không làm đợt này | tiền tố dời + ghi vào `kbnt-backlog.md` |
| Giữ trong đợt, nhưng cần bản build có đủ mã | **không** tiền tố; nêu ở mục cảnh báo `A1` kèm danh sách case; thiếu mã thì để trống cột kết quả, KHÔNG đánh Không đạt |
| Giữ trong đợt, nhưng chờ chốt nghiệp vụ | **không** tiền tố; `[TBD]` trong `Điều kiện` + một dòng ở mục `B3` |

## 3. Case cho unit không có màn

Thứ tự ưu tiên khi diễn đạt:

1. **Bề mặt người dùng gián tiếp** — màn báo cáo hiển thị kết quả, màn quản lý file, file kết quả gửi đối tác, trạng thái bản ghi. Người dùng tự thao tác và tự phán xử.
2. **Có hỗ trợ kỹ thuật** — khi không có bề mặt nào tự kích hoạt được. Khi đó case phải nêu rõ ba thứ: cách tạo kích thích (đẩy file mẫu, chờ job chạy theo lịch, gửi bản tin thử), ai làm phần đó, và **điểm quan sát mà người dùng cuối tự xác nhận được**. Ghi chú đánh dấu `Cần hỗ trợ kỹ thuật`.

Không có điểm quan sát nào cho người dùng cuối thì case đó không phải KBNT — chuyển sang KBKT và nêu ở gate 2.

## 4. Case luồng E2E (nghiệm thu ảnh hưởng)

- Một case đi qua nhiều unit theo **thứ tự nghiệp vụ**, không phải theo thứ tự kỹ thuật.
- Tiền điều kiện nêu đủ trạng thái đầu luồng; các bước nêu điểm chuyển giao giữa các chặng; kết quả mong đợi nêu điểm cuối cùng người dùng kiểm được, cộng các mốc trung gian quan sát được.
- Mục đích của luồng phải nói rõ **cái gì có thể vỡ** do thay đổi của đợt này — đó là lý do luồng có mặt.

## 5. Khung fallback (chỉ khi fetch template lỗi)

Cảnh báo người dùng đang dùng fallback, rồi dùng khung này:

1. Thông tin đợt nghiệm thu (tên đợt, phạm vi, ngày, người lập, phạm vi đẩy lên Confluence).
2. **Mục A — Cảnh báo trước khi mở đợt** (`A1`, `A2`, …): thứ quyết định case nào ký được.
3. **Mục B — Chuẩn bị dữ liệu và môi trường** (`B1`, `B2`, …): gom `[TBD]` theo nhóm người phải cấp.
4. Danh sách chức năng nghiệm thu trong đợt.
5. Kịch bản nghiệm thu theo chức năng — bảng: `STT (mã case) | Mục đích | Tiền điều kiện | Các bước thực hiện | Dữ liệu | Kết quả mong đợi | Kết quả thực tế | Đạt/Không đạt | Người nghiệm thu | Ngày | Ghi chú`.
6. Kịch bản nghiệm thu ảnh hưởng (luồng E2E) — cùng bộ cột.
7. **Phụ lục 1** — lệch giữa tài liệu và mã nguồn; **Phụ lục 2** — chi tiết `[TBD]` theo từng mục.
8. Kết luận và ký duyệt, kèm dòng **bản build đã nghiệm thu**.

**Đánh số bắt đầu từ A.** Hai mục đầu là `A`/`B`, hai phụ lục là `Phụ lục 1`/`Phụ lục 2`. Đừng đặt mục thân bài là `C`, `D` rồi phụ lục lại `A`, `B` — người đọc mở tài liệu sẽ tưởng thiếu hai mục đầu.

**Chỉ mục 1 (bảng thông tin đầu tài liệu) và mục 5-6 (bảng case) được đẩy lên Confluence.** Phần còn lại là bản làm việc nội bộ.
