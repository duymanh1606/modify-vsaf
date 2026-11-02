# Mode `baseline` — DEFAULT · Audit-grade + Cross-System Contract Matrix

> **Trigger:** STEP 2 của [../workflow.md](../workflow.md) khi `--mode baseline` — **đây là mode mặc định**, chạy khi user không nêu `--mode`.
>
> **Input:** `scope_list` + `out_of_scope_list` từ STEP 1 (đã PASS multi-root gate), `planning_artifacts` đã resolve.
>
> **Output:**
> - Per-sub-system: `{planning_artifacts}/{sub_system}.md` (10 sections **+ Section 0 + Section E**)
> - Cross-system: `{planning_artifacts}/_overview.md` (Contract Match Matrix, Integration Diagram, Detected vs Scope)
> - Archive snapshot: `{planning_artifacts}/archive/_v{N}_{date}/` (cả 2 file trên)
>
> **Evidence policy:** Tier 1 + Tier 2 + Tier 3 (Contract Matrix strict) — xem [../principles.md](../principles.md).

---

## Flow tổng quan

```
STEP 2.1  Parallel scan (Agent A × N)
          → {planning_artifacts}/_parts/{sub_system}.md (intermediate)
                                ↓
STEP 2.2  High-impact Q filter + Interactive Q&A loop (default,
          skip nếu --skip-qa)
          → patch _parts/ files với câu trả lời SA
                                ↓
STEP 2.3  Cross-system synthesis (Agent B)
          → _parts/_overview.md
                                ↓
STEP 2.4  SA review gate (3-choice: approve/refine/cancel)
                                ↓
STEP 2.5  Dual-write finalize: _parts/ → canonical + archive snapshot
```

---

## STEP 2.1 — Parallel scan (Agent A × N)

Spawn N sub-agent `general-purpose` trong 1 message (parallel). Batch ≤5 nếu N>5, chạy group sequential.

Mỗi instance scan 1 sub-system. **Prompt template** (fill `{sub_system_name}`, `{repo_abs_path}`, `{intermediate_file_abs_path}`, `{stack_hint}`, `{project_label_or_empty}`):

