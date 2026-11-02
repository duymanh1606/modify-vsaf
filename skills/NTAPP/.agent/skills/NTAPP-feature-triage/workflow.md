# NTAPP Feature Triage — Workflow

Triage một feature mới **tại intake** (Stage 0.5 — trước Stage 1 Discovery), trước khi viết code/spec. Trả lời: *"Feature này nên đi lane nào, slash command kế tiếp là gì?"*

Skill là **forcing function for clarity**, không phải correctness oracle. Output advisory; dev confirm bằng cách chạy command được recommend. Skill enforce hard gates (refuse nếu thiếu prerequisite), còn lại lean trên dev attestation.

## Stage placement

```
(Feature intent xuất hiện)
        │
        ▼
Stage 0.5: /ntapp-feature-triage
        │
        ├─ LANE 1 (Express hotfix preset)   → edit + SKIP_PRECOMMIT=1 + compensate 48h
        ├─ LANE 2 (Path B quick-dev)        → /bmad-quick-dev
        ├─ LANE 3 (Full per-slice loop)     → Stage 3-4-5 (slice active)
        ├─ LANE 4 (Ad-hoc per-unit)         → /ntapp-feature-design (skip Stage 2b)
        │     Trigger A: project PoC (≤3 unit toàn bộ)
        │     Trigger B: per-feature contained (1 unit, module cũ, no contract change)
        └─ REFUSE / ESCALATE                → unblock command cụ thể
```

---

## Config resolution

3-layer cascade chuẩn NTAPP:

- **Layer 1** — `{project-root}/_bmad/bmm/config.yaml`: `planning_artifacts`, `stage_1_discovery`, `stage_2_architecture`, `design_system_root`.
- **Layer 2** — `{project-root}/.bmm-config.yaml` section `ntapp-feature-triage:`: override `triage_output_dir` (default `{stage_1_discovery}/triage`), `manifest_dir` (default `{triage_output_dir}/manifests`), `scope_creep_guardrail` (default `false`).
- **Layer 3** — Interactive fallback nếu miss.

Biến runtime:

| Biến | Nguồn | Dùng cho |
|:--|:--|:--|
| `triage_output_dir` | L1/L2/L3 | OUTPUT — `YYYY-MM-DD-{slug}.md` decision file |
| `manifest_dir` | L1/L2/L3 | OUTPUT — `{id}.yaml` manifest (chỉ ghi khi opt-in) |
| `scope_creep_guardrail` | L2 | Khi `true` + lane=4 trigger-B → ghi manifest |
| `stage_2_architecture` | L1 | INPUT — `project_wbs.md`, `00_system_connectivity_integration.md`, `slices/SLICE-*.md` |
| `stage_1_discovery` | L1 | INPUT — `epics.md` (match intent với epic) |
| `design_system_root` | L1 | INPUT — **family root** DS (`registry.yaml` nằm ở đây khi multi-DS). Check bootstrap: Bước 0 + Bước 4.1 |
| `ds_id_target` | derive (Bước 4.1) | DS mà feature thuộc về — resolve theo `_shared/ds-resolution.md` nhánh B |

`{project-root}`: walk up từ `cwd` tìm `_bmad/` rồi `.git/`.

---

## Quy trình

### Bước 0 — Pre-flight scan (auto, không refuse)

Build state map từ filesystem:

| Signal | Cách lấy |
|:--|:--|
| `wbs_present` | `[[ -f {stage_2_architecture}/project_wbs.md ]]` |
| `module0_present` | `[[ -f {stage_2_architecture}/00_system_connectivity_integration.md ]]` |
| `active_slice_count` | `ls {stage_2_architecture}/slices/SLICE-*.md 2>/dev/null \| wc -l` |
| `ds_family_root` | `{design_system_root}` — family root. `registry.yaml` tồn tại ở đây ⇒ project multi-DS |
| `ds_systems` | Không có `registry.yaml` → 1 system ẩn danh, root = family root (legacy). Có → parse `systems.{ds_id}`: `root`, `code_repo`, `id_prefixes`, `modules` (+ `default_ds`) |
| `ds_bootstrap_map` | Mỗi system → `[[ -f {ds_family_root}/{root}/master_token.json ]]` (`root: "."` ⇒ chính family root). Legacy 1 system ⇒ y hệt check `{design_system_root}/master_token.json` cũ |
| `wbs_module_list` | parse `project_wbs.md` cột "Module" — tập prefix declared |
| `wbs_unit_count` | đếm row data của `project_wbs.md` |

