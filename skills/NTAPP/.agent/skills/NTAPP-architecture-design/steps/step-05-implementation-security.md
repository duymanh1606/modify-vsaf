# STEP 05: IMPLEMENTATION & SECURITY DESIGN

> **Acting as:** [Agent D — Implementation & Security Lead](../agents/agent_d_implementation_sec.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication), R4 (Traceability — Project Tree map sang Container), R5 (Consistency — Folder name khớp Container name).

**Input:** `part_04.1_global_architecture.md` + `part_04.2_modular_deepdive.md` + `part_03_tech_research.md` (nếu có) + `part_02_context_strategy.md`
**Output:** `part_05_implementation_security.md` — (Bao gồm: Project Tree, Ánh xạ tính năng, Giải pháp ATTT & Hiệu năng)

---

## MỤC TIÊU BƯỚC NÀY

Ánh xạ kiến trúc phần mềm xuống cấu trúc code vật lý (Folder Structure) và đặc tả 3 lớp ngoài-vào-trong của HLD: kiến trúc bảo mật (ATTT), giải pháp hiệu năng, và quản trị dữ liệu.

---

## QUY TRÌNH THỰC THI

### 4. CHIẾN LƯỢC TRIỂN KHAI VẬT LÝ

#### 4.1 Cấu trúc thư mục dự án

Căn cứ vào danh sách Containers và Modules từ các tệp `part_04.x`, Agent D phải tạo cấu trúc thư mục vật lý thực tế. Stack ngôn ngữ và framework quyết định cấu trúc cụ thể; ví dụ dưới mang tính tham khảo cho monorepo/multi-module, **agent điều chỉnh theo stack thực tế của dự án**:

```text
{project_root}/
├── apps/                          # Deployable applications (FE + BE)
│   ├── {frontend_app}/            # Framework: {Angular/React/Vue/...}
│   │   └── src/
│   │       ├── core/              # Auth guards, interceptors, global state
│   │       ├── features/          # Feature modules (1 folder per Epic)
│   │       └── shared/            # Reusable UI components
│   └── {backend_app}/             # Framework: {Spring/FastAPI/Express/...}
│       ├── api/                   # API endpoints (REST/gRPC handlers)
│       ├── core/                  # Config, security, gateway proxy
│       ├── services/              # Business logic services
│       └── adapters/              # Connectors tới external systems
├── libs/                          # Shared libraries (không deploy độc lập)
│   ├── adapters/                  # External system adapters
│   │   └── {external_system}/     # 1 folder per external system
│   │       └── ...                # Adapter pattern: API client + data transformer + schema validator (file convention theo stack)
│   ├── domain/                    # Domain logic dùng chung (optional)
│   └── shared/
│       ├── schema/                # Canonical Data Models (mapping 1-1 ERD)
│       └── utils/                 # Shared utilities
└── infrastructure/                # Deploy configs (CI/CD-managed)
    ├── containers/                # Container build files
    ├── orchestration/             # K8s manifests / Helm charts / Compose
    └── scripts/                   # Migration, seed, sync scripts
```

**Quy tắc:**
- Mỗi thư mục PHẢI có comment giải thích vai trò.
- **Data Governance**: Thư mục `schema/` (canonical data models) và schema validator của mỗi adapter phải ánh xạ 1-1 với thực thể trong ERD.
- Dependency direction: `apps/` import được từ `libs/`, ngược lại KHÔNG được phép.
- Mỗi External System trong `libs/adapters/{system}/` phải có đủ adapter pattern (API client + data transformer + schema validator) — phân thành bao nhiêu file là quyết định của stack (Python: 3 file riêng; TypeScript: thường gộp vào 1 module với 3 export).

#### 4.2 Ánh xạ tính năng (Feature-to-Path)

| Feature/Epic | Folder Path | Files chính | Dependency |
| :--- | :--- | :--- | :--- |
| `{Epic 1 - Tên Feature}` | `{apps/backend/api/...}` | `{handler + schema file theo stack}` | `{libs/adapters/{external_system}/}` |
| `{Epic 2 - Tên Feature}` | `{apps/frontend/features/...}` | `{component + service theo stack}` | `{libs/shared/schema/}` |

---

### 5.1 Kiến trúc bảo mật hệ thống - ATTT

#### 5.1.1 Internal Security Boundary (Trong hệ thống)

| Cơ chế | Công cụ/Chuẩn | Mô tả chi tiết |
| :--- | :--- | :--- |
| Authentication | `{Keycloak / Auth0 / JWT}` | `{Token format, Expiry time, Refresh strategy}` |
| Authorization | `{RBAC / ABAC}` | `{Danh sách roles và quyền tương ứng}` |
| API Validation | `{Pydantic / Joi / Zod}` | `{Validate schema trên mọi request trước khi xử lý}` |
| Data Encryption | `{AES-256 / TLS 1.3}` | `{Mã hóa at-rest và in-transit}` |
| PII Masking | `{Custom Middleware}` | `{Trường nào bị mask trong ERD, mask pattern}` |
| Secret Management | `{Hashicorp Vault / AWS Secrets}` | `{Loại secret nào lưu ở đây}` |

#### 5.1.2 External & Network Security (High-Fidelity Zoning)

