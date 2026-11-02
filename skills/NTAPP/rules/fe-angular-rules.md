# Rule khi code Frontend (Angular)

Các rule dưới đây CHỈ áp dụng khi sửa/tạo file Frontend Angular (`*.component.ts` và các `*.ts` thuộc FE, `*.html`, `*.scss`, `*.css`, `*.sass`, `*.less`). Với file Backend hoặc file không thuộc FE thì bỏ qua toàn bộ mục này. Cách áp dụng giống rule Sonar: review phần code FE đã đụng tới TRƯỚC khi báo hoàn thành, phát hiện vi phạm thì sửa luôn và nêu trong báo cáo cuối.

# SENIOR ANGULAR & FRONTEND RULES (OPTIMIZED FOR LLM)

> Stack: Angular 16+ · ngx-translate · Keycloak · SCSS.
> Mỗi rule CẤM đều có mục **Ngoại lệ** — ngoài ngoại lệ đó ra, không được vi phạm.
> [Legacy ≤15] = chỉ áp dụng khi project dùng Angular 15 trở xuống.

## 1. RXJS & DECLARATIVE PROGRAMMING
* **CẤM nested subscription**: dùng higher-order operator để flatten. Chọn đúng operator theo ngữ cảnh:
  - `switchMap`: search/autocomplete/param đổi liên tục (hủy request cũ).
  - `exhaustMap`: submit button, action ghi dữ liệu (chống double-click).
  - `concatMap`: các thao tác ghi cần đúng thứ tự.
  - `mergeMap`: chỉ khi cần chạy song song và thứ tự không quan trọng.
* **Ưu tiên declarative**: expose stream qua `async` pipe hoặc `toSignal()`; hạn chế subscribe trong TS.
  - **Ngoại lệ được subscribe trong TS**: side-effect thuần (navigation, toast, dialog, gọi API ghi) — khi đó BẮT BUỘC áp Rule 2.
* **Cache API dùng chung**: `shareReplay({ bufferSize: 1, refCount: true })`.
  - Master-data/config cần sống suốt session → cache trong service `providedIn: 'root'` (BehaviorSubject/signal), không dựa vào `refCount`.
* **Error không được kill stream**: `catchError` đặt ở INNER observable (bên trong `switchMap`/...), không đặt ở outer pipe của stream long-lived (valueChanges, router events).

## 2. QUẢN LÝ SUBSCRIPTION & MEMORY LEAK
* **Mọi subscribe trong TS phải tự hủy**: dùng `takeUntilDestroyed(this.destroyRef)` — đặt CUỐI CÙNG trong `pipe()`.
  - [Legacy ≤15] dùng `takeUntil(this.destroy$)` + `destroy$.next(); destroy$.complete();` trong `ngOnDestroy()`.
  - **Ngoại lệ**: observable chắc chắn complete ngay (HttpClient one-shot trong service không giữ tham chiếu component) — vẫn khuyến khích áp dụng cho đồng nhất.
* **Hủy tài nguyên ngoài trong `ngOnDestroy()`**: `setTimeout`/`setInterval`, `Renderer2.listen`, ResizeObserver/IntersectionObserver, instance thư viện ngoài (chart, map, editor...).

## 3. HIỆU NĂNG & CHANGE DETECTION
* **OnPush bắt buộc**: `changeDetection: ChangeDetectionStrategy.OnPush` cho mọi component. State thay đổi qua signal / async pipe / immutable `@Input`.
  - `markForCheck()` là biện pháp CUỐI CÙNG — chỉ dùng cho callback từ thư viện ngoài chạy ngoài zone. KHÔNG rắc `markForCheck()` như thói quen.
* **CẤM gọi function/getter trong template binding**: `{{ calc() }}`, `[disabled]="check()"` chạy lại mỗi CD cycle. Thay bằng: pure pipe, signal `computed()`, hoặc biến tính sẵn khi data đổi.
  - **Ngoại lệ**: signal call (`count()`), hàm `track` của `@for`.
* **Vòng lặp**: dùng `@for (item of items; track item.id)`. [Legacy ≤15] `*ngFor` + `trackBy` bắt buộc.
* **Chạy ngoài zone**: event tần suất cao (scroll, mousemove, drag, polling) → `ngZone.runOutsideAngular()`; chỉ `ngZone.run()` khi cần cập nhật UI.
* **Lazy loading bắt buộc**: route-level lazy load cho mọi feature (`loadChildren`/`loadComponent`). Block render nặng dưới màn hình đầu → `@defer`.
* **List dài (> ~100 item)**: dùng `cdk-virtual-scroll-viewport`, không render thẳng.

## 4. TYPESCRIPT STRICTNESS
* **CẤM `any`**: dùng type tường minh hoặc `unknown` + type guard. Response API phải có interface/type riêng — CẤM dùng object trần.
* **tsconfig**: bật `strict: true` + `strictTemplates: true`. Code mới không được sinh lỗi strict.
* **CẤM non-null assertion `!` tràn lan**: chỉ dùng khi có bằng chứng rõ ràng (đã guard trước đó); ưu tiên optional chaining + default value.
* **DI**: dùng `inject()` thay constructor injection cho code mới. [Legacy ≤15] constructor injection.

## 5. FORMS & CUSTOM CONTROLS (CVA)
* **Strict Typed Forms**: `FormGroup`/`FormControl` phải có type tường minh (`FormControl<string>`, `FormGroup<LoginForm>`). CẤM untyped form cho code mới.
* **ControlValueAccessor**: mọi component dùng chung trong form phải implement đủ 4 method: `writeValue`, `registerOnChange`, `registerOnTouched`, `setDisabledState`.
* **Normalize input trong `writeValue()`**: CVA không được giả định kiểu dữ liệu bên ngoài truyền vào — normalize về internal shape (vd nhận cả `['A','B']` lẫn `'A,B'` thì convert về một dạng duy nhất trước khi xử lý).
* **Validator dùng chung**: tách thành function/class riêng tái sử dụng, không viết inline lặp lại.