Mọi refuse logic ở Bước 2 (single source). Bước 0 chỉ collect.

---

### Bước 1 — Gather signals (interactive Q&A)

Hỏi dev tuần tự, **cheap → expensive**. Skip câu nào có thể infer từ câu trước hoặc từ state map.

| # | Câu hỏi | Signal | Skip rule |
|---|---|---|---|
| 1 | "1 câu mô tả feature/việc cần làm?" | `intent_text` + LLM-classify `change_type` ∈ {new-behavior, bug-fix, refactor, chore, hotfix} | provided as `$ARG` |
| 2 | "Touch module nào? (chọn từ `wbs_module_list` / multiple / unsure)" | `target_module`, `cross_module_surface` | suy rõ từ intent |
| 3 | (nếu change_type=hotfix) "Có nằm trong 5 loại preset: typo / config / log-level / lint / test-fix?" | `is_express_eligible` | change_type ≠ hotfix |
| 4 | (auto) Grep `project_wbs.md` cho id match keyword trong intent | `wbs_id_match` (id hoặc null) | — |
| 5 | "Scope: ≤3 unit hay >3?" | `scope_attestation` | change_type=hotfix |
| 6 | (nếu target_module touch contract — INT-* hoặc intent mention API) "Có đổi response shape của contract đã có không?" | `breaks_existing_contract` | non-API rõ ràng |
| 7 | "Đụng tiền / auth / RBAC / PII không?" | `touches_critical_domain` → drive Mandatory ATDD | clearly cosmetic |
| 8 | (nếu intent có keyword regulator/compliance/audit) "Audience demo: internal / customer / regulator?" | `demo_audience` | không có keyword |
| 9 | (nếu target_module UI hoặc intent UI) "Reuse UX journey hay introduce actor/flow mới?" | `introduces_new_actor` | non-UI |

Vagueness/multi-feature check inline → trigger refuse case 2/3 ở Bước 2.

---

### Bước 2 — HARD GATES (single source for refusal)

Áp theo thứ tự, refuse ngay khi match. Output: `❌ {reason} → unblock: {command}`.

| # | Trigger | Unblock |
|---|---|---|
| 1 | `!wbs_present` | `/bmad-create-prd` → `/bmad-create-epics-and-stories` → `/ntapp-architecture-design` |
| 2 | `intent_text` thiếu (verb + object + module hint) sau Q1-Q2 | "Viết 1 đoạn problem statement (vấn đề + actor + outcome), re-run." |
| 3 | LLM phát hiện intent ≥2 goals không liên quan | "Split intent, re-run per feature." |
| 4 | `breaks_existing_contract=yes` | "Module 0 contract change → escalate SA + Compliance. Stage 2 re-run với Module 0 update, KHÔNG triagable." |
| 5 | `target_module` không có trong `wbs_module_list` (module mới) | "Module mới → Stage 2 Agent C re-lock WBS, sau đó re-run triage." |
| 6 | `change_type=new-behavior` AND `!wbs_id_match` AND không phải hotfix | "Unit mới chưa trong WBS. Amend WBS bằng `/ntapp-architecture-design --append` (mode nhẹ — merge unit mới + audit + sync HLD §3.2.0, KHÔNG re-run full pipeline). Nếu unit chạm contract/boundary Module 0 → append escalate sang FULL re-lock. Sau khi amend → re-run triage." |
| 7 | `target_module=INT` AND `!module0_present` | "Module 0 missing — finish Stage 2 trước." |

WARN-only (không refuse): `wbs_unit_count ≥ 15` OR `wbs_module_list.size ≥ 5` → ghi vào decision file: "Phase 1 threshold reached → cân nhắc Phase 1.5 trước khi pile thêm feature." Tiếp tục triage.

---

### Bước 3 — Lane selection

Pass Bước 2 → áp decision tree (first-match wins):

