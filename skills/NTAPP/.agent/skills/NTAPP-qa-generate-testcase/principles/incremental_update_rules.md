# INCREMENTAL UPDATE & ROUND-TRIP RULES — Cập nhật delta + nuốt kết quả

> **Mục đích:** Đóng vòng lifecycle School B: (a) khi SLICE/spec đổi → chỉ regen phần delta thay vì cả slice;
> (b) nuốt ngược kết quả chạy automation (`qa-robot results/`) để đánh dấu trạng thái + chọn regression.
> Dùng ở [step-05-roundtrip.md](../steps/step-05-roundtrip.md). KHÔNG nới lỏng Iron Rules.
>
> **Delta là ENTRY-MODE, không chỉ post-step:** khi lane `delta` được resolve ở [Step 00](../steps/step-00-shiftleft-gate.md) (auto-detect 3 artifact đã tồn tại — xem [run_mode_rules.md](./run_mode_rules.md) §5), skill **bỏ qua Step 00–03** và vào thẳng §1 dưới đây qua [Step 05 Nhánh A](../steps/step-05-roundtrip.md). Không cần chạy lại full-ceremony chỉ để sửa 1 label / thêm 1 unit.

---

## 1. Delta Detection (cập nhật tăng dần)

Khi chạy lại skill trên một SLICE/unit **đã có** 3 artifact:

| Thay đổi phát hiện | Phạm vi regen | Giữ nguyên |
|---|---|---|
| 1 unit mới thêm vào `units[]` | Chỉ sinh khối Màn hình Action cho unit đó; ID `@id` nối tiếp cuối dải | Các màn cũ |
| Nhãn Giao diện đổi (cùng control) | Patch Nhãn hiển thị trong các dòng liên quan | Logic/risk/exec |
| Logic/Dữ liệu đổi (nhánh/validation) | Regen các case `@rule` liên quan + đánh dấu `@regression` | Phần không liên quan |
| Unit bị gỡ khỏi SLICE | Đánh dấu các case của unit đó `deprecated`, KHÔNG xóa cứng (giữ audit) | — |

**Bất biến:** Sau delta, vẫn chạy lại **Math Check Gate (R2)** + **Sync Invariant 3 chiều** (feature ⇔ markdown ⇔ fixtures) trên toàn file. ID không nhảy cóc (R8).

> Không có cơ chế diff tự động → so khớp theo `@id` + `@rule` + `@scr`. Ghi rõ "delta map" ra chat trước khi sửa.

---

## 2. Result Ingestion (nuốt kết quả automation)

Sau khi `/ntapp-qa-robot` chạy (`results/output.xml`):

1. Đọc `results/output.xml` (read-only; KHÔNG sửa code repo từ skill này).
2. Map mỗi Robot test ↔ `@id` (qa-robot giữ tên test theo ID manual testcase).
3. Cập nhật Mục 5.4 markdown: điền `{pass_tcs}`/`{fail_tcs}`/`{skip_tcs}` từ kết quả thật (thay vì để trống).
4. Gắn `@regression` cho các case `@exec:automate` đã PASS ổn định → là tập regression guard cho `bmad-testarch-ci`.
5. Case `manual`/`exploratory`: trạng thái do tester điền tay (skill không tự suy).

---

## 3. Regression Selection

- Khi chỉ 1 unit đổi: bộ regression đề xuất = các case `@regression` của **unit đó + downstream theo demoable** (không phải cả slice).
- Xuất danh sách `@id` cần chạy lại ra chat để qa-robot/CI chạy chọn lọc.

---

## 4. Ranh giới

- Skill QA này **chỉ đọc** `results/` của qa-robot, không thực thi test, không sửa Robot code.
- Mọi cập nhật vẫn ghi canonical-only vào `{qa_artifacts}` (R6) — không archive/_vN.
