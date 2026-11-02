# Phase BE — Spring Boot + vds-keycloak-adapter

Mục tiêu: thêm login/phân quyền Keycloak vào BE Spring Boot, giữ được chế độ login cũ (VSA/oauth) qua cờ `auth.provider`, không vỡ bean/classpath.

## 1. Dependency (pom.xml)

Adapter khai `vds-spring-starter` + `spring-boot-starter-security` ở scope **provided** → KHÔNG kéo transitive → app phải tự khai. Thiếu sẽ lỗi `BaseController.class cannot be opened because it does not exist`.

```xml
<!-- vds keycloak adapter -->
<dependency>
    <groupId>vn.com.viettel.vds</groupId>
    <artifactId>vds-keycloak-adapter</artifactId>
    <version>1.0.1-WEB</version>
</dependency>
<!-- provided trong adapter -> app tu khai; chua BaseController/ResponseFactory/GeneralResponse -->
<dependency>
    <groupId>vn.com.viettel.vds</groupId>
    <artifactId>vds-spring-starter</artifactId>
    <version>1.1.3.RELEASE</version>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
<dependency>
    <groupId>commons-collections</groupId>
    <artifactId>commons-collections</artifactId>
    <version>3.2.1</version>
</dependency>
```

**Pin version lib nền**: nếu lib nền cũ (vd `vds-vsa-lib`) đang để version range `[1.0,)` → đổi sang version cố định (bản đang resolve, xem `dependency:tree`). Range gây build không tái lập.

## 2. Xung đột JAX-RS (LỖI HAY GẶP NHẤT khi login)

Triệu chứng: login 500 `NoSuchMethodError: javax.ws.rs.core.UriBuilder.resolveTemplate(String,Object,boolean)`.
Nguyên nhân: classpath có JAX-RS **1.1** cũ (`javax.ws.rs:jsr311-api`, thường qua `spring-cloud-starter-netflix-*` → `ribbon-httpclient` → `com.sun.jersey:jersey-client`) che mất JAX-RS **2.1** (`org.jboss.spec.javax.ws.rs:jboss-jaxrs-api_2.1_spec`, do `keycloak-admin-client` → `resteasy-client` kéo vào).

Dò thủ phạm:
```
mvn -o dependency:tree | grep -iE "ws.rs|jsr311|jersey|resteasy|keycloak"
```
Fix: loại `jsr311-api` khỏi dependency top-level kéo nó vào (thường là zuul/eureka/ribbon starter):
```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-zuul</artifactId>
    <version>...</version>
    <exclusions>
        <exclusion>
            <groupId>javax.ws.rs</groupId>
            <artifactId>jsr311-api</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```
JAX-RS 2.1 là superset → jersey 1.x vẫn chạy. Verify: `dependency:tree` chỉ còn `jboss-jaxrs-api_2.1_spec` cung cấp `javax.ws.rs`. **Phải rebuild + restart** (classpath cũ vẫn còn jsr311).

## 3. Xung đột bean name (khi có ≥2 lib cùng namespace `vn.com.viettel.vds`)

Triệu chứng: `ConflictingBeanDefinitionException` (vd bean `responseFactory` trùng giữa lib nền và `vds-spring-starter`). Xảy ra vì `@ComponentScan("vn.com.viettel.vds")` quét cả 2 lib, nhiều class trùng **tên bean mặc định**.

`spring.main.allow-bean-definition-overriding=true` KHÔNG cứu (lỗi ném ở scanner, trước override).

**Fix ưu tiên — SafeBeanNameGenerator** (đặt bean name = FQN cho mọi bean `vn.com.viettel.vds.*`, gỡ mọi va chạm tên trong 1 lần; an toàn khi mọi injection theo TYPE và không có `@Qualifier("tênNgắn")`/`getBean("tênNgắn")`/`@Resource(name)` — kiểm tra trước bằng grep):
```java
public static class SafeBeanNameGenerator extends AnnotationBeanNameGenerator {
    @Override
    public String buildDefaultBeanName(BeanDefinition definition) {
        String className = definition.getBeanClassName();
        if (className != null && className.startsWith("vn.com.viettel.vds.")) {
            return className; // FQN -> khong con trung ten
        }
        return super.buildDefaultBeanName(definition);
    }
}
public static void main(String[] args) {
    SpringApplication application = new SpringApplication(App.class);
    application.setBeanNameGenerator(new SafeBeanNameGenerator());
    application.run(args);
}
```
Kiểm tra an toàn trước khi dùng: `grep -rE "@Qualifier|@Resource\(|getBean\(\"" src/main/java` — nếu chỉ trỏ tới `@Bean` method nội bộ thì OK (generator chỉ đổi tên bean quét từ class, không đổi tên `@Bean` method). spring.xml chỉ ref bean khai bằng XML → không ảnh hưởng.