```
if change_type=hotfix AND is_express_eligible:
    → LANE 1 (Express)

elif change_type ∈ {bug-fix, refactor, chore}
     AND scope_attestation=≤3
     AND wbs_id_match
     AND !touches_critical_domain:
    → LANE 2 (Path B quick-dev)

elif wbs_unit_count ≤ 3:
    → LANE 4 trigger-A (Ad-hoc per-unit — project PoC scale)

elif wbs_id_match AND active_slice_count > 0:
    if id ∈ active SLICE-N (parse SLICE-*.md):
        → LANE 3 (Full per-slice loop — resume SLICE-N)
    else:
        → ADVISORY: "Unit trong WBS nhưng không thuộc slice active.
                     Chạy /ntapp-slice-planning --rerun để re-balance."

elif change_type=new-behavior
     AND scope_attestation=≤3
     AND target_module ∈ wbs_module_list
     AND breaks_existing_contract=no
     AND !introduces_new_actor:
    → LANE 4 trigger-B (Ad-hoc per-unit — per-feature contained)

else:
    → LANE 3 (default — Full per-slice loop)
```

---

### Bước 4 — Lane modifiers

#### 4.1 — Resolve DS của feature (chỉ chạy khi target là UI module)

Chạy SAU Bước 1-3 vì cần `target_module` + `wbs_id_match`. Thủ tục chuẩn: `design-system/_shared/ds-resolution.md` **nhánh B** — triage KHÔNG tự chế logic resolve.

- `ds_systems` chỉ có **1 entry** (legacy không registry, hoặc registry 1 system) → `ds_id_target` = system đó, `ds_bootstrap_done = ds_bootstrap_map[đó]`. **Hành vi y hệt trước multi-DS.**
- **≥2 systems** → match theo thứ tự tín hiệu B.4, dừng ở tín hiệu đầu tiên cho kết quả DUY NHẤT:
  1. thẻ `<br>- repo: <code-repo>` ở Cluster Header của cluster chứa `wbs_id_match` trong `project_wbs.md` → khớp `systems.{ds}.code_repo`;
  2. `id_prefixes` — longest-prefix match trên `wbs_id_match`;
  3. `target_module` ∈ `systems.{ds}.modules`;
  4. `default_ds`.
- Tín hiệu 1 mâu thuẫn 2/3 (config drift) → **KHÔNG chọn im lặng**: `ds_bootstrap_done = unknown`, ghi vào decision file "registry hints ↔ thẻ WBS `repo:` lệch nhau — DSO sửa trước khi build".
- Không tín hiệu nào khớp (feature chưa có unit trong WBS, cluster thiếu thẻ `repo:`) → `ds_bootstrap_done = unknown`, KHÔNG đoán.

`unknown` là advisory, **không refuse** — triage vẫn emit modifier dưới dạng liệt kê ứng viên. STOP-hỏi-HITL thật sự thuộc về Stage 4a/4b (nhánh B), nơi unit đã xác định.

#### 4.2 — Injection

Sau khi chọn lane, áp injection (additive, không đổi lane):

| Condition | Inject |
|:--|:--|
| `touches_critical_domain=true` AND lane ∈ {2, 3, 4} | "`/bmad-testarch-atdd` BEFORE first commit (Mandatory ATDD)" |
| `demo_audience=regulator` | "`/bmad-testarch-nfr` + `/bmad-testarch-trace` BEFORE sign-off" |
| `introduces_new_actor=true` AND lane=3 | "`/ntapp-ux-sketch` BEFORE `/ntapp-technical-design`" |
| `ds_bootstrap_done=false` AND UI module | "`/ntapp-ds-bootstrap` FIRST cho DS `{ds_id_target}` (one-time / FE repo `{code_repo}`)" |
| `ds_bootstrap_done=unknown` AND UI module | "DS của feature chưa resolve được (xem 4.1) — DS chưa bootstrap: {liệt kê `ds_id` có `ds_bootstrap_map=false`}. Chạy `/ntapp-ds-bootstrap` từ FE repo tương ứng trước Stage 4b." |
| lane=4 trigger-B AND `scope_creep_guardrail=true` | "Write manifest `{manifest_dir}/{id}.yaml` (xem 5b)" |

