# Troubleshooting — lỗi lường trước → nguyên nhân → fix

Tra khi gặp lỗi compile/runtime trong lúc tích hợp.

## BE

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `BaseController.class cannot be opened because it does not exist` | adapter khai `vds-spring-starter` scope **provided** → không kéo transitive | thêm `vds-spring-starter` + `spring-boot-starter-security` + `commons-collections` vào pom (be-integration §1) |
| `ConflictingBeanDefinitionException` (vd bean `responseFactory`) | 2 lib cùng `vn.com.viettel.vds` có class trùng tên bean mặc định, bị `@ComponentScan` gom | `SafeBeanNameGenerator` (bean name = FQN) — be-integration §3. `allow-bean-definition-overriding` KHÔNG cứu |
| Login 500 `NoSuchMethodError: UriBuilder.resolveTemplate(String,Object,boolean)` | JAX-RS 1.1 cũ (`jsr311-api` qua ribbon/jersey1) che JAX-RS 2.1 (resteasy/keycloak) | exclude `javax.ws.rs:jsr311-api` khỏi starter kéo nó vào; rebuild+restart — be-integration §2 |
| Bearer token keycloak bị 401 ở API nghiệp vụ dù đã login | chain VSA `@EnableResourceServer` (order thấp) match mọi request, chặn trước chain keycloak | tắt 3 config VSA ở chế độ keycloak (excludeFilters + `@ConditionalOnProperty(vsa)`) — be-integration §4 |
| Wiring fail thiếu `TokenStore` khi `auth.provider=keycloak` | `UserController` lib nền inject TokenStore (chỉ có ở vsa) nhưng vẫn bị scan | exclude `UserController` + đăng ký lại `@Bean` trong config `@ConditionalOnProperty(vsa)` — be-integration §4 |
| Build không tái lập / tự nhảy version | dependency để version range `[1.0,)` | pin version cố định (bản đang resolve theo `dependency:tree`) |

### JwtService/UserUtils instanceof-safe (chuỗi identity nội bộ)
```java
Object principal = SecurityContextHolder.getContext().getAuthentication() != null
    ? SecurityContextHolder.getContext().getAuthentication().getPrincipal() : null;
if (principal instanceof UserInfoBean) { /* VSA: roleId so, email tu getUserData() */ }
else if (principal instanceof KeycloakPrincipal) {
    AccessToken t = ((KeycloakPrincipal<?>) principal).getKeycloakSecurityContext().getToken();
    // role = t.getResourceAccess(clientId).getRoles()  (TEN client role)
    // username = t.getPreferredUsername(); email = t.getEmail()
}
```
Service downstream map role theo TÊN role (không phải roleId số) — chỉnh chỗ nhận role cho chấp nhận cả 2.

### Lệnh quét jar để biết loại bean nào / dependency nào (trước khi exclude)
```bash
JAR=~/.m2/repository/.../lib.jar; TMP=$(mktemp -d); unzip -q "$JAR" -d "$TMP"
# class nao la bean (stereotype)
for c in $(find "$TMP" -name "*.class"|grep -v '\$'); do fq=$(echo $c|sed "s#$TMP/##;s#/#.#g;s#.class##");
  javap -v -p -cp "$TMP" "$fq" 2>/dev/null|grep -qE "stereotype/(Component|Service|Repository|Controller)|annotation/(Configuration|RestController)" && echo "$fq"; done
# class nao inject TokenStore/oauth2
for c in ...; do javap -p -c -cp "$TMP" "$fq" 2>/dev/null|grep -qiE "TokenStore|security/oauth2" && echo "$fq"; done
# tim ten bean trung giua 2 lib: so simple-name (decap) cua cac class co stereotype
```
`dependency:tree` chẩn classpath: `mvn -o dependency:tree | grep -iE "ws.rs|jsr311|jersey|resteasy|keycloak"`.

## FE

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `Cannot read properties of undefined (reading 'modulePath')` khi bấm menu | `item.routerLink` có `/` đầu, không khớp `rootPath` (không slash) trong config lazy-load; framework so `===` | `routerLink: url.replace(/^\/+/, '')` — fe-integration §7 |
| `Cannot read properties of undefined (reading 'userName')` sau login | `userInfo.userData` thiếu (header đọc `userInfo.userData.userName`) | populate `userData` từ token keycloak — fe-integration §7 |
| Chế độ keycloak nhưng nhảy về trang login VSA (`/account/login`) | HttpInterceptor bắt 401 hardcode navigate `/account/login` (+ `localStorage.clear()`) | redirect theo `ACTIVE_AUTH_PROVIDER` — fe-integration §8 |
| Đổi `authProvider` mà không thấy đổi trang login | `ACTIVE_AUTH_PROVIDER` là hằng số build-time | ng serve recompile + hard reload (Ctrl+Shift+R), xoá token mode cũ |
| API nghiệp vụ timeout khi test local | `environment.apiUrl` trỏ server remote, không qua proxy | apiUrl tương đối `/…` → qua proxy dev → BE local — fe-integration §3 |
| `oauth/token` timeout/404 nền | framework cũ (mobile-money) refresh token VSA bắn nền | vô hại nếu chỉ noise; nếu gây logout-loop qua ErrorHandleGuard thì skip URL `oauth/token` |
| `Cannot find module ./pages/...` khi vào menu | (nếu dùng custom NgModuleFactoryLoader) menu mới chưa khai ở lazy-module loader | thêm cả `menu-config.ts` + lazy-module.loader.ts |
| Warning `Could not find Angular Material core theme` | thiếu Material theme css | vô hại nếu không dùng Material; bỏ qua |

## Keycloak

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| Partial Import trên Console báo lỗi chung chung / nuốt lỗi | file khai lại `clients[]` mà client đã tồn tại → ifResourceExists FAIL rollback cả file | bỏ mảng `clients` khỏi file; tách authorization sang file riêng apply bằng kc-admin.js |
| Đổi username không ăn (PUT trả 2xx nhưng username giữ nguyên) | realm `editUsernameAllowed=false` | delete + recreate user (username chỉ set lúc tạo) — keycloak-config "Lưu ý đổi tên" |
| `curl` tới `*.digital.vn` DNS fail trong sandbox | proxy công ty | `curl --noproxy "*"` hoặc dùng Node core http (kc-admin.js đã vậy) |
| apply-authz báo role chưa tồn tại | chạy authz trước roles | chạy `apply-roles` trước `apply-authz` |
