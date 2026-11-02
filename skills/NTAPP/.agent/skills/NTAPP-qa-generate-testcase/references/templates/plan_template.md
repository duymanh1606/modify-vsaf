> **Biến thể theo `surface_type`:** khung dưới đây (§1–§5) cho bề mặt **`ui`**. Bề mặt **`service`** (no-UI) dùng khung ở cuối file ("BIẾN THỂ SERVICE") — thay §1 Ánh xạ Nhãn UI bằng Contract Map, §2 Bảng Mapping Rule đổi cột "Loại UI Control" → "Field/Contract element", giữ nguyên §3–§5.

### 1. Nhật Ký Đọc File & Ánh Xạ Nhãn Hiển Thị (UI Label Mapping)
- **Tài liệu màn hình hiện tại & Backend:** ...
- **Tài liệu màn hình đích (Target Screen):** ... (Ghi chú rõ nếu màn hình này không thuộc SLICE hiện tại)

**Ánh Xạ Nhãn Hiển Thị (LIỆT KÊ ĐẦY ĐỦ TỪNG ELEMENT — không glossary chung):**
- Liệt kê **MỌI** element của màn: từng control/tiêu đề/placeholder/cột bảng/empty-state/banner/dialog/toast/inline-error → `biến_kỹ_thuật` → **Nhãn hiển thị verbatim + cite DD**. Thiếu element = thiếu testcase ở Step 03 (xem slice_planning Chốt 3).

### 2. Bảng Mapping Rule (Targeted Mapping Bắt Buộc)
| Loại UI Control | Nạp File Rule Tương Ứng |
|:---|:---|
| Global/Core | `00-core/...` |
| Textbox (Tên trường) | `02-input/...` |
| Checkbox/Radio | `03-selection/...` |

### 3. Tính Toán Toán Học & Ma Trận Quyết Định (Mathematical Forcing)
- **Validation `Field 1`**: ... cases
- **Tổng số lượng dự kiến tối thiểu**: ... cases.

**Ma Trận Quyết Định — nếu gom ≥2 nguồn: dòng đầu PHẢI là Cartesian các nguồn × {0,1,M} (nhánh nghiệp vụ/lỗi = bảng orthogonal, không thay thế):**
| Case | [Điều Kiện 1] | [Điều Kiện N] | Kết quả & Trạng thái |
|:---:|:---:|:---:|:---|
| 1 | ... | ... | ... |

### 4. Self-Reflection Gate (Cross-Source)
> **Đánh giá Self-Audit:** Tính năng này có giao thoa dữ liệu không? Tôi ĐÃ vẽ rõ Ma Trận Quyết Định gồm N trường hợp...

### 5. (ĐÃ BỎ) Checklist Kiểm Đếm
> Plan **KHÔNG** còn section này. Tổng `X` lấy từ **§3 (Math Forcing)**. Materialize 1-1 mỗi rule-case → 1 dòng testcase ở **Step 03** (Math Check `X = Y`).
> Ghi kèm ở §3/§4: **Phân định Action-Verify** (Màn trước → verify màn đích trong Expected của hành động · Màn sau → chỉ hành động nội tại).

---

## BIẾN THỂ SERVICE (no-UI: HUB/MPF/INT) — xem [service_surface_rules.md](../../principles/service_surface_rules.md)

### 1s. Contract Map (thay Ánh Xạ Nhãn UI)
**Operation:** `{METHOD /path}` / tên operation nghiệp vụ
| Request field (kiểu · required · ràng buộc) | Response / HTTP status | Error catalog (mã → status → điều kiện) | Side-effect (bảng DB · event/MSG · audit log) | State machine (transition hợp lệ) |
|:---|:---|:---|:---|:---|
| ... | ... | ... | ... | ... |

*Phân loại Dynamic Data (field khóa tra cứu/unique):* `field → Tier(0/1/2/3) → source_id` *(BẮT BUỘC — Quality Gate 3b)*

### 2s. Bảng Mapping Rule (tầng service)
| Field/Contract element | Nạp File Rule Tương Ứng |
|:---|:---|
| Core | `00-core/...` (Ledger) |
| Backend (LUÔN áp) | `10-be/backend-resilience-rule`, `10-be/data-visibility-rule` |
| Field required/length/format/enum (tầng payload) | `02-input/*`, `03-selection/*` (phần allowed-values) |
| Duplicate / error response | `06-validation/duplicate-data-rule`, `error-response-behavior-rule` |
| N/A (đánh dấu 0 case) | `01-ui/*`, `04-dynamic-form/*`, phần render `03-selection`/`09-data-grid` |

### 3s–5s
Dùng §3 (Math + Decision Matrix — bổ sung nguồn: error catalog completeness · state machine transition · idempotency/dedupe · resilience), §4 (Self-Reflection); bung testcase 3 nhóm (**Hợp đồng & Request Validation / Nghiệp vụ & E2E / Phân quyền & ATTT**) ở Step 03 như bề mặt ui — KHÔNG checklist vào plan (Chốt 8).