`atdd_class = mandatory` IFF `touches_critical_domain=true`; else `optional`.

---

### Bước 5 — Emit output

#### 5a. Decision file (LUÔN ghi)

Path: `{triage_output_dir}/{YYYY-MM-DD}-{slug-from-intent}.md`

```markdown
# Triage Decision — {slug}

**Date:** {YYYY-MM-DD}  **Triaged by:** {git user.name}
**Intent:** {intent_text}

## Recommended Lane
**LANE {N} — {name}**{lane-specific suffix, vd "(resume SLICE-N)" hoặc "(trigger-B)"}

## Reasoning
- {signal_key}={value}  ← {tại sao signal này khiến chọn lane này}
- ... (list mọi signal đã collect — positive và negative)

## Next Slash Command
```
{exact command}
```

## Subsequent Steps (preview)
1. {command 1}
2. {command 2}
...

## Injected Modifiers
- {modifier 1} (lý do)

## Refused Paths
- LANE {X}: blocked — {reason}

## Honest Limits
{copy 4-5 limit liên quan từ section "Honest limits" dưới}
```

#### 5b. Manifest (chỉ ghi khi lane=4 trigger-B AND `scope_creep_guardrail=true`)

Path: `{manifest_dir}/{id}.yaml`

```yaml
# AUTO-GENERATED by /ntapp-feature-triage — DO NOT EDIT manually
# Pre-commit hook (nếu enabled) enforce bounds tại commit time.
id: {id}
type: {new | modify}
parent_module: {wbs_module}
parent_epic: {epic_id_from_wbs_lookup}
scope:
  units_planned: [{id}]
  max_units: 2
attestations:
  module_0_unchanged: true        # Q6
  no_new_contract: true
  no_new_module: true             # verified ở Bước 2 gate 5
  actor_journey: {reuse-only | minor-delta}  # Q9
atdd_class: {optional | mandatory}
demo_audience: {internal | customer | regulator}
triaged_at: {ISO-8601 timestamp}
triaged_by: {git user.name}
triage_log: {relative path to 5a decision file}
```

Manifest tự nó không enforce gì — cần hook đọc file này (chưa implement). Khi hook chưa có, manifest là documentation + tripwire bằng mắt khi reviewer xem PR.

---

## Honest limits — skill KHÔNG detect được

Ghi vào mọi decision file mục "Honest Limits" (copy các item áp dụng):

- **True scope** — `scope_attestation` là LLM guess + dev claim; thực tế chỉ biết sau DD. Skill không ngăn under-estimation; phụ thuộc dev discipline + code review.
- **Contract drift implicit** — `breaks_existing_contract` dựa dev honesty; skill không diff được code. Dev nói "no" nhưng thực tế đổi DTO → caught muộn ở Stage 3 contract review.
- **Cross-slice ripple** — không predict Lane 3 slice force sibling slice re-balance không; emerges ở Stage 5 retro.
- **DS token gaps** — chỉ flag nếu intent mention visual primitive; gap tinh tế surface ở `/ntapp-ui-generation`.
- **DS binding tại intake (multi-DS)** — `ds_id_target` resolve từ WBS + registry hints; feature chưa có unit trong WBS, hoặc project ≥2 FE repo mà cluster thiếu thẻ `repo:` → skill chỉ liệt kê ứng viên, không chốt. Binding thật chốt ở Stage 4a/4b (`ds-resolution.md` nhánh B, có STOP HITL).
- **Test-first discipline trong Lane 2** — `/bmad-quick-dev` không enforce ATDD; skill chỉ recommend.
- **Stale slice plan vs WBS** — không auto-detect `slices/SLICE-*.md` cũ hơn `project_wbs.md`; dev tự re-run `/ntapp-slice-planning`.

---

## Re-run

Skill idempotent — re-run cùng intent + cùng project state → cùng output (decision file mới timestamp, manifest overwrite). Re-run khi: attestation sai, WBS đổi, scope creep mid-build.

---

## Scope

Skill **chỉ** sinh: decision file (luôn) + manifest (opt-in lane=4 trigger-B). KHÔNG modify: WBS, DD, UI schema, code, hooks, docs khác.
