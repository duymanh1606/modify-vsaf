---
name: NTAPP-keycloak-integrate
description: >-
  Tích hợp bộ lib VDS theme (@vds/design-tokens) + đăng nhập/phân quyền Keycloak (FE @vds/vds-keycloak-fe, BE
  vds-keycloak-adapter) vào một dự án FE Angular + BE Spring Boot bất kỳ, kèm switch 2 chế độ login
  (keycloak/vsa), tự dò & fix lỗi thiếu/duplicate thư viện BE, các lỗi FE lường trước được, và quét FE+BE để
  sinh cấu hình Keycloak (client/role/resource/policy/permission/user) rồi apply idempotent qua Admin REST API.
  Dùng khi user muốn "tích hợp keycloak vào dự án", "thêm login keycloak FE/BE", "áp theme VDS + keycloak",
  "sinh cấu hình Keycloak từ project", hoặc gõ /vds-keycloak-integrate. CẢNH BÁO BẮT BUỘC NHẮC LẠI cho người
  dùng mỗi lần sinh bản xuất phân quyền: tệp gắn chặt với MỘT client vì role policy nhúng tham chiếu dạng
  clientId/roleName bên trong config, nạp vào client khác sẽ ghi đè role policy của nơi đó và làm mất sạch quyền
  — triệu chứng dễ đọc nhầm thành "chỉ import được scope" vì resource và scope không bị ảnh hưởng.
---

# VDS Keycloak Integrate

Tích hợp theme VDS + đăng nhập/phân quyền Keycloak vào FE (Angular) + BE (Spring Boot), mirror playbook đã đúc kết từ dự án EMS (mirror của product-catalog). Chạy theo 3 phase độc lập; có thể chạy cả 3 tuần tự hoặc từng phase.

## Khi nào chạy phase nào
- **Phase FE** — tích hợp `@vds/design-tokens` + `@vds/vds-keycloak-fe`, switch authProvider, ngx-permissions, dựng menu/userData, fix các lỗi FE lường trước.
- **Phase BE** — thêm `vds-keycloak-adapter` + dependency kèm theo, fix bean conflict / JAX-RS / version, switch chain vsa↔keycloak, chuỗi identity nội bộ.
- **Phase Keycloak** — quét FE (menu/permission) + BE (endpoint controller) → sinh file cấu hình client/role/resource/policy/permission/user → review → apply idempotent qua Admin REST API bằng `scripts/kc-admin.js`.

## Nguyên tắc bắt buộc (đọc trước khi làm)
1. **KHÔNG tự động apply lên Keycloak khi chưa review.** Luôn sinh file cấu hình + bảng tóm tắt, cho user xác nhận rồi mới `apply-*`. Realm thường DÙNG CHUNG nhiều dự án.
2. **KHÔNG ghi access token / client secret ra file hay log.** Token chỉ giữ trong biến nhớ tiến trình. Secret truyền qua ENV hoặc hỏi user tại thời điểm chạy, không hardcode vào repo.
3. **KHÔNG commit secret.** Nếu buộc phải để tạm trong `application.properties` (git nội bộ), cảnh báo user externalize + rotate.
4. **Verify sau mỗi phase**: BE phải `mvn compile` SUCCESS; FE phải build/serve được; Keycloak apply xong phải `diagnose` lại + Policy Evaluation.
5. **Idempotent**: mọi thao tác Keycloak chạy lại nhiều lần phải an toàn (create-or-update, không tạo trùng).
6. Trước khi sửa file, **dò trước** (grep/read) để bám đúng convention project đích; đừng áp cứng tên biến/đường dẫn của EMS.

## Quy trình tổng quát

### Bước 0 — Khảo sát project đích
Xác định: thư mục FE (Angular, có `angular.json`), thư mục BE (Spring Boot, có `pom.xml`), có sẵn login cũ (VSA/oauth) không, có framework layout riêng không (vd `mobile-money` / `mobile-money-layout`), Keycloak realm/base-url/client dự kiến. Ghi lại rồi hỏi user xác nhận cái nào thiếu.

### Bước 1 — Phase BE (làm trước để có endpoint chuẩn cho Keycloak)
Theo `references/be-integration.md`. Tóm tắt: thêm 4 dependency (adapter + vds-spring-starter + spring-boot-starter-security + commons-collections), cấu hình `app.keycloak.*` + `auth.provider`, xử lý bean conflict (`SafeBeanNameGenerator` + excludeFilters cho 3 config OAuth2 của lib nền + `UserController`), loại JAX-RS cũ `jsr311-api`, pin version lib nền. Kết thúc bằng `mvn compile` SUCCESS.

### Bước 2 — Phase FE
Theo `references/fe-integration.md`. Tóm tắt: `.npmrc` registry VDS, cài `@vds/design-tokens` + `@vds/vds-keycloak-fe` (postinstall ngcc), `KeycloakAuthModule.forRoot`, `...KEYCLOAK_AUTH_ROUTES` + `AuthSwitchGuard`, ngx-permissions `PermissionsGuard`, dựng menu + `userData` từ token, các fix lường trước (routerLink không slash, ErrorHandleGuard redirect theo authProvider, apiUrl tương đối để qua proxy khi test local). Kết thúc bằng serve chạy được, login + menu OK.

### Bước 3 — Phase Keycloak
Theo `references/keycloak-config.md`. Quét FE (menu.constant/perms.constant/routes) + BE (controller `@RequestMapping`) → sinh 2 file: `<project>-keycloak-partial-import.json` (roles + users, KHÔNG có mảng `clients`) và `<project>-keycloak-authorization.json` (resources + rolePolicies + scopePermissions + remove). Review với user. Apply bằng `scripts/kc-admin.js` (ENV: `KEYCLOAK_BASE_URL/REALM/ADMIN_USER/ADMIN_PASS`, arg `--client`). Verify bằng `diagnose` + Policy Evaluation.

## Tham chiếu
- `references/be-integration.md` — playbook BE + snippet code.
- `references/fe-integration.md` — playbook FE + snippet code.
- `references/keycloak-config.md` — cách quét & mô hình hoá cấu hình Keycloak.
- `references/troubleshooting.md` — bảng lỗi → nguyên nhân → fix (tra khi gặp lỗi runtime/compile).
- `scripts/kc-admin.js` — CLI gọi Keycloak Admin REST API (diagnose/validate-authz/export-client/apply-roles/apply-users/apply-authz/run-partial-import), idempotent, bỏ qua proxy.

## Môi trường đã biết (tham khảo, xác nhận lại với user)
- Registry npm VDS + nexus maven nội bộ (`nexus.digital.vn`). FE lib là gói **View Engine** → cần `postinstall: ngcc`.
- Từ sandbox có proxy công ty: `curl` tới `*.digital.vn` cần `--noproxy "*"`; Node core `http/https` tự đi thẳng (kc-admin.js dùng cách này).
- Máy build không có `mvn` trên PATH thì dùng maven wrapper trong `~/.m2/wrapper/...` với `JAVA_HOME` JDK8.
