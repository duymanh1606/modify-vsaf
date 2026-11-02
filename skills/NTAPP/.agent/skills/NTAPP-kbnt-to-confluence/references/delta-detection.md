# Dò nội dung đợt và dò ảnh hưởng

Dùng ở §2 của `workflow.md`. Mục tiêu: từ mốc `{since}` ra hai danh sách — **target trực tiếp** (thứ vừa làm) và **ứng viên ảnh hưởng** (thứ có thể vỡ mà không ai đụng tới).

Cả hai danh sách đều là **đề xuất**, không phải kết luận. Người dùng tick ở gate 1.

---

## 1. Target trực tiếp — hợp bốn nguồn

### Nguồn A — code repo (bắt cả code chưa commit)

Với mỗi code repo trong workspace (lấy từ file workspace hoặc thư mục cha của spec repo):

```bash
git -C "$repo" log --since="$since" --name-only --pretty=format:%H
git -C "$repo" status --porcelain
```

Duyệt path bằng `while IFS= read -r` (path có dấu cách). Với mỗi file đổi, đọc **10 dòng đầu** tìm header `id: <ID>` do pre-commit Rule 1 bắt buộc, lấy `<ID>` làm unit.

File không có header `id:` (file cũ, file config, file test) → **không bỏ im lặng**: gom thành danh sách "file đổi không map được unit" và trình ở gate 1 để người dùng gán tay hoặc bỏ qua. Đây là chỗ dễ sót nhất.

### Nguồn B — spec repo

- `{stage4_dir}/*_detailed_design.md` và `{stage5_dir}/*.md` có commit kể từ `{since}`, cộng file đang dirty theo `git status`.
- ID lấy từ tên file (`BE-RA-13_detailed_design.md` → `BE-RA-13`; `E5-SCR-BC1-DETAIL-sent-audit-columns.md` → `SCR-BC1-DETAIL`).
- DD đổi mà code không đổi vẫn là ứng viên hợp lệ: có thể spec đi trước, hoặc code nằm ở nhánh chưa merge.

### Nguồn C — slice plan

Slice trong `{slices_dir}` có `demo_status: passed` và chưa từng xuất hiện ở cột target của `{history}`.

### Nguồn D — trang KBNT đã có trên Confluence (chống nghiệm thu hai lần)

Ba nguồn trên trả lời "đợt này **đã làm** gì". Chúng KHÔNG trả lời "thứ đó **đã nghiệm thu** chưa" — và hai câu đó khác nhau, vì đội có thể đã viết KBNT tay từ lâu trước khi skill tồn tại. `{history}` rỗng chỉ nói skill chưa chạy, không nói chưa ai ký.

Thủ tục, chạy cả khi `--local` vì hoàn toàn read-only:

1. Liệt kê con của nhánh KBNT (`{branch_ref}`; chưa có thì dò theo `confluence-resolve.md` §1).
2. Với mỗi trang đợt, đọc storage rồi rút bốn thứ: **tên trang**, **tên các mục chức năng** (hàng có ô thứ hai `colspan` lớn), **số dòng case**, và **số dòng case đã điền ô kết quả**.
3. **Ô kết quả đã điền = đợt đó đã nghiệm thu.** Dấu hiệu chắc chắn nhất là ô "Mã giao dịch" có mã thật và ô "Kết quả" có ký hiệu đạt. Đừng suy từ tiêu đề hay từ ngày sửa trang.
4. Đối chiếu **theo nghĩa nghiệp vụ**, không theo mã case — trang viết tay không có mã `NT-*` nào để khớp. So tên mục chức năng và mô tả trường hợp với danh sách target đang xét.
5. Mỗi target trùng: ghi rõ **pageId nào phủ nó, phủ phần nào**, và đề xuất một trong ba — **bỏ khỏi đợt** (đã ký, không sửa gì thêm), **giữ làm case hồi quy** (đợt này sửa đúng vùng đó), hoặc **giữ nguyên** (trang cũ chỉ phủ một nhánh, phần còn lại chưa ai ký).

Trang lạ chưa có trong `{history}` thì backfill vào ledger ở §11 của `workflow.md` — nếu không, đợt sau lại dò lại từ đầu và lại trùng.

### Hợp và chuẩn hóa

- Khử trùng theo ID.
- Map unit → slice chứa nó (đọc slice plan) để nhóm hiển thị; **không** tự động kéo cả slice vào đợt chỉ vì một unit trong đó đổi.
- Mỗi dòng ứng viên phải trả lời được: ID, tên, **tín hiệu nào phát hiện ra nó**, có DD không, có story không, có KBKT không, đã từng nghiệm thu ở đợt nào.

---

## 2. Ứng viên ảnh hưởng (ripple)

Ba tín hiệu, chạy trên **tập file đã đổi** ở nguồn A.

### 2.1 Seam code dùng chung

Với mỗi file đổi, lấy tên class/hàm public bị sửa (đọc hunk), rồi tìm nơi khác gọi tới:

```bash
grep -rn "<TenClass>\|<tenHam>" --include=*.java --include=*.ts "$repo" | grep -v "<file da doi>"
```

Với mỗi file gọi tìm được, đọc header `id:` → unit khác chịu ảnh hưởng. Ví dụ thật của dự án: sửa `BaseMethod.createSshClient` chạm cả `BE-RP-01` lẫn `BE-RP-08`, dù chỉ commit vào một luồng.

### 2.2 Tài nguyên chung

Từ DD của target trực tiếp, trích các tài nguyên nó đọc/ghi: tên collection hoặc bảng, topic, endpoint, key cache, tên file trao đổi với đối tác. Rồi grep chính các tên đó trong **DD của các unit khác**:

```bash
grep -rln "<ten tai nguyen>" "{stage4_dir}"
```

Unit khác cùng ghi một tài nguyên là ứng viên ảnh hưởng mạnh nhất trong hệ đối soát — hai nguồn cùng ghi một bản ghi là nơi lỗi tiền hay xuất hiện.

### 2.3 Phụ thuộc slice

Đọc slice plan lấy quan hệ phụ thuộc giữa slice; slice phụ thuộc vào slice chứa target trực tiếp là ứng viên.

### Trình bày

Mỗi ứng viên ảnh hưởng phải có **bằng chứng đường dẫn file cụ thể**, không được chỉ nói "có liên quan". Ứng viên không nêu được bằng chứng thì không đưa vào danh sách.

---

## 3. Gom thành luồng E2E

Ứng viên ảnh hưởng được người dùng giữ lại sẽ gom thành **luồng nghiệp vụ đặt tên**, không phải danh sách unit rời. Một luồng gồm: tên nghiệp vụ (do người dùng đặt), thứ tự các bước đi qua các unit, và điểm quan sát cuối cùng mà người dùng cuối kiểm được.

Luồng không đặt được tên nghiệp vụ là dấu hiệu nhóm sai — hỏi lại người dùng thay vì tự đặt tên kỹ thuật kiểu "luồng BE-RP-01 + BE-RP-08".

Mã target của luồng: `FLOW-<slug ngắn>` do người dùng chốt ở gate 1, dùng làm tiền tố mã case (`NT-FLOW-DOISOAT-T1-01`).
