# Audit Commands — VDS Scripts Skill

Detailed command reference for audit orchestrator operations.

These are interactive/operator command examples using `uv run --directory ~/.claude/vds-scripts --package <package-name>` for cross-platform execution. Preferred integrated baseline for the `vds-scripts` workspace is Python 3.14+.

## Audit Prep Sequence (Hard-Cut State-First)

```/dev/null/audit-commands-prep-sequence.sh#L1-20
# 1) Seed centralized state from registry
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit parse-registry \
  --registry-page "<REGISTRY_PAGE_URL_OR_ID>"

# 2) Sync repositories for code evidence
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit --json-only sync repos \
  --bitbucket-project "<BITBUCKET_PROJECT_KEY>" \
  --project-storage-key "<PROJECT_STORAGE_KEY>"

# 3) Materialize docs + code chunks
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit extract-docs \
  --registry-page "<REGISTRY_PAGE_URL_OR_ID>" \
  --project-storage-key "<PROJECT_STORAGE_KEY>" \
  --output-dir "<EVIDENCE_DIR>"

# 4) Hard gate before workflow
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit --json-only state readiness \
  --project "<PROJECT_STORAGE_KEY>" --repo "<REPO_SELECTOR>" \
  | jq '{ready, docs_chunk_ready, code_chunk_ready}'

# 5) Phase 87 direct project/repo parsing
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit --json-only parse-project \
  --project "<PROJECT_PAGE_ID>" > /tmp/parse-project.json

uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit --json-only parse-repo \
  --project "<PROJECT_PAGE_ID>" --bitbucket-project "<BITBUCKET_PROJECT_KEY>" \
  --repo "<REPO_SELECTOR>" > /tmp/parse-repo.json

# 6) Execute workflow with resolved repo seed
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit workflow "<LOCAL_REPO_PATH>" \
  --thread-id "<THREAD_ID>" --canonical-checklist \
  --checklist-profile "<PROFILE_ID>" \
  --seed-payload /tmp/parse-repo.json
```

## Selector Notes

- `parse-project` / `parse-repo` `--project` accepts only Confluence page-id selectors (numeric or URL with `pageId=<ID>`)
- Checklist precedence: `--checklist-page-id` > `--checklist-profile` > state profile resolution > canonical fallback `88722450`
- Phase 102 hard-cut: Legacy `CL-NNN:row_N` tokens not parsed; run `state migrate-row-keys --execute` first
- Phase 90 selector isolation: `parse-project` rejects Bitbucket keys in `--project`; use `parse-repo --bitbucket-project`
- `parse-repo` returns `repo_coverage` (project-wide) and `selected_repo_coverage` (filtered); use latter for single-repo seeds
- `sync repos` selectors: `--local` > `--bitbucket-project` > `--github-org` > `--git-url` (precedence)

## Audit Monitoring (Phase 68)

```/dev/null/audit-commands-monitoring.sh#L1-11
# Preflight credentials
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit \
  --json-only doctor credentials --require-state-dsn

# Dual-source prep gate
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit \
  --json-only state readiness --project "<PROJECT_KEY>" --repo "<REPO_KEY>" \
  | jq '{ready, docs_chunk_ready, code_chunk_ready, hierarchy_ready}'

# Follow runtime logs
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit \
  doctor logs-follow --follow --tail 200 --audit-id "<AUDIT_ID>" --json

# Crawl diagnostics (Phase 80)
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator vds-audit \
  doctor crawl-status --project-storage-key "<PROJECT_KEY>"
```

## Corpus Lifecycle (Phase 94)

```bash
# Dry-run purge
vds-audit --json-only corpus purge --project "<PROJECT_KEY>"

# Execute purge with advisory lock
vds-audit --json-only corpus purge --project "<PROJECT_KEY>" --execute

# Keep latest, purge older
vds-audit corpus purge --project "<PROJECT_KEY>" --keep-latest --execute

# Backfill metadata
vds-audit --json-only corpus backfill-metadata --project "<PROJECT_KEY>"

# Health diagnostics
vds-audit --json-only doctor corpus-status --project "<PROJECT_KEY>"

# Force full re-ingest
vds-audit extract-docs --project-storage-key "<PROJECT_KEY>" \
  --force-full-reingest --execute
```

## DSPy Judge & Gold Dataset (Phase 108)

DSPy is **enabled by default**. No `--use-dspy` flag needed.

```bash
# Workflow with DSPy judge (default)
vds-audit workflow "<REPO_PATH>" --thread-id "<THREAD_ID>" --canonical-checklist

# Disable DSPy explicitly
vds-audit workflow "<REPO_PATH>" --thread-id "<THREAD_ID>" --canonical-checklist --no-use-dspy

# Build gold dataset
vds-audit build-gold-dataset [--search-root <dir>] [--output <path>] \
  [--checklist-aware] [--category-balance] [--benchmark-slice]
```

**Key Environment Variables**:
- `VDS_AUDIT_FEATURES__DSPY_ENABLED` (default: `true`)
- `VDS_AUDIT_DSPY_JUDGE_MAX_INVOCATIONS_PER_RUN` (default: `20`)
- `VDS_AUDIT_LLM__DSPY_JUDGE_LOW_CONFIDENCE_THRESHOLD` (default: `0.65`)
- `VDS_AUDIT_DSPY_ASSERTIONS_ENABLED` (default: `true`)

## Multi-Provider Runs (Phase 107)

```/dev/null/audit-commands-multi-provider.sh#L1-21
# Alibaba-openai (qwen3.5-plus)
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator \
  vds-audit workflow "<REPO_PATH>" \
  --profile alibaba-openai \
  --project-storage-key "<PROJECT_STORAGE_KEY>" \
  --thread-id "<THREAD_ID>" \
  --canonical-checklist \
  --target "CL-004,CL-001"

# Z.ai-openai (glm-5)
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator \
  vds-audit workflow "<REPO_PATH>" \
  --profile zai-openai \
  --project-storage-key "<PROJECT_STORAGE_KEY>" \
  --thread-id "<THREAD_ID>" \
  --canonical-checklist \
  --target "CL-004,CL-001"

# Gemini (via local proxy)
uv run --directory ~/.claude/vds-scripts --package audit_orchestrator \
  vds-audit workflow "<REPO_PATH>" \
  --profile antigravity-gemini \
  --project-storage-key "<PROJECT_STORAGE_KEY>" \
  --thread-id "<THREAD_ID>" \
  --canonical-checklist \
  --target "CL-004,CL-001"
```

Non-Claude profiles have increased budgets: `MAX_TURNS=32`, `MAX_TOOL_CALLS=96`.

For single-row reruns such as `CL-002`, keep the same workflow shape and pass `--target CL-002`. Do not use unsupported legacy selectors such as `--check-ids` or `--targeted-rows`.

## System Documentation (Phase 106)

```bash
# Publish 6-page Vietnamese hierarchy
vds-audit publish-system-doc --project "<PROJECT_ID>" --sync-policy if-changed

# Force re-publish
vds-audit publish-system-doc --project "<PROJECT_ID>" --sync-policy force
```

Hierarchy pages:
- Root: Tài liệu Hệ thống Audit
  - 📐 Công nghệ & Kiến trúc
  - ⚙️ Quy trình Vận hành
  - 📊 Kết quả Audit & Chỉ số
  - 🔧 Hướng dẫn Cài đặt & Cấu hình
  - 📖 Tham chiếu Kỹ thuật
