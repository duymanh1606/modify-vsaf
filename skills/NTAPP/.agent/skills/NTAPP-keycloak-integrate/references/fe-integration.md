# Phase FE — Angular + @vds/design-tokens + @vds/vds-keycloak-fe

Mục tiêu: thêm theme VDS + login/phân quyền Keycloak vào FE Angular, switch 2 chế độ login qua `environment.authProvider`, không vỡ layout/menu.

## 1. Registry + cài lib

`.npmrc` (cạnh package.json):
```
@vds:registry=http://nexus.digital.vn/repository/npm-private/
```
Cài: `@vds/design-tokens` (^1.0.9+) và `@vds/vds-keycloak-fe` (^1.2.2+). `@vds/vds-keycloak-fe` là gói **View Engine** → thêm `postinstall: ngcc` vào package.json scripts (nếu chưa có), peer dep bắt buộc `ng-zorro-antd ^12`.

## 2. Theme (@vds/design-tokens)

Thêm CSS token vào `angular.json` build `styles`:
```
node_modules/@vds/design-tokens/build/css/themes.css
node_modules/@vds/design-tokens/bridge/ng-zorro-12.css   # neu dung ng-zorro
```
Nếu cần đổi màu legacy/hex cứng sang token chuẩn hoặc gắn popup Theme Studio → có thể gọi riêng skill `vds-token-migrate`. Theme-aware qua CSS var; ảnh login khai qua `--url-*` trong scss theme nếu lib hỗ trợ.

## 3. environment.ts (switch 2 chế độ)

```ts
export const environment = {
  // ...
  authProvider: 'keycloak',            // 'keycloak' | 'vsa'
  endpoint: '/errors-management',      // TUONG DOI -> qua proxy dev; ghep apiBase keycloak-fe
  apiUrl: '/errors-management',        // TUONG DOI khi test local (qua proxy -> BE local); tranh tro remote timeout
  authenUrl: '/errors-management',
  storageKeyPrefix: 'vds_<app>_',      // prefix DUY NHAT cho storage cua auth lib
  defaultLang: 'vi',
  languages: [{ code:'en', name:'English (USA)'}, { code:'vi', name:'Tiếng Việt'}],
};
```
Prod (`environment.prod.ts`) thường giữ `authProvider:'vsa'` + URL remote — đổi khi sẵn sàng. Framework auth lib chỉ nối chuỗi `${apiBase}...` nên dạng tương đối chạy qua proxy OK. Proxy dev (`proxy-local.conf.json`): `{ "/errors-management/*": { "target":"http://localhost:8080", "changeOrigin":true } }`. **apiUrl phải tương đối** khi muốn call nghiệp vụ đi qua proxy về BE local, nếu để URL remote sẽ timeout/401 sai.

## 4. app.module.ts

```ts
KeycloakAuthModule.forRoot({
  apiBase: environment.endpoint + '/api/v1/',   // login = apiBase + 'private/auth'
  loginRoute: '/login',
  redirectAfterLogin: '/',
  storageKeyPrefix: environment.storageKeyPrefix,
  useBuiltinInterceptor: false,                 // EMS tu gan Bearer -> xem PermissionService
  defaultLang: environment.defaultLang,
  languages: environment.languages.map(l => ({ code:l.code, label:l.name })),
}),
NgxPermissionsModule.forRoot(),
```
i18n cần nhánh `KEYCLOAK.*` trong file lang. `AUTH_LOADING_SERVICE` là @Optional — không cần provide.

## 5. Routing + guard switch

```ts
const routes: Routes = [
  ...KEYCLOAK_AUTH_ROUTES,                       // login/forgot-password/change-password (path KHONG rong)
  { path: '', component: MainComponent /* layout */,
    canActivate: [AuthSwitchGuard, PermissionsGuard],
    canActivateChild: [AuthSwitchGuard, NgxPermissionsGuard],
    children: [ /* cac route nghiep vu, data: permissionGuard('/<route>') */ ] },
  { path: 'account/login', component: LoginComponent /* login VSA cu */ },
  { path: '**', redirectTo: '/404' },
];
```
`AuthSwitchGuard` delegate theo cờ (đọc `ACTIVE_AUTH_PROVIDER` = environment.authProvider, khác 'vsa' đều về 'keycloak'):
```ts
export const ACTIVE_AUTH_PROVIDER = environment.authProvider === 'vsa' ? 'vsa' : 'keycloak';
canActivate(r,s){ return ACTIVE_AUTH_PROVIDER==='keycloak'
  ? this.keycloakGuard.canActivate(r,s) : this.vsaGuard.canActivate(r,s); }
```
keycloak guard chưa login → redirect `/login`; vsa guard → `/account/login`. **ACTIVE_AUTH_PROVIDER là hằng số biên dịch build-time** → đổi cờ phải để ng serve recompile + hard reload (không chỉ F5).