| Cơ chế | Công cụ/Chuẩn | Mô tả chi tiết |
| :--- | :--- | :--- |
| **Network Zoning**| DMZ / Trust Zone | **DMZ:** Mọi public-facing gateway (Reverse Proxy, API Gateway, LLM Gateway nếu có). **Internal:** App services, DB, message broker. |
| API Gateway | `{Kong / Nginx / Cloud-native}` | `{Rate limiting: X req/min, IP whitelist}` |
| AI/LLM Gateway (nếu có) | `{Custom proxy}` | `PII Masking, Audit log, Token rotation, Fallback model` |
| VPN Tunnel | `{WireGuard / OpenVPN}` | `{Luồng nào bắt buộc đi qua VPN}` |
| Third-party Auth | `{API Key / OAuth2}` | `{Cách cấp phát và rotate Key}` |


#### 5.1.3 Security Guardrails (Vùng cấm - Agent phải check trước khi code)

```
[ ] KHÔNG lưu plaintext credentials trong source code
[ ] KHÔNG log dữ liệu PII (SĐT, CMND, Email) dưới dạng plaintext
[ ] KHÔNG expose internal stack trace ra API response (dùng error codes)
[ ] KHÔNG bỏ qua Token validation ở bất kỳ endpoint nào
[ ] MỌI request cross-service phải có Service Account JWT
[ ] Zero-retention: Session context phải bị flush sau {X} phút idle
```

---

### 5.2 Giải pháp đối với yêu cầu hiệu năng

#### 5.2.1 Caching Strategy

| Cache Layer | Công cụ | Key Pattern | TTL | Chiến lược Invalidation |
| :--- | :--- | :--- | :--- | :--- |
| API Response Cache | `Redis Cluster` | `{entity}:{id}:{version}` | `{X}s` | `{Event-based: khi update → xóa key liên quan}` |
| Schema Cache | `Redis` | `schema:{system}:{type}` | `24h` | `Cron job refresh lúc 00:00 hàng ngày` |
| Session Cache | `Redis` | `session:{user_id}:{token_hash}` | `30m` | `Tự expire sau TTL; Flush khi logout` |

#### 5.2.2 Database Scaling

| Database | Sharding Strategy | Index Fields | Connection Pool |
| :--- | :--- | :--- | :--- |
| `{PostgreSQL}` | `{Shard by tenant_id}` | `{tenant_id, created_at, status}` | `{Max 20 connections/pod}` |
| `{Redis}` | `{Cluster mode 3 master + 3 replica}` | N/A | `{Max 100 connections}` |

#### 5.2.3 Auto-scaling Rules

```
Pod Scale-up trigger:  CPU > 70% trong 2 phút liên tiếp → +{N} pods
Pod Scale-down trigger: CPU < 20% trong 10 phút → -{N} pods
Max pods: {X}
Min pods: {Y}
```

---

### 5.3 Các giải pháp đối với các yêu cầu đặc biệt khác
`[Mô tả các Pattern như Event-Driven Architecture, Microservices, quy trình CI/CD và cơ chế Deployment.]`

### 5.4 Các giải pháp tuân thủ tiêu chuẩn Quản trị dữ liệu

| Tiêu chuẩn | Cơ chế | Công cụ | Chi tiết |
| :--- | :--- | :--- | :--- |
| Secret Management | Vault (centralized) | `Hashicorp Vault` | `Tất cả API Keys, DB credentials, LLM keys` |
| Encryption at Rest | Hash + Salt | `bcrypt / SHA-256 + salt` | `Password, sensitive ID fields` |
| Audit Immutability | Write-once Log | `PostgreSQL WAL / Event Sourcing` | `Bảng audit_trails: chỉ INSERT, không UPDATE/DELETE` |
| Centralized Logging | Log aggregation | `ELK Stack (Elastic, Logstash, Kibana)` | `Tất cả service log gửi về Logstash qua Filebeat` |
| Data Retention | TTL policy | `Cron + Soft Delete` | `PII data xóa sau {X} ngày per regulation` |

---

## Ghi output ra file

Ghi vào một file duy nhất:
- `{intermediate_folder}/part_05_implementation_security.md` — (Bao gồm: Project Tree, Ánh xạ tính năng, Giải pháp ATTT & Hiệu năng)

---

## ĐIỀU KIỆN TIẾP TỤC (Exit Criteria)

- [ ] Cây thư mục Project Tree đã được đặc tả đầy đủ với comment cho mỗi thư mục.
- [ ] Feature-to-Path Mapping Table có ít nhất 1 dòng per Epic trong PRD.
- [ ] 100% Shared Schemas trong Project Tree khớp với danh mục thực thể ERD (Step 4.1).
- [ ] Bảng ATTT Internal và External đều có đủ hàng.
- [ ] Security Guardrails checklist đã được điền với giá trị cụ thể (thay `{X}` bằng con số thực).
- [ ] Bảng Caching Strategy có đủ các Layer (API, Schema, Session).
- [ ] Không có `{placeholder}` còn sót trong output.

---

## ⛔ [GATE — Exit Criteria] (đặt TRƯỚC Next)

Chỉ sang Step 06 khi toàn bộ Exit Criteria trên PASS (Project Tree đủ comment, Feature-to-Path ≥ 1 dòng/Epic, schema khớp ERD, bảng ATTT/Caching đủ hàng, không còn `{placeholder}`).

**Next:** Read fully and follow `./step-06-module0.md`