```
Bạn là Software Architect / Senior Technical Analyst, đang sản xuất system baseline
cho input của Stage 2 HLD.

NHIỆM VỤ
Scan repo tại: {repo_abs_path}
Ghi file vào: {intermediate_file_abs_path}

Theo template:
  .agent/skills/NTAPP-system-overview/templates/per_repo.md
Mode = baseline → BAO GỒM Section 0 (Service Identity & Auth Profile) + Section E
(Open Questions for SA).

QUY TẮC
- KHÔNG đọc file ngoài {repo_abs_path}.
- KHÔNG đụng git.
- KHÔNG viết file nào khác ngoài {intermediate_file_abs_path}.
- Báo cáo cuối ≤200 từ: count Section 0/A-F + path file đã ghi.

EVIDENCE POLICY (strict mode baseline)
- Tier 1 prose (Exec Summary, Architecture narrative, Business Features description,
  Flows, Assessment, Risks): Assumption cho phép với prefix "**Assumption:** ...".
- Tier 2 bảng (Section 0 + Section 4 API + Section 5 DB tables + Section 6 Integration
  + Section 10 Full Feature List): MỖI ROW phải có cột "File evidence" (file:line).
  Thiếu → <TODO: SA verify — câu hỏi cụ thể>.
- Section 0 (Service Identity) là **join key** cho Cross-System Contract Matrix
  ở STEP 2.3. PHẢI scan KỸ:
    0.1 Self-Exposed Endpoints: grep app.listen / server.listen / uvicorn.run /
        http.ListenAndServe / Spring server.port / K8s Service / Docker EXPOSE.
    0.2 External Consumed URLs: grep .env files, vite/next/webpack proxy,
        runtime config (src/config, application.yaml services.*.url),
        client init inline (axios.create({baseURL}), httpx.Client(base_url)).
    0.3 IDL Artifacts:
        Provided: glob **/openapi.{yaml,yml,json}, **/swagger.*, **/*.proto,
                  **/buf.{yaml,yml}, **/*.graphql, **/schema.gql, **/asyncapi.*,
                  **/pacts/*.json, **/*.tsp, **/*.smithy, **/schemas/*.json.
                  Exclude node_modules/, vendor/, __generated__/, .git/.
        Consumed: detect generated client (header "// Code generated",
                  folder __generated__/, *_pb.{ts,go,py}, *_grpc.{ts,go,py},
                  generator config orval.config.*, codegen.*, openapi-generator-config.*,
                  buf.gen.yaml). Trace source IDL từ generator config nếu có.
    0.4 Auth Profile: lib import (auth0-spa-js, next-auth, oidc-client-ts, passport,
        jsonwebtoken, jose, pyjwt, python3-saml, mTLS cert config).
        Token pattern: Authorization: Bearer, X-API-Key header, cookie HttpOnly.
        Storage (FE/mobile): localStorage, SecureStore, Keychain, in-memory store.
        Không có signal → TODO. KHÔNG đoán từ tên framework.

- Section 6.1 Outbound — 4-tier discovery cascade (chi tiết ở per_repo.md Section 6.1):
    Tier 1 IDL Consumed → Tier 2 API client centralization →
    Tier 3 AST grep → Tier 4 Base URL join (cross-ref Section 0.2).
  Cột "Source tier" + "Confidence" PHẢI fill cho mỗi row.

- Section 6.2 Inbound — thường khó trích từ source. Evidence ưu tiên:
    CORS whitelist → k8s Ingress → allowed-callers config → doc.
  Không có → TODO. KHÔNG bịa caller.

- Section 5.3 Shared Schema Candidates — chỉ mode baseline. Heuristic: entity
  export ra API DTO / event payload / DB shared connection / file share. Phát hiện
  → dòng candidate + best-guess target (hoặc TODO). Synthesizer ở STEP 2.3
  cross-confirm khi entity name xuất hiện ≥2 per-repo file.

- Section E (Open Questions for SA): xem template `per_repo.md` Section E —
  chỉ HIGH-impact (0.2 / 0.3 / 0.4 / 6.1), là audit log của Q&A loop.
  Format khởi tạo: "- [ ] (Section X.Y) {câu hỏi nguyên văn}".

TODO MARKER WORDING TEMPLATE (BẮT BUỘC — để orchestrator dedup exact-match ở STEP 2.2)
Mọi HIGH-impact TODO marker phải dùng đúng 1 trong 4 template wording sau, KHÔNG paraphrase.
Cross-repo dedup ở STEP 2.2 dựa vào exact string match — wording lệch nhỏ = mất cơ hội merge.

  Template H1 — External URL target unknown (Section 0.2):
    <TODO: SA verify — Target của env `{ENV_NAME}` (value=`{URL_VALUE}`)?>
    vd: <TODO: SA verify — Target của env `USER_SVC_URL` (value=`https://users.internal:8080`)?>

  Template H2 — IDL Consumed source unknown (Section 0.3):
    <TODO: SA verify — IDL source của generated file `{FILE_PATH}`?>
    vd: <TODO: SA verify — IDL source của generated file `src/__generated__/user-api.ts`?>

  Template H3 — Auth scheme unknown (Section 0.4):
    <TODO: SA verify — Auth scheme cho lib `{LIB_NAME}` ở `{FILE_PATH}`?>
    vd: <TODO: SA verify — Auth scheme cho lib `next-auth` ở `src/auth.ts`?>

  Template H4 — Outbound target unknown / runtime URL (Section 6.1):
    <TODO: SA verify — Target của runtime URL pattern `{PATTERN}` ở `{FILE_PATH}`?>
    vd: <TODO: SA verify — Target của runtime URL pattern `${PAYMENT_HOST}/charge` ở `src/clients/payment.ts:42`?>

QUY TẮC FILL PLACEHOLDER:
- `{ENV_NAME}` — uppercase, không quote thêm: `USER_SVC_URL` (không phải `'USER_SVC_URL'`).
- `{URL_VALUE}` — copy nguyên văn từ .env / config, GIỮ trailing slash nếu có, GIỮ port,
  GIỮ scheme. KHÔNG normalize. KHÔNG lowercase.
