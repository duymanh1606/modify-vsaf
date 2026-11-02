# Reference: Hợp nhất ERD toàn hệ từ Stage 3 (erd-consolidation)

Quy tắc cho `agent_erd_data_architect` + mục ERD của workflow. Nguyên tắc gốc: no-fabrication, cite nguồn, nhóm theo datastore.

## 1. Nguồn nhận & loại trừ

**NHẬN** (chỉ đọc, canonical): `NTAPP-output/Stage_3_Specs/techspec/*_techspec.md` §11 — có `### 11.1 Sơ đồ thực thể logic` và/hoặc `### 11.2 Từ điển dữ liệu`.
- Bỏ qua mọi file trong `archive/` và mọi `*.ts_parts/` (bản ghép trung gian).

**LOẠI khỏi ERD:**
- `integration-*_techspec.md` — §11 là event payload schema / contract Kafka-partner, KHÔNG phải bảng datastore. (Để dành skill riêng.)
- `observability_techspec.md` — không own business entity (§11 đã bỏ).
- techspec FE / techspec không có §11 backed bởi datastore thật → skip (log lý do).

## 2. Xác định datastore sở hữu (cluster key)

Đọc câu mở đầu §11 của mỗi techspec để lấy datastore + tên logic. Ví dụ tín hiệu:
- "MongoDB `reconcile_service_staging`" → cluster `MongoDB · RS`.
- "MariaDB C-34 share schema" → cluster `MariaDB · Config (admin)`.
- staging/data_raw EDS/IDS → cluster theo store khai báo.
Một techspec có thể ghi vào >1 store → tách entity theo store, KHÔNG gộp nhầm cluster.
Store mơ hồ / không khai báo rõ → đặt entity vào cluster `[Cần xác nhận]` + ghi nguồn.

## 3. Trích entity + quan hệ — NGUỒN KÉP (quan hệ ≠ field)

**Nguyên tắc tách nguồn (quan trọng — đừng trộn):**
- **Quan hệ giữa bảng = HLD `architecture_design.md §3.2` (Global Data Model ERD) — nguồn CHUẨN, ĐẦY ĐỦ.** Bê TRỌN bộ quan hệ mỗi sub-diagram (không rút gọn cạnh song song, không bỏ cạnh). Đây là bộ quan hệ đã review; techspec §11.1 chỉ mô tả góc nhìn per-module nên quan hệ nghèo hơn → KHÔNG dùng §11.1 làm nguồn quan hệ chính.
- **Từ điển field = techspec §11.2** (per bảng). Bảng nào **có trong HLD ERD nhưng chưa techspec-hoá §11** → vẫn tạo hộp trong sơ đồ + dòng summary, phần field ghi `[Cần bổ sung]` (đừng bỏ bảng khỏi sơ đồ chỉ vì thiếu field).

Từ HLD §3.2 (mỗi ```mermaid erDiagram``` sub-diagram theo store):
- Mỗi entity khai báo → 1 hộp bảng trong cluster tương ứng store.
- Mỗi dòng `A ||--o{ B : "label"` → quan hệ nội cluster (A,B cùng store) hoặc **cross-store bridge** (khác store; các entity hậu tố `_ref` = proxy cross-store, map về bảng nguồn thật ở store kia).
- Nhãn cạnh rút gọn (tên khoá / cụm từ ≤ 3 từ) cho dễ đọc; giữ diacritics tối thiểu, ưu tiên ASCII.

Từ techspec §11.1 (`ENTITY { ... }`) chỉ để **lấy field/PK/FK** map vào từ điển bảng; KHÔNG lấy quan hệ ở đây.

## 4. Cross-store bridge (Tầng A)

**Nguồn bridge = cột FK thật trong ERD chi tiết** (vd `docs/ba-erd-kbnv.md` — nếu có), KHÔNG chỉ dựa HLD §3.2. HLD thường *distil* ERD chi tiết → gộp nhiều bridge vào 1 proxy `_ref` (vd chỉ vẽ `statistic_retrieval_data_ref → data_raw`, bỏ mất `reconcile_bank_service.processRequestId → statistic_retrieval_data`). ⇒ **quét cột FK của mọi bảng đích**: field đánh dấu `FK` + "Liên kết/Tham chiếu tới `<bảng khác store>`" = 1 bridge cross-store.

Quy tắc nối: chỉ nối 2 bảng khác store khi khoá chung là FK/matching/link key xác nhận ở (a) cột FK ERD chi tiết, (b) §11 techspec, (c) arch §ERD, hoặc (d) Module 0 §3.3/§6. Trùng tên field nhưng không có xác nhận ngữ nghĩa → KHÔNG nối, ghi `[Cần xác nhận]`. Bảng đích chưa techspec-hoá vẫn nối bridge (theo FK) + hiện hộp, field `[Cần bổ sung]`.

⚠️ Phân biệt: `reconcile_* → statistic_reconcile_*` (rollup) là **nội cụm MongoDB**, KHÔNG cross-store — đừng nhầm với `statistic_send_data`/`statistic_retrieval_data` (MariaDB).

## 5. Từ điển 2 tầng mỗi bảng

- **Tầng 1 (nghiệp vụ):** `Tên field | Kiểu | Ý nghĩa` — rút từ §11.2 cột Field/Type/Description, bỏ jargon.
- **Tầng 2 (kỹ thuật, đầy đủ):** bê nguyên bảng §11.2 `Field | Type | Constraints | Storage | Description` + ghi chú code-as-is/drift.

