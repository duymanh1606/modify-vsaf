# Per-Repo Overview Template

> Skill `ntapp-system-overview` dùng template này cho mỗi code repo trong scope. Mode `baseline` inject Section 0 (Service Identity) trước Section 1; mode `overview` skip Section 0.

---

## Header (frontmatter + warning)

```markdown
---
generated_by_skill: ntapp-system-overview
mode: {overview|baseline}
repo: {repo_name}
source_repo_path: {repo_abs_path}
date: {YYYY-MM-DD}
status: best-effort-{overview|baseline}
---

# {Service Display Name} — Tài liệu mô tả

> **Phiên bản:** 1.0 — **Ngày tạo:** {YYYY-MM-DD} — **Repo:** {repo_name}
> {project_label_line_or_omit}
>
> **⚠️ Best-effort document.** Tier 1 (body) cho phép Assumption. Tier 2 (bảng API/Integration/Data) yêu cầu evidence file:line. SA verify trước khi dùng quyết định kiến trúc.
```

(Nếu `project_label` rỗng → bỏ dòng đó hoàn toàn. Không in placeholder.)

---

## Mục lục

1. [Executive Summary](#1-executive-summary)
{IF mode=baseline}0. [Service Identity & Auth Profile](#0-service-identity--auth-profile){/IF}
2. [Architecture Overview](#2-architecture-overview)
3. [Business Features](#3-business-features)
4. [API Analysis](#4-api-analysis)
5. [Database Analysis](#5-database-analysis)
6. [Integration Analysis](#6-integration-analysis)
7. [Main Processing Flows](#7-main-processing-flows)
8. [Technical Assessment](#8-technical-assessment)
9. [Risks & Recommendations](#9-risks--recommendations)
10. [Full Feature List](#10-full-feature-list)
{IF mode=baseline}E. [Open Questions for SA](#e-open-questions-for-sa){/IF}

---

## 0. Service Identity & Auth Profile (mode baseline only)

> Mục tiêu: snapshot "danh tính" của sub-system này như 1 service trên mạng — base URL, IDL artifact, auth scheme. Là **join key cho Cross-System Contract Match Matrix**. **Tier 2 evidence required — không Assumption.**

### 0.1 Self-Exposed Endpoints (provider role)

| Field | Value | File evidence |
|---|---|---|
| Base URL(s) | `{url hoặc "(không expose)"}` | `{file:line}` hoặc TODO |
| Listen port(s) | `{8080 / 3000 / N/A}` | `{config file:line}` |

### 0.2 External Service Endpoints Consumed (consumer role)

| Target name (best-guess) | Base URL | Environment | File evidence |
|---|---|---|---|
| `{e.g. "user-service" hoặc <TODO: SA verify — Target của env \`{ENV_NAME}\` (value=\`{URL_VALUE}\`)?>}` | `{url}` | `{dev/staging/prod/all}` | `{.env file:line hoặc client init}` |

Heuristic: subdomain hoặc tên env var (`USER_SERVICE_URL` → `user-service`). Không suy được → TODO.

### 0.3 IDL Artifacts

| Direction | Artifact path | Format | Notes |
|---|---|---|---|
| **Provided** (repo này define) | `{api/openapi.yaml / *.proto / *.graphql / asyncapi.yaml / pacts/*.json / *.tsp / *.smithy}` | `OpenAPI / gRPC / GraphQL / AsyncAPI / Pact / TypeSpec / Smithy / none` | `{version, generator}` |
| **Consumed** (repo này generate client từ IDL ngoài) | `{src/__generated__/api.ts → source IDL nếu trace được}` | `{format}` | `{source repo hoặc TODO}` |

Detection signal cho generated client: header `// Code generated`, folder `__generated__/`, suffix `*_pb.{ts,go,py}` / `*_grpc.{ts,go,py}`.

### 0.4 Auth Profile

| Scheme | Token storage / mechanism | Library / SDK | File evidence |
|---|---|---|---|
| `bearer / cookie-httpOnly / API-key / OAuth2 / mTLS / SAML / none / mixed` | `{LocalStorage / Cookie / Env / Vault / Keychain / in-memory}` | `{auth0-spa-js / next-auth / oidc-client-ts / passport / custom}` | `{file:line set Authorization header / đọc cookie}` |

KHÔNG đoán auth scheme từ tên framework hay package.json dependency. Không có signal → TODO.

---

## 1. Executive Summary

Tier 1 prose. Cover:
- Mục đích chính + bài toán nghiệp vụ.
- Vai trò trong hệ thống tổng thể (suy từ README, naming, integration với service khác — `**Assumption:**` nếu không chắc).
- Actors / clients chính.
- Dependency chính (DB, MQ, downstream service).

---

## 2. Architecture Overview

Tier 1 prose. Cover:
- Kiến trúc tổng thể (hexagonal / layered / clean / monolith / microservice / ...).
- Layer / module / package chính.
- Design pattern đang dùng.
- Tech stack với version cụ thể từ build manifest.
- Tree thư mục 2-3 cấp.
- Config / env management.
- Logging / monitoring / tracing.
- AuthN / AuthZ (mode overview — high-level; mode baseline đã cover Section 0.4 chi tiết).

---

## 3. Business Features

Tier 1 prose per feature. Template per feature:

### {Tên feature}
- **Mục đích:** ...
- **Flow xử lý:** (3-5 bullet)
- **API/service liên quan:** ...
- **Input/Output chính:** ...
- **DB table sử dụng:** ...
- **Rule nghiệp vụ + validation:** ...
- **Exception handling:** ...
- **External integration:** ...
- **Scheduler / async / cache / MQ:** (chỉ ghi cái nào có)

Suy luận business từ naming + SQL + workflow → cho phép. `**Assumption:**` nếu không chắc.

---

## 4. API Analysis (Tier 2 — evidence required)

### 4.1 Public API

| Method | Endpoint | Chức năng | Request DTO | Response DTO | Auth | File evidence | Source (IDL/AST) |
|---|---|---|---|---|---|---|---|

### 4.2 Internal API

| Method | Endpoint | Chức năng | Service gọi tới | File evidence |
|---|---|---|---|---|

### 4.3 External API integration (outbound)

| Hệ thống | Endpoint | Mục đích | Direction | File evidence |
|---|---|---|---|---|

**Tier 1 ưu tiên** (mode baseline): nếu Section 0.3 có IDL Provided → mỗi method = 1 row IDL-derived (Source = `IDL: {path}`). Tier 2 AST grep chỉ làm phần IDL không cover.

Nếu repo không expose API loại nào → ghi `(không phát hiện)` ở row, KHÔNG xóa table header.

---

## 5. Database Analysis (Tier 2)

### 5.1 Tables

| Table | Chức năng | Module sử dụng | File evidence (schema) |
|---|---|---|---|

### 5.2 Quan hệ + Entity

Tier 1 prose hoặc ERD ngắn:
- Quan hệ dữ liệu chính.
- Entity / model quan trọng.
- Transaction handling.
- Locking / retry / optimistic concurrency.
- Migration tooling (Flyway / Liquibase / Alembic / Knex / Prisma / Drizzle).

### 5.3 Shared Schema Candidates (mode baseline only — skip ở mode overview)

> Entity có khả năng dùng chung với sub-system khác (export qua API DTO / event payload / DB shared / file share). Đây là **candidate** từ góc nhìn 1 repo — Synthesizer ở `_overview.md` Section D sẽ cross-confirm khi có entity name xuất hiện ở ≥2 per-repo file.
>
> **Tier 2** — evidence required. Chỉ scan từ source code; không suy ra "chắc chắn dùng chung" — đó là việc của Synthesizer.

| Entity | Mechanism | Evidence (export point) | Candidate target sub-system |
|---|---|---|---|
| `{EntityName}` | `API DTO / event payload / DB shared / file share` | `{file:line nơi entity được export}` | `{best-guess từ context hoặc <TODO: SA verify — entity X có dùng chung với ai?>}` |

**Heuristic detect:**
- Entity là return type của endpoint ở Section 4.1 → `API DTO`.
- Entity là payload schema của event ở Section 4.3 (B.3) / 6.1 → `event payload`.
- Connection string Section 6.1 trỏ DB của sub-system khác (DB name khác DB chính của repo này) → `DB shared`.
- Path Section 6.1 trỏ shared storage (NFS / S3 bucket dùng chung) → `file share`.

Không phát hiện candidate → ghi `(không phát hiện shared schema candidate)`. KHÔNG xóa section.

---

## 6. Integration Analysis (Tier 2 cho table, Tier 1 cho narrative)

### 6.1 Outbound (sub-system này gọi → bên ngoài)

| Target | Giao thức | Endpoint / topic | DTO | File evidence | Confidence | Source tier |
|---|---|---|---|---|---|---|

Source tier values: `IDL` (highest) → `client-layer` → `AST` → `config`. Confidence `HIGH/MEDIUM/LOW`.

Discovery cascade:
1. **Tier 1 IDL Consumed** — cross-ref Section 0.3 mục Consumed (mode baseline).
2. **Tier 2 API client centralization** — `src/api/`, `src/services/`, `axios.create({baseURL})`, query hooks (`useQuery({queryKey, queryFn})`), RTK Query `createApi`.
3. **Tier 3 AST grep** — `axios.get`, `requests.get`, `fetch(`, `WebClient`, `RestTemplate`, gRPC stub method, MQ producer.
4. **Tier 4 Base URL join** — cross-ref Section 0.2 để map host → target name.

### 6.2 Inbound (sub-system này bị gọi ← bên ngoài)

| Caller | Giao thức | Endpoint exposed | Evidence | Confidence |
|---|---|---|---|---|

Evidence ưu tiên: CORS whitelist → k8s Ingress → allowed-callers config → doc. Không có → TODO.

### 6.3 Narrative

Tier 1 prose:
- MQ / Kafka / RabbitMQ / SQS / NATS — topic, schema, retry, DLQ, idempotency.
- File / SFTP / batch transfer.
- Cache (Redis / Memcached / Caffeine / in-memory).
- Secret management (Vault / config server / env / cloud KMS).

---

## 7. Main Processing Flows (Tier 1)

End-to-end flow mô tả + Mermaid sequence/flowchart cho 2-3 flow quan trọng. Cover:
- Async flow / retry / DLQ.
- Batch / scheduler flow.
- Error flow.

`**Assumption:**` cho phép khi suy intent từ workflow code.

---

## 8. Technical Assessment (Tier 1)

- Điểm mạnh kiến trúc.
- Technical debt.
- Bottleneck tiềm năng.
- Khả năng scale (horizontal / vertical).
- Khả năng maintain (test coverage hint, code organization).
- Observability.
- Security concern.
- Coding convention.

---

## 9. Risks & Recommendations (Tier 1)

- **Risk:** 1 dòng / risk + severity `High/Med/Low`.
- **Recommendation:** cụ thể, actionable. KHÔNG sinh full plan (R-No-PRD/HLD).

---

## 10. Full Feature List (Tier 2 cho cột API)

| # | Feature | Mô tả | Module | API liên quan | File evidence (entry point) |
|---|---|---|---|---|---|

---

## E. Open Questions for SA (mode baseline only — chỉ HIGH-impact)

> **Section này LÀ audit log của Q&A loop**, KHÔNG phải checklist toàn bộ TODO. Chỉ aggregate HIGH-impact questions đã được Q&A loop xử lý.

**HIGH-impact scope** (4 loại cùng Q&A filter ở Step 2.2):
- Section 0.2 — External URL target unknown.
- Section 0.3 — IDL Consumed source unknown.
- Section 0.4 — Auth scheme unknown.
- Section 6.1 — Outbound target unknown (Tier 4 fail).

**Chỉ 2 status:**
- `Answered by SA on {date}` — user trả lời ở Q&A loop, cell gốc đã patch.
- `Asked, deferred (user skip)` — user chọn skip ở Q&A loop, TODO giữ inline ở cell.

**Format mỗi item:**

```markdown
- [x] (Section 0.2) Target sub-system của `USER_SVC_URL=https://users.internal`?
      → Answered by SA on 2026-05-27: `svc-a` (propagated across 3 repos)

- [ ] (Section 0.4) `next-auth` callback endpoint của svc-a?
      → Asked, deferred (user skip) — TODO giữ inline ở cell gốc.
```

**Notes:**
- Mode `overview` KHÔNG có Section E.
- MEDIUM/LOW TODO và HIGH-impact dropped-by-cap → chỉ inline tại cell, KHÔNG aggregate vào Section E. Section E phản ánh đúng những gì Q&A loop touched.
- Section E rỗng = `--skip-qa` / scope clean / IDL đầy đủ.
