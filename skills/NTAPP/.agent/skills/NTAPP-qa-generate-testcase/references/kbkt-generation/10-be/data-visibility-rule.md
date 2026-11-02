---
cases_count: 7
---

# Data Visibility Rule (Cross-Actor Scoping)

## Mục đích

Sinh testcase kiểm tra phạm vi hiển thị dữ liệu theo actor/vai trò (data scoping) — dữ liệu do user/role này tạo có hoặc không hiển thị cho user/role khác đúng đặc tả nghiệp vụ. Khác với 403-deny của [backend-resilience-rule](./backend-resilience-rule.md) (chặn quyền); rule này kiểm phạm vi thấy được của kết quả.

## Điều kiện kích hoạt

Kích hoạt khi list/search gom dữ liệu theo business key (merchant/filter/trạng thái) mà response có field người tạo (`createdBy`)/đơn vị/role, HOẶC spec mô tả phạm vi xem theo vai trò.

## Thành phần cần kiểm tra

- Bản ghi seed bởi actor A.
- Phiên đăng nhập actor B (khác user / khác role).
- Danh sách kết quả và field `createdBy`/đơn vị.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Cùng scope, khác người tạo: bản ghi do A tạo hiển thị cho B khi spec quy định phạm vi theo filter (không theo `createdBy`).
2. Role cao hơn (Admin): xem được bản ghi của mọi user trong scope.
3. Khác scope: bản ghi ngoài phạm vi (merchant/đơn vị khác) KHÔNG hiển thị cho actor không thuộc scope.
4. Role thấp/không quyền: chặn theo đặc tả (ẩn field / không thấy record / 403).
5. Field `createdBy` chỉ hiển thị, KHÔNG dùng làm điều kiện lọc trừ khi spec yêu cầu.
6. Bộ lọc theo người tạo (nếu spec có): lọc đúng theo `createdBy` được chọn, không mặc định giới hạn về user đang đăng nhập.
7. **Rendering theo role — mỗi role × mỗi bề mặt 1 case riêng.** Cấm case UI trần "màn hiện N cột" (ngầm mọi role như nhau). Phải neo role cho case mặc định + 1 case cho mỗi biến thể thu hẹp. Tách theo bề mặt: ẩn ô-lọc ≠ ẩn cột-bảng ≠ ẩn menu ≠ ẩn CTA — mỗi cái 1 dòng, không suy cái này ra cái kia. Field/cột ẩn assert KHÔNG render DOM (khác disabled).

## Yêu cầu data (bắt buộc)

Multi-actor: seed bằng **≥2 user/role khác nhau**; `fixtures.yaml` phải có ≥2 auth principal (mỗi principal 1 dataset seed riêng). Cấm test cross-actor với 1 principal.

## Expected chuẩn

Kỳ vọng dựa hoàn toàn vào đặc tả phạm vi trong `_detailed_design`/HLD, ví dụ:

```text
Danh sách gom theo merchantCode <value>, hiển thị đủ bản ghi của mọi người tạo trong scope; field Người tạo chỉ hiển thị, không lọc.
```

## Điều kiện cần Q&A

Tạo Q&A nếu spec không nói rõ:

- Phạm vi visibility theo `createdBy` hay theo filter/scope?
- Role nào xem được data của role/user khác?
