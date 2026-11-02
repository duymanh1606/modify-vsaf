# Phase Keycloak — Quét project → sinh cấu hình → apply

Mục tiêu: từ FE (menu + permission) và BE (endpoint thật) sinh cấu hình Authorization Services của Keycloak, review, rồi apply idempotent.

## Mô hình chuẩn (convention từ product-catalog / EMS)
- **resource** = một màn hình / capability. `name` PHẢI trùng `sourceName` mà FE dùng trong permission string. `uris` = **đường dẫn API BE THẬT** (full path enforcer nhìn thấy). `scopes` = **HTTP method** (GET/POST/PUT/DELETE).
- Hành động đặc biệt tách **resource riêng** (approve/import/export/xoá) với uri riêng + scope riêng.
- **policy** = nhóm role (role-based hoặc group-based). Đặt theo NĂNG LỰC dùng chung (P_VIEW, P_WRITE, P_APPROVE, P_IMPORT, P_EXPORT...) thay vì mỗi menu một policy → gọn, linh hoạt.
- **permission** = scope-based, gắn (resource + scope) ↔ policy, `decisionStrategy` AFFIRMATIVE.
- **client role** = vai trò (ADMIN/SOC/DEV/BA/CSKH/...), map từ role hệ cũ.
- **users** mẫu để test (mật khẩu tạm, xoá khi lên thật).

## Bước 1 — Quét FE
Tìm (Grep/Read):
- File hằng menu (vd `core/constants/menu.constant.ts`): mỗi menu có `id`, `title`, `url`, `permissions[]`. → danh sách màn + route.
- File hằng permission (vd `core/constants/perms.constant.ts`): các key `<SOURCE>_<METHOD>` = `"<sourceName> : <METHOD>"`. → tập (sourceName, method) FE mong đợi.
- `app-routing.module.ts`: path + `data: permissionGuard('/<route>')`.
Rút ra: mỗi màn → sourceName + các method (view=GET, write=POST/PUT, ...) + route FE.

## Bước 2 — Quét BE (để URI/scope bám endpoint THẬT)
Tìm controller (`@RestController`/`@RequestMapping`), liệt kê path + HTTP method thật. Nếu BE chỉ **proxy** sang downstream (như EMS: `/errors-management/v1/ems/**`), lấy path proxy làm uri. Xác định:
- Endpoint ghi/duyệt/import = POST; search/export = GET; có PUT/DELETE không.
- Endpoint approve là per-module (`/<module>/approve`) hay tách? import/export toàn cục hay per-module?
- Endpoint lấy quyền của adapter: `${base-path}/users/permissions` → resource `<PREFIX>_PERMISSION`.
Đối chiếu FE↔BE: resource name theo FE (sourceName), uri/scope theo BE thật.

## Bước 3 — Sinh 2 file (đặt trong thư mục `keycloak/` của project đích)

### `<project>-keycloak-partial-import.json` (roles + users, KHÔNG có mảng `clients`)
> Bỏ hẳn `clients[]`: nếu client đã tồn tại, khai lại trong partial-import (ifResourceExists mặc định FAIL) sẽ rollback TOÀN BỘ file. Client tạo/bật Authorization Services thủ công 1 lần trên Console.
```json
{
  "roles": { "client": { "<client-id>": [
    { "name": "ADMIN", "description": "...", "clientRole": true },
    { "name": "DEV",   "description": "...", "clientRole": true }
  ] } },
  "users": [
    { "username": "<prefix>_admin", "enabled": true, "emailVerified": true,
      "firstName": "...", "lastName": "...", "email": "...",
      "credentials": [ { "type":"password", "value":"<pwd>", "temporary": false } ],
      "clientRoles": { "<client-id>": ["ADMIN"] } }
  ]
}
```
Username test nên có tiền tố dự án (vd `ems_admin`, `ems_dev`) tránh đụng tài khoản dùng chung (`admin` thường đã bị dự án khác chiếm). `temporary:false` để đăng nhập được ngay khi test.