## 6. KIẾN TRÚC COMPONENT & STATE
* **Smart / Presentation tách bạch**: Presentation (dumb) chỉ dùng `@Input`/`@Output` (hoặc `input()`/`output()`), không inject service nghiệp vụ.
* **Facade Pattern**: logic xử lý, state, gọi API tách khỏi `.component.ts` sang facade service. Component < 400 dòng.
* **Local state**: ưu tiên signal (`signal`, `computed`); RxJS cho async stream (API, events); `toSignal()`/`toObservable()` ở biên chuyển đổi.
* **CẤM logic trong constructor**: constructor chỉ để DI; init logic đặt ở `ngOnInit` hoặc field initializer.

## 7. BẢO MẬT (XSS + KEYCLOAK)
* **CẤM `bypassSecurityTrust*`** khi chưa có review rõ ràng nguồn dữ liệu — mỗi chỗ dùng phải có comment giải thích vì sao an toàn.
* **Hạn chế `[innerHTML]`**: chỉ cho nội dung đã qua sanitize của Angular; CẤM nối chuỗi HTML thủ công từ input người dùng.
* **CẤM thao tác DOM trực tiếp**: không `document.*`, không đọc/ghi `ElementRef.nativeElement` tùy tiện — dùng `Renderer2` / binding.
* **Guards & Resolvers**: kiểm tra quyền bằng functional guard (`CanActivateFn`); preload data màn hình bằng `ResolveFn` để tránh blank/flashing UI.
* **HTTP Interceptor**: chèn Keycloak access token + xử lý token refresh tập trung tại interceptor. CẤM gắn token thủ công ở từng service; CẤM tự lưu token vào `localStorage`.
* **Phân quyền UI**: ẩn/hiện element theo role qua directive/service dùng chung, không if-else role rải rác trong component.

## 8. ERROR HANDLING
* **Global**: có `ErrorHandler` custom + interceptor xử lý lỗi HTTP tập trung (401 → refresh/logout, 403 → thông báo quyền, 5xx → toast chung).
* **CẤM nuốt lỗi im lặng**: `catchError` phải log hoặc chuyển trạng thái UI (error state), không `catchError(() => EMPTY)` trống.
* **UI phải có 3 trạng thái**: loading / error / empty cho mọi màn hình gọi API — không để user nhìn màn hình trắng.

## 9. ĐA NGÔN NGỮ (i18n)
* **CẤM hardcode text**: 100% text hiển thị đi qua i18n.
* **Key JSON**: `UPPERCASE_SNAKE_CASE`, phân cấp dot notation `MODULE.SCREEN.ELEMENT`.
* **CẤM key động hoàn toàn** (`translate.instant(prefix + variable)`): làm mất khả năng trace key. Nếu cần map theo enum → khai báo map tường minh key literal.
* **Binding**: pipe `translate` trong HTML; trong TS dùng `TranslateService` dạng stream (`get`/`stream`) — `instant` chỉ khi chắc chắn file dịch đã load.
* **Interpolation**: dùng tham số hóa (`"KEY": "Hello {{name}}"`); CẤM cộng chuỗi thủ công trong TS.

## 10. SCSS / CSS
* **Style scoping**: style component đặt trong `:host`. `::ng-deep` (deprecated) chỉ để đè UI thư viện ngoài và PHẢI đi kèm `:host ::ng-deep`; ưu tiên CSS variables xuyên component nếu thư viện hỗ trợ.
* **Nesting tối đa 3 cấp**.
* **CẤM hardcode màu** (HEX/RGB/tên màu): dùng CSS variables của theme (Light/Dark).
* **CẤM animation gây reflow** (`width`/`height`/`margin`/`top`/`left`): dùng `transform` (`translate3d`, `scale`) + `opacity`.
* **CẤM inline style tĩnh** `style="..."` và tiêm HTML style qua TS (`innerHTML`).
  - **Ngoại lệ**: binding giá trị runtime (`[style.width.%]="progress"`, `[style.--var]`) là hợp lệ.
* **CẤM viết CSS trong metadata** `styles: [...]`: tách file `.scss` riêng.
* **Layout**: Grid/Flexbox first; `clamp()`/`calc()` cho fluid layout; CSS variables cho theming.

## 11. ACCESSIBILITY (A11Y)
* **Semantic HTML**: element có hành vi click phải là `<button>`/`<a>`, CẤM `div (click)`.
* **Ảnh/icon có nghĩa** phải có `alt`/`aria-label`; icon trang trí → `aria-hidden="true"`.
* **Keyboard**: component tương tác custom (dropdown, modal, tab) phải điều khiển được bằng bàn phím + quản lý focus (trap focus trong modal, trả focus khi đóng).
* **CẤM bỏ outline focus** mà không có focus style thay thế.

## 12. NAMING & CẤU TRÚC
* **File theo feature**: `feature/` chứa components / services / models của riêng feature; dùng chung → `shared/`; singleton toàn app → `core/`.
* **Đặt tên**: component `PascalCase` + suffix theo loại (`UserListComponent`, `AuthFacade`, `DateFormatPipe`); observable suffix `$`; signal không suffix.
* **Barrel/import**: CẤM feature import chéo feature khác trực tiếp — đi qua `shared`/`core` hoặc public API của feature.
