# Merge với trang đã có chữ ký

Áp dụng ở §8 và §10 của `workflow.md`. Đây là phần dễ mất dữ liệu nhất của skill: bốn ô mỗi dòng do **người dùng điền tay trên Confluence**, không tồn tại ở bản local.

Quyết định nền và các phương án đã bác: `docs/adr/0014-kbnt-round-page-and-signed-cell-merge.md` của spec repo.

---

## 1. Phân loại ô

| Nhóm | Ai là nguồn sự thật | Hành vi khi publish lại |
|:---|:---|:---|
| Mã case (ô đầu, `STT`) | Registry local | Khóa khớp dòng, không bao giờ sửa |
| Nội dung case (mục đích, tiền điều kiện, các bước, dữ liệu, kết quả mong đợi) | Markdown local, **trừ khi bị sửa tay trên trang** | So ba chiều, mặc định giữ bản trên trang khi có sửa tay |
| Kết quả thực tế, Đạt/Không đạt, Người nghiệm thu, Ngày | **Trang Confluence** | Giữ nguyên verbatim, tuyệt đối không sinh lại |
| Cột 2 của **bảng thông tin đầu tài liệu** (Version KBNV / Ngày thực hiện / Người tạo / Người phê duyệt / Người thực hiện / Kết luận) | **Trang Confluence** | Khối chữ ký — carry nguyên văn từ snapshot (`--carry-info`), không sinh lại |
| Ghi chú | Cả hai | Nối thêm phần mới, không xóa phần người dùng viết |

Tên chính xác của bốn ô người dùng lấy từ **template fetch được** ở §3, không đoán. Không nhận diện được đủ bốn ô → DỪNG hỏi người dùng chỉ cột.

## 2. Đọc và parse trang

1. `confluence_get_page(page_id, convert_to_markdown=false)` lấy storage XHTML, ghi nhớ `version.number`.
2. Parse từng bảng case: hàng tiêu đề để định vị chỉ số cột, các hàng còn lại thành bản ghi khóa bởi mã case ở ô đầu.
3. **DỪNG, không ghi** khi gặp bất kỳ điều nào sau:
   - Không tìm thấy bảng case nào.
   - Có dòng mà ô đầu không phải mã case hợp lệ (người dùng chèn dòng tay).
   - Mã case trùng nhau trong cùng trang.
   - Số cột của một dòng lệch hàng tiêu đề.
   Báo rõ dòng nào hỏng và đề nghị người dùng sửa trên trang, hoặc xác nhận cho phép bỏ qua dòng đó.

## 3. So ba chiều

Ba bản: `A` = snapshot lần publish trước (`{dot_dir}/last-published.snapshot.xhtml`), `B` = trang hiện tại, `C` = bản mới sinh từ markdown local.

Với mỗi ô nội dung của một mã case:

| A vs B | B vs C | Xử lý |
|:---|:---|:---|
| Giống (người dùng không sửa) | Khác | Lấy `C` — cập nhật bình thường |
| Giống | Giống | Giữ nguyên |
| Khác (người dùng đã sửa tay) | Khác | **Giữ `B`**, đưa vào danh sách xung đột để người dùng tick nếu muốn đè bằng `C` |
| Khác | Giống | Giữ `B` |

Không có snapshot `A` (đợt cũ, hoặc snapshot bị xóa) → coi như **mọi khác biệt đều là sửa tay**: giữ toàn bộ `B`, liệt kê khác biệt để người dùng chọn. An toàn trước, tiện sau.

## 4. Case mới, case biến mất

