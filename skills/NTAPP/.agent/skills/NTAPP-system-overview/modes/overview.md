# Mode `overview` — Opt-in ergonomic per-repo overview

> **Trigger:** STEP 2 của [../workflow.md](../workflow.md) khi `--mode overview` — **opt-in, phải gõ flag tường minh** (default là `baseline`), hoặc user chọn option (e) ở scope confirm.
>
> **Input:** `scope_list` từ STEP 1, output dir đã resolve.
>
> **Output:** 1 file per repo tại `{output_dir}/{repo_name}_overview.md` theo [../templates/per_repo.md](../templates/per_repo.md) (skip Section 0 + Section E).
>
> **Evidence policy:** Tuân thủ [../principles.md](../principles.md) Tier 1 (body) + Tier 2 (bảng API/Integration/Data). KHÔNG Section 0, KHÔNG cross-system synthesis, KHÔNG Q&A loop.

---

## Spawn parallel sub-agents

Sau khi user confirm scope, spawn **N sub-agent trong cùng 1 message** (parallel). Mỗi agent là `general-purpose`, độc lập, không share state.

**Prompt template cho mỗi agent** (fill `{repo_name}`, `{repo_abs_path}`, `{output_file_abs_path}`, `{stack_hint}`, `{project_label_or_empty}`):

```
Bạn là Software Architect / Senior Technical Analyst.

NHIỆM VỤ
Đọc và phân tích toàn bộ source code repo tại:
  {repo_abs_path}
(Stack hint: {stack_hint})

Ghi file Markdown vào:
  {output_file_abs_path}

QUY TẮC
- KHÔNG đọc file ngoài `{repo_abs_path}`.
- KHÔNG đụng git (không commit / checkout / clean).
- KHÔNG viết file nào khác ngoài `{output_file_abs_path}`.
- Nếu file đã tồn tại — overwrite (caller đã xác nhận --force).
- Báo cáo cuối ≤200 từ: tóm tắt repo + path file đã ghi.

EVIDENCE POLICY
- Tier 1 (Executive Summary, Architecture narrative, Business Features, Flows, Assessment, Risks):
  prose-friendly. Cho phép `**Assumption:** ...` khi suy luận business intent.
- Tier 2 (bảng API Analysis, Database tables, Integration tables, Full Feature List):
  mỗi row PHẢI có cột "File evidence" trỏ file:line. Thiếu → `<TODO: SA verify — câu hỏi cụ thể>`.
- KHÔNG dán TODO trong Tier 1 prose.

ƯU TIÊN ĐỌC
1. README, README.md
2. Build manifest: pom.xml / build.gradle / package.json / go.mod / requirements.txt / Cargo.toml / Gemfile / composer.json / mix.exs
3. Config: application.yml / application.properties / *.env / config/* / appsettings.json
4. Dockerfile, docker-compose.yml, helm/, k8s/, .github/workflows/, Jenkinsfile, .gitlab-ci.yml
5. Entry points: controller / router / handler / endpoint, main()/Application class / index.* / cmd/
6. Service / business logic layer
7. Repository / DAO / DB access layer
8. Scheduler / cron / background job
9. MQ consumer / producer / listener / subscriber
10. Entity / model / DTO / schema
11. Migration scripts (Flyway / Liquibase / Alembic / Knex / Prisma)
12. External client (Feign / RestTemplate / HTTP client / gRPC stub / SDK wrapper)

============================================================
FORMAT OUTPUT — Markdown, tiếng Việt
============================================================

Tuân thủ template:
  .agent/skills/NTAPP-system-overview/templates/per_repo.md

LƯU Ý MODE OVERVIEW:
- SKIP Section 0 (Service Identity & Auth Profile) — chỉ mode baseline có.
- SKIP Section 5.3 (Shared Schema Candidates) — chỉ mode baseline có (cần cross-system synthesis).
- SKIP Section E (Open Questions for SA) — TODO giữ inline tại Tier 2 cell, không aggregate.
- Frontmatter: status: best-effort-overview, mode: overview.
- AuthN/AuthZ ghi gọn ở Section 2 (Architecture Overview), không tách section riêng.

Nếu `{project_label_or_empty}` không rỗng → in `> **Dự án:** {project_label}` ở header.
Nếu rỗng → bỏ dòng đó.

Bắt đầu phân tích và ghi file ngay.
```

**Sub-agent type:** `general-purpose` (cần Read, Glob, Grep, Write).

**Parallel rule:** Tất cả Agent tool call trong 1 message. Không tuần tự.

---

## Collect results

Sau khi mọi sub-agent return:

1. Verify mỗi file output: size > 0, có H1 header `# {service}`.
2. Render bảng tổng kết:

```
Hoàn thành (mode overview). Kết quả:

| Repo | Status | File |
|---|---|---|
| {repo-b} | OK | {output-dir}/{repo-b}_overview.md |
| {repo-c} | OK | {output-dir}/{repo-c}_overview.md |
| {repo-a} | SKIP | (already exists, dùng --force để regen) |
| {repo-d} | FAILED | sub-agent báo lỗi: {error msg} |

Tiếp theo:
- Mở file review nội dung.
- Re-run với --force <repo> để regen.
- Re-run với --repos <name> cho repo fail.
- Cần cross-system contract matrix + Section 0 làm input HLD? → /ntapp-system-overview (mode baseline default)
```

---

## Edge cases

| Tình huống | Xử lý |
|---|---|
| Không tìm thấy code repo nào | Báo user kiểm tra `--workspace-root` / `--repos`, không spawn |
| Output dir không tạo được (permission) | DỪNG ở STEP 0, báo user |
| Sub-agent timeout / fail | Ghi FAILED + error vào bảng, KHÔNG retry tự động |
| File output đã tồn tại + không `--force` | SKIP silently, ghi SKIP vào bảng |
| User huỷ ở STEP 1.4 | Dừng |
| Repo > 10000 file | Agent vẫn tự xoay (general-purpose có Glob/Grep), nhắc user overview có thể mất 5-10 phút |
| Repo frontend (Angular/React/Vue/Svelte) | Section 4 chỉ consumer-side, Section 5 thường rỗng hoặc localStorage/IndexedDB, giữ structure 10 sections |
| Repo library/SDK | Section 4 ghi public API surface (exported class/function), Section 7 ghi typical usage pattern thay vì runtime flow |