- `{FILE_PATH}` — relative path từ repo root, dùng `/` (không phải `\`). Format file:line
  nếu trỏ tới line cụ thể.
- `{LIB_NAME}` — npm/pypi/maven artifact name canonical (`next-auth`, không phải `nextauth`).
- `{PATTERN}` — copy nguyên văn từ code, GIỮ `${...}` template syntax, GIỮ quotes.

MEDIUM/LOW TODO không có template ràng buộc — có thể wording tự do.

FRONTMATTER
status: best-effort-baseline
mode: baseline

Bắt đầu scan và ghi file ngay.
```

**Sub-agent type:** `general-purpose`.

### Pre-flight verify mỗi instance

- `{repo_abs_path}` tồn tại + readable. Fail → instance DỪNG, báo Orchestrator.
- Detect manifest file. Ghi vào Section F (Scan Metadata).

### Re-dispatch logic

Sau khi tất cả N instance return: nếu chỉ có M < N file output → re-dispatch instance thiếu (1 lần). Vẫn fail → DỪNG, báo user, không proceed STEP 2.2.

---

## STEP 2.2 — High-impact Q filter + Interactive Q&A loop

> **Đây là fix chính cho UX feedback "quá nhiều câu hỏi, không hiểu, không interact được".**
>
> Thay vì chờ SA tự đọc 100+ TODO markers scattered trong file, skill **chủ động hỏi 5-10 câu hỏi cao-impact** ngay trong chat. Câu trả lời được patch trực tiếp vào file `_parts/{sub_system}.md`. Câu hỏi thấp-impact (mô tả module phụ, naming convention) giữ inline TODO.

### 2.2.1 Skip nếu `--skip-qa`

User chạy với `--skip-qa` → skip toàn bộ STEP 2.2, mọi TODO giữ inline. Báo user:
```
⏭ Skipped Q&A loop. {total_todos} TODO markers giữ inline trong _parts/ files.
SA tự fill sau khi review.
```

→ Proceed STEP 2.3.

### 2.2.2 HIGH-impact Q filter + cross-repo deduplication (exact-match)

**Step A — Extract TODO inventory (Bash grep, KHÔNG đọc full file)**

Orchestrator chạy 1 Bash command để extract toàn bộ TODO markers — không Read N file (tránh context overload):

```bash
grep -rHn '<TODO: SA verify — ' {intermediate_folder}/*.md
```

Output (~50-200 dòng tùy scope, < 5K tokens):

```
_parts/svc-a.md:42:| Target name | <TODO: SA verify — Target của env `USER_SVC_URL` (value=`https://users.internal:8080`)?> | prod | .env.production:5 |
_parts/svc-b.md:68:| Auth scheme | <TODO: SA verify — Auth scheme cho lib `next-auth` ở `src/auth.ts`?> | ...
_parts/fe-app.md:42:| Target name | <TODO: SA verify — Target của env `USER_SVC_URL` (value=`https://users.internal:8080`)?> | ...
...
```

→ Orchestrator giờ chỉ làm việc trên grep output, KHÔNG đọc full per-repo file.

**Step B — Filter HIGH-impact only**

Phân loại từng TODO theo template wording (đã standardize ở §2.1):

| Wording starts with | Impact | Hành động |
|---|---|---|
| `Target của env` | HIGH (H1) | Hỏi |
| `IDL source của generated file` | HIGH (H2) | Hỏi |
| `Auth scheme cho lib` | HIGH (H3) | Hỏi |
| `Target của runtime URL pattern` | HIGH (H4) | Hỏi |
| Bất kỳ wording khác (free-form) | MEDIUM/LOW | **DROP** — không hỏi, chỉ inline |

→ Match wording deterministic. Không cần fuzzy semantic.

**Step C — Exact-match deduplication**

Gom TODO theo fingerprint = exact substring giữa `—` và `?>` của marker. Identical → merge thành 1 câu với `applies_to = [repo list]`. Lệch 1 ký tự → giữ riêng (KHÔNG normalize).

**Step D — Cap động**

`hard_cap = max(3, min(8, scope_count * 2))` — 1 repo → 3, 2 repo → 4, 3 repo → 6, ≥4 repo → 8.

Sau dedup nếu `count_after_dedup > hard_cap` → ưu tiên theo thứ tự template (H1 > H2 > H3 > H4). Câu vượt cap → giữ inline TODO.

### 2.2.3 Theme-grouped Q&A prompt

Group câu hỏi theo theme (KHÔNG theo repo) để user giữ mental context khi trả lời:

```
🎯 INTERACTIVE Q&A — {capped_count} câu HIGH-impact (gom {theme_count} nhóm).
MEDIUM/LOW TODO: {low_count} — chỉ inline, không hỏi.
Muốn skip toàn bộ: trả lời "skip all".

═══ NHÓM 1: External service targets ({n} câu) ═══

Q1 [áp dụng cho: fe-app, fe-admin, mobile-app — đều gọi USER_SVC_URL=https://users.internal]
   Target sub-system của URL này là?
     (a) {svc-a}  (b) external  (c) skip → giữ TODO ở cả 3 file

Q2 [svc-b]
   Target của `${PAYMENT_HOST}/charge` (PAYMENT_HOST không trong .env)?
     (a) {svc-c}  (b) external Stripe  (c) external khác (specify)  (d) skip

═══ NHÓM 2: Auth schemes ({n} câu) ═══

Q3 [fe-app, mobile-app — đều dùng next-auth]
   Backend callback endpoint của svc-a là?
     (free text — vd "/api/v1/auth/session", hoặc "skip")

═══ NHÓM 3: IDL source ({n} câu) ═══

Q4 [svc-a]
   File `src/__generated__/user-api.ts` generate từ IDL nào?
     (a) svc-b/api/openapi.yaml  (b) external  (c) skip

──────────────────────────────────────────────────

Trả lời 1 message (format: "Q1=a, Q2=external Stripe, Q3=/api/v1/auth/session, Q4=skip").
```

**Implementation note:** Nếu dùng được `AskUserQuestion` UI → render mỗi Q là 1 question. Nếu CLI fallback → text batch như trên.

**Pause & Wait.**

### 2.2.4 Patch per-repo files (propagate cho merged questions)

Parse user response, mỗi câu:

**Câu MERGED (multi-repo)** — vd Q1 áp dụng cho 3 repo:
- User chọn option / free text → replace `<TODO: SA verify — ...>` ở **CẢ 3 file** (cùng section/cell tương ứng) bằng câu trả lời + tag `<!-- Confirmed by SA: {date} (propagated across {n} repos) -->`. Update Section E của cả 3 file: `- [x] (Section X.Y) {câu hỏi} → Answered by SA on {date}: {trả lời} (propagated across 3 repos)`.
- User skip → TODO giữ inline ở cả 3 file. Update Section E của cả 3 file: `- [ ] (Section X.Y) {câu hỏi} → Asked, deferred (user skip)`.

**Câu SINGLE (1 repo)**:
- User chọn / free text → patch chỉ file đó với tag `<!-- Confirmed by SA: {date} -->`. Update Section E: `- [x] (Section X.Y) {câu hỏi} → Answered by SA on {date}: {trả lời}`.
- User skip → TODO giữ inline. Update Section E: `- [ ] (Section X.Y) {câu hỏi} → Asked, deferred (user skip)`.

**Báo summary:**
```
✓ Patched {answered_count} câu trả lời vào {affected_repo_count} file (sau dedup propagation).
⏭ {skipped_count} câu skip → TODO giữ inline + log vào Section E "Asked, deferred".
ℹ️ {dropped_by_cap_count} câu HIGH vượt cap + {medium_low_count} câu MEDIUM/LOW → chỉ inline TODO.
→ Proceed cross-system synthesis.
```

---

## STEP 2.3 — Cross-system synthesis (Agent B)

Spawn 1 sub-agent `general-purpose`. Prompt:

```
Bạn là System Architect đang tổng hợp baseline cross-system cho input HLD.

INPUT
Đọc tất cả file trong: {intermediate_folder}/
  {file list per-repo, exclude _overview.md nếu tồn tại}

OUTPUT
Ghi: {intermediate_folder}/_overview.md
Theo template: .agent/skills/NTAPP-system-overview/templates/cross_system.md

NHIỆM VỤ
1. Section A — Detected vs Scope: list {detected_list} vs {scope_list},
   ghi nguyên văn lý do skip cho out-of-scope (từ user input STEP 1.4),
   hoặc TODO nếu user không nêu.

2. Section B — Integration Diagram (Mermaid): node = mỗi sub-system in scope
   + external service. Edge = mỗi row Section 6.1 (Outbound) của các per-repo file.
   Edge label = giao thức + endpoint pattern (rút gọn). Node "external" dùng shape
   stadium `(["..."])` để highlight cross-boundary. Theo đúng example trong
   template `cross_system.md` Section B.

3. Section C — Contract Match Matrix (Tier 3 strict, NO Assumption):
   Cross-reference Section 0.3 (IDL) + Section 4 (API exposed) + Section 6.1
   (API consumed) giữa các per-repo file.
   Mỗi cặp (provider endpoint, consumer call) → 1 row matrix với status:
     MATCHED       — provider + consumer đều có IDL, version + DTO khớp.
     VERSION-MISMATCH — path/method khớp nhưng version diff.
     CONSUMER-ONLY    — consumer call endpoint không có provider trong scope.
     PROVIDER-ORPHAN  — provider expose endpoint không ai gọi trong scope.
     DTO-DRIFT        — path/method khớp, schema field khác (so sánh IDL bên provider
                        với generated client type bên consumer).
     UNKNOWN          — không đủ evidence để classify → kèm TODO.
   Mỗi row ghi 2 file:line (provider + consumer) trừ ORPHAN/CONSUMER-ONLY (1 phía).

4. Section D — Shared Data Models: cross-confirm Section 5.3 (Shared Schema
   Candidates) giữa per-repo files. Entity name xuất hiện ở ≥2 sub-system qua
   API DTO / event payload / DB shared / file share = MATCHED shared entity.
   Candidate chỉ ở 1 sub-system = KHÔNG list (chưa đủ evidence cross-system).
   Mỗi MATCHED entity ghi storage canonical (sub-system chính + table/collection) +
   sub-system cùng dùng + mechanism + risk (schema drift check needed nếu mechanism
   khác nhau giữa các sub-system).

5. Section E — Open Questions Summary: KHÔNG verbatim copy TODO từ per-repo files.
   Chỉ count + link tới per-repo file Section E. Câu HIGH-impact đã hỏi qua Q&A
   loop (Step 2.2) ghi vào table riêng (Q gốc + trả lời / skip status + patch target).

6. Section F — Scan Metadata: aggregate count từ per-repo Section F + thêm
   contract MATCHED rate + cross-boundary edge count.

EVIDENCE POLICY
- Section A, B (narrative + diagram): suy luận edge từ Section 6.1 — chấp nhận.
- Section C (Matrix): STRICT, không Assumption. UNKNOWN status thay vì đoán.
- Section D (Shared): cross-confirm bắt buộc — entity chỉ ở 1 sub-system → KHÔNG list.

Báo cáo cuối ≤200 từ: count mỗi status Matrix + cross-boundary edges + path file.
```

**Sub-agent type:** `general-purpose`.

### Verify

- `_overview.md` size > 0, có Section A → F đầy đủ.
- Section C có ≥1 row hoặc note "(không phát hiện contract pair nào — single sub-system hoặc fully isolated)".
- Section F counts plausible (matched_count + drift + version_mismatch = total bilateral edges).

Fail → re-dispatch Agent B 1 lần với error context. Vẫn fail → DỪNG, báo user.

---

## STEP 2.4 — SA Review gate

Aggregate metric, present 3-choice:

```
📋 SA REVIEW — System Baseline ({project_name})

Đã hoàn thành scan + synthesis. Output ở `_parts/` (chưa promote canonical).

### Files
- Cross-system overview: {intermediate_folder}/_overview.md
- Per-sub-system: {intermediate_folder}/{repo}.md × {N}

### Metric

| Metric | Value |
|---|---|
| Sub-system in scope | {N} |
| Sub-system out-of-scope | {M-N} |
| Q&A loop: HIGH-impact đã trả lời | {answered} / {high_asked} |
| HIGH-impact deferred (asked + skip) | {deferred} |
| HIGH-impact dropped (vượt cap) — inline TODO | {high_dropped} |
| MEDIUM/LOW TODO — inline TODO | {medium_low} |
| Integration edges trong scope | {E_in} |
| Cross-boundary edges (target ngoài scope) | {E_cross} ⚠️ HLD attention |
| Contract Matrix status |  |
|   MATCHED | {matched_count} |
|   VERSION-MISMATCH | {vm_count} 🔴 HLD priority |
|   DTO-DRIFT | {drift_count} 🔴 HLD priority |
|   CONSUMER-ONLY | {co_count} |
|   PROVIDER-ORPHAN | {po_count} |
|   UNKNOWN | {unknown_count} |
| Shared entities | {shared_count} |

### Top 3 sub-system có nhiều TODO nhất

1. {svc-X} — {n} TODO
2. {svc-Y} — {n} TODO
3. {svc-Z} — {n} TODO

### Quyết định

  (a) **Approve** — STEP 2.5 promote _parts/ → canonical + archive snapshot.
       Có thể tiếp tục với /ntapp-architecture-design Stage 2.
  (b) **Refine** — mô tả thay đổi (rescan repo X / redo synthesis / extra Q&A).
       Orchestrator parse feedback và dispatch lại.
  (c) **Cancel** — bỏ workflow. _parts/ giữ debug, không promote.
```

**Pause & Wait.**

### Xử lý decision

- **(a) Approve** → proceed STEP 2.5.
- **(b) Refine** → parse feedback, dispatch tương ứng (re-scan / re-synthesize / extra Q&A), sau đó quay lại STEP 2.4 (recursive).
- **(c) Cancel** → log cancellation, KHÔNG xóa `_parts/`, KHÔNG snapshot. Workflow chấm dứt.

---

## STEP 2.5 — Dual-write finalize

1. **Snapshot bản cũ:** Nếu `{planning_artifacts}/*.md` đã có từ run trước → mkdir `{planning_artifacts}/archive/_v{N_next}_{date}/` (N_next = max của `ls archive/_v*` + 1) và copy file canonical cũ vào.
2. **Promote:** copy `{intermediate_folder}/*.md` → `{planning_artifacts}/`. Giữ `_parts/` nguyên (overwrite run sau, debug).
3. **Report:**
```
✓ Baseline finalized.

Canonical:
- {planning_artifacts}/_overview.md
- {planning_artifacts}/{repo}.md × {N}

Archive snapshot bản trước (nếu có):
- {planning_artifacts}/archive/_v{N}_{date}/

Tiếp theo:
- Mở _overview.md review Contract Match Matrix.
- Gõ /ntapp-architecture-design — sub-agent HLD sẽ load baseline làm input.
```

---

## Edge cases

| Tình huống | Xử lý |
|---|---|
| Multi-root workspace gate fail | HALT ở STEP 1.3 (workflow.md) — không vào STEP 2.x |
| Scan instance fail sau re-dispatch | DỪNG STEP 2.1, báo user trước STEP 2.2 |
| Q&A loop user không trả lời gì (Enter trống) | Treat = skip all, log warning, proceed STEP 2.3 |
| Synthesizer fail 2 lần | DỪNG STEP 2.3, báo user, _parts/ giữ debug |
| User chọn cancel STEP 2.4 | _parts/ giữ, không promote, không snapshot |
| `_parts/` đã có từ run trước khi STEP 2.1 start | Cảnh báo user ở STEP 1.4, hỏi overwrite hay cancel |
| Scope chỉ có 1 sub-system | Skip Section C/D synthesis (không có contract pair), _overview.md vẫn ghi với note "Single sub-system — Contract Matrix N/A" |
| Repo > 10000 file | Agent A vẫn tự xoay, nhắc user mỗi instance có thể mất 5-10 phút |
