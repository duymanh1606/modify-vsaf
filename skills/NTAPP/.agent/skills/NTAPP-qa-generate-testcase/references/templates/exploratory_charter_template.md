# EXPLORATORY CHARTER — {id}

> Sinh cho các kịch bản gắn `@exec:exploratory` (vùng bất định / khó scripted hóa).
> Theo tinh thần School B: thay scripted manual bằng phiên khám phá có charter + time-box.
> Gắn vào cuối markdown view (Mục 5.5) — KHÔNG sang automation, KHÔNG đếm vào Math Check scripted.

## Mục 5.5. Exploratory Test Charters

*(Lặp lại block dưới cho mỗi charter)*

### CH-{NN}: {Tiêu đề vùng khám phá}

> **Loại charter** (theo [explore_and_consistency_rules.md](../../principles/explore_and_consistency_rules.md)): `CH-CMP` (so sánh giao diện màn tương đồng — §4) · `CH-FLEX` (thao tác linh hoạt/timing — §5) · `CH-TBD` (case bị chặn vì spec gap — §3) · generic (vùng bất định khác). Ghi mã loại vào Charter ID (vd `CH-CMP-01`).

| Trường | Nội dung |
|:---|:---|
| **Charter ID** | CH-{NN} |
| **Loại** | {CH-CMP \| CH-FLEX \| CH-TBD \| generic} |
| **Liên quan** | {unit_id} · {@risk} · {block} |
| **Explore** | {khám phá cái gì — vd "form động khi đổi loại hồ sơ liên tục"} |
| **With** | {công cụ/data — vd "Chrome devtools, data biên từ fixtures"} |
| **To discover** | {tìm rủi ro gì — vd "trạng thái UI không nhất quán khi toggle nhanh"} |
| **Time-box** | {vd 45 phút} |
| **Nguồn bất định** | {`[TBD]` nào / spec mơ hồ nào dẫn tới charter này} |
| **Oracle/heuristics** | {nguyên tắc đánh giá — consistency, CRUD, error-handling…} |
| **Ghi nhận** | {để trống — tester điền findings + bug ID sau phiên} |

> Khi một charter phát hiện hành vi xác định và có thể đặc tả → chuyển hóa thành testcase scripted (`@exec:automate`/`manual`) ở vòng cập nhật sau (xem [incremental_update_rules.md](../../principles/incremental_update_rules.md)).