## 6. Format artifact `erd-consolidated.md` (độc lập, trace lại được)

```
# ERD hợp nhất toàn hệ — <project>
> Sinh bởi agent_erd_data_architect | <ngày> | Nguồn: <list techspec + arch §ERD + Module 0>

## 0. Cross-store relationship map (Tầng A)
   - (mô tả sơ đồ cross-store: entity thu gọn + FK bắc cầu)
   - Bảng: Bảng nguồn | Khoá | Bảng đích | Store↔Store | Nguồn

## <n>. Cụm datastore: <cluster name>
   ### <n>.1 Danh sách bảng + quan hệ nội cụm (cho sơ đồ erd)
   ### <n>.2 Bảng tổng hợp: STT | Tên bảng | Ý nghĩa | Nguồn
   ### <n>.3 Từ điển field từng bảng
       #### <tên_bảng>   (Nguồn: <techspec>#<section>)
          Tầng 1: | Tên field | Kiểu | Ý nghĩa |
          Tầng 2: | Field | Type | Constraints | Storage | Description |

## X. Điểm cần xác nhận
   - [Cần xác nhận] ...
```

## 6b. 🔴 GATE BẮT BUỘC — đối chiếu CODE trước khi render ERD

HLD và techspec **liệt kê cả bảng chưa/không bao giờ tồn tại**, và mô tả quan hệ theo ý đồ thiết kế chứ không theo
hiện trạng. Render thẳng = đưa mô hình dữ liệu sai lên tài liệu bàn giao (thực tế DSTT 2026-08-10: **5/48 bảng
không có trong code**, **4 quan hệ sai bản chất**). Trước khi render §4 phải:

1. **Xác minh từng bảng** bằng khai báo thật trong code, không bằng tên gọi:
   - quan hệ (JPA): `@Table(name = "...")`;
   - tài liệu (MongoDB): `@Document(collection = ...)` **hoặc hằng số tên collection** — nhiều dự án khai báo bằng
     hằng số + đọc từ config, grep `@Document` ra rỗng và rất dễ kết luận nhầm là "không có collection nào".
   - ⚠️ Bẫy đã dính: (a) tên chỉ tồn tại trong **DTO báo cáo** — không phải bảng; (b) lớp `*Adapter` mang tên bảng
     nhưng bên trong đọc bảng khác; (c) literal là **tên trường** trong pipeline tổng hợp; (d) literal là **tên
     database**. Luôn mở file xem ngữ cảnh trước khi kết luận.
2. **Xác minh từng quan hệ**: tìm chỗ code thực sự ghép hai bảng (`findBy...`, join JPQL/native, filter, pipeline).
   Không tìm được chỗ ghép → đó là **luồng xử lý** hoặc quan hệ sai, không phải quan hệ dữ liệu.
3. **Ghi khoá nối cho MỌI quan hệ** — chỉ có `1:N` là chưa đủ, người đọc cần biết hai bảng ghép nhau *qua thông tin
   nào*. Phân loại: `Khoá ngoại` (ràng buộc thật ở DB) · `Khoá nghiệp vụ` (không ràng buộc, ứng dụng tra theo mã) ·
   `Khoá tài liệu` (hai document cùng mang một mã) · `Luồng xử lý` (KHÔNG phải quan hệ — tiến trình đọc bảng này ghi
   bảng kia) · `Nhật ký`. Nhãn trên sơ đồ = **khoá nối** (ngắn); diễn giải để ở bảng dưới sơ đồ.
4. **Kết quả đối chiếu ghi thành artifact riêng, mỗi dòng trích dẫn `file:dòng`** (vd `_erd_truth.py` của DSTT), rồi
   cho bộ render đọc artifact đó để lọc bảng + làm giàu nhãn. KHÔNG sửa tay vào sơ đồ — lần re-run sau sẽ mất.
5. Bảng/quan hệ bị loại phải **báo cho user kèm lý do + bằng chứng**, không im lặng xoá.

> **NoSQL:** MongoDB không có khoá ngoại. Phần lớn "quan hệ" giữa collection là **luồng xử lý** do job thực hiện
> (đọc → ghi), không phải liên kết tham chiếu. Trình bày lẫn lộn hai thứ là nguyên nhân điển hình khiến người đọc
> không hiểu sơ đồ — tách rõ bằng cột *Loại quan hệ* + một đoạn diễn giải ngay dưới sơ đồ.

## 7. Render sang mục ERD Confluence (2 tầng)

- **Tầng A → CHỈ 1 sơ đồ** draw.io `erd(..., collapsed=True)`, quan hệ thể hiện trực tiếp bằng cạnh + nhãn khoá. **KHÔNG render bảng mô tả prose cross-store** (bảng §0 chỉ là nguồn máy để dựng cạnh, không đưa lên Confluence — quan hệ chỉ cần sơ đồ).
- Tầng B → mỗi cluster 1 sơ đồ `erd()` (đủ mọi cạnh nội cụm HLD) + bảng tổng hợp bảng `STT | Tên bảng | Ý nghĩa | Nguồn`; mỗi bảng 1 macro `expand` chứa Tầng 1, lồng `expand` "Chi tiết kỹ thuật đầy đủ" chứa Tầng 2. Bảng chưa techspec-hoá → expand hiện `[Cần bổ sung]`.