## 4. Switch chain vsa ↔ keycloak (giữ 2 chế độ login)

Lib nền kiểu VSA thường có 3 config bảo mật (`SecurityConfig @EnableWebSecurity`, `ResourceServerConfig @EnableResourceServer` order thấp match MỌI request và 401 Bearer keycloak, `AuthorizationServerConfig @EnableAuthorizationServer`). Ở chế độ keycloak phải **TẮT** chúng, nếu không chain VSA chặn token keycloak.

Cách: `@ComponentScan(excludeFilters=@Filter(ASSIGNABLE_TYPE, classes={SecurityConfig, ResourceServerConfig, AuthorizationServerConfig}))` rồi đăng ký lại qua 3 subclass `@ConditionalOnProperty(name="auth.provider", havingValue="vsa", matchIfMissing=true)`:
```java
@Configuration @EnableWebSecurity @EnableGlobalMethodSecurity(prePostEnabled=true) @Order(2147483642)
@ConditionalOnProperty(name="auth.provider", havingValue="vsa", matchIfMissing=true)
public class VsaSecurityConfig extends SecurityConfig {}
// tuong tu VsaResourceServerConfig extends ResourceServerConfig (@EnableResourceServer)
// va VsaAuthorizationServerConfig extends AuthorizationServerConfig (@EnableAuthorizationServer)
```
Annotation phải khai lại (không kế thừa). `matchIfMissing=true` → thiếu cờ mặc định = vsa (giữ hành vi cũ).

**UserController của lib nền** (endpoint revoke/token) inject `TokenStore` — chỉ tồn tại ở chế độ vsa → cũng exclude khỏi scan + đăng ký lại `@Bean` trong config `@ConditionalOnProperty(vsa)`:
```java
@Configuration @ConditionalOnProperty(name="auth.provider", havingValue="vsa", matchIfMissing=true)
public class VsaLegacyEndpointConfig {
    @Bean public UserController userController() { return new UserController(); }
}
```
(@Bean vẫn được field-inject và @RestController vẫn được quét request-mapping. Nếu đã dùng SafeBeanNameGenerator thì KHÔNG cần exclude ResponseFactory nữa — tên đã tách theo FQN.)

Trước khi exclude/loại bean nào, quét lib để biết class nào là bean (`@Component/@Service/@Configuration/@RestController`) và class nào inject `TokenStore`/OAuth2 — chỉ loại đúng cái coupling OAuth2. Xem cách quét jar trong `troubleshooting.md`.

## 5. application.properties

```properties
server.port=8080
# switch: keycloak = tat chain VSA, dung adapter; vsa = giu cu (mac dinh)
auth.provider=keycloak
# --- vds-keycloak-adapter ---
app.keycloak.realm=<realm>
app.keycloak.auth-server-url=<https://.../keycloak>
app.keycloak.resource=<client-id>
app.keycloak.secret=${APP_KEYCLOAK_SECRET}      # externalize, dung hardcode
app.keycloak.use-resource-role-mappings=true    # doc role tu resource_access.<client>.roles
app.keycloak.bearer-only=true
app.keycloak.base-path=${baseUrl}/api/${version}/private   # login = ${base-path}/auth
app.keycloak.auth.security.enabled=true          # bat chain keycloak
#app.keycloak.enable-authorization=true          # bat khi muon keycloak enforce URL theo resource/permission
```
Endpoint login mà FE gọi = `${app.keycloak.base-path}/auth` (adapter tự expose AuthController + PermissionController `/users/permissions`). Adapter `KeycloakWebAutoConfiguration` chỉ `@ComponentScan("vn.com.viettel.vds.keycloak.controller")` nên KHÔNG tự gây trùng bean.

## 6. Chuỗi identity nội bộ (nếu BE proxy sang service downstream)

`JwtService`/`UserUtils` phải instanceof-safe cho CẢ 2 principal: `UserInfoBean` (VSA) và `KeycloakPrincipal` (keycloak). Với keycloak, đọc role từ `token.getResourceAccess(clientId).getRoles()` (tên client role), username từ `token.getPreferredUsername()`, email `token.getEmail()`. Service downstream map role theo TÊN (không phải roleId số). Xem snippet trong `troubleshooting.md` mục JwtService.

## 7. Verify
`mvn -DskipTests clean compile` → BUILD SUCCESS. Nếu chạy được app: start ở chế độ keycloak, `POST ${base-path}/auth {username,password}` phải trả token; đổi `auth.provider=vsa` phải giữ login cũ.
