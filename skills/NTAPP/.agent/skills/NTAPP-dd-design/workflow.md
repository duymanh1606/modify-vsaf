# Domain-Driven Design Reproduction Workflow (NTAPP Multi-Agent Edition)

**Goal:** Tái dựng mô hình DDD **as-is** của hệ thống hiện hữu, chấm điểm **maturity** (cái gì tốt — giữ, cái gì sai — sửa), rồi đề xuất **to-be blueprint + migration roadmap**. Output là một bộ artifact SỐNG, spec-canonical, làm SSoT cho cả business lẫn dev. Thực thi qua 5 Agent (D0/D1/D2/D3/D4) chuyên biệt hoạt động tuần tự.

**Your Role:** Bạn đóng vai **Agent D0 (Domain Orchestrator)** — điều phối tuần tự D1 → D2 → D3 → D4, vận hành quality gate, và assembly bộ artifact cuối. Bạn là điểm chạm duy nhất với người dùng (SA/Domain Expert) trong toàn workflow.

**Iron Rules:** Toàn workflow tuân thủ [principles/iron_rules.md](./principles/iron_rules.md). **Maturity Rubric** dùng chung ở [principles/maturity_rubric.md](./principles/maturity_rubric.md). Đọc cả 2 file trước khi thực thi bất kỳ step nào.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (mode + roster + bản đồ + rule + launch). Chi tiết thực thi nằm TRONG từng step file `./steps/`.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi PAUSE/GATE) RỒI mới đọc step kế qua pointer `**Next:**`. KHÔNG đọc trước nhiều step. State chuyển tiếp qua `part_*.md` trong `{intermediate_folder}`, không qua việc giữ instruction trong context.
- 🧭 **Nguyên tắc cốt lõi (R10):** Tách bạch **as-is** (mô tả thực tại — kể cả khuyết tật) khỏi **to-be** (tương lai mong muốn). KHÔNG "làm đẹp" model as-is, vì như vậy sẽ che mất chính những gap mà skill này tồn tại để phơi bày.

---

## MODE SELECTION (Agent D0 đọc ĐẦU TIÊN)

Skill có 2 mode. Agent D0 xác định mode từ user message **trước khi** chạy bất kỳ step nào:

| Mode | Trigger | Khi nào dùng |
|---|---|---|
| **REPRODUCE** (default) | "tái dựng DDD" / "reproduce domain model" / "DDD audit" / không có flag | Lần đầu dựng domain model, hoặc overhaul toàn bộ |
| **REFRESH** | `--refresh <bc_id>`, "cập nhật bounded context X", "sync domain model sau slice" | Đã có domain model; cần cập nhật MỘT bounded context vừa đổi + re-score maturity, KHÔNG re-run full interview |

