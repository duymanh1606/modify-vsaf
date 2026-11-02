# Priority Resolution Rule — cách chốt phương án cho mỗi gap

Đây là **lõi tư duy** của skill. Mọi step phân tích/đề xuất phải tuân theo file này.

---

## 0. Nguyên tắc nền

- **Skill KHÔNG tự quyết.** Skill chỉ *phân tích + đề xuất*. Mọi gap đưa người dùng/PO chốt.
- **Tách bạch 2 câu hỏi** — một nguồn không trả lời được cả hai:
  - **(A) Hành vi nào là ĐÚNG?** → dùng để ra phương án.
  - **(B) Hệ thống HIỆN đang làm gì?** → dùng để đo khoảng cách + chi phí sửa.
- **Code thực tế thuộc câu hỏi (B), không phải (A).** Code là *hiện trạng để đo độ lệch*, KHÔNG phải chân lý để quyết định hành vi đúng. Chốt theo code chỉ vì "code đang chạy vậy" = hợp thức hoá bug — bị cấm (xem §4).

---

## 1. Thứ tự ưu tiên khi đề xuất "hành vi đúng" (câu hỏi A)

Xét lần lượt, nguồn cao hơn thắng khi mâu thuẫn:

1. **Dữ liệu thực tế** — *chỉ khi report có cite* (staging sample trong `f2`, giá trị thật) **và** data đó hợp lệ nghiệp vụ (không phải rác/legacy). Data mạnh nhất khi dùng để **bác bỏ một ràng buộc sai** (vd regex bắt chữ hoa nhưng data thật là chữ thường → regex chắc chắn cần xem lại). Report KHÔNG cite data thật → bỏ qua tầng này, KHÔNG tự query DB.
2. **TechSpec / Contract canonical (L2 SSoT)** — theo R8 Contract Lock của dự án. Đây là nguồn mặc định để chốt khi các bản DD/FE lệch nhau.
3. **DD (L3)** — chỉ dùng khi *không* mâu thuẫn TechSpec.

**Code hiện tại = ĐO độ lệch + chi phí sửa**, không phải nguồn quyết định.
**PO / nghiệp vụ = tầng phá thế bí** — khi các nguồn trên mâu thuẫn mà không nguồn nào rõ đúng, hoặc gap là mơ hồ nghiệp vụ thật.

---

## 2. Vai trò của code KHÔNG cố định — phải xác định CHIỀU LỆCH

Code có thể **cũ hơn** tài liệu (viết theo DD stale) HOẶC **mới hơn** tài liệu (vừa fix bug/thêm yêu cầu mới nhưng docs chưa cập nhật). Không được áp thứ tự tầng một cách mù quáng — phải xác định chiều lệch bằng **dấu vết thời gian**:

- `git log`/`git blame` dòng code liên quan → ngày sửa gần nhất.
- Ngày các Change Request trong TechSpec (vd `v2.4 CR-COMPOSE-1`, `v3.0 CR-HUB-PUSH-REMOVAL`).
- Ngày sinh của DD part (header/frontmatter, hoặc git).

So 3 mốc → biết ai cũ ai mới → chọn đúng loại gap ở §3.

---

## 3. Phân loại gap → hành động tương ứng

Mỗi gap PHẢI gán đúng 1 nhãn. Nhãn quyết định Phase 2 làm gì:

| Nhãn | Dấu hiệu | Hành động đề xuất (Phase 2) |
|---|---|---|
| **stale-docs** | DD/FE part cũ hơn TechSpec (sinh trước CR); TechSpec là SSoT rõ ràng | Chốt theo TechSpec canonical → **regen DD part** (gọi `NTAPP-feature-design`/`NTAPP-dd-design`) hoặc sửa docs trực tiếp cho khớp |
| **code-mới-docs-cũ** | git blame cho thấy code sửa SAU ngày DD/CR; code phản ánh yêu cầu mới/bugfix nhưng docs chưa cập nhật | Chốt theo **code** (là intent thật) → **cập nhật DD/TechSpec cho khớp code**; flag "docs cần đồng bộ" |
| **lệch-code-vs-contract** | code làm KHÁC contract/SSoT, và code KHÔNG mới hơn (không phải yêu cầu mới) → **bug thật** | **Sửa code** → Phase 2 chỉ **sinh diff + lý do** cho dev duyệt (KHÔNG tự commit code) |
| **mơ-hồ-nghiệp-vụ** | kể cả TechSpec/data cũng không trả lời được; cần quyết định nghiệp vụ | **KHÔNG execute** — giữ Todo, đề xuất `[Cần PO chốt]` + nêu phương án & trade-off |

> Một gap có thể có nhiều mặt (vd vừa stale-docs vừa lộ bug code). Ghi rõ từng mặt, xử lý từng mặt theo bảng.

---

## 4. Cấm tuyệt đối (Red Flags — dừng lại nếu bạn đang làm)

- ❌ Tự chọn giá trị/enum/hành vi "cho xong" mà không trích nguồn (xem [no-hallucination-rule.md](./no-hallucination-rule.md)).
- ❌ Chốt theo code chỉ vì code đang chạy vậy, KHI chưa xác định chiều lệch → có thể đang hợp thức hoá bug.
- ❌ Suy ra chiều lệch mà không mở git blame/log.
- ❌ Sửa code trực tiếp / commit code trong Phase 2 (code chỉ được sinh diff đề xuất).
- ❌ Flip một gap sang `Resolved` khi nó là `mơ-hồ-nghiệp-vụ` chưa có PO chốt.
- ❌ Đề xuất mà không kèm **hiện trạng code đang làm gì** (câu hỏi B) — thiếu cái này thì không đo được độ lệch/chi phí.