### `<project>-keycloak-authorization.json` (định dạng RIÊNG của kc-admin.js, không phải export Keycloak)
> Role-policy cần UUID role thật (chỉ có sau khi tạo) → script tự tra UUID lúc apply, KHÔNG viết tay.
```json
{
  "resources": [
    { "name": "<SRC>_MODULE", "displayName": "...", "uris": ["/real/be/path/*"], "scopes": ["GET","POST"] },
    { "name": "<SRC>_APPROVE", "displayName": "...", "uris": ["/real/be/path/approve"], "scopes": ["POST"] },
    { "name": "<PREFIX>_PERMISSION", "uris": ["/.../users/permissions"], "scopes": ["GET"] }
  ],
  "rolePolicies": [
    { "name": "P_VIEW",    "roleNames": ["ADMIN","SOC","DEV","BA","CSKH"] },
    { "name": "P_WRITE",   "roleNames": ["ADMIN","DEV","BA"] },
    { "name": "P_APPROVE", "roleNames": ["ADMIN","SOC"] }
  ],
  "scopePermissions": [
    { "name": "<SRC>_VIEW",  "decisionStrategy":"AFFIRMATIVE", "resources":["<SRC>_MODULE"],  "scopes":["GET"],  "policies":["P_VIEW"] },
    { "name": "<SRC>_WRITE", "decisionStrategy":"AFFIRMATIVE", "resources":["<SRC>_MODULE"],  "scopes":["POST"], "policies":["P_WRITE"] }
  ],
  "remove": { "permissions": [], "policies": [] }
}
```
`remove` để dọn artifact cũ (policy/permission gộp cũ) khi tái cấu trúc.

## Bước 4 — Review với user
In bảng: resource → uri → scope → policy → role nào có quyền. Xác nhận ma trận (ai view/write/approve/import/export). Chỉ apply khi user OK.

## Bước 5 — Apply (idempotent) bằng scripts/kc-admin.js

> **Phiên bản công cụ:** `kc-admin.js` phải là **v2026-08-20 trở lên** (chạy không tham số sẽ in phiên bản ở dòng đầu).
> Bản cũ hơn KHÔNG hiểu `resourceType` trong `scopePermissions` và bỏ qua `remove.resources`: permission sẽ được tạo
> với danh sách resource rỗng, áp cho MỌI resource có scope đó — rộng hơn hẳn ý định, và không báo lỗi.

## ⚠ BÀI HỌC — bản xuất phân quyền gắn chặt với MỘT client

**Đã xảy ra thật (2026-08-21, realm `pmt-staging`).** Đọc mục này trước khi giao hoặc nạp bất kỳ bản xuất phân quyền nào.

### Chuyện gì xảy ra

Role policy lưu tham chiếu vai trò dạng `<clientId>/<roleName>` **ngay bên trong `config.roles`**, không phải ở khoá nào nhìn thấy khi lướt file. Bản xuất nhắm client A bị nạp vào client B thì role policy của B bị ghi đè, trỏ sang client A không tồn tại, và **mọi permission mất hiệu lực cùng lúc**.

Lần đó: bản xuất nhắm `policy-uat` bị nạp vào chính `policy-staging`. Tài khoản quản trị tụt từ **48 quyền xuống 1**, mọi đường dẫn được bảo vệ trả 403, và `GET /authz/resource-server/settings` trả 500.

### Vì sao rất dễ đọc nhầm triệu chứng

Resource và scope trùng tên sẵn nên **không đổi gì** — người nạp nhìn vào thấy resource còn nguyên, scope còn nguyên, và kết luận "chỉ import được scope, phần khác không vào". Thực tế ngược lại: scope là thứ *không* bị ảnh hưởng, còn thứ bị phá là role policy. Đừng chẩn đoán bằng cách đếm resource.

### Cách chẩn đoán đúng — lấy RPT thật, đừng suy luận

```bash
# Đăng nhập một tài khoản đã biết chắc quyền, rồi đổi lấy RPT
curl -s -X POST "$BASE/realms/$REALM/protocol/openid-connect/token" \
  -d grant_type=urn:ietf:params:oauth:grant-type:uma-ticket \
  -d audience=<clientId> -d response_mode=permissions \
  -H "Authorization: Bearer $USER_ACCESS_TOKEN"
```

Đếm số quyền trả về. Tài khoản quản trị mà chỉ còn `Default Resource` nghĩa là role policy đã hỏng.

### Phòng: ba lớp, đã dựng sẵn từ v2026-08-21d