- **REPRODUCE mode** → chạy full pipeline D1→D2→D3→D4 (mục [EXECUTION](#execution)).
- **REFRESH mode** → chạy luồng rút gọn ở mục [REFRESH MODE EXECUTION](#refresh-mode-execution-keep-the-model-living). **Bỏ qua** mục EXECUTION đầy đủ.

> **Vì sao có REFRESH:** Model spec-canonical (do business sở hữu, tách khỏi code) có rủi ro **drift** khỏi code theo thời gian. REFRESH là entry point nhẹ — gọi từ `slice-loop` Definition-of-Done mỗi khi một slice chạm tới một bounded context → grill lại đúng BC đó, re-sync CONTEXT-MAP, re-score maturity của BC. Đây là cơ chế giữ model SỐNG.

---

## ROSTER & ROLES

| Agent | Role | Steps Owned |
|---|---|---|
| **D0** | Domain Orchestrator + QA Gatekeeper | 01, 06 |
| **D1** | Strategic Domain Analyst (Bounded Context + Subdomain + Context Map) | 02 |
| **D2** | Tactical Domain Modeler (Aggregate + Entity/VO + Invariant + Domain Event + Ubiquitous Language) | 03 |
| **D3** | Maturity Assessor (chấm điểm as-is theo rubric) | 04 |
| **D4** | Target-State & Migration Architect (to-be blueprint + roadmap) | 05 |

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

Mỗi step là một file độc lập trong `./steps/`, mở đầu bằng `> **Acting as:** [Agent Dx]` trỏ persona, kết thúc bằng pointer `**Next:**` tới step kế (step cuối là TERMINAL).

| # | Step file | Agent | Output | Gate |
|---|---|---|---|---|
| 01 | steps/step-01-init.md | D0 | Evidence Inventory + Scope (BC in-scope) | intake — user confirm scope + nguồn evidence |
| 02 | steps/step-02-strategic.md | D1 | part_02_strategic.md → `CONTEXT-MAP.md` | **G1** Boundary Coverage (mọi module ∈ ≥1 BC) |
| 03 | steps/step-03-tactical.md | D2 | part_03_tactical.md → per-BC `CONTEXT.md` + `AGGREGATES.md` + `EVENTS.md` | **G2** Tactical Completeness (aggregate có root + invariant; event có producer+consumer) |
| 04 | steps/step-04-maturity.md | D3 | part_04_maturity.md → `maturity.md` | **G3** Scored & Evidenced (mọi BC chấm đủ 7 trục; mọi ❌ có evidence + remediation) |
| 05 | steps/step-05-target-migration.md | D4 | part_05_target.md → `TARGET.md` + `MIGRATION.md` (+ ADR) | **G4** Lane-mapped (mọi remediation map về lane + DAG không cycle) |
| 06 | steps/step-06-assembly.md | D0 | assembly toàn bộ `domain/` (+ archive) | **G5** Quantitative Audit + HITL sign-off (TERMINAL) |

Chuỗi (REPRODUCE mode): **01 → [intake] 02 → [G1] 03 → [G2] 04 → [G3] 05 → [G4] 06 → [G5]**.
Cổng người-dùng: **intake** (Step 01) + **HITL sign-off** (Step 06). Gate G1–G5 là QA/self-check (FAIL → loop về owner — KHÔNG phải pointer `**Next:**`).

---

## INITIALIZATION

### Phân giải cấu hình (Configuration Resolution)

Trước khi chạy bất kỳ step nào, Agent D0 PHẢI resolve config theo cascade 3 layer (ưu tiên cao → thấp).

#### Bước 0 — Resolve `{project-root}`

Walk up từ `cwd` tìm marker folder: `_bmad/` → đó là `{project-root}`; nếu không thấy thì `.git/`; nếu lên `/` vẫn không thấy → fallback `cwd` + log warning.

#### Layer 1 — BMad project config

Đọc `{project-root}/_bmad/bmm/config.yaml` nếu tồn tại. Lookup keys (**giống nhau giữa mọi repo** — chỉ value khác): `project_name`, `planning_artifacts`. BMad dùng placeholder `{project-root}` trong values → thay bằng absolute path đã resolve.

> ⚠️ **Portability (CLAUDE.md):** KHÔNG hardcode output-root (`NTAPP-output/` / `_bmad-output/`). Mọi path derive từ key `planning_artifacts` — đây cũng là nơi `/ntapp-architecture-design` GHI HLD/Module 0/WBS (và `/ntapp-system-overview` ghi `system_overview/`), nên dd-design đọc đúng chỗ chúng tồn tại bất kể repo map key đó về stage-folder nào.

#### Layer 2 — Skill family config (override)

Đọc `{project-root}/.bmm-config.yaml` nếu tồn tại. Tìm section `ntapp-dd-design:`. Override giá trị từ Layer 1 nếu có.

```yaml
ntapp-dd-design:
  project_name: <string>          # optional, override Layer 1
  domain_artifacts: <path>        # optional — nơi ghi bộ artifact DDD
```

#### Layer 3 — Default + Interactive (fallback)

Khi cả Layer 1 và Layer 2 đều miss biến cần → DỪNG, hỏi user (Pause & Wait), rồi ghi vào `.bmm-config.yaml` section `ntapp-dd-design:` để lần sau không hỏi lại.

#### Biến runtime cuối cùng

| Biến | Nguồn | Ghi chú |
|---|---|---|
| `project_name` | Layer 1/2/3 | Tên dự án — hiển thị header artifact |
| `planning_artifacts` | Layer 1 key `planning_artifacts` | Nơi ĐỌC mọi input: HLD, Module 0, `project_wbs.md`, `system_overview/`, PRD/Epics, `CONTEXT.md`. Cùng folder `/ntapp-architecture-design` ghi ra. |
| `domain_artifacts` | Layer 2 override → else derive | Nơi GHI bộ artifact DDD. Default = `{planning_artifacts}/domain/` (co-locate cạnh HLD). Override qua `.bmm-config.yaml` `ntapp-dd-design.domain_artifacts`. |
| `intermediate_folder` | Auto-derive | = `{domain_artifacts}/_parts/` |
| `template_path` | Hardcode | `./templates/` — relative to **skill root** (folder chứa workflow.md) |
| `agent_personas_path` | Hardcode | `./agents/` — relative to skill root |
| `rubric_path` | Hardcode | `./principles/maturity_rubric.md` — relative to skill root |
| `iron_rules_path` | Hardcode | `./principles/iron_rules.md` — relative to skill root |
| `date` | System | ISO 8601 `YYYY-MM-DD` |

### Output Naming Convention (Dual-Write)

Mọi output cuối đều ghi 2 bản: canonical (latest) + archive (versioned snapshot). Bộ artifact:

| Output | Canonical (latest) | Archive (history) |
|---|---|---|
| Context Map | `{domain_artifacts}/CONTEXT-MAP.md` | `{domain_artifacts}/archive/CONTEXT-MAP_v{N}.md` |
| Per-BC ubiquitous language | `{domain_artifacts}/contexts/<bc>/CONTEXT.md` | archive theo BC |
| Per-BC aggregates | `{domain_artifacts}/contexts/<bc>/AGGREGATES.md` | archive theo BC |
| Domain event catalog | `{domain_artifacts}/EVENTS.md` | `{domain_artifacts}/archive/EVENTS_v{N}.md` |
| Maturity assessment | `{domain_artifacts}/maturity.md` | `{domain_artifacts}/archive/maturity_v{N}.md` |
| To-be blueprint | `{domain_artifacts}/TARGET.md` | `{domain_artifacts}/archive/TARGET_v{N}.md` |
| Migration roadmap | `{domain_artifacts}/MIGRATION.md` | `{domain_artifacts}/archive/MIGRATION_v{N}.md` |
| ADR | `{domain_artifacts}/adr/NNNN-slug.md` | (immutable — không archive, append-only) |
| Intermediate parts | `{intermediate_folder}/part_*.md` | (không archive — overwrite mỗi run) |

**Versioning logic:** Detect `N_next` bằng `ls archive/{base}_v*.md` → `max(N) + 1` (hoặc `1` nếu rỗng).

---

## GLOBAL RULES (bất biến — áp dụng mọi step)

- ✅ Toàn workflow tuân thủ [Iron Rules R1–R10](./principles/iron_rules.md) (SSoT — không lặp body ở đây). Trục chính: **R3** No-Fabrication · **R8** Model Alignment · **R10** As-is ≠ To-be.
- ✅ Agent D0 là điểm chạm duy nhất với người dùng; mỗi step hoá thân đúng persona trong [`./agents/`](./agents/).
- ⛔ Đọc đúng MỘT step file mỗi lần; chỉ đọc step kế qua pointer `**Next:**` khi step hiện tại xong + qua cổng (nếu có).

---

## REFRESH MODE EXECUTION (Keep the model living)

> **Acting as:** Agent D0 điều phối; D2 thực thi grill lại tactical của BC; D3 re-score. D1 chỉ tham gia khi boundary của BC đổi.
> **Tuân thủ:** [Iron Rules](./principles/iron_rules.md) — R3, R5 (Consistency), R8 (Model Alignment), R10 (As-is ≠ To-be).
> **Mục tiêu:** Cập nhật MỘT bounded context vừa đổi + re-sync CONTEXT-MAP + re-score maturity, KHÔNG re-run full pipeline.

### F1 — Pre-flight (Agent D0)

1. Resolve config — **giống REPRODUCE mode** [INITIALIZATION](#initialization).
2. Parse `<bc_id>` từ `--refresh` flag hoặc hỏi user. Verify `<bc_id>` tồn tại trong `{domain_artifacts}/CONTEXT-MAP.md`.
   - **Không tồn tại** → STOP: *"BC chưa có trong model. Nếu là BC mới → chạy REPRODUCE (hoặc escalate `/ntapp-architecture-design` nếu chạm contract)."*
3. Xác định **trigger** của refresh: slice nào / commit nào / intent gì khiến BC này đổi (để grill đúng trọng tâm, R4 Traceability).

### F2 — Boundary check (Agent D0 → escalate nếu cần)

Nếu thay đổi làm **đổi ranh giới BC** (gộp/tách BC, đổi quan hệ context-map, đổi integration pattern, hoặc chạm contract Module 0) → **STOP, escalate**: đây không phải refresh nhẹ. Chạy REPRODUCE cho cụm BC liên quan, và nếu chạm Module 0 thì `/ntapp-architecture-design` trước. (Mirror R8.)

Pass → thay đổi nằm gọn TRONG ranh giới BC (aggregate/invariant/event/ngôn ngữ) → F3.

### F3 — Re-grill tactical (Agent D2)

Chạy [Step 03](./steps/step-03-tactical.md) nhưng **scope = chỉ `<bc_id>`**: cập nhật `contexts/<bc>/CONTEXT.md` + `AGGREGATES.md` + các domain event của BC trong `EVENTS.md`. Giữ nguyên BC khác (R1 Verbatim cho phần không đổi).

### F4 — Re-score maturity (Agent D3)

Chạy [Step 04](./steps/step-04-maturity.md) scope chỉ `<bc_id>`: re-score 7 trục cho BC, cập nhật row của BC trong `maturity.md` roll-up, ghi lại delta điểm so với version trước.

### F5 — Sync + version bump (Agent D0)

1. Re-inject row của BC vào `CONTEXT-MAP.md` (chỉ phần BC, R1 + R2 cho phần còn lại).
2. Dual-write archive cho mọi file đã đụng (`CONTEXT-MAP`, `EVENTS`, `maturity`, per-BC).
3. Nếu maturity của BC **giảm** so với trước → WARN user (drift dấu hiệu): gợi ý mở remediation unit.

### Exit Criteria (REFRESH)

- [ ] `<bc_id>` đã cập nhật trong per-BC artifacts + CONTEXT-MAP + EVENTS.
- [ ] maturity row của BC re-scored + ghi delta.
- [ ] KHÔNG đổi boundary/contract (nếu có → đã escalate ở F2).
- [ ] Archive version bump cho file đã đụng.

---

## EXECUTION

> **Áp dụng cho REPRODUCE mode.** REFRESH mode dùng mục [REFRESH MODE EXECUTION](#refresh-mode-execution-keep-the-model-living) ở trên.

Sau khi resolve config ([INITIALIZATION](#initialization)) và xác nhận **mode = REPRODUCE** → khởi động pipeline tuần tự theo PIPELINE MAP. Đọc đúng MỘT step mỗi lần; mỗi step tự trỏ step kế qua `**Next:**`. KHÔNG đọc trước nhiều step.

**Next:** Read fully and follow `./steps/step-01-init.md`
