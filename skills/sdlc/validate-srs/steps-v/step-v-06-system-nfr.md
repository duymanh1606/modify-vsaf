---
# model: sonnet
# findingsOutput: '{output_folder}/_validation_temp/findings-system-nfr.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
---

# Step V-06: System & NFR — Validate kiến trúc và yêu cầu phi chức năng

Weight: **1.0**

---

## 0. Load Context
Read `{contextFile}` → get `srs_path`, `kg.prd_key_sections`, `kg.brd_key_sections`. Use KG line ranges for all upstream document reads — do NOT read full PRD/BRD.

## 1. Performance check

Kiểm tra mỗi SRS file:

- Có **latency target** cho key operations? (VD: API response < 200ms, page load < 3s)
- Có **TPS / throughput** targets? (VD: 1000 requests/second)
- Có **SLA** định nghĩa? (VD: 99.9% uptime)
- Có **load expectations** cụ thể? (VD: concurrent users, peak traffic)

**Scoring:**
- Đủ cả 4: latency + TPS + SLA + load → 1.0
- Có 2-3 mục → 0.75
- Chỉ có 1 mục chung chung → 0.5
- Không có → 0.0

Item ID: `nfr_performance`

---

## 2. Reliability & Resilience check

Kiểm tra:

- **Retry policy** cho external calls? (số lần retry, backoff strategy)
- **Idempotency** cho payment / order operations?
- **Fallback strategy** khi service xuống?
- **Circuit breaker** pattern?
- **Data consistency** khi failure (rollback, compensating transaction)?

**Scoring:**
- Retry + idempotency + fallback đầy đủ → 1.0
- Có retry + idempotency nhưng thiếu fallback → 0.75
- Chỉ mention "cần xử lý lỗi" chung chung → 0.5
- Không có → 0.0

Item ID: `nfr_reliability`

---

## 3. Security & Compliance check

Kiểm tra:

- **Authentication** required cho sensitive operations?
- **Authorization (RBAC)** cho từng role?
- **PII protection**: Dữ liệu cá nhân được xử lý như thế nào?
- **Compliance requirements**: PDPA, PCI-DSS, ISO, Nghị định liên quan?
- **Data encryption**: in-transit và at-rest?
- **Audit logging** cho financial operations?

**Scoring:**
- Auth + RBAC + PII + compliance đầy đủ → 1.0
- Auth + RBAC + PII có nhưng thiếu compliance detail → 0.75
- Chỉ có auth requirement → 0.5
- Không đề cập → 0.0

Item ID: `nfr_security`

---

## 4. Observability check

Kiểm tra:

- **Logging requirements**: log level, log format, log retention?
- **Metrics**: key metrics cần track? (VD: order success rate, payment latency)
- **Alerts / thresholds**: điều kiện trigger alert?
- **Tracing**: distributed tracing / correlation ID?
- **Health check / readiness probe** requirements?

**Scoring:**
- Logging + metrics + alerts đầy đủ → 1.0
- Có logging + metrics nhưng thiếu alerts → 0.75
- Chỉ mention "cần log" chung chung → 0.5
- Không có → 0.0

Item ID: `nfr_observability`

---

## 5. Scalability check

Kiểm tra:

- **Horizontal scaling**: có thể scale out không?
- **Stateless design** cho API services?
- **Caching strategy**: Redis, CDN, in-memory?
- **Database**: read replica, sharding, partition strategy?
- **Queue / async processing** cho heavy operations?

**Scoring:**
- Scalability approach rõ ràng với strategy cụ thể → 1.0
- Có đề cập caching + async nhưng không chi tiết → 0.75
- Chỉ mention "cần scalable" chung chung → 0.5
- Không đề cập → 0.0

Item ID: `nfr_scalability`

---

## 6. Architecture Alignment check

Kiểm tra SRS có consistent với architecture decisions:

- Technology stack (DB, messaging, framework) có nhất quán với System SRS?
- Integration patterns (sync vs async, REST vs event) rõ ràng?
- Service boundaries rõ ràng? (không có SRS function vượt ranh giới service)

Item ID: `architecture_alignment`

---

## 7. Architecture NFR Alignment (via KG)

**Token-efficient:** Read architecture entity → find NFR/ADR sections → targeted read.

1. From KG: read architecture entity `key_sections` → find NFR-related sections
2. Targeted read of architecture NFR targets
3. Compare:
   - SRS performance targets (latency, TPS) align with architecture capacity planning?
   - SRS security requirements consistent with architecture security decisions?
   - SRS data storage decisions match architecture DB choices (from service entity)?

Item ID: `architecture_nfr_alignment`
Scoring: 1.0 (consistent) / 0.75 (minor gaps) / 0.5 (significant deviation) / 0.0 (contradicts)

---

## 9. Ghi findings

```markdown
| # | Severity | Dimension | File | Item ID | Score | Evidence | Suggestion | Business Impact | Source |
```

Each finding MUST include `business_impact` with three sub-fields:
- **WHO**: Primary stakeholder affected (Dev, QA, PO, Ops, Customer)
- **WHAT**: Impact type (Blocked, Rework risk, UX degradation, Compliance risk)
- **WHEN**: When impact materializes (Before Sprint, During Sprint, After Release)
```

---

## 10. Tính System & NFR dimension score

```
system_nfr_score = round(sum(item_scores.values()) / 7 × 100, 1)
```

Canonical item IDs (N = 7, fixed):
`nfr_performance`, `nfr_reliability`, `nfr_security`, `nfr_observability`, `nfr_scalability`, `architecture_alignment`, `architecture_nfr_alignment`

⚠️ MANDATORY: N = 7 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

Weight: **1.0**

---

## 11. Append findings vào report

Append CRITICAL/HIGH → section "4. Critical & High Findings".
Append MEDIUM/LOW → section "5. Medium & Low Findings".

Update frontmatter: thêm `step-v-06-system-nfr` vào `stepsCompleted`.

---

## [NEW] Write Structured Findings
Write `{findingsOutput}`:
```yaml
dimension: system_nfr
weight: 1.0
dimension_score: 0   # = round(sum(item_scores.values()) / 7 × 100, 1)
status: OK
findings: []
summary: {total: 0, critical: 0, high: 0, medium: 0, low: 0}
item_scores:
  nfr_performance: 0.0
  nfr_reliability: 0.0
  nfr_security: 0.0
  nfr_observability: 0.0
  nfr_scalability: 0.0
  architecture_alignment: 0.0
  architecture_nfr_alignment: 0.0
```

## 12. Menu

```
System & NFR Score: {X}% ({status}) [weight 1.0]
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

[C] Continue — Sang Delivery Readiness (Step V-07)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-07-delivery-readiness.md`