## 6. Phân quyền (ngx-permissions, port từ product-catalog)

- Permission string: `"<sourceName> : <HTTP method>"` (separator `" : "`).
- `PermissionService.loadPermissions()`: `GET {endpoint}/api/v1/private/users/permissions` (tự gắn `Bearer` vì `useBuiltinInterceptor=false`), flatten `data[].scopes[]` → nạp `NgxPermissionsService` + localStorage['PERMS']. Cache theo access token.
- `PermissionsGuard` (canActivate, luôn true): chế độ keycloak → loadPermissions + `applyMenuFromPermissions` + `syncLegacyAccessToken`; chế độ vsa → cấp toàn bộ PERMS (chặn route để cơ chế cũ lo).
- Chặn route: `NgxPermissionsGuard` (canActivateChild) + `data: permissionGuard(url)` → không quyền redirect /404.
- `syncLegacyAccessToken`: ghi token keycloak vào `localStorage[<APP>_access_token]` để interceptor của framework layout gắn Bearer cho API nghiệp vụ.

## 7. Dựng menu + userData (nếu dùng framework layout kiểu mobile-money)

`applyMenuFromPermissions(perms)` ghi vào `localStorage[<APP>_userToken].userInfo` cấu trúc mà framework layout đọc:
```ts
const items = MENUS.filter(m => m.permissions.some(p => granted.has(p))).map(m => ({
  id: m.id, parentId: null, title: m.title, icon: null, tags: m.title, method: null,
  routerLink: m.url.replace(/^\/+/, ''),   // *** KHONG co '/' dau ***
  active:false, open:false, matched:false, navTitle:false, ord:m.ord, grantedComponent:[], items:[]
}));
const userData = buildUserDataFromToken();   // { userName, fullName, staffCode, staffName, email, shopCode:'', ... }
userToken.userInfo = { ...userToken.userInfo, userData, items };
```
**2 lỗi lường trước phải xử lý:**
1. `routerLink` PHẢI khớp tuyệt đối `rootPath` trong config lazy-load của framework (thường KHÔNG có `/` đầu, vd `ems/mapping-management`). Framework so `rootPath === moduleName(=tab.routerLink)`; lệch `/` → module loader ném `Cannot read 'modulePath' of undefined`.
2. `userData` phải có `userName` (+ fullName/staffCode/shopCode... để rỗng an toàn) vì header/user-menu đọc `userInfo.userData.userName` → thiếu sẽ `Cannot read 'userName' of undefined`. Lấy từ decode JWT keycloak (`preferred_username`, `name`, `email`).

Decode JWT an toàn UTF-8:
```ts
private decodeToken(t: string|null){ if(!t) return {}; try{
  const p=t.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
  return JSON.parse(decodeURIComponent(atob(p).split('').map(c=>'%'+('00'+c.charCodeAt(0).toString(16)).slice(-2)).join('')));
}catch{ return {}; } }
```

## 8. ErrorHandleGuard / HttpInterceptor redirect (LỖI LƯỜNG TRƯỚC)

Nhiều project cũ có HttpInterceptor bắt 401 rồi **hardcode** `router.navigate(['/account/login'])` (+ `localStorage.clear()`). Ở chế độ keycloak, một call 401 sẽ đá về trang login VSA sai + xoá token keycloak. **Fix: redirect theo authProvider**:
```ts
if (err.status === 401) {
  localStorage.clear();
  const loginUrl = ACTIVE_AUTH_PROVIDER === 'keycloak' ? '/login' : '/account/login';
  void this.router.navigate([loginUrl]);
}
```
Lưu ý: `localStorage.clear()` trên MỌI 401 có thể gây logout-loop nếu có call nền 401 sau login (vd refresh oauth/token của framework cũ). Nếu gặp loop → cho interceptor bỏ qua URL `oauth/token` và/hoặc chỉ xoá key liên quan.

## 9. Verify
`npm start` (proxy) → `localhost:4200` (tab ẩn danh) phải về đúng trang login theo authProvider; login user thật; menu render; bấm menu vào được module (không lỗi modulePath/userName); API nghiệp vụ 200 (qua proxy → BE local).
