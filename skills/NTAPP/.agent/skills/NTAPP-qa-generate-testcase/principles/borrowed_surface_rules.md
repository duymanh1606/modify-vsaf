# BORROWED SURFACE RULES — Bề mặt mượn (Delta Action trên màn của slice khác)

> **Mục đích:** slice không sở hữu màn nào (`units:` toàn BE) nhưng có hành động chạy trên màn của slice khác → test đúng phần hành động, **KHÔNG** test lại màn.
> **Nạp ở:** [step-00](../steps/step-00-shiftleft-gate.md) 0a-bis · [step-01](../steps/step-01-init-slice.md) · [step-02](../steps/step-02-plan-screen.md).

---

## 1. Nhận diện (chạy TRƯỚC khi kết luận `surface_type=service`)

| Bước | Làm gì | Kết luận |
|---|---|---|
| A | `units:` có `SCR-*`/`WGT-*`? | CÓ → `ui` bình thường, KHÔNG áp file này |
| B | Quét `## What to build` + `demoable` tìm ID `SCR-*`/`WGT-*` | Không có → `surface_type=service`, dừng file này |
| C | Cross-check cơ học: ID đó nằm trong `units:` của slice khác (grep `{slices_root}/*.md`) **và** slice đó khai `enhanced_by` chứa slice hiện tại | Fail 1 trong 2 → **DỪNG**, hỏi user (gap spec, KHÔNG đoán) |
| D | Kết luận | `surface_type=ui` · màn đó = `[Nav]` (host, nav-only) · bề mặt test = **cụm hành động** |
| E | Dựng Delta Manifest (§2) | In ở HITL gate Step 01 chờ ký |

Màn KHÔNG nằm trong `units:` slice hiện tại ⇒ **không bao giờ** là bề mặt test của slice này (suy ra, không cần khai báo thêm field).

## 2. Delta Manifest (BẮT BUỘC — ghi vào Context Ledger)

| Cột | Nội dung |
|---|---|
| Cụm hành động | tên nghiệp vụ (vd "Từ chối sub-link") |
| Trích dẫn | verbatim từ `What to build`/`demoable` + cite dòng |
| Control | nút / modal / banner / toast thuộc cụm |
| Oracle | ui / api / db |

**Nguồn định biên:** `What to build` + `demoable`. DD màn host chỉ dùng để lấy (a) nhãn hiển thị verbatim của chính delta, (b) đường vào, (c) điều kiện ẩn/khoá. **CẤM** dùng DD host để phát sinh cụm/case mới.

## 3. IN / OUT

- **IN:** control của cụm · modal/banner/toast do cụm sinh · state gating của cụm (ẩn/khoá/chặn theo trạng thái) · **chiều hành vi mà delta thay đổi trên control cũ** (chỉ chiều đó, không bung full rule của control cũ).
- **OUT → Precondition 1 dòng:** layout · bảng/grid · tab · filter/paging/sort · empty-state · responsive/zoom/keyboard cấp màn · mọi logic của unit thuộc host slice.

## 4. Hai ngân sách (KHÔNG gộp)

| Ngân sách | Giới hạn bởi | Ghi chú |
|---|---|---|
| UI | Delta Manifest | màn host = **0 case** |
| BE | `units:` của slice | hành vi không có mặt trên UI → dòng **API-only** (bỏ `@scr`, Công cụ `Postman`) |

Delta Manifest **không** giới hạn phần backend.

## 5. Ranh giới liên-slice (suy từ khai báo, KHÔNG phán đoán)

- Phạm vi liên-slice = **đúng** các slice mà file slice khai: `blocked_by` + ID nêu trong `What to build`/`demoable`.
- Hệ quả land ở slice **chưa khai** → assert **bất biến phủ định** ở biên (vd "trạng thái KHÔNG đổi", "0 dòng audit khi lỗi") + **1 dòng Coverage Debt** trỏ slice chủ.
- **Case xuyên chuỗi thuộc slice khai báo phía sau** (slice có `blocked_by` chứa slice này), KHÔNG phải slice này.

## 6. Override 9 chốt (Step 02)

| Chốt | Khi có bề mặt mượn |
|---|---|
| 3 | Biên liệt kê = **cụm hành động** (vẫn ĐẦY ĐỦ mọi element của cụm — không giảm độ sâu). Ghi 1 dòng `Base screen: OUT — host {slice}` |
| 4 | `screen-default-display` → N/A 0 case · `layout-visual`/`keyboard-navigation` áp cho **modal/banner của cụm** · `09-data-grid`/`11-independent-filter` N/A nếu thuộc host |
| 6 | `X` = Σ(rule-cases × control delta) + Σ(case BE của `units:`); control host = 0. `[GATE multi-source]` **không** áp cho ma trận thuộc unit của host slice — chỉ assert **transition đại diện** do delta sinh |
| 8 | Không lặp verify của host slice |

## 7. HARD CHECK (Step 03)

- Mọi dòng testcase phải map về **1 dòng Delta Manifest** HOẶC là dòng **BE API-only** thuộc `units:`. Dòng nhắc control ngoài 2 nhóm này → **FAIL**, xoá.
- Mỗi biên chưa khai (§5) phải có **đúng 1 dòng Coverage Debt** — cấm im lặng bỏ.