- **Case mới:** append cuối bảng của target tương ứng. Không chèn giữa, không sắp xếp lại bảng — thứ tự dòng là thứ tự người dùng đã quen.
- **Case biến mất khỏi spec:** không xóa dòng. Thêm vào ô Ghi chú tiền tố `[Đã hủy — đợt {tên đợt}]` và giữ nguyên mọi ô khác. Dòng đã có kết quả ký thì càng phải giữ: đó là bằng chứng nghiệm thu.
- **Case dời sang đợt sau:** cũng không xóa dòng, nhưng tiền tố **khác**: `[Chưa nghiệm thu đợt này — dời đợt KBNT sau: <lý do>]`. Phân biệt rõ với `[Đã hủy]` — hủy là bỏ vĩnh viễn, dời là còn nợ và phải quay lại. Case dời giữ nguyên các ô kết quả trống; đợt sau khi mang case này trở lại thì **xóa tiền tố**, không tạo dòng mới.
- **Chỉ parse và chỉ ghi bảng case.** Trang có thể chứa nội dung khác do người trong đội thêm tay (ghi chú họp, ảnh chụp, bảng phụ). Những phần đó **giữ nguyên vị trí, không xóa, không sắp lại** — skill chỉ thay đúng bảng case.
- **Target biến mất khỏi đợt:** giữ nguyên cả bảng của target đó, ghi chú ở đầu bảng.
- **Mục bị cắt vì đã nghiệm thu ở đợt khác:** **giữ lại hàng mục**, thêm vào tên mục hậu tố `— **ĐÃ NGHIỆM THU** tại trang “{tên trang}” (pageId {id}). Không chạy lại trong đợt này.`, và **bỏ toàn bộ hàng case** của mục đó. Đừng xoá hẳn hàng mục: số La Mã sẽ hụt (`I, IV, V, …`) làm người đọc tưởng trang thiếu, và mất luôn lý do vì sao mục đó không có case. Case tương ứng chuyển `trang_thai: done` trong registry kèm `dot_da_ky` và `nghiem_thu_tai_page` — **không** xoá khỏi registry, vì mã case là bất biến.
- **Danh sách mục bị cắt phải nằm trong `{dot_dir}/dot-manifest.yaml`** (khối `da_nghiem_thu_o_dot_khac`, khóa là số La Mã, giá trị là `page_id` + `page_title`) và bộ build storage **đọc từ đó**. Hardcode danh sách trong script tạm là mất tái lập: chạy lại là mất phần cắt, và không ai tra được ai quyết cắt cái gì.

## 5. Khóa lạc quan

Giữa lúc đọc trang (§8) và lúc ghi (§10) có thể có người vừa ký hoặc vừa sửa. Ngay trước khi ghi:

1. `get_page` lại, so `version.number` với giá trị đã ghi nhớ.
2. Khớp → ghi.
3. Lệch → **hủy ghi**, không PUT. Đọc lại trang, chạy lại §8, trình lại preview. Không có ngoại lệ, không có cờ ép ghi.

Ghi xong thì lưu `{dot_dir}/last-published.snapshot.xhtml` bằng **đúng nội dung vừa PUT**, và cập nhật `version` mới vào `page-ref.json`.

## 6. Registry mã case

`{kbnt_root}/case-registry.yaml`, một mục cho mỗi mã:

Dạng **map theo mã** — khóa là mã case, nên không thể trùng khóa và tra được trực tiếp:

```yaml
NT-BE-RA-13-01:
  target: BE-RA-13
  muc: XIII                 # số La Mã của mục trong bảng case
  dot_cap_ma: ban-giao-thang-8
  muc_dich: "Xác nhận file kết quả gửi lại được sinh đúng ngày đối soát"
  trang_thai: active        # active | deferred | done | huy
  lan_dau: 2026-08-17
NT-BE-RP-18-01:
  target: BE-RP-18
  muc: XI
  dot_cap_ma: ban-giao-thang-8
  muc_dich: "..."
  trang_thai: deferred
  lan_dau: 2026-08-17
  ly_do_doi: "ACB chưa cấp mã bí mật bên gọi"
NT-BE-RA-22-03:
  target: BE-RA-22
  muc: II
  dot_cap_ma: ban-giao-thang-8
  muc_dich: "..."
  trang_thai: done
  lan_dau: 2026-08-17
  dot_da_ky: ban-giao-thang-8
  hoi_quy: true
```

Bốn trạng thái:

| `trang_thai` | Nghĩa | Có trong `kbnt-backlog.md`? |
|:---|:---|:---|
| `active` | đã đưa vào đợt đang chạy | không |
| `deferred` | đã cấp mã, người dùng chốt **dời sang đợt sau** | **có** — kèm `ly_do_doi` |
| `done` | đã nghiệm thu và ký xong | không — kèm `dot_da_ky` |
| `huy` | bỏ hẳn; mã **không** tái sử dụng | không |

Luật:
- Cấp `nn` = số lớn nhất hiện có của target đó cộng một. **Không lấp chỗ trống** của mã đã hủy hay đã dời.
- Case cũ xuất hiện lại ở đợt sau thì dùng lại mã cũ, không cấp mã mới; thêm `hoi_quy: true` nếu là case hồi quy.
- Registry là ledger: không xóa mục, không đánh số lại, không sinh lại từ đầu. Mất registry thì mã đã ký trên các trang cũ hết truy vết được.
- `deferred` và `done` là **cặp bù nhau với `kbnt-backlog.md`**: mỗi mã `deferred` phải có đúng một dòng trong backlog; đổi sang `done` thì đồng thời xóa dòng đó khỏi backlog. Lệch một trong hai chiều là case bị mất hoặc bị làm hai lần.