1. **Tên tệp mang tên client đích** (`export-client` tự đặt tiền tố theo `--new-client-id`). Nhìn tên tệp là biết nó nhắm vào đâu.
2. **In cảnh báo cuối mỗi lần chạy** `export-client`.
3. **Trước khi nạp, mở tệp phân quyền kiểm một dòng bất kỳ** có `"type": "role"` và xác nhận `config.roles` ghi đúng tên client sắp nạp vào.

Cảnh báo **không** được nhét vào khoá lạ cấp một trong JSON: chưa kiểm chứng được Keycloak có chấp nhận khoá lạ hay không, và không đưa rủi ro chưa biết vào đúng bộ tệp dùng để khôi phục.

### Chữa

```bash
# 1. Áp lại bản gốc theo khuôn công cụ (bản này khai vai trò theo TÊN nên không dính client nào)
node "$KC" apply-authz --client <client-bi-hong> --file <ban-goc-authorization.json>
# 2. Xoá policy mồ côi mà bản nạp nhầm để lại — kiểm không còn permission nào tham chiếu rồi mới xoá
# 3. Lấy lại RPT để xác nhận số quyền đã về đủ
```

Bản gốc theo khuôn công cụ khai vai trò bằng **tên trần** (`roleNames: ["PFA_ADMIN"]`) và nhận client qua tham số `--client`, nên nó không mang tên client nào trong nội dung — áp vào client nào cũng đúng. Đó là lý do nên giữ nó làm bản gốc thay vì bản xuất theo khuôn Keycloak.

### Chiều ngược lại — sao client sang môi trường khác

Client đã chạy rồi, cần dựng lại ở realm khác thì dùng `export-client` thay vì khai lại từ đầu:

```
node scripts/kc-admin.js export-client --client <clientId> --out keycloak/ --prefix <ten>
```

Sinh ba tệp nạp tay được trên Console: client kèm vai trò, client kèm vai trò kèm người dùng, và phần
phân quyền theo khuôn gốc Keycloak.

**Người dùng chưa nêu rõ thì BẮT BUỘC hỏi lại hai điều trước khi chạy:** tên client ở môi trường mới là gì
(chưa biết thì để trống, tệp sẽ mang chỗ giữ chỗ để người nạp tự thay), và có xuất người dùng hay không
(môi trường thật thường là không). Chi tiết đầy đủ ở skill `keycloak-admin`.
ENV: `KEYCLOAK_BASE_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_ADMIN_USER`, `KEYCLOAK_ADMIN_PASS` (admin realm-user, client_id=admin-cli). Client phải tồn tại + bật Authorization Services trước.
```
# Bat buoc chay TRUOC khi apply — kiem cu phap file, khong can mang:
node scripts/kc-admin.js validate-authz    --file keycloak/<project>-keycloak-authorization.json
node scripts/kc-admin.js diagnose          --client <client-id>
node scripts/kc-admin.js apply-roles        --client <client-id> --file keycloak/<project>-keycloak-partial-import.json
node scripts/kc-admin.js apply-users        --client <client-id> --file keycloak/<project>-keycloak-partial-import.json
node scripts/kc-admin.js apply-authz        --client <client-id> --file keycloak/<project>-keycloak-authorization.json
```
Thứ tự: roles → users → authz (policy tham chiếu role UUID; permission tham chiếu policy).

## Bước 6 — Verify
- `diagnose` lại: đủ role/resource/policy.
- Policy Evaluation API (`/clients/{id}/authz/resource-server/policy/evaluate`, entitlements=true) cho vài user mẫu → khớp ma trận kỳ vọng.
- Nếu bật `app.keycloak.enable-authorization=true` ở BE → test gọi API thật với token từng role.

## Lưu ý đổi tên user (gotcha)
Realm có thể `editUsernameAllowed=false` → KHÔNG đổi username tại chỗ (PUT bỏ qua field username; reset-password vẫn ăn). Muốn đổi tên phải **delete + recreate** (username chỉ set được lúc tạo). Trước khi xoá/đổi user cũ, xác minh đúng là tài khoản test mình tạo (createdTimestamp, chỉ có role của dự án, không có realm-role/client-mapping lạ) — tránh đụng user thật trên realm dùng chung.
